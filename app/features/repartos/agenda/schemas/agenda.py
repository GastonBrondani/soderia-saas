from pydantic import BaseModel
from typing import Optional

class AgendaMoverIn(BaseModel):
    id_cliente: int
    id_dia: int
    turno: Optional[str] = None
    posicion: str  # "inicio" | "final" | "despues"
    despues_de_legajo: Optional[int] = None
