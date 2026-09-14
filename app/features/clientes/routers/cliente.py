from fastapi import APIRouter, Depends, status, Query
from app.core.security import get_current_user
from typing import List
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.features.clientes.schemas.cliente import (
    ClienteCreate,
    ClienteOut,
    ClienteUpdate,
    ClienteListOut,
)

from app.features.clientes.service import ClienteService
from app.features.clientes.schemas.cliente_detalle import ClienteDetalleOut, ClienteDetalleUpdate

from app.features.auditoria.schemas.historico import HistoricoOut
from app.features.pedidos.schemas.pedido import PedidoOutCorto
from app.features.clientes.schemas.producto_cliente import (
    ProductoClienteOut,
    ProductoClienteUpsert,
    ProductoClientePatch,
)


router = APIRouter(prefix="/clientes", tags=["Clientes"],dependencies=[Depends(get_current_user)],)


@router.post("/", response_model=ClienteDetalleOut, status_code=status.HTTP_201_CREATED)
def CrearCliente(payload: ClienteCreate, db: Session = Depends(get_db)):
    return ClienteService.crear_cliente(db, payload)

# Get masivo que trae todo lo relacionado al cliente mediante el legajo.
@router.get(
    "/{legajo}/detalle",
    response_model=ClienteDetalleOut,
    status_code=status.HTTP_200_OK,
)
def ObtenerDetalleCliente(legajo: int, db: Session = Depends(get_db)):
    return ClienteService.get_detalle_cliente(db, legajo)

@router.get("/", response_model=List[ClienteListOut], status_code=status.HTTP_200_OK)
def ListarClientes(db: Session = Depends(get_db)):
    return ClienteService.listar_clientes(db)

@router.put("/{legajo}", response_model=ClienteOut)
def ActualizarCliente(
    legajo: int, payload: ClienteUpdate, db: Session = Depends(get_db)
):
    return ClienteService.actualizar_cliente(db, legajo, payload)

#Nuevo put que actualiza todo lo relacionado al cliente.
@router.put("/{legajo}/detalle", response_model=ClienteDetalleOut)
def update_cliente_detalle(
    legajo: int,
    payload: ClienteDetalleUpdate,
    db: Session = Depends(get_db),
):
    return ClienteService.update_detalle_cliente(db, legajo, payload)

@router.delete("/{legajo}", status_code=status.HTTP_204_NO_CONTENT)
def BorrarCliente(legajo: int, db: Session = Depends(get_db)):
    ClienteService.eliminar_cliente(db, legajo)
    return None

@router.get(
    "/{legajo}/historicos",
    response_model=List[HistoricoOut],
    status_code=status.HTTP_200_OK,
)
def listar_historico_cliente(
    legajo: int,
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return ClienteService.listar_historico_cliente(db, legajo, limit)

@router.get(
    "/{legajo}/pedidos",
    response_model=List[PedidoOutCorto],
    status_code=status.HTTP_200_OK,
)
def listar_pedidos_cliente(
    legajo: int,
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return ClienteService.listar_pedidos_cliente(db, legajo, limit)

@router.get(
    "/{legajo}/productos",
    response_model=List[ProductoClienteOut],
    status_code=status.HTTP_200_OK,
)
def listar_productos_cliente(legajo: int, db: Session = Depends(get_db)):
    return ClienteService.listar_productos_cliente(db, legajo)

@router.put(
    "/{legajo}/productos/{id_producto}",
    response_model=ProductoClienteOut,
    status_code=status.HTTP_200_OK,
)
def upsert_producto_cliente(
    legajo: int,
    id_producto: int,
    payload: ProductoClienteUpsert,
    db: Session = Depends(get_db),
):
    """
    Crea o reemplaza por completo el producto del cliente (PUT idempotente).
    Si no existía la fila, la crea; si existía, sobreescribe todos los campos.
    """
    return ClienteService.upsert_producto_cliente(db, legajo, id_producto, payload)

@router.patch(
    "/{legajo}/productos/{id_producto}",
    response_model=ProductoClienteOut,
    status_code=status.HTTP_200_OK,
)
def actualizar_producto_cliente(
    legajo: int,
    id_producto: int,
    payload: ProductoClientePatch,
    db: Session = Depends(get_db),
):
    """
    Actualiza parcialmente el producto del cliente (PATCH).
    Solo modifica los campos enviados; la fila debe existir (404 si no).
    """
    return ClienteService.actualizar_producto_cliente(db, legajo, id_producto, payload)
