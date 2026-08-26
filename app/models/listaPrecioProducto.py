from __future__ import annotations
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .listaDePrecios import ListaDePrecios
    from .producto import Producto

from sqlalchemy import Integer, Numeric, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

#SCHEMA = "soderia"


class ListaPrecioProducto(Base):
    __tablename__ = "lista_precio_producto"
    #__table_args__ = ({"schema": SCHEMA},)

    #PKs
    id_lista: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("lista_de_precios.id_lista"),
        primary_key=True,
        nullable=False,
    )
    id_producto: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("producto.id_producto"),
        primary_key=True,
        nullable=False,
    )

    #Campos
    precio: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

    #Relaciones
    lista: Mapped["ListaDePrecios"] = relationship(
        "ListaDePrecios",back_populates="lista_productos"
    )
    producto: Mapped["Producto"] = relationship(
        "Producto",back_populates="listas_precios"
    )

    def __repr__(self) -> str:
        return f"<ListaPrecioProducto lista={self.id_lista} producto={self.id_producto} precio={self.precio}>"
