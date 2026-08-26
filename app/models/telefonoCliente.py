from __future__ import annotations
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .cliente import Cliente

from sqlalchemy import Integer, String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

#SCHEMA = "soderia"


class TelefonoCliente(Base):
    __tablename__ = "telefono_cliente"
    #__table_args__ = ({"schema": SCHEMA},)

    #PK
    id_telefono: Mapped[int] = mapped_column(Integer, primary_key=True)

    #FK
    legajo: Mapped[int] = mapped_column(
        ForeignKey("cliente.legajo", ondelete="CASCADE"),
        nullable=False,
    )

    #Campos
    nro_telefono: Mapped[Optional[str]] = mapped_column(String(50))
    estado: Mapped[Optional[str]] = mapped_column(String(20))
    observacion: Mapped[Optional[str]] = mapped_column(Text)

    #Relación
    cliente: Mapped["Cliente"] = relationship(
        "Cliente",back_populates="telefonos"
    )

    def __repr__(self) -> str:
        return f"<TelefonoCliente id={self.id_telefono} legajo={self.legajo} nro={self.nro_telefono}>"
