#!/usr/bin/env python
"""
PASO 2: mover el codigo a la estructura por features.

Que hace, en este orden:

  1. Escanea app/models, app/routers, app/services, app/schemas.
  2. Decide a que feature va cada archivo segun la tabla ASIGNACION.
  3. Los que no puede ubicar, los REPORTA y frena. No adivina.
  4. Mueve con `git mv` para no perder el historial de cada archivo.
  5. Renombra camelCase -> snake_case.
  6. Reescribe los imports en todo el repo, resolviendo tambien los
     agregados (`from app.models import Cliente, Pedido`).
  7. Genera los __init__.py, el models_registry.py y el api/router.py.

No cambia una sola linea de logica. Solo mueve archivos y ajusta imports.
Por eso el test del paso 0 tiene que quedar en verde antes y despues: si
falla, el movimiento rompio algo.

Uso:

    python scripts/migrar_estructura.py --dry-run     # ver el plan completo
    python scripts/migrar_estructura.py --solo-plan   # exportar el plan a JSON
    python scripts/migrar_estructura.py               # ejecutar

Antes de correrlo en serio: commiteá todo. El script pide un repo limpio.
Si algo sale mal: `git reset --hard`.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

# ======================================================================
# TABLA DE ASIGNACION
#
# Clave: nombre base del archivo, sin extension y sin el sufijo "Service".
#        clienteCuenta.py, clienteCuentaService.py y schemas/clienteCuenta.py
#        comparten la clave "clienteCuenta".
# Valor: ruta del feature dentro de app/features/
#
# Si agregaste archivos despues de que armamos esto, el script te los va a
# listar como desconocidos. Agregalos aca y volvé a correr.
# ======================================================================

ASIGNACION: dict[str, str] = {
    # --- Autenticacion y usuarios ---
    "auth": "auth",
    "usuario": "usuarios",
    "rol": "usuarios",
    "usuarioRol": "usuarios",
    # --- Entidades base ---
    "persona": "personas",
    "empresa": "empresas",
    "cuentaBancariaEmpresa": "empresas",
    "empleado": "empleados",
    # --- Tablas maestras ---
    "diaSemana": "maestros",
    "medioPago": "maestros",
    "tipoEvento": "maestros",
    "tipoMovimientoCaja": "maestros",
    # --- Clientes ---
    "cliente": "clientes",
    "direccionCliente": "clientes",
    "emailCliente": "clientes",
    "telefonoCliente": "clientes",
    "clienteCuenta": "clientes",
    "productoCliente": "clientes",
    # --- Catalogo ---
    "catalogo": "catalogo",
    "producto": "catalogo/productos",
    "combo": "catalogo/combos",
    "comboProducto": "catalogo/combos",
    "servicios": "catalogo/servicios",
    "clienteServicio": "catalogo/servicios",
    "clienteServicioPeriodo": "catalogo/servicios",
    "listaDePrecios": "catalogo/listas_precios",
    "listaPrecios": "catalogo/listas_precios",
    "listaPrecio": "catalogo/listas_precios",
    "listaPrecioProducto": "catalogo/listas_precios",
    "listaPrecioCombo": "catalogo/listas_precios",
    "listaPrecioServicio": "catalogo/listas_precios",
    "listaPrecioItem": "catalogo/listas_precios",
    "precioItem": "catalogo/listas_precios",
    # --- Inventario ---
    "stock": "inventario/stock",
    "movimientoStock": "inventario/movimientos",
    "movimientoEnvaseCliente": "inventario/envases",
    "envaseCliente": "inventario/envases",
    # --- Operaciones ---
    "pedido": "pedidos",
    "pedidoProducto": "pedidos",
    "pago": "pagos",
    "idempotency": "pagos",
    "cajaEmpresa": "caja",
    # --- Repartos ---
    "camionReparto": "repartos/camiones",
    "recorrido": "repartos/recorridos",
    "repartoDia": "repartos/repartos_dia",
    "clienteRepartoDia": "repartos/repartos_dia",
    "visita": "repartos/visitas",
    "agenda": "repartos/agenda",
    "clienteDiaSemana": "repartos/agenda",
    # --- Transversales ---
    "bootstrap": "sincronizacion",
    "documentos": "documentos",
    "comprobantePago": "documentos",
    "comprobantePedido": "documentos",
    "historico": "auditoria",
    "enumsHistorico": "auditoria",
    "reportes": "reportes",
}

# Archivos que NO se mueven.
IGNORAR = {
    "__init__.py",
    "router.py",  # app/api/router.py se regenera
    "deps.py",    # app/api/deps.py se maneja aparte
}

# Carpetas viejas que el script vacia.
ORIGENES = {
    "models": "models",
    "routers": "router",
    "services": "service",
    "schemas": "schemas",
    "queries": "queries",
}

# Carpetas del repo donde hay que reescribir imports.
RAICES_CODIGO = ["app", "alembic", "scripts", "tests"]

# Nombres que aparecen en casi todos los archivos y no sirven para resolver
# imports agregados.
NOMBRES_UBICUOS = {
    "router",
    "logger",
    "Base",
    "SCHEMA",
    "oauth2_scheme",
    "settings",
    "TWOPLACES",
}


# ======================================================================
# Utilidades
# ======================================================================


def a_snake(nombre: str) -> str:
    """clienteRepartoDia -> cliente_reparto_dia; MailCliente -> mail_cliente"""
    s = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", nombre)
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s)
    return s.lower()


def clave_de(nombre_archivo: str, carpeta: str) -> str:
    """Nombre base normalizado para buscar en ASIGNACION."""
    base = Path(nombre_archivo).stem
    if carpeta == "services" and base.endswith("Service"):
        base = base[: -len("Service")]
    return base


def correr(cmd: list[str], cwd: Path) -> tuple[int, str]:
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return proc.returncode, (proc.stdout + proc.stderr).strip()


# ======================================================================
# Plan de movimiento
# ======================================================================


@dataclass
class Movimiento:
    origen: Path            # relativa a la raiz del repo
    destino: Path
    feature: str
    tipo: str               # models | router | service | schemas | queries
    simbolos: list[str] = field(default_factory=list)

    @property
    def modulo_viejo(self) -> str:
        return ".".join(self.origen.with_suffix("").parts)

    @property
    def modulo_nuevo(self) -> str:
        return ".".join(self.destino.with_suffix("").parts)


@dataclass
class Plan:
    movimientos: list[Movimiento] = field(default_factory=list)
    desconocidos: list[Path] = field(default_factory=list)

    @property
    def features(self) -> dict[str, list[Movimiento]]:
        agrupado: dict[str, list[Movimiento]] = defaultdict(list)
        for m in self.movimientos:
            agrupado[m.feature].append(m)
        return dict(sorted(agrupado.items()))


def simbolos_publicos(ruta: Path) -> list[str]:
    """Clases y funciones de nivel superior de un archivo.

    Se usa para resolver los imports agregados: cuando alguien escribe
    `from app.models import Cliente, Pedido`, hay que saber en que modulo
    nuevo quedo cada nombre.
    """
    try:
        arbol = ast.parse(ruta.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        return []

    nombres = []
    for nodo in arbol.body:
        if isinstance(nodo, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            if not nodo.name.startswith("_"):
                nombres.append(nodo.name)
        elif isinstance(nodo, ast.Assign):
            for destino in nodo.targets:
                if isinstance(destino, ast.Name) and not destino.id.startswith("_"):
                    nombres.append(destino.id)
    # `router`, `logger` y compañia existen en casi todos los archivos.
    # Dejarlos en el mapa generaria colisiones falsas en cada modulo.
    return [n for n in nombres if n not in NOMBRES_UBICUOS]


def armar_plan(raiz: Path) -> Plan:
    plan = Plan()
    # Cuantos archivos de cada tipo cayeron en cada feature. Si hay mas de
    # uno, en vez de service.py se arma un paquete services/.
    conteo: dict[tuple[str, str], int] = defaultdict(int)

    encontrados: list[tuple[Path, str, str, str]] = []

    for carpeta, tipo in ORIGENES.items():
        directorio = raiz / "app" / carpeta
        if not directorio.is_dir():
            continue
        for archivo in sorted(directorio.rglob("*.py")):
            if archivo.name in IGNORAR:
                continue
            relativa = archivo.relative_to(raiz)
            clave = clave_de(archivo.name, carpeta)
            feature = ASIGNACION.get(clave)
            if feature is None:
                plan.desconocidos.append(relativa)
                continue
            encontrados.append((archivo, relativa, feature, tipo))
            conteo[(feature, tipo)] += 1

    for archivo, relativa, feature, tipo in encontrados:
        base = a_snake(clave_de(archivo.name, archivo.parent.name))
        varios = conteo[(feature, tipo)] > 1

        if tipo == "models":
            # Los modelos SIEMPRE van a un paquete models/, uno por archivo.
            # Concatenarlos en un models.py unico seria un merge de codigo,
            # no un movimiento, y eso ya no es reversible con git.
            destino = Path("app/features") / feature / "models" / f"{base}.py"
        elif tipo == "schemas":
            destino = (
                Path("app/features") / feature / "schemas" / f"{base}.py"
                if varios
                else Path("app/features") / feature / "schemas.py"
            )
        elif tipo == "service":
            destino = (
                Path("app/features") / feature / "services" / f"{base}.py"
                if varios
                else Path("app/features") / feature / "service.py"
            )
        elif tipo == "queries":
            destino = (
                Path("app/features") / feature / "queries" / f"{base}.py"
                if varios
                else Path("app/features") / feature / "queries.py"
            )
        else:  # router
            destino = (
                Path("app/features") / feature / "routers" / f"{base}.py"
                if varios
                else Path("app/features") / feature / "router.py"
            )

        plan.movimientos.append(
            Movimiento(
                origen=relativa,
                destino=destino,
                feature=feature,
                tipo=tipo,
                simbolos=simbolos_publicos(archivo),
            )
        )

    return plan


# ======================================================================
# Reescritura de imports
# ======================================================================


def construir_mapas(plan: Plan) -> tuple[dict[str, str], dict[str, str]]:
    """Devuelve (modulo_viejo -> modulo_nuevo, simbolo -> modulo_nuevo)."""
    modulos = {m.modulo_viejo: m.modulo_nuevo for m in plan.movimientos}

    simbolos: dict[str, str] = {}
    duplicados: dict[str, list[str]] = defaultdict(list)
    for m in plan.movimientos:
        for s in m.simbolos:
            if s in simbolos and simbolos[s] != m.modulo_nuevo:
                duplicados[s].append(m.modulo_nuevo)
            else:
                simbolos[s] = m.modulo_nuevo

    if duplicados:
        print("\n  Aviso: estos nombres existen en mas de un modulo.")
        print("  Los imports agregados que los usen quedan marcados con TODO:")
        for nombre, modulos_ in sorted(duplicados.items()):
            print(f"    {nombre}: {simbolos[nombre]} / {', '.join(modulos_)}")

    return modulos, simbolos


# Paquetes viejos que se importaban en bloque: `from app.models import X, Y`
PAQUETES_AGREGADOS = ("app.models", "app.schemas", "app.services", "app.routers")


def reescribir_texto(
    texto: str, modulos: dict[str, str], simbolos: dict[str, str]
) -> tuple[str, int]:
    cambios = 0

    # 1. from app.models.cliente import Cliente  ->  ruta nueva
    def sub_from(match: re.Match) -> str:
        nonlocal cambios
        modulo = match.group("mod")
        nuevo = modulos.get(modulo)
        if nuevo is None:
            return match.group(0)
        cambios += 1
        return f"from {nuevo} import"

    texto = re.sub(
        r"from\s+(?P<mod>app\.[A-Za-z0-9_.]+)\s+import", sub_from, texto
    )

    # 2. import app.models.cliente [as x]
    def sub_import(match: re.Match) -> str:
        nonlocal cambios
        modulo = match.group("mod")
        nuevo = modulos.get(modulo)
        if nuevo is None:
            return match.group(0)
        cambios += 1
        alias = match.group("alias") or ""
        return f"import {nuevo}{alias}"

    texto = re.sub(
        r"import\s+(?P<mod>app\.[A-Za-z0-9_.]+)(?P<alias>\s+as\s+\w+)?",
        sub_import,
        texto,
    )

    # 3. from app.models import Cliente, Pedido -> se parte por modulo destino
    def sub_agregado(match: re.Match) -> str:
        nonlocal cambios
        paquete = match.group("paq")
        crudo = match.group("nombres")
        if paquete not in PAQUETES_AGREGADOS:
            return match.group(0)

        nombres = [n.strip() for n in crudo.replace("(", "").replace(")", "").split(",")]
        nombres = [n for n in nombres if n]

        por_modulo: dict[str, list[str]] = defaultdict(list)
        sin_resolver: list[str] = []
        for nombre in nombres:
            base = nombre.split(" as ")[0].strip()
            destino = simbolos.get(base)
            if destino:
                por_modulo[destino].append(nombre)
            else:
                sin_resolver.append(nombre)

        if not por_modulo:
            return match.group(0)

        cambios += 1
        lineas = [
            f"from {mod} import {', '.join(sorted(ns))}"
            for mod, ns in sorted(por_modulo.items())
        ]
        if sin_resolver:
            lineas.append(
                f"# TODO migracion: no se pudo ubicar {', '.join(sin_resolver)} "
                f"(venia de {paquete})"
            )
        return "\n".join(lineas)

    texto = re.sub(
        r"from\s+(?P<paq>app\.\w+)\s+import\s+(?P<nombres>\(?[^\n()]+\)?)",
        sub_agregado,
        texto,
    )

    # 4. Base pasa a vivir en app.db.base
    if "from app.core.database import" in texto:
        texto_nuevo = re.sub(
            r"from app\.core\.database import Base\s*$",
            "from app.db.base import Base",
            texto,
            flags=re.MULTILINE,
        )
        if texto_nuevo != texto:
            cambios += 1
            texto = texto_nuevo

    # 5. require_roles / require_admin se mudaron a permissions
    texto_nuevo = re.sub(
        r"from app\.core\.security import (?P<n>[^\n]*require_[^\n]*)",
        lambda m: _separar_permisos(m.group("n")),
        texto,
    )
    if texto_nuevo != texto:
        cambios += 1
        texto = texto_nuevo

    return texto, cambios


def _separar_permisos(nombres_crudos: str) -> str:
    nombres = [n.strip() for n in nombres_crudos.split(",") if n.strip()]
    permisos = [n for n in nombres if n.startswith("require_")]
    resto = [n for n in nombres if not n.startswith("require_")]
    lineas = []
    if resto:
        lineas.append(f"from app.core.security import {', '.join(resto)}")
    if permisos:
        lineas.append(f"from app.core.permissions import {', '.join(permisos)}")
    return "\n".join(lineas)


# ======================================================================
# Generacion de archivos
# ======================================================================


def generar_inits(raiz: Path, plan: Plan, escribir: bool) -> list[Path]:
    """Crea los __init__.py. Los de models/ re-exportan sus clases."""
    creados: list[Path] = []
    paquetes: set[Path] = set()

    for m in plan.movimientos:
        actual = m.destino.parent
        while actual != Path("app") and actual != Path("."):
            paquetes.add(actual)
            actual = actual.parent
    paquetes.add(Path("app/features"))

    por_paquete_models: dict[Path, list[Movimiento]] = defaultdict(list)
    for m in plan.movimientos:
        if m.tipo == "models":
            por_paquete_models[m.destino.parent].append(m)

    for paquete in sorted(paquetes):
        destino = raiz / paquete / "__init__.py"
        if paquete in por_paquete_models:
            movs = sorted(por_paquete_models[paquete], key=lambda x: x.destino.name)
            lineas = [
                '"""Modelos del feature. Re-exportados para que el resto del',
                'codigo pueda hacer `from ...models import Cliente`."""',
                "",
            ]
            todos: list[str] = []
            for mov in movs:
                modulo = mov.destino.stem
                clases = [s for s in mov.simbolos if s[:1].isupper()]
                if not clases:
                    continue
                lineas.append(f"from .{modulo} import {', '.join(sorted(clases))}")
                todos.extend(clases)
            lineas.append("")
            lineas.append("__all__ = [")
            for nombre in sorted(set(todos)):
                lineas.append(f'    "{nombre}",')
            lineas.append("]")
            contenido = "\n".join(lineas) + "\n"
        else:
            contenido = ""

        if escribir:
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_text(contenido, encoding="utf-8")
        creados.append(paquete / "__init__.py")

    return creados


