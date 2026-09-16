from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional, TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.features.catalogo.servicios.models.cliente_servicio_periodo import ClienteServicioPeriodo

if TYPE_CHECKING:
    from app.features.empresas.models.empresa import Empresa
    from app.features.pedidos.models.pedido import Pedido
    from app.features.repartos.repartos_dia.models.reparto_dia import RepartoDia
    from app.features.maestros.models.medio_pago import MedioPago
    from app.features.clientes.models.cliente import Cliente

from app.features.clientes.models.cliente_cuenta import ClienteCuenta  # si querés relationship tipada


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

    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
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
