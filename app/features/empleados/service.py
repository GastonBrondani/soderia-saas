from typing import List

from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select

from app.core.exceptions import Conflict, NotFound
from app.features.empleados.models.empleado import Empleado
from app.features.empleados.schemas import EmpleadoCreate, EmpleadoUpdate
from app.features.personas.models.persona import Persona


def crear_empleado(db: Session, payload: EmpleadoCreate) -> Empleado:
    # Resolver DNI final coherente
    dni_final = payload.persona.dni if payload.persona else payload.dni

    persona = db.get(Persona, dni_final)
    if payload.persona:
        if not persona:
            persona = Persona(**payload.persona.model_dump())
            db.add(persona)
    else:
        if not persona:
            raise NotFound("La persona (dni) no existe. Envía 'persona' para crearla.")

    # Evitar duplicado por regla de negocio (dni, id_empresa)
    duplicado = db.execute(
        select(Empleado).where(
            Empleado.dni == dni_final,
            Empleado.id_empresa == 1,
        )
    ).scalar_one_or_none()
    if duplicado:
        raise Conflict("Ya existe un empleado para ese DNI en esa empresa.")

    nuevo = Empleado(
        id_empresa=1,  # Es uno porque ya cree la empresa y tiene id 1
        dni=dni_final,
        fecha_ingreso=payload.fecha_ingreso,
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)

    nuevo.persona = persona
    return nuevo


def listar_empleados(db: Session) -> List[Empleado]:
    return db.query(Empleado).options(selectinload(Empleado.persona)).all()


def obtener_empleado(db: Session, legajo: int) -> Empleado:
    empleado = (
        db.query(Empleado)
        .options(selectinload(Empleado.persona))
        .filter(Empleado.legajo == legajo)
        .first()
    )
    if not empleado:
        raise NotFound("Empleado no encontrado.")
    return empleado


def actualizar_empleado(db: Session, legajo: int, payload: EmpleadoUpdate) -> Empleado:
    empleado = db.get(Empleado, legajo)
    if not empleado:
        raise NotFound("Empleado no encontrado.")

    # dump parcial, EXCLUYENDO id_empresa para que jamás lo toquemos
    data_empleado = payload.model_dump(
        exclude_unset=True,
        exclude={"id_empresa"},
    )
    persona_patch = data_empleado.pop("persona", None)

    # setear solo campos con valor NO None (evita overwrites a NULL)
    for campo, valor in data_empleado.items():
        if valor is not None:
            setattr(empleado, campo, valor)

    if persona_patch:
        persona = db.get(Persona, empleado.dni)
        if not persona:
            raise Conflict("Inconsistencia: el empleado no tiene persona asociada.")
        for campo, valor in persona_patch.items():
            if valor is not None:
                setattr(persona, campo, valor)
    db.commit()

    return obtener_empleado(db, legajo)


def eliminar_empleado(db: Session, legajo: int) -> None:
    empleado = db.query(Empleado).filter(Empleado.legajo == legajo).first()
    if not empleado:
        raise NotFound("Empleado no encontrado.")

    db.delete(empleado)
    db.commit()
