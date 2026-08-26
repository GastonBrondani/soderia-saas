from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from fastapi import APIRouter, Depends, HTTPException
from app.core.security import get_current_user, require_admin, CurrentUser
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.database import get_db
from app.api.deps import get_cliente_or_404_dep
from app.models.clienteCuenta import ClienteCuenta
from app.models.pedido import Pedido
from app.schemas.clienteCuenta import (
    ClienteCuentaCreate,
    ClienteCuentaOut,
    ClienteCuentaUpdate,
    AplicarInteresIn,
    AplicarInteresOut,
)
from app.services.historicoService import registrar_evento_cliente
from app.schemas.enumsHistorico import TipoEventoCodigoEnum

_TWOPLACES = Decimal("0.01")


def _q2(v) -> Decimal:
    v = Decimal("0") if v is None else Decimal(str(v))
    return v.quantize(_TWOPLACES, rounding=ROUND_HALF_UP)

router = APIRouter(prefix="/clientes/{legajo}", tags=["ClienteCuenta"],dependencies=[Depends(get_current_user)],)

def _get_cuenta_or_404(db: Session, legajo: int, id_cuenta: int) -> ClienteCuenta:
    cuenta = db.execute(
        select(ClienteCuenta).where(
            ClienteCuenta.legajo == legajo,
            ClienteCuenta.id_cuenta == id_cuenta,
        )
    ).scalar_one_or_none()
    if not cuenta:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada.")
    return cuenta

@router.post("/cuentas", response_model=ClienteCuentaOut, status_code=201)
def create_cuenta(legajo: int, payload: ClienteCuentaCreate, db: Session = Depends(get_db)):
    get_cliente_or_404_dep(legajo, db)
    cuenta = ClienteCuenta(legajo=legajo, **payload.model_dump(exclude_unset=True))
    db.add(cuenta)
    db.commit()
    db.refresh(cuenta)
    return cuenta

@router.get("/cuentas", response_model=list[ClienteCuentaOut])
def listar_cuentas(legajo: int, db: Session = Depends(get_db)):
    get_cliente_or_404_dep(legajo, db)
    return db.execute(
        select(ClienteCuenta).where(ClienteCuenta.legajo == legajo)
    ).scalars().all()

@router.get("/cuentas/{id_cuenta}", response_model=ClienteCuentaOut)
def obtener_cuenta(legajo: int, id_cuenta: int, db: Session = Depends(get_db)):
    get_cliente_or_404_dep(legajo, db)
    return _get_cuenta_or_404(db, legajo, id_cuenta)

@router.put("/cuentas/{id_cuenta}", response_model=ClienteCuentaOut)
def actualizar_cuenta(
    legajo: int,
    id_cuenta: int,
    payload: ClienteCuentaUpdate,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_admin),
):
    get_cliente_or_404_dep(legajo, db)
    cuenta = _get_cuenta_or_404(db, legajo, id_cuenta)

    updates = payload.model_dump(exclude_unset=True, exclude={"id_cuenta"})
    for campo, valor in updates.items():
        setattr(cuenta, campo, valor)

    db.add(cuenta)
    db.commit()
    db.refresh(cuenta)
    return cuenta


@router.post("/cuentas/{id_cuenta}/aplicar-interes", response_model=AplicarInteresOut, status_code=200)
def aplicar_interes(
    legajo: int,
    id_cuenta: int,
    payload: AplicarInteresIn,
    db: Session = Depends(get_db),
):
    get_cliente_or_404_dep(legajo, db)

    cuenta = db.execute(
        select(ClienteCuenta)
        .where(ClienteCuenta.legajo == legajo, ClienteCuenta.id_cuenta == id_cuenta)
        .with_for_update()
    ).scalar_one_or_none()
    if cuenta is None:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada.")

    deuda_anterior = _q2(cuenta.deuda or Decimal("0"))
    if deuda_anterior <= Decimal("0"):
        raise HTTPException(status_code=400, detail="El cliente no tiene deuda pendiente.")

    # Verificar que exista al menos un pedido impago con más de 30 días de antigüedad
    limite_fecha = datetime.now() - timedelta(days=30)
    pedido_vencido = db.execute(
        select(Pedido).where(
            Pedido.legajo == legajo,
            Pedido.estado.in_(["pendiente", "abonado_parcialmente"]),
            Pedido.fecha <= limite_fecha,
        )
    ).scalar_one_or_none()

    if pedido_vencido is None:
        raise HTTPException(
            status_code=400,
            detail="No hay deuda pendiente con más de 30 días de antigüedad.",
        )

    porcentaje = _q2(payload.porcentaje)
    interes = _q2(deuda_anterior * porcentaje / Decimal("100"))
    if interes <= Decimal("0"):
        raise HTTPException(status_code=400, detail="El interés calculado es $0.00.")

    cuenta.deuda = _q2(deuda_anterior + interes)
    fecha = datetime.now()

    try:
        registrar_evento_cliente(
            db,
            legajo=legajo,
            codigo_evento=TipoEventoCodigoEnum.INTERES_APLICADO,
            observacion=payload.observacion or f"Interés del {porcentaje}% aplicado sobre deuda de ${deuda_anterior}",
            datos={
                "id_cuenta": id_cuenta,
                "deuda_anterior": str(deuda_anterior),
                "interes_aplicado": str(interes),
                "deuda_nueva": str(cuenta.deuda),
                "porcentaje": str(porcentaje),
            },
        )
    except RuntimeError:
        # El tipo_evento INTERES_APLICADO no existe en la tabla tipo_evento.
        # Insertar: INSERT INTO tipo_evento (nombre) VALUES ('INTERES_APLICADO');
        pass

    db.commit()

    return AplicarInteresOut(
        id_cuenta=cuenta.id_cuenta,
        legajo=cuenta.legajo,
        deuda_anterior=deuda_anterior,
        interes_aplicado=interes,
        deuda_nueva=cuenta.deuda,
        porcentaje=porcentaje,
        fecha=fecha,
    )
