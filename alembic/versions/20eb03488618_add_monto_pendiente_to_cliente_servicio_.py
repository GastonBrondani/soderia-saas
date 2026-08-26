"""add monto_pendiente to cliente_servicio_periodo

Revision ID: 20eb03488618
Revises: e2697aaa7b06
Create Date: 2026-03-09 20:28:47.084888

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20eb03488618'
down_revision: Union[str, Sequence[str], None] = 'e2697aaa7b06'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column(
        "cliente_servicio_periodo",
        sa.Column("monto_pendiente", sa.Numeric(10, 2), nullable=True),
    )

    op.execute("""
        UPDATE cliente_servicio_periodo
        SET monto_pendiente = CASE
            WHEN estado = 'PAGADO' THEN 0
            ELSE monto
        END
    """)

    op.alter_column(
        "cliente_servicio_periodo",
        "monto_pendiente",
        existing_type=sa.Numeric(10, 2),
        nullable=False,
    )


def downgrade():
    op.drop_column("cliente_servicio_periodo", "monto_pendiente")
