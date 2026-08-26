from datetime import datetime
from typing import Optional,Literal,List
from pydantic import BaseModel,ConfigDict,model_validator

from app.schemas.envaseCliente import EnvaseMovimientoPedidoIn



class VisitaBase(BaseModel):
    fecha: Optional[datetime] = None
    estado: Literal[
        "cliente_compra",
        "cliente_no_compra",
        "postergacion_cliente",
    ]

class VisitaCreate(VisitaBase):
    # Offline sync: idempotencia. La tablet manda estos valores al reintentar.
    idempotency_key: Optional[str] = None
    client_uuid: Optional[str] = None

    # Movimiento de envases durante la visita (ej: el cliente devuelve bidones
    # sin comprar). Reusamos el mismo schema que la confirmación de pedido.
    # `id_repartodia` es de dónde se resuelve la empresa para mover el stock.
    id_repartodia: Optional[int] = None
    envases: Optional[List[EnvaseMovimientoPedidoIn]] = None

    @model_validator(mode="after")
    def _exigir_repartodia_si_hay_envases(self) -> "VisitaCreate":
        if self.envases and self.id_repartodia is None:
            raise ValueError(
                "id_repartodia es obligatorio cuando se envían envases."
            )
        return self

class VisitaOut(VisitaBase):
    model_config = ConfigDict(from_attributes=True)

    id_visita: int
    legajo: int
    idempotency_key: Optional[str] = None
    client_uuid: Optional[str] = None