# app/schemas/stockDetalle.py
from pydantic import BaseModel
from typing import Optional

class StockDetalleOut(BaseModel):
    id_producto: int
    nombre_producto: str
    cantidad: int
    litros: Optional[float] = None
    tipo_dispenser: Optional[str] = None
