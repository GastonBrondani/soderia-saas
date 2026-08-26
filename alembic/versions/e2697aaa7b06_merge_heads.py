"""merge_heads

Revision ID: e2697aaa7b06
Revises: 668e9b105672, f00dcafe1234
Create Date: 2026-02-02 21:18:56.133476

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e2697aaa7b06'
down_revision: Union[str, Sequence[str], None] = ('668e9b105672', 'f00dcafe1234')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
