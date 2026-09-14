"""Helpers para idempotencia en la sincronización offline.

Cuando la tablet pierde conexión guarda las operaciones localmente y luego
las reintenta. Para que el backend no duplique pedidos/pagos/visitas, el front
manda un `idempotency_key` (único por operación). Si ya existe un registro con
esa clave, devolvemos el registro original en vez de crear uno nuevo.
"""
from __future__ import annotations

from typing import Optional, Type, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

T = TypeVar("T")


def buscar_por_idempotency_key(
    db: Session,
    model: Type[T],
    idempotency_key: Optional[str],
) -> Optional[T]:
    """Devuelve el registro existente con esa clave de idempotencia, o None.

    Si `idempotency_key` es None/vacío (operación sin offline), no busca nada.
    """
    if not idempotency_key:
        return None
    return db.execute(
        select(model).where(model.idempotency_key == idempotency_key)
    ).scalar_one_or_none()
