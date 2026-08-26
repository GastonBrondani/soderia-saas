from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional


# --------- Bases / I-O simples ---------
class LPSBase(BaseModel):
    precio: Decimal = Field(..., ge=0)


class LPSCreate(LPSBase):
    id_lista: int
    id_cliente_servicio: int


class LPSUpsert(LPSCreate):
    """Idéntico a create para un upsert lógico en router."""

    id_lista: Optional[int] = None
    id_cliente_servicio: Optional[int] = None


class LPSOut(LPSBase):
    model_config = ConfigDict(from_attributes=True)
    id_lista: int
    id_cliente_servicio: int


# Mínimo para incrustar dentro de "servicio con precios" o "lista con precios".
class LPSBasicOut(LPSBase):
    model_config = ConfigDict(from_attributes=True)
    id_lista: int
    id_cliente_servicio: int
    # Opcional: nombre del servicio si quisiéramos mostrar "Alquiler Dispenser"
    servicio_tipo: Optional[str] = None
