# app/services/agenda_service.py

from datetime import date, datetime, timedelta, time
from typing import List, Optional

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session
from sqlalchemy.sql import over

from app.core.exceptions import AppError, NotFound
from app.features.clientes.models.cliente import Cliente
from app.features.clientes.models.cliente_cuenta import ClienteCuenta
from app.features.clientes.models.direccion_cliente import DireccionCliente
from app.features.clientes.models.telefono_cliente import TelefonoCliente
from app.features.maestros.models.dia_semana import DiaSemana
from app.features.personas.models.persona import Persona
from app.features.repartos.agenda.models.cliente_dia_semana import ClienteDiaSemana
from app.features.repartos.agenda.schemas.cliente_dia_semana import (
    AgendaConDatosOut,
    AgendaRangoDiaOut,
    AgendaRangoOut,
    ClienteAgendaConDatosItem,
    ClientePorDiaItem,
    ClientesPorDiaOut,
    ClientesPorDiaSinFechaOut,
)
from app.features.repartos.visitas.models.visita import Visita


TEMP_ORDEN_MOVIMIENTO = -32768  # válido para smallint


def _obtener_bucket(db: Session, id_dia: int, turno: str) -> list[ClienteDiaSemana]:
    return db.execute(
        select(ClienteDiaSemana)
        .where(
            ClienteDiaSemana.id_dia == id_dia,
            ClienteDiaSemana.turno_visita == turno,
        )
        .order_by(ClienteDiaSemana.orden, ClienteDiaSemana.id_cliente)
        .with_for_update()
    ).scalars().all()


def _reasignar_ordenes_sin_choque(
    db: Session,
    filas: list[ClienteDiaSemana],
) -> None:
    # Paso 1: órdenes temporales negativas
    for i, fila in enumerate(filas, start=1):
        fila.orden = -i
        db.add(fila)
    db.flush()

    # Paso 2: órdenes finales
    for i, fila in enumerate(filas, start=1):
        fila.orden = i
        db.add(fila)
    db.flush()


def insertar_cliente_en_agenda(
    *,
    db: Session,
    id_cliente: int,
    id_dia: int,
    turno: str,
    posicion: str,
    despues_de_legajo: int | None,
):
    if not turno:
        raise AppError("Falta turno")

    registro = db.execute(
        select(ClienteDiaSemana)
        .where(
            ClienteDiaSemana.id_cliente == id_cliente,
            ClienteDiaSemana.id_dia == id_dia,
        )
        .with_for_update()
    ).scalars().first()

    if registro and registro.turno_visita != turno:
        turno_origen = registro.turno_visita

        registro.turno_visita = turno
        registro.orden = TEMP_ORDEN_MOVIMIENTO
        db.add(registro)
        db.flush()

        filas_origen = _obtener_bucket(db, id_dia, turno_origen)
        _reasignar_ordenes_sin_choque(db, filas_origen)

    filas = _obtener_bucket(db, id_dia, turno)

    if registro is None:
        registro = ClienteDiaSemana(
            id_cliente=id_cliente,
            id_dia=id_dia,
            turno_visita=turno,
        )
    else:
        filas = [f for f in filas if f.id_cliente != id_cliente]
        registro.id_dia = id_dia
        registro.turno_visita = turno

    if posicion == "inicio":
        idx = 0
    elif posicion == "final":
        idx = len(filas)
    elif posicion == "despues":
        if not despues_de_legajo:
            raise AppError("Falta despues_de_legajo")

        idx = None
        for i, f in enumerate(filas):
            if f.id_cliente == despues_de_legajo:
                idx = i + 1
                break

        if idx is None:
            raise NotFound("Cliente referencia no encontrado")
    else:
        raise AppError("Posición inválida")

    filas.insert(idx, registro)
    _reasignar_ordenes_sin_choque(db, filas)


def eliminar_dia_visita_cliente(db: Session, legajo: int, id_dia: int) -> None:
    db.execute(
        delete(ClienteDiaSemana).where(
            ClienteDiaSemana.id_cliente == legajo,
            ClienteDiaSemana.id_dia == id_dia,
        )
    )
    db.commit()


# ----------------------------------------------------------------------
# Agenda: reportes de clientes por día / rango
# ----------------------------------------------------------------------


