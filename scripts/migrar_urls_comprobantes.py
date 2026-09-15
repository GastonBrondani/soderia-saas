#!/usr/bin/env python
"""
Migra comprobantes con el formato de URL viejo (de antes del multi-tenant)
al formato nuevo de app/core/storage.py.

Antes (single-tenant, todo en una carpeta plana):
    /docs/comprobantes/pagos/pago_5.pdf
    /docs/comprobantes/pedidos/pedido_12.pdf

Ahora (una carpeta por sodería, particionado por año/mes de carga):
    /archivos/<codigo>/comprobantes/pagos/2024/03/pago_5.pdf

Este script es para el dia que se importen los datos de la sodería que ya
esta en produccion (single-tenant, sin este esquema) a una base de este
sistema nuevo: copia los archivos fisicos a su carpeta de tenant/año/mes y
reescribe documentos.url_archivo. Un tenant creado desde cero con
crear_tenant.py nunca va a tener filas con el formato viejo, así que no
hace falta correr esto en ese caso.

Uso:
    # Ver que haria, sin tocar nada
    python scripts/migrar_urls_comprobantes.py --codigo solmar \
        --origen /ruta/al/storage/viejo --dry-run

    # Aplicar
    python scripts/migrar_urls_comprobantes.py --codigo solmar \
        --origen /ruta/al/storage/viejo

--origen es la carpeta raíz del sistema viejo (monotenant), que tenia esta
forma:
    <origen>/comprobantes/pagos/<archivo>
    <origen>/comprobantes/pedidos/<archivo>

El año/mes de la carpeta nueva sale de documentos.fecha_carga: es el mismo
criterio que usa storage.guardar() para un comprobante nuevo (fecha en la
que se subio, no la fecha del pago/pedido en si).

Los archivos originales NO se borran. Una vez verificado que todo migro
bien, se borran a mano.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402

from app.core.control_plane import buscar_tenant, init_control_plane  # noqa: E402
from app.core.database import sesion_tenant  # noqa: E402
from app.core.storage import (  # noqa: E402
    CATEGORIA_COMPROBANTES_PAGOS,
    CATEGORIA_COMPROBANTES_PEDIDOS,
    get_storage,
    nombre_seguro,
)
from app.core.tenancy import usar_tenant  # noqa: E402
from app.db import models_registry  # noqa: E402, F401 (registra todos los modelos para el ORM)
from app.features.documentos.models.documentos import Documentos  # noqa: E402

# /docs/comprobantes/pagos/pago_5.pdf  (el /docs/ es opcional: algunas filas
# ya lo tenian sin el prefijo)
RE_URL_VIEJA = re.compile(r"^/?(?:docs/)?comprobantes/(pagos|pedidos)/([^/]+)$")


def clasificar(url_archivo: str) -> tuple[str, str] | None:
    """(categoria, nombre_archivo) si la URL es del formato viejo, None si ya es nueva."""
    m = RE_URL_VIEJA.match(url_archivo.strip())
    if not m:
        return None
    carpeta, nombre = m.groups()
    categoria = (
        CATEGORIA_COMPROBANTES_PAGOS if carpeta == "pagos" else CATEGORIA_COMPROBANTES_PEDIDOS
    )
    return categoria, nombre


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Migra documentos.url_archivo del formato viejo (single-tenant) al nuevo."
    )
    parser.add_argument("--codigo", required=True, help="Codigo del tenant, ej: solmar")
    parser.add_argument(
        "--origen",
        required=True,
        type=Path,
        help="Carpeta raiz del storage viejo (contiene comprobantes/pagos y comprobantes/pedidos)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Solo muestra que haria, no toca nada"
    )
    args = parser.parse_args()

    init_control_plane()
    tenant = buscar_tenant(args.codigo, usar_cache=False)
    storage = get_storage()

    with usar_tenant(tenant), sesion_tenant() as db:
        filas = db.execute(select(Documentos).order_by(Documentos.id_documento)).scalars().all()

        candidatas = [
            (doc, *resultado)
            for doc in filas
            if (resultado := clasificar(doc.url_archivo)) is not None
        ]

        if not candidatas:
            print(f"'{tenant.codigo}': ningun documento con formato de URL viejo. Nada para hacer.")
            return 0

        print(
            f"'{tenant.codigo}': {len(candidatas)} de {len(filas)} documento(s) "
            "con formato viejo.\n"
        )

        migrados = 0
        con_problemas = 0
        for doc, categoria, nombre_original in candidatas:
            origen = args.origen / categoria / nombre_original
            clave_nueva = (
                f"{tenant.codigo}/{categoria}/"
                f"{doc.fecha_carga:%Y/%m}/{nombre_seguro(nombre_original)}"
            )

            if storage.existe(clave_nueva):
                print(f"  [SALTEADO] doc {doc.id_documento}: ya existe {clave_nueva}")
                con_problemas += 1
                continue

            if not origen.is_file():
                print(f"  [FALTA ARCHIVO] doc {doc.id_documento}: no se encontro {origen}")
                con_problemas += 1
                continue

            print(f"  doc {doc.id_documento}: {origen} -> {clave_nueva}")

            if not args.dry_run:
                destino = storage.ruta_absoluta(clave_nueva)
                destino.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(origen, destino)
                doc.url_archivo = storage.url_publica(clave_nueva)

            migrados += 1

        if args.dry_run:
            print(
                f"\n(dry-run) {migrados} se migrarian, {con_problemas} con problemas. "
                "No se escribio nada."
            )
            return 0

        db.commit()
        print(f"\n{migrados} migrados, {con_problemas} con problemas (ver arriba).")
        print("Los archivos originales no se borraron. Verifica antes de borrarlos a mano.")
        return 1 if con_problemas else 0


if __name__ == "__main__":
    raise SystemExit(main())
