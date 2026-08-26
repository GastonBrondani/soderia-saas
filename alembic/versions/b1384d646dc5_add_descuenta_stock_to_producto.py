"""Add descuenta_stock to producto

Revision ID: b1384d646dc5
Revises: 50a6eb108e44
Create Date: 2025-12-19 18:41:09.874400

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b1384d646dc5'
down_revision: Union[str, Sequence[str], None] = '50a6eb108e44'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "producto",
        sa.Column(
            "descuenta_stock",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )


def downgrade() -> None:
    op.drop_column("producto", "descuenta_stock")
