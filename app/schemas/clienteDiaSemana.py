from typing import Optional, List
from datetime import date
from pydantic import BaseModel, ConfigDict

from app.schemas.enums_cliente import DiaSemanaEnum, TurnoVisitaEnum, PosicionEnum


# ================== BASE ==================

class ClienteDiaSemanaBase(BaseModel):
    # 👇 ya no exigimos id_cliente en los payloads de entrada
    id_dia: int
    turno_visita: Optional[str] = None


# ================== CREATE ==================

class ClienteDiaSemanaCreate(ClienteDiaSemanaBase):
    posicion: PosicionEnum = PosicionEnum.final
    despues_de_legajo: Optional[int] = None  # requerido si posicion = "despues"


# ================== UPDATE ==================

class ClienteDiaSemanaUpdate(BaseModel):
    # Para el PUT /{legajo}/detalle solo necesitamos esto:
    id_dia: int
    turno_visita: Optional[str] = None
    orden: Optional[int] = None


# ================== OUT ==================

class ClienteDiaSemanaOut(ClienteDiaSemanaBase):
    model_config = ConfigDict(from_attributes=True)
    id_cliente: int
    orden: Optional[int] = None


# ================== FRECUENCIA (crear cliente) ==================

class FrecuenciaItemIn(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    dia: DiaSemanaEnum          # "lun".."dom"
    turno: Optional[TurnoVisitaEnum]  # "manana"|"tarde"|"noche"|None
    posicion: PosicionEnum = PosicionEnum.final
    despues_de_legajo: Optional[int] = None  # requerido si posicion="despues"


class ClienteDiaVisitaOut(BaseModel):
    id_dia: int
    nombre_dia: str
    turno_visita: Optional[str] = None

class ClienteAgendaConDatosItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    legajo: int
    dni: Optional[int] = None
    nombre: Optional[str] = None
    apellido: Optional[str] = None
    turno_visita: Optional[str] = None
    estado_visita: Optional[str] = None
    # --- campos que antes venían del /detalle ---
    direccion: Optional[str] = None
    telefono: Optional[str] = None
    id_cuenta: Optional[int] = None
    saldo: float = 0.0
    deuda: float = 0.0
    observacion: Optional[str] = None   # observación del CLIENTE

class AgendaConDatosOut(BaseModel):
    fecha: date
    id_dia: int
    nombre_dia: str
    clientes: List[ClienteAgendaConDatosItem]
