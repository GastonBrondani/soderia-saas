"""Modelos del feature. Re-exportados para que el resto del
codigo pueda hacer `from ...models import Cliente`."""

from .camion_reparto import CamionReparto

__all__ = [
    "CamionReparto",
]
