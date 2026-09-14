from sqlalchemy.orm import Session
from sqlalchemy import select, delete

from app.core.exceptions import Conflict, NotFound
from app.features.personas.models.persona import Persona
from app.features.personas.schemas import PersonaCreate, PersonaUpdate


def listar_personas(db: Session) -> list[Persona]:
    return db.query(Persona).all()


def obtener_persona(db: Session, dni: int) -> Persona:
    persona = db.get(Persona, dni)
    if not persona:
        raise NotFound("Persona no encontrada.")
    return persona


def crear_persona(db: Session, data: PersonaCreate) -> Persona:
    if db.get(Persona, data.dni):
        raise Conflict("Ya existe la persona con ese DNI.")
    persona = Persona(**data.model_dump())
    db.add(persona)
    db.commit()
    db.refresh(persona)
    return persona


def actualizar_persona(db: Session, dni: int, data: PersonaUpdate) -> Persona:
    persona = obtener_persona(db, dni)
    for campo, valor in data.model_dump(exclude_unset=True).items():
        setattr(persona, campo, valor)
    db.commit()
    db.refresh(persona)
    return persona


def eliminar_persona(db: Session, dni: int) -> None:
    existe = db.execute(
        select(Persona.dni).where(Persona.dni == dni).limit(1)
    ).scalar_one_or_none()
    if existe is None:
        raise NotFound("Persona no encontrada.")

    # Borro directo en SQL Core -> deja que la BD haga CASCADE
    db.execute(delete(Persona).where(Persona.dni == dni))
    db.commit()
