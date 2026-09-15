from fastapi import APIRouter, Depends, Query, status
from app.core.security import get_current_user
from sqlalchemy.orm import Session
from sqlalchemy import func, select, delete

from app.core.database import get_db
from app.core.exceptions import NotFound
from app.features.empresas.service import EmpresaService
from app.features.inventario.stock.models.stock import Stock
from app.features.inventario.stock.schemas.stock import StockOut
from app.features.inventario.stock.service import StockService
from app.features.catalogo.productos.models.producto import Producto
from app.features.inventario.stock.schemas.stock_detalle import StockDetalleOut


router = APIRouter(prefix="/stock", tags=["Stock"],dependencies=[Depends(get_current_user)],)

@router.get("/", response_model=list[StockOut])
def listar(
    db: Session = Depends(get_db),
    id_producto: int | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    stmt = select(Stock)
    if id_producto is not None:
        stmt = stmt.where(Stock.id_producto == id_producto)
    rows = db.execute(stmt.order_by(Stock.id_stock).limit(limit).offset(offset)).scalars().all()
    return rows

@router.put("/set", response_model=StockOut, status_code=status.HTTP_200_OK)
def set_por_clave(id_producto: int, cantidad: int, db: Session = Depends(get_db)):
    """Setea el stock exacto por (id_producto, id_empresa). Upsert + validación no-negativo."""
    id_empresa = EmpresaService.get_id_empresa_actual(db)
    return StockService.set_stock(db, id_producto=id_producto, id_empresa=id_empresa, cantidad=cantidad)

@router.delete("/{id_stock}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar(id_stock: int, db: Session = Depends(get_db)):
    entity = db.get(Stock, id_stock)
    if not entity:
        raise NotFound("Stock no encontrado.")
    db.execute(delete(Stock).where(Stock.id_stock == id_stock))
    db.commit()
    
@router.get(
    "/detalle",
    response_model=list[StockDetalleOut],
)
def listar_detalle(
    db: Session = Depends(get_db),
):
    id_empresa = EmpresaService.get_id_empresa_actual(db)
    stmt = (
        select(
            Producto.id_producto,
            Producto.nombre,
            Producto.litros,
            Producto.tipo_dispenser,
            func.coalesce(Stock.cantidad, 0).label("cantidad"),
        )
        .outerjoin(
            Stock,
            (Stock.id_producto == Producto.id_producto)
            & (Stock.id_empresa == id_empresa),
        )
        .where(
            (Producto.estado == 'true') | (Producto.estado.is_(None))
        )
        .order_by(Producto.nombre)
    )

    rows = db.execute(stmt).all()

    return [
        StockDetalleOut(
            id_producto=r.id_producto,
            nombre_producto=r.nombre,
            cantidad=r.cantidad,
            litros=r.litros,
            tipo_dispenser=r.tipo_dispenser,
        )
        for r in rows
    ]
