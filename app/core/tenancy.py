"""
Resolucion del tenant de cada request.

Esta es la pieza que reemplaza al `id_empresa: Optional[int] = Query(None)`
que hoy tenes repartido por repartoDia.py, cajaEmpresa.py y compania.
Ese parametro es lo que permite que un usuario de una sodería lea los datos
de otra. Con esto, el tenant deja de ser algo que el cliente elige y pasa a
ser algo que el servidor determina.

Orden de resolucion:
  1. Subdominio del Host           solmar.tuapp.com  -> solmar
  2. Header X-Tenant               X-Tenant: solmar
  3. DEFAULT_TENANT del .env       solo en desarrollo

El JWT ademas lleva el claim `ten`. Si el tenant del token no coincide con
el del request, se rechaza con 403: un token robado de una sodería no sirve
para pegarle a otra.
"""

from __future__ import annotations

import logging
from contextvars import ContextVar, Token

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import settings
from app.core.control_plane import TenantInfo, buscar_tenant
from app.core.exceptions import AppError, TenantNoResuelto

logger = logging.getLogger(__name__)

# El tenant del request en curso. Se usa ContextVar (no una global) para que
# cada request tenga el suyo, incluso con varios corriendo en paralelo.
_tenant_actual: ContextVar[TenantInfo | None] = ContextVar(
    "tenant_actual", default=None
)


# ----------------------------------------------------------------------
# Acceso al tenant desde cualquier capa
# ----------------------------------------------------------------------


def tenant_actual() -> TenantInfo:
    """El tenant del request en curso.

    Sirve dentro de services, repositories y jobs, sin tener que pasar el
    tenant como parametro por diez niveles de llamadas.
    """
    info = _tenant_actual.get()
    if info is None:
        raise TenantNoResuelto(
            "No hay tenant en el contexto. Si estas en un script o un job, "
            "envolve el codigo en `with usar_tenant(info):`."
        )
    return info


def tenant_actual_opcional() -> TenantInfo | None:
    return _tenant_actual.get()


def _set_tenant(info: TenantInfo | None) -> Token:
    return _tenant_actual.set(info)


def _reset_tenant(token: Token) -> None:
    _tenant_actual.reset(token)


class usar_tenant:
    """Context manager para fijar el tenant fuera de un request HTTP.

    Lo necesitan el scheduler, los scripts de mantenimiento y los tests:

        for t in listar_tenants():
            with usar_tenant(t):
                crear_repartos_del_dia_automaticos()
    """

    def __init__(self, info: TenantInfo) -> None:
        self._info = info
        self._token: Token | None = None

    def __enter__(self) -> TenantInfo:
        self._token = _set_tenant(self._info)
        return self._info

    def __exit__(self, *exc) -> None:
        if self._token is not None:
            _reset_tenant(self._token)
            self._token = None


# ----------------------------------------------------------------------
# Extraccion del codigo desde el request
# ----------------------------------------------------------------------

# Codigos que ninguna sodería puede tener: chocan con subdominios de
# infraestructura (www, api, admin, cdn...) o con nombres reservados de
# Postgres (postgres, template0/1, public). Fuente unica: crear_tenant.py
# valida el alta contra esta misma lista (antes eran dos listas separadas
# que podian divergir sin que nadie lo notara).
CODIGOS_RESERVADOS = frozenset({
    "www", "api", "admin", "app", "mail", "ftp", "static", "cdn", "assets",
    "postgres", "template0", "template1", "public", "control", "test",
})


def _codigo_desde_subdominio(host: str) -> str | None:
    # host puede venir con puerto: solmar.tuapp.com:8000
    host = host.split(":", 1)[0].strip().lower()
    if not host:
        return None

    base = settings.BASE_DOMAIN.strip().lower()
    if base and host.endswith("." + base):
        sub = host[: -(len(base) + 1)]
        # Descartar subdominios de infraestructura
        if sub and sub not in CODIGOS_RESERVADOS:
            # solo el primer nivel: a.b.tuapp.com -> a
            return sub.split(".")[0]
    return None


def _codigo_desde_header(request: Request) -> str | None:
    valor = request.headers.get(settings.TENANT_HEADER)
    if valor:
        return valor.strip().lower()
    return None


def resolver_codigo_tenant(request: Request) -> str | None:
    modo = settings.TENANT_RESOLUTION

    if modo in ("subdomain", "both"):
        codigo = _codigo_desde_subdominio(request.headers.get("host", ""))
        if codigo:
            return codigo

    if modo in ("header", "both"):
        codigo = _codigo_desde_header(request)
        if codigo:
            return codigo

    if settings.DEFAULT_TENANT:
        # Solo llega aca en dev: el validador de config lo prohibe en prod.
        return settings.DEFAULT_TENANT.strip().lower()

    return None


def _esta_exento(path: str) -> bool:
    return any(
        path == exento or path.startswith(exento.rstrip("/") + "/")
        for exento in settings.TENANT_EXEMPT_PATHS
    )


# ----------------------------------------------------------------------
# Middleware
# ----------------------------------------------------------------------


class TenantMiddleware(BaseHTTPMiddleware):
    """Resuelve el tenant antes de que corra cualquier endpoint.

    Va antes que la autenticacion a proposito: el login tambien necesita
    saber contra que base validar el usuario.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if _esta_exento(request.url.path):
            return await call_next(request)

        codigo = resolver_codigo_tenant(request)
        if not codigo:
            return _respuesta_error(
                TenantNoResuelto(
                    f"Identifica la sodería por subdominio o por el header "
                    f"{settings.TENANT_HEADER}."
                )
            )

        try:
            info = buscar_tenant(codigo)
        except AppError as exc:
            return _respuesta_error(exc)

        token = _set_tenant(info)
        # Disponible tambien como request.state.tenant para el logging.
        request.state.tenant = info
        try:
            respuesta = await call_next(request)
        finally:
            _reset_tenant(token)

        respuesta.headers["X-Tenant"] = info.codigo
        return respuesta


def _respuesta_error(exc: AppError) -> JSONResponse:
    # El middleware corre fuera del stack de exception handlers de FastAPI,
    # asi que la respuesta se arma a mano para mantener el mismo formato.
    return JSONResponse(status_code=exc.status_code, content=exc.to_dict())


# ----------------------------------------------------------------------
# Dependency para routers
# ----------------------------------------------------------------------


def get_tenant() -> TenantInfo:
    """Inyecta el tenant en un endpoint que necesite mostrarlo.

        @router.get("/mi-empresa")
        def mi_empresa(tenant: TenantInfo = Depends(get_tenant)):
            return {"razon_social": tenant.razon_social}
    """
    return tenant_actual()
