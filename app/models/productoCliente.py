from __future__ import annotations
from datetime import date
from typing import TYPE_CHECKING, List


if TYPE_CHECKING:
    from .producto import Producto
    from .cliente import Cliente
    from .movimientoEnvaseCliente import MovimientoEnvaseCliente

from sqlalchemy import Integer, String, Date, ForeignKey, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

#SCHEMA = "soderia"


class ProductoCliente(Base):
    __tablename__ = "producto_cliente"
    #__table_args__ = ({"schema": SCHEMA},)

    #PKs
    legajo: Mapped[int] = mapped_column(
        ForeignKey("cliente.legajo", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    id_producto: Mapped[int] = mapped_column(
        ForeignKey("producto.id_producto"),
        primary_key=True,
        nullable=False,
    )

    #Campos
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    estado: Mapped[str | None] = mapped_column(String(30))
    fecha_entrega: Mapped[date | None] = mapped_column(Date)

    #Relaciones
    producto: Mapped["Producto"] = relationship(
        "Producto", back_populates="productos_cliente"
    )
    cliente: Mapped["Cliente"] = relationship(
        "Cliente",back_populates="productos"
    )
    movimientos_envase: Mapped[List["MovimientoEnvaseCliente"]] = relationship(
    "MovimientoEnvaseCliente",
    primaryjoin="and_(ProductoCliente.legajo == MovimientoEnvaseCliente.legajo, "
                "ProductoCliente.id_producto == MovimientoEnvaseCliente.id_producto)",
    foreign_keys="[MovimientoEnvaseCliente.legajo, MovimientoEnvaseCliente.id_producto]",
    viewonly=True,
)
    
    def __repr__(self) -> str:
        return (
            f"<ProductoCliente legajo={self.legajo} prod={self.id_producto} "
            f"cant={self.cantidad} estado={self.estado}>"
        )
