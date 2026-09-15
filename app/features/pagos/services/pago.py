from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from contextlib import nullcontext

from app.core.exceptions import AppError, Conflict, NotFound
from app.features.pagos.services.idempotency import buscar_por_idempotency_key

from app.features.pagos.models.pago import Pago
from app.features.maestros.models.medio_pago import MedioPago
from app.features.clientes.models.cliente_cuenta import ClienteCuenta
from app.features.repartos.repartos_dia.models.reparto_dia import RepartoDia
from app.features.caja.models.caja_empresa import CajaEmpresa
from app.features.pagos.schemas import PagoLibreIn, PagoLibreOut
from app.features.documentos.services.comprobante_pago import ComprobantePagoService
from app.features.auditoria.service import registrar_evento_cliente
from app.features.auditoria.schemas.enums_historico import TipoEventoCodigoEnum
from app.features.empresas.service import EmpresaService

TWOPLACES = Decimal("0.01")


def _q2(v: Decimal | None) -> Decimal:
    v = Decimal("0") if v is None else Decimal(v)
    return v.quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def _bucket_medio_pago(nombre: str) -> str:
    n = (nombre or "").strip().lower()
    if n in {"efectivo", "cash"}:
        return "efectivo"
    if n in {
        "transferencia",
        "virtual",
        "tarjeta",
        "debito",
        "crédito",
        "credito",
        "qr",
        "mp",
        "mercadopago",
    }:
        return "virtual"
    raise AppError(f"medio_pago no soportado: {nombre!r}")


def _aplicar_pago_a_cuenta(cuenta: ClienteCuenta, monto: Decimal) -> None:
    monto = _q2(monto)
    deuda = _q2(cuenta.deuda or Decimal("0"))
    saldo = _q2(cuenta.saldo or Decimal("0"))

    if monto <= deuda:
        cuenta.deuda = _q2(deuda - monto)
    else:
        sobrante = _q2(monto - deuda)
        cuenta.deuda = _q2(Decimal("0"))
        cuenta.saldo = _q2(saldo + sobrante)


def _sumar_recaudacion_reparto(rep: RepartoDia, bucket: str, monto: Decimal) -> None:
    monto = _q2(monto)
    rep.total_recaudado = _q2(getattr(rep, "total_recaudado", Decimal("0.00"))) + monto
    if bucket == "efectivo":
        rep.total_efectivo = (
            _q2(getattr(rep, "total_efectivo", Decimal("0.00"))) + monto
        )
    else:
        rep.total_virtual = _q2(getattr(rep, "total_virtual", Decimal("0.00"))) + monto


