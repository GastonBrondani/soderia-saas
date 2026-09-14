# app/api/routers/auth.py
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import Unauthorized
from app.core.security import (
    create_access_token,
    hash_password,
    necesita_rehash,
    verify_password,
)
from app.core.tenancy import tenant_actual
from app.features.usuarios.models.usuario import Usuario
from app.features.usuarios.models.usuario_rol import UsuarioRol
from app.features.usuarios.models.rol import Rol
from app.features.auth.schemas import LoginRequest, LoginResponse
from fastapi.security import OAuth2PasswordRequestForm

router = APIRouter(prefix="/auth", tags=["Auth"])


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
        raise Unauthorized("Credenciales inválidas.")

    # 2) Verificar contraseña
    if not verify_password(payload.contrasena, user.contrasena):
        raise Unauthorized("Credenciales inválidas.")

    # Hashes viejos (100.000 iteraciones) se migran solos al login.
    if necesita_rehash(user.contrasena):
        user.contrasena = hash_password(payload.contrasena)
        db.commit()

    # 3) Roles del usuario
    roles = (
        db.query(Rol.nombre)
        .join(UsuarioRol, UsuarioRol.id_rol == Rol.id_rol)
        .filter(UsuarioRol.id_usuario == user.id_usuario)
        .all()
    )
    roles_list = [r[0] for r in roles] if roles else []

    # 4) Crear token con roles
    access_token = create_access_token(
        id_usuario=user.id_usuario,
        nombre_usuario=user.nombre_usuario,
        roles=roles_list,
        tenant_codigo=tenant_actual().codigo,
    )

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
        raise Unauthorized("Credenciales inválidas.")

    # 2) Verificar contraseña
    if not verify_password(contrasena, user.contrasena):
        raise Unauthorized("Credenciales inválidas.")

    # Hashes viejos (100.000 iteraciones) se migran solos al login.
    if necesita_rehash(user.contrasena):
        user.contrasena = hash_password(contrasena)
        db.commit()

    # 3) Roles
    roles = (
        db.query(Rol.nombre)
        .join(UsuarioRol, UsuarioRol.id_rol == Rol.id_rol)
        .filter(UsuarioRol.id_usuario == user.id_usuario)
        .all()
    )
    roles_list = [r[0] for r in roles] if roles else []

    # 4) Token con roles
    access_token = create_access_token(
        id_usuario=user.id_usuario,
        nombre_usuario=user.nombre_usuario,
        roles=roles_list,
        tenant_codigo=tenant_actual().codigo,
    )

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        id_usuario=user.id_usuario,
        nombre_usuario=user.nombre_usuario,
        roles=roles_list,
    )