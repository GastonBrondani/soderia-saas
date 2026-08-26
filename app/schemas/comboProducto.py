from __future__ import annotations

from pydantic import BaseModel, Field, ConfigDict


# --------- INPUT (para crear/actualizar composición) ---------

class ComboProductoIn(BaseModel):
    """
    Item de composición de un combo:
    - id_producto: producto que integra el combo
    - cantidad: cuántas unidades de ese producto contiene el combo
    """
    id_producto: int
    cantidad: int = Field(gt=0)


# --------- OUTPUT BÁSICO (solo ids + cantidad) ---------

class ComboProductoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_producto: int
    cantidad: int


# --------- OUTPUT DETALLADO (incluye info del producto) ---------

class ProductoMiniOut(BaseModel):
    """
    Info mínima del producto para devolver junto a la composición del combo.
    Sirve para que el front sepa, por ejemplo, si descuenta stock.
    """
    model_config = ConfigDict(from_attributes=True)

    id_producto: int
    nombre: str
    descuenta_stock: bool


class ComboProductoDetalleOut(BaseModel):
    """
    Devuelve la composición con el detalle del producto embebido.
    """
    model_config = ConfigDict(from_attributes=True)

    id_producto: int
    cantidad: int
    producto: ProductoMiniOut

