"""Schemas para los endpoints de bootstrap (offline sync).

La tablet baja de una sola vez todo lo que necesita para trabajar offline:
- /repartos-dia/bootstrap : reparto del día + clientes a visitar (con dirección,
  teléfono, cuenta, saldo/deuda y estado de visita).
- /catalogo/bootstrap     : listas de precios, productos, combos y medios de pago.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict

from app.schemas.precioItem import PrecioItemOut
from app.schemas.medioPago import MedioPagoOut


# ---------------------------------------------------------------------------
# Reparto del día
# ---------------------------------------------------------------------------
class DireccionBootstrap(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id_direccion: int
    direccion: Optional[str] = None
    localidad: Optional[str] = None
    zona: Optional[str] = None
    entre_calle1: Optional[str] = None
    entre_calle2: Optional[str] = None
    latitud_longitud: Optional[str] = None


class CuentaBootstrap(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id_cuenta: int
    saldo: Decimal
    deuda: Decimal
    estado: Optional[str] = None
    tipo_de_cuenta: Optional[str] = None
    numero_bidones: Optional[int] = None


class ClienteRepartoBootstrap(BaseModel):
    legajo: int
    nombre: Optional[str] = None
    apellido: Optional[str] = None
    telefono: Optional[str] = None
    direccion: Optional[DireccionBootstrap] = None
    cuenta: Optional[CuentaBootstrap] = None
    # saldo/deuda planos para que el front no tenga que entrar a `cuenta`
    saldo: Optional[Decimal] = None
    deuda: Optional[Decimal] = None
    turno: Optional[str] = None
    orden: Optional[int] = None
    estado_visita: Optional[str] = None


class RepartoBootstrap(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id_repartodia: int
    fecha: date
    id_empresa: int
    total_recaudado: Optional[Decimal] = None
    total_efectivo: Optional[Decimal] = None
    total_virtual: Optional[Decimal] = None


class RepartoBootstrapOut(BaseModel):
    fecha: date
    id_dia: int  # 1=Lunes ... 7=Domingo
    # `reparto` es None si todavía no se creó el reparto para esa fecha.
    reparto: Optional[RepartoBootstrap] = None
    clientes: List[ClienteRepartoBootstrap]


# ---------------------------------------------------------------------------
# Catálogo
# ---------------------------------------------------------------------------
class ComboProductoBootstrap(BaseModel):
    id_producto: int
    nombre: Optional[str] = None
    cantidad: int


class ProductoBootstrap(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id_producto: int
    nombre: str
    estado: Optional[str] = None
    litros: Optional[Decimal] = None
    tipo_dispenser: Optional[str] = None
    es_envase: bool
    descuenta_stock: bool


class ComboBootstrap(BaseModel):
    id_combo: int
    nombre: str
    descripcion: Optional[str] = None
    estado: bool
    productos: List[ComboProductoBootstrap]


class ListaPreciosBootstrap(BaseModel):
    id_lista: int
    nombre: Optional[str] = None
    estado: Optional[str] = None
    items: List[PrecioItemOut]


class CatalogoBootstrapOut(BaseModel):
    listas_precios: List[ListaPreciosBootstrap]
    productos: List[ProductoBootstrap]
    combos: List[ComboBootstrap]
    medios_pago: List[MedioPagoOut]
