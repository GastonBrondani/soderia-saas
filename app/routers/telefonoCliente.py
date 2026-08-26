from fastapi import APIRouter, Depends, HTTPException,status
from app.core.security import get_current_user
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.core.database import get_db
from app.models.telefonoCliente import TelefonoCliente
from app.api.deps import get_cliente_or_404_dep
from app.schemas.telefonoCliente import TelefonoClienteCreate, TelefonoClienteUpdate, TelefonoClienteOut
from typing import List

router = APIRouter(prefix="/clientes/{legajo}/telefonos", tags=["Teléfonos Cliente"],dependencies=[Depends(get_current_user)],)



@router.get("/", response_model=List[TelefonoClienteOut])
def ListarTelefonos(legajo: int, db: Session = Depends(get_db)):
    get_cliente_or_404_dep(legajo, db)
    rows = db.execute(select(TelefonoCliente).where(TelefonoCliente.legajo == legajo).order_by(TelefonoCliente.id_telefono)).scalars().all()
    return rows

@router.post("/", response_model=TelefonoClienteOut,status_code=status.HTTP_201_CREATED)
def CrearTelefono(legajo:int, playload:TelefonoClienteCreate, db:Session=Depends(get_db)):
    get_cliente_or_404_dep(legajo, db)    
    
    nuevo= TelefonoCliente(legajo=legajo,
                          nro_telefono=playload.nro_telefono,
                          estado=playload.estado,
                          observacion=playload.observacion)
    db.add(nuevo)
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400,detail="El teléfono ya existe para este cliente") from e 
    db.refresh(nuevo)
    return nuevo

@router.put("/{id_telefono}", response_model=TelefonoClienteOut)
def ActualizarTelefono(legajo:int, id_telefono:int, playload:TelefonoClienteUpdate, db:Session=Depends(get_db)):
    get_cliente_or_404_dep(legajo, db)    
    obj=db.get(TelefonoCliente,id_telefono)
    if not obj or obj.legajo != legajo:
        raise HTTPException(status_code=404,detail="Teléfono no encontrado para este cliente.")
    
    data=playload.model_dump(exclude_unset=True)

    for k,v in data.items():
        setattr(obj,k,v)
    
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400,detail="El teléfono ya existe para este cliente") from e
    db.refresh(obj)
    return obj

@router.delete("/{id_telefono}", status_code=status.HTTP_204_NO_CONTENT)
def EliminarTelefono(legajo:int, id_telefono:int, db:Session=Depends(get_db)):
    get_cliente_or_404_dep(legajo, db)
    obj=db.get(TelefonoCliente,id_telefono)
    if not obj or obj.legajo != legajo:
        raise HTTPException(status_code=404,detail="Teléfono no encontrado para este cliente.")
    
    db.delete(obj)
    db.commit()
    return None

