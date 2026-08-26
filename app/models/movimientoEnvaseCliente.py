from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .cliente import Cliente
    from .producto import Producto
    from .repartoDia import RepartoDia
    from .pedido import Pedido

from sqlalchemy import Integer, String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class MovimientoEnvaseCliente(Base):
    __tablename__ = "movimiento_envase_cliente"

    # PK
    id_movimiento: Mapped[int] = mapped_column(Integer, primary_key=True)

    # FKs
    legajo: Mapped[int] = mapped_column(
        ForeignKey("cliente.legajo", ondelete="CASCADE"),
        nullable=False,
    )
    id_producto: Mapped[int] = mapped_column(
        ForeignKey("producto.id_producto"),
        nullable=False,
    )
    id_repartodia: Mapped[Optional[int]] = mapped_column(
        ForeignKey("reparto_dia.id_repartodia"),
        nullable=True,
    )
    id_pedido: Mapped[Optional[int]] = mapped_column(
        ForeignKey("pedido.id_pedido"),
        nullable=True,
    )

    # Campos
    fecha: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )
    tipo: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    # ENTREGA | RETIRO | COBRO | PERDIDA
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)
    observacion: Mapped[Optional[str]] = mapped_column(Text)

    # Relaciones
    cliente: Mapped["Cliente"] = relationship(
        "Cliente", back_populates="movimientos_envase"
    )
    producto: Mapped["Producto"] = relationship(
        "Producto", back_populates="movimientos_envase_cliente"
    )
    reparto_dia: Mapped[Optional["RepartoDia"]] = relationship(
        "RepartoDia", back_populates="movimientos_envase"
    )
    pedido: Mapped[Optional["Pedido"]] = relationship(
        "Pedido", back_populates="movimientos_envase"
    )

    def __repr__(self) -> str:
        return (
            f"<MovimientoEnvaseCliente id={self.id_movimiento} "
            f"legajo={self.legajo} prod={self.id_producto} "
            f"tipo={self.tipo} cant={self.cantidad}>"
        )