"""servicios alquiler dispenser

Revision ID: b881f9bc3a14
Revises: 4cb932ca2fa8
Create Date: 2025-12-31 16:47:44.108221

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b881f9bc3a14'
down_revision: Union[str, Sequence[str], None] = '4cb932ca2fa8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(
        "cliente_servicio",
        sa.Column("id_cliente_servicio", sa.Integer(), primary_key=True),
        sa.Column("legajo", sa.Integer(), sa.ForeignKey("cliente.legajo", ondelete="CASCADE"), nullable=False),
        sa.Column("tipo_servicio", sa.String(length=50), nullable=False),
        sa.Column("monto_mensual", sa.Numeric(12, 2), nullable=False),
        sa.Column("fecha_inicio", sa.Date(), nullable=False),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_cliente_servicio_legajo_activo", "cliente_servicio", ["legajo", "activo"])

    op.create_table(
        "cliente_servicio_periodo",
        sa.Column("id_periodo", sa.Integer(), primary_key=True),
        sa.Column("id_cliente_servicio", sa.Integer(), sa.ForeignKey("cliente_servicio.id_cliente_servicio", ondelete="CASCADE"), nullable=False),
        sa.Column("periodo", sa.Date(), nullable=False),  # 1er día del mes
        sa.Column("monto", sa.Numeric(12, 2), nullable=False),
        sa.Column("estado", sa.String(length=20), nullable=False, server_default="PENDIENTE"),
        sa.Column("fecha_vencimiento", sa.Date(), nullable=False),
        sa.Column("fecha_pago", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("id_cliente_servicio", "periodo", name="uq_servicio_periodo"),
    )
    op.create_index("ix_servicio_periodo_estado", "cliente_servicio_periodo", ["estado"])

    # pago -> link opcional al periodo
    op.add_column("pago", sa.Column("id_cliente_servicio_periodo", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_pago_servicio_periodo",
        "pago",
        "cliente_servicio_periodo",
        ["id_cliente_servicio_periodo"],
        ["id_periodo"],
        ondelete="SET NULL",
    )

    # (Opcional) CHECK simples para mantener integridad sin enums
    op.create_check_constraint(
        "ck_cliente_servicio_tipo",
        "cliente_servicio",
        "tipo_servicio IN ('ALQUILER_DISPENSER')",
    )
    op.create_check_constraint(
        "ck_servicio_periodo_estado",
        "cliente_servicio_periodo",
        "estado IN ('PENDIENTE','PAGADO','VENCIDO')",
    )


def downgrade():
    op.drop_constraint("ck_servicio_periodo_estado", "cliente_servicio_periodo", type_="check")
    op.drop_constraint("ck_cliente_servicio_tipo", "cliente_servicio", type_="check")
    op.drop_constraint("fk_pago_servicio_periodo", "pago", type_="foreignkey")
    op.drop_column("pago", "id_cliente_servicio_periodo")
    op.drop_index("ix_servicio_periodo_estado", table_name="cliente_servicio_periodo")
    op.drop_table("cliente_servicio_periodo")
    op.drop_index("ix_cliente_servicio_legajo_activo", table_name="cliente_servicio")
    op.drop_table("cliente_servicio")
