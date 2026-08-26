from datetime import date
from fastapi import APIRouter, Depends, Query
from app.core.security import get_current_user
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.cajaEmpresaService import CajaEmpresaService
from app.schemas.cajaEmpresa import CajaEmpresaTotalOut
from app.schemas.cajaEmpresa import (   
    CajaEmpresaMovimientosListOut,
)

router = APIRouter(prefix="/caja-empresa", tags=["Caja Empresa"],dependencies=[Depends(get_current_user)],)

#Usado para probar el cierre diario de caja por repartos, despues se hace automatico
@router.post("/cierre-diario", summary="Generar cierre de caja por repartos del día")
def generar_cierre_diario(
    fecha: date | None = Query(None, description="Fecha del reparto (default: hoy)"),
    db: Session = Depends(get_db),
):
    if fecha is None:
        from datetime import date as _date
        fecha = _date.today()

    creados = CajaEmpresaService.generar_cierre_repartos_por_fecha(db, fecha)

    return {
        "fecha": fecha,
        "movimientos_creados": creados,
    }


#Get total de la caja empresa
@router.get("/total", response_model=CajaEmpresaTotalOut)
def get_total_caja(
    id_empresa: int | None = Query(
        None, description="Opcional: filtrar por empresa"
    ),
    db: Session = Depends(get_db),
):
    total = CajaEmpresaService.total_general(db, id_empresa=id_empresa)
    return CajaEmpresaTotalOut(total=total)

#Get total de la caja empresa por fecha
@router.get("/total-por-fecha", response_model=CajaEmpresaTotalOut)
def get_total_caja_por_fecha(
    fecha: date = Query(..., description="Fecha a consultar"),
    id_empresa: int | None = Query(
        None, description="Opcional: filtrar por empresa"
    ),
    db: Session = Depends(get_db),
):
    total = CajaEmpresaService.total_por_fecha(
        db,
        fecha=fecha,
        id_empresa=id_empresa,
    )
    return CajaEmpresaTotalOut(total=total)

#Get total de la caja empresa por rango de fechas
@router.get("/total-por-rango", response_model=CajaEmpresaTotalOut)
def get_total_caja_por_rango(
    fecha_desde: date = Query(..., description="Desde (inclusive)"),
    fecha_hasta: date = Query(..., description="Hasta (inclusive)"),
    id_empresa: int | None = Query(
        None, description="Opcional: filtrar por empresa"
    ),
    db: Session = Depends(get_db),
):
    total = CajaEmpresaService.total_por_rango(
        db,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        id_empresa=id_empresa,
    )
    return CajaEmpresaTotalOut(total=total)

@router.get("/movimientos", response_model=CajaEmpresaMovimientosListOut)
def listar_movimientos(
    fecha_desde: date = Query(..., description="Desde (inclusive)"),
    fecha_hasta: date = Query(..., description="Hasta (inclusive)"),
    id_empresa: int | None = Query(None, description="Opcional: filtrar por empresa"),
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    items, total = CajaEmpresaService.listar_movimientos(
        db,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        id_empresa=id_empresa,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "total": total}
