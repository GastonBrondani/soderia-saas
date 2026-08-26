from fastapi import APIRouter, Depends, HTTPException,status
from app.core.security import get_current_user
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.core.database import get_db 
from app.models.direccionCliente import DireccionCliente
from app.api.deps import get_cliente_or_404_dep
from app.schemas.direccionCliente import DireccionClienteCreate, DireccionClienteUpdate, DireccionClienteOut
from typing import List

router = APIRouter(prefix="/clientes/{legajo}/direcciones", tags=["Direcciones Cliente"],dependencies=[Depends(get_current_user)],)

@router.get("/", response_model=List[DireccionClienteOut])
def ListarDirecciones(legajo: int, db: Session = Depends(get_db)):
    get_cliente_or_404_dep(legajo, db)
    rows = db.execute(select(DireccionCliente).where(DireccionCliente.legajo == legajo).order_by(DireccionCliente.id_direccion)).scalars().all()
    return rows

@router.post("/", response_model=DireccionClienteOut,status_code=status.HTTP_201_CREATED)
def CrearDireccion(legajo:int, playload:DireccionClienteCreate, db:Session=Depends(get_db)):
    get_cliente_or_404_dep(legajo, db)    
    
    nuevo= DireccionCliente(legajo=legajo,
                          localidad=playload.localidad,
                          direccion=playload.direccion,
                          zona=playload.zona,
                            entre_calle1=playload.entre_calle1,
                          entre_calle2=playload.entre_calle2,
                            observacion=playload.observacion,
                            tipo=playload.tipo,
                            latitud_longitud=playload.latitud_longitud)
    db.add(nuevo)
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400,detail="Error al crear la dirección para este cliente") from e
    db.refresh(nuevo)
    return nuevo

@router.put("/{id_direccion}", response_model=DireccionClienteOut)
def ActualizarDireccion(legajo:int, id_direccion:int, playload:DireccionClienteUpdate, db:Session=Depends(get_db)):
    get_cliente_or_404_dep(legajo, db)    
    obj=db.get(DireccionCliente,id_direccion)
    if not obj or obj.legajo != legajo:
        raise HTTPException(status_code=404,detail="Dirección no encontrada para este cliente.")
    
    data=playload.model_dump(exclude_unset=True)
    for k,v in data.items():
        setattr(obj,k,v)
    
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400,detail="Error al actualizar la dirección para este cliente") from e
    db.refresh(obj)
    return obj

@router.delete("/{id_direccion}", status_code=status.HTTP_204_NO_CONTENT)
def EliminarDireccion(legajo:int, id_direccion:int, db:Session=Depends(get_db)):
    get_cliente_or_404_dep(legajo, db)
    obj=db.get(DireccionCliente,id_direccion)
    if not obj or obj.legajo != legajo:
        raise HTTPException(status_code=404,detail="Dirección no encontrada para este cliente.")
    db.delete(obj)
    db.commit()
    return

