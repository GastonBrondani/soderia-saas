"""Modelos del feature. Re-exportados para que el resto del
codigo pueda hacer `from ...models import Cliente`."""

from .cliente_dia_semana import ClienteDiaSemana

__all__ = [
    "ClienteDiaSemana",
]
