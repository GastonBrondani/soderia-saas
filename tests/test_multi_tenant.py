"""
Tests de integracion multi-tenant: usan un Postgres de verdad.

Del punto 7 de la revision cruzada del 2026-09-15: "las garantias centrales
del producto no estan testeadas". Cubre tres cosas que hasta ahora vivian
solo como creencia:

1. Un tenant recien dado de alta queda realmente usable (login + endpoints
   basicos) -- es ademas el smoke test del propio scripts/crear_tenant.py,
   que es donde vivia el bug de la fila de `empresa` faltante.
2. El token de una sodería no sirve contra otra (403 tenant_mismatch) --
   la garantia central de aislamiento del producto.
3. Idempotencia real end-to-end: el mismo payload de sync offline dos
   veces no duplica el pago.

Si no hay Postgres accesible con las credenciales de TENANT_DB_* /
CONTROL_PLANE_DATABASE_URL (ver conftest.py para los defaults), estos
tests se saltan solos -- no rompen CI en una maquina sin Postgres.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError


def _postgres_disponible() -> bool:
    from app.core.config import get_settings

    try:
        engine = create_engine(get_settings().maintenance_dsn())
        with engine.connect():
            pass
        engine.dispose()
        return True
    except OperationalError:
        return False


pytestmark = pytest.mark.skipif(
    not _postgres_disponible(),
    reason="No hay Postgres accesible (TENANT_DB_*): se saltan los tests de integracion.",
)


@pytest.fixture(scope="module")
def control_plane_db():
    """Crea (si hace falta) la base y las tablas del control plane de test."""
    from app.core.config import get_settings
    from app.core.control_plane import init_control_plane

    url = make_url(get_settings().CONTROL_PLANE_DATABASE_URL)
    admin_url = url.set(database="postgres")
    engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    try:
        with engine.connect() as conn:
            existe = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :n"),
                {"n": url.database},
            ).scalar()
            if not existe:
                conn.execute(text(f'CREATE DATABASE "{url.database}"'))
    finally:
        engine.dispose()

    init_control_plane()
    yield


@pytest.fixture
def crear_tenant_prueba(control_plane_db):
    """Da de alta una sodería de prueba de verdad (mismo camino que
    scripts/crear_tenant.py) y la borra al terminar el test.

    Devuelve una funcion `crear(codigo) -> (codigo, dsn, password_admin)`.
    """
    from app.core.config import get_settings
    from app.core.control_plane import (
        EstadoTenant,
        Tenant,
        control_session,
        invalidar_cache,
    )
    from scripts.crear_tenant import (
        borrar_base,
        crear_admin,
        crear_base,
        crear_empresa,
        migrar,
        preparar_archivos,
        verificar_alta,
    )

    settings = get_settings()
    creados: list[tuple[str, str]] = []

    def _crear(codigo: str, razon_social: str = "Sodería de prueba"):
        db_name = settings.tenant_db_name(codigo)
        dsn = settings.tenant_dsn(db_name)

        with control_session() as db:
            db.add(
                Tenant(
                    codigo=codigo,
                    razon_social=razon_social,
                    db_name=db_name,
                    estado=EstadoTenant.PROVISIONANDO,
                    plan="basico",
                    timezone="America/Argentina/Cordoba",
                )
            )
            db.commit()

        crear_base(db_name)
        migrar(dsn)
        crear_empresa(dsn, razon_social)
        password = crear_admin(dsn, "admin", None)
        preparar_archivos(codigo)

        problemas = verificar_alta(dsn, "admin")
        assert not problemas, f"alta de '{codigo}' quedo incompleta: {problemas}"

        with control_session() as db:
            fila = db.execute(select(Tenant).where(Tenant.codigo == codigo)).scalar_one()
            fila.estado = EstadoTenant.ACTIVO
            db.commit()
        invalidar_cache(codigo)

        creados.append((codigo, db_name))
        return codigo, dsn, password

    yield _crear

    for codigo, db_name in creados:
        borrar_base(db_name)
        with control_session() as db:
            fila = db.execute(
                select(Tenant).where(Tenant.codigo == codigo)
            ).scalar_one_or_none()
            if fila:
                db.delete(fila)
                db.commit()
        invalidar_cache(codigo)


def _codigo_unico(prefijo: str) -> str:
    return f"{prefijo}{uuid.uuid4().hex[:8]}"


def _login(client, codigo: str, password: str, usuario: str = "admin") -> str:
    resp = client.post(
        "/auth/login",
        json={"nombre_usuario": usuario, "contrasena": password},
        headers={"X-Tenant": codigo},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def test_tenant_nuevo_queda_usable(crear_tenant_prueba):
    """Smoke test del alta: login + bootstrap + stock en un tenant nuevo.

    Es la regresion puntual del bug de la fila de `empresa` faltante: sin
    el fix de scripts/crear_tenant.py esto daba 404 en /stock/ y en
    /catalogo/bootstrap.
    """
    from fastapi.testclient import TestClient

    from app.main import app

    codigo, _dsn, password = crear_tenant_prueba(_codigo_unico("prueba"))

    with TestClient(app) as client:
        token = _login(client, codigo, password)
        headers = {"X-Tenant": codigo, "Authorization": f"Bearer {token}"}

        resp = client.get("/catalogo/bootstrap", headers=headers)
        assert resp.status_code == 200, resp.text

        resp = client.get("/stock/", headers=headers)
        assert resp.status_code == 200, resp.text


def test_token_de_un_tenant_no_sirve_en_otro(crear_tenant_prueba):
    """Garantia central de aislamiento: el JWT lleva el claim `ten`, y un
    token de la sodería A usado con el header de la sodería B tiene que
    dar 403 tenant_mismatch, no colarse."""
    from fastapi.testclient import TestClient

    from app.main import app

    codigo_a, _, password_a = crear_tenant_prueba(_codigo_unico("tena"))
    codigo_b, _, _password_b = crear_tenant_prueba(_codigo_unico("tenb"))

    with TestClient(app) as client:
        token_a = _login(client, codigo_a, password_a)

        resp = client.get(
            "/catalogo/bootstrap",
            headers={"X-Tenant": codigo_b, "Authorization": f"Bearer {token_a}"},
        )
        assert resp.status_code == 403, resp.text
        assert resp.json()["codigo"] == "tenant_mismatch"


def test_pago_offline_con_misma_idempotency_key_no_se_duplica(crear_tenant_prueba):
    """El mismo payload de sync offline mandado dos veces (reintento tras
    timeout, doble tap, lo que sea) no tiene que crear dos pagos."""
    from fastapi.testclient import TestClient

    from app.main import app

    codigo, _, password = crear_tenant_prueba(_codigo_unico("idem"))

    with TestClient(app) as client:
        token = _login(client, codigo, password)
        headers = {"X-Tenant": codigo, "Authorization": f"Bearer {token}"}

        payload = {
            "id_medio_pago": 1,
            "fecha": "2026-09-15T10:00:00",
            "monto": 100.0,
            "tipo_pago": "INGRESO_EMPRESA",
            "idempotency_key": str(uuid.uuid4()),
            "client_uuid": str(uuid.uuid4()),
        }

        r1 = client.post("/pagos", json=payload, headers=headers)
        assert r1.status_code == 200, r1.text
        r2 = client.post("/pagos", json=payload, headers=headers)
        assert r2.status_code == 200, r2.text

        assert r1.json()["id_pago"] == r2.json()["id_pago"]

        from app.core.config import get_settings

        settings = get_settings()
        engine = create_engine(settings.tenant_dsn(settings.tenant_db_name(codigo)))
        try:
            with engine.connect() as conn:
                total = conn.execute(
                    text("SELECT count(*) FROM pago WHERE idempotency_key = :k"),
                    {"k": payload["idempotency_key"]},
                ).scalar()
        finally:
            engine.dispose()
        assert total == 1


def test_cancelar_deuda_persiste_de_verdad(crear_tenant_prueba):
    """Regresion puntual: POST /pagos/cancelar-deuda hacia `with db.begin():`
    con una sesion que get_current_user ya habia tocado (autobegin de
    SQLAlchemy), lo que tiraba "A transaction is already begun on this
    Session" en TODA llamada autenticada real -- nunca funcionaba mas alla
    de una prueba manual con sesion nueva. Ademas de no romper, confirma
    que el pago y la baja de deuda quedan commiteados de verdad."""
    from fastapi.testclient import TestClient

    from app.main import app

    codigo, dsn, password = crear_tenant_prueba(_codigo_unico("candeuda"))

    engine = create_engine(dsn)
    try:
        with engine.begin() as conn:
            id_usuario = conn.execute(
                text("SELECT id_usuario FROM usuario WHERE nombre_usuario = 'admin'")
            ).scalar_one()
            conn.execute(
                text(
                    "INSERT INTO persona (dni, nombre, apellido) "
                    "VALUES (30999888, 'Prueba', 'Test')"
                )
            )
            conn.execute(
                text(
                    "INSERT INTO cliente (legajo, id_empresa, dni) "
                    "VALUES (999888, 1, 30999888)"
                )
            )
            conn.execute(
                text(
                    "INSERT INTO cliente_cuenta (id_cuenta, legajo, saldo, deuda) "
                    "VALUES (999888, 999888, 0, 100)"
                )
            )
            conn.execute(
                text(
                    "INSERT INTO reparto_dia (id_repartodia, id_usuario, id_empresa, fecha) "
                    "VALUES (999888, :u, 1, CURRENT_DATE)"
                ),
                {"u": id_usuario},
            )
    finally:
        engine.dispose()

    with TestClient(app) as client:
        token = _login(client, codigo, password)
        headers = {"X-Tenant": codigo, "Authorization": f"Bearer {token}"}

        resp = client.post(
            "/pagos/cancelar-deuda",
            json={
                "legajo": 999888,
                "id_medio_pago": 1,
                "id_repartodia": 999888,
                "monto": 40.0,
            },
            headers=headers,
        )
        assert resp.status_code == 200, resp.text
        assert float(resp.json()["deuda"]) == 60.0

    engine = create_engine(dsn)
    try:
        with engine.connect() as conn:
            deuda = conn.execute(
                text("SELECT deuda FROM cliente_cuenta WHERE id_cuenta = 999888")
            ).scalar_one()
            pagos = conn.execute(
                text("SELECT count(*) FROM pago WHERE legajo = 999888")
            ).scalar_one()
    finally:
        engine.dispose()

    assert float(deuda) == 60.0
    assert pagos == 1
