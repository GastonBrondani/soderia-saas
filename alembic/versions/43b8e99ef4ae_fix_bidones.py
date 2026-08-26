"""fix_bidones

Revision ID: 43b8e99ef4ae
Revises: 46624bf94f27
Create Date: 2026-04-29 17:04:59.300090

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '43b8e99ef4ae'
down_revision: Union[str, Sequence[str], None] = '46624bf94f27'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column("producto",
        sa.Column("es_envase", sa.Boolean(), nullable=False, server_default="false")
    )
    op.create_table(
        "movimiento_envase_cliente",
        sa.Column("id_movimiento", sa.Integer(), primary_key=True),
        sa.Column("legajo", sa.Integer(), sa.ForeignKey("cliente.legajo", ondelete="CASCADE"), nullable=False),
        sa.Column("id_producto", sa.Integer(), sa.ForeignKey("producto.id_producto"), nullable=False),
        sa.Column("id_repartodia", sa.Integer(), sa.ForeignKey("reparto_dia.id_repartodia"), nullable=True),
        sa.Column("id_pedido", sa.Integer(), sa.ForeignKey("pedido.id_pedido"), nullable=True),
        sa.Column("fecha", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("tipo", sa.String(20), nullable=False),
        sa.Column("cantidad", sa.Integer(), nullable=False),
        sa.Column("observacion", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    pass
