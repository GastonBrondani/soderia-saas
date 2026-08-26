"""add datos jsonb to historico

Revision ID: 8c228284a4e9
Revises: b8989cea9903
Create Date: 2025-11-19 16:52:26.986687

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '8c228284a4e9'
down_revision: Union[str, Sequence[str], None] = 'b8989cea9903'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "historico",
        sa.Column(
            "datos",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )

def downgrade() -> None:
    op.drop_column("historico", "datos")
