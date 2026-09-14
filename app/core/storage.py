"""
Almacenamiento de archivos (comprobantes de pago, de pedido, documentos).

Hoy las rutas estan hardcodeadas en tres lugares distintos:
  - main.py:      "/data/comprobantes/pagos", "/data/comprobantes/pedidos"
  - settings.py:  COMPROBANTES_BASE_PATH, COMPROBANTES_PEDIDOS_BASE_PATH
  - Dockerfile:   RUN mkdir -p /data/comprobantes/pagos

Ademas, con varias soderias los archivos se mezclarian en el mismo directorio.
Aca cada tenant tiene su carpeta:

    /data/solmar/comprobantes/pagos/2026/08/pago-1234.pdf
    /data/lacascada/comprobantes/pagos/2026/08/pago-1234.pdf

La interfaz es abstracta para que mañana puedas mover todo a S3 sin tocar
los servicios que generan PDFs.
"""

from __future__ import annotations

import re
import shutil
import unicodedata
from abc import ABC, abstractmethod
from datetime import date
from pathlib import Path
from typing import BinaryIO

from app.core.config import settings
from app.core.tenancy import tenant_actual

# Categorias validas. Evita que un bug escriba en cualquier lado.
CATEGORIA_COMPROBANTES_PAGOS = "comprobantes/pagos"
CATEGORIA_COMPROBANTES_PEDIDOS = "comprobantes/pedidos"
CATEGORIA_DOCUMENTOS = "documentos"

CATEGORIAS = {
    CATEGORIA_COMPROBANTES_PAGOS,
    CATEGORIA_COMPROBANTES_PEDIDOS,
    CATEGORIA_DOCUMENTOS,
}

_SEGURO = re.compile(r"[^A-Za-z0-9._-]+")


def nombre_seguro(nombre: str) -> str:
    """Normaliza un nombre de archivo. Corta path traversal."""
    nombre = unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode()
    nombre = _SEGURO.sub("-", nombre).strip("-._")
    return nombre[:180] or "archivo"


class Storage(ABC):
    @abstractmethod
    def guardar(self, categoria: str, nombre: str, contenido: bytes) -> str:
        """Guarda y devuelve la clave relativa del archivo."""

    @abstractmethod
    def guardar_stream(self, categoria: str, nombre: str, stream: BinaryIO) -> str: ...

    @abstractmethod
    def leer(self, clave: str) -> bytes: ...

    @abstractmethod
    def borrar(self, clave: str) -> None: ...

    @abstractmethod
    def existe(self, clave: str) -> bool: ...

    @abstractmethod
    def url_publica(self, clave: str) -> str: ...

    @abstractmethod
    def ruta_absoluta(self, clave: str) -> Path | None:
        """Ruta en disco, o None si el backend no es local."""


class LocalStorage(Storage):
    def __init__(self, base: str | Path, url_base: str) -> None:
        self._base = Path(base).resolve()
        self._url_base = url_base.rstrip("/")

    # -- helpers internos ------------------------------------------------

    def _dir_tenant(self) -> Path:
        return self._base / tenant_actual().codigo

    def _clave(self, categoria: str, nombre: str, cuando: date | None = None) -> str:
        if categoria not in CATEGORIAS:
            raise ValueError(f"Categoria desconocida: {categoria}")
        cuando = cuando or date.today()
        # Particionar por año/mes: un directorio con 200.000 PDFs es lento
        # de listar y molesto de respaldar.
        return (
            f"{tenant_actual().codigo}/{categoria}/"
            f"{cuando:%Y/%m}/{nombre_seguro(nombre)}"
        )

    def _resolver(self, clave: str) -> Path:
        destino = (self._base / clave).resolve()
        # Defensa contra "../../etc/passwd"
        if not destino.is_relative_to(self._base):
            raise ValueError("Ruta fuera del directorio de storage.")
        return destino

    # -- interfaz --------------------------------------------------------

    def guardar(self, categoria: str, nombre: str, contenido: bytes) -> str:
        clave = self._clave(categoria, nombre)
        destino = self._resolver(clave)
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(contenido)
        return clave

    def guardar_stream(self, categoria: str, nombre: str, stream: BinaryIO) -> str:
        clave = self._clave(categoria, nombre)
        destino = self._resolver(clave)
        destino.parent.mkdir(parents=True, exist_ok=True)
        with destino.open("wb") as f:
            shutil.copyfileobj(stream, f)
        return clave

    def leer(self, clave: str) -> bytes:
        return self._resolver(clave).read_bytes()

    def borrar(self, clave: str) -> None:
        self._resolver(clave).unlink(missing_ok=True)

    def existe(self, clave: str) -> bool:
        return self._resolver(clave).is_file()

    def url_publica(self, clave: str) -> str:
        return f"{self._url_base}/{clave}"

    def ruta_absoluta(self, clave: str) -> Path:
        return self._resolver(clave)

    def preparar_tenant(self, codigo: str) -> None:
        """Crea el arbol de carpetas de una sodería nueva."""
        for categoria in CATEGORIAS:
            (self._base / codigo / categoria).mkdir(parents=True, exist_ok=True)


_storage: Storage | None = None


def get_storage() -> Storage:
    global _storage
    if _storage is None:
        if settings.STORAGE_BACKEND == "local":
            _storage = LocalStorage(
                settings.STORAGE_LOCAL_PATH, settings.STORAGE_PUBLIC_URL_BASE
            )
        else:
            raise RuntimeError(
                f"Backend de storage no soportado: {settings.STORAGE_BACKEND}"
            )
    return _storage


# ----------------------------------------------------------------------
# Nota sobre servir archivos
# ----------------------------------------------------------------------
# main.py hoy monta StaticFiles sobre /data. Eso deja los comprobantes
# accesibles a cualquiera que adivine la URL, y con varias soderias implica
# que un cliente puede leer los PDFs de otro.
#
# El main.py nuevo lo reemplaza por un endpoint que verifica autenticacion
# y que el archivo pertenezca al tenant del request antes de devolverlo.
