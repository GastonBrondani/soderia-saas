from __future__ import annotations
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .cliente import Cliente

from sqlalchemy import Integer, String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

#SCHEMA = "soderia"


class DireccionCliente(Base):
    __tablename__ = "direccion_cliente"
    #__table_args__ = ({"schema": SCHEMA},)

    #PK
    id_direccion: Mapped[int] = mapped_column(Integer, primary_key=True)

    #FK
    legajo: Mapped[int] = mapped_column(
        ForeignKey("cliente.legajo", ondelete="CASCADE"),
        nullable=False,
    )

    #Campos
    localidad: Mapped[Optional[str]] = mapped_column(String(100))
    direccion: Mapped[Optional[str]] = mapped_column(String(200))
    zona: Mapped[Optional[str]] = mapped_column(String(100))
    entre_calle1: Mapped[Optional[str]] = mapped_column(String(100))
    entre_calle2: Mapped[Optional[str]] = mapped_column(String(100))
    observacion: Mapped[Optional[str]] = mapped_column(Text)
    tipo: Mapped[Optional[str]] = mapped_column(String(50))
    latitud_longitud: Mapped[Optional[str]] = mapped_column(String(100))

    #Relaciones
    cliente: Mapped["Cliente"] = relationship(
        "Cliente",back_populates="direcciones"
    )

    def __repr__(self) -> str:
        return f"<DireccionCliente id={self.id_direccion} legajo={self.legajo} direccion={self.direccion}>"
