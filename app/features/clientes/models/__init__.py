"""Modelos del feature. Re-exportados para que el resto del
codigo pueda hacer `from ...models import Cliente`."""

from .cliente import Cliente
from .cliente_cuenta import ClienteCuenta
from .direccion_cliente import DireccionCliente
from .email_cliente import MailCliente
from .producto_cliente import ProductoCliente
from .telefono_cliente import TelefonoCliente

__all__ = [
    "Cliente",
    "ClienteCuenta",
    "DireccionCliente",
    "MailCliente",
    "ProductoCliente",
    "TelefonoCliente",
]
