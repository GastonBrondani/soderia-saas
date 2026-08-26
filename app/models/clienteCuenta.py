from __future__ import annotations
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .cliente import Cliente

from sqlalchemy import Integer, String, Numeric, ForeignKey, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

#SCHEMA = "soderia"


class ClienteCuenta(Base):
    __tablename__ = "cliente_cuenta"
    #__table_args__ = ({"schema": SCHEMA},)

    #PK
    id_cuenta: Mapped[int] = mapped_column(Integer, primary_key=True)

    #FK
    legajo: Mapped[int] = mapped_column(
        ForeignKey("cliente.legajo", ondelete="CASCADE"),
        nullable=False,
    )

    #Campos
    saldo: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), server_default=text("0")
    )
    deuda: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), server_default=text("0")
    )
    estado: Mapped[str | None] = mapped_column(String(30))
    tipo_de_cuenta: Mapped[str | None] = mapped_column(String(50))
    numero_bidones: Mapped[int | None] = mapped_column(Integer, server_default=text("0"))

    #Relación
    cliente: Mapped["Cliente"] = relationship(
        "Cliente", back_populates="cuentas"
    )

    def __repr__(self) -> str:
        return (
            f"<ClienteCuenta id={self.id_cuenta} legajo={self.legajo} "
            f"saldo={self.saldo} deuda={self.deuda}>"
        )
