from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:    
    from .tipoEvento import TipoEvento
    from .cliente import Cliente

from sqlalchemy import Integer, Text, DateTime, ForeignKey, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from sqlalchemy.dialects.postgresql import JSONB

#SCHEMA = "soderia"


class Historico(Base):
    __tablename__ = "historico"
    #__table_args__ = ({"schema": SCHEMA},)

    #PK
    id_historico: Mapped[int] = mapped_column(Integer, primary_key=True)

    #FKs
    legajo: Mapped[int] = mapped_column(
        ForeignKey("cliente.legajo", ondelete="CASCADE"), 
        nullable=False,
    )
    id_evento: Mapped[int] = mapped_column(
        ForeignKey("tipo_evento.id_evento"),
        nullable=False,
    )

    #Campos
    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        server_default=text("now()"),
    )
    observacion: Mapped[Optional[str]] = mapped_column(Text)

    datos: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    #Relaciones
    cliente: Mapped["Cliente"] = relationship(
        "Cliente", back_populates="historicos"
    )
    
    tipo_evento: Mapped["TipoEvento"] = relationship(
        "TipoEvento", back_populates="historicos"
    )

    def __repr__(self) -> str:
        return f"<Historico id={self.id_historico} legajo={self.legajo} evento={self.id_evento} fecha={self.fecha}>"
