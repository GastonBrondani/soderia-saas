"""Modelos del feature. Re-exportados para que el resto del
codigo pueda hacer `from ...models import Cliente`."""

from .stock import Stock

__all__ = [
    "Stock",
]
