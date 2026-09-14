from fastapi import APIRouter, Depends
from app.core.security import get_current_user
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.exceptions import NotFound
from app.features.repartos.recorridos.schemas import RecorridoCreate, RecorridoOut
from app.features.repartos.recorridos.service import RecorridoService
from app.features.repartos.recorridos.models.recorrido import Recorrido

router = APIRouter(prefix="/recorridos", tags=["Recorrido"],dependencies=[Depends(get_current_user)],)

@router.post("/", response_model=RecorridoOut, status_code=201)
def abrir_recorrido(payload: RecorridoCreate, db: Session = Depends(get_db)):
    return RecorridoService.abrir_recorrido(db, payload)


#Devolver todos el recorrido para ver si se creo bien. Es para ver si anda, no se utiliza.
@router.get("/recorridos/{id_recorrido}", response_model=RecorridoOut)
def get_recorrido(id_recorrido: int, db: Session = Depends(get_db)):
    recorrido = db.get(Recorrido, id_recorrido)
    if not recorrido:
        raise NotFound("Recorrido no encontrado")
    return recorrido
