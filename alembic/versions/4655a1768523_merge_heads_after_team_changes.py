"""merge heads after team changes

Revision ID: 4655a1768523
Revises: 610598a8b6eb, b1384d646dc5
Create Date: 2025-12-24 18:45:56.563476

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4655a1768523'
down_revision: Union[str, Sequence[str], None] = ('610598a8b6eb', 'b1384d646dc5')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
