# app/core/settings.py (o similar)
#
# TODO migracion paso 3: comprobantePedidoService.py y comprobantePagoService.py
# son los unicos que quedan usando esto. Migrarlos a core/storage.py
# (get_storage()) y borrar este archivo.
import os

from dotenv import load_dotenv

# database.py ya no llama load_dotenv() (pydantic-settings lee .env solo),
# asi que este modulo necesita el suyo propio para los os.getenv de abajo.
load_dotenv()

COMPROBANTES_BASE_PATH = "/data/comprobantes/pagos"
COMPROBANTES_BASE_URL = "/docs/comprobantes/pagos"
COMPROBANTES_PEDIDOS_BASE_PATH = os.getenv("COMPROBANTES_PEDIDOS_BASE_PATH")
COMPROBANTES_PEDIDOS_BASE_URL = os.getenv("COMPROBANTES_PEDIDOS_BASE_URL")