class PagoService:
    @staticmethod
    def crear(
        db: Session,
        *,
        id_empresa: int,
        id_medio_pago: int,
        fecha: datetime,
        monto: Decimal,
        tipo_pago: str,
        observacion: str | None = None,
        legajo: int | None = None,
        id_cuenta: int | None = None,
        id_pedido: int | None = None,
        id_repartodia: int | None = None,
        id_cliente_servicio_periodo: int | None = None,
        id_tipo_mov_ingreso: int = 1,
        id_tipo_mov_egreso: int = 2,
        impactar_cuenta: bool = True,
        impactar_reparto: bool = True,
        idempotency_key: str | None = None,
        client_uuid: str | None = None,
    ) -> Pago:
        monto = _q2(monto)
        if monto <= 0:
            raise AppError("monto debe ser > 0")

        # Idempotencia (offline sync): si ya llegó este pago, devolver el original
        existente = buscar_por_idempotency_key(db, Pago, idempotency_key)
        if existente is not None:
            return existente

        started_tx = not db.in_transaction()
        tx_ctx = db.begin() if started_tx else nullcontext()

        try:
            with tx_ctx:
                mp = db.execute(
                    select(MedioPago).where(MedioPago.id_medio_pago == id_medio_pago)
                ).scalar_one_or_none()
                if mp is None:
                    raise AppError("id_medio_pago inexistente.")
                bucket = _bucket_medio_pago(mp.nombre)

                if legajo is None and tipo_pago in {"COBRO_PEDIDO", "PAGO_DEUDA"}:
                    raise AppError("Falta legajo para pago de cliente.")

                # --- cuenta (si aplica) ---
                cuenta = None
                if legajo is not None:
                    if id_cuenta is None:
                        ids = (
                            db.execute(
                                select(ClienteCuenta.id_cuenta).where(
                                    ClienteCuenta.legajo == legajo
                                )
                            )
                            .scalars()
                            .all()
                        )
                        if not ids:
                            raise Conflict("El cliente no tiene cuenta creada.")
                        if len(ids) > 1:
                            raise AppError(
                                "El cliente tiene más de una cuenta. Enviar id_cuenta.",
                            )
                        id_cuenta = ids[0]

                    cuenta = db.execute(
                        select(ClienteCuenta)
                        .where(
                            ClienteCuenta.legajo == legajo,
                            ClienteCuenta.id_cuenta == id_cuenta,
                        )
                        .with_for_update()
                    ).scalar_one_or_none()
                    if cuenta is None:
                        raise NotFound("Cuenta no encontrada para ese cliente.")

                # --- reparto (si aplica) ---
                rep = None
                if id_repartodia is not None:
                    rep = db.execute(
                        select(RepartoDia)
                        .where(RepartoDia.id_repartodia == id_repartodia)
                        .with_for_update()
                    ).scalar_one_or_none()
                    if rep is None:
                        raise NotFound("Reparto del día no encontrado")

                # --- crear pago ---
                pago = Pago(
                    id_empresa=id_empresa,
                    legajo=legajo,
                    id_pedido=id_pedido,
                    id_repartodia=id_repartodia,
                    id_medio_pago=id_medio_pago,
                    fecha=fecha,
                    monto=monto,
                    tipo_pago=tipo_pago,
                    observacion=observacion,
                    id_cuenta=id_cuenta,  # ✅ AGREGAR
                    id_cliente_servicio_periodo=id_cliente_servicio_periodo,
                    idempotency_key=idempotency_key,
                    client_uuid=client_uuid,
                )
                db.add(pago)
                db.flush()

                # --- caja empresa ---
                es_egreso = tipo_pago in {"EGRESO_EMPRESA"}
                id_tipo_mov = id_tipo_mov_egreso if es_egreso else id_tipo_mov_ingreso
                tipo = "egreso" if es_egreso else "ingreso"

                monto_caja = -monto if es_egreso else monto
                mov = CajaEmpresa(
                    id_empresa=id_empresa,
                    id_tipo_movimiento=id_tipo_mov,
                    id_medio_pago=id_medio_pago,
                    fecha=fecha,
                    tipo=tipo,
                    monto=monto_caja,
                    observacion=(
                        f"PAGO#{pago.id_pago} {tipo_pago} - {observacion}"
                        if observacion
                        else f"PAGO#{pago.id_pago} {tipo_pago}"
                    ),
                )
                db.add(mov)

                # --- impactar cuenta/reparto ---
                if (
                    cuenta is not None
                    and impactar_cuenta
                    and tipo_pago in {"COBRO_PEDIDO", "PAGO_DEUDA"}
                ):
                    _aplicar_pago_a_cuenta(cuenta, monto)

                if (
                    rep is not None
                    and impactar_reparto
                    and tipo_pago in {"COBRO_PEDIDO", "PAGO_DEUDA"}
                ):
                    _sumar_recaudacion_reparto(rep, bucket, monto)

                return pago

        except IntegrityError:
            # Carrera entre dos reintentos del mismo pago: el índice único de
            # idempotency_key rechazó el segundo. Devolvemos el que sí se creó.
            if started_tx:
                db.rollback()
            existente = buscar_por_idempotency_key(db, Pago, idempotency_key)
            if existente is not None:
                return existente
            raise
        except SQLAlchemyError:
            if started_tx:
                db.rollback()
            raise

    @staticmethod
    def crear_pago_libre(
        db: Session,
        data: PagoLibreIn,
    ) -> PagoLibreOut:

        # 1️⃣ Crear el pago
        pago = PagoService.crear(
            db,
            id_empresa=EmpresaService.get_id_empresa_actual(db),
            id_medio_pago=data.id_medio_pago,
            fecha=datetime.now(timezone.utc).replace(tzinfo=None),
            monto=data.monto,
            tipo_pago="PAGO_DEUDA",
            observacion=data.observacion,
            legajo=data.legajo,
            id_cuenta=data.id_cuenta,
            id_repartodia=data.id_repartodia,
        )

        # 2️⃣ Generar y guardar comprobante
        doc = ComprobantePagoService.generar_y_guardar(
            db,
            id_pago=pago.id_pago,
        )

        # 3️⃣ Registrar en histórico del cliente
        if data.legajo is not None:
            try:
                registrar_evento_cliente(
                    db,
                    legajo=data.legajo,
                    codigo_evento=TipoEventoCodigoEnum.PAGO_DEUDA_REGISTRADO,
                    observacion=data.observacion or "Pago libre de deuda",
                    datos={
                        "monto": str(data.monto),
                        "id_pago": pago.id_pago,
                    },
                )
                db.commit()
            except RuntimeError:
                db.rollback()

        return PagoLibreOut(
            id_pago=pago.id_pago,
            comprobante_url=doc.url_archivo,
        )

    @staticmethod
    def asignar_a_reparto(db: Session, id_pago: int, id_repartodia: int) -> Pago:
        """
        Asigna un pago YA EXISTENTE a un reparto, actualizando los totales de recaudación
        del reparto (efectivo/virtual/total).
        NO genera movimiento en CajaEmpresa (se asume que se generó al crear el pago).
        """
        # 1) Traer Pago + MedioPago
        stmt = select(Pago).where(Pago.id_pago == id_pago).with_for_update()
        pago = db.execute(stmt).scalar_one_or_none()

        if not pago:
            raise NotFound("Pago no encontrado.")

        if pago.id_repartodia is not None:
            raise Conflict(
                f"El pago {id_pago} ya está asignado al reparto {pago.id_repartodia}.",
            )

        # Necesitamos el medio de pago para saber el bucket (efectivo vs virtual)
        mp = db.execute(
            select(MedioPago).where(MedioPago.id_medio_pago == pago.id_medio_pago)
        ).scalar_one()
        bucket = _bucket_medio_pago(mp.nombre)

        # 2) Traer RepartoDia
        rep = db.execute(
            select(RepartoDia)
            .where(RepartoDia.id_repartodia == id_repartodia)
            .with_for_update()
        ).scalar_one_or_none()

        if not rep:
            raise NotFound("RepartoDia no encontrado.")

        # 3) Asignar y actualizar
        pago.id_repartodia = id_repartodia
        _sumar_recaudacion_reparto(rep, bucket, pago.monto)

        db.flush()
        return pago