def generar_registry(raiz: Path, plan: Plan, escribir: bool) -> str:
    por_modulo: dict[str, list[str]] = defaultdict(list)
    for m in plan.movimientos:
        if m.tipo != "models":
            continue
        clases = [s for s in m.simbolos if s[:1].isupper()]
        if clases:
            por_modulo[m.modulo_nuevo].extend(clases)

    lineas = [
        '"""',
        "Registro de modelos. Generado por scripts/migrar_estructura.py.",
        "",
        "Alembic lee Base.metadata en frio. Si un modelo no esta importado",
        "aca, autogenerate no lo ve y genera un drop_table de su tabla.",
        "",
        "Cada modelo nuevo se agrega aca. El test tests/test_models_registry.py",
        "avisa si te olvidas.",
        '"""',
        "",
        "from __future__ import annotations",
        "",
        "# ruff: noqa: F401",
        "# Los imports 'sin usar' son el punto del archivo.",
        "",
        "from app.db.base import Base",
        "",
    ]
    for modulo, clases in sorted(por_modulo.items()):
        lineas.append(f"from {modulo} import {', '.join(sorted(set(clases)))}")

    lineas += [
        "",
        "",
        "def tablas_registradas() -> list[str]:",
        '    """Nombres de las tablas que Alembic va a ver."""',
        "    return sorted(Base.metadata.tables.keys())",
        "",
        "",
        '__all__ = ["Base", "tablas_registradas"]',
        "",
    ]
    contenido = "\n".join(lineas)

    if escribir:
        destino = raiz / "app/db/models_registry.py"
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(contenido, encoding="utf-8")
    return contenido


