"""
Registro de modelos. Generado por scripts/migrar_estructura.py.

Alembic lee Base.metadata en frio. Si un modelo no esta importado
aca, autogenerate no lo ve y genera un drop_table de su tabla.

Cada modelo nuevo se agrega aca. El test tests/test_models_registry.py
avisa si te olvidas.
"""

from __future__ import annotations

# ruff: noqa: F401
# Los imports 'sin usar' son el punto del archivo.

from app.db.base import Base

from app.features.auditoria.models.historico import Historico
from app.features.caja.models.caja_empresa import CajaEmpresa
from app.features.catalogo.combos.models.combo import Combo
from app.features.catalogo.combos.models.combo_producto import ComboProducto
from app.features.catalogo.listas_precios.models.lista_de_precios import ListaDePrecios
from app.features.catalogo.listas_precios.models.lista_precio_combo import ListaPrecioCombo
from app.features.catalogo.listas_precios.models.lista_precio_producto import ListaPrecioProducto
from app.features.catalogo.listas_precios.models.lista_precio_servicio import ListaPrecioServicio
from app.features.catalogo.productos.models.producto import Producto
from app.features.catalogo.servicios.models.cliente_servicio import ClienteServicio
from app.features.catalogo.servicios.models.cliente_servicio_periodo import ClienteServicioPeriodo
from app.features.clientes.models.cliente import Cliente
from app.features.clientes.models.cliente_cuenta import ClienteCuenta
from app.features.clientes.models.direccion_cliente import DireccionCliente
from app.features.clientes.models.email_cliente import MailCliente
from app.features.clientes.models.producto_cliente import ProductoCliente
from app.features.clientes.models.telefono_cliente import TelefonoCliente
from app.features.documentos.models.documentos import Documentos
from app.features.empleados.models.empleado import Empleado
from app.features.empresas.models.cuenta_bancaria_empresa import CuentaBancariaEmpresa
from app.features.empresas.models.empresa import Empresa
from app.features.inventario.envases.models.movimiento_envase_cliente import MovimientoEnvaseCliente
from app.features.inventario.movimientos.models.movimiento_stock import MovimientoStock
from app.features.inventario.stock.models.stock import Stock
from app.features.maestros.models.dia_semana import DiaSemana
from app.features.maestros.models.medio_pago import MedioPago
from app.features.maestros.models.tipo_evento import TipoEvento
from app.features.maestros.models.tipo_movimiento_caja import TipoMovimientoCaja
from app.features.pagos.models.pago import Pago
from app.features.pedidos.models.pedido import IDEMPOTENCY_KEY_LEN, Pedido
from app.features.pedidos.models.pedido_producto import PedidoProducto
from app.features.personas.models.persona import Persona
from app.features.repartos.agenda.models.cliente_dia_semana import ClienteDiaSemana
from app.features.repartos.camiones.models.camion_reparto import CamionReparto
from app.features.repartos.recorridos.models.recorrido import Recorrido
from app.features.repartos.repartos_dia.models.cliente_reparto_dia import ClienteRepartoDia
from app.features.repartos.repartos_dia.models.reparto_dia import RepartoDia
from app.features.repartos.visitas.models.visita import Visita
from app.features.usuarios.models.rol import Rol
from app.features.usuarios.models.usuario import Usuario
from app.features.usuarios.models.usuario_rol import UsuarioRol


def tablas_registradas() -> list[str]:
    """Nombres de las tablas que Alembic va a ver."""
    return sorted(Base.metadata.tables.keys())


__all__ = ["Base", "tablas_registradas"]
