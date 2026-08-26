# app/routers/medios_pago.py
from fastapi import APIRouter, Depends, status, HTTPException
from app.core.security import get_current_user
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.core.database import get_db
from app.models.medioPago import MedioPago   # ajustá la ruta si difiere
from app.schemas.medioPago import MedioPagoCreate, MedioPagoOut

router = APIRouter(prefix="/medios-pago", tags=["Medios de pago"],dependencies=[Depends(get_current_user)],)

@router.post("/", response_model=MedioPagoOut, status_code=status.HTTP_201_CREATED)
def crear_medio_pago(data: MedioPagoCreate, db: Session = Depends(get_db)):
    nombre_norm = data.nombre.strip()

    # Evitar duplicados (case-insensitive)
    existe = db.execute(
        select(MedioPago).where(func.lower(MedioPago.nombre) == nombre_norm.lower())
    ).scalar_one_or_none()
    if existe:
        raise HTTPException(status_code=409, detail="El medio de pago ya existe.")

    medio = MedioPago(nombre=nombre_norm)
    db.add(medio)
    db.commit()
    db.refresh(medio)
    return medio

@router.get("/", response_model=list[MedioPagoOut])
def listar_medios_pago(db: Session = Depends(get_db)):
    return db.execute(
        select(MedioPago).order_by(MedioPago.nombre)
    ).scalars().all()
