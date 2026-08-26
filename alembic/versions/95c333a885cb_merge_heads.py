"""merge heads

Revision ID: 95c333a885cb
Revises: 20eb03488618, 26777f116cdf
Create Date: 2026-03-14 17:03:36.005140

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '95c333a885cb'
down_revision: Union[str, Sequence[str], None] = ('20eb03488618', '26777f116cdf')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
