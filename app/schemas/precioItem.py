from __future__ import annotations

from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field


TipoItemPrecio = Literal["producto", "combo", "servicio"]


class PrecioItemUpsert(BaseModel):
    precio: Decimal = Field(gt=0)


class PrecioItemOut(BaseModel):
    tipo: TipoItemPrecio
    id_lista: int
    id_item: int
    nombre: str
    precio: float | None
    estado: bool | None = None
