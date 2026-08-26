"""add id_cuenta to pedido

Revision ID: bcaa8abf99de
Revises: 4cb932ca2fa8
Create Date: 2026-01-27 19:25:48.575566
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "bcaa8abf99de"
down_revision: Union[str, Sequence[str], None] = "4cb932ca2fa8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) Agregar columna
    op.add_column("pedido", sa.Column("id_cuenta", sa.Integer(), nullable=True))

    # 2) Crear FK con nombre explícito (mejor que None)
    op.create_foreign_key(
        "fk_pedido_id_cuenta_cliente_cuenta",
        "pedido",
        "cliente_cuenta",
        ["id_cuenta"],
        ["id_cuenta"],
        ondelete=None,
    )


def downgrade() -> None:
    op.drop_constraint("fk_pedido_id_cuenta_cliente_cuenta", "pedido", type_="foreignkey")
    op.drop_column("pedido", "id_cuenta")
