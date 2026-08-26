from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from fastapi import HTTPException

from app.models.clienteCuenta import ClienteCuenta
from app.models.clienteServicio import ClienteServicio
from app.models.clienteServicioPeriodo import ClienteServicioPeriodo
from app.services.pagoService import PagoService
from app.services.historicoService import registrar_evento_cliente
from app.schemas.enumsHistorico import TipoEventoCodigoEnum

from app.utils.periodos import mes_inicio, vencimiento_mes


def _resolver_cuenta(
    db: Session, legajo: int, id_cuenta: int | None, *, lock: bool = False
) -> ClienteCuenta:
    """
    Devuelve la cuenta a usar para el cliente.
    - Si id_cuenta es None y hay una sola cuenta -> usa esa.
    - Si hay múltiples y no se envió id_cuenta -> error 400/409.
    - Si se envió id_cuenta que no pertenece -> 404.
    """
    ids = (
        db.execute(
            select(ClienteCuenta.id_cuenta).where(ClienteCuenta.legajo == legajo)
        )
        .scalars()
        .all()
    )

    if not ids:
        raise HTTPException(
            status_code=409, detail="El cliente no tiene cuenta creada."
        )

    if id_cuenta is None:
        if len(ids) > 1:
            raise HTTPException(
                status_code=400,
                detail="El cliente tiene múltiples cuentas. Enviar id_cuenta.",
            )
        id_cuenta = ids[0]
    else:
        if id_cuenta not in ids:
            raise HTTPException(
                status_code=404,
                detail="Cuenta no encontrada para ese cliente.",
            )

    stmt = (
        select(ClienteCuenta)
        .where(
            ClienteCuenta.legajo == legajo,
            ClienteCuenta.id_cuenta == id_cuenta,
        )
        .with_for_update()
        if lock
        else select(ClienteCuenta).where(
            ClienteCuenta.legajo == legajo, ClienteCuenta.id_cuenta == id_cuenta
        )
    )

    cuenta = db.execute(stmt).scalar_one_or_none()
    if cuenta is None:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada.")
    return cuenta


def crear_servicio_alquiler_dispenser(
    db: Session,
    legajo: int,
    monto_mensual: Decimal,
) -> tuple[ClienteServicio, ClienteServicioPeriodo]:
    fecha_inicio = date.today()

    existe = db.execute(
        select(ClienteServicio).where(
            ClienteServicio.legajo == legajo,
            ClienteServicio.tipo_servicio == "ALQUILER_DISPENSER",
            ClienteServicio.activo,
        )
    ).scalar_one_or_none()
    if existe:
        raise HTTPException(409, "El cliente ya tiene un alquiler de dispenser activo.")

    srv = ClienteServicio(
        legajo=legajo,
        tipo_servicio="ALQUILER_DISPENSER",
        monto_mensual=monto_mensual,
        fecha_inicio=fecha_inicio,
        activo=True,
    )
    db.add(srv)
    db.flush()

    periodo = mes_inicio(fecha_inicio)
    per = _upsert_periodo(
        db,
        srv,
        periodo,
        estado="PENDIENTE",
        fecha_pago=None,
    )
    try:
        registrar_evento_cliente(
            db,
            legajo=legajo,
            codigo_evento=TipoEventoCodigoEnum.DISPENSER_ALTA,
            observacion=f"Alta de alquiler dispenser a ${monto_mensual}/mes",
            datos={
                "id_cliente_servicio": srv.id_cliente_servicio,
                "monto_mensual": str(monto_mensual),
                "fecha_inicio": fecha_inicio.isoformat(),
                "id_periodo": per.id_periodo,
                "periodo": per.periodo.isoformat(),
            },
        )
    except RuntimeError:
        pass

    db.flush()
    return srv, per


def _upsert_periodo(
    db: Session,
    srv: ClienteServicio,
    periodo: date,
    *,
    estado: str = "PENDIENTE",
    fecha_pago: date | None = None,
) -> ClienteServicioPeriodo:
    per = db.execute(
        select(ClienteServicioPeriodo).where(
            ClienteServicioPeriodo.id_cliente_servicio == srv.id_cliente_servicio,
            ClienteServicioPeriodo.periodo == periodo,
        )
    ).scalar_one_or_none()

    if per:
        return per

    per = ClienteServicioPeriodo(
        id_cliente_servicio=srv.id_cliente_servicio,
        periodo=periodo,
        monto=srv.monto_mensual,
        monto_pendiente=Decimal("0") if estado == "PAGADO" else Decimal(srv.monto_mensual),
        estado=estado,
        fecha_vencimiento=vencimiento_mes(periodo),
        fecha_pago=fecha_pago,
    )
    db.add(per)
    db.flush()
    return per


