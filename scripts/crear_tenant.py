#!/usr/bin/env python
"""
Alta de una sodería nueva.

Esto es tu producto: el tiempo que tardas en poner a andar un cliente nuevo.
Hoy serian varias horas de trabajo manual. Con esto es un comando.

    python scripts/crear_tenant.py \
        --codigo solmar \
        --razon-social "Sodería Sol del Mar SRL" \
        --admin-usuario admin \
        --timezone America/Argentina/Cordoba

Pasos que ejecuta, en orden:
    1. Valida el codigo (va en un subdominio y en un nombre de base).
    2. CREATE DATABASE soderia_solmar
    3. alembic upgrade head sobre esa base (las tablas maestras --dias de
       la semana, medios de pago, roles, etc.-- vienen de la migracion de
       seed, no de este script)
    4. Crea la fila de `empresa` con la razon social pasada por parametro
    5. Crea el usuario administrador y muestra su contraseña una sola vez
    6. Prepara las carpetas de archivos
    7. Verifica que el alta haya quedado completa (empresa, rol ADMIN,
       usuario admin con ese rol)
    8. Marca el tenant como ACTIVO en el control plane

Si algo falla en el medio -- incluida la verificacion del paso 7 -- el
tenant queda en estado PROVISIONANDO y no atiende requests. Con --rollback
se limpia todo y se vuelve a empezar.
"""

from __future__ import annotations

import argparse
import re
import secrets
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, select, text  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.control_plane import (  # noqa: E402
    EstadoTenant,
    Tenant,
    control_session,
    init_control_plane,
    invalidar_cache,
)
# Misma lista que usa el resolver de subdominios en tenancy.py (antes eran
# dos listas separadas que podian divergir sin que nadie lo notara).
from app.core.tenancy import CODIGOS_RESERVADOS as RESERVADOS  # noqa: E402

RE_CODIGO = re.compile(r"^[a-z][a-z0-9]{2,30}$")


def validar_codigo(codigo: str) -> str:
    codigo = codigo.strip().lower()
    if not RE_CODIGO.match(codigo):
        raise SystemExit(
            "El codigo tiene que empezar con letra y tener entre 3 y 31 "
            "caracteres, solo minusculas y numeros. Va en el subdominio "
            "(solmar.tuapp.com) y en el nombre de la base."
        )
    if codigo in RESERVADOS:
        raise SystemExit(f"'{codigo}' es un nombre reservado.")
    return codigo


def base_existe(db_name: str) -> bool:
    engine = create_engine(settings.maintenance_dsn(), isolation_level="AUTOCOMMIT")
    try:
        with engine.connect() as conn:
            return bool(
                conn.execute(
                    text("SELECT 1 FROM pg_database WHERE datname = :n"),
                    {"n": db_name},
                ).scalar()
            )
    finally:
        engine.dispose()


def crear_base(db_name: str) -> None:
    # CREATE DATABASE no corre dentro de una transaccion, de ahi el AUTOCOMMIT.
    engine = create_engine(settings.maintenance_dsn(), isolation_level="AUTOCOMMIT")
    try:
        with engine.connect() as conn:
            # El nombre no se puede parametrizar; ya viene validado por regex.
            conn.execute(
                text(
                    f'CREATE DATABASE "{db_name}" '
                    "ENCODING 'UTF8' TEMPLATE template0"
                )
            )
        print(f"  base creada: {db_name}")
    finally:
        engine.dispose()


def borrar_base(db_name: str) -> None:
    engine = create_engine(settings.maintenance_dsn(), isolation_level="AUTOCOMMIT")
    try:
        with engine.connect() as conn:
            conn.execute(
                text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname = :n AND pid <> pg_backend_pid()"
                ),
                {"n": db_name},
            )
            conn.execute(text(f'DROP DATABASE IF EXISTS "{db_name}"'))
        print(f"  base eliminada: {db_name}")
    finally:
        engine.dispose()


