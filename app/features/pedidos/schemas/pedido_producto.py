from __future__ import annotations
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator

class PedidoItemIn(BaseModel):
    id_producto: int | None = None
    id_combo: int | None = None
    cantidad: int = Field(gt=0)
    precio_unitario: Decimal

    @model_validator(mode="after")
    def validar_item(self):
        if not self.id_producto and not self.id_combo:
            raise ValueError("Debe venir id_producto o id_combo")

        if self.id_producto and self.id_combo:
            raise ValueError("No puede venir id_producto e id_combo juntos")

        return self

class PedidoItemsBulkIn(BaseModel):
    items: List[PedidoItemIn]

class PedidoItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id_producto: int
    cantidad: int
    precio_unitario: Decimal
