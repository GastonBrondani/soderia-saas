"""columnas de fecha/hora pasan a timestamptz (con timezone)

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-09-16

Convencion nueva (documentada en CONTEXTO_MIGRACION.md): toda columna que
representa "cuando paso esto" se guarda en UTC, con timezone. Antes convivian
datetime.now() (hora local del proceso) y datetime.utcnow() (UTC) escribiendo
a columnas naive (timestamp sin timezone) -- un pago hecho a las 22:00 en
Cordoba quedaba guardado como las 01:00 del dia siguiente, y un pedido creado
en el mismo minuto por otro camino quedaba en 22:00. El cierre de caja y los
reportes diarios contaban esos dos eventos en dias distintos.

Se hace ahora (2026-09-16) porque la base de cada sodería todavia esta vacia
de datos reales: no hay filas historicas ambiguas que interpretar. El dia que
se importen los datos del cliente actual, esa importacion tiene que escribir
directamente en el formato nuevo (timestamptz, UTC) -- no hay una conversion
automatica correcta posible para datos donde no se sabe con certeza, fila por
fila, si quedaron guardados en hora local o en UTC.

USING <col> AT TIME ZONE 'UTC' interpreta cualquier valor naive existente
como si ya fuera UTC. Para los datos de prueba de este entorno eso alcanza;
no se garantiza que sea correcto para datos reales (ver parrafo anterior).
"""
from typing import Sequence, Union

from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLA_COLUMNA = [
    ("historico", "fecha"),
    ("caja_empresa", "fecha"),
    ("lista_de_precios", "fecha_creacion"),
    ("documentos", "fecha_carga"),
    ("movimiento_stock", "fecha"),
    ("pago", "fecha"),
    ("pedido", "fecha"),
    ("visita", "fecha"),
    ("movimiento_envase_cliente", "fecha"),
]


def upgrade() -> None:
    for tabla, columna in TABLA_COLUMNA:
        op.execute(
            f'ALTER TABLE "{tabla}" ALTER COLUMN "{columna}" '
            f"TYPE timestamptz USING \"{columna}\" AT TIME ZONE 'UTC'"
        )


def downgrade() -> None:
    for tabla, columna in TABLA_COLUMNA:
        op.execute(
            f'ALTER TABLE "{tabla}" ALTER COLUMN "{columna}" '
            f"TYPE timestamp USING \"{columna}\" AT TIME ZONE 'UTC'"
        )
