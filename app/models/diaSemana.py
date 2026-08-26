from __future__ import annotations
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from .clienteDiaSemana import ClienteDiaSemana

from sqlalchemy import SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

#SCHEMA = "soderia"


class DiaSemana(Base):
    __tablename__ = "dia_semana"
    #__table_args__ = {"schema": SCHEMA}

    #PK
    id_dia: Mapped[int] = mapped_column(SmallInteger, primary_key=True)

    #Campos
    nombre_dia: Mapped[str] = mapped_column(String(15), nullable=False)

    #Relaciones
    clientes: Mapped[List["ClienteDiaSemana"]] = relationship(
        "ClienteDiaSemana", back_populates="dia_semana"
    )

    def __repr__(self) -> str:
        return f"<DiaSemana id={self.id_dia} nombre={self.nombre_dia}>"
