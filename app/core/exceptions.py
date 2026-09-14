"""
Excepciones de dominio + handlers globales.

Hoy tus servicios levantan HTTPException directamente (ver empleado.py,
camionReparto.py). Eso ata la logica de negocio a FastAPI: no podes reusar
un service desde un script, un job del scheduler o un test sin arrastrar HTTP.

Con esto, los services levantan errores de dominio y la capa HTTP los traduce
a status codes en un solo lugar.

    # en el service
    raise NotFound("Camion no encontrado", recurso="camion")

    # en el router: nada, se traduce solo a 404
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Base de todos los errores de negocio."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    codigo: str = "error"
    mensaje: str = "Ocurrio un error."

    def __init__(
        self,
        mensaje: str | None = None,
        *,
        codigo: str | None = None,
        detalles: dict[str, Any] | None = None,
    ) -> None:
        self.mensaje = mensaje or self.mensaje
        self.codigo = codigo or self.codigo
        self.detalles = detalles or {}
        super().__init__(self.mensaje)

    def to_dict(self) -> dict[str, Any]:
        cuerpo: dict[str, Any] = {"codigo": self.codigo, "detail": self.mensaje}
        if self.detalles:
            cuerpo["detalles"] = self.detalles
        return cuerpo


class NotFound(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    codigo = "no_encontrado"
    mensaje = "El recurso no existe."


class Conflict(AppError):
    """Choque con el estado actual: duplicados, transiciones invalidas."""

    status_code = status.HTTP_409_CONFLICT
    codigo = "conflicto"
    mensaje = "La operacion choca con el estado actual del recurso."


class ValidationFailed(AppError):
    status_code = 422
    codigo = "validacion"
    mensaje = "Los datos enviados no son validos."


class Unauthorized(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    codigo = "no_autenticado"
    mensaje = "Credenciales invalidas."


class Forbidden(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    codigo = "sin_permisos"
    mensaje = "No tenes permisos para esta operacion."


class BusinessRuleViolation(AppError):
    """Regla de negocio: stock insuficiente, caja cerrada, saldo negativo."""

    status_code = status.HTTP_409_CONFLICT
    codigo = "regla_negocio"
    mensaje = "La operacion viola una regla de negocio."


# ----------------------------------------------------------------------
# Errores de tenancy
# ----------------------------------------------------------------------


class TenantError(AppError):
    codigo = "tenant"


class TenantNoResuelto(TenantError):
    status_code = status.HTTP_400_BAD_REQUEST
    codigo = "tenant_no_resuelto"
    mensaje = "No se pudo identificar la sodería del request."


class TenantNoEncontrado(TenantError):
    status_code = status.HTTP_404_NOT_FOUND
    codigo = "tenant_no_encontrado"
    mensaje = "La sodería no existe."


class TenantSuspendido(TenantError):
    status_code = status.HTTP_402_PAYMENT_REQUIRED
    codigo = "tenant_suspendido"
    mensaje = "La cuenta está suspendida. Contactá a soporte."


class TenantMismatch(TenantError):
    """El token pertenece a otra sodería que la del request."""

    status_code = status.HTTP_403_FORBIDDEN
    codigo = "tenant_mismatch"
    mensaje = "El token no corresponde a esta sodería."


# ----------------------------------------------------------------------
# Handlers
# ----------------------------------------------------------------------


def register_exception_handlers(app: FastAPI) -> None:
    from app.core.config import settings

    @app.exception_handler(AppError)
    async def _app_error(request: Request, exc: AppError):
        if exc.status_code >= 500:
            logger.exception("AppError 5xx en %s", request.url.path)
        else:
            logger.info(
                "%s en %s: %s", exc.codigo, request.url.path, exc.mensaje
            )
        headers = None
        if exc.status_code == status.HTTP_401_UNAUTHORIZED:
            headers = {"WWW-Authenticate": "Bearer"}
        return JSONResponse(
            status_code=exc.status_code, content=exc.to_dict(), headers=headers
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={
                "codigo": "validacion",
                "detail": "Los datos enviados no son validos.",
                "detalles": {"errores": exc.errors()},
            },
        )

    @app.exception_handler(IntegrityError)
    async def _integrity(request: Request, exc: IntegrityError):
        # Reemplaza los try/except IntegrityError repetidos en cada router.
        logger.warning("IntegrityError en %s: %s", request.url.path, exc.orig)
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "codigo": "conflicto",
                "detail": (
                    "La operacion viola una restriccion de la base "
                    "(duplicado o referencia inexistente)."
                ),
            },
        )

    @app.exception_handler(SQLAlchemyError)
    async def _sqlalchemy(request: Request, exc: SQLAlchemyError):
        logger.exception("Error de base en %s", request.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"codigo": "error_base", "detail": "Error de base de datos."},
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception):
        logger.exception("Error no manejado en %s", request.url.path)
        detalle = str(exc) if settings.DEBUG else "Error interno del servidor."
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"codigo": "error_interno", "detail": detalle},
        )
