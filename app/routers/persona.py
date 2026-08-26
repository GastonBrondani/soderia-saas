from fastapi import APIRouter,Depends,HTTPException,status
from app.core.security import get_current_user
from sqlalchemy.orm import Session
from typing import List
from sqlalchemy import select, delete

from app.core.database import get_db
from app.models.persona import Persona
from app.schemas.persona import PersonaCreate,PersonaOut,PersonaUpdate


router = APIRouter(prefix="/personas", tags=["Personas"],dependencies=[Depends(get_current_user)],)

@router.get("/",response_model=List[PersonaOut])
def ListarPersonas(db:Session=Depends(get_db)):
    return db.query(Persona).all()

@router.get("/{dni}",response_model=PersonaOut)
def BuscarPersona(dni:int,db:Session=Depends(get_db)):
    persona = db.get(Persona,dni)
    if not persona:
        raise HTTPException(status_code=404,detail="Persona no encontrada.")
    return persona

@router.post("/",response_model=PersonaOut,status_code=status.HTTP_201_CREATED)
def CrearPersona(data:PersonaCreate,db:Session=Depends(get_db)):
    if db.get(Persona,data.dni):
        raise HTTPException(status_code=409,detail="Ya existe la persona con ese DNI.")
    persona=Persona(**data.model_dump())
    db.add(persona)
    db.commit()
    db.refresh(persona)
    return persona

@router.put("/{dni}",response_model=PersonaOut)
def ActualizarPersona(dni:int,data:PersonaUpdate,db:Session=Depends(get_db)):
    persona = db.get(Persona,dni)
    if not persona:
        raise HTTPException(status_code=404,detail="Persona no encontrada.")
    for campo,valor in data.model_dump(exclude_unset=True).items():
        setattr(persona,campo,valor)
    db.commit()
    db.refresh(persona)
    return persona

@router.delete("/{dni}",status_code=status.HTTP_204_NO_CONTENT)
def EliminarPersona(dni:int,db:Session=Depends(get_db)):
    existe = db.execute(
        select(Persona.dni).where(Persona.dni == dni).limit(1)
    ).scalar_one_or_none()
    if existe is None:
        raise HTTPException(status_code=404, detail="Persona no encontrada")

    # 2) Borro directo en SQL Core -> deja que la BD haga CASCADE
    db.execute(delete(Persona).where(Persona.dni == dni))
    db.commit()
    return None



                

