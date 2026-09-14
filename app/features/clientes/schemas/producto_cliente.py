from datetime import date
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


class ProductoClienteUpsert(BaseModel):
    """Body para PUT: setea (crea o reemplaza) el producto del cliente por completo."""
    cantidad: int = Field(ge=0)
    estado: Optional[str] = None
    fecha_entrega: Optional[date] = None


class ProductoClientePatch(BaseModel):
    """Body para PATCH: actualiza solo los campos enviados (el resto queda igual)."""
    cantidad: Optional[int] = Field(default=None, ge=0)
    estado: Optional[str] = None
    fecha_entrega: Optional[date] = None


class ProductoClienteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_producto: int
    nombre: str
    cantidad: int
    estado: Optional[str] = None
    fecha_entrega: Optional[date] = None

    @model_validator(mode="before")
    @classmethod
    def _flatten(cls, data):
        if not isinstance(data, dict) and hasattr(data, "producto"):
            return {
                "id_producto": data.id_producto,
                "nombre": data.producto.nombre if data.producto else "",
                "cantidad": data.cantidad,
                "estado": data.estado,
                "fecha_entrega": data.fecha_entrega,
            }
        return data
