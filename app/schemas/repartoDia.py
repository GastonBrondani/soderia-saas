from __future__ import annotations
from datetime import date
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

class RepartoDiaBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_usuario: int
    id_empresa: int = 1
    fecha: date
    observacion: Optional[str] = None

    @field_validator("observacion")
    @classmethod
    def trim_obs(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if isinstance(v, str) else v

class RepartoDiaCreate(RepartoDiaBase):    
    pass

class RepartoDiaUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id_usuario: Optional[int] = None
    id_empresa: Optional[int] = None
    fecha: Optional[date] = None
    observacion: Optional[str] = None

    @field_validator("observacion")
    @classmethod
    def trim_obs(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if isinstance(v, str) else v

class RepartoDiaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id_repartodia: int
    id_usuario: int
    id_empresa: int
    fecha: date
    total_recaudado: Decimal = Field(default=Decimal("0.00"))
    total_efectivo: Decimal = Field(default=Decimal("0.00"))
    total_virtual: Decimal = Field(default=Decimal("0.00"))
    observacion: Optional[str] = None

class RegistrarCobroIn(BaseModel):
    """
    Payload para sumar recaudación al reparto (operación atómica).
    Dejá en 0 el que no corresponda.
    """
    efectivo: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    virtual: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    
