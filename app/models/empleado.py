from __future__ import annotations
from datetime import date
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .persona import Persona
    from .recorrido import Recorrido
    from .usuario import Usuario
    from .empresa import Empresa

from sqlalchemy import Integer, BigInteger, Date,ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

#SCHEMA = "soderia"


class Empleado(Base):
    __tablename__ = "empleado"
    #__table_args__ = ({"schema": SCHEMA},)

    #PK
    legajo: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    #Fk
    dni: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("persona.dni"),
        nullable=False,                                  
    )
    id_empresa: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("empresa.id_empresa"),  
        nullable=False,
        index=True,
    )

    #Campos
          
    fecha_ingreso: Mapped[date | None] = mapped_column(Date)

    #Relaciones
    persona: Mapped["Persona"] = relationship(
        "Persona",back_populates="empleado"
    )
    
    recorrido: Mapped["Recorrido"] = relationship(
        "Recorrido", back_populates="empleado"
    )
    
    usuarios: Mapped["Usuario"] = relationship(
        "Usuario",back_populates="empleado"
    )

    empresa: Mapped["Empresa"] = relationship("Empresa", back_populates="empleados")

    def __repr__(self) -> str:
        return f"<Empleado legajo={self.legajo} dni={self.dni} ingreso={self.fecha_ingreso}>"
