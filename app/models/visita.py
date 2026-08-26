# app/models/visita.py
from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .cliente import Cliente 

from sqlalchemy import Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Visita(Base):
    __tablename__ = "visita"

    # PK autoincremental
    id_visita: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    # FK a cliente.legajo
    legajo: Mapped[int] = mapped_column(
        ForeignKey("cliente.legajo", ondelete="CASCADE"),
        nullable=False,
    )

    fecha: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    estado: Mapped[str] = mapped_column(String(50), nullable=False)

    # Offline sync: clave de idempotencia (única) y uuid generado por la tablet
    idempotency_key: Mapped[str | None] = mapped_column(
        String(80), nullable=True, unique=True, index=True
    )
    client_uuid: Mapped[str | None] = mapped_column(String(80), nullable=True)

    cliente: Mapped["Cliente"] = relationship("Cliente", back_populates="visitas")
