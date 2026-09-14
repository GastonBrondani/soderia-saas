"""
Verifica que todos los modelos esten en el registry.

El fallo que previene es feo: agregas un modelo en un feature, te olvidas de
importarlo en app/db/models_registry.py, corres `alembic revision
--autogenerate` y Alembic, que no ve esa tabla en la metadata pero si en la
base, genera un `op.drop_table()`. Si la migracion se aplica sin leerla, se
pierden datos.

Este test recorre app/features buscando clases que hereden de Base y compara
con lo que el registry efectivamente carga.
"""

from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path

import pytest

RAIZ_FEATURES = Path(__file__).resolve().parents[1] / "app" / "features"


def _modulos_de_modelos() -> list[str]:
    if not RAIZ_FEATURES.exists():
        return []
    modulos = []
    for info in pkgutil.walk_packages(
        [str(RAIZ_FEATURES)], prefix="app.features."
    ):
        nombre = info.name.rsplit(".", 1)[-1]
        if nombre == "models" or nombre.startswith("models"):
            modulos.append(info.name)
        elif ".models." in info.name:
            modulos.append(info.name)
    return modulos


def test_registry_incluye_todos_los_modelos() -> None:
    if not RAIZ_FEATURES.exists():
        pytest.skip("Todavia no existe app/features (paso 2 pendiente).")

    from app.db.base import Base
    import app.db.models_registry  # noqa: F401

    del_registry = set(Base.metadata.tables)

    # Importar cada modulo de modelos fuerza el registro de sus tablas.
    for modulo in _modulos_de_modelos():
        importlib.import_module(modulo)

    todas = set(Base.metadata.tables)
    faltantes = todas - del_registry

    assert not faltantes, (
        "Estos modelos NO estan importados en app/db/models_registry.py:\n  "
        + "\n  ".join(sorted(faltantes))
        + "\n\nSi corres 'alembic revision --autogenerate' asi, la migracion "
        "va a incluir un drop_table de cada una."
    )


def test_ninguna_tabla_sin_primary_key() -> None:
    if not RAIZ_FEATURES.exists():
        pytest.skip("Todavia no existe app/features (paso 2 pendiente).")

    from app.db.base import Base
    import app.db.models_registry  # noqa: F401

    sin_pk = [
        nombre
        for nombre, tabla in Base.metadata.tables.items()
        if not tabla.primary_key.columns
    ]
    assert not sin_pk, f"Tablas sin clave primaria: {sin_pk}"
