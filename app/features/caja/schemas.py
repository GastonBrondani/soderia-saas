# app/schemas/cajaEmpresa.py
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


# =========================
# TOTAL DE CAJA
# =========================

class CajaEmpresaTotalOut(BaseModel):
    total: Decimal

    model_config = ConfigDict(from_attributes=True)


# =========================
# MOVIMIENTOS DE CAJA
# =========================

class CajaEmpresaMovimientoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_movimiento: int
    id_empresa: int
    fecha: datetime
    tipo: str
    monto: Decimal
    observacion: Optional[str] = None

    # Campos “enriquecidos” por joins
    medio_pago: Optional[str] = None
    tipo_movimiento: Optional[str] = None


class CajaEmpresaMovimientosListOut(BaseModel):
    items: List[CajaEmpresaMovimientoOut]
    total: int

