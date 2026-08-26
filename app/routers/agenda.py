from fastapi import APIRouter, Depends
from app.core.security import get_current_user
from sqlalchemy.orm import Session


from app.core.database import get_db

from app.schemas.agenda import AgendaMoverIn
from app.services.agendaService import insertar_cliente_en_agenda


router = APIRouter(prefix="/agenda", tags=["Agenda"],dependencies=[Depends(get_current_user)],)

@router.post("/mover")
def mover_cliente_agenda(payload: AgendaMoverIn, db: Session = Depends(get_db)):
    try:
        insertar_cliente_en_agenda(
            db=db,
            id_cliente=payload.id_cliente,
            id_dia=payload.id_dia,
            turno=payload.turno,
            posicion=payload.posicion,
            despues_de_legajo=payload.despues_de_legajo,
        )
        db.commit()
        return {"ok": True}
    except Exception:
        db.rollback()
        raise


