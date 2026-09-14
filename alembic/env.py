"""
Alembic en modo una-base-por-sodería.

El env.py actual toma DATABASE_URL del .env y migra esa unica base. Aca la
URL llega por parametro, porque hay N bases:

    alembic -x tenant=solmar upgrade head      # una sola
    python scripts/migrate_all_tenants.py      # todas

Si no se pasa nada, usa ALEMBIC_TARGET_URL del entorno. Eso sirve para
generar revisiones contra una base de trabajo:

    ALEMBIC_TARGET_URL=postgresql+psycopg2://... alembic revision --autogenerate -m "x"
"""

from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Permitir importar la app
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.config import settings  # noqa: E402
from app.db.base import Base  # noqa: E402

# Importar el registry ANTES de leer Base.metadata. Sin esto, con los
# modelos repartidos en features/, autogenerate ve la metadata vacia y
# genera migraciones que borran todas tus tablas.
import app.db.models_registry  # noqa: E402, F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _resolver_url() -> str:
    # 1. -x url=...
    x_args = context.get_x_argument(as_dictionary=True)
    if url := x_args.get("url"):
        return url

    # 2. -x tenant=codigo  -> se resuelve contra el control plane
    if codigo := x_args.get("tenant"):
        from app.core.control_plane import Tenant, control_session
        from sqlalchemy import select

        with control_session() as db:
            fila = db.execute(
                select(Tenant).where(Tenant.codigo == codigo.strip().lower())
            ).scalar_one_or_none()
        if fila is None:
            raise SystemExit(f"No existe la sodería '{codigo}' en el control plane.")
        return fila.dsn_override or settings.tenant_dsn(fila.db_name)

    # 3. Base de trabajo para generar revisiones
    if url := os.getenv("ALEMBIC_TARGET_URL"):
        return url

    raise SystemExit(
        "Falta indicar la base. Usa -x tenant=<codigo>, -x url=<dsn> "
        "o la variable ALEMBIC_TARGET_URL."
    )


def include_object(objeto, nombre, tipo, reflejado, comparar_con) -> bool:
    # La tabla del control plane no vive en las bases de negocio.
    if tipo == "table" and nombre == "tenant":
        return False
    return True


def run_migrations_offline() -> None:
    context.configure(
        url=_resolver_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        include_object=include_object,
        version_table="alembic_version",
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    conectable = engine_from_config(
        {"sqlalchemy.url": _resolver_url()},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with conectable.connect() as conexion:
        context.configure(
            connection=conexion,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            include_object=include_object,
            version_table="alembic_version",
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
