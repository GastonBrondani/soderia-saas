from fastapi import APIRouter, Depends, HTTPException, Query
from app.core.security import get_current_user
from datetime import date, datetime, timedelta, time
from sqlalchemy.orm import Session
from sqlalchemy import select, delete
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.api.deps import get_cliente_or_404_dep  
from app.core.database import get_db
from app.models.clienteDiaSemana import ClienteDiaSemana
from app.models.diaSemana import DiaSemana
from app.models.cliente import Cliente
from app.models.persona import Persona
from app.models.visita import Visita
from sqlalchemy import  func
from sqlalchemy.sql import over


from sqlalchemy.dialects.postgresql import insert as pg_insert
from app.models.direccionCliente import DireccionCliente
from app.models.telefonoCliente import TelefonoCliente
from app.models.clienteCuenta import ClienteCuenta
from app.schemas.clienteDiaSemana import ClienteDiaVisitaOut, ClienteAgendaConDatosItem, AgendaConDatosOut





router = APIRouter(prefix="/clientes", tags=["Cliente - días de visita"],dependencies=[Depends(get_current_user)],)

# ---- Schemas específicos del router (payload/response del endpoint) ----
class ClienteDiaVisitaIn(BaseModel):
    id_dia: int
    turno_visita: Optional[str] = None  # "mañana", "tarde", etc.

class ClienteDiasVisitaUpsert(BaseModel):
    dias: List[ClienteDiaVisitaIn]

class ClienteDiaVisitaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id_dia: int
    nombre_dia: str
    turno_visita: Optional[str] = None

   

# ===== Schemas de respuesta =====
class ClientePorDiaItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    legajo: int
    dni: Optional[int] = None
    nombre: Optional[str] = None
    apellido: Optional[str] = None
    turno_visita: Optional[str] = None
    estado_visita: Optional[str] = None

class ClientesPorDiaOut(BaseModel):
    fecha: date
    id_dia: int
    nombre_dia: str
    clientes: List[ClientePorDiaItem]

class ClientesPorDiaSinFechaOut(BaseModel):
    id_dia: int
    nombre_dia: str
    clientes: List[ClientePorDiaItem]

#Para mejorar la performance
class AgendaRangoDiaOut(BaseModel):
    fecha: date
    id_dia: int
    nombre_dia: str
    clientes: List[ClientePorDiaItem]

class AgendaRangoOut(BaseModel):
    desde: date
    hasta: date
    dias: List[AgendaRangoDiaOut]

#Este router maneja los días de visita de los clientes pasandome una fecha te muestro todos los clientes de ese dia.(Funciona)
@router.get("/agenda/visitas", response_model=ClientesPorDiaOut)
def listar_clientes_por_fecha(
    fecha: date = Query(..., description="YYYY-MM-DD"),
    turno: Optional[str] = Query(None, description="Mañana | Tarde | ..."),
    db: Session = Depends(get_db),
):
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
        .order_by(ClienteDiaSemana.turno_visita,ClienteDiaSemana.orden,Persona.apellido,Persona.nombre,)
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
                estado_visita=r.estado_visita,  # 👈 ya viene siempre (pendiente si no hay visita)
            )
            for r in rows
        ],
    )

@router.get("/agenda/visitas/con-datos", response_model=AgendaConDatosOut)
def listar_clientes_por_fecha_con_datos(
    fecha: date = Query(..., description="YYYY-MM-DD"),
    turno: Optional[str] = Query(None, description="Mañana | Tarde | ..."),
    db: Session = Depends(get_db),
):
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

@router.get("/agenda/visitas/rango", response_model=AgendaRangoOut)
def listar_clientes_por_rango(
    desde: date = Query(..., description="YYYY-MM-DD"),
    hasta: date = Query(..., description="YYYY-MM-DD"),
    turno: Optional[str] = Query(None, description="Mañana | Tarde | ..."),
    db: Session = Depends(get_db),
):
    if hasta < desde:
        raise HTTPException(400, "'hasta' no puede ser anterior a 'desde'.")
    if (hasta - desde).days > 92:
        raise HTTPException(400, "El rango no puede superar los 92 días.")

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

