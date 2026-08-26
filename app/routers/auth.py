# app/api/routers/auth.py
from __future__ import annotations
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from jose import jwt
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import (
    verify_password,
    SECRET_KEY,
    JWT_ALGORITHM,
)
from app.models.usuario import Usuario
from app.models.usuarioRol import UsuarioRol
from app.models.rol import Rol
from app.schemas.auth import LoginRequest, LoginResponse
from fastapi.security import OAuth2PasswordRequestForm

router = APIRouter(prefix="/auth", tags=["Auth"])

# En la práctica estos valores deberían venir de tu .env
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 1 día, cambia a gusto


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    # 1) Buscar usuario por nombre_usuario
    user: Usuario | None = (
        db.query(Usuario)
        .filter(Usuario.nombre_usuario == payload.nombre_usuario.strip())
        .first()
    )
    if not user:
        # No revelamos si falló usuario o pass
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas.",
        )

    # 2) Verificar contraseña
    if not verify_password(payload.contrasena, user.contrasena):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas.",
        )

    # 3) Roles del usuario
    roles = (
        db.query(Rol.nombre)
        .join(UsuarioRol, UsuarioRol.id_rol == Rol.id_rol)
        .filter(UsuarioRol.id_usuario == user.id_usuario)
        .all()
    )
    roles_list = [r[0] for r in roles] if roles else []

    # 4) Crear token con roles
    token_data = {
        "sub": str(user.id_usuario),
        "nombre_usuario": user.nombre_usuario,
        "roles": roles_list,
    }
    access_token = create_access_token(token_data)

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        id_usuario=user.id_usuario,
        nombre_usuario=user.nombre_usuario,
        roles=roles_list,
    )


@router.post("/token", response_model=LoginResponse)
def token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    # Swagger manda "username" y "password"
    nombre_usuario = form_data.username.strip()
    contrasena = form_data.password

    # 1) Buscar usuario
    user: Usuario | None = (
        db.query(Usuario)
        .filter(Usuario.nombre_usuario == nombre_usuario)
        .first()
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas.",
        )

    # 2) Verificar contraseña
    if not verify_password(contrasena, user.contrasena):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas.",
        )

    # 3) Roles
    roles = (
        db.query(Rol.nombre)
        .join(UsuarioRol, UsuarioRol.id_rol == Rol.id_rol)
        .filter(UsuarioRol.id_usuario == user.id_usuario)
        .all()
    )
    roles_list = [r[0] for r in roles] if roles else []

    # 4) Token con roles
    token_data = {
        "sub": str(user.id_usuario),
        "nombre_usuario": user.nombre_usuario,
        "roles": roles_list,
    }
    access_token = create_access_token(token_data)

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        id_usuario=user.id_usuario,
        nombre_usuario=user.nombre_usuario,
        roles=roles_list,
    )