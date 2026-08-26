from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional, TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.clienteServicioPeriodo import ClienteServicioPeriodo

if TYPE_CHECKING:
    from app.models.empresa import Empresa
    from app.models.pedido import Pedido
    from app.models.repartoDia import RepartoDia
    from app.models.medioPago import MedioPago
    from app.models.cliente import Cliente

from app.models.clienteCuenta import ClienteCuenta  # si querés relationship tipada


class Pago(Base):
    __tablename__ = "pago"

    id_pago: Mapped[int] = mapped_column(Integer, primary_key=True)

    id_empresa: Mapped[int] = mapped_column(ForeignKey("empresa.id_empresa", ondelete="CASCADE"), nullable=False)
    legajo: Mapped[Optional[int]] = mapped_column(ForeignKey("cliente.legajo", ondelete="SET NULL"), nullable=True)

    # ✅ NUEVO
    id_cuenta: Mapped[Optional[int]] = mapped_column(
        ForeignKey("cliente_cuenta.id_cuenta", ondelete="SET NULL"),
        nullable=True,
    )

    id_pedido: Mapped[Optional[int]] = mapped_column(ForeignKey("pedido.id_pedido", ondelete="SET NULL"), nullable=True)
    id_repartodia: Mapped[Optional[int]] = mapped_column(ForeignKey("reparto_dia.id_repartodia", ondelete="SET NULL"), nullable=True)

    id_medio_pago: Mapped[int] = mapped_column(ForeignKey("medio_pago.id_medio_pago"), nullable=False)

    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    monto: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

    tipo_pago: Mapped[str] = mapped_column(String(30), nullable=False)
    observacion: Mapped[Optional[str]] = mapped_column(Text)
    id_cliente_servicio_periodo: Mapped[Optional[int]] = mapped_column(ForeignKey("cliente_servicio_periodo.id_periodo", ondelete="SET NULL"), nullable=True)

    # Offline sync: clave de idempotencia (única) y uuid generado por la tablet
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(80), nullable=True, unique=True, index=True)
    client_uuid: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)

    empresa: Mapped["Empresa"] = relationship("Empresa")
    cliente: Mapped[Optional["Cliente"]] = relationship("Cliente")
    pedido: Mapped[Optional["Pedido"]] = relationship("Pedido")
    reparto_dia: Mapped[Optional["RepartoDia"]] = relationship("RepartoDia")
    medio_pago: Mapped["MedioPago"] = relationship("MedioPago")

    # (opcional) relationship a cuenta
    cuenta: Mapped[Optional["ClienteCuenta"]] = relationship("ClienteCuenta")
    servicio_periodo: Mapped[Optional["ClienteServicioPeriodo"]] = relationship("ClienteServicioPeriodo")
