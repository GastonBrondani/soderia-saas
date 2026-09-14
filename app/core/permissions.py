"""
Autorizacion por roles.

Sale de security.py para que ese archivo quede solo con criptografia y
tokens. La diferencia importa: security responde "quien sos", permissions
responde "que podes hacer".

Uso en un router:

    router = APIRouter(
        prefix="/caja",
        dependencies=[Depends(require_roles("ADMIN", "CAJERO"))],
    )

Uso en un endpoint puntual:

    @router.delete("/{id}")
    def borrar(id: int, user: CurrentUser = Depends(require_admin)):
        ...
"""

from __future__ import annotations

import hmac
from typing import Callable

from fastapi import Depends, Header

from app.core.config import settings
from app.core.exceptions import Forbidden, Unauthorized
from app.core.security import CurrentUser, get_current_user


def require_roles(*permitidos: str) -> Callable[..., CurrentUser]:
    """Exige al menos uno de los roles indicados."""
    requeridos = {rol.upper() for rol in permitidos}

    def dependency(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if requeridos and not user.tiene_rol(*requeridos):
            raise Forbidden(
                f"Requiere alguno de estos roles: {', '.join(sorted(requeridos))}."
            )
        return user

    return dependency


def require_all_roles(*requeridos_todos: str) -> Callable[..., CurrentUser]:
    """Exige TODOS los roles indicados."""
    requeridos = {rol.upper() for rol in requeridos_todos}

    def dependency(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        propios = {r.upper() for r in user.roles}
        faltantes = requeridos - propios
        if faltantes:
            raise Forbidden(f"Faltan roles: {', '.join(sorted(faltantes))}.")
        return user

    return dependency


def require_admin(
    user: CurrentUser = Depends(require_roles("ADMIN")),
) -> CurrentUser:
    return user


# ----------------------------------------------------------------------
# Administracion de la plataforma
# ----------------------------------------------------------------------


def require_platform_admin(
    x_platform_token: str | None = Header(default=None, alias="X-Platform-Token"),
) -> None:
    """Protege los endpoints de alta y baja de soderias.

    No usa el sistema de usuarios: esos viven dentro de la base de cada
    sodería, y quien administra la plataforma esta por encima de todas.
    Es un token estatico en el .env, comparado en tiempo constante.

    Para un SaaS chico alcanza. Cuando tengas un panel de administracion
    de verdad, reemplazalo por usuarios propios en el control plane.
    """
    esperado = settings.PLATFORM_ADMIN_TOKEN
    if not esperado:
        raise Forbidden("La administracion de plataforma esta deshabilitada.")
    if not x_platform_token or not hmac.compare_digest(x_platform_token, esperado):
        raise Unauthorized("Token de plataforma invalido.")
