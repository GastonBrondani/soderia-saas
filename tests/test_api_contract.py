"""
Compara la API actual contra el snapshot tomado antes del refactor.

Este es el test que te deja mover 120 archivos sin miedo. No valida logica
de negocio: valida que la superficie de la API no cambio. Si un router quedo
sin registrar en api/router.py, si un prefijo se escribio mal o si un schema
perdio un campo, falla y te dice cual.

Cuando un cambio es intencional (agregas un endpoint nuevo, sacas uno viejo),
se regenera el snapshot:

    python scripts/snapshot_openapi.py

y se commitea junto con el cambio. Asi el diff del snapshot queda en el
historial de git y se revisa como cualquier otro codigo.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.snapshot_openapi import detectar_duplicados, normalizar

SNAPSHOT = Path(__file__).parent / "snapshots" / "openapi_baseline.json"


@pytest.fixture(scope="module")
def baseline() -> dict:
    if not SNAPSHOT.exists():
        pytest.skip(
            f"No hay snapshot en {SNAPSHOT}. Generalo con:\n"
            f"  python scripts/snapshot_openapi.py"
        )
    return json.loads(SNAPSHOT.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def actual() -> dict:
    from app.main import app

    return normalizar(app.openapi())


def test_no_desaparecieron_operaciones(baseline: dict, actual: dict) -> None:
    faltantes = sorted(set(baseline) - set(actual))
    assert not faltantes, (
        f"{len(faltantes)} operaciones desaparecieron de la API.\n"
        "Causa tipica: un router que quedo sin incluir en api/router.py, "
        "o un prefijo mal escrito.\n\n  "
        + "\n  ".join(faltantes[:25])
    )


def test_parametros_iguales(baseline: dict, actual: dict) -> None:
    problemas = []
    for clave in sorted(set(baseline) & set(actual)):
        antes = baseline[clave]["parametros"]
        ahora = actual[clave]["parametros"]
        if antes != ahora:
            problemas.append(
                f"{clave}\n    antes: {antes}\n    ahora: {ahora}"
            )
    assert not problemas, "Cambiaron parametros:\n\n" + "\n\n".join(problemas[:15])


def test_bodies_iguales(baseline: dict, actual: dict) -> None:
    problemas = []
    for clave in sorted(set(baseline) & set(actual)):
        if baseline[clave]["body"] != actual[clave]["body"]:
            problemas.append(
                f"{clave}\n    antes: {baseline[clave]['body']}"
                f"\n    ahora: {actual[clave]['body']}"
            )
    assert not problemas, (
        "Cambio el cuerpo esperado de algunas operaciones. Si moviste un "
        "schema y le cambiaste campos sin querer, aca se ve:\n\n"
        + "\n\n".join(problemas[:15])
    )


def test_respuestas_iguales(baseline: dict, actual: dict) -> None:
    problemas = []
    for clave in sorted(set(baseline) & set(actual)):
        antes = baseline[clave]["respuestas"]
        ahora = actual[clave]["respuestas"]
        if antes != ahora:
            problemas.append(
                f"{clave}\n    antes: {antes}\n    ahora: {ahora}"
            )
    assert not problemas, (
        "Cambiaron respuestas. Esto rompe la app de Flutter:\n\n"
        + "\n\n".join(problemas[:15])
    )


def test_no_se_desprotegieron_endpoints(baseline: dict, actual: dict) -> None:
    """El refactor no puede dejar sin autenticacion algo que la tenia."""
    desprotegidos = [
        clave
        for clave in sorted(set(baseline) & set(actual))
        if baseline[clave]["protegido"] and not actual[clave]["protegido"]
    ]
    assert not desprotegidos, (
        "Estas operaciones perdieron la autenticacion:\n  "
        + "\n  ".join(desprotegidos)
    )


@pytest.mark.xfail(
    reason=(
        "Duplicados preexistentes anotados en 'Deuda tecnica conocida' de "
        "CONTEXTO_MIGRACION.md (listaPrecios.py x2, stock.py). Se arreglan "
        "recien en el paso 3: no se toca logica fuera de ese paso. Sacar "
        "este marcador cuando esos 3 se corrijan."
    ),
    strict=True,
)
def test_sin_rutas_duplicadas() -> None:
    """Una ruta registrada dos veces significa codigo muerto que parece vivo.

    Tu listaPrecios.py tiene este problema hoy con obtener_lista y
    listar_productos_con_precio. Este test evita que vuelva a pasar.
    """
    from app.main import app

    duplicadas = detectar_duplicados(app)
    assert not duplicadas, (
        "Rutas registradas mas de una vez. FastAPI usa la primera:\n  "
        + "\n  ".join(duplicadas)
    )


def test_operaciones_nuevas_informativo(baseline: dict, actual: dict) -> None:
    """No falla: solo lista lo agregado, para revisarlo en el pull request."""
    nuevas = sorted(set(actual) - set(baseline))
    if nuevas:
        print(f"\n{len(nuevas)} operaciones nuevas desde el snapshot:")
        for op in nuevas[:25]:
            print(f"  + {op}")
