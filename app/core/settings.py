# app/core/settings.py (o similar)
import os


COMPROBANTES_BASE_PATH = "/data/comprobantes/pagos"
COMPROBANTES_BASE_URL = "/docs/comprobantes/pagos"
COMPROBANTES_PEDIDOS_BASE_PATH = os.getenv("COMPROBANTES_PEDIDOS_BASE_PATH")
COMPROBANTES_PEDIDOS_BASE_URL = os.getenv("COMPROBANTES_PEDIDOS_BASE_URL")

