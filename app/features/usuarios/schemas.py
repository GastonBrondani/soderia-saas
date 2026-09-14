from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

# ⚠️ IMPORTANTE:
# - En tu modelo SQLAlchemy, usá el atributo Python "contrasena" y mapealo a la columna "contraseña":
#   contrasena = mapped_column("contraseña", String(255), nullable=False)
# - En estos schemas, exponemos "contraseña" en JSON con alias, pero trabajamos "contrasena" en Python.


class UsuarioBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    nombre_usuario: str = Field(min_length=3, max_length=100)
    legajo_empleado: Optional[int] = None
    legajo_cliente: Optional[int] = None

    @field_validator("nombre_usuario")
    @classmethod
    def _trim_nombre(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("El nombre de usuario no puede quedar vacío.")
        return v


class UsuarioCreate(UsuarioBase):
    # alias JSON "contraseña" -> atributo Python "contrasena"
    contrasena: str = Field(alias="contraseña", min_length=8, max_length=255)

    @field_validator("contrasena")
    @classmethod
    def _password_rules(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres.")
        return v


class UsuarioUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    nombre_usuario: Optional[str] = Field(default=None, min_length=3, max_length=100)
    # password opcional en update; mismo alias JSON
    contrasena: Optional[str] = Field(default=None, alias="contraseña", min_length=8, max_length=255)
    legajo_empleado: Optional[int] = None
    legajo_cliente: Optional[int] = None

    @field_validator("nombre_usuario")
    @classmethod
    def _trim_nombre(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if isinstance(v, str) else v

    @field_validator("contrasena")
    @classmethod
    def _password_rules(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        if len(v) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres.")
        return v


class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_usuario: int
    nombre_usuario: str
    legajo_empleado: Optional[int] = None
    legajo_cliente: Optional[int] = None
    # ⚠️ NO exponemos contraseña en la respuesta