def _orden_original(raiz: Path) -> list[str]:
    """Lee el orden de include_router del app/api/router.py actual.

    Esto importa mas de lo que parece. FastAPI resuelve por primera
    coincidencia, asi que si `/repartos-dia/bootstrap` esta registrado
    despues de `/repartos-dia/{id_repartodia}`, la ruta literal nunca se
    alcanza: "bootstrap" entra como valor del parametro.

    Tu codigo actual funciona con el orden que tiene. Reordenar alfabetica-
    mente puede romper rutas sin que el contrato lo note, porque las dos
    siguen existiendo en el OpenAPI. Por eso se respeta el orden de siempre
    y los routers nuevos van al final.
    """
    archivo = raiz / "app/api/router.py"
    if not archivo.is_file():
        return []
    try:
        texto = archivo.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return []
    return re.findall(r"api_router\.include_router\(\s*(\w+)\.router\s*\)", texto)


def generar_api_router(raiz: Path, plan: Plan, escribir: bool) -> str:
    routers = [m for m in plan.movimientos if m.tipo == "router"]

    # Ordenar como estaban antes; lo que no aparecia, al final.
    orden = _orden_original(raiz)
    posicion = {nombre: i for i, nombre in enumerate(orden)}

    def clave_orden(m: Movimiento) -> tuple[int, str, str]:
        original = m.origen.stem
        return (posicion.get(original, len(orden)), m.feature, m.destino.name)

    routers.sort(key=clave_orden)
    nuevos = [m for m in routers if m.origen.stem not in posicion]

    lineas = [
        '"""',
        "Router raiz. Generado por scripts/migrar_estructura.py.",
        "",
        "El orden de los include_router es el mismo que tenia el archivo",
        "original. NO lo reordenes alfabeticamente: FastAPI resuelve por",
        "primera coincidencia, y una ruta literal registrada despues de una",
        "con parametro queda inalcanzable.",
        '"""',
        "",
        "from fastapi import APIRouter",
        "",
    ]

    alias: dict[str, str] = {}
    usados: set[str] = set()
    for m in routers:
        base = f"{m.feature.replace('/', '_')}_{m.destino.stem}"
        base = re.sub(r"_router$", "", base)
        nombre = f"{base}_router"
        n = 2
        while nombre in usados:
            nombre = f"{base}_{n}_router"
            n += 1
        usados.add(nombre)
        alias[m.modulo_nuevo] = nombre
        lineas.append(f"from {m.modulo_nuevo} import router as {nombre}")

    lineas += ["", "api_router = APIRouter()", ""]

    for m in routers:
        if m in nuevos and nuevos and m is nuevos[0]:
            lineas.append("")
            lineas.append("# --- no estaban en el router original ---")
        lineas.append(
            f"api_router.include_router({alias[m.modulo_nuevo]})"
            f"  # {m.feature}"
        )
    lineas.append("")

    contenido = "\n".join(lineas)
    if escribir:
        destino = raiz / "app/api/router.py"
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(contenido, encoding="utf-8")
    return contenido


