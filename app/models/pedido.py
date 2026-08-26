from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional, List

if TYPE_CHECKING:
    from .cliente import Cliente
    from .empresa import Empresa
    from .medioPago import MedioPago
    from .movimientoStock import MovimientoStock
    from .pedidoProducto import PedidoProducto
    from .repartoDia import RepartoDia
    from .movimientoEnvaseCliente import MovimientoEnvaseCliente
    

from sqlalchemy import Integer, String, Text, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

# Longitud usada para las claves de idempotencia/UUID del cliente (offline sync)
IDEMPOTENCY_KEY_LEN = 80

#SCHEMA = "soderia"


class Pedido(Base):
    __tablename__ = "pedido"
    #__table_args__ = ({"schema": SCHEMA},)

    #PK
    id_pedido: Mapped[int] = mapped_column(Integer, primary_key=True)

    #FKs
    legajo: Mapped[int] = mapped_column(
        ForeignKey("cliente.legajo", ondelete="CASCADE"),
        nullable=False,
    )
    id_medio_pago: Mapped[int] = mapped_column(
        ForeignKey("medio_pago.id_medio_pago"),
        nullable=False,
    )
    id_empresa: Mapped[int] = mapped_column(
        ForeignKey("empresa.id_empresa"),
        nullable=False,
    )
    id_repartodia: Mapped[Optional[int]] = mapped_column(
        ForeignKey("reparto_dia.id_repartodia"),
        nullable=True,
    )
    id_cuenta: Mapped[int | None] = mapped_column(
        ForeignKey("cliente_cuenta.id_cuenta"),
        nullable=True,
    )


    #Campos
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    monto_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    monto_abonado: Mapped[Decimal] = mapped_column(Numeric(14, 2), server_default="0")
    estado: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="pendiente",
        server_default="pendiente",
    )
    observacion: Mapped[Optional[str]] = mapped_column(Text)

    # Offline sync: clave de idempotencia (única) y uuid generado por la tablet
    idempotency_key: Mapped[Optional[str]] = mapped_column(
        String(IDEMPOTENCY_KEY_LEN), nullable=True, unique=True, index=True
    )
    client_uuid: Mapped[Optional[str]] = mapped_column(
        String(IDEMPOTENCY_KEY_LEN), nullable=True
    )

    #Relaciones
    cliente: Mapped["Cliente"] = relationship(
        "Cliente", back_populates="pedidos"
        )
    medio_pago: Mapped["MedioPago"] = relationship(
        "MedioPago", back_populates="pedidos"
    )

    
    empresa: Mapped["Empresa"] = relationship(
        "Empresa", back_populates="pedidos"
    )

    movimientos_stock: Mapped[List["MovimientoStock"]] = relationship(
        "MovimientoStock", back_populates="pedido"
    )
    pedidos_productos: Mapped[List["PedidoProducto"]] = relationship(
        "PedidoProducto", back_populates="pedido"
    )
    reparto_dia: Mapped[Optional["RepartoDia"]] = relationship(
    "RepartoDia", back_populates="pedidos"
    )
    movimientos_envase: Mapped[List["MovimientoEnvaseCliente"]] = relationship(
    "MovimientoEnvaseCliente", back_populates="pedido"
    )

    def __repr__(self) -> str:
        return (
            f"<Pedido id={self.id_pedido} legajo={self.legajo} "
            f"total={self.monto_total} abonado={self.monto_abonado} estado={self.estado}>"
        )
