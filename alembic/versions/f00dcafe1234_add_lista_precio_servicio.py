"""add_lista_precio_servicio

Revision ID: f00dcafe1234
Revises: b881f9bc3a14
Create Date: 2026-02-02 16:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f00dcafe1234"
down_revision: Union[str, Sequence[str], None] = "b881f9bc3a14"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "lista_precio_servicio",
        sa.Column("id_lista", sa.Integer(), nullable=False),
        sa.Column("id_cliente_servicio", sa.Integer(), nullable=False),
        sa.Column("precio", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.ForeignKeyConstraint(
            ["id_lista"], ["lista_de_precios.id_lista"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["id_cliente_servicio"],
            ["cliente_servicio.id_cliente_servicio"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id_lista", "id_cliente_servicio"),
    )


def downgrade() -> None:
    op.drop_table("lista_precio_servicio")
