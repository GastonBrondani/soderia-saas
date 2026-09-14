#!/usr/bin/env python
"""
PASO 0: la red de seguridad.

Esto es lo primero que hay que correr, ANTES de mover un solo archivo.

Toma el OpenAPI que FastAPI ya genera solo, lo normaliza a un "contrato"
estable y lo guarda. Despues del refactor, el test tests/test_api_contract.py
vuelve a generarlo y compara. Si desaparecio una ruta, cambio un parametro o
se cayo un campo de una respuesta, el test te dice exactamente cual.

Por que esto y no tests de endpoints: no necesita base de datos, corre en
dos segundos y cubre el 90% de lo que un refactor estructural puede romper
(routers que quedaron sin registrar, imports que se pisan, prefijos mal
armados). Los tests de negocio vienen despues, feature por feature.

Uso en el repo VIEJO, antes de tocar nada:

    python scripts/snapshot_openapi.py --salida tests/snapshots/openapi_baseline.json

Uso en el repo NUEVO, para comparar:

    pytest tests/test_api_contract.py

Bonus: al generarlo sobre tu codigo actual vas a ver un aviso por las rutas
duplicadas de listaPrecios.py (obtener_lista y listar_productos_con_precio
estan definidas dos veces). Es el bug que te marque.
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

MAX_PROFUNDIDAD = 6


def cargar_app(ruta: str):
    """Importa 'modulo:atributo' y devuelve la app de FastAPI."""
    modulo_str, _, atributo = ruta.partition(":")
    modulo = importlib.import_module(modulo_str)
    return getattr(modulo, atributo or "app")


def _resolver(nodo: Any, componentes: dict, profundidad: int = 0) -> Any:
    """Sigue los $ref para poder comparar formas y no nombres de clase.

    Importa porque el refactor renombra schemas: ClienteDiaVisitaOut puede
    pasar a llamarse DiaVisitaOut sin que la API cambie para el cliente.
    Comparar por nombre daria falsos positivos.
    """
    if profundidad > MAX_PROFUNDIDAD or not isinstance(nodo, dict):
        return nodo

    if "$ref" in nodo:
        nombre = nodo["$ref"].rsplit("/", 1)[-1]
        destino = componentes.get(nombre)
        if destino is None:
            return {"tipo": "desconocido"}
        return _resolver(destino, componentes, profundidad + 1)

    if nodo.get("type") == "array":
        return {
            "tipo": "array",
            "items": _resolver(nodo.get("items", {}), componentes, profundidad + 1),
        }

    if "properties" in nodo:
        requeridos = set(nodo.get("required", []))
        return {
            "tipo": "objeto",
            "campos": sorted(
                f"{nombre}{'!' if nombre in requeridos else ''}"
                for nombre in nodo["properties"]
            ),
        }

    for clave in ("anyOf", "oneOf", "allOf"):
        if clave in nodo:
            return {
                "tipo": clave,
                "opciones": [
                    _resolver(o, componentes, profundidad + 1) for o in nodo[clave]
                ],
            }

    tipo = nodo.get("type")
    return {"tipo": tipo} if tipo else {"tipo": "any"}


def normalizar(openapi: dict) -> dict:
    """Reduce el OpenAPI a lo que le importa a quien consume la API."""
    componentes = openapi.get("components", {}).get("schemas", {})
    contrato: dict[str, Any] = {}

    for ruta, metodos in sorted(openapi.get("paths", {}).items()):
        for metodo, op in sorted(metodos.items()):
            if metodo.lower() not in {
                "get", "post", "put", "patch", "delete", "head", "options"
            }:
                continue

            parametros = sorted(
                f"{p.get('name')}:{p.get('in')}:"
                f"{'req' if p.get('required') else 'opt'}"
                for p in op.get("parameters", [])
            )

            body = None
            if rb := op.get("requestBody"):
                contenido = rb.get("content", {}).get("application/json", {})
                if esquema := contenido.get("schema"):
                    body = {
                        "requerido": bool(rb.get("required")),
                        "forma": _resolver(esquema, componentes),
                    }

            respuestas = {}
            for codigo, r in sorted(op.get("responses", {}).items()):
                contenido = r.get("content", {}).get("application/json", {})
                respuestas[codigo] = (
                    _resolver(contenido["schema"], componentes)
                    if contenido.get("schema")
                    else None
                )

            contrato[f"{metodo.upper()} {ruta}"] = {
                "tags": sorted(op.get("tags", [])),
                "parametros": parametros,
                "body": body,
                "respuestas": respuestas,
                "protegido": bool(op.get("security")),
            }

    return contrato


def detectar_duplicados(app) -> list[str]:
    """Rutas registradas mas de una vez.

    FastAPI se queda con la primera y las siguientes son codigo muerto que
    parece vivo. Es un error silencioso: leyendo el archivo ves la segunda
    definicion y asumis que es la que corre.
    """
    vistas: dict[tuple[str, str], int] = {}
    for ruta in app.routes:
        for metodo in getattr(ruta, "methods", []) or []:
            clave = (metodo, getattr(ruta, "path", ""))
            vistas[clave] = vistas.get(clave, 0) + 1
    return [
        f"{metodo} {path} (definida {n} veces)"
        for (metodo, path), n in sorted(vistas.items())
        if n > 1
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--app", default="app.main:app")
    parser.add_argument("--salida", default="tests/snapshots/openapi_baseline.json")
    args = parser.parse_args()

    app = cargar_app(args.app)
    contrato = normalizar(app.openapi())

    salida = Path(args.salida)
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(
        json.dumps(contrato, indent=2, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )

    print(f"Contrato guardado en {salida}")
    print(f"  {len(contrato)} operaciones")
    tags = sorted({t for op in contrato.values() for t in op["tags"]})
    print(f"  {len(tags)} tags: {', '.join(tags[:8])}{'...' if len(tags) > 8 else ''}")
    sin_proteger = [k for k, v in contrato.items() if not v["protegido"]]
    if sin_proteger:
        print(f"\n  {len(sin_proteger)} operaciones sin autenticacion:")
        for op in sin_proteger[:10]:
            print(f"    {op}")

    if duplicadas := detectar_duplicados(app):
        print(f"\n  ATENCION: {len(duplicadas)} rutas duplicadas.")
        print("  FastAPI usa la primera; las demas nunca se ejecutan.")
        for d in duplicadas:
            print(f"    {d}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
