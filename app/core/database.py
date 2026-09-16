"""
Acceso a base de datos en modo una-base-por-sodería.

Reemplaza al database.py actual, que tiene un `engine` y un `SessionLocal`
globales. Con una base por cliente eso deja de servir: hay que resolver a
que base conectarse en cada request.

La estrategia es un cache LRU de engines, **uno por proceso**. Dockerfile.prod
corre gunicorn con --workers ${WEB_CONCURRENCY:-2} (configurable en Railway,
no fijo), asi que hay esa cantidad de caches independientes. El limite real
de conexiones es:

    WEB_CONCURRENCY * TENANT_ENGINE_CACHE_SIZE * (TENANT_POOL_SIZE + TENANT_MAX_OVERFLOW)

Con los defaults (2 * 10 * (2+2) = 80) y un Postgres con max_connections=100
default, entra justo. Si subís WEB_CONCURRENCY en Railway, recalculá esta
cuenta antes de tener varios tenants activos a la vez, o meté PgBouncer
adelante.

El `Base` declarativo sigue siendo uno solo: el esquema es identico en todas
las bases, lo que cambia es a cual te conectas.
"""

from __future__ import annotations

import logging
import threading
from collections import OrderedDict
from contextlib import contextmanager
from typing import Generator, Iterator

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings
from app.core.control_plane import TenantInfo
from app.core.tenancy import tenant_actual

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Base declarativa de los modelos de negocio.

    Migracion desde el codigo actual: hoy usas
        Base = declarative_base()
    en app/core/database.py. Los modelos hacen `from app.core.database import Base`,
    asi que ese import sigue funcionando sin tocar los 40 archivos de modelos.
    """


# ----------------------------------------------------------------------
# Cache de engines
# ----------------------------------------------------------------------


class _RegistroEngines:
    def __init__(self, max_size: int) -> None:
        self._max = max_size
        self._engines: OrderedDict[str, tuple[Engine, sessionmaker]] = OrderedDict()
        self._lock = threading.RLock()

    def obtener(self, info: TenantInfo) -> tuple[Engine, sessionmaker]:
        with self._lock:
            entrada = self._engines.get(info.codigo)
            if entrada is not None:
                self._engines.move_to_end(info.codigo)
                return entrada

            engine = create_engine(
                info.dsn,
                pool_pre_ping=True,
                pool_size=settings.TENANT_POOL_SIZE,
                max_overflow=settings.TENANT_MAX_OVERFLOW,
                pool_recycle=settings.TENANT_POOL_RECYCLE,
                echo=settings.DEBUG,
                # Identifica la conexion en pg_stat_activity. Cuando algo
                # anda lento, esto te dice de que sodería es la query.
                connect_args={"application_name": f"soderia-api[{info.codigo}]"},
            )
            factory = sessionmaker(
                bind=engine,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False,
            )
            self._engines[info.codigo] = (engine, factory)
            self._engines.move_to_end(info.codigo)
            logger.info("Engine creado para tenant '%s'", info.codigo)

            while len(self._engines) > self._max:
                codigo_viejo, (engine_viejo, _) = self._engines.popitem(last=False)
                logger.info("Cerrando engine de '%s' (LRU)", codigo_viejo)
                engine_viejo.dispose()

            return self._engines[info.codigo]

    def descartar(self, codigo: str) -> None:
        with self._lock:
            entrada = self._engines.pop(codigo, None)
        if entrada:
            entrada[0].dispose()
            logger.info("Engine descartado para '%s'", codigo)

    def cerrar_todo(self) -> None:
        with self._lock:
            items = list(self._engines.items())
            self._engines.clear()
        for codigo, (engine, _) in items:
            engine.dispose()
            logger.info("Engine cerrado para '%s'", codigo)


_registro = _RegistroEngines(settings.TENANT_ENGINE_CACHE_SIZE)


def get_engine(info: TenantInfo | None = None) -> Engine:
    return _registro.obtener(info or tenant_actual())[0]


def get_sessionmaker(info: TenantInfo | None = None) -> sessionmaker:
    return _registro.obtener(info or tenant_actual())[1]


def descartar_engine(codigo: str) -> None:
    """Llamar al suspender o migrar un tenant."""
    _registro.descartar(codigo)


def cerrar_engines() -> None:
    """Llamar en el shutdown de la app."""
    _registro.cerrar_todo()


# ----------------------------------------------------------------------
# Sesiones
# ----------------------------------------------------------------------


def get_db() -> Generator[Session, None, None]:
    """Dependency de FastAPI. Mantiene la misma firma que la actual.

    Los routers no cambian: siguen haciendo
        db: Session = Depends(get_db)
    Lo que cambia es que la sesion apunta a la base de la sodería del request.
    """
    factory = get_sessionmaker()
    db = factory()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def sesion_tenant(info: TenantInfo | None = None) -> Iterator[Session]:
    """Sesion fuera de un request HTTP: scripts, jobs del scheduler, tests.

        with usar_tenant(t), sesion_tenant() as db:
            ...
    """
    factory = get_sessionmaker(info)
    db = factory()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def transaccion(db: Session) -> Iterator[Session]:
    """Commit al salir, rollback si algo revienta.

    Reemplaza al patron repetido en tus routers:
        try:
            ...
            db.commit()
        except Exception:
            db.rollback()
            raise
    """
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise


def chequear_conexion(info: TenantInfo | None = None) -> bool:
    """Para el endpoint /health/ready."""
    try:
        with get_engine(info).connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        logger.exception("Fallo el chequeo de conexion")
        return False
