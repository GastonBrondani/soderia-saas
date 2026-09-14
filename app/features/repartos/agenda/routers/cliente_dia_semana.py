from fastapi import APIRouter, Depends, Query
from app.core.security import get_current_user
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import List, Optional
from pydantic import BaseModel, ConfigDict

from app.features.repartos.agenda import service as agenda_service
from app.features.clientes.dependencies import get_cliente_or_404_dep
from app.core.database import get_db
from app.features.repartos.agenda.models.cliente_dia_semana import ClienteDiaSemana
from app.features.maestros.models.dia_semana import DiaSemana
from app.features.clientes.models.cliente import Cliente
from app.features.repartos.agenda.schemas.cliente_dia_semana import (
    AgendaConDatosOut,
    AgendaRangoOut,
    ClientesPorDiaOut,
    ClientesPorDiaSinFechaOut,
)


router = APIRouter(prefix="/clientes", tags=["Cliente - días de visita"],dependencies=[Depends(get_current_user)],)

# ---- Schemas específicos del router (payload/response del endpoint) ----
class ClienteDiaVisitaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id_dia: int
    nombre_dia: str
    turno_visita: Optional[str] = None


#Este router maneja los días de visita de los clientes pasandome una fecha te muestro todos los clientes de ese dia.(Funciona)
@router.get("/agenda/visitas", response_model=ClientesPorDiaOut)
def listar_clientes_por_fecha(
    fecha: date = Query(..., description="YYYY-MM-DD"),
    turno: Optional[str] = Query(None, description="Mañana | Tarde | ..."),
    db: Session = Depends(get_db),
):
    return agenda_service.listar_clientes_por_fecha(db, fecha, turno)

@router.get("/agenda/visitas/con-datos", response_model=AgendaConDatosOut)
def listar_clientes_por_fecha_con_datos(
    fecha: date = Query(..., description="YYYY-MM-DD"),
    turno: Optional[str] = Query(None, description="Mañana | Tarde | ..."),
    db: Session = Depends(get_db),
):
    return agenda_service.listar_clientes_por_fecha_con_datos(db, fecha, turno)

@router.get("/agenda/visitas/rango", response_model=AgendaRangoOut)
def listar_clientes_por_rango(
    desde: date = Query(..., description="YYYY-MM-DD"),
    hasta: date = Query(..., description="YYYY-MM-DD"),
    turno: Optional[str] = Query(None, description="Mañana | Tarde | ..."),
    db: Session = Depends(get_db),
):
    return agenda_service.listar_clientes_por_rango(db, desde, hasta, turno)

#Trae los dias de visita del cliente por los id del dia (Funciona)
@router.get("/agenda/visitas/dia/{id_dia}", response_model=ClientesPorDiaSinFechaOut)
def listar_clientes_por_id_dia(
    id_dia: int,
    turno: Optional[str] = Query(None),
    fecha: Optional[date] = Query(None, description="YYYY-MM-DD (opcional para estado_visita)"),
    db: Session = Depends(get_db),
):
    return agenda_service.listar_clientes_por_id_dia(db, id_dia, turno, fecha)
#-----------------------------------


#Muestra el dia de la semana que visita el cliente (Funciona)
@router.get("/{legajo}/dias-visita", response_model=List[ClienteDiaVisitaOut])
def listar_dias_visita_cliente(
    cliente: Cliente = Depends(get_cliente_or_404_dep),
    db: Session = Depends(get_db),
):
    stmt = (
        select(
            ClienteDiaSemana.id_dia,
            DiaSemana.nombre_dia,
            ClienteDiaSemana.turno_visita,
        )
        .select_from(ClienteDiaSemana)
        .join(DiaSemana, DiaSemana.id_dia == ClienteDiaSemana.id_dia)
        .where(ClienteDiaSemana.id_cliente == cliente.legajo)
        .order_by(ClienteDiaSemana.id_dia)
    )
    rows = db.execute(stmt).all()
    return [
        ClienteDiaVisitaOut(
            id_dia=r.id_dia,
            nombre_dia=r.nombre_dia,
            turno_visita=r.turno_visita,
        )
        for r in rows
    ]

#Elimina un dia de visita del cliente (Funciona)
@router.delete("/{legajo}/dias-visita/{id_dia}", status_code=204)
def eliminar_dia_visita_cliente(
    id_dia: int,
    cliente: Cliente = Depends(get_cliente_or_404_dep),
    db: Session = Depends(get_db),
):
    agenda_service.eliminar_dia_visita_cliente(db, cliente.legajo, id_dia)