def asegurar_periodo_mes_actual(db: Session, legajo: int) -> None:
    hoy = date.today()
    periodo = mes_inicio(hoy)

    servicios = (
        db.execute(
            select(ClienteServicio).where(
                ClienteServicio.legajo == legajo, ClienteServicio.activo
            )
        )
        .scalars()
        .all()
    )

    for srv in servicios:
        _upsert_periodo(db, srv, periodo)


def listar_pendientes_cliente(db: Session, legajo: int):
    # asegura período actual antes de listar
    asegurar_periodo_mes_actual(db, legajo)

    stmt = (
        select(ClienteServicioPeriodo)
        .join(
            ClienteServicio,
            ClienteServicio.id_cliente_servicio
            == ClienteServicioPeriodo.id_cliente_servicio,
        )
        .where(
            ClienteServicio.legajo == legajo,
            ClienteServicio.activo,
            ClienteServicioPeriodo.estado.in_(["PENDIENTE", "VENCIDO"]),
        )
        .order_by(ClienteServicioPeriodo.periodo.desc())
    )
    return db.execute(stmt).scalars().all()


def marcar_vencidos(db: Session) -> int:
    hoy = date.today()

    stmt = (
        select(ClienteServicioPeriodo)
        .options(selectinload(ClienteServicioPeriodo.servicio))
        .where(
            ClienteServicioPeriodo.estado == "PENDIENTE",
            ClienteServicioPeriodo.fecha_vencimiento < hoy,
        )
        .with_for_update()
    )

    periodos = db.execute(stmt).scalars().all()
    procesados = 0

    for per in periodos:
        per.estado = "VENCIDO"
        procesados += 1
        try:
            registrar_evento_cliente(
                db,
                legajo=per.servicio.legajo,
                codigo_evento=TipoEventoCodigoEnum.PERIODO_VENCIDO,
                observacion=f"Período {per.periodo.strftime('%Y-%m')} de dispenser vencido",
                datos={
                    "id_periodo": per.id_periodo,
                    "periodo": per.periodo.isoformat(),
                    "monto_pendiente": str(per.monto_pendiente),
                    "id_cliente_servicio": per.id_cliente_servicio,
                },
            )
        except RuntimeError:
            pass

    return procesados


def pagar_periodo_servicio(
    db: Session,
    id_periodo: int,
    legajo: int,
    id_medio_pago: int | None = None,
    observacion: str | None = None,
    *,
    id_cuenta: int | None = None,
    usar_saldo: bool = False,
):
    per = db.execute(
        select(ClienteServicioPeriodo)
        .where(ClienteServicioPeriodo.id_periodo == id_periodo)
        .with_for_update()
    ).scalar_one_or_none()

    if not per:
        raise HTTPException(status_code=404, detail="Periodo inexistente.")

    srv = db.execute(
        select(ClienteServicio).where(
            ClienteServicio.id_cliente_servicio == per.id_cliente_servicio
        )
    ).scalar_one()

    if srv.legajo != legajo:
        raise HTTPException(
            status_code=403, detail="El periodo no pertenece al cliente."
        )

    if per.estado == "PAGADO":
        raise HTTPException(status_code=409, detail="El periodo ya está pagado.")

    cuenta = _resolver_cuenta(db, legajo, id_cuenta=id_cuenta, lock=True)

    monto = Decimal(per.monto_pendiente or per.monto or Decimal("0"))
    if monto <= 0:
        raise HTTPException(
            status_code=409,
            detail="El período no tiene monto pendiente para cobrar.",
        )

    pago = None

    if usar_saldo:
        saldo = Decimal(cuenta.saldo or Decimal("0"))
        if saldo < monto:
            raise HTTPException(
                status_code=409,
                detail="Saldo insuficiente para cubrir el período.",
            )

        cuenta.saldo = saldo - monto

    else:
        if id_medio_pago is None:
            raise HTTPException(
                status_code=400,
                detail="id_medio_pago es obligatorio salvo usar_saldo.",
            )

        pago = PagoService.crear(
            db,
            id_empresa=1,
            id_medio_pago=id_medio_pago,
            fecha=datetime.now(),
            monto=monto,
            tipo_pago="SERVICIO",
            observacion=observacion
            or f"Pago alquiler dispenser {per.periodo.strftime('%Y-%m')}",
            legajo=legajo,
            id_cliente_servicio_periodo=per.id_periodo,
            id_cuenta=cuenta.id_cuenta,
            impactar_cuenta=False,
        )

    per.estado = "PAGADO"
    per.fecha_pago = date.today()
    per.monto_pendiente = Decimal("0")

    try:
        registrar_evento_cliente(
            db,
            legajo=legajo,
            codigo_evento=TipoEventoCodigoEnum.DISPENSER_PAGO,
            observacion=f"Pago alquiler dispenser {per.periodo.strftime('%Y-%m')}",
            datos={
                "id_periodo": per.id_periodo,
                "periodo": per.periodo.isoformat(),
                "monto": str(monto),
                "id_pago": pago.id_pago if pago else None,
                "usando_saldo": usar_saldo,
            },
        )
    except RuntimeError:
        pass

    return pago, monto


