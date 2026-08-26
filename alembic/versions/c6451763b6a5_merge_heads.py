"""merge heads

Revision ID: c6451763b6a5
Revises: 043c59d9f681, eb0d71ad3c76
Create Date: 2025-11-26 19:10:05.135645

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c6451763b6a5'
down_revision: Union[str, Sequence[str], None] = ('043c59d9f681', 'eb0d71ad3c76')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
