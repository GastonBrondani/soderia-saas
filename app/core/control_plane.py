"""
Control plane: la unica base de datos fija del sistema.

No guarda datos de negocio. Guarda el registro de soderias: quien existe,
donde vive su base, en que estado esta la suscripcion.

Es una base chica (una tabla, unas decenas de filas) pero es el punto unico
de falla del sistema: si se cae, no se resuelve ningun tenant. Ponela en la
misma instancia de Postgres que las demas y hace backup con la misma politica.

    control_plane (base: soderia_control)
      └── tenant
            ├── solmar      -> soderia_solmar
            ├── lacascada   -> soderia_lacascada
            └── aguaviva    -> soderia_aguaviva  (suspendido)
"""

from __future__ import annotations

import enum
import threading
import time
from dataclasses import dataclass
from functools import lru_cache
from datetime import datetime
from typing import Generator

from sqlalchemy import (
    Boolean,
    DateTime,
    Engine,
    Enum as SAEnum,
    Integer,
    String,
    create_engine,
    func,
    select,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    sessionmaker,
)

from app.core.config import settings
from app.core.exceptions import (
    TenantNoEncontrado,
    TenantSuspendido,
)


class ControlBase(DeclarativeBase):
    """Base declarativa SEPARADA de la de negocio.

    Importante: no mezclar con app.db.base.Base. Si compartieran metadata,
    Alembic intentaria crear la tabla `tenant` dentro de cada base de sodería.
    """


class EstadoTenant(str, enum.Enum):
    PROVISIONANDO = "provisionando"
    ACTIVO = "activo"
    SUSPENDIDO = "suspendido"
    ARCHIVADO = "archivado"


class Tenant(ControlBase):
    __tablename__ = "tenant"

    id_tenant: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Identificador que viaja en el subdominio y en el JWT. Inmutable.
    codigo: Mapped[str] = mapped_column(String(63), unique=True, nullable=False, index=True)

    razon_social: Mapped[str] = mapped_column(String(150), nullable=False)

    db_name: Mapped[str] = mapped_column(String(63), nullable=False)
    # Si esta sodería vive en otro servidor de Postgres, se guarda el DSN
    # completo aca y se ignora la construccion por defecto.
    dsn_override: Mapped[str | None] = mapped_column(String(500))

    estado: Mapped[EstadoTenant] = mapped_column(
        SAEnum(EstadoTenant, name="estado_tenant", native_enum=False, length=20),
        nullable=False,
        default=EstadoTenant.PROVISIONANDO,
    )

    plan: Mapped[str] = mapped_column(String(30), nullable=False, default="basico")

    # Cada sodería puede estar en otra provincia.
    timezone: Mapped[str] = mapped_column(
        String(50), nullable=False, default=settings.DEFAULT_TIMEZONE
    )

    # Apagar jobs para un cliente puntual sin tocar a los demas.
    scheduler_activo: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )

    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<Tenant {self.codigo} estado={self.estado.value}>"


# ----------------------------------------------------------------------
# Engine del control plane
# ----------------------------------------------------------------------

@lru_cache(maxsize=1)
def get_control_engine() -> Engine:
    """Engine del control plane, creado la primera vez que se usa.

    Perezoso a proposito: si se creara al importar el modulo, cualquier
    script o test que toque control_plane necesitaria el driver de Postgres
    instalado y la config completa, aunque nunca consulte nada.
    """
    return create_engine(
        settings.CONTROL_PLANE_DATABASE_URL,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=5,
        echo=False,
        connect_args={"application_name": "soderia-api[control]"},
    )


@lru_cache(maxsize=1)
def _control_sessionmaker() -> sessionmaker:
    return sessionmaker(
        bind=get_control_engine(),
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )


def control_session() -> Session:
    """Sesion contra el control plane.

        with control_session() as db:
            ...
    """
    return _control_sessionmaker()()


def get_control_db() -> Generator[Session, None, None]:
    """Dependency de FastAPI para endpoints de administracion."""
    db = control_session()
    try:
        yield db
    finally:
        db.close()


