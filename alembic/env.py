from __future__ import annotations
import os
import sys
from logging.config import fileConfig
from sqlalchemy import engine_from_config,pool
from alembic import context

# === Cargar .env (para DATABASE_URL, DEBUG, etc.) ===
from dotenv import load_dotenv
load_dotenv()

# === Permitir importar tu app ===
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import app.models

# Importá tu Base (metadatos) y, si querés, tu engine
from app.core.database import Base
from app.core.database import engine

# Configuración de Alembic
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadatos objetivo para autogenerate
target_metadata = Base.metadata

# Tomar URL desde env
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL no definido en entorno / .env")

# Opciones útiles para autogenerate
def include_object(object, name,type_,reflected,compare_to):
    # podemos filtrar objetos si hiciera falta
    return True

def run_migrations_offline() -> None:
    """Modo offline: emite SQL sin conectarse."""
    context.configure(url=DATABASE_URL,
                      target_metadata=target_metadata,
                      literal_binds=True,
                      dialect_opts={"paramstyle": "named"},
                      compare_type=True,
                      include_schemas=False,                      
                      include_object=include_object,
                      version_table="alembic_version",
    )
    with context.begin_transaction():
        context.run_migrations()
    
def run_migrations_online() -> None:
    """Modo online: usa conexión real."""
    connectable = engine_from_config(
        {"sqlalchemy.url": DATABASE_URL},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            include_schemas=False,            
            include_object=include_object,
            version_table="alembic_version",
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()