"""
Logging estructurado.

Con varios clientes en el mismo proceso, un log que dice "error creando
pedido" no sirve: hay que saber de que sodería. Este modulo inyecta el
tenant y un id de request en cada linea, sin que tengas que acordarte de
pasarlos.

En dev sale legible; en prod sale JSON para que lo trague cualquier
agregador de logs.
"""

from __future__ import annotations

import json
import logging
import sys
import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings
from app.core.tenancy import tenant_actual_opcional

_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)


def request_id_actual() -> str | None:
    return _request_id.get()


class ContextoFilter(logging.Filter):
    """Agrega tenant y request_id a todos los registros."""

    def filter(self, record: logging.LogRecord) -> bool:
        tenant = tenant_actual_opcional()
        record.tenant = tenant.codigo if tenant else "-"
        record.request_id = _request_id.get() or "-"
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        cuerpo = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "nivel": record.levelname,
            "logger": record.name,
            "tenant": getattr(record, "tenant", "-"),
            "request_id": getattr(record, "request_id", "-"),
            "mensaje": record.getMessage(),
        }
        if record.exc_info:
            cuerpo["excepcion"] = self.formatException(record.exc_info)
        return json.dumps(cuerpo, ensure_ascii=False)


def configurar_logging() -> None:
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(settings.LOG_LEVEL.upper())

    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(ContextoFilter())

    if settings.is_prod:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)-7s [%(tenant)s] %(name)s: %(message)s",
                datefmt="%H:%M:%S",
            )
        )

    root.addHandler(handler)

    # SQLAlchemy es ruidoso en INFO.
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.DEBUG else logging.WARNING
    )
    logging.getLogger("apscheduler").setLevel(logging.WARNING)


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Asigna un id a cada request y lo devuelve en la respuesta.

    Cuando un cliente reporta un error, le pedis el X-Request-Id y buscas
    exactamente esa traza en los logs.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        rid = request.headers.get("X-Request-Id") or uuid.uuid4().hex[:16]
        token = _request_id.set(rid)
        try:
            respuesta = await call_next(request)
        finally:
            _request_id.reset(token)
        respuesta.headers["X-Request-Id"] = rid
        return respuesta
