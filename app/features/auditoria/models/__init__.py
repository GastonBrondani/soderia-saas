"""Modelos del feature. Re-exportados para que el resto del
codigo pueda hacer `from ...models import Cliente`."""

from .historico import Historico

__all__ = [
    "Historico",
]
