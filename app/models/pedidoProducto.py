from __future__ import annotations
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .pedido import Pedido
    from .producto import Producto
    from .combo import Combo

from sqlalchemy import Integer, Numeric, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

#SCHEMA = "soderia"


class PedidoProducto(Base):
    __tablename__ = "pedido_producto"

    id_pedido_producto: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    id_pedido: Mapped[int] = mapped_column(ForeignKey("pedido.id_pedido"), nullable=False)

    id_producto: Mapped[Optional[int]] = mapped_column(ForeignKey("producto.id_producto"), nullable=True)
    id_combo: Mapped[Optional[int]] = mapped_column(ForeignKey("combo.id_combo"), nullable=True)

    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

    pedido: Mapped["Pedido"] = relationship("Pedido", back_populates="pedidos_productos")
    producto: Mapped[Optional["Producto"]] = relationship("Producto", back_populates="pedidos_productos")
    combo: Mapped[Optional["Combo"]] = relationship("Combo", back_populates="pedidos_productos")

    def __repr__(self) -> str:
        ref = f"producto={self.id_producto}" if self.id_producto is not None else f"combo={self.id_combo}"
        return f"<PedidoProducto id={self.id_pedido_producto} pedido={self.id_pedido} {ref} cant={self.cantidad} precio={self.precio_unitario}>"
