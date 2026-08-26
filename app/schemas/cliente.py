from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.persona import PersonaCreate, PersonaOut, PersonaUpdate
from app.schemas.direccionCliente import DireccionClienteOut
from app.schemas.telefonoCliente import TelefonoClienteOut
from app.schemas.emailCliente import MailClienteOut
from app.schemas.producto import ProductoOut
from app.schemas.clienteCuenta import ClienteCuentaOut
from app.schemas.clienteDiaSemana import FrecuenciaItemIn, ClienteDiaSemanaOut
from app.schemas.enums_cliente import DiaSemanaEnum, TurnoVisitaEnum


# Emma
# -----------------------------
from app.schemas.pedido import PedidoOutCorto
from app.schemas.historico import HistoricoOut
# -----------------------------


class DireccionClienteCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    direccion: str
    entre_calle1: Optional[str] = None
    entre_calle2: Optional[str] = None
    zona: Optional[str] = None

    @field_validator("direccion", "entre_calle1", "entre_calle2", "zona")
    @classmethod
    def _trim(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if isinstance(v, str) else v


class TelefonoClienteCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    nro_telefono: str

    @field_validator("nro_telefono")
    @classmethod
    def _trim_phone(cls, v: str) -> str:
        return v.strip()


class MailClienteCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    mail: str


# -----------------------------
# Cliente (Base/Create/Update/Out)
# -----------------------------
class ClienteBase(BaseModel):
    observacion: Optional[str] = None

    @field_validator("observacion")
    @classmethod
    def _trim_obs(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if isinstance(v, str) else v


class ClienteCreate(ClienteBase):
    dni: Optional[int] = Field(default=None, gt=0)
    persona: Optional[PersonaCreate] = None

    direcciones: List[DireccionClienteCreate] = Field(default_factory=list)
    telefonos: List[TelefonoClienteCreate] = Field(default_factory=list)
    emails: List[MailClienteCreate] = Field(default_factory=list)

    # 👇 ahora sí: días + (opcional) turno común
    dias_visita: List[DiaSemanaEnum] = Field(default_factory=list)
    turno_visita: Optional[TurnoVisitaEnum] = None
    frecuencias: Optional[List[FrecuenciaItemIn]] = None

    @model_validator(mode="after")
    def _check_persona_or_dni(self):
        dni = self.dni
        persona_dni = getattr(self.persona, "dni", None) if self.persona else None
        if not dni and not self.persona:
            raise ValueError(
                "Debes enviar 'dni' de una persona existente o 'persona' completa para crearla."
            )
        if dni and self.persona and persona_dni and dni != persona_dni:
            raise ValueError("Si envías 'dni' y 'persona', ambos deben coincidir.")
        return self


class ClienteUpdate(BaseModel):
    observacion: Optional[str] = None
    persona: Optional[PersonaUpdate] = None


class ClienteOut(ClienteBase):
    model_config = ConfigDict(from_attributes=True)
    legajo: int
    dni: int
    persona: Optional[PersonaOut] = None
    dias_semanas: List[ClienteDiaSemanaOut] = Field(default_factory=list)


class ClienteDetalleOut(ClienteOut): 
    direcciones: List[DireccionClienteOut] = Field(default_factory=list) 
    telefonos: List[TelefonoClienteOut] = Field(default_factory=list) 
    emails: List[MailClienteOut] = Field(default_factory=list) 
    productos: List[ProductoOut] = Field(default_factory=list) 
    cuentas: List[ClienteCuentaOut] = Field(default_factory=list)  
     #dias_visita: List[DiaSemanaEnum] = Field(default_factory=list) 
     #turno_visita: Optional[TurnoVisitaEnum] = None
    
    # Emma
        # relaciones adicionales
    pedidos: List[PedidoOutCorto] = Field(default_factory=list)
    historicos: List[HistoricoOut] = Field(default_factory=list)
    
        # datos de visita
    dias_visita: List[DiaSemanaEnum] = Field(default_factory=list)
    turno_visita: Optional[TurnoVisitaEnum] = None

class ClienteListOut(ClienteBase):
    model_config = ConfigDict(from_attributes=True)

    legajo: int
    dni: int
    persona: Optional[PersonaOut] = None
    telefonos: List[TelefonoClienteOut] = Field(default_factory=list)
    dias_semanas: List[ClienteDiaSemanaOut] = Field(default_factory=list)
