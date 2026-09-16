from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field


class TipoPago(str, Enum):
    """Todo lo que PagoService.crear() sabe interpretar para impactar
    cuenta/reparto/caja. Los 5 valores son los que realmente existen hoy en
    la tabla `pago` (auditado 2026-09-15 via grep de literales en el
    codigo) -- si aparece algo mas en datos historicos de produccion que
    no pasó por este código, hay que agregarlo aca antes de deployar, o
    la serializacion de PagoOut revienta con 500 al leer esa fila.
    """

    COBRO_PEDIDO = "COBRO_PEDIDO"
    PAGO_DEUDA = "PAGO_DEUDA"
    INGRESO_EMPRESA = "INGRESO_EMPRESA"
    EGRESO_EMPRESA = "EGRESO_EMPRESA"
    SERVICIO = "SERVICIO"


# Los unicos dos valores que un cliente puede elegir mandando POST /pagos
# (sync offline incluido). INGRESO_EMPRESA/EGRESO_EMPRESA los ponen sus
# propios endpoints (/pagos/ingreso, /pagos/egreso) como literal de
# Python, no via este schema; SERVICIO lo pone
# catalogo/servicios/service.py, tampoco via este schema. Un valor que no
# sea ninguno de estos dos (ej. "cobro_reparto", el bug que motivo esto)
# ahora da 422 en vez de crear un pago que no impacta nada.
TipoPagoCliente = Literal["COBRO_PEDIDO", "PAGO_DEUDA"]


class PagoCreate(BaseModel):
    # El servidor infiere la empresa del tenant actual (ver
    # EmpresaService.get_id_empresa_actual). Si el cliente lo manda, se
    # ignora: no es la frontera de seguridad desde que hay una base por
    # sodería, y confiar en el valor del cliente es el agujero que la
    # migración vino a cerrar.
    id_empresa: Optional[int] = None
    id_medio_pago: int
    fecha: datetime
    monto: Decimal = Field(gt=0)

    tipo_pago: TipoPagoCliente
    observacion: Optional[str] = None

    legajo: Optional[int] = None
    id_cuenta: Optional[int] = None
    id_pedido: Optional[int] = None
    id_repartodia: Optional[int] = None

    # Offline sync: idempotencia. La tablet manda estos valores al reintentar.
    idempotency_key: Optional[str] = None
    client_uuid: Optional[str] = None


class PagoOut(BaseModel):
    id_pago: int
    id_empresa: int
    id_medio_pago: int
    fecha: datetime
    monto: Decimal
    # str, no TipoPago: esto lee filas de `pago` que ya existen (incluida
    # data historica de produccion, si algun dia se importa). Estricto en
    # la entrada (PagoCreate.tipo_pago), tolerante en la salida -- un
    # valor viejo o inesperado no puede tirar 500 al leerlo.
    tipo_pago: str
    observacion: Optional[str]

    legajo: Optional[int]
    id_pedido: Optional[int]
    id_repartodia: Optional[int]

    idempotency_key: Optional[str] = None
    client_uuid: Optional[str] = None

    class Config:
        from_attributes = True

class PagoLibreIn(BaseModel):
    legajo: int
    id_cuenta: int
    id_empresa: Optional[int] = None
    id_medio_pago: int
    monto: Decimal = Field(gt=0)
    observacion: Optional[str] = None
    id_repartodia: Optional[int] = None


class PagoLibreOut(BaseModel):
    id_pago: int
    comprobante_url: str


class MotivoEgreso(str, Enum):
    COMBUSTIBLE = "COMBUSTIBLE"
    SUELDOS = "SUELDOS"
    INSUMOS = "INSUMOS"
    OTRO = "OTRO"


class PagoEgresoCreate(BaseModel):
    id_medio_pago: int
    monto: Decimal = Field(gt=0)
    motivo: MotivoEgreso
    observacion: Optional[str] = None
    fecha: Optional[datetime] = None


class PagoIngresoCreate(BaseModel):
    id_medio_pago: int
    monto: Decimal = Field(gt=0)
    observacion: Optional[str] = None
    fecha: Optional[datetime] = None
