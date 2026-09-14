from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EnvaseMovimientoPedidoIn(BaseModel):
    """
    Envases entregados/devueltos durante la confirmación de un pedido.

    entregados:
        Cantidad de envases que la empresa le deja al cliente.

    devueltos:
        Cantidad de envases que el cliente devuelve a la empresa.
    """

    id_producto: int
    entregados: int = Field(default=0, ge=0)
    devueltos: int = Field(default=0, ge=0)
    observacion: Optional[str] = None

    @model_validator(mode="after")
    def validar_movimiento(self):
        if self.entregados == 0 and self.devueltos == 0:
            raise ValueError("Debe venir al menos un envase entregado o devuelto.")

        return self


class EnvaseMovimientoManualIn(BaseModel):
    """
    Para un futuro endpoint manual:
    POST /envases/movimiento

    Sirve para registrar envases sin pedido, por ejemplo:
    - cliente devuelve envase sin comprar
    - se ajusta saldo manualmente
    - se marca pérdida
    """

    legajo: int
    id_producto: int
    id_empresa: int = 1
    entregados: int = Field(default=0, ge=0)
    devueltos: int = Field(default=0, ge=0)
    id_repartodia: Optional[int] = None
    observacion: Optional[str] = None

    @model_validator(mode="after")
    def validar_movimiento(self):
        if self.entregados == 0 and self.devueltos == 0:
            raise ValueError("Debe venir al menos un envase entregado o devuelto.")

        return self


class EnvaseSaldoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    legajo: int
    id_producto: int
    cantidad: int
    estado: Optional[str] = None
    fecha_entrega: Optional[datetime] = None


class MovimientoEnvaseClienteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_movimiento: int
    legajo: int
    id_producto: int
    id_repartodia: Optional[int] = None
    id_pedido: Optional[int] = None
    fecha: datetime
    tipo: str
    cantidad: int
    observacion: Optional[str] = None