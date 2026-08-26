"""seed datos base

Revision ID: 409913c99187
Revises: 20eb03488618
Create Date: 2026-03-18 20:58:33.854449

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '409913c99187'
down_revision: Union[str, Sequence[str], None] = '20eb03488618'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.execute("""
        INSERT INTO dia_semana (id_dia, nombre_dia) VALUES
            (1, 'Lunes'),
            (2, 'Martes'),
            (3, 'Miercoles'),
            (4, 'Jueves'),
            (5, 'Viernes'),
            (6, 'Sabado'),
            (7, 'Domingo')
        ON CONFLICT DO NOTHING;
    """)

    op.execute("""
        INSERT INTO medio_pago (id_medio_pago, nombre) VALUES
            (1, 'Efectivo'),
            (2, 'Virtual')
        ON CONFLICT DO NOTHING;
    """)

    op.execute("""
        INSERT INTO rol (id_rol, nombre, descripcion) VALUES
            (1, 'ADMIN', 'Administrador del sistema')
        ON CONFLICT DO NOTHING;
    """)

    op.execute("""
        INSERT INTO tipo_movimiento_caja (id_tipo_movimiento, descripcion) VALUES
            (1, 'INGRESO_REPARTO'),
            (2, 'EGRESO_EMPRESA')
        ON CONFLICT DO NOTHING;
    """)

    op.execute("""
        INSERT INTO tipo_evento (id_evento, nombre) VALUES
            (1, 'CLIENTE_ACTUALIZADO'),
            (2, 'VISITA_REGISTRADA')
        ON CONFLICT DO NOTHING;
    """)

    # Ajustar secuencias/seriales para que no fallen futuros inserts
    op.execute("""
    SELECT setval(
        pg_get_serial_sequence('dia_semana', 'id_dia'),
        COALESCE((SELECT MAX(id_dia) FROM dia_semana), 1),
        true
    );
    """)

    op.execute("""
        SELECT setval(
            pg_get_serial_sequence('medio_pago', 'id_medio_pago'),
            COALESCE((SELECT MAX(id_medio_pago) FROM medio_pago), 1),
            true
        );
    """)

    op.execute("""
        SELECT setval(
            pg_get_serial_sequence('rol', 'id_rol'),
            COALESCE((SELECT MAX(id_rol) FROM rol), 1),
            true
        );
    """)

    op.execute("""
        SELECT setval(
            pg_get_serial_sequence('tipo_movimiento_caja', 'id_tipo_movimiento'),
            COALESCE((SELECT MAX(id_tipo_movimiento) FROM tipo_movimiento_caja), 1),
            true
        );
    """)

    op.execute("""
    SELECT setval(
        pg_get_serial_sequence('tipo_evento', 'id_evento'),
        COALESCE((SELECT MAX(id_evento) FROM tipo_evento), 1),
        true
    );
    """)


def downgrade() -> None:
    """Downgrade schema."""
    pass
