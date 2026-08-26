from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .producto import Producto
    from .empresa import Empresa

from sqlalchemy import Integer, ForeignKey, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

#SCHEMA = "soderia"


class Stock(Base):
    __tablename__ = "stock"
    #__table_args__ = ({"schema": SCHEMA},)

    #PK
    id_stock: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    #FKs
    id_producto: Mapped[int] = mapped_column(
        ForeignKey("producto.id_producto"),
        nullable=False,
    )
    id_empresa: Mapped[int] = mapped_column(
        ForeignKey("empresa.id_empresa"),
        nullable=False,
    )

    #Campos
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))

    #Relaciones
    producto: Mapped["Producto"] = relationship(
        "Producto", back_populates="stocks"
    )
    empresa: Mapped["Empresa"] = relationship(
        "Empresa", back_populates="stocks"
    )

    def __repr__(self) -> str:
        return (
            f"<Stock id={self.id_stock} prod={self.id_producto} "
            f"emp={self.id_empresa} cant={self.cantidad}>"
        )
