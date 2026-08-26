from fastapi import APIRouter, Depends, HTTPException,status
from app.core.security import get_current_user
from typing import List
from sqlalchemy.orm import Session,selectinload
from sqlalchemy import select
from app.core.database import get_db
from app.models.empleado import Empleado
from app.models.persona import Persona
from app.schemas.empleado import EmpleadoCreate, EmpleadoOut, EmpleadoUpdate


router = APIRouter(prefix="/empleados", tags=["Empleados"],dependencies=[Depends(get_current_user)],)

@router.post("/", response_model=EmpleadoOut, status_code=status.HTTP_201_CREATED)
def CrearEmpleado(payload: EmpleadoCreate, db: Session = Depends(get_db)):
    try:
        # Resolver DNI final coherente
        dni_final = payload.persona.dni if payload.persona else payload.dni
        
        persona = db.get(Persona, dni_final)
        if payload.persona:
            if not persona:
                persona = Persona(**payload.persona.model_dump())
                db.add(persona)
            else:
                # Si quisieras sincronizar nombre/apellido si vinieran distintos, podrías actualizar acá
                pass
        else:
            if not persona:
                raise HTTPException(status_code=404, detail="La persona (dni) no existe. Envía 'persona' para crearla.")

        # Evitar duplicado por regla de negocio (dni, id_empresa)
        duplicado = db.execute(
            select(Empleado).where(
                Empleado.dni == dni_final,
                Empleado.id_empresa == 1
            )
        ).scalar_one_or_none()
        if duplicado:
            raise HTTPException(status_code=409, detail="Ya existe un empleado para ese DNI en esa empresa.")
        
        nuevo = Empleado(
            id_empresa=1, #Es uno porque ya cree la empresa y tiene id 1
            dni=dni_final,
            fecha_ingreso=payload.fecha_ingreso
        )
        db.add(nuevo)
        db.commit()
        db.refresh(nuevo)
        
        nuevo.persona = persona
        return nuevo

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creando empleado: {e}")
    
@router.get("/", response_model=List[EmpleadoOut])
def ListarEmpleados(db: Session = Depends(get_db),):
        return db.query(Empleado).options(selectinload(Empleado.persona)).all()

@router.get("/{legajo}", response_model=EmpleadoOut)
def BuscarEmpleado(legajo: int, db: Session = Depends(get_db)):
    empleado = (
        db.query(Empleado)
        .options(selectinload(Empleado.persona))
        .filter(Empleado.legajo == legajo)
        .first()
    )
    if not empleado:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    return empleado

@router.put("/{legajo}", response_model=EmpleadoOut)
def ActualizarEmpleado(legajo: int, payload: EmpleadoUpdate, db: Session = Depends(get_db)):
    try:
        empleado = db.get(Empleado, legajo)
        if not empleado:
            raise HTTPException(status_code=404, detail="Empleado no encontrado")

        # dump parcial, EXCLUYENDO id_empresa para que jamás lo toquemos
        data_empleado = payload.model_dump(
            exclude_unset=True,
            exclude={"id_empresa"}
        )
        persona_patch = data_empleado.pop("persona", None)

        # setear solo campos con valor NO None (evita overwrites a NULL)
        for campo, valor in data_empleado.items():
            if valor is not None:
                setattr(empleado, campo, valor)

        if persona_patch:
            persona = db.get(Persona, empleado.dni)
            if not persona:
                raise HTTPException(status_code=409, detail="Inconsistencia: el empleado no tiene persona asociada.")
            for campo, valor in persona_patch.items():
                if valor is not None:
                    setattr(persona, campo, valor)
        db.commit()
        # asegurar persona en salida
        empleado = (
            db.query(Empleado)
              .options(selectinload(Empleado.persona))
              .filter(Empleado.legajo == legajo)
              .first()
        )
        return empleado
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error actualizando empleado: {e}")

@router.delete("/{legajo}", status_code=status.HTTP_204_NO_CONTENT)
def EliminarEmpleado(legajo: int, db: Session = Depends(get_db)):
    try:
        empleado = db.query(Empleado).filter(Empleado.legajo == legajo).first()
        if not empleado:
            raise HTTPException(status_code=404, detail="Empleado no encontrado")
        
        db.delete(empleado)
        db.commit()
        return

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error eliminando empleado: {e}")