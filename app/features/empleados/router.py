from fastapi import APIRouter, Depends, status
from app.core.security import get_current_user
from typing import List
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.features.empleados.schemas import EmpleadoCreate, EmpleadoOut, EmpleadoUpdate
from app.features.empleados import service


router = APIRouter(prefix="/empleados", tags=["Empleados"],dependencies=[Depends(get_current_user)],)

@router.post("/", response_model=EmpleadoOut, status_code=status.HTTP_201_CREATED)
def CrearEmpleado(payload: EmpleadoCreate, db: Session = Depends(get_db)):
    return service.crear_empleado(db, payload)

@router.get("/", response_model=List[EmpleadoOut])
def ListarEmpleados(db: Session = Depends(get_db)):
    return service.listar_empleados(db)

@router.get("/{legajo}", response_model=EmpleadoOut)
def BuscarEmpleado(legajo: int, db: Session = Depends(get_db)):
    return service.obtener_empleado(db, legajo)

@router.put("/{legajo}", response_model=EmpleadoOut)
def ActualizarEmpleado(legajo: int, payload: EmpleadoUpdate, db: Session = Depends(get_db)):
    return service.actualizar_empleado(db, legajo, payload)

@router.delete("/{legajo}", status_code=status.HTTP_204_NO_CONTENT)
def EliminarEmpleado(legajo: int, db: Session = Depends(get_db)):
    service.eliminar_empleado(db, legajo)
    return None
