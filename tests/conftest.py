"""
Fixtures compartidas.

El punto delicado al testear multi-tenant es que el codigo llama a
tenant_actual() en todos lados. Fuera de un request HTTP eso levanta
excepcion. La fixture `tenant` fija uno en el contexto para que los tests
de servicios funcionen sin levantar la app entera.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

# Variables minimas para que la config valide sin un .env de verdad.
# Se ponen antes de cualquier import de app.* porque Settings se instancia
# al importar app.core.config.
os.environ.setdefault("ENV", "dev")
os.environ.setdefault("SECRET_KEY", "clave-de-test-suficientemente-larga-1234567890")
os.environ.setdefault(
    "CONTROL_PLANE_DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@localhost:5432/soderia_control_test",
)
os.environ.setdefault("TENANT_DB_USER", "postgres")
os.environ.setdefault("TENANT_DB_PASSWORD", "postgres")
os.environ.setdefault("DEFAULT_TENANT", "test")
os.environ.setdefault("SCHEDULER_ENABLED", "false")


@pytest.fixture(scope="session")
def tenant_info():
    """Ficha de tenant de mentira. No toca el control plane."""
    from app.core.control_plane import EstadoTenant, TenantInfo

    return TenantInfo(
        id_tenant=1,
        codigo="test",
        razon_social="Sodería de Prueba",
        dsn=os.environ.get(
            "TEST_TENANT_DSN",
            "postgresql+psycopg2://postgres:postgres@localhost:5432/soderia_test",
        ),
        estado=EstadoTenant.ACTIVO,
        plan="basico",
        timezone="America/Argentina/Cordoba",
        scheduler_activo=False,
    )


@pytest.fixture
def tenant(tenant_info):
    """Fija el tenant en el contexto durante el test.

        def test_algo(tenant, db):
            assert crear_cliente(db, ...) is not None
    """
    from app.core.tenancy import usar_tenant

    with usar_tenant(tenant_info) as info:
        yield info


@pytest.fixture
def db(tenant):
    """Sesion contra la base de test. Hace rollback al terminar.

    Cada test corre dentro de una transaccion que nunca se commitea, asi
    que la base queda limpia sin necesidad de truncar tablas.
    """
    from app.core.database import get_engine
    from sqlalchemy.orm import Session

    conexion = get_engine().connect()
    transaccion = conexion.begin()
    sesion = Session(bind=conexion, expire_on_commit=False)
    try:
        yield sesion
    finally:
        sesion.close()
        transaccion.rollback()
        conexion.close()


@pytest.fixture
def client(tenant_info):
    """Cliente HTTP con el header de tenant ya puesto."""
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        c.headers.update({"X-Tenant": tenant_info.codigo})
        yield c
