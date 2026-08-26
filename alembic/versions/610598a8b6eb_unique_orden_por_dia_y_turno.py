"""unique orden por dia y turno

Revision ID: 610598a8b6eb
Revises: c6451763b6a5
Create Date: 2025-12-22 20:36:53.287734

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '610598a8b6eb'
down_revision: Union[str, Sequence[str], None] = 'c6451763b6a5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_index(
        "ux_cliente_dia_turno_orden",
        "cliente_dia_semana",
        ["id_dia", "turno_visita", "orden"],
        unique=True,
    )


def downgrade():
    op.drop_index(
        "ux_cliente_dia_turno_orden",
        table_name="cliente_dia_semana",
    )
