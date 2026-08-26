from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING, Optional, List

if TYPE_CHECKING:
    from .producto import Producto
    from .recorrido import Recorrido
    from .pedido import Pedido

from sqlalchemy import Integer, String, Text, DateTime, ForeignKey, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

#SCHEMA = "soderia"


class MovimientoStock(Base):
    __tablename__ = "movimiento_stock"
    #__table_args__ = {"schema": SCHEMA}

    #PK
    id_movimiento: Mapped[int] = mapped_column(Integer, primary_key=True)

    #FKs
    id_producto: Mapped[int] = mapped_column(
        ForeignKey("producto.id_producto"),
        nullable=False,
    )
    id_recorrido: Mapped[Optional[int]] = mapped_column(
        ForeignKey("recorrido.id_recorrido"),
        nullable=True,
    )
    id_pedido: Mapped[Optional[int]] = mapped_column(
        ForeignKey("pedido.id_pedido"),
        nullable=True,
    )

    #Campos
    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        server_default=text("now()"),
    )
    tipo_movimiento: Mapped[Optional[str]] = mapped_column(String(30))
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)
    observacion: Mapped[Optional[str]] = mapped_column(Text)

    #Relaciones    
    producto: Mapped["Producto"] = relationship(
        "Producto", back_populates="movimientos_stock"
    )
    recorrido: Mapped["Recorrido"] = relationship(
        "Recorrido", back_populates="movimientos_stock"
    )
    pedido: Mapped[List["Pedido"]] = relationship(
        "Pedido", back_populates="movimientos_stock"
    )

    def __repr__(self) -> str:
        return (
            f"<MovimientoStock id={self.id_movimiento} prod={self.id_producto} "
            f"tipo={self.tipo_movimiento} cant={self.cantidad}>"
        )