def listar_clientes_por_fecha(
    db: Session, fecha: date, turno: Optional[str] = None
) -> ClientesPorDiaOut:
    id_dia = fecha.isoweekday()

    # Range filter allows the index on visita(fecha) to be used.
    fecha_inicio = datetime.combine(fecha, time.min)
    fecha_fin = fecha_inicio + timedelta(days=1)

    # Subquery: última visita por cliente en esa fecha
    v = (
        select(
            Visita.legajo.label("legajo"),
            Visita.estado.label("estado_visita"),
            over(
                func.row_number(),
                partition_by=Visita.legajo,
                order_by=Visita.fecha.desc(),
            ).label("rn"),
        )
        .where(Visita.fecha >= fecha_inicio, Visita.fecha < fecha_fin)
        .subquery()
    )

    stmt = (
        select(
            Cliente.legajo,
            Cliente.dni,
            Persona.nombre,
            Persona.apellido,
            ClienteDiaSemana.turno_visita,
            ClienteDiaSemana.id_dia,
            DiaSemana.nombre_dia,
            func.coalesce(v.c.estado_visita, "pendiente").label("estado_visita"),
        )
        .select_from(ClienteDiaSemana)
        .join(Cliente, Cliente.legajo == ClienteDiaSemana.id_cliente)
        .outerjoin(Persona, Persona.dni == Cliente.dni)
        .join(DiaSemana, DiaSemana.id_dia == ClienteDiaSemana.id_dia)
        .outerjoin(
            v,
            (v.c.legajo == Cliente.legajo) & (v.c.rn == 1),
        )
        .where(ClienteDiaSemana.id_dia == id_dia)
        .order_by(ClienteDiaSemana.turno_visita, ClienteDiaSemana.orden, Persona.apellido, Persona.nombre)
    )

    if turno:
        stmt = stmt.where(ClienteDiaSemana.turno_visita.ilike(turno))

    rows = db.execute(stmt).all()

    nombre_dia = rows[0].nombre_dia if rows else db.execute(
        select(DiaSemana.nombre_dia).where(DiaSemana.id_dia == id_dia)
    ).scalar_one()

    return ClientesPorDiaOut(
        fecha=fecha,
        id_dia=id_dia,
        nombre_dia=nombre_dia,
        clientes=[
            ClientePorDiaItem(
                legajo=r.legajo,
                dni=r.dni,
                nombre=r.nombre,
                apellido=r.apellido,
                turno_visita=r.turno_visita,
                estado_visita=r.estado_visita,  # ya viene siempre (pendiente si no hay visita)
            )
            for r in rows
        ],
    )


