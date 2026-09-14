"""
Scheduler multi-tenant.

Dos problemas del scheduler actual:

  1. Arranca dentro del proceso de la app. El Dockerfile.prod corre gunicorn
     con --workers 4, asi que hoy `crear_repartos_del_dia_automaticos` se
     ejecuta CUATRO veces todos los dias a las 00:05. Que no hayas visto
     repartos duplicados es porque la funcion chequea si ya existen, pero es
     suerte, no diseño. El job de cierre de caja que dejaste comentado con
     "esta duplicando los montos en caja empresa" es exactamente este bug.

  2. La zona horaria esta fija en America/Argentina/Cordoba. Una sodería en
     Jujuy o en otro pais necesita la suya.

Solucion: advisory locks de Postgres. Antes de correr, cada worker pide un
lock; el que lo consigue trabaja y los otros tres siguen de largo. Es un
lock a nivel de servidor de base, asi que funciona tambien con la app
replicada en varias maquinas.

Los jobs se agrupan por zona horaria: si tenes ocho soderias en Cordoba y
dos en Salta, se registran dos cron jobs, no diez.
"""

from __future__ import annotations

import logging
import zlib
from datetime import datetime, timedelta, timezone
from typing import Callable
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import text

from app.core.config import settings
from app.core.control_plane import TenantInfo, get_control_engine, listar_tenants
from app.core.database import sesion_tenant
from app.core.tenancy import usar_tenant

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None

# Namespace de los advisory locks de esta app. Cualquier entero sirve, pero
# tiene que ser distinto del que use otro sistema contra la misma base.
_LOCK_NAMESPACE = 84_001


def _clave_lock(nombre_job: str, id_tenant: int) -> tuple[int, int]:
    clave = f"{nombre_job}:{id_tenant}".encode()
    # crc32 da 32 bits sin signo; se recorta al rango de int4 de Postgres.
    return _LOCK_NAMESPACE, zlib.crc32(clave) & 0x7FFFFFFF


def _con_lock(nombre_job: str, tenant: TenantInfo, fn: Callable[[], None]) -> bool:
    """Corre fn solo si se consigue el lock. Devuelve si se ejecuto.

    El lock se toma sobre la conexion del control plane y se sostiene hasta
    que la funcion termina. Si el proceso muere en el medio, Postgres lo
    libera al cerrarse la conexion.
    """
    k1, k2 = _clave_lock(nombre_job, tenant.id_tenant)
    with get_control_engine().connect() as conn:
        obtenido = conn.execute(
            text("SELECT pg_try_advisory_lock(:k1, :k2)"), {"k1": k1, "k2": k2}
        ).scalar()
        if not obtenido:
            logger.debug(
                "Job '%s' de '%s' ya lo esta corriendo otro worker",
                nombre_job,
                tenant.codigo,
            )
            return False
        try:
            fn()
            return True
        finally:
            conn.execute(
                text("SELECT pg_advisory_unlock(:k1, :k2)"), {"k1": k1, "k2": k2}
            )


def ejecutar_para_tenants(
    nombre_job: str,
    tarea: Callable[[], None],
    tenants: list[TenantInfo] | None = None,
) -> None:
    """Corre una tarea para cada tenant, aislando fallas.

    Si la sodería 3 revienta, las 4 a 10 igual se procesan. Sin esto, un
    error en un cliente le corta el servicio a todos los demas.
    """
    tenants = tenants or [t for t in listar_tenants() if t.scheduler_activo]
    ok = fallidos = 0

    for tenant in tenants:
        try:
            with usar_tenant(tenant):
                if _con_lock(nombre_job, tenant, tarea):
                    ok += 1
        except Exception:
            fallidos += 1
            logger.exception(
                "Job '%s' fallo para la sodería '%s'", nombre_job, tenant.codigo
            )

    logger.info("Job '%s': %s ok, %s con error", nombre_job, ok, fallidos)


# ----------------------------------------------------------------------
# Tareas
# ----------------------------------------------------------------------


