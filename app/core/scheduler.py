from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select
from sqlalchemy.orm import Session


from app.core.database import SessionLocal
from app.models.repartoDia import RepartoDia
from app.models.empresa import Empresa
from app.models.usuario import Usuario
from app.models.rol import Rol
from app.models.usuarioRol import UsuarioRol

# from app.services.cajaEmpresaService import CajaEmpresaService


scheduler: AsyncIOScheduler | None = None


def ensure_usuario_sis(db: Session) -> Usuario:
    usuarios = (
        db.execute(
            select(Usuario).where(Usuario.nombre_usuario == "sis")
        )
        .scalars()
        .all()
    )

    if len(usuarios) == 0:
        raise RuntimeError(
            "No existe el usuario de sistema 'sis'. Debe existir exactamente uno."
        )

    if len(usuarios) > 1:
        raise RuntimeError(
            f"Se encontraron {len(usuarios)} usuarios 'sis'. Debe existir solo uno."
        )

    usuario = usuarios[0]

    tiene_superadmin = db.execute(
        select(Rol.id_rol)
        .join(UsuarioRol, UsuarioRol.id_rol == Rol.id_rol)
        .where(
            UsuarioRol.id_usuario == usuario.id_usuario,
            Rol.nombre == "SUPERADMINISTRADOR",
        )
    ).first()

    if not tiene_superadmin:
        raise RuntimeError(
            "El usuario 'sis' no tiene el rol SUPERADMINISTRADOR."
        )

    return usuario
    




def crear_repartos_del_dia_automaticos(
    db: Session,
    fecha: Optional[date] = None,
) -> None:
    """
    Crea, para cada empresa, un registro reparto_dia en la fecha indicada
    (o en hoy si no se pasa fecha), usando el usuario 'sis'.

    Si para una empresa ya existe reparto_dia con esa fecha, no hace nada.
    """
    if fecha is None:
        fecha = date.today()

    usuario_sis = ensure_usuario_sis(db)

    empresas_ids = db.execute(select(Empresa.id_empresa)).scalars().all()

    for id_empresa in empresas_ids:
        reparto = (
            db.execute(
                select(RepartoDia).where(
                    RepartoDia.id_empresa == id_empresa,
                    RepartoDia.fecha == fecha,
                )
            )
            .scalars()
            .first()
        )

        if reparto:
            continue

        nuevo = RepartoDia(
            id_usuario=usuario_sis.id_usuario,
            id_empresa=id_empresa,
            fecha=fecha,
            total_recaudado=Decimal("0"),
            total_efectivo=Decimal("0"),
            total_virtual=Decimal("0"),
            observacion="Creado automáticamente por el sistema (usuario sis)",
        )
        db.add(nuevo)

    db.commit()


def start_scheduler() -> None:
    """
    - Asegura que exista el reparto_dia de HOY al arrancar.
    - Arranca el scheduler para crear repartos todos los días a las 00:05.
    """
    global scheduler

    if scheduler is not None and scheduler.running:
        return

    # 1) Crear repartos del día actual (si no existen)
    db = SessionLocal()
    try:
        crear_repartos_del_dia_automaticos(db)
    finally:
        db.close()

    # 2) Scheduler diario
    scheduler = AsyncIOScheduler(timezone="America/Argentina/Cordoba")

    @scheduler.scheduled_job(CronTrigger(hour=0, minute=5))
    def job_crear_repartos():
        db = SessionLocal()
        try:
            crear_repartos_del_dia_automaticos(db)
        finally:
            db.close()

    # No lo usamos porque esta duplicando los montos en caja empresa
    # @scheduler.scheduled_job(CronTrigger(hour=23, minute=55))
    # def job_cerrar_caja():
    #    db = SessionLocal()
    #    try:
    #        CajaEmpresaService.generar_cierre_repartos_por_fecha(db)
    #    finally:
    #        db.close()

    scheduler.start()


def stop_scheduler() -> None:
    """
    Detiene el scheduler cuando se apaga la app.
    """
    global scheduler

    if scheduler is not None and scheduler.running:
        scheduler.shutdown()
