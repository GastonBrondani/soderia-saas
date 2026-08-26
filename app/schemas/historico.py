from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.schemas.tipoEvento import TipoEventoOut
from app.utils.historicoDetalle import construir_detalle, extraer_monto


class HistoricoOut(BaseModel):
    """
    Para listar el historial de un cliente.
    """
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )

    id_historico: int
    legajo: int
    fecha: datetime
    observacion: Optional[str] = None
    datos: Optional[Dict[str, Any]] = None

    # En el modelo SQLAlchemy la relación seguramente se llama "tipo_evento",
    # pero en el JSON la exponemos como "evento".
    evento: TipoEventoOut = Field(alias="tipo_evento")

    # Texto legible armado a partir de `datos` según el tipo de evento.
    # El front puede mostrarlo directamente como descripción del evento.
    detalle: Optional[str] = None

    # Monto numérico principal del evento (p. ej. el total del pedido).
    # Es None para eventos que no tienen un monto asociado.
    monto: Optional[float] = None

    @model_validator(mode="after")
    def _armar_detalle(self) -> "HistoricoOut":
        if self.detalle is None:
            self.detalle = construir_detalle(
                self.evento.nombre,
                self.datos,
                self.observacion,
            )
        if self.monto is None:
            self.monto = extraer_monto(self.evento.nombre, self.datos)
        return self
