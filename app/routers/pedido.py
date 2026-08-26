from fastapi import APIRouter, Depends, HTTPException, status, Response
from app.core.security import get_current_user
from sqlalchemy.orm import Session
from datetime import date

from app.core.database import get_db
from app.schemas.pedido import PedidoCreate, PedidoOut, PedidoConfirmarIn
from app.services.pedidoService import PedidoService
from app.services.comprobantePedidoService import ComprobantePedidoService


router = APIRouter(prefix="/pedidos", tags=["Pedidos"],dependencies=[Depends(get_current_user)],)

@router.post("/", response_model=PedidoOut, status_code=status.HTTP_201_CREATED)
def crear_pedido(data: PedidoCreate, response: Response, db: Session = Depends(get_db)):
    """
    Crea un pedido y ajusta la deuda del cliente (cliente_cuenta.deuda)
    en una sola transacción. Si el cliente no tiene cuenta, responde 409.

    Soporta idempotencia (offline sync): si llega un `idempotency_key` ya
    usado, no se duplica el pedido y se devuelve el original con 200.
    """
    pedido, creado = PedidoService.crear_pedido(db, data)
    if not creado:
        response.status_code = status.HTTP_200_OK
    return pedido

@router.post("/{id_pedido}/confirmar", response_model=PedidoOut, status_code=status.HTTP_200_OK)
def confirmar_pedido(id_pedido: int, data: PedidoConfirmarIn, db: Session = Depends(get_db)):
    """
    Confirma el pedido:
    - Linkea con id_repartodia
    - Actualiza total_recaudado + (efectivo|virtual) según medio_pago.nombre
    - Cambia estado a 'confirmado'
    """
    return PedidoService.confirmar_pedido(db, id_pedido, data)

#Cancelado
#@router.post("/cancelar-deuda", response_model=ClienteCuentaOut)
#def cancelar_deuda(
#    data: PedidoCancelarDeudaIn,
#    db: Session = Depends(get_db),
#):
#    """
#    Permite registrar un pago de cuenta SIN generar un pedido.
#    Actualiza deuda/saldo y la recaudación del reparto.
#    """
#    return PedidoService.cancelar_deuda(db, data)

@router.get("/por-fecha", response_model=list[PedidoOut], status_code=status.HTTP_200_OK)
def obtener_pedido(fecha: date, db: Session = Depends(get_db)):
    """
    Obtiene un pedido por alguna fecha dentro del rango indicado.
    """
    return PedidoService.Listar_pedidos_por_Fecha(db, fecha)

@router.post("/{id_pedido}/comprobante")
def generar_comprobante_pedido(id_pedido: int, db: Session = Depends(get_db)):
    try:
        doc = ComprobantePedidoService.generar_y_guardar(db, id_pedido=id_pedido)
        return {
            "id_documento": doc.id_documento,
            "nombre_archivo": doc.nombre_archivo,
            "tipo_archivo": doc.tipo_archivo,
            "url": doc.url_archivo,
            "fecha": doc.fecha_carga,
            "observacion": doc.observacion,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando comprobante: {e}")