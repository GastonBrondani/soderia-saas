# app/core/security.py
from __future__ import annotations
import hashlib
import hmac
import secrets
import os
from dataclasses import dataclass
from typing import List

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.usuario import Usuario


ALGORITHM = "pbkdf2_sha256"
ITERATIONS = 100_000

SECRET_KEY = os.getenv(
    "SECRET_KEY", "CAMBIA_ESTA_CLAVE_POR_ALGO_LARGO_Y_SECRETO"
)
JWT_ALGORITHM = "HS256"


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


@dataclass
class CurrentUser:
    id_usuario: int
    nombre_usuario: str
    roles: List[str]


def hash_password(raw: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        raw.encode("utf-8"),
        salt.encode("utf-8"),
        ITERATIONS,
    )
    return f"{ALGORITHM}${ITERATIONS}${salt}${dk.hex()}"


def verify_password(raw: str, hashed: str) -> bool:
    try:
        algorithm, iterations_str, salt, hash_hex = hashed.split("$", 3)
    except ValueError:
        return False

    if algorithm != ALGORITHM:
        return False

    try:
        iterations = int(iterations_str)
    except ValueError:
        return False

    new_dk = hashlib.pbkdf2_hmac(
        "sha256",
        raw.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    )
    return hmac.compare_digest(new_dk.hex(), hash_hex)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> CurrentUser:
    cred_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
        sub = payload.get("sub")
        nombre_usuario = payload.get("nombre_usuario")
    except JWTError:
        raise cred_exc

    if sub is None or nombre_usuario is None:
        raise cred_exc

    try:
        user_id = int(sub)
    except (TypeError, ValueError):
        raise cred_exc

    user: Usuario | None = db.get(Usuario, user_id)
    if user is None:
        raise cred_exc

    # SIEMPRE leer roles actuales desde DB
    roles = [ur.rol.nombre for ur in user.usuario_roles] if user.usuario_roles else []

    return CurrentUser(
        id_usuario=user.id_usuario,
        nombre_usuario=user.nombre_usuario,
        roles=roles,
    )


def require_roles(*permitidos: str):
    permitidos_set = {rol.upper() for rol in permitidos}

    def wrapper(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        user_roles = {rol.upper() for rol in user.roles}

        if permitidos_set and not user_roles.intersection(permitidos_set):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para esta operación.",
            )
        return user

    return wrapper


def require_admin(user: CurrentUser = Depends(require_roles("ADMIN"))) -> CurrentUser:
    return user
