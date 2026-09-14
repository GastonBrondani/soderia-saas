from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import Conflict, NotFound
from app.features.repartos.camiones.models.camion_reparto import CamionReparto
from app.features.repartos.camiones.schemas import (
    CamionRepartoCreate,
    CamionRepartoUpdate,
)


def obtener_camion(db: Session, patente: str) -> CamionReparto:
    obj = db.get(CamionReparto, patente)
    if not obj:
        raise NotFound("Camión no encontrado.")
    return obj


def crear_camion(db: Session, payload: CamionRepartoCreate) -> CamionReparto:
    existing = db.get(CamionReparto, payload.patente)
    if existing:
        raise Conflict("Ya existe un camión con esa patente.")

    entity = CamionReparto(
        patente=payload.patente,
        id_empresa=payload.id_empresa,
        activo=payload.activo,
    )
    db.add(entity)
    try:
        db.commit()
        db.refresh(entity)
    except IntegrityError as e:
        db.rollback()
        raise Conflict(
            "No se pudo crear el camión. Verificá que la empresa exista y que la patente no esté duplicada."
        ) from e
    return entity


def listar_camiones(db: Session, activo: Optional[bool] = None) -> list[CamionReparto]:
    stmt = select(CamionReparto).order_by(CamionReparto.patente)
    if activo is not None:
        stmt = stmt.where(CamionReparto.activo == activo)
    return db.execute(stmt).scalars().all()


def actualizar_camion(db: Session, patente: str, payload: CamionRepartoUpdate) -> CamionReparto:
    entity = obtener_camion(db, patente)

    data = payload.model_dump(exclude_unset=True)

    if "id_empresa" in data:
        entity.id_empresa = data["id_empresa"]
    if "activo" in data:
        entity.activo = data["activo"]

    try:
        db.commit()
        db.refresh(entity)
    except IntegrityError as e:
        db.rollback()
        raise Conflict(
            "No se pudo actualizar el camión. Verificá la empresa o los datos enviados."
        ) from e

    return entity


def eliminar_camion(db: Session, patente: str) -> None:
    entity = obtener_camion(db, patente)

    try:
        db.delete(entity)
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise Conflict(
            "No se puede eliminar el camión porque está siendo utilizado en otra parte."
        ) from e
