"""actualizacion tabla pago

Revision ID: 4cb932ca2fa8
Revises: 8cce5e38f4cc
Create Date: 2025-12-22 21:00:35.084437

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4cb932ca2fa8'
down_revision: Union[str, Sequence[str], None] = '4655a1768523'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(
        "pago",
        sa.Column("id_pago", sa.Integer(), primary_key=True),
        sa.Column("id_empresa", sa.Integer(), sa.ForeignKey("empresa.id_empresa", ondelete="CASCADE"), nullable=False),
        sa.Column("legajo", sa.Integer(), sa.ForeignKey("cliente.legajo", ondelete="SET NULL"), nullable=True),
        sa.Column("id_pedido", sa.Integer(), sa.ForeignKey("pedido.id_pedido", ondelete="SET NULL"), nullable=True),
        sa.Column("id_repartodia", sa.Integer(), sa.ForeignKey("reparto_dia.id_repartodia", ondelete="SET NULL"), nullable=True),

        sa.Column("id_medio_pago", sa.Integer(), sa.ForeignKey("medio_pago.id_medio_pago"), nullable=False),

        sa.Column("fecha", sa.DateTime(timezone=False), nullable=False),
        sa.Column("monto", sa.Numeric(14, 2), nullable=False),

        sa.Column("tipo_pago", sa.String(30), nullable=False),  # ej: "COBRO_PEDIDO", "PAGO_DEUDA", "EGRESO_EMPRESA"
        sa.Column("observacion", sa.Text(), nullable=True),
    )

    op.create_index("ix_pago_empresa_fecha", "pago", ["id_empresa", "fecha"])
    op.create_index("ix_pago_pedido", "pago", ["id_pedido"])
    op.create_index("ix_pago_legajo", "pago", ["legajo"])
    op.create_index("ix_pago_reparto", "pago", ["id_repartodia"])

def downgrade():
    op.drop_index("ix_pago_reparto", table_name="pago")
    op.drop_index("ix_pago_legajo", table_name="pago")
    op.drop_index("ix_pago_pedido", table_name="pago")
    op.drop_index("ix_pago_empresa_fecha", table_name="pago")
    op.drop_table("pago")
