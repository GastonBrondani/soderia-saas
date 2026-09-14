from fastapi import APIRouter, Depends, status
from app.core.security import get_current_user
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.features.personas.schemas import PersonaCreate, PersonaOut, PersonaUpdate
from app.features.personas import service


router = APIRouter(prefix="/personas", tags=["Personas"],dependencies=[Depends(get_current_user)],)

@router.get("/",response_model=List[PersonaOut])
def ListarPersonas(db:Session=Depends(get_db)):
    return service.listar_personas(db)

@router.get("/{dni}",response_model=PersonaOut)
def BuscarPersona(dni:int,db:Session=Depends(get_db)):
    return service.obtener_persona(db, dni)

@router.post("/",response_model=PersonaOut,status_code=status.HTTP_201_CREATED)
def CrearPersona(data:PersonaCreate,db:Session=Depends(get_db)):
    return service.crear_persona(db, data)

@router.put("/{dni}",response_model=PersonaOut)
def ActualizarPersona(dni:int,data:PersonaUpdate,db:Session=Depends(get_db)):
    return service.actualizar_persona(db, dni, data)

@router.delete("/{dni}",status_code=status.HTTP_204_NO_CONTENT)
def EliminarPersona(dni:int,db:Session=Depends(get_db)):
    service.eliminar_persona(db, dni)
    return None
