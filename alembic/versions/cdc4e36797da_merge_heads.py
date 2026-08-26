"""merge heads

Revision ID: cdc4e36797da
Revises: 668e9b105672, b881f9bc3a14
Create Date: 2026-01-29 21:02:43.627488

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cdc4e36797da'
down_revision: Union[str, Sequence[str], None] = ('668e9b105672', 'b881f9bc3a14')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
