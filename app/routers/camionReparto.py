from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from app.core.security import get_current_user
from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError


from app.core.database import get_db  # ajustá el import según tu proyecto
from app.models.camionReparto import CamionReparto
from app.schemas.camionReparto import (
    CamionRepartoCreate,
    CamionRepartoUpdate,
    CamionRepartoOut,
)

router = APIRouter(prefix="/camiones-reparto", tags=["CamiónReparto"],dependencies=[Depends(get_current_user)],)



def _get_or_404(db: Session, patente: str) -> CamionReparto:
    obj = db.get(CamionReparto, patente)
    if not obj:
        raise HTTPException(status_code=404, detail="Camión no encontrado.")
    return obj



@router.post("/", response_model=CamionRepartoOut, status_code=status.HTTP_201_CREATED)
def crear_camion(payload: CamionRepartoCreate, db: Session = Depends(get_db)):
    
    existing = db.get(CamionReparto, payload.patente)
    if existing:
        raise HTTPException(status_code=409, detail="Ya existe un camión con esa patente.")

    entity = CamionReparto(
        patente=payload.patente,
        id_empresa=payload.id_empresa,
        activo=payload.activo,
    )
    db.add(entity)
    try:
        db.commit()
        db.refresh(entity)
    except IntegrityError as e:
        db.rollback()        
        raise HTTPException(
            status_code=409,
            detail="No se pudo crear el camión. Verificá que la empresa exista y que la patente no esté duplicada.",
        ) from e
    return entity



@router.get("/", response_model=List[CamionRepartoOut])
def listar_camiones(db: Session = Depends(get_db), activo: Optional[bool] = None):
    stmt = select(CamionReparto).order_by(CamionReparto.patente)
    if activo is not None:
        stmt = stmt.where(CamionReparto.activo == activo)
    rows = db.execute(stmt).scalars().all()
    return rows



@router.get("/{patente}", response_model=CamionRepartoOut)
def obtener_camion(patente: str, db: Session = Depends(get_db)):
    entity = _get_or_404(db, patente)
    return entity



@router.patch("/{patente}", response_model=CamionRepartoOut)
def actualizar_camion(patente: str, payload: CamionRepartoUpdate, db: Session = Depends(get_db)):
    entity = _get_or_404(db, patente)

    data = payload.model_dump(exclude_unset=True)
    
    if "id_empresa" in data:
        entity.id_empresa = data["id_empresa"]
    if "activo" in data:
        entity.activo = data["activo"]

    try:
        db.commit()
        db.refresh(entity)
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="No se pudo actualizar el camión. Verificá la empresa o los datos enviados.",
        ) from e

    return entity



@router.delete("/{patente}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_camion(patente: str, db: Session = Depends(get_db)):
    entity = _get_or_404(db, patente)

    try:
        db.delete(entity)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="No se puede eliminar el camión porque está siendo utilizado en otra parte.",
        )
    return None

