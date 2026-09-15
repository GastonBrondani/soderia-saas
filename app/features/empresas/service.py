"""Cada sodería (tenant) tiene una única empresa en su base.

Varios endpoints todavia piden `id_empresa` como parametro al cliente, un
resabio de una epoca en la que la sodería no era su propia base de datos.
Este helper reemplaza eso: la empresa se infiere del tenant actual en vez de
que la mande quien llama.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFound
from app.features.empresas.models.empresa import Empresa


class EmpresaService:
    @staticmethod
    def get_id_empresa_actual(db: Session) -> int:
        """Id de la (unica) empresa de esta sodería."""
        id_empresa = db.execute(
            select(Empresa.id_empresa).order_by(Empresa.id_empresa).limit(1)
        ).scalar_one_or_none()
        if id_empresa is None:
            raise NotFound("La sodería no tiene una empresa configurada.")
        return id_empresa
