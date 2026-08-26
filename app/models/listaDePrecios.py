from __future__ import annotations
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from .listaPrecioProducto import ListaPrecioProducto
    from .listaPrecioCombo import ListaPrecioCombo
    from .listaPrecioServicio import ListaPrecioServicio

from sqlalchemy import Integer, String, DateTime, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

# SCHEMA = "soderia"


class ListaDePrecios(Base):
    __tablename__ = "lista_de_precios"
    # __table_args__ = ({"schema": SCHEMA},)

    # PK
    id_lista: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Campos
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    fecha_creacion: Mapped["DateTime"] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        server_default=text("now()"),
    )
    estado: Mapped[str] = mapped_column(String(20), nullable=False)

    # Relaciones
    lista_productos: Mapped[List["ListaPrecioProducto"]] = relationship(
        "ListaPrecioProducto", back_populates="lista"
    )
    listas_precios_combos: Mapped[List["ListaPrecioCombo"]] = relationship(
        "ListaPrecioCombo", back_populates="lista"
    )
    listas_precios_servicios: Mapped[List["ListaPrecioServicio"]] = relationship(
        "ListaPrecioServicio", back_populates="lista"
    )

    def __repr__(self) -> str:
        return f"<ListaDePrecios id={self.id_lista} nombre={self.nombre} estado={self.estado}>"
