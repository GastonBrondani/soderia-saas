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

from typing import Callable

from fastapi import Depends

from app.core.exceptions import Forbidden
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
