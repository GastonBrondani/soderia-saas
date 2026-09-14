from datetime import date
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional

class ServicioMontoUpdate(BaseModel):
    monto_mensual: Decimal = Field(..., gt=0)
    aplicar_desde: Optional[date] = None
    actualizar_periodos_no_pagados: bool = True


class ClienteServicioOut(BaseModel):
    id_cliente_servicio: int
    legajo: int
    tipo_servicio: str
    monto_mensual: Decimal
    fecha_inicio: date
    activo: bool

    model_config = ConfigDict(from_attributes=True)