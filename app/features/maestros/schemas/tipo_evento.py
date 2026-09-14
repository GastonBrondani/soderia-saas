from __future__ import annotations
from pydantic import BaseModel, ConfigDict


class TipoEventoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_evento: int
    nombre: str
