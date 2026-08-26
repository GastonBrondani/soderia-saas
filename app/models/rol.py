from __future__ import annotations
from typing import TYPE_CHECKING,Optional

if TYPE_CHECKING:
    from .usuarioRol import UsuarioRol

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

#SCHEMA = "soderia"


class Rol(Base):
    __tablename__ = "rol"
    #__table_args__ = ({"schema": SCHEMA},)

    #PK
    id_rol: Mapped[int] = mapped_column(Integer, primary_key=True)

    #Campos
    nombre: Mapped[str] = mapped_column(String(50), nullable=False)
    descripcion: Mapped[Optional[str]] = mapped_column(Text)

    #Relaciones
    usuarios_rol: Mapped["UsuarioRol"] = relationship(
        "UsuarioRol", back_populates="rol"
    )

    def __repr__(self) -> str:
        return f"<Rol id={self.id_rol} nombre={self.nombre}>"
