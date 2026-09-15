from fastapi import APIRouter, Depends, status, Query
from app.core.security import get_current_user
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date

from app.core.database import get_db
from app.features.empresas.service import EmpresaService
from app.features.repartos.repartos_dia.schemas.reparto_dia import (
    RepartoDiaCreate, RepartoDiaOut
)
from app.features.sincronizacion.schemas import RepartoBootstrapOut
from app.features.repartos.repartos_dia.services.reparto_dia import RepartoDiaService
from app.features.sincronizacion.service import reparto_bootstrap

router = APIRouter(prefix="/repartos-dia", tags=["Reparto Día"],dependencies=[Depends(get_current_user)],)


# Offline sync: baja en una sola request el reparto del día + los clientes a
# visitar (dirección, teléfono, cuenta, saldo/deuda y estado de visita).
@router.get("/bootstrap", response_model=RepartoBootstrapOut)
def bootstrap_reparto_dia(
    fecha: date = Query(..., description="Fecha del reparto (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
):
    return reparto_bootstrap(db, fecha=fecha)

@router.post("/", response_model=RepartoDiaOut, status_code=status.HTTP_201_CREATED)

# Crear un nuevo reparto del día(Funciona)
def crear_reparto_dia(payload: RepartoDiaCreate, db: Session = Depends(get_db)):
    return RepartoDiaService.create(
        db,
        id_usuario=payload.id_usuario,
        id_empresa=EmpresaService.get_id_empresa_actual(db),
        fecha=payload.fecha,
        observacion=payload.observacion,
    )


#Obtener un reparto del día por fecha (Funciona)
@router.get("/por-fecha", response_model=RepartoDiaOut)
def obtener_reparto_dia_por_fecha(
    fecha: date = Query(..., description="Fecha del reparto"),
    id_usuario: Optional[int] = Query(None, description="Usuario creador (opcional)"),
    db: Session = Depends(get_db),
):
    return RepartoDiaService.get_by_fecha(
        db,
        fecha=fecha,
        id_usuario=id_usuario,
    )


@router.get("/por-rango", response_model=List[RepartoDiaOut])
def listar_repartos_por_rango(
    fecha_desde: date = Query(..., description="Desde (inclusive)"),
    fecha_hasta: date = Query(..., description="Hasta (inclusive)"),
    id_usuario: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    return RepartoDiaService.listar_por_rango(
        db,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        id_usuario=id_usuario,
    )


@router.post("/{id_repartodia}/cerrar", response_model=RepartoDiaOut)
def cerrar_reparto_dia(id_repartodia: int, db: Session = Depends(get_db)):
    return RepartoDiaService.cerrar(db, id_repartodia=id_repartodia)
