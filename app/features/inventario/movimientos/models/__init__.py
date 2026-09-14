"""Modelos del feature. Re-exportados para que el resto del
codigo pueda hacer `from ...models import Cliente`."""

from .movimiento_stock import MovimientoStock

__all__ = [
    "MovimientoStock",
]
