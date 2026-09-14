"""Modelos del feature. Re-exportados para que el resto del
codigo pueda hacer `from ...models import Cliente`."""

from .empleado import Empleado

__all__ = [
    "Empleado",
]