def migrar(dsn: str) -> None:
    raiz = Path(__file__).resolve().parents[1]
    resultado = subprocess.run(
        ["alembic", "-x", f"url={dsn}", "upgrade", "head"],
        cwd=raiz,
        capture_output=True,
        text=True,
    )
    if resultado.returncode != 0:
        print(resultado.stdout)
        print(resultado.stderr, file=sys.stderr)
        raise RuntimeError("Fallo alembic upgrade head")
    print("  migraciones aplicadas")


def crear_empresa(dsn: str, razon_social: str) -> int:
    """La empresa de la sodería. Con una base por tenant hay una sola fila.

    Las tablas maestras de verdad (dias de la semana, medios de pago,
    roles, tipos de movimiento/evento) ya vienen sembradas por la
    migracion de Alembic `409913c99187_seed_datos_base` -- son constantes
    del esquema, iguales para cualquier sodería. La empresa no: la razon
    social es dato del cliente, por eso se crea aca y no en una migracion.
    """
    engine = create_engine(dsn)
    try:
        with engine.begin() as conn:
            id_empresa = conn.execute(
                text(
                    "INSERT INTO empresa (razon_social) VALUES (:r) "
                    "RETURNING id_empresa"
                ),
                {"r": razon_social},
            ).scalar_one()
        print(f"  empresa creada: id_empresa={id_empresa}")
        return id_empresa
    finally:
        engine.dispose()


def verificar_alta(dsn: str, admin_usuario: str) -> list[str]:
    """Chequeos minimos de que el tenant queda usable de verdad.

    Sin esto, un alta a medias (por ejemplo por el ImportError que se
    tragaba en silencio el paso de seed) queda marcada ACTIVA igual, y el
    primer sintoma es un 404 confuso de EmpresaService.get_id_empresa_actual
    en el primer request real del cliente.
    """
    problemas: list[str] = []
    engine = create_engine(dsn)
    try:
        with engine.connect() as conn:
            if conn.execute(text("SELECT 1 FROM empresa")).first() is None:
                problemas.append("no hay ninguna fila en 'empresa'")

            id_rol = conn.execute(
                text("SELECT id_rol FROM rol WHERE upper(nombre) = 'ADMIN'")
            ).scalar()
            if id_rol is None:
                problemas.append("no existe el rol ADMIN")
            else:
                tiene_admin = conn.execute(
                    text(
                        "SELECT 1 FROM usuario u "
                        "JOIN usuario_rol ur ON ur.id_usuario = u.id_usuario "
                        "WHERE u.nombre_usuario = :u AND ur.id_rol = :r"
                    ),
                    {"u": admin_usuario, "r": id_rol},
                ).first()
                if tiene_admin is None:
                    problemas.append(
                        f"el usuario '{admin_usuario}' no tiene el rol ADMIN"
                    )
    finally:
        engine.dispose()
    return problemas


def crear_admin(dsn: str, usuario: str, password: str | None) -> str:
    from app.core.security import hash_password

    password = password or secrets.token_urlsafe(12)

    engine = create_engine(dsn)
    try:
        with engine.begin() as conn:
            existe = conn.execute(
                text("SELECT 1 FROM usuario WHERE nombre_usuario = :u"),
                {"u": usuario},
            ).scalar()
            if existe:
                print(f"  el usuario '{usuario}' ya existe, no se toca")
                return "(sin cambios)"

            id_usuario = conn.execute(
                text(
                    "INSERT INTO usuario (nombre_usuario, contraseña) "
                    "VALUES (:u, :p) RETURNING id_usuario"
                ),
                {"u": usuario, "p": hash_password(password)},
            ).scalar()

            id_rol = conn.execute(
                text("SELECT id_rol FROM rol WHERE upper(nombre) = 'ADMIN'")
            ).scalar()
            if id_rol is None:
                id_rol = conn.execute(
                    text("INSERT INTO rol (nombre) VALUES ('ADMIN') RETURNING id_rol")
                ).scalar()

            conn.execute(
                text(
                    "INSERT INTO usuario_rol (id_usuario, id_rol) "
                    "VALUES (:u, :r) ON CONFLICT DO NOTHING"
                ),
                {"u": id_usuario, "r": id_rol},
            )
        print(f"  usuario administrador creado: {usuario}")
        return password
    finally:
        engine.dispose()


