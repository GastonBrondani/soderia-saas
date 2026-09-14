"""Modelos del feature. Re-exportados para que el resto del
codigo pueda hacer `from ...models import Cliente`."""

from .caja_empresa import CajaEmpresa

__all__ = [
    "CajaEmpresa",
]
