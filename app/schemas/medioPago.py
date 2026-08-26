# app/schemas/medio_pago.py
from pydantic import BaseModel, ConfigDict, field_validator

class MedioPagoCreate(BaseModel):
    nombre: str

    @field_validator("nombre")
    @classmethod
    def trim_and_require(cls, v: str) -> str:
        v2 = (v or "").strip()
        if not v2:
            raise ValueError("El nombre es obligatorio")
        return v2

class MedioPagoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id_medio_pago: int
    nombre: str
