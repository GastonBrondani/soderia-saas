"""add idempotency_key/client_uuid a pedido, pago y visita (offline sync)

Esta migración también fusiona las dos heads existentes
(43b8e99ef4ae y a35473d423e9) para dejar un único head.

Revision ID: d1f0offline01
Revises: 43b8e99ef4ae, a35473d423e9
Create Date: 2026-06-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d1f0offline01"
down_revision: Union[str, Sequence[str], None] = ("43b8e99ef4ae", "a35473d423e9")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Tablas que reciben las columnas de idempotencia para la sincronización offline.
_TABLAS = ("pedido", "pago", "visita")


def upgrade() -> None:
    for tabla in _TABLAS:
        op.add_column(
            tabla,
            sa.Column("idempotency_key", sa.String(length=80), nullable=True),
        )
        op.add_column(
            tabla,
            sa.Column("client_uuid", sa.String(length=80), nullable=True),
        )
        # Índice único: garantiza que la misma operación no se cree dos veces.
        # En Postgres los NULL se consideran distintos, así que las filas
        # antiguas sin clave no chocan entre sí.
        op.create_index(
            f"uq_{tabla}_idempotency_key",
            tabla,
            ["idempotency_key"],
            unique=True,
        )


def downgrade() -> None:
    for tabla in _TABLAS:
        op.drop_index(f"uq_{tabla}_idempotency_key", table_name=tabla)
        op.drop_column(tabla, "client_uuid")
        op.drop_column(tabla, "idempotency_key")
