from decimal import Decimal
from fastapi import APIRouter, Depends
from app.core.security import get_current_user
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.clienteServicioService import (
    crear_servicio_alquiler_dispenser,
    listar_pendientes_cliente,
    pagar_periodo_servicio,
    actualizar_monto_servicio,
    listar_servicios_cliente,
    dar_de_baja_dispenser,
)
from app.schemas.servicios import ServicioMontoUpdate, ClienteServicioOut

router = APIRouter(
    prefix="/servicios",
    tags=["Servicios"],
    dependencies=[Depends(get_current_user)],
)


@router.post("/clientes/{legajo}/alquiler-dispenser")
def alta_alquiler_dispenser(
    legajo: int,
    monto_mensual: Decimal,
    db: Session = Depends(get_db),
):
    try:
        srv, per = crear_servicio_alquiler_dispenser(db, legajo, monto_mensual)
        db.commit()

        return {
            "ok": True,
            "id_cliente_servicio": srv.id_cliente_servicio,
            "id_periodo": per.id_periodo,
            "estado_periodo": per.estado,
            "periodo": per.periodo.isoformat(),
            "monto_mensual": str(srv.monto_mensual),
            "monto_pendiente": str(per.monto_pendiente),
        }
    except Exception:
        db.rollback()
        raise


@router.get("/clientes/{legajo}/pendientes")
def pendientes(legajo: int, db: Session = Depends(get_db)):
    return listar_pendientes_cliente(db, legajo)


@router.get("/clientes/{legajo}", response_model=list[ClienteServicioOut])
def get_servicios_cliente(
    legajo: int,
    db: Session = Depends(get_db),
):
    return listar_servicios_cliente(db, legajo)


@router.post("/periodos/{id_periodo}/pagar")
def pagar(
    id_periodo: int,
    legajo: int,
    id_medio_pago: int | None = None,
    id_cuenta: int | None = None,
    usar_saldo: bool = False,
    observacion: str | None = None,
    db: Session = Depends(get_db),
):
    try:
        pago, monto = pagar_periodo_servicio(
            db,
            id_periodo,
            legajo,
            id_medio_pago,
            observacion,
            id_cuenta=id_cuenta,
            usar_saldo=usar_saldo,
        )
        db.commit()

        return (
            {"ok": True, "id_pago": pago.id_pago, "monto": str(pago.monto)}
            if pago
            else {"ok": True, "id_pago": None, "monto": str(monto)}
        )
    except Exception:
        db.rollback()
        raise


@router.delete("/{id_cliente_servicio}/alquiler-dispenser")
def baja_alquiler_dispenser(
    id_cliente_servicio: int,
    db: Session = Depends(get_db),
):
    try:
        srv = dar_de_baja_dispenser(db, id_cliente_servicio)
        db.commit()
        return {"ok": True, "id_cliente_servicio": srv.id_cliente_servicio, "activo": srv.activo}
    except Exception:
        db.rollback()
        raise


@router.patch("/{id_cliente_servicio}/monto")
def patch_monto_servicio(
    id_cliente_servicio: int,
    payload: ServicioMontoUpdate,
    db: Session = Depends(get_db),
):
    try:
        srv = actualizar_monto_servicio(
            db,
            id_cliente_servicio=id_cliente_servicio,
            nuevo_monto=payload.monto_mensual,
            aplicar_desde=payload.aplicar_desde,
            actualizar_periodos_no_pagados=payload.actualizar_periodos_no_pagados,
        )
        db.commit()

        return {
            "ok": True,
            "id_cliente_servicio": srv.id_cliente_servicio,
            "monto_mensual": str(srv.monto_mensual),
        }
    except Exception:
        db.rollback()
        raise
