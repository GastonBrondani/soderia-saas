from fastapi import APIRouter, Depends, Query, status
from app.core.security import get_current_user
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.database import get_db
from app.models.movimientoStock import MovimientoStock
from app.schemas.movimientoStock import MovimientoCreate, MovimientoOut
from app.services.stockService import StockService
from app.schemas.enumsStock import TipoMovimiento

router = APIRouter(prefix="/movimientos-stock", tags=["Movimiento de Stock"],dependencies=[Depends(get_current_user)],)

@router.post("/", response_model=list[MovimientoOut], status_code=status.HTTP_201_CREATED)
def crear(payload: MovimientoCreate, db: Session = Depends(get_db)):
    """
    Crea movimientos y ajusta stock:
      - ingreso/egreso/ajuste: ajusta en empresa indicada
    Devuelve los últimos movimientos del producto para referencia.
    """
    # delta positivo suma, delta negativo resta
    delta = payload.cantidad if payload.tipo_movimiento in (TipoMovimiento.ingreso, TipoMovimiento.ajuste) else -payload.cantidad

    StockService.ajustar_stock(
        db,
        id_producto=payload.id_producto,
        id_empresa=1,  
        delta=delta,
        tipo=payload.tipo_movimiento,
        fecha=payload.fecha,
        observacion=payload.observacion,
        id_pedido=payload.id_pedido,
        id_recorrido=payload.id_recorrido,
    )

    rows = db.execute(
        select(MovimientoStock)
        .where(MovimientoStock.id_producto == payload.id_producto)
        .order_by(MovimientoStock.id_movimiento.desc())
        .limit(2)
    ).scalars().all()
    return rows

@router.get("/", response_model=list[MovimientoOut])
def listar(
    db: Session = Depends(get_db),
    id_producto: int | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
):
    stmt = select(MovimientoStock)
    if id_producto:
        stmt = stmt.where(MovimientoStock.id_producto == id_producto)

    return (
        db.execute(
            stmt.order_by(MovimientoStock.fecha.desc()).limit(limit)
        )
        .scalars()
        .all()
    )

