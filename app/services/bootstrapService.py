"""Servicios de bootstrap para la sincronización offline.

Arman en una sola consulta todo lo que la tablet necesita para arrancar el día
sin conexión: el reparto + clientes a visitar, y el catálogo completo.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.cliente import Cliente
from app.models.clienteDiaSemana import ClienteDiaSemana
from app.models.clienteRepartoDia import ClienteRepartoDia
from app.models.repartoDia import RepartoDia
from app.models.producto import Producto
from app.models.combo import Combo
from app.models.comboProducto import ComboProducto
from app.models.listaDePrecios import ListaDePrecios
from app.models.medioPago import MedioPago

from app.services.listaPrecioItemService import listar_items_con_precio

from app.schemas.bootstrap import (
    RepartoBootstrapOut,
    RepartoBootstrap,
    ClienteRepartoBootstrap,
    DireccionBootstrap,
    CuentaBootstrap,
    CatalogoBootstrapOut,
    ListaPreciosBootstrap,
    ProductoBootstrap,
    ComboBootstrap,
    ComboProductoBootstrap,
)
from app.schemas.medioPago import MedioPagoOut


def reparto_bootstrap(
    db: Session,
    *,
    fecha: date,
    id_empresa: Optional[int] = None,
) -> RepartoBootstrapOut:
    """Devuelve el reparto del día + los clientes agendados para esa fecha.

    Los clientes son los que están agendados para el día de la semana de
    `fecha` (tabla cliente_dia_semana). El estado de la visita sale de
    cliente_reparto_dia si ya se registró algo para ese reparto.
    """
    # date.isoweekday(): 1=Lunes ... 7=Domingo, igual que la tabla dia_semana.
    id_dia = fecha.isoweekday()

    # 1) Reparto del día (puede no existir todavía)
    rep_stmt = select(RepartoDia).where(RepartoDia.fecha == fecha)
    if id_empresa is not None:
        rep_stmt = rep_stmt.where(RepartoDia.id_empresa == id_empresa)
    reparto = db.execute(rep_stmt).scalars().first()

    # 2) Estados de visita ya registrados para ese reparto (por legajo)
    estados: dict[int, ClienteRepartoDia] = {}
    if reparto is not None:
        filas = (
            db.execute(
                select(ClienteRepartoDia).where(
                    ClienteRepartoDia.id_repartodia == reparto.id_repartodia
                )
            )
            .scalars()
            .all()
        )
        estados = {f.legajo: f for f in filas}

    # 3) Clientes agendados para ese día de la semana
    cli_stmt = (
        select(Cliente, ClienteDiaSemana)
        .join(ClienteDiaSemana, ClienteDiaSemana.id_cliente == Cliente.legajo)
        .where(ClienteDiaSemana.id_dia == id_dia)
        .options(
            selectinload(Cliente.persona),
            selectinload(Cliente.telefonos),
            selectinload(Cliente.direcciones),
            selectinload(Cliente.cuentas),
        )
        .order_by(
            ClienteDiaSemana.turno_visita,
            ClienteDiaSemana.orden,
            Cliente.legajo,
        )
    )
    if id_empresa is not None:
        cli_stmt = cli_stmt.where(Cliente.id_empresa == id_empresa)

    clientes_out: list[ClienteRepartoBootstrap] = []
    for cliente, cds in db.execute(cli_stmt).all():
        persona = cliente.persona

        telefono = next(
            (t.nro_telefono for t in cliente.telefonos if t.nro_telefono),
            None,
        )

        direccion = None
        if cliente.direcciones:
            direccion = DireccionBootstrap.model_validate(cliente.direcciones[0])

        cuenta = None
        saldo = None
        deuda = None
        if cliente.cuentas:
            cuenta = CuentaBootstrap.model_validate(cliente.cuentas[0])
            saldo = cuenta.saldo
            deuda = cuenta.deuda

        crd = estados.get(cliente.legajo)

        clientes_out.append(
            ClienteRepartoBootstrap(
                legajo=cliente.legajo,
                nombre=persona.nombre if persona else None,
                apellido=persona.apellido if persona else None,
                telefono=telefono,
                direccion=direccion,
                cuenta=cuenta,
                saldo=saldo,
                deuda=deuda,
                turno=cds.turno_visita,
                orden=cds.orden,
                estado_visita=crd.estado_de_la_visita if crd else None,
            )
        )

    return RepartoBootstrapOut(
        fecha=fecha,
        id_dia=id_dia,
        reparto=RepartoBootstrap.model_validate(reparto) if reparto else None,
        clientes=clientes_out,
    )


def catalogo_bootstrap(
    db: Session,
    *,
    id_empresa: Optional[int] = None,
) -> CatalogoBootstrapOut:
    """Devuelve listas de precios (con sus items), productos, combos y medios de pago."""
    # 1) Listas de precios con sus items (productos + combos + servicios con precio)
    listas = db.execute(select(ListaDePrecios).order_by(ListaDePrecios.id_lista)).scalars().all()
    listas_out = [
        ListaPreciosBootstrap(
            id_lista=lista.id_lista,
            nombre=lista.nombre,
            estado=lista.estado,
            items=listar_items_con_precio(db, id_lista=lista.id_lista),
        )
        for lista in listas
    ]

    # 2) Productos
    productos = db.execute(select(Producto).order_by(Producto.nombre)).scalars().all()
    productos_out = [ProductoBootstrap.model_validate(p) for p in productos]

    # 3) Combos con su composición de productos
    combo_stmt = (
        select(Combo)
        .options(
            selectinload(Combo.combos_productos).selectinload(ComboProducto.producto)
        )
        .order_by(Combo.nombre)
    )
    if id_empresa is not None:
        combo_stmt = combo_stmt.where(Combo.id_empresa == id_empresa)

    combos_out: list[ComboBootstrap] = []
    for combo in db.execute(combo_stmt).scalars().all():
        productos_combo = [
            ComboProductoBootstrap(
                id_producto=cp.id_producto,
                nombre=cp.producto.nombre if cp.producto else None,
                cantidad=cp.cantidad,
            )
            for cp in combo.combos_productos
        ]
        combos_out.append(
            ComboBootstrap(
                id_combo=combo.id_combo,
                nombre=combo.nombre,
                descripcion=combo.descripcion,
                estado=combo.estado,
                productos=productos_combo,
            )
        )

    # 4) Medios de pago
    medios = db.execute(select(MedioPago).order_by(MedioPago.nombre)).scalars().all()
    medios_out = [MedioPagoOut.model_validate(m) for m in medios]

    return CatalogoBootstrapOut(
        listas_precios=listas_out,
        productos=productos_out,
        combos=combos_out,
        medios_pago=medios_out,
    )
