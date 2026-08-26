from __future__ import annotations
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import Integer, String, Text, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

if TYPE_CHECKING:
    from .empresa import Empresa
    from .comboProducto import ComboProducto
    from .listaPrecioCombo import ListaPrecioCombo
    from .pedidoProducto import PedidoProducto


class Combo(Base):
    __tablename__ = "combo"

    id_combo: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_empresa: Mapped[int] = mapped_column(ForeignKey("empresa.id_empresa", ondelete="CASCADE"), nullable=False)

    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    descripcion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    estado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")

    empresa: Mapped["Empresa"] = relationship("Empresa", back_populates="combos")
    combos_productos: Mapped[List["ComboProducto"]] = relationship(
        "ComboProducto", back_populates="combo", cascade="all, delete-orphan"
    )
    listas_precios: Mapped[List["ListaPrecioCombo"]] = relationship(
        "ListaPrecioCombo", back_populates="combo", cascade="all, delete-orphan"
    )
    pedidos_productos: Mapped[List["PedidoProducto"]] = relationship(
        "PedidoProducto", back_populates="combo"
    )
