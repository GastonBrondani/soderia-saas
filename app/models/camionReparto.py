from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .empresa import Empresa
    from .recorrido import Recorrido

from sqlalchemy import String, Boolean, ForeignKey, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

#SCHEMA = "soderia"


class CamionReparto(Base):
    __tablename__ = "camion_reparto"
    #__table_args__ = ({"schema": SCHEMA},)

    #PK
    patente: Mapped[str] = mapped_column(String(20), primary_key=True)

    #FK
    id_empresa: Mapped[int] = mapped_column(
        ForeignKey("empresa.id_empresa"),
        nullable=False,
    )

    #Campos
    activo: Mapped[bool | None] = mapped_column(Boolean, server_default=text("true"))

    #Relaciones
    empresa: Mapped["Empresa"] = relationship(
        "Empresa",
        back_populates="camiones_reparto",
        
    )
    
    recorridos: Mapped["Recorrido"] = relationship(
        "Recorrido",
        back_populates="camion_reparto",
        
        
    )

    def __repr__(self) -> str:
        return f"<CamionReparto patente={self.patente} empresa={self.id_empresa} activo={self.activo}>"
