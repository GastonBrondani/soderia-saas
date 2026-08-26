from typing import Optional, List
from pydantic import BaseModel, field_validator, ConfigDict, Field
from enum import StrEnum
from datetime import datetime
from decimal import Decimal
from app.schemas.pedidoProducto import PedidoItemIn
from app.schemas.envaseCliente import EnvaseMovimientoPedidoIn


class PedidoServicioCreate(BaseModel):
    tipo_servicio: Optional[str] = "ALQUILER_DISPENSER"
    monto: Optional[Decimal] = None


class EstadoPedido(StrEnum):
    pendiente = "pendiente"  # Pendiente de pago, todavia no se pago
    abonado = "abonado"  # Total o parcialmente abonado
    abonado_parcialmente = (
        "abonado parcialmente"  # Abonado parcialmente, queda deuda pendiente
    )
    cliente_no_compra = "cliente no compra"  # El cliente no compro nada, este estado hace referencia a que el pedido no existio, es para guardar el historico.
    pedido_postergado = "pedido postergado"  # El cliente pidio postergar el pedido para otro momento/horario
    cliente_pago_de_mas = "cliente pago de más"  # El cliente pago de mas queda con saldo a favor en cliente cuenta.


class PedidoItemCreate(BaseModel):
    id_producto: int
    cantidad: Decimal
    precio_unitario: Decimal



class PedidoBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    legajo: int
    id_medio_pago: int
    id_empresa: int = 1
    fecha: datetime = Field(default_factory=datetime.now)
    monto_total: Decimal
    monto_abonado: Decimal = Decimal("0.00")
    estado: EstadoPedido = EstadoPedido.pendiente
    observacion: Optional[str] = None
    id_repartodia: int
    id_cuenta: Optional[int] = None
    items: Optional[List[PedidoItemIn]] = None

    # Offline sync: idempotencia. La tablet manda estos valores al reintentar.
    idempotency_key: Optional[str] = None
    client_uuid: Optional[str] = None

    @field_validator("estado", "observacion")
    @classmethod
    def strip_strings(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if isinstance(v, str) else v


class PedidoCreate(PedidoBase):
    legajo: int  # obligatorio
    id_medio_pago: int  # obligatorio
    id_empresa: int  # obligatorio
    fecha: datetime  # obligatorio
    monto_total: Decimal  # obligatorio


# Usado para cancelar deudas.
class PedidoCancelarDeudaIn(BaseModel):
    legajo: int
    id_medio_pago: int
    id_repartodia: int
    monto: Decimal
    observacion: str | None = None


class PedidoOut(PedidoBase):
    model_config = ConfigDict(from_attributes=True)
    id_pedido: int


class PedidoConfirmarIn(BaseModel):
    id_repartodia: int
    envases: List[EnvaseMovimientoPedidoIn] = Field(default_factory=list)


# EMMA
class PedidoOutCorto(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id_pedido: int
    fecha: datetime
    estado: Optional[str] = None

    # "total" en la respuesta, pero sale de Pedido.monto_total (ORM)
    total: Optional[Decimal] = Field(
        default=None,
        validation_alias="monto_total",
        serialization_alias="total",
    )
