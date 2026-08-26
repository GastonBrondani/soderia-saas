from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from fastapi import HTTPException

from app.models.stock import Stock
from app.models.movimientoStock import MovimientoStock
from app.schemas.movimientoStock import TipoMovimiento


class StockService:
    @staticmethod
    def set_stock(db: Session, id_producto: int, id_empresa: int, cantidad: int) -> Stock:
        if cantidad < 0:
            raise HTTPException(status_code=400, detail="La cantidad no puede ser negativa.")
        stmt = select(Stock).where(
            Stock.id_producto == id_producto,
            Stock.id_empresa == id_empresa
        )
        entity = db.execute(stmt).scalar_one_or_none()
        if entity:
            entity.cantidad = cantidad
        else:
            entity = Stock(id_producto=id_producto, id_empresa=id_empresa, cantidad=cantidad)
            db.add(entity)
        db.commit()
        db.refresh(entity)
        return entity
    
    @staticmethod
    def _add_movimiento(
        db: Session,
        *,
        id_producto: int,       
        tipo: TipoMovimiento,
        cantidad: int,
        fecha: Optional[datetime] = None,
        observacion: Optional[str] = None,
        id_pedido: Optional[int] = None,
        id_recorrido: Optional[int] = None,
    ) -> MovimientoStock:
        mov = MovimientoStock(
            id_producto=id_producto,
            id_pedido=id_pedido,
            id_recorrido=id_recorrido,
            fecha=fecha or datetime.now(timezone.utc),
            tipo_movimiento=tipo.value,
            cantidad=cantidad,
            observacion=observacion,            
        )
        db.add(mov)
        return mov
    
    @staticmethod
    def ajustar_stock(
        db: Session,
        *,
        id_producto: int,
        id_empresa: int,
        delta: int,
        tipo: TipoMovimiento,
        fecha: Optional[datetime] = None,
        observacion: Optional[str] = None,
        id_pedido: Optional[int] = None,
        id_recorrido: Optional[int] = None,
    ) -> Stock:
        # Traer o crear el registro de stock
        stmt = select(Stock).where(Stock.id_producto == id_producto, Stock.id_empresa == id_empresa)
        entity = db.execute(stmt).scalar_one_or_none()
        if not entity:
            entity = Stock(id_producto=id_producto, id_empresa=id_empresa, cantidad=0)
            db.add(entity)
            db.flush()

        nueva = entity.cantidad + delta
        if nueva < 0:
            raise HTTPException(status_code=409, detail="El stock resultante no puede ser negativo.")

        entity.cantidad = nueva
        StockService._add_movimiento(
            db,
            id_producto=id_producto,            
            tipo=tipo,
            cantidad=abs(delta),
            fecha=fecha,
            observacion=observacion,
            id_pedido=id_pedido,
            id_recorrido=id_recorrido,
        )
        db.commit()
        db.refresh(entity)
        return entity