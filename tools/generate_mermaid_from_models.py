#!/usr/bin/env python3
"""
Genera un diagrama Mermaid (erDiagram) a partir de los modelos SQLAlchemy en app/models.

Salida: backend/diagrams/db_er.mmd

Este script hace parsing estático de los archivos Python en `backend/app/models` buscando
`__tablename__`, columnas definidas con `mapped_column` y occurrences de `ForeignKey("table.col")`.

No requiere instalar dependencias externas (usa stdlib).
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = ROOT / "app" / "models"
OUT_DIR = ROOT / "diagrams"
OUT_FILE = OUT_DIR / "db_er.mmd"

TABLENAME_RE = re.compile(r"__tablename__\s*=\s*['\"]([a-zA-Z0-9_]+)['\"]")
# allow mapped_column args that span multiple lines (DOTALL)
MAPPED_COL_RE = re.compile(r"^(\s*)([a-zA-Z0-9_]+)\s*:\s*Mapped\[.*?\]\s*=\s*mapped_column\((.*?)\)", re.MULTILINE | re.DOTALL)
FOREIGNKEY_RE = re.compile(r"ForeignKey\(\s*['\"]([a-zA-Z0-9_\.]+)['\"]", re.DOTALL)
PK_RE = re.compile(r"primary_key\s*=\s*True")


def parse_model(path: Path):
    text = path.read_text(encoding="utf-8")
    table = None
    m = TABLENAME_RE.search(text)
    if m:
        table = m.group(1)
    else:
        return None

    cols = []
    # find mapped_column declarations (simple heuristic)
    for match in MAPPED_COL_RE.finditer(text):
        name = match.group(2)
        args = match.group(3)
        is_pk = bool(PK_RE.search(args))
        fk = None
        m_fk = FOREIGNKEY_RE.search(args)
        if m_fk:
            fk_full = m_fk.group(1)
            # fk may be like schema.table.col or table.col
            fk_table = fk_full.split(".")[0]
            fk = fk_table
        cols.append({"name": name, "pk": is_pk, "fk_table": fk})

    return {"table": table, "cols": cols, "file": str(path.name)}


def main():
    models = []
    for p in sorted(MODELS_DIR.glob("*.py")):
        if p.name.startswith("__"):
            continue
        parsed = parse_model(p)
        if parsed:
            models.append(parsed)

    # map of table name -> model info (not used directly but easy to build if needed)
    # tables = {m["table"]: m for m in models}

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    lines = ["erDiagram\n"]

    # Entities
    for m in models:
        t = m["table"]
        lines.append(f"    {t} {{")
        for c in m["cols"]:
            # Mermaid's erDiagram expects each attribute line to start with a type
            # e.g. `int id PK` or `string name`. We use simple heuristics:
            # - primary keys -> int
            # - foreign keys -> int
            # - otherwise -> string
            if c["pk"]:
                col_line = f"int {c['name']} PK"
            elif c.get("fk_table"):
                col_line = f"int {c['name']} FK"
            else:
                col_line = f"string {c['name']}"
            lines.append(f"        {col_line}")
        lines.append("    }")

    # Relationships
    rels = set()
    # detect association tables (two fks both pk) for m:n
    assoc_tables = {}
    for m in models:
        fks = [c for c in m["cols"] if c["fk_table"]]
        pk_count = sum(1 for c in m["cols"] if c["pk"])
        if len(fks) == 2 and pk_count >= 2:
            assoc_tables[m["table"]] = fks

    for m in models:
        child = m["table"]
        for c in m["cols"]:
            if c["fk_table"]:
                parent = c["fk_table"]
                # if association table, will be handled separately
                if child in assoc_tables:
                    continue
                # multiplicity: parent 1 -- child many
                rel = f"{parent} ||--o{{ {child} : \"{c['name']}\""
                rels.add(rel)

    # association tables produce m:n between referenced tables
    for assoc, fks in assoc_tables.items():
        t1 = fks[0]["fk_table"]
        t2 = fks[1]["fk_table"]
        # literal '}' and '{' must be escaped in f-strings as '}}' and '{{'
        rel = f"{t1} }}o--o{{ {t2} : \"{assoc}\""
        rels.add(rel)

    for r in sorted(rels):
        lines.append(f"    {r}")

    content = "\n".join(lines) + "\n"
    OUT_FILE.write_text(content, encoding="utf-8")
    print(f"Mermaid ER diagram generado en: {OUT_FILE}")


if __name__ == "__main__":
    main()
