from __future__ import annotations
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from .cliente import Cliente
    from .empleado import Empleado

from sqlalchemy import String, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

#SCHEMA = "soderia"


class Persona(Base):
    __tablename__ = "persona"
    #__table_args__ = {"schema": SCHEMA}

    #PK
    dni: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    #Campos
    apellido: Mapped[str] = mapped_column(String(100), nullable=False)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    

    #Relaciones
    clientes: Mapped[List["Cliente"]] = relationship(
        "Cliente",back_populates="persona",passive_deletes=True,
    )
    
    empleado: Mapped["Empleado"] = relationship(
        "Empleado",back_populates="persona"
    )

    def __repr__(self) -> str:
        return f"<Persona dni={self.dni} nombre={self.nombre} apellido={self.apellido}>"
