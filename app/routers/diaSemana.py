from fastapi import APIRouter, Depends
from app.core.security import get_current_user
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import List

from app.core.database import get_db
from app.models.diaSemana import DiaSemana
from app.schemas.diaSemana import DiaSemanaCreate, DiaSemanaOut

router = APIRouter(prefix="/dias-semana", tags=["Días de semana"],dependencies=[Depends(get_current_user)],)

@router.post("/", response_model=list[DiaSemanaOut])
def crear_dias(
    payload: list[DiaSemanaCreate],
    db: Session = Depends(get_db)
):
    dias = [DiaSemana(**dia.model_dump()) for dia in payload]
    db.add_all(dias)
    db.commit()
    for dia in dias:
        db.refresh(dia)
    return dias

@router.get("/", response_model=List[DiaSemanaOut])
def listar_dias(db: Session = Depends(get_db)):
    rows = db.execute(select(DiaSemana).order_by(DiaSemana.id_dia)).scalars().all()
    return rows

