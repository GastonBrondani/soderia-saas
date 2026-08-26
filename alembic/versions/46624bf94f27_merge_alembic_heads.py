"""merge alembic heads

Revision ID: 46624bf94f27
Revises: 409913c99187, 95c333a885cb
Create Date: 2026-04-29 17:04:39.738271

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '46624bf94f27'
down_revision: Union[str, Sequence[str], None] = ('409913c99187', '95c333a885cb')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
