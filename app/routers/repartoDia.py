from fastapi import APIRouter, Depends, status, Query
from app.core.security import get_current_user
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date

from app.core.database import get_db
from app.schemas.repartoDia import (
    RepartoDiaCreate, RepartoDiaUpdate, RepartoDiaOut, RegistrarCobroIn
)
from app.schemas.bootstrap import RepartoBootstrapOut
from app.services.repartoDiaService import RepartoDiaService
from app.services.bootstrapService import reparto_bootstrap

router = APIRouter(prefix="/repartos-dia", tags=["Reparto Día"],dependencies=[Depends(get_current_user)],)


# Offline sync: baja en una sola request el reparto del día + los clientes a
# visitar (dirección, teléfono, cuenta, saldo/deuda y estado de visita).
@router.get("/bootstrap", response_model=RepartoBootstrapOut)
def bootstrap_reparto_dia(
    fecha: date = Query(..., description="Fecha del reparto (YYYY-MM-DD)"),
    id_empresa: Optional[int] = Query(None, description="Empresa (opcional)"),
    db: Session = Depends(get_db),
):
    return reparto_bootstrap(db, fecha=fecha, id_empresa=id_empresa)

@router.post("/", response_model=RepartoDiaOut, status_code=status.HTTP_201_CREATED)

# Crear un nuevo reparto del día(Funciona)
def crear_reparto_dia(payload: RepartoDiaCreate, db: Session = Depends(get_db)):
    return RepartoDiaService.create(
        db,
        id_usuario=payload.id_usuario,
        id_empresa=payload.id_empresa,
        fecha=payload.fecha,
        observacion=payload.observacion,
    )


#Obtener un reparto del día por fecha (Funciona)
@router.get("/por-fecha", response_model=RepartoDiaOut)
def obtener_reparto_dia_por_fecha(
    fecha: date = Query(..., description="Fecha del reparto"),
    id_empresa: Optional[int] = Query(None, description="Empresa (opcional, pero recomendable)"),
    id_usuario: Optional[int] = Query(None, description="Usuario creador (opcional)"),
    db: Session = Depends(get_db),
):
    return RepartoDiaService.get_by_fecha(
        db,
        fecha=fecha,
        id_empresa=id_empresa,
        id_usuario=id_usuario,
    )
    
    
@router.get("/por-rango", response_model=List[RepartoDiaOut])
def listar_repartos_por_rango(
    fecha_desde: date = Query(..., description="Desde (inclusive)"),
    fecha_hasta: date = Query(..., description="Hasta (inclusive)"),
    id_empresa: Optional[int] = Query(None),
    id_usuario: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    return RepartoDiaService.listar_por_rango(
        db,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        id_empresa=id_empresa,
        id_usuario=id_usuario,
    )


@router.post("/{id_repartodia}/cerrar", response_model=RepartoDiaOut)
def cerrar_reparto_dia(id_repartodia: int, db: Session = Depends(get_db)):
    return RepartoDiaService.cerrar(db, id_repartodia=id_repartodia)

    
#--------------------------------------------
#Desabilitado por ahora el actulizar reparto del dia y eliminar
#@router.put("/{id_repartodia}", response_model=RepartoDiaOut)
#def actualizar_reparto_dia(
#    id_repartodia: int, payload: RepartoDiaUpdate, db: Session = Depends(get_db)
#):
#    return RepartoDiaService.update(
#        db,
#        id_repartodia=id_repartodia,
#        id_usuario=payload.id_usuario,
#        id_empresa=payload.id_empresa,
#        fecha=payload.fecha,
#        observacion=payload.observacion,
#    )

#@router.delete("/{id_repartodia}", status_code=status.HTTP_204_NO_CONTENT)
#def eliminar_reparto_dia(id_repartodia: int, db: Session = Depends(get_db)):
#    RepartoDiaService.delete(db, id_repartodia=id_repartodia)
#---------
#Desabilitado por ahora
#@router.post("/{id_repartodia}/registrar-cobro", response_model=RepartoDiaOut)
#def registrar_cobro(id_repartodia: int, payload: RegistrarCobroIn, db: Session = Depends(get_db)):
#    return RepartoDiaService.registrar_cobro(
#        db,
#        id_repartodia=id_repartodia,
#        efectivo=payload.efectivo,
#        virtual=payload.virtual,
#    )