# ======================================================================
# Ejecucion
# ======================================================================


def repo_limpio(raiz: Path) -> bool:
    codigo, salida = correr(["git", "status", "--porcelain"], raiz)
    if codigo != 0:
        print("  (no es un repo git: se mueve con shutil y sin historial)")
        return True
    return not salida.strip()


def mover(raiz: Path, mov: Movimiento, usar_git: bool) -> None:
    destino_abs = raiz / mov.destino
    destino_abs.parent.mkdir(parents=True, exist_ok=True)
    if usar_git:
        codigo, salida = correr(
            ["git", "mv", str(mov.origen), str(mov.destino)], raiz
        )
        if codigo != 0:
            raise RuntimeError(f"git mv fallo: {salida}")
    else:
        import shutil

        shutil.move(str(raiz / mov.origen), str(destino_abs))


def reescribir_repo(
    raiz: Path, modulos: dict[str, str], simbolos: dict[str, str], escribir: bool
) -> dict[str, int]:
    tocados: dict[str, int] = {}
    for carpeta in RAICES_CODIGO:
        base = raiz / carpeta
        if not base.is_dir():
            continue
        for archivo in sorted(base.rglob("*.py")):
            if "__pycache__" in archivo.parts:
                continue
            try:
                original = archivo.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            nuevo, cambios = reescribir_texto(original, modulos, simbolos)
            if cambios and nuevo != original:
                tocados[str(archivo.relative_to(raiz))] = cambios
                if escribir:
                    archivo.write_text(nuevo, encoding="utf-8")
    return tocados