def listar_clientes_por_fecha_con_datos(
    db: Session, fecha: date, turno: Optional[str] = None
) -> AgendaConDatosOut:
    id_dia = fecha.isoweekday()
    fecha_inicio = datetime.combine(fecha, time.min)
    fecha_fin = fecha_inicio + timedelta(days=1)

    # Última visita por cliente en esa fecha (igual que el endpoint original)
    v = (
        select(
            Visita.legajo.label("legajo"),
            Visita.estado.label("estado_visita"),
            over(
                func.row_number(),
                partition_by=Visita.legajo,
                order_by=Visita.fecha.desc(),
            ).label("rn"),
        )
        .where(Visita.fecha >= fecha_inicio, Visita.fecha < fecha_fin)
        .subquery()
    )

    # Primera dirección por cliente (menor id_direccion)
    d = (
        select(
            DireccionCliente.legajo.label("legajo"),
            DireccionCliente.direccion.label("direccion"),
            over(
                func.row_number(),
                partition_by=DireccionCliente.legajo,
                order_by=DireccionCliente.id_direccion.asc(),
            ).label("rn"),
        )
        .subquery()
    )

    # Primer teléfono por cliente (menor id_telefono)
    t = (
        select(
            TelefonoCliente.legajo.label("legajo"),
            TelefonoCliente.nro_telefono.label("telefono"),
            over(
                func.row_number(),
                partition_by=TelefonoCliente.legajo,
                order_by=TelefonoCliente.id_telefono.asc(),
            ).label("rn"),
        )
        .subquery()
    )

    # Primera cuenta por cliente (menor id_cuenta)
    cu = (
        select(
            ClienteCuenta.legajo.label("legajo"),
            ClienteCuenta.id_cuenta.label("id_cuenta"),
            ClienteCuenta.saldo.label("saldo"),
            ClienteCuenta.deuda.label("deuda"),
            over(
                func.row_number(),
                partition_by=ClienteCuenta.legajo,
                order_by=ClienteCuenta.id_cuenta.asc(),
            ).label("rn"),
        )
        .subquery()
    )

    stmt = (
        select(
            Cliente.legajo,
            Cliente.dni,
            Cliente.observacion.label("observacion"),
            Persona.nombre,
            Persona.apellido,
            ClienteDiaSemana.turno_visita,
            ClienteDiaSemana.id_dia,
            DiaSemana.nombre_dia,
            func.coalesce(v.c.estado_visita, "pendiente").label("estado_visita"),
            d.c.direccion,
            t.c.telefono,
            cu.c.id_cuenta,
            cu.c.saldo,
            cu.c.deuda,
        )
        .select_from(ClienteDiaSemana)
        .join(Cliente, Cliente.legajo == ClienteDiaSemana.id_cliente)
        .outerjoin(Persona, Persona.dni == Cliente.dni)
        .join(DiaSemana, DiaSemana.id_dia == ClienteDiaSemana.id_dia)
        .outerjoin(v, (v.c.legajo == Cliente.legajo) & (v.c.rn == 1))
        .outerjoin(d, (d.c.legajo == Cliente.legajo) & (d.c.rn == 1))
        .outerjoin(t, (t.c.legajo == Cliente.legajo) & (t.c.rn == 1))
        .outerjoin(cu, (cu.c.legajo == Cliente.legajo) & (cu.c.rn == 1))
        .where(ClienteDiaSemana.id_dia == id_dia)
        .order_by(
            ClienteDiaSemana.turno_visita,
            ClienteDiaSemana.orden,
            Persona.apellido,
            Persona.nombre,
        )
    )
    if turno:
        stmt = stmt.where(ClienteDiaSemana.turno_visita.ilike(turno))

    rows = db.execute(stmt).all()

    nombre_dia = rows[0].nombre_dia if rows else db.execute(
        select(DiaSemana.nombre_dia).where(DiaSemana.id_dia == id_dia)
    ).scalar_one()

    return AgendaConDatosOut(
        fecha=fecha,
        id_dia=id_dia,
        nombre_dia=nombre_dia,
        clientes=[
            ClienteAgendaConDatosItem(
                legajo=r.legajo,
                dni=r.dni,
                nombre=r.nombre,
                apellido=r.apellido,
                turno_visita=r.turno_visita,
                estado_visita=r.estado_visita,
                direccion=r.direccion,
                telefono=r.telefono,
                id_cuenta=r.id_cuenta,
                saldo=float(r.saldo) if r.saldo is not None else 0.0,
                deuda=float(r.deuda) if r.deuda is not None else 0.0,
                observacion=r.observacion,
            )
            for r in rows
        ],
    )


