# app/schemas/recorrido.py
from typing import Optional, List
from pydantic import BaseModel, field_validator,ConfigDict

class ItemCantidad(BaseModel):
    id_producto: int
    cantidad: int

    @field_validator("cantidad")
    @classmethod
    def positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("cantidad debe ser > 0")
        return v

class RecorridoBase(BaseModel):
    id_empleado: Optional[int] = None
    id_repartodia: Optional[int] = None
    id_camion: Optional[str] = None
    dinero_inicial: Optional[float] = 0
    stock_inicial: Optional[int] = 0
    observacion: Optional[str] = None

class RecorridoCreate(RecorridoBase):    
    detalle_stock_inicial: List[ItemCantidad]

class RecorridoOut(RecorridoBase):
    model_config = ConfigDict(from_attributes=True)
    id_recorrido: int    
    
