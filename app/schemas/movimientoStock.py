from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict,field_validator

class TipoMovimiento(str, Enum):
    ingreso = "ingreso"
    egreso = "egreso"
    ajuste = "ajuste"    

class MovimientoStockBase(BaseModel):
    id_producto: int    
    id_recorrido: Optional[int] = None
    id_pedido: Optional[int] = None
    fecha: Optional[datetime] = None
    tipo_movimiento: TipoMovimiento
    cantidad: int
    observacion: Optional[str] = None

    @field_validator("cantidad")
    @classmethod
    def cantidad_positiva(cls, v):
        if v <= 0:
            raise ValueError("cantidad debe ser > 0")
        return v

class MovimientoCreate(MovimientoStockBase):
    """Schema para crear un movimiento (ingreso, egreso o ajuste)."""
    pass

class MovimientoOut(MovimientoStockBase):
    model_config = ConfigDict(from_attributes=True)
    id_movimiento: int
    