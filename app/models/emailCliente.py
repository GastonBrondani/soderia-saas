from __future__ import annotations
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .cliente import Cliente

from sqlalchemy import Integer, String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

#SCHEMA = "soderia"


class MailCliente(Base):
    __tablename__ = "mail_cliente"
    #__table_args__ = ({"schema": SCHEMA},)

    #PK
    id_mail: Mapped[int] = mapped_column(Integer, primary_key=True)

    #FK
    legajo: Mapped[int] = mapped_column(
        ForeignKey("cliente.legajo", ondelete="CASCADE"),
        nullable=False,
    )

    #Campos
    mail: Mapped[Optional[str]] = mapped_column(String(150))
    estado: Mapped[Optional[str]] = mapped_column(String(20))
    observacion: Mapped[Optional[str]] = mapped_column(Text)

    #Relaciones
    cliente: Mapped["Cliente"] = relationship(
        "Cliente",back_populates="emails"
    )

    def __repr__(self) -> str:
        return f"<MailCliente id={self.id_mail} legajo={self.legajo} mail={self.mail}>"
