from typing import Optional, List,TYPE_CHECKING
from decimal import Decimal
from pydantic import BaseModel, field_validator,ConfigDict

if TYPE_CHECKING:
    from app.schemas.listaPrecioProducto import LPPBasicOut  # evitar import circular

class ProductoBase(BaseModel):
    nombre: Optional[str] = None
    estado: Optional[bool] = True
    litros: Optional[Decimal] = None
    tipo_dispenser: Optional[str] = None
    observacion: Optional[str] = None
    stock_inicial: Optional[int] = None        # cantidad inicial
    id_empresa_stock: Optional[int] = None     # empresa donde se crea el stock inicial
    es_envase: bool = False

    stock_inicial: Optional[int] = None        # cantidad inicial
    id_empresa_stock: Optional[int] = None     # empresa donde se crea el stock inicial
    @field_validator("nombre", "estado", "tipo_dispenser", "observacion")
    @classmethod
    def strip_strings(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if isinstance(v, str) else v


class ProductoCreate(ProductoBase):
    nombre: str  # obligatorio

class ProductoUpdate(ProductoBase):
    """PATCH/PUT parcial: sólo actualiza lo enviado."""


class ProductoOut(ProductoBase):
    model_config = ConfigDict(from_attributes=True)
    id_producto: int

class ProductoConPrecioOut(ProductoOut):
    """Producto + el precio de una lista en particular."""
    precio: Decimal
    id_lista: int

   
# --------- “Ref” liviana para anidar en otros outputs ---------
class ProductoRefOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id_producto: int
    nombre: str
   

# --------- (Opcional) Producto expandido con precios ---------
# Se define el tipo acá y se referencia por string para evitar import circular.
class ProductoWithPreciosOut(ProductoOut):
    model_config = ConfigDict(from_attributes=True)
    precios: List["LPPBasicOut"] = []  # ver lista_precio_producto.LPPBasicOut