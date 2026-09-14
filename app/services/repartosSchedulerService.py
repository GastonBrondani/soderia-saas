"""
Creacion automatica de repartos del dia, usada por el scheduler.

Movido desde app/core/scheduler.py: el scheduler nuevo (paso 1) espera
encontrar esta logica en un service, no definida inline.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.empresa import Empresa
from app.models.repartoDia import RepartoDia
from app.models.rol import Rol
from app.models.usuario import Usuario
from app.models.usuarioRol import UsuarioRol


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