def imprimir_plan(plan: Plan) -> None:
    print(f"\n{'=' * 72}")
    print("PLAN DE MIGRACION")
    print("=" * 72)

    for feature, movs in plan.features.items():
        print(f"\n  app/features/{feature}/")
        for m in sorted(movs, key=lambda x: str(x.destino)):
            relativo = str(m.destino).replace(f"app/features/{feature}/", "")
            print(f"      {str(m.origen):<45} -> {relativo}")

    print(f"\n{'-' * 72}")
    print(f"  {len(plan.movimientos)} archivos a mover")
    print(f"  {len(plan.features)} features")

    if plan.desconocidos:
        print(f"\n  {len(plan.desconocidos)} ARCHIVOS SIN ASIGNAR:")
        for ruta in plan.desconocidos:
            clave = clave_de(ruta.name, ruta.parent.name)
            print(f"      {ruta}   (clave: '{clave}')")
        print(
            "\n  Agregalos a la tabla ASIGNACION arriba en este script.\n"
            "  El script no adivina: si moviera un archivo al feature\n"
            "  equivocado, lo ibas a descubrir semanas despues."
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Reorganiza el backend en estructura por features."
    )
    parser.add_argument("--raiz", default=".", help="Raiz del repo.")
    parser.add_argument("--dry-run", action="store_true", help="Solo mostrar el plan.")
    parser.add_argument("--solo-plan", metavar="ARCHIVO", help="Exportar el plan a JSON.")
    parser.add_argument(
        "--permitir-desconocidos",
        action="store_true",
        help="Seguir aunque haya archivos sin asignar (los deja donde estan).",
    )
    parser.add_argument(
        "--sin-git", action="store_true", help="Mover con shutil en vez de git mv."
    )
    args = parser.parse_args()

    raiz = Path(args.raiz).resolve()
    if not (raiz / "app").is_dir():
        print(f"No encuentro app/ en {raiz}", file=sys.stderr)
        return 1

    print(f"Repo: {raiz}")
    plan = armar_plan(raiz)
    imprimir_plan(plan)

    if args.solo_plan:
        Path(args.solo_plan).write_text(
            json.dumps(
                {
                    "movimientos": [
                        {
                            "origen": str(m.origen),
                            "destino": str(m.destino),
                            "feature": m.feature,
                            "tipo": m.tipo,
                            "simbolos": m.simbolos,
                        }
                        for m in plan.movimientos
                    ],
                    "desconocidos": [str(d) for d in plan.desconocidos],
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        print(f"\nPlan exportado a {args.solo_plan}")

    if plan.desconocidos and not args.permitir_desconocidos and not args.dry_run:
        print("\nFrenado: hay archivos sin asignar. Usa --permitir-desconocidos "
              "si querés dejarlos donde estan.", file=sys.stderr)
        return 1

    modulos, simbolos = construir_mapas(plan)
    escribir = not args.dry_run

    if escribir:
        if not repo_limpio(raiz):
            print(
                "\nEl repo tiene cambios sin commitear. Commiteá primero: si "
                "esto sale mal, querés poder hacer `git reset --hard`.",
                file=sys.stderr,
            )
            return 1

        usar_git = not args.sin_git and (raiz / ".git").exists()
        print(f"\nMoviendo {len(plan.movimientos)} archivos"
              f"{' con git mv' if usar_git else ''}...")
        for m in plan.movimientos:
            mover(raiz, m, usar_git)
        print("  hecho")

    print("\nReescribiendo imports...")
    tocados = reescribir_repo(raiz, modulos, simbolos, escribir)
    print(f"  {len(tocados)} archivos con imports actualizados")
    for archivo, n in sorted(tocados.items())[:15]:
        print(f"      {archivo} ({n})")
    if len(tocados) > 15:
        print(f"      ... y {len(tocados) - 15} mas")

    print("\nGenerando archivos de soporte...")
    inits = generar_inits(raiz, plan, escribir)
    print(f"  {len(inits)} __init__.py")
    generar_registry(raiz, plan, escribir)
    print("  app/db/models_registry.py")
    generar_api_router(raiz, plan, escribir)
    print("  app/api/router.py")

    if args.dry_run:
        print("\n--dry-run: no se toco nada. Sacá el flag para ejecutar.")
        return 0

    print(
        "\n"
        + "=" * 72
        + "\nListo. Ahora, en este orden:\n\n"
        "  1. rm app/models/__init__.py   (lo reemplaza app/db/models_registry.py)\n"
        "  2. app/api/deps.py: mové cada dependency al feature que le toca.\n"
        "     get_cliente_or_404_dep va a features/clientes/dependencies.py\n"
        "  3. Buscá 'TODO migracion' en el repo y resolvé lo que quedo marcado\n"
        "  4. python -c 'import app.main'      <- que importe sin errores\n"
        "  5. pytest tests/test_api_contract.py\n"
        "  6. pytest tests/test_models_registry.py\n"
        "  7. uvicorn app.main:app --reload    <- probá el login a mano\n"
        "  8. Cuando todo pase: borrá las carpetas app/models, app/routers,\n"
        "     app/services y app/schemas si quedaron vacias\n\n"
        "Si el contrato falla, mira primero app/api/router.py: el orden de\n"
        "los include_router es la causa mas probable.\n\n"
        "Commiteá esto SOLO cuando el contrato este en verde, y hacelo en un\n"
        "commit aparte, sin mezclar con cambios de logica. Asi, si algo se\n"
        "rompe en dos semanas, sabes que este commit no toco comportamiento.\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
