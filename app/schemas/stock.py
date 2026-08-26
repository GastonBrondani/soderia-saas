from pydantic import BaseModel,ConfigDict
from typing import Optional


class StockBase(BaseModel):
    id_producto: int
    id_empresa: int
    cantidad: int =0

class StockCreate(StockBase):
    """Schema para crear un nuevo registro de stock"""
    pass


class StockUpdate(BaseModel):
    """Schema para actualizar cantidad de stock"""
    cantidad: Optional[int] = None


class StockOut(StockBase):
    model_config = ConfigDict(from_attributes=True)
    id_stock: int
      
class StockDetalleOut(BaseModel):
    id_stock: int
    id_producto: int
    id_empresa: int
    cantidad: int

    nombre_producto: str
    litros: Optional[str] = None
    tipo_dispenser: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)