# ---- Helper de validación ----
def _validar_dias_existen(db: Session, ids: List[int]) -> None:
    if not ids:
        return  # permitir limpiar días (lista vacía)
    existentes = {
        row.id_dia
        for row in db.execute(
            select(DiaSemana.id_dia).where(DiaSemana.id_dia.in_(ids))
        ).all()
    }
    faltantes = set(ids) - existentes
    if faltantes:
        raise HTTPException(
            status_code=400,
            detail=f"Días inexistentes: {sorted(faltantes)}"
        )
    
#Trae los dias de visita del cliente por los id del dia (Funciona)
@router.get("/agenda/visitas/dia/{id_dia}", response_model=ClientesPorDiaSinFechaOut)
def listar_clientes_por_id_dia(
    id_dia: int,
    turno: Optional[str] = Query(None),
    fecha: Optional[date] = Query(None, description="YYYY-MM-DD (opcional para estado_visita)"),
    db: Session = Depends(get_db),
):
    # Validación de rango
    if not (1 <= id_dia <= 7):
        raise HTTPException(status_code=400, detail="id_dia debe estar entre 1 y 7 (Lunes=1, Domingo=7)")

    # Consulta base (misma forma que tu endpoint por fecha)
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
        raise HTTPException(status_code=404, detail="Día inexistente.")

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
#-----------------------------------


#Muestra el dia de la semana que visita el cliente (Funciona)
@router.get("/{legajo}/dias-visita", response_model=List[ClienteDiaVisitaOut])
def listar_dias_visita_cliente(
    cliente: Cliente = Depends(get_cliente_or_404_dep),
    db: Session = Depends(get_db),
):
    stmt = (
        select(
            ClienteDiaSemana.id_dia,
            DiaSemana.nombre_dia,
            ClienteDiaSemana.turno_visita,
        )
        .select_from(ClienteDiaSemana)
        .join(DiaSemana, DiaSemana.id_dia == ClienteDiaSemana.id_dia)
        .where(ClienteDiaSemana.id_cliente == cliente.legajo)
        .order_by(ClienteDiaSemana.id_dia)
    )
    rows = db.execute(stmt).all()
    return [
        ClienteDiaVisitaOut(
            id_dia=r.id_dia,
            nombre_dia=r.nombre_dia,
            turno_visita=r.turno_visita,
        )
        for r in rows
    ]

""" #Le asignamos un dia de visita al cliente (Funciona)
@router.put("/{legajo}/dias-visita", response_model=List[ClienteDiaVisitaOut])
def upsert_dias_visita_cliente(
    payload: ClienteDiasVisitaUpsert,
    cliente: Cliente = Depends(get_cliente_or_404_dep),
    db: Session = Depends(get_db),
):
    ids = [d.id_dia for d in payload.dias]
    _validar_dias_existen(db, ids)

    # borrar asociaciones actuales del cliente
    db.execute(
        delete(ClienteDiaSemana).where(ClienteDiaSemana.id_cliente == cliente.legajo)
    )

    # insertar nuevas (si hay)
    if payload.dias:
        db.add_all([
            ClienteDiaSemana(
                id_cliente=cliente.legajo,
                id_dia=item.id_dia,
                turno_visita=item.turno_visita,
            )
            for item in payload.dias
        ])

    db.commit()

    # devolver el estado actual (misma consulta que en GET)
    stmt = (
        select(
            ClienteDiaSemana.id_dia,
            DiaSemana.nombre_dia,
            ClienteDiaSemana.turno_visita,
        )
        .select_from(ClienteDiaSemana)
        .join(DiaSemana, DiaSemana.id_dia == ClienteDiaSemana.id_dia)
        .where(ClienteDiaSemana.id_cliente == cliente.legajo)
        .order_by(ClienteDiaSemana.id_dia)
    )
    rows = db.execute(stmt).all()
    return [
        ClienteDiaVisitaOut(
            id_dia=r.id_dia,
            nombre_dia=r.nombre_dia,
            turno_visita=r.turno_visita,
        )
        for r in rows
    ] """

