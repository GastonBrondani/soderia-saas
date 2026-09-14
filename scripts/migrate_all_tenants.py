#!/usr/bin/env python
"""
Aplica migraciones a todas las bases de soderias.

Con una base por cliente, `alembic upgrade head` deja de ser un comando y
pasa a ser un proceso. Este script lo maneja y, sobre todo, te dice que paso
en cada base cuando algo sale mal a la mitad.

    python scripts/migrate_all_tenants.py --dry-run     # que versión tiene cada una
    python scripts/migrate_all_tenants.py               # aplicar a todas
    python scripts/migrate_all_tenants.py --solo solmar,lacascada
    python scripts/migrate_all_tenants.py --parar-en-error

Por defecto sigue aunque una base falle, y al final lista cuales quedaron
atrasadas. Es lo que queres en un deploy: que 19 de 20 clientes queden al
dia y no que se corte en el tercero.

Antes de correr esto en produccion: backup. Alembic no tiene "deshacer" para
una migracion que ya corrio a medias en veinte bases.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, text  # noqa: E402

from app.core.control_plane import TenantInfo, listar_tenants  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]


@dataclass
class Resultado:
    codigo: str
    ok: bool
    version_antes: str | None
    version_despues: str | None
    segundos: float
    error: str | None = None


def version_actual(dsn: str) -> str | None:
    engine = create_engine(dsn, pool_pre_ping=True)
    try:
        with engine.connect() as conn:
            existe = conn.execute(
                text(
                    "SELECT 1 FROM information_schema.tables "
                    "WHERE table_name = 'alembic_version'"
                )
            ).scalar()
            if not existe:
                return None
            return conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
    except Exception as exc:
        return f"error: {exc}"
    finally:
        engine.dispose()


def version_head() -> str:
    salida = subprocess.run(
        ["alembic", "heads"], cwd=RAIZ, capture_output=True, text=True
    )
    if salida.returncode != 0:
        raise SystemExit(f"No se pudo leer el head de alembic:\n{salida.stderr}")
    primera = salida.stdout.strip().splitlines()[0] if salida.stdout.strip() else ""
    return primera.split(" ")[0] if primera else "?"


def migrar_uno(tenant: TenantInfo, revision: str) -> Resultado:
    inicio = time.monotonic()
    antes = version_actual(tenant.dsn)

    proceso = subprocess.run(
        ["alembic", "-x", f"url={tenant.dsn}", "upgrade", revision],
        cwd=RAIZ,
        capture_output=True,
        text=True,
    )
    duracion = time.monotonic() - inicio

    if proceso.returncode != 0:
        return Resultado(
            codigo=tenant.codigo,
            ok=False,
            version_antes=antes,
            version_despues=antes,
            segundos=duracion,
            error=(proceso.stderr or proceso.stdout).strip()[-800:],
        )

    return Resultado(
        codigo=tenant.codigo,
        ok=True,
        version_antes=antes,
        version_despues=version_actual(tenant.dsn),
        segundos=duracion,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Migra todas las bases de soderias.")
    parser.add_argument("--revision", default="head")
    parser.add_argument(
        "--solo", default=None, help="Lista de codigos separados por coma."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Solo muestra que version tiene cada base.",
    )
    parser.add_argument(
        "--parar-en-error",
        action="store_true",
        help="Corta en la primera base que falle.",
    )
    parser.add_argument(
        "--incluir-suspendidos",
        action="store_true",
        help="Migrar tambien las soderias suspendidas.",
    )
    args = parser.parse_args()

    tenants = listar_tenants(incluir_suspendidos=args.incluir_suspendidos)

    if args.solo:
        pedidos = {c.strip().lower() for c in args.solo.split(",") if c.strip()}
        tenants = [t for t in tenants if t.codigo in pedidos]
        faltantes = pedidos - {t.codigo for t in tenants}
        if faltantes:
            print(f"No se encontraron: {', '.join(sorted(faltantes))}", file=sys.stderr)

    if not tenants:
        print("No hay soderias para migrar.")
        return 0

    head = version_head()
    print(f"Revision objetivo: {args.revision} (head = {head})")
    print(f"Soderias: {len(tenants)}\n")

    if args.dry_run:
        ancho = max(len(t.codigo) for t in tenants)
        atrasadas = 0
        for t in tenants:
            actual = version_actual(t.dsn)
            al_dia = actual == head
            atrasadas += 0 if al_dia else 1
            marca = "  al dia" if al_dia else "  PENDIENTE"
            print(f"  {t.codigo.ljust(ancho)}  {actual or '(sin migrar)'}{marca}")
        print(f"\n{atrasadas} de {len(tenants)} necesitan migracion.")
        return 0

    resultados: list[Resultado] = []
    for i, tenant in enumerate(tenants, 1):
        print(f"[{i}/{len(tenants)}] {tenant.codigo} ... ", end="", flush=True)
        resultado = migrar_uno(tenant, args.revision)
        resultados.append(resultado)

        if resultado.ok:
            if resultado.version_antes == resultado.version_despues:
                print(f"sin cambios ({resultado.segundos:.1f}s)")
            else:
                print(
                    f"{resultado.version_antes or 'vacia'} -> "
                    f"{resultado.version_despues} ({resultado.segundos:.1f}s)"
                )
        else:
            print(f"ERROR ({resultado.segundos:.1f}s)")
            if args.parar_en_error:
                print(f"\n{resultado.error}", file=sys.stderr)
                print(
                    f"\nSe corto en '{resultado.codigo}'. "
                    f"{len(tenants) - i} soderias quedaron sin migrar.",
                    file=sys.stderr,
                )
                return 1

    fallidos = [r for r in resultados if not r.ok]
    print(f"\n{'-' * 60}")
    print(f"Migradas: {len(resultados) - len(fallidos)} / {len(resultados)}")

    if fallidos:
        print(f"\nFallaron {len(fallidos)}:")
        for r in fallidos:
            print(f"\n  {r.codigo} (quedo en {r.version_antes or 'vacia'})")
            for linea in (r.error or "").splitlines()[-6:]:
                print(f"    {linea}")
        print(
            "\nEstas soderias siguen con el esquema viejo. Si la version nueva "
            "de la app no es compatible hacia atras, no la despliegues hasta "
            "resolverlo."
        )
        return 1

    print("Todas al dia.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
