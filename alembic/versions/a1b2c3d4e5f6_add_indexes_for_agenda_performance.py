"""add indexes for agenda performance

Revision ID: a1b2c3d4e5f6
Revises: d1f0offline01
Create Date: 2026-06-13

"""
from typing import Sequence, Union
from alembic import op


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "d1f0offline01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Covering index for the agenda subquery:
    # WHERE fecha >= X AND fecha < Y  →  legajo, estado selected
    # Avoids a full table scan on visita when loading the daily agenda.
    op.create_index(
        "idx_visita_fecha_legajo_estado",
        "visita",
        ["fecha", "legajo", "estado"],
    )


def downgrade() -> None:
    op.drop_index("idx_visita_fecha_legajo_estado", table_name="visita")