#Elimina un dia de visita del cliente (Funciona)
@router.delete("/{legajo}/dias-visita/{id_dia}", status_code=204)
def eliminar_dia_visita_cliente(
    id_dia: int,
    cliente: Cliente = Depends(get_cliente_or_404_dep),
    db: Session = Depends(get_db),
):
    db.execute(
        delete(ClienteDiaSemana).where(
            ClienteDiaSemana.id_cliente == cliente.legajo,
            ClienteDiaSemana.id_dia == id_dia,
        )
    )
    db.commit()

def _validar_dias_existen(db: Session, ids: list[int]) -> None:
    if not ids:
        return
    rows = db.execute(
        select(DiaSemana.id_dia).where(DiaSemana.id_dia.in_(ids))
    ).scalars().all()
    faltantes = set(ids) - set(rows)
    if faltantes:
        raise HTTPException(
            status_code=400,
            detail=f"Días inexistentes: {sorted(faltantes)}",
        )
    
""" @router.post("/{legajo}/dias-visita",
             response_model=List[ClienteDiaVisitaOut],
             status_code=status.HTTP_201_CREATED)
def agregar_dias_visita_cliente(
    payload: ClienteDiasVisitaUpsert,
    cliente: Cliente = Depends(get_cliente_or_404_dep),
    db: Session = Depends(get_db),
):
    # Validaciones
    ids = [d.id_dia for d in payload.dias]
    _validar_dias_existen(db, ids)

    # Nada que agregar
    if not payload.dias:
        # Devolver estado actual
        stmt = (
            select(
                ClienteDiaSemana.id_dia,
                DiaSemana.nombre_dia,
                ClienteDiaSemana.turno_visita,
            )
            .join(DiaSemana, DiaSemana.id_dia == ClienteDiaSemana.id_dia)
            .where(ClienteDiaSemana.id_cliente == cliente.legajo)
            .order_by(ClienteDiaSemana.id_dia)
        )
        rows = db.execute(stmt).all()
        return [
            ClienteDiaVisitaOut(
                id_dia=r.id_dia,
                nombre_dia=r.nombre_dia,
                turno_visita=r.turno_visita,
            )
            for r in rows
        ]

    # Insertar nuevos sin borrar existentes
    valores = [
        {
            "id_cliente": cliente.legajo,
            "id_dia": item.id_dia,
            "turno_visita": item.turno_visita,
        }
        for item in payload.dias
    ]

    # INSERT ... ON CONFLICT DO NOTHING sobre (id_cliente, id_dia)
    stmt_insert = (
        pg_insert(ClienteDiaSemana)
        .values(valores)
        .on_conflict_do_nothing(
            index_elements=["id_cliente", "id_dia"]
        )
    )
    db.execute(stmt_insert)
    db.commit()

    # Devolver estado actual (mismo SELECT que en tu PUT/GET)
    stmt = (
        select(
            ClienteDiaSemana.id_dia,
            DiaSemana.nombre_dia,
            ClienteDiaSemana.turno_visita,
        )
        .select_from(ClienteDiaSemana)
        .join(DiaSemana, DiaSemana.id_dia == ClienteDiaSemana.id_dia)
        .where(ClienteDiaSemana.id_cliente == cliente.legajo)
        .order_by(ClienteDiaSemana.id_dia)
    )
    rows = db.execute(stmt).all()
    return [
        ClienteDiaVisitaOut(
            id_dia=r.id_dia,
            nombre_dia=r.nombre_dia,
            turno_visita=r.turno_visita,
        )
        for r in rows
    ] """
