"""merge heads

Revision ID: a35473d423e9
Revises: 409913c99187, 95c333a885cb
Create Date: 2026-04-07 11:23:04.705027

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a35473d423e9'
down_revision: Union[str, Sequence[str], None] = ('409913c99187', '95c333a885cb')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
