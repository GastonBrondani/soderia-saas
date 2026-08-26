"""Creacion combo + lista_precio_combo + combo_producto

Revision ID: 50a6eb108e44
Revises: c6451763b6a5
Create Date: 2025-12-17 21:31:17.487672

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '50a6eb108e44'
down_revision: Union[str, Sequence[str], None] = 'c6451763b6a5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- tablas nuevas ---
    op.create_table(
        "combo",
        sa.Column("id_combo", sa.Integer(), nullable=False),
        sa.Column("id_empresa", sa.Integer(), nullable=False),
        sa.Column("nombre", sa.String(length=120), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("estado", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.ForeignKeyConstraint(["id_empresa"], ["empresa.id_empresa"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id_combo"),
    )

    op.create_table(
        "combo_producto",
        sa.Column("id_combo", sa.Integer(), nullable=False),
        sa.Column("id_producto", sa.Integer(), nullable=False),
        sa.Column("cantidad", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["id_combo"], ["combo.id_combo"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["id_producto"], ["producto.id_producto"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id_combo", "id_producto"),
    )

    op.create_table(
        "lista_precio_combo",
        sa.Column("id_lista", sa.Integer(), nullable=False),
        sa.Column("id_combo", sa.Integer(), nullable=False),
        sa.Column("precio", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.ForeignKeyConstraint(["id_combo"], ["combo.id_combo"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["id_lista"], ["lista_de_precios.id_lista"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id_lista", "id_combo"),
    )

    # --- pedido_producto: columna nueva PK + combo ---
    op.execute("CREATE SEQUENCE IF NOT EXISTS pedido_producto_id_pedido_producto_seq")

    # 1) agregar columnas (todavía nullable)
    op.add_column("pedido_producto", sa.Column("id_pedido_producto", sa.Integer(), nullable=True))
    op.add_column("pedido_producto", sa.Column("id_combo", sa.Integer(), nullable=True))

    # 2) backfill para filas existentes
    op.execute(
        "UPDATE pedido_producto "
        "SET id_pedido_producto = nextval('pedido_producto_id_pedido_producto_seq') "
        "WHERE id_pedido_producto IS NULL"
    )

    # 3) dejar id_pedido_producto listo para ser PK
    op.alter_column(
        "pedido_producto",
        "id_pedido_producto",
        nullable=False,
        server_default=sa.text("nextval('pedido_producto_id_pedido_producto_seq')"),
    )

    # 4) cambiar PK (primero dropeo la vieja, después creo la nueva)
    op.drop_constraint("pedido_producto_pkey", "pedido_producto", type_="primary")
    op.create_primary_key("pedido_producto_pkey", "pedido_producto", ["id_pedido_producto"])

    # 5) ahora sí puedo hacer id_producto nullable
    op.alter_column("pedido_producto", "id_producto", existing_type=sa.INTEGER(), nullable=True)

    # 6) FK a combo
    op.create_foreign_key(
        "fk_pedido_producto_combo",
        "pedido_producto",
        "combo",
        ["id_combo"],
        ["id_combo"],
        ondelete="RESTRICT",
    )

    # 7) CHECK: exactamente uno entre producto/combo
    op.create_check_constraint(
        "ck_pedido_producto_exactly_one",
        "pedido_producto",
        "(id_producto IS NOT NULL AND id_combo IS NULL) OR (id_producto IS NULL AND id_combo IS NOT NULL)",
    )

    # 8) unicidad por pedido (Postgres: índices únicos parciales)
    op.create_index(
        "ux_pedido_producto_pedido_prod",
        "pedido_producto",
        ["id_pedido", "id_producto"],
        unique=True,
        postgresql_where=sa.text("id_combo IS NULL AND id_producto IS NOT NULL"),
    )
    op.create_index(
        "ux_pedido_producto_pedido_combo",
        "pedido_producto",
        ["id_pedido", "id_combo"],
        unique=True,
        postgresql_where=sa.text("id_producto IS NULL AND id_combo IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ux_pedido_producto_pedido_combo", table_name="pedido_producto")
    op.drop_index("ux_pedido_producto_pedido_prod", table_name="pedido_producto")

    op.drop_constraint("ck_pedido_producto_exactly_one", "pedido_producto", type_="check")
    op.drop_constraint("fk_pedido_producto_combo", "pedido_producto", type_="foreignkey")

    # si hay filas con combos, no se puede volver a NOT NULL id_producto sin borrar/transformar
    op.execute("DELETE FROM pedido_producto WHERE id_combo IS NOT NULL")

    op.drop_constraint("pedido_producto_pkey", "pedido_producto", type_="primary")
    op.create_primary_key("pedido_producto_pkey", "pedido_producto", ["id_pedido", "id_producto"])

    op.alter_column("pedido_producto", "id_producto", existing_type=sa.INTEGER(), nullable=False)

    op.drop_column("pedido_producto", "id_combo")
    op.drop_column("pedido_producto", "id_pedido_producto")

    op.execute("DROP SEQUENCE IF EXISTS pedido_producto_id_pedido_producto_seq")

    op.drop_table("lista_precio_combo")
    op.drop_table("combo_producto")
    op.drop_table("combo")