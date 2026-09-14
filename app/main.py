"""
Punto de entrada de la aplicacion.

Diferencias con el main.py actual:

  - CORS sale de configuracion, no de una lista hardcodeada con localhost
    y "*" mezclados.
  - Se reemplaza el mount de StaticFiles sobre /data por un endpoint que
    valida autenticacion y pertenencia al tenant antes de devolver un archivo.
  - /health deja de mentir: hoy devuelve {"status": "ok"} aunque la base
    este caida. Se separa en /health (el proceso vive) y /health/ready
    (el proceso puede atender).
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.api.router import api_router
from app.core.config import settings
from app.core.control_plane import init_control_plane
from app.core.database import cerrar_engines, chequear_conexion
from app.core.exceptions import NotFound, register_exception_handlers
from app.core.logging import RequestIdMiddleware, configurar_logging
from app.core.scheduler import start_scheduler, stop_scheduler
from app.core.security import CurrentUser, get_current_user
from app.core.storage import get_storage
from app.core.tenancy import TenantMiddleware, tenant_actual

configurar_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_control_plane()
    start_scheduler()
    try:
        yield
    finally:
        stop_scheduler()
        cerrar_engines()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs" if settings.ENABLE_DOCS else None,
    redoc_url="/redoc" if settings.ENABLE_DOCS else None,
    openapi_url="/openapi.json" if settings.ENABLE_DOCS else None,
)

register_exception_handlers(app)

# ----------------------------------------------------------------------
# Middlewares
#
# Starlette los aplica en orden inverso al de registro: el ultimo agregado
# es el mas externo. Queda, de afuera hacia adentro:
#     RequestId -> CORS -> Tenant -> endpoint
# El tenant se resuelve despues de CORS para que un preflight OPTIONS mal
# formado no muera con un 400 de tenant sin los headers de CORS puestos.
# ----------------------------------------------------------------------

app.add_middleware(TenantMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=settings.CORS_ORIGIN_REGEX,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-Id", "X-Tenant"],
)

app.add_middleware(RequestIdMiddleware)

app.include_router(api_router)


# ----------------------------------------------------------------------
# Health checks
# ----------------------------------------------------------------------


@app.get("/health", tags=["Infra"])
def health():
    """Liveness: el proceso responde. No toca la base."""
    return {"status": "ok", "version": settings.APP_VERSION}


@app.get("/health/ready", tags=["Infra"], include_in_schema=False)
def ready():
    """Readiness: el control plane contesta.

    Sin tenant en contexto no se puede chequear una base de negocio, asi
    que se valida el control plane, que es el que habilita todo lo demas.
    """
    from sqlalchemy import text

    from app.core.control_plane import get_control_engine

    try:
        with get_control_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception:
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=503, content={"status": "sin base"})


# ----------------------------------------------------------------------
# Archivos
# ----------------------------------------------------------------------


@app.get(settings.STORAGE_PUBLIC_URL_BASE + "/{clave:path}", tags=["Archivos"])
def descargar_archivo(
    clave: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Sirve un comprobante o documento.

    El mount de StaticFiles que habia antes dejaba los PDFs accesibles a
    cualquiera que adivinara la URL. Con varias soderias eso significa que
    un cliente puede leer los comprobantes de otro. Aca se exige token y se
    verifica que la clave empiece con el codigo del tenant del request.
    """
    tenant = tenant_actual()
    if not clave.startswith(f"{tenant.codigo}/"):
        raise NotFound("El archivo no existe.")

    storage = get_storage()
    if not storage.existe(clave):
        raise NotFound("El archivo no existe.")

    ruta = storage.ruta_absoluta(clave)
    if ruta is None:
        raise NotFound("El archivo no existe.")

    return FileResponse(ruta, filename=ruta.name)