# ----------------------------------------------------------------------
# Ficha de tenant + cache
# ----------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TenantInfo:
    """Snapshot inmutable de un tenant, lo que la app necesita en runtime.

    Se usa esto en vez del modelo ORM para no arrastrar una Session viva
    del control plane por todo el request.
    """

    id_tenant: int
    codigo: str
    razon_social: str
    dsn: str
    estado: EstadoTenant
    plan: str
    timezone: str
    scheduler_activo: bool

    @property
    def esta_activo(self) -> bool:
        return self.estado is EstadoTenant.ACTIVO


def _a_info(t: Tenant) -> TenantInfo:
    dsn = t.dsn_override or settings.tenant_dsn(t.db_name)
    return TenantInfo(
        id_tenant=t.id_tenant,
        codigo=t.codigo,
        razon_social=t.razon_social,
        dsn=dsn,
        estado=t.estado,
        plan=t.plan,
        timezone=t.timezone,
        scheduler_activo=t.scheduler_activo,
    )


class _CacheTenants:
    """Cache con TTL. Evita pegarle al control plane en cada request.

    El TTL corto (60s por defecto) es a proposito: cuando suspendas una
    sodería por falta de pago, querés que corte rapido sin reiniciar la app.
    """

    def __init__(self, ttl: int) -> None:
        self._ttl = ttl
        self._datos: dict[str, tuple[float, TenantInfo]] = {}
        self._lock = threading.RLock()

    def get(self, codigo: str) -> TenantInfo | None:
        with self._lock:
            entrada = self._datos.get(codigo)
            if entrada is None:
                return None
            vence, info = entrada
            if time.monotonic() > vence:
                self._datos.pop(codigo, None)
                return None
            return info

    def set(self, info: TenantInfo) -> None:
        with self._lock:
            self._datos[info.codigo] = (time.monotonic() + self._ttl, info)

    def invalidar(self, codigo: str | None = None) -> None:
        with self._lock:
            if codigo is None:
                self._datos.clear()
            else:
                self._datos.pop(codigo, None)


_cache = _CacheTenants(settings.TENANT_CACHE_TTL_SECONDS)


def buscar_tenant(codigo: str, *, usar_cache: bool = True) -> TenantInfo:
    """Devuelve la ficha del tenant. Levanta si no existe o esta suspendido."""
    codigo = codigo.strip().lower()

    if usar_cache:
        cacheado = _cache.get(codigo)
        if cacheado is not None:
            _verificar_estado(cacheado)
            return cacheado

    with control_session() as db:
        fila = db.execute(
            select(Tenant).where(Tenant.codigo == codigo)
        ).scalar_one_or_none()

    if fila is None:
        raise TenantNoEncontrado(f"No existe la sodería '{codigo}'.")

    info = _a_info(fila)
    _cache.set(info)
    _verificar_estado(info)
    return info


def _verificar_estado(info: TenantInfo) -> None:
    if info.estado is EstadoTenant.SUSPENDIDO:
        raise TenantSuspendido()
    if info.estado is EstadoTenant.ARCHIVADO:
        raise TenantNoEncontrado(f"La sodería '{info.codigo}' fue dada de baja.")
    if info.estado is EstadoTenant.PROVISIONANDO:
        raise TenantNoEncontrado(
            f"La sodería '{info.codigo}' todavia se esta configurando."
        )


def listar_tenants(
    *, solo_activos: bool = True, incluir_suspendidos: bool = False
) -> list[TenantInfo]:
    """Usado por el scheduler y por el runner de migraciones."""
    with control_session() as db:
        stmt = select(Tenant).order_by(Tenant.codigo)
        if solo_activos:
            estados = [EstadoTenant.ACTIVO]
            if incluir_suspendidos:
                estados.append(EstadoTenant.SUSPENDIDO)
            stmt = stmt.where(Tenant.estado.in_(estados))
        return [_a_info(t) for t in db.execute(stmt).scalars().all()]


def invalidar_cache(codigo: str | None = None) -> None:
    """Llamar despues de cambiar el estado o el plan de un tenant."""
    _cache.invalidar(codigo)


def init_control_plane() -> None:
    """Crea la tabla `tenant` si no existe.

    El control plane tiene una sola tabla y cambia muy poco, asi que no
    justifica su propia cadena de migraciones de Alembic.
    """
    ControlBase.metadata.create_all(bind=get_control_engine())
