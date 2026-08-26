from __future__ import annotations

from typing import List

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.listaPrecioCombo import ListaPrecioCombo
from app.models.combo import Combo

from app.schemas.listaPrecioCombo import LPCOut, LPCUpsert, LPCBasicOut
from app.schemas.combo import ComboConPrecioOut


def listar_precios_de_lista_combo(
    db: Session,
    id_lista: int,
    include_combo: bool = True,
) -> List[LPCBasicOut]:
    """
    Devuelve los precios de combos cargados en una lista.
    Si include_combo=True agrega combo_nombre (útil para UI).
    """
    if include_combo:
        rows = db.execute(
            select(ListaPrecioCombo, Combo)
            .join(Combo, Combo.id_combo == ListaPrecioCombo.id_combo)
            .where(ListaPrecioCombo.id_lista == id_lista)
            .order_by(Combo.nombre.asc())
        ).all()

        return [
            LPCBasicOut(
                id_lista=lpc.id_lista,
                id_combo=lpc.id_combo,
                precio=lpc.precio,
                combo_nombre=combo.nombre,
            )
            for (lpc, combo) in rows
        ]

    # sin join (solo ids + precio)
    rows = db.execute(
        select(ListaPrecioCombo)
        .where(ListaPrecioCombo.id_lista == id_lista)
        .order_by(ListaPrecioCombo.id_combo.asc())
    ).scalars().all()

    return [
        LPCBasicOut(
            id_lista=r.id_lista,
            id_combo=r.id_combo,
            precio=r.precio,
            combo_nombre=None,
        )
        for r in rows
    ]


def upsert_precio_combo(db: Session, id_lista: int, payload: LPCUpsert) -> LPCOut:
    """
    Inserta o actualiza el precio de un combo dentro de una lista.
    """
    if payload.id_combo is None:
        raise HTTPException(status_code=400, detail="Falta id_combo")
    if payload.id_lista is None:
        payload.id_lista = id_lista

    # Validar combo existe (si querés validar también que sea de la misma empresa, se puede)
    combo = db.get(Combo, payload.id_combo)
    if not combo:
        raise HTTPException(status_code=404, detail="Combo no encontrado")

    # Buscar si existe la fila (PK compuesta id_lista + id_combo)
    obj = db.get(ListaPrecioCombo, {"id_lista": id_lista, "id_combo": payload.id_combo})

    if obj:
        obj.precio = payload.precio
    else:
        obj = ListaPrecioCombo(
            id_lista=id_lista,
            id_combo=payload.id_combo,
            precio=payload.precio,
        )
        db.add(obj)

    db.commit()
    db.refresh(obj)
    return LPCOut.model_validate(obj, from_attributes=True)


def listar_combos_con_precio_por_lista(db: Session, id_lista: int) -> List[ComboConPrecioOut]:
    """
    Devuelve combos que tienen precio cargado en la lista indicada.
    """
    rows = db.execute(
        select(Combo.id_combo, Combo.nombre, ListaPrecioCombo.precio)
        .join(ListaPrecioCombo, ListaPrecioCombo.id_combo == Combo.id_combo)
        .where(ListaPrecioCombo.id_lista == id_lista)
        .order_by(Combo.nombre.asc())
    ).all()

    return [
        ComboConPrecioOut(
            id_combo=r.id_combo,
            nombre=r.nombre,
            precio=r.precio,
        )
        for r in rows
    ]