def preparar_archivos(codigo: str) -> None:
    from app.core.storage import LocalStorage, get_storage

    storage = get_storage()
    if isinstance(storage, LocalStorage):
        storage.preparar_tenant(codigo)
        print("  carpetas de archivos creadas")


# ----------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description="Da de alta una sodería nueva.")
    parser.add_argument("--codigo", required=True, help="Identificador: solmar")
    parser.add_argument("--razon-social", required=True)
    parser.add_argument("--plan", default="basico")
    parser.add_argument("--timezone", default=settings.DEFAULT_TIMEZONE)
    parser.add_argument("--admin-usuario", default="admin")
    parser.add_argument(
        "--admin-password",
        default=None,
        help="Si no se pasa, se genera una y se muestra una sola vez.",
    )
    parser.add_argument(
        "--dsn-override",
        default=None,
        help="Para poner esta sodería en otro servidor de Postgres.",
    )
    parser.add_argument(
        "--rollback",
        action="store_true",
        help="Borra la base y el registro si el alta quedo a medias.",
    )
    args = parser.parse_args()

    codigo = validar_codigo(args.codigo)
    db_name = settings.tenant_db_name(codigo)
    dsn = args.dsn_override or settings.tenant_dsn(db_name)

    init_control_plane()

    if args.rollback:
        print(f"Revirtiendo alta de '{codigo}'...")
        borrar_base(db_name)
        with control_session() as db:
            fila = db.execute(
                select(Tenant).where(Tenant.codigo == codigo)
            ).scalar_one_or_none()
            if fila:
                db.delete(fila)
                db.commit()
                print("  registro eliminado del control plane")
        invalidar_cache(codigo)
        return 0

    with control_session() as db:
        ya_esta = db.execute(
            select(Tenant).where(Tenant.codigo == codigo)
        ).scalar_one_or_none()
        if ya_esta:
            raise SystemExit(
                f"Ya existe la sodería '{codigo}' (estado: {ya_esta.estado.value}). "
                "Usa --rollback si el alta anterior quedo a medias."
            )

        if base_existe(db_name):
            raise SystemExit(
                f"La base '{db_name}' ya existe pero no esta registrada. "
                "Revisala a mano antes de seguir."
            )

        tenant = Tenant(
            codigo=codigo,
            razon_social=args.razon_social,
            db_name=db_name,
            dsn_override=args.dsn_override,
            estado=EstadoTenant.PROVISIONANDO,
            plan=args.plan,
            timezone=args.timezone,
        )
        db.add(tenant)
        db.commit()
        print(f"Alta de '{codigo}' registrada, provisionando...")

    try:
        crear_base(db_name)
        migrar(dsn)
        crear_empresa(dsn, args.razon_social)
        password = crear_admin(dsn, args.admin_usuario, args.admin_password)
        preparar_archivos(codigo)

        problemas = verificar_alta(dsn, args.admin_usuario)
        if problemas:
            raise RuntimeError(
                "El alta quedo incompleta:\n  - " + "\n  - ".join(problemas)
            )

        with control_session() as db:
            fila = db.execute(
                select(Tenant).where(Tenant.codigo == codigo)
            ).scalar_one()
            fila.estado = EstadoTenant.ACTIVO
            db.commit()
        invalidar_cache(codigo)

    except Exception as exc:
        print(f"\nFallo el alta: {exc}", file=sys.stderr)
        print(
            f"El tenant quedo en PROVISIONANDO y no atiende requests.\n"
            f"Para limpiar: python scripts/crear_tenant.py --codigo {codigo} "
            f"--razon-social x --rollback",
            file=sys.stderr,
        )
        return 1

    print(
        f"\nListo.\n"
        f"  sodería:   {args.razon_social}\n"
        f"  codigo:    {codigo}\n"
        f"  base:      {db_name}\n"
        f"  url:       https://{codigo}.{settings.BASE_DOMAIN}\n"
        f"  usuario:   {args.admin_usuario}\n"
        f"  password:  {password}\n"
        f"\nAnota la contraseña ahora: no se vuelve a mostrar."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
