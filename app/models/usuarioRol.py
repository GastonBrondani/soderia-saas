from __future__ import annotations
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from .usuario import Usuario
    from .rol import Rol

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

#SCHEMA = "soderia"


class UsuarioRol(Base):
    __tablename__ = "usuario_rol"
    #__table_args__ = ({"schema": SCHEMA},)

    #PKs
    id_usuario: Mapped[int] = mapped_column(
        ForeignKey("usuario.id_usuario"),
        primary_key=True,
        nullable=False,
    )
    id_rol: Mapped[int] = mapped_column(
        ForeignKey("rol.id_rol"),
        primary_key=True,
        nullable=False,
    )

    #Relaciones
    usuario: Mapped["Usuario"] = relationship(
        "Usuario", back_populates="usuario_roles"
    )
    rol: Mapped[List["Rol"]] = relationship(
        "Rol", back_populates="usuarios_rol"
    )

    def __repr__(self) -> str:
        return f"<UsuarioRol usuario={self.id_usuario} rol={self.id_rol}>"