def actualizar_monto_servicio(
    db,
    *,
    id_cliente_servicio: int,
    nuevo_monto: Decimal,
    aplicar_desde: date | None = None,
    actualizar_periodos_no_pagados: bool = True,
):
    if nuevo_monto <= 0:
        raise HTTPException(status_code=400, detail="monto_mensual debe ser > 0")

    vigencia = mes_inicio(aplicar_desde or date.today())

    # lock del servicio
    srv = db.execute(
        select(ClienteServicio)
        .where(ClienteServicio.id_cliente_servicio == id_cliente_servicio)
        .with_for_update()
    ).scalar_one_or_none()

    if not srv:
        raise HTTPException(status_code=404, detail="Servicio inexistente.")
    if not srv.activo:
        raise HTTPException(status_code=409, detail="El servicio está inactivo.")

    # 1) actualizar precio base del servicio
    monto_anterior = Decimal(str(srv.monto_mensual))
    srv.monto_mensual = nuevo_monto

    # 2) opcional: actualizar períodos no pagados desde vigencia
    if actualizar_periodos_no_pagados:
        periodos = (
            db.execute(
                select(ClienteServicioPeriodo)
                .where(
                    ClienteServicioPeriodo.id_cliente_servicio
                    == srv.id_cliente_servicio,
                    ClienteServicioPeriodo.periodo >= vigencia,
                    ClienteServicioPeriodo.estado != "PAGADO",
                )
                .with_for_update()
            )
            .scalars()
            .all()
        )

        for p in periodos:
            p.monto = nuevo_monto
            if p.estado == "PENDIENTE":
                p.monto_pendiente = nuevo_monto

    try:
        registrar_evento_cliente(
            db,
            legajo=srv.legajo,
            codigo_evento=TipoEventoCodigoEnum.CAMBIO_PRECIO_DISPENSER,
            observacion=f"Cambio de precio dispenser de ${monto_anterior} a ${nuevo_monto}",
            datos={
                "id_cliente_servicio": srv.id_cliente_servicio,
                "monto_anterior": str(monto_anterior),
                "monto_nuevo": str(nuevo_monto),
                "aplicar_desde": vigencia.isoformat(),
            },
        )
    except RuntimeError:
        pass

    return srv


def dar_de_baja_dispenser(db: Session, id_cliente_servicio: int) -> ClienteServicio:
    srv = db.execute(
        select(ClienteServicio)
        .where(ClienteServicio.id_cliente_servicio == id_cliente_servicio)
        .with_for_update()
    ).scalar_one_or_none()

    if not srv:
        raise HTTPException(status_code=404, detail="Servicio inexistente.")
    if not srv.activo:
        raise HTTPException(status_code=409, detail="El servicio ya está inactivo.")

    srv.activo = False

    try:
        registrar_evento_cliente(
            db,
            legajo=srv.legajo,
            codigo_evento=TipoEventoCodigoEnum.DISPENSER_DADO_DE_BAJA,
            observacion="Baja del alquiler de dispenser",
            datos={
                "id_cliente_servicio": srv.id_cliente_servicio,
                "monto_mensual": str(srv.monto_mensual),
                "fecha_inicio": srv.fecha_inicio.isoformat(),
            },
        )
    except RuntimeError:
        pass

    return srv


def listar_servicios_cliente(db: Session, legajo: int):
    return (
        db.execute(
            select(ClienteServicio)
            .where(ClienteServicio.legajo == legajo)
            .order_by(ClienteServicio.id_cliente_servicio.desc())
        )
        .scalars()
        .all()
    )