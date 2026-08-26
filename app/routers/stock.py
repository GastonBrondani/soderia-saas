from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.core.security import get_current_user
from sqlalchemy.orm import Session
from sqlalchemy import func, select, delete

from app.core.database import get_db
from app.models.stock import Stock
from app.schemas.stock import StockOut
from app.services.stockService import StockService
from app.models.producto import Producto
from app.schemas.stock import StockDetalleOut
from app.schemas.stockDetalle import StockDetalleOut


router = APIRouter(prefix="/stock", tags=["Stock"],dependencies=[Depends(get_current_user)],)

@router.get("/", response_model=list[StockOut])
def listar(
    db: Session = Depends(get_db),
    id_producto: int | None = Query(None),
    id_empresa: int | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    stmt = select(Stock)
    if id_producto is not None:
        stmt = stmt.where(Stock.id_producto == id_producto)
    if id_empresa is not None:
        stmt = stmt.where(Stock.id_empresa == id_empresa)
    rows = db.execute(stmt.order_by(Stock.id_stock).limit(limit).offset(offset)).scalars().all()
    return rows

@router.put("/set", response_model=StockOut, status_code=status.HTTP_200_OK)
def set_por_clave(id_producto: int, id_empresa: int, cantidad: int, db: Session = Depends(get_db)):
    """Setea el stock exacto por (id_producto, id_empresa). Upsert + validación no-negativo."""
    return StockService.set_stock(db, id_producto=id_producto, id_empresa=id_empresa, cantidad=cantidad)

@router.delete("/{id_stock}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar(id_stock: int, db: Session = Depends(get_db)):
    entity = db.get(Stock, id_stock)
    if not entity:
        raise HTTPException(status_code=404, detail="Stock no encontrado.")
    db.execute(delete(Stock).where(Stock.id_stock == id_stock))
    db.commit()
    
@router.get(
    "/detalle",
    response_model=list[StockDetalleOut],
)
def listar_detalle(
    db: Session = Depends(get_db),
    id_empresa: int = Query(...),
):
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

@router.get("/detalle")
def listar_detalle(
    db: Session = Depends(get_db),
    id_empresa: int = Query(...),
):
    """
    Devuelve TODOS los productos activos con su stock actual.
    Si no hay stock, devuelve cantidad = 0.
    """

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
        .where(Producto.estado == True)
        .order_by(Producto.nombre)
    )

    rows = db.execute(stmt).all()

    return [
        {
            "id_producto": r.id_producto,
            "nombre_producto": r.nombre,
            "litros": r.litros,
            "tipo_dispenser": r.tipo_dispenser,
            "cantidad": r.cantidad,
        }
        for r in rows
    ]
