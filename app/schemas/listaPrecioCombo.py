from __future__ import annotations

from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class LPCUpsert(BaseModel):
    """
    Body para upsert de precio de combo en una lista.
    Nota: id_lista y id_combo los vamos a setear desde el path.
    """
    id_lista: Optional[int] = None
    id_combo: Optional[int] = None
    precio: Decimal = Field(gt=0)


class LPCOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_lista: int
    id_combo: int
    precio: Decimal


class LPCBasicOut(BaseModel):
    """
    Igual que LPPBasicOut, pero para combos.
    Si include_combo=True en el service, llenamos combo_nombre para UI.
    """
    id_lista: int
    id_combo: int
    precio: Decimal
    combo_nombre: Optional[str] = None
