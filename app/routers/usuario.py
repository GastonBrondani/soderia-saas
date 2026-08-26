# app/api/routers/usuarios.py
from __future__ import annotations

from sqlalchemy import select
from fastapi import APIRouter, Depends, HTTPException, status
from app.core.security import get_current_user
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import hash_password
from app.models.usuario import Usuario
from app.schemas.usuario import UsuarioCreate, UsuarioOut

router = APIRouter(prefix="/usuarios", tags=["Usuarios"],dependencies=[Depends(get_current_user)],)


@router.post("/", response_model=UsuarioOut, status_code=status.HTTP_201_CREATED)
def crear_usuario(payload: UsuarioCreate, db: Session = Depends(get_db)):
    hashed = hash_password(payload.contrasena)
    entity = Usuario(
        nombre_usuario=payload.nombre_usuario,
        contrasena=hashed,
        legajo_empleado=payload.legajo_empleado,
        legajo_cliente=payload.legajo_cliente,
    )
    try:
        db.add(entity)
        db.commit()
        db.refresh(entity)
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="No se pudo crear el usuario (duplicado o FK inválida).",
        ) from e
    return entity


@router.get("/", response_model=list[UsuarioOut])
def listar_usuarios(db: Session = Depends(get_db)):
    stmt = select(Usuario)
    result = db.scalars(stmt).all()
    return result


@router.get("/{id_usuario}", response_model=UsuarioOut)
def obtener_usuario(id_usuario: int, db: Session = Depends(get_db)):
    entity = db.get(Usuario, id_usuario)
    if not entity:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return entity
