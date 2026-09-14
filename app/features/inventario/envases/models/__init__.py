"""Modelos del feature. Re-exportados para que el resto del
codigo pueda hacer `from ...models import Cliente`."""

from .movimiento_envase_cliente import MovimientoEnvaseCliente

__all__ = [
    "MovimientoEnvaseCliente",
]
