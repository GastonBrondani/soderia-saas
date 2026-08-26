"""Genera diagrams/db_er.mmd a partir de los modelos SQLAlchemy en app/models.

Ejecución: python scripts/generate_db_er.py
"""
from __future__ import annotations
import importlib
import pkgutil
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Asegurarse que el proyecto esté en el path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Evitar dependencia en dotenv si no está instalada (no es necesario para inspeccionar metadata)
import types
import types as _types
import os
# Proveer DATABASE_URL por defecto para que create_engine no falle al importar
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

if "dotenv" not in sys.modules:
    _m = _types.ModuleType("dotenv")
    _m.load_dotenv = lambda *a, **k: None
    sys.modules["dotenv"] = _m

from app.core.database import Base

OUTPUT = Path(ROOT) / "diagrams" / "db_er.mmd"


def import_models(package_name: str = "app.models") -> None:
    """Importa todos los módulos en app.models para que Base.metadata se llene."""
    package = importlib.import_module(package_name)
    package_path = Path(package.__file__).parent
    for finder, name, ispkg in pkgutil.iter_modules([str(package_path)]):
        module_name = f"{package_name}.{name}"
        try:
            importlib.import_module(module_name)
        except Exception as e:
            print(f"Advertencia: no se pudo importar {module_name}: {e}")


def column_type_repr(col) -> str:
    # Simplified type representation
    try:
        return col.type.__class__.__name__
    except Exception:
        return "string"


def main():
    import_models()

    lines: List[str] = []
    lines.append("erDiagram\n")

    # Tablas y columnas
    for tname, table in Base.metadata.tables.items():
        lines.append(f"    {tname} {{")
        for col in table.columns:
            pk = " PK" if col.primary_key else ""
            fk = " FK" if col.foreign_keys else ""
            coltype = column_type_repr(col)
            lines.append(f"        {col.name} {coltype}{pk}{fk}")
        lines.append("    }")

    lines.append("")

    # Relaciones: por cada foreign key, representamos referenced_table ||--o{ referencing_table : "fk_column"
    rel_lines = set()
    for tname, table in Base.metadata.tables.items():
        for col in table.columns:
            for fk in col.foreign_keys:
                ref_table = fk.column.table.name
                # build relation: ref_table ||--o{ table : "col.name"
                rel = f"    {ref_table} ||--o{{ {tname} : \"{col.name}\""
                rel_lines.add(rel)

    for rl in sorted(rel_lines):
        lines.append(rl)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Generado {OUTPUT}")


if __name__ == "__main__":
    main()
