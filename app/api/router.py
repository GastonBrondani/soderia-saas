"""
Router raiz. Generado por scripts/migrar_estructura.py.

El orden de los include_router es el mismo que tenia el archivo
original. NO lo reordenes alfabeticamente: FastAPI resuelve por
primera coincidencia, y una ruta literal registrada despues de una
con parametro queda inalcanzable.
"""

from fastapi import APIRouter

from app.features.empresas.router import router as empresas_router
from app.features.personas.router import router as personas_router
from app.features.clientes.routers.cliente import router as clientes_cliente_router
from app.features.clientes.routers.direccion_cliente import router as clientes_direccion_cliente_router
from app.features.clientes.routers.email_cliente import router as clientes_email_cliente_router
from app.features.clientes.routers.telefono_cliente import router as clientes_telefono_cliente_router
from app.features.empleados.router import router as empleados_router
from app.features.clientes.routers.cliente_cuenta import router as clientes_cliente_cuenta_router
from app.features.catalogo.productos.router import router as catalogo_productos_router
from app.features.catalogo.listas_precios.router import router as catalogo_listas_precios_router
from app.features.inventario.stock.router import router as inventario_stock_router
from app.features.inventario.movimientos.router import router as inventario_movimientos_router
from app.features.repartos.recorridos.router import router as repartos_recorridos_router
from app.features.repartos.camiones.router import router as repartos_camiones_router
from app.features.repartos.repartos_dia.routers.reparto_dia import router as repartos_repartos_dia_reparto_dia_router
from app.features.usuarios.router import router as usuarios_router
from app.features.repartos.agenda.routers.cliente_dia_semana import router as repartos_agenda_cliente_dia_semana_router
from app.features.maestros.routers.dia_semana import router as maestros_dia_semana_router
from app.features.repartos.repartos_dia.routers.cliente_reparto_dia import router as repartos_repartos_dia_cliente_reparto_dia_router
from app.features.pedidos.router import router as pedidos_router
from app.features.maestros.routers.medio_pago import router as maestros_medio_pago_router
from app.features.auth.router import router as auth_router
from app.features.repartos.visitas.router import router as repartos_visitas_router
from app.features.auditoria.router import router as auditoria_router
from app.features.caja.router import router as caja_router
from app.features.catalogo.combos.router import router as catalogo_combos_router
from app.features.pagos.router import router as pagos_router
from app.features.repartos.agenda.routers.agenda import router as repartos_agenda_agenda_router
from app.features.documentos.router import router as documentos_router
from app.features.catalogo.servicios.router import router as catalogo_servicios_router
from app.features.reportes.router import router as reportes_router
from app.features.catalogo.router import router as catalogo_router

api_router = APIRouter()

api_router.include_router(empresas_router)  # empresas
api_router.include_router(personas_router)  # personas
api_router.include_router(clientes_cliente_router)  # clientes
api_router.include_router(clientes_direccion_cliente_router)  # clientes
api_router.include_router(clientes_email_cliente_router)  # clientes
api_router.include_router(clientes_telefono_cliente_router)  # clientes
api_router.include_router(empleados_router)  # empleados
api_router.include_router(clientes_cliente_cuenta_router)  # clientes
api_router.include_router(catalogo_productos_router)  # catalogo/productos
api_router.include_router(catalogo_listas_precios_router)  # catalogo/listas_precios
api_router.include_router(inventario_stock_router)  # inventario/stock
api_router.include_router(inventario_movimientos_router)  # inventario/movimientos
api_router.include_router(repartos_recorridos_router)  # repartos/recorridos
api_router.include_router(repartos_camiones_router)  # repartos/camiones
api_router.include_router(repartos_repartos_dia_reparto_dia_router)  # repartos/repartos_dia
api_router.include_router(usuarios_router)  # usuarios
api_router.include_router(repartos_agenda_cliente_dia_semana_router)  # repartos/agenda
api_router.include_router(maestros_dia_semana_router)  # maestros
api_router.include_router(repartos_repartos_dia_cliente_reparto_dia_router)  # repartos/repartos_dia
api_router.include_router(pedidos_router)  # pedidos
api_router.include_router(maestros_medio_pago_router)  # maestros
api_router.include_router(auth_router)  # auth
api_router.include_router(repartos_visitas_router)  # repartos/visitas
api_router.include_router(auditoria_router)  # auditoria
api_router.include_router(caja_router)  # caja
api_router.include_router(catalogo_combos_router)  # catalogo/combos
api_router.include_router(pagos_router)  # pagos
api_router.include_router(repartos_agenda_agenda_router)  # repartos/agenda
api_router.include_router(documentos_router)  # documentos
api_router.include_router(catalogo_servicios_router)  # catalogo/servicios
api_router.include_router(reportes_router)  # reportes
api_router.include_router(catalogo_router)  # catalogo
