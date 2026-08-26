"""add cascade on cliente foreign keys

Revision ID: 043c59d9f681
Revises: 40e5d84473a6
Create Date: 2025-11-12 21:19:14.456750

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '043c59d9f681'
down_revision: Union[str, Sequence[str], None] = '40e5d84473a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # cliente_cuenta.legajo -> cliente.legajo
    op.drop_constraint(
        "cliente_cuenta_legajo_fkey",
        "cliente_cuenta",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "cliente_cuenta_legajo_fkey",
        "cliente_cuenta",
        "cliente",
        ["legajo"],
        ["legajo"],
        ondelete="CASCADE",
    )

    # cliente_dia_semana.id_cliente -> cliente.legajo
    op.drop_constraint(
        "cliente_dia_semana_id_cliente_fkey",
        "cliente_dia_semana",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "cliente_dia_semana_id_cliente_fkey",
        "cliente_dia_semana",
        "cliente",
        ["id_cliente"],
        ["legajo"],
        ondelete="CASCADE",
    )

    # direccion_cliente.legajo -> cliente.legajo
    op.drop_constraint(
        "direccion_cliente_legajo_fkey",
        "direccion_cliente",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "direccion_cliente_legajo_fkey",
        "direccion_cliente",
        "cliente",
        ["legajo"],
        ["legajo"],
        ondelete="CASCADE",
    )

    # documentos.legajo -> cliente.legajo
    op.drop_constraint(
        "documentos_legajo_fkey",
        "documentos",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "documentos_legajo_fkey",
        "documentos",
        "cliente",
        ["legajo"],
        ["legajo"],
        ondelete="CASCADE",
    )

    # historico.legajo -> cliente.legajo
    op.drop_constraint(
        "historico_legajo_fkey",
        "historico",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "historico_legajo_fkey",
        "historico",
        "cliente",
        ["legajo"],
        ["legajo"],
        ondelete="CASCADE",
    )

    # mail_cliente.legajo -> cliente.legajo
    op.drop_constraint(
        "mail_cliente_legajo_fkey",
        "mail_cliente",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "mail_cliente_legajo_fkey",
        "mail_cliente",
        "cliente",
        ["legajo"],
        ["legajo"],
        ondelete="CASCADE",
    )

    # producto_cliente.legajo -> cliente.legajo
    op.drop_constraint(
        "producto_cliente_legajo_fkey",
        "producto_cliente",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "producto_cliente_legajo_fkey",
        "producto_cliente",
        "cliente",
        ["legajo"],
        ["legajo"],
        ondelete="CASCADE",
    )

    # telefono_cliente.legajo -> cliente.legajo
    op.drop_constraint(
        "telefono_cliente_legajo_fkey",
        "telefono_cliente",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "telefono_cliente_legajo_fkey",
        "telefono_cliente",
        "cliente",
        ["legajo"],
        ["legajo"],
        ondelete="CASCADE",
    )

    # usuario.legajo_cliente -> cliente.legajo
    op.drop_constraint(
        "usuario_legajo_cliente_fkey",
        "usuario",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "usuario_legajo_cliente_fkey",
        "usuario",
        "cliente",
        ["legajo_cliente"],
        ["legajo"],
        ondelete="CASCADE",
    )

    # cliente_reparto_dia.legajo -> cliente.legajo
    op.drop_constraint(
        "cliente_reparto_dia_legajo_fkey",
        "cliente_reparto_dia",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "cliente_reparto_dia_legajo_fkey",
        "cliente_reparto_dia",
        "cliente",
        ["legajo"],
        ["legajo"],
        ondelete="CASCADE",
    )

    # pedido.legajo -> cliente.legajo
    op.drop_constraint(
        "pedido_legajo_fkey",
        "pedido",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "pedido_legajo_fkey",
        "pedido",
        "cliente",
        ["legajo"],
        ["legajo"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    """Downgrade schema."""
    pass
