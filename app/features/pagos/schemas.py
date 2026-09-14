from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class PagoCreate(BaseModel):
    id_empresa: int
    id_medio_pago: int
    fecha: datetime
    monto: Decimal = Field(gt=0)

    tipo_pago: str
    observacion: Optional[str] = None

    legajo: Optional[int] = None
    id_pedido: Optional[int] = None
    id_repartodia: Optional[int] = None

    # Offline sync: idempotencia. La tablet manda estos valores al reintentar.
    idempotency_key: Optional[str] = None
    client_uuid: Optional[str] = None


class PagoOut(BaseModel):
    id_pago: int
    id_empresa: int
    id_medio_pago: int
    fecha: datetime
    monto: Decimal
    tipo_pago: str
    observacion: Optional[str]

    legajo: Optional[int]
    id_pedido: Optional[int]
    id_repartodia: Optional[int]

    idempotency_key: Optional[str] = None
    client_uuid: Optional[str] = None

    class Config:
        from_attributes = True

class PagoLibreIn(BaseModel):
    legajo: int
    id_cuenta: int
    id_empresa: int
    id_medio_pago: int
    monto: Decimal = Field(gt=0)
    observacion: Optional[str] = None
    id_repartodia: Optional[int] = None


class PagoLibreOut(BaseModel):
    id_pago: int
    comprobante_url: str


class MotivoEgreso(str, Enum):
    COMBUSTIBLE = "COMBUSTIBLE"
    SUELDOS = "SUELDOS"
    INSUMOS = "INSUMOS"
    OTRO = "OTRO"


class PagoEgresoCreate(BaseModel):
    id_medio_pago: int
    monto: Decimal = Field(gt=0)
    motivo: MotivoEgreso
    observacion: Optional[str] = None
    fecha: Optional[datetime] = None


class PagoIngresoCreate(BaseModel):
    id_medio_pago: int
    monto: Decimal = Field(gt=0)
    observacion: Optional[str] = None
    fecha: Optional[datetime] = None
