from __future__ import annotations
from datetime import datetime
from typing import Any, Mapping, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.historico import Historico
from app.models.tipoEvento import TipoEvento
from app.schemas.enumsHistorico import TipoEventoCodigoEnum


def _get_tipo_evento_or_fail(
    db: Session,
    codigo: TipoEventoCodigoEnum,
) -> TipoEvento:
    stmt = select(TipoEvento).where(TipoEvento.nombre == codigo.value)
    tipo = db.execute(stmt).scalar_one_or_none()
    if tipo is None:
        # Podés cambiar esto por HTTPException si lo usás directo desde un router,
        # o dejarlo como RuntimeError porque es un error de configuración.
        raise RuntimeError(
            f"No existe TipoEvento con nombre={codigo.value}. "
            "Crealo en la tabla tipo_evento."
        )
    return tipo


def registrar_evento_cliente(db: Session,*,legajo: int,codigo_evento: TipoEventoCodigoEnum,observacion: Optional[str] = None,datos: Optional[Mapping[str, Any]] = None,) -> Historico:
    tipo = _get_tipo_evento_or_fail(db, codigo_evento)

    hist = Historico(
        legajo=legajo,
        id_evento=tipo.id_evento,
        fecha=datetime.now(),  
        observacion=observacion,
        datos=dict(datos) if datos is not None else None,
    )
    db.add(hist)
    # OJO: no hacemos commit acá. Lo hace quien llama.
    return hist
