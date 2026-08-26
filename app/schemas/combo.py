from __future__ import annotations

from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field
from decimal import Decimal

from app.schemas.comboProducto import (
    ComboProductoIn,
    ComboProductoOut,
    ComboProductoDetalleOut,
)


# --------- BASE ---------

class ComboBase(BaseModel):
    id_empresa: int
    nombre: str = Field(min_length=1, max_length=120)
    descripcion: Optional[str] = None
    estado: bool = True


# --------- CREATE / UPDATE ---------

class ComboCreate(ComboBase):
    """
    Para crear un combo con su composición (opcional).
    """
    productos: List[ComboProductoIn] = []


class ComboUpdate(BaseModel):
    """
    Para actualizar campos del combo.
    - Si 'productos' viene (incluso vacío), se interpreta como "reemplazar composición".
    - Si no viene, no se toca la composición.
    """
    nombre: Optional[str] = Field(default=None, min_length=1, max_length=120)
    descripcion: Optional[str] = None
    estado: Optional[bool] = None
    productos: Optional[List[ComboProductoIn]] = None


# --------- OUTPUT ---------

class ComboOut(ComboBase):
    model_config = ConfigDict(from_attributes=True)

    id_combo: int


class ComboDetalleOut(ComboOut):
    """
    Combo + composición detallada (incluye producto.nombre y descuenta_stock).
    Ideal para GET /combos/{id_combo}
    """
    productos: List[ComboProductoDetalleOut] = []


class ComboComposicionBasicaOut(ComboOut):
    """
    Variante si querés devolver solo id_producto y cantidad (sin datos del producto).
    """
    productos: List[ComboProductoOut] = []


class ComboConPrecioOut(BaseModel):
    """
    Para GET /listas-precios/{id_lista}/combos:
    devuelve combos con precio cargado en esa lista
    """
    model_config = ConfigDict(from_attributes=True)

    id_combo: int
    nombre: str
    precio: Decimal