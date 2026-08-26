from __future__ import annotations
from typing import TYPE_CHECKING
from sqlalchemy import Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

if TYPE_CHECKING:
    from .combo import Combo
    from .producto import Producto


class ComboProducto(Base):
    __tablename__ = "combo_producto"

    id_combo: Mapped[int] = mapped_column(ForeignKey("combo.id_combo", ondelete="CASCADE"), primary_key=True)
    id_producto: Mapped[int] = mapped_column(ForeignKey("producto.id_producto", ondelete="RESTRICT"), primary_key=True)

    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)

    combo: Mapped["Combo"] = relationship("Combo", back_populates="combos_productos")
    producto: Mapped["Producto"] = relationship("Producto", back_populates="combos_productos")
