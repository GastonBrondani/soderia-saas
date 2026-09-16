from pydantic import BaseModel,ConfigDict
from typing import Optional


class StockBase(BaseModel):
    id_producto: int
    id_empresa: int
    cantidad: int =0

class StockCreate(StockBase):
    """Schema para crear un nuevo registro de stock. Sin router que lo use
    hoy (StockService.set_stock/ajustar_stock resuelven el stock por
    upsert), pero si algún día se cablea uno: el servidor infiere la
    empresa del tenant actual, no confíes en este campo."""
    id_empresa: Optional[int] = None


class StockUpdate(BaseModel):
    """Schema para actualizar cantidad de stock"""
    cantidad: Optional[int] = None


class StockOut(StockBase):
    model_config = ConfigDict(from_attributes=True)
    id_stock: int