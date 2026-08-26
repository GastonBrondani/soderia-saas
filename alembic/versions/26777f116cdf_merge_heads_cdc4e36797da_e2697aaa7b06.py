"""merge heads cdc4e36797da + e2697aaa7b06

Revision ID: 26777f116cdf
Revises: cdc4e36797da, e2697aaa7b06
Create Date: 2026-02-18 20:01:53.858552

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '26777f116cdf'
down_revision: Union[str, Sequence[str], None] = ('cdc4e36797da', 'e2697aaa7b06')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
