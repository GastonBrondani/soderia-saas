"""add id_cuenta to pago

Revision ID: 668e9b105672
Revises: bcaa8abf99de
Create Date: 2026-01-28 18:57:11.878059

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '668e9b105672'
down_revision: Union[str, Sequence[str], None] = 'bcaa8abf99de'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1️⃣ Agregar columna
    op.add_column(
        "pago",
        sa.Column("id_cuenta", sa.Integer(), nullable=True),
    )

    # 2️⃣ Foreign key a cliente_cuenta
    op.create_foreign_key(
        "fk_pago_id_cuenta_cliente_cuenta",
        "pago",
        "cliente_cuenta",
        ["id_cuenta"],
        ["id_cuenta"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    # rollback limpio
    op.drop_constraint(
        "fk_pago_id_cuenta_cliente_cuenta",
        "pago",
        type_="foreignkey",
    )
    op.drop_column("pago", "id_cuenta")