def _crear_repartos_del_dia() -> None:
    """Envuelve el service de repartos_dia."""
    from app.features.repartos.repartos_dia.services.repartos_scheduler import crear_repartos_del_dia_automaticos

    with sesion_tenant() as db:
        crear_repartos_del_dia_automaticos(db)
        db.commit()


def _job_repartos(timezone_str: str) -> Callable[[], None]:
    def job() -> None:
        tenants = [
            t
            for t in listar_tenants()
            if t.scheduler_activo and t.timezone == timezone_str
        ]
        ahora = datetime.now(ZoneInfo(timezone_str))
        logger.info(
            "Creando repartos para %s soderias en %s (hora local %s)",
            len(tenants),
            timezone_str,
            ahora.strftime("%Y-%m-%d %H:%M"),
        )
        ejecutar_para_tenants("crear_repartos", _crear_repartos_del_dia, tenants)

    return job


# ----------------------------------------------------------------------
# Registro y sincronizacion de jobs
# ----------------------------------------------------------------------


def _sincronizar_jobs() -> None:
    """Registra un cron job por zona horaria de los tenants activos.

    Corre tambien de forma periodica: cuando das de alta una sodería en una
    provincia nueva, sus jobs quedan registrados sin reiniciar la app.
    """
    if _scheduler is None:
        return

    try:
        zonas = {t.timezone for t in listar_tenants() if t.scheduler_activo}
    except Exception:
        logger.exception("No se pudo leer la lista de tenants; se dejan los jobs actuales")
        return

    if not zonas:
        zonas = {settings.DEFAULT_TIMEZONE}

    esperados = {f"repartos:{z}" for z in zonas}

    for zona in zonas:
        job_id = f"repartos:{zona}"
        if _scheduler.get_job(job_id):
            continue
        _scheduler.add_job(
            _job_repartos(zona),
            CronTrigger(
                hour=settings.SCHEDULER_REPARTOS_HOUR,
                minute=settings.SCHEDULER_REPARTOS_MINUTE,
                timezone=ZoneInfo(zona),
            ),
            id=job_id,
            name=f"Crear repartos del dia ({zona})",
            # Si la app estuvo caida a la hora del job, lo corre al volver
            # siempre que no hayan pasado mas de 2 horas.
            misfire_grace_time=7200,
            coalesce=True,
            max_instances=1,
            replace_existing=True,
        )
        logger.info("Job registrado: %s", job_id)

    # Sacar jobs de zonas que ya no tienen tenants. "repartos:arranque" no es
    # una zona, es el job unico de catch-up al iniciar (DateTrigger): si este
    # barrido lo tocara antes de que dispare, nunca llegaria a correr.
    for job in _scheduler.get_jobs():
        if (
            job.id.startswith("repartos:")
            and job.id != "repartos:arranque"
            and job.id not in esperados
        ):
            _scheduler.remove_job(job.id)
            logger.info("Job eliminado: %s", job.id)


def start_scheduler() -> None:
    global _scheduler

    if not settings.SCHEDULER_ENABLED:
        logger.info("Scheduler deshabilitado por configuracion")
        return

    if _scheduler is not None and _scheduler.running:
        return

    _scheduler = AsyncIOScheduler(timezone="UTC")

    # Al arrancar: crear los repartos de hoy si faltan. DateTrigger corre
    # una sola vez y el job se descarta solo. Con el advisory lock, solo uno
    # de los cuatro workers lo ejecuta de verdad.
    _scheduler.add_job(
        lambda: ejecutar_para_tenants("crear_repartos", _crear_repartos_del_dia),
        DateTrigger(run_date=datetime.now(timezone.utc) + timedelta(seconds=10)),
        id="repartos:arranque",
        name="Crear repartos faltantes al arrancar",
        max_instances=1,
        misfire_grace_time=120,
    )

    _scheduler.add_job(
        _sincronizar_jobs,
        IntervalTrigger(minutes=30),
        id="sincronizar_jobs",
        name="Resincronizar jobs con la lista de soderias",
        max_instances=1,
        next_run_time=datetime.now(timezone.utc) + timedelta(seconds=5),
    )

    _scheduler.start()
    logger.info("Scheduler iniciado")


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler detenido")
    _scheduler = None
