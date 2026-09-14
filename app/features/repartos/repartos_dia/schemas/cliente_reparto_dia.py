from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, field_validator


# --- Catálogos sugeridos (podés ampliar si hace falta) ---
ESTADOS_PERMITIDOS = {
    "pendiente",
    "entregado",
    "ausente",
    "rechazado",
    "reprogramado",
    "parcial",
}

TURNOS_PERMITIDOS = {
    "mañana",
    "tarde",
    "noche",
}



class ClienteRepartoDiaCreate(BaseModel):   
    pass


# --------- UPDATE (Resultado de la visita) ----------
class ClienteRepartoDiaUpdate(BaseModel):
     pass

# --------- OUT (Respuesta) ----------
class ClienteRepartoDiaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_repartodia: int
    legajo: int
    bidones_entregado: int
    monto_abonado: Decimal
    estado_de_la_visita: Optional[str] = None
    turno_de_la_visita: Optional[str] = None
    observacion: Optional[str] = None