def listar_clientes_por_rango(
    db: Session, desde: date, hasta: date, turno: Optional[str] = None
) -> AgendaRangoOut:
    if hasta < desde:
        raise AppError("'hasta' no puede ser anterior a 'desde'.")
    if (hasta - desde).days > 92:
        raise AppError("El rango no puede superar los 92 días.")

    # --- Query 1: agenda base (frecuencia de cada cliente por día de semana) ---
    stmt = (
        select(
            ClienteDiaSemana.id_dia,
            Cliente.legajo,
            Cliente.dni,
            Persona.nombre,
            Persona.apellido,
            ClienteDiaSemana.turno_visita,
        )
        .select_from(ClienteDiaSemana)
        .join(Cliente, Cliente.legajo == ClienteDiaSemana.id_cliente)
        .outerjoin(Persona, Persona.dni == Cliente.dni)
        .order_by(
            ClienteDiaSemana.turno_visita,
            ClienteDiaSemana.orden,
            Persona.apellido,
            Persona.nombre,
        )
    )
    if turno:
        stmt = stmt.where(ClienteDiaSemana.turno_visita.ilike(turno))

    schedule_rows = db.execute(stmt).all()

    # Agrupo la frecuencia por día de semana (1=Lunes .. 7=Domingo)
    sched_por_dia: dict[int, list] = {}
    for r in schedule_rows:
        sched_por_dia.setdefault(r.id_dia, []).append(r)

    # Nombres de los días (tabla de 7 filas)
    nombre_por_id = {
        r.id_dia: r.nombre_dia
        for r in db.execute(select(DiaSemana.id_dia, DiaSemana.nombre_dia)).all()
    }

    # --- Query 2: última visita por (cliente, día) dentro del rango ---
    fecha_inicio = datetime.combine(desde, time.min)
    fecha_fin = datetime.combine(hasta, time.min) + timedelta(days=1)

    vsub = (
        select(
            Visita.legajo.label("legajo"),
            func.date(Visita.fecha).label("dia"),
            Visita.estado.label("estado"),
            over(
                func.row_number(),
                partition_by=(Visita.legajo, func.date(Visita.fecha)),
                order_by=Visita.fecha.desc(),
            ).label("rn"),
        )
        .where(Visita.fecha >= fecha_inicio, Visita.fecha < fecha_fin)
        .subquery()
    )
    visita_rows = db.execute(
        select(vsub.c.legajo, vsub.c.dia, vsub.c.estado).where(vsub.c.rn == 1)
    ).all()
    estado_map = {(r.legajo, r.dia): r.estado for r in visita_rows}

    # --- Armado: recorro fecha por fecha y proyecto la frecuencia ---
    dias_out: List[AgendaRangoDiaOut] = []
    cur = desde
    while cur <= hasta:
        id_dia = cur.isoweekday()
        rows = sched_por_dia.get(id_dia, [])
        clientes = [
            ClientePorDiaItem(
                legajo=r.legajo,
                dni=r.dni,
                nombre=r.nombre,
                apellido=r.apellido,
                turno_visita=r.turno_visita,
                estado_visita=estado_map.get((r.legajo, cur), "pendiente"),
            )
            for r in rows
        ]
        dias_out.append(
            AgendaRangoDiaOut(
                fecha=cur,
                id_dia=id_dia,
                nombre_dia=nombre_por_id.get(id_dia, ""),
                clientes=clientes,
            )
        )
        cur += timedelta(days=1)

    return AgendaRangoOut(desde=desde, hasta=hasta, dias=dias_out)


def listar_clientes_por_id_dia(
    db: Session,
    id_dia: int,
    turno: Optional[str] = None,
    fecha: Optional[date] = None,
) -> ClientesPorDiaSinFechaOut:
    # Validación de rango
    if not (1 <= id_dia <= 7):
        raise AppError("id_dia debe estar entre 1 y 7 (Lunes=1, Domingo=7)")

    # Consulta base (misma forma que el endpoint por fecha)
    stmt = (
        select(
            Cliente.legajo,
            Cliente.dni,
            Persona.nombre,
            Persona.apellido,
            ClienteDiaSemana.turno_visita,
            ClienteDiaSemana.id_dia,
            DiaSemana.nombre_dia,
        )
        .select_from(ClienteDiaSemana)
        .join(Cliente, Cliente.legajo == ClienteDiaSemana.id_cliente)
        .outerjoin(Persona, Persona.dni == Cliente.dni)
        .join(DiaSemana, DiaSemana.id_dia == ClienteDiaSemana.id_dia)
        .where(ClienteDiaSemana.id_dia == id_dia)
        .order_by(
            ClienteDiaSemana.turno_visita,
            ClienteDiaSemana.orden,
            Persona.apellido,
            Persona.nombre,
        )
    )

    if turno:
        stmt = stmt.where(ClienteDiaSemana.turno_visita.ilike(turno))

    rows = db.execute(stmt).all()

    # nombre del día (si no hay filas, lo saco de la tabla de días)
    nombre_dia = rows[0].nombre_dia if rows else db.execute(
        select(DiaSemana.nombre_dia).where(DiaSemana.id_dia == id_dia)
    ).scalar_one_or_none()

    if not nombre_dia:
        raise NotFound("Día inexistente.")

    return ClientesPorDiaSinFechaOut(
        id_dia=id_dia,
        nombre_dia=nombre_dia,
        clientes=[
            ClientePorDiaItem(
                legajo=r.legajo,
                dni=r.dni,
                nombre=r.nombre,
                apellido=r.apellido,
                turno_visita=r.turno_visita,
            )
            for r in rows
        ],
    )