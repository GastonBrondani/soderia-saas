from __future__ import annotations
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .cliente import Cliente
    from .repartoDia import RepartoDia

from sqlalchemy import Integer, String, Text, Numeric, ForeignKey, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

#SCHEMA = "soderia"


class ClienteRepartoDia(Base):
    __tablename__ = "cliente_reparto_dia"
    #__table_args__ = ({"schema": SCHEMA},)

    #PK
    id_repartodia: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("reparto_dia.id_repartodia"),
        primary_key=True,
        nullable=False,
    )
    legajo: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("cliente.legajo", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )

    #Campos
    bidones_entregado: Mapped[Optional[int]] = mapped_column(
        Integer, server_default=text("0")
    )
    monto_abonado: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(14, 2), server_default=text("0")
    )
    estado_de_la_visita: Mapped[Optional[str]] = mapped_column(String(30))
    turno_de_la_visita: Mapped[Optional[str]] = mapped_column(String(20))
    observacion: Mapped[Optional[str]] = mapped_column(Text)

    #Relaciones
    reparto_dia: Mapped["RepartoDia"] = relationship(
        "RepartoDia",back_populates="reparto_clientes"
    )
    cliente: Mapped["Cliente"] = relationship(
        "Cliente",back_populates="repartos_dias"
    )

    def __repr__(self) -> str:
        return (
            f"<ClienteRepartoDia reparto={self.id_repartodia} "
            f"legajo={self.legajo} estado={self.estado_de_la_visita} "
            f"turno={self.turno_de_la_visita}>"
        )
