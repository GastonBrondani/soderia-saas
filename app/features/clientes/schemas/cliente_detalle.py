from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field

# schemas para mostrar detalles relacionados
from app.features.personas.schemas import PersonaOut, PersonaUpdate
from app.features.clientes.schemas.direccion_cliente import DireccionClienteOut, DireccionClienteUpdate
from app.features.clientes.schemas.telefono_cliente import TelefonoClienteOut, TelefonoClienteUpdate
from app.features.clientes.schemas.email_cliente import MailClienteOut, MailClienteUpdate

# from app.schemas.documentos import DocumentosOut
from app.features.catalogo.productos.schemas import ProductoOut
from app.features.clientes.schemas.cliente_cuenta import ClienteCuentaOut, ClienteCuentaUpdate
from app.features.repartos.agenda.schemas.cliente_dia_semana import ClienteDiaSemanaOut, ClienteDiaSemanaUpdate
from app.features.auditoria.schemas.historico import HistoricoOut


# Mostramos todo lo relacionado al cliente.
class ClienteDetalleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    legajo: int
    persona: Optional[PersonaOut] = None
    direcciones: List[DireccionClienteOut] = Field(default_factory=list)
    telefonos: List[TelefonoClienteOut] = Field(default_factory=list)
    emails: List[MailClienteOut] = Field(default_factory=list)
    # documentos: List[DocumentosOut] = Field(default_factory=list)
    productos: List[ProductoOut] = Field(default_factory=list)
    cuentas: List[ClienteCuentaOut] = Field(default_factory=list)
    dias_semanas: List[ClienteDiaSemanaOut] = Field(default_factory=list)
    historicos: List[HistoricoOut] = Field(default_factory=list)


# relaciones adicionales

# app/schemas/clienteDetalle.py
from typing import List, Optional
from pydantic import Field
from app.features.clientes.schemas.cliente import ClienteOut
from app.features.clientes.schemas.direccion_cliente import DireccionClienteOut
from app.features.clientes.schemas.telefono_cliente import TelefonoClienteOut
from app.features.clientes.schemas.email_cliente import MailClienteOut
from app.features.catalogo.productos.schemas import ProductoOut
from app.features.clientes.schemas.cliente_cuenta import ClienteCuentaOut
from app.features.pedidos.schemas.pedido import PedidoOutCorto
from app.features.auditoria.schemas.historico import HistoricoOut
from app.features.clientes.schemas.cliente import DiaSemanaEnum, TurnoVisitaEnum


class ClienteDetalleOut(ClienteOut):
    direcciones: List[DireccionClienteOut] = Field(default_factory=list)
    telefonos: List[TelefonoClienteOut] = Field(default_factory=list)
    emails: List[MailClienteOut] = Field(default_factory=list)
    productos: List[ProductoOut] = Field(default_factory=list)
    cuentas: List[ClienteCuentaOut] = Field(default_factory=list)

    pedidos: List[PedidoOutCorto] = Field(default_factory=list)
    historicos: List[HistoricoOut] = Field(default_factory=list)

    dias_visita: List[DiaSemanaEnum] = Field(default_factory=list)
    turno_visita: Optional[TurnoVisitaEnum] = None

    # Esquema para actualizar todo lo relacionado al cliente.


# Ir agregando si es necesario.
class ClienteDetalleUpdate(BaseModel):
    persona: Optional[PersonaUpdate] = None
    direcciones: Optional[List[DireccionClienteUpdate]] = None
    telefonos: Optional[List[TelefonoClienteUpdate]] = None
    emails: Optional[List[MailClienteUpdate]] = None
    cuentas: Optional[List[ClienteCuentaUpdate]] = None
    dias_semanas: Optional[List[ClienteDiaSemanaUpdate]] = None
