from typing import Optional, List
from fastapi import APIRouter, Depends, status
from app.core.security import get_current_user
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.features.repartos.camiones.schemas import (
    CamionRepartoCreate,
    CamionRepartoUpdate,
    CamionRepartoOut,
)
from app.features.repartos.camiones import service

router = APIRouter(prefix="/camiones-reparto", tags=["CamiónReparto"],dependencies=[Depends(get_current_user)],)


@router.post("/", response_model=CamionRepartoOut, status_code=status.HTTP_201_CREATED)
def crear_camion(payload: CamionRepartoCreate, db: Session = Depends(get_db)):
    return service.crear_camion(db, payload)


@router.get("/", response_model=List[CamionRepartoOut])
def listar_camiones(db: Session = Depends(get_db), activo: Optional[bool] = None):
    return service.listar_camiones(db, activo)


@router.get("/{patente}", response_model=CamionRepartoOut)
def obtener_camion(patente: str, db: Session = Depends(get_db)):
    return service.obtener_camion(db, patente)


@router.patch("/{patente}", response_model=CamionRepartoOut)
def actualizar_camion(patente: str, payload: CamionRepartoUpdate, db: Session = Depends(get_db)):
    return service.actualizar_camion(db, patente, payload)


@router.delete("/{patente}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_camion(patente: str, db: Session = Depends(get_db)):
    service.eliminar_camion(db, patente)
    return None
