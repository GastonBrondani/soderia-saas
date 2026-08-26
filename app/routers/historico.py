from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Query, status, Depends, HTTPException
from app.core.security import get_current_user
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.orm import Session
from typing import List, Optional


from app.core.database import get_db

from app.models.cliente import Cliente
from app.models.historico import Historico
from app.schemas.historico import HistoricoOut


router = APIRouter(prefix="/historico", tags=["Historico"],dependencies=[Depends(get_current_user)],)


@router.get(
    "/{legajo}/feed",
    response_model=List[HistoricoOut],
    status_code=status.HTTP_200_OK,
)
def feed_historico_cliente(
    legajo: int,
    fecha_desde: Optional[date] = Query(
        None, description="Inicio del rango (inclusive). Default: hace 7 días."
    ),
    fecha_hasta: Optional[date] = Query(
        None, description="Fin del rango (inclusive). Default: hoy."
    ),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """
    Histórico de un cliente filtrado por rango de fechas, ordenado del más
    reciente al más antiguo. Si no se pasan fechas, devuelve la última semana.
    Cada evento incluye el `monto` (el total del pedido cuando aplica).
    """
    cliente = db.get(Cliente, legajo)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    hoy = date.today()
    if fecha_hasta is None:
        fecha_hasta = hoy
    if fecha_desde is None:
        fecha_desde = fecha_hasta - timedelta(days=7)
    if fecha_desde > fecha_hasta:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="fecha_desde no puede ser mayor que fecha_hasta",
        )

    inicio = datetime.combine(fecha_desde, time.min)
    fin = datetime.combine(fecha_hasta, time.max)

    stmt = (
        select(Historico)
        .where(
            Historico.legajo == legajo,
            Historico.fecha >= inicio,
            Historico.fecha <= fin,
        )
        .order_by(Historico.fecha.desc())
        .limit(limit)
        .options(selectinload(Historico.tipo_evento))
    )
    rows = db.execute(stmt).scalars().all()
    return [HistoricoOut.model_validate(h) for h in rows]


@router.get("/{legajo}",response_model=HistoricoOut, status_code=status.HTTP_200_OK)
def obtener_historico_cliente(legajo: int,db=Depends(get_db)):
    historico = db.query(Historico).filter(Historico.legajo == legajo).first()
    if not historico:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Historico no encontrado")
    return historico

@router.get(
    "/{legajo}/historicos",
    response_model=List[HistoricoOut],
    status_code=status.HTTP_200_OK,
)
def listar_historico_cliente(
    legajo: int,
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    cliente = db.get(Cliente, legajo)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    stmt = (
        select(Historico)
        .where(Historico.legajo == legajo)
        .order_by(Historico.fecha.desc())
        .limit(limit)
        .options(selectinload(Historico.tipo_evento))  # 👈 cambio clave
    )
    rows = db.execute(stmt).scalars().all()
    return [HistoricoOut.model_validate(h) for h in rows]
