from datetime import datetime
from fastapi import APIRouter, Depends
from app.core.exceptions import AppError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import CurrentUser, get_current_user
from app.core.permissions import require_roles
from app.features.pedidos.schemas.pedido import PedidoCancelarDeudaIn
from app.features.clientes.schemas.cliente_cuenta import ClienteCuentaOut
from app.features.pedidos.service import PedidoService
from app.features.pagos.schemas import (
    PagoCreate,
    PagoLibreIn,
    PagoLibreOut,
    PagoOut,
    PagoEgresoCreate,
    PagoIngresoCreate,
)
from app.features.pagos.services.pago import PagoService
from app.features.documentos.services.comprobante_pago import ComprobantePagoService as ComprobantePagoServiceExtended
from app.features.empresas.service import EmpresaService


router = APIRouter(prefix="/pagos", tags=["Pagos"],dependencies=[Depends(get_current_user)],)


@router.post("/cancelar-deuda", response_model=ClienteCuentaOut)
def cancelar_deuda(
    data: PedidoCancelarDeudaIn,
    db: Session = Depends(get_db),
):
    """
    Permite registrar un pago de cuenta SIN generar un pedido.
    Actualiza deuda/saldo y la recaudación del reparto.
    """
    return PedidoService.cancelar_deuda(db, data)

@router.post("", response_model=PagoOut)
def crear_pago(payload: PagoCreate, db: Session = Depends(get_db)):
    """
    Crea un pago. Soporta idempotencia (offline sync): si llega un
    `idempotency_key` ya usado, no se duplica el pago y se devuelve el original.
    """
    return PagoService.crear(
        db,
        id_empresa=payload.id_empresa,
        id_medio_pago=payload.id_medio_pago,
        fecha=payload.fecha,
        monto=payload.monto,
        tipo_pago=payload.tipo_pago,
        observacion=payload.observacion,
        legajo=payload.legajo,
        id_pedido=payload.id_pedido,
        id_repartodia=payload.id_repartodia,
        idempotency_key=payload.idempotency_key,
        client_uuid=payload.client_uuid,
    )


@router.post("/ingreso", response_model=PagoOut)
def crear_ingreso(
    payload: PagoIngresoCreate,
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(require_roles("ADMIN")),
):
    observacion = (
        f"[INGRESO] {payload.observacion or ''}".strip()
        + f" (usuario {current.nombre_usuario})"
    )

    pago = PagoService.crear(
        db,
        id_empresa=EmpresaService.get_id_empresa_actual(db),
        id_medio_pago=payload.id_medio_pago,
        fecha=payload.fecha or datetime.utcnow(),
        monto=payload.monto,
        tipo_pago="INGRESO_EMPRESA",
        observacion=observacion,
        impactar_cuenta=False,
        impactar_reparto=False,
    )

    db.commit()
    db.refresh(pago)
    return pago


@router.post("/egreso", response_model=PagoOut)
def crear_egreso(
    payload: PagoEgresoCreate,
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(require_roles("ADMIN")),
):
    observacion = (
        f"[EGRESO {payload.motivo}] {payload.observacion or ''}".strip()
        + f" (usuario {current.nombre_usuario})"
    )

    pago = PagoService.crear(
        db,
        id_empresa=EmpresaService.get_id_empresa_actual(db),
        id_medio_pago=payload.id_medio_pago,
        fecha=payload.fecha or datetime.utcnow(),
        monto=payload.monto,
        tipo_pago="EGRESO_EMPRESA",
        observacion=observacion,
        impactar_cuenta=False,
        impactar_reparto=False,
    )

    db.commit()
    db.refresh(pago)
    return pago


@router.post("/{id_pago}/comprobante")
def generar_comprobante_pago(
    id_pago: int,
    db: Session = Depends(get_db),
):
    try:
        doc = ComprobantePagoServiceExtended.generar_y_guardar(db, id_pago=id_pago)
        return {
            "id_documento": doc.id_documento,
            "url": doc.url_archivo,
        }
    except Exception as e:
        print("ERROR GENERANDO COMPROBANTE:", repr(e))
        raise AppError(str(e))
    
@router.post("/libre", response_model=PagoLibreOut)
def crear_pago_libre(
    data: PagoLibreIn,
    db: Session = Depends(get_db),
):
    return PagoService.crear_pago_libre(db, data)
