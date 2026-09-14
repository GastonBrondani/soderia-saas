"""
Hashing de contraseñas y JWT.

Cambios respecto del security.py actual:

  1. SECRET_KEY sale de settings (sin fallback inseguro).
  2. create_access_token vive aca, no en el router de auth.
  3. El token lleva el claim `ten` con el codigo de la sodería. Si el token
     no coincide con el tenant del request, se rechaza. Un token de una
     sodería no sirve para pegarle a otra.
  4. El token lleva `iat` y `jti`, necesarios para poder revocar sesiones.

Lo que NO cambia: el formato de hash pbkdf2_sha256$...$...$... queda igual.
Tus usuarios actuales siguen entrando con su contraseña. Al final del archivo
hay una nota sobre como migrar a argon2 sin resetear contraseñas.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import TenantMismatch, Unauthorized
from app.core.tenancy import tenant_actual

# ----------------------------------------------------------------------
# Hashing
# ----------------------------------------------------------------------

ALGORITHM = "pbkdf2_sha256"
ITERATIONS = 210_000  # OWASP 2023 para pbkdf2-sha256. Antes: 100_000.


def hash_password(raw: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac(
        "sha256", raw.encode("utf-8"), salt.encode("utf-8"), ITERATIONS
    )
    return f"{ALGORITHM}${ITERATIONS}${salt}${dk.hex()}"


def verify_password(raw: str, hashed: str) -> bool:
    try:
        algoritmo, iteraciones_str, salt, hash_hex = hashed.split("$", 3)
    except (ValueError, AttributeError):
        return False

    if algoritmo != ALGORITHM:
        return False

    try:
        iteraciones = int(iteraciones_str)
    except ValueError:
        return False

    nuevo = hashlib.pbkdf2_hmac(
        "sha256", raw.encode("utf-8"), salt.encode("utf-8"), iteraciones
    )
    return hmac.compare_digest(nuevo.hex(), hash_hex)


def necesita_rehash(hashed: str) -> bool:
    """True si el hash usa menos iteraciones que las actuales.

    Se usa en el login: si la contraseña es correcta pero el hash es viejo,
    se regenera con las iteraciones nuevas. La actualizacion es transparente
    y no requiere que el usuario cambie nada.
    """
    try:
        algoritmo, iteraciones_str, _, _ = hashed.split("$", 3)
        return algoritmo != ALGORITHM or int(iteraciones_str) < ITERATIONS
    except (ValueError, AttributeError):
        return True


# ----------------------------------------------------------------------
# JWT
# ----------------------------------------------------------------------

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token", auto_error=False)


def create_access_token(
    *,
    id_usuario: int,
    nombre_usuario: str,
    roles: list[str],
    tenant_codigo: str,
    expires_delta: timedelta | None = None,
    extra: dict[str, Any] | None = None,
) -> str:
    ahora = datetime.now(timezone.utc)
    expira = ahora + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload: dict[str, Any] = {
        "sub": str(id_usuario),
        "nombre_usuario": nombre_usuario,
        "roles": roles,
        "ten": tenant_codigo,  # <- el claim que ata el token a una sodería
        "iat": ahora,
        "exp": expira,
        "jti": uuid.uuid4().hex,
        "typ": "access",
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
    except JWTError as exc:
        raise Unauthorized("Token invalido o vencido.") from exc


# ----------------------------------------------------------------------
# Usuario autenticado
# ----------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CurrentUser:
    id_usuario: int
    nombre_usuario: str
    roles: list[str] = field(default_factory=list)
    tenant_codigo: str = ""

    def tiene_rol(self, *nombres: str) -> bool:
        propios = {r.upper() for r in self.roles}
        return bool(propios & {n.upper() for n in nombres})

    @property
    def es_admin(self) -> bool:
        return self.tiene_rol("ADMIN")


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> CurrentUser:
    if not token:
        raise Unauthorized("Falta el token de acceso.")

    payload = decode_token(token)

    if payload.get("typ") not in (None, "access"):
        raise Unauthorized("Tipo de token incorrecto.")

    sub = payload.get("sub")
    nombre_usuario = payload.get("nombre_usuario")
    if sub is None or nombre_usuario is None:
        raise Unauthorized()

    # El token tiene que ser de esta sodería.
    tenant = tenant_actual()
    codigo_token = payload.get("ten")
    if codigo_token is None:
        # Token emitido antes de la migracion. En dev se tolera para no
        # romper sesiones abiertas; en prod se rechaza.
        if settings.is_prod:
            raise Unauthorized("Token sin identificacion de sodería. Volve a entrar.")
    elif codigo_token != tenant.codigo:
        raise TenantMismatch()

    try:
        user_id = int(sub)
    except (TypeError, ValueError):
        raise Unauthorized()

    # Import diferido: el modelo vive en features/ y features importa core.
    # Hacerlo arriba crearia un ciclo.
    # TODO migracion paso 2: from app.features.usuarios.models import Usuario
    from app.models.usuario import Usuario

    usuario = db.get(Usuario, user_id)
    if usuario is None:
        raise Unauthorized()

    # Los roles se leen de la base, no del token: si le sacas el rol ADMIN a
    # alguien, deja de ser admin ya mismo y no cuando venza su token.
    roles = [ur.rol.nombre for ur in usuario.usuario_roles] if usuario.usuario_roles else []

    return CurrentUser(
        id_usuario=usuario.id_usuario,
        nombre_usuario=usuario.nombre_usuario,
        roles=roles,
        tenant_codigo=tenant.codigo,
    )


def get_current_user_opcional(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> CurrentUser | None:
    if not token:
        return None
    try:
        return get_current_user(token=token, db=db)
    except Unauthorized:
        return None


# ----------------------------------------------------------------------
# Nota sobre migrar a argon2
# ----------------------------------------------------------------------
# pbkdf2 esta bien, pero argon2id es mejor contra ataques con GPU. Se migra
# sin resetear contraseñas:
#   1. Agregar argon2-cffi y una funcion verify que detecte el prefijo del
#      hash ("$argon2id$" vs "pbkdf2_sha256$") y use el verificador que toque.
#   2. En el login, si la contraseña es correcta y el hash es pbkdf2,
#      regenerarlo con argon2 y guardarlo.
#   3. A los pocos meses, todos los usuarios activos quedaron migrados.
# Es el mismo mecanismo que ya implementa necesita_rehash() de arriba.
