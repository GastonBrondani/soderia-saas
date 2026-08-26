from fastapi import APIRouter, Depends, HTTPException,status
from app.core.security import get_current_user
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.core.database import get_db
from app.models.emailCliente import MailCliente
from app.api.deps import get_cliente_or_404_dep
from app.schemas.emailCliente import MailClienteCreate, MailClienteUpdate, MailClienteOut
from typing import List


router = APIRouter(prefix="/clientes/{legajo}/emails", tags=["Emails Cliente"],dependencies=[Depends(get_current_user)],)


@router.get("/", response_model=List[MailClienteOut])
def ListarEmails(legajo: int, db: Session = Depends(get_db)):
    get_cliente_or_404_dep(legajo, db)
    rows = db.execute(select(MailCliente).where(MailCliente.legajo == legajo).order_by(MailCliente.id_mail)).scalars().all()
    return rows

@router.post("/", response_model=MailClienteOut,status_code=status.HTTP_201_CREATED)
def CrearEmail(legajo:int, playload:MailClienteCreate, db:Session=Depends(get_db)):
    get_cliente_or_404_dep(legajo, db)    
    
    nuevo= MailCliente(legajo=legajo,mail=str(playload.mail).lower(),
                       estado=playload.estado,
                       observacion=playload.observacion)
    db.add(nuevo)
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400,detail="El email ya existe para este cliente") from e 
    db.refresh(nuevo)
    return nuevo

@router.put("/{id_mail}", response_model=MailClienteOut)
def ActualizarEmail(legajo:int, id_mail:int, playload:MailClienteUpdate, db:Session=Depends(get_db)):
    get_cliente_or_404_dep(legajo, db)
    obj=db.get(MailCliente,id_mail)
    if not obj or obj.legajo != legajo:
        raise HTTPException(status_code=404,detail="Email no encontrado para este cliente.")
    
    data=playload.model_dump(exclude_unset=True)
    if "mail" in data and data["mail"] is not None:
        data["mail"] = str(data["mail"]).lower()

    for k,v in data.items():
        setattr(obj,k,v)
    
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400,detail="El email ya existe para este cliente") from e
    db.refresh(obj)
    return obj

@router.delete("/{id_mail}",status_code=status.HTTP_204_NO_CONTENT)
def EliminarEmail(legajo:int, id_mail:int, db:Session=Depends(get_db)):
    get_cliente_or_404_dep(legajo, db)
    obj = db.get(MailCliente,id_mail)
    if not obj or obj.legajo != legajo:
        raise HTTPException(status_code=404,detail="Email no encontrado para este cliente.")
    db.delete(obj)
    db.commit()
    return None
