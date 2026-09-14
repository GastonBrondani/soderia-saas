"""
Registro de modelos.

Este archivo existe por una sola razon: cuando los modelos se reparten en
app/features/*/models.py, nada los importa hasta que alguien usa el feature.
Alembic autogenerate lee Base.metadata en frio, ve pocas tablas o ninguna, y
genera una migracion que DROPEA todo lo que no encontro.

Importar todo aca, y hacer que alembic/env.py importe este modulo, resuelve
el problema. Es el equivalente al app/models/__init__.py que tenes hoy.

Regla: cada vez que agregues un modelo, agregalo aca. Si te olvidas, el test
tests/test_models_registry.py te avisa.
"""

from __future__ import annotations

# ruff: noqa: F401
# Los imports "sin usar" son el punto del archivo.

from app.db.base import Base

# ----------------------------------------------------------------------
# Este bloque se completa en el paso 2, cuando el script mueva los modelos.
# Mientras tanto sigue valiendo el __init__.py de app/models.
#
# Asi va a quedar:
#
# from app.features.usuarios.models import Rol, Usuario, UsuarioRol
# from app.features.personas.models import Persona
# from app.features.empresas.models import CuentaBancariaEmpresa, Empresa
# from app.features.maestros.models import (
#     DiaSemana, MedioPago, TipoEvento, TipoMovimientoCaja,
# )
# from app.features.clientes.models import (
#     Cliente, ClienteCuenta, ClienteDiaSemana, DireccionCliente,
#     MailCliente, ProductoCliente, TelefonoCliente,
# )
# from app.features.catalogo.productos.models import Producto
# from app.features.catalogo.combos.models import Combo, ComboProducto
# from app.features.catalogo.servicios.models import (
#     ClienteServicio, ClienteServicioPeriodo,
# )
# from app.features.catalogo.listas_precios.models import (
#     ListaDePrecios, ListaPrecioCombo, ListaPrecioProducto, ListaPrecioServicio,
# )
# from app.features.inventario.stock.models import Stock
# from app.features.inventario.movimientos.models import MovimientoStock
# from app.features.inventario.envases.models import MovimientoEnvaseCliente
# from app.features.pedidos.models import Pedido, PedidoProducto
# from app.features.pagos.models import Pago
# from app.features.caja.models import CajaEmpresa
# from app.features.repartos.camiones.models import CamionReparto
# from app.features.repartos.recorridos.models import Recorrido
# from app.features.repartos.repartos_dia.models import (
#     ClienteRepartoDia, RepartoDia,
# )
# from app.features.repartos.visitas.models import Visita
# from app.features.documentos.models import Documentos
# from app.features.auditoria.models import Historico
# ----------------------------------------------------------------------


def tablas_registradas() -> list[str]:
    """Nombres de las tablas que Alembic va a ver. Util para depurar."""
    return sorted(Base.metadata.tables.keys())


__all__ = ["Base", "tablas_registradas"]
