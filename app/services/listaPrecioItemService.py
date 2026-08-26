from __future__ import annotations

from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.schemas.precioItem import PrecioItemOut, TipoItemPrecio

from app.models.producto import Producto
from app.models.combo import Combo
from app.models.listaPrecioProducto import ListaPrecioProducto
from app.models.listaPrecioCombo import ListaPrecioCombo
from app.models.listaPrecioServicio import ListaPrecioServicio
from app.models.clienteServicio import ClienteServicio
from app.models.cliente import Cliente
from app.models.persona import Persona


def upsert_precio_item(
    db: Session,
    *,
    id_lista: int,
    tipo: TipoItemPrecio,
    id_item: int,
    precio,
) -> PrecioItemOut:
    if tipo == "producto":
        prod = db.get(Producto, id_item)
        if not prod:
            raise HTTPException(status_code=404, detail="Producto no encontrado")

        obj = db.get(
            ListaPrecioProducto, {"id_lista": id_lista, "id_producto": id_item}
        )
        if obj:
            obj.precio = precio
        else:
            obj = ListaPrecioProducto(
                id_lista=id_lista, id_producto=id_item, precio=precio
            )
            db.add(obj)

        db.commit()
        db.refresh(obj)
        return PrecioItemOut(
            tipo="producto",
            id_lista=id_lista,
            id_item=id_item,
            precio=obj.precio,
            nombre=prod.nombre,
        )

    if tipo == "combo":
        combo = db.get(Combo, id_item)
        if not combo:
            raise HTTPException(status_code=404, detail="Combo no encontrado")

        obj = db.get(ListaPrecioCombo, {"id_lista": id_lista, "id_combo": id_item})
        if obj:
            obj.precio = precio
        else:
            obj = ListaPrecioCombo(id_lista=id_lista, id_combo=id_item, precio=precio)
            db.add(obj)

        db.commit()
        db.refresh(obj)
        return PrecioItemOut(
            tipo="combo",
            id_lista=id_lista,
            id_item=id_item,
            precio=obj.precio,
            nombre=combo.nombre,
        )

    raise HTTPException(status_code=400, detail="tipo inválido (producto|combo)")


def listar_items_con_precio(db: Session, *, id_lista: int) -> List[PrecioItemOut]:
    # productos con precio
    prod_rows = db.execute(
        select(Producto.id_producto, Producto.nombre, ListaPrecioProducto.precio)
        .join(
            ListaPrecioProducto, ListaPrecioProducto.id_producto == Producto.id_producto
        )
        .where(ListaPrecioProducto.id_lista == id_lista)
    ).all()

    # combos con precio
    combo_rows = db.execute(
        select(Combo.id_combo, Combo.nombre, Combo.estado, ListaPrecioCombo.precio)
        .join(ListaPrecioCombo, ListaPrecioCombo.id_combo == Combo.id_combo)
        .where(ListaPrecioCombo.id_lista == id_lista)
    ).all()

    # servicios con precio (y datos de cliente)
    servicio_rows = db.execute(
        select(
            ListaPrecioServicio.id_cliente_servicio,
            ListaPrecioServicio.precio,
            ClienteServicio.tipo_servicio,
            Persona.nombre,
            Persona.apellido,
        )
        .join(
            ClienteServicio,
            ClienteServicio.id_cliente_servicio
            == ListaPrecioServicio.id_cliente_servicio,
        )
        .join(Cliente, Cliente.legajo == ClienteServicio.legajo)
        .join(Persona, Persona.dni == Cliente.dni)
        .where(ListaPrecioServicio.id_lista == id_lista)
    ).all()

    out: List[PrecioItemOut] = []
    for id_producto, nombre, precio in prod_rows:
        out.append(
            PrecioItemOut(
                tipo="producto",
                id_lista=id_lista,
                id_item=id_producto,
                precio=precio,
                nombre=nombre,
            )
        )

    for id_combo, nombre, estado, precio in combo_rows:
        out.append(
            PrecioItemOut(
                tipo="combo",
                id_lista=id_lista,
                id_item=id_combo,
                precio=precio,
                nombre=nombre,
                estado=estado,
            )
        )

    for id_servicio, precio, tipo_svc, nombre_cli, apellido_cli in servicio_rows:
        nombre_mostrar = f"{tipo_svc} - {nombre_cli} {apellido_cli}"
        out.append(
            PrecioItemOut(
                tipo="servicio",
                id_lista=id_lista,
                id_item=id_servicio,
                precio=precio,
                nombre=nombre_mostrar,
                estado=True,  # Asumimos activo si tiene precio y existe el contrato
            )
        )

    # orden opcional para UI
    out.sort(key=lambda x: (x.tipo, x.nombre or ""))
    return out
