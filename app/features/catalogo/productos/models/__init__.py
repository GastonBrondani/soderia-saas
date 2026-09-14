"""Modelos del feature. Re-exportados para que el resto del
codigo pueda hacer `from ...models import Cliente`."""

from .producto import Producto

__all__ = [
    "Producto",
]
