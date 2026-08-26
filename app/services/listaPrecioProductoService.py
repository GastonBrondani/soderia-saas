from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from fastapi import HTTPException

from app.models.listaDePrecios import ListaDePrecios
from app.models.listaPrecioProducto import ListaPrecioProducto
from app.models.producto import Producto
from app.schemas.listaPrecioProducto import LPPUpsert, LPPOut, LPPBasicOut
from app.schemas.producto import ProductoConPrecioOut


def _get_lista_or_404(db: Session, id_lista: int) -> ListaDePrecios:
    lista = db.get(ListaDePrecios, id_lista)
    if not lista:
        raise HTTPException(status_code=404, detail="Lista de precios no encontrada")
    return lista


def listar_precios_de_lista(db: Session, id_lista: int, include_producto: bool) -> List[LPPBasicOut]:
    _get_lista_or_404(db, id_lista)

    if include_producto:
        stmt = (
            select(
                ListaPrecioProducto.id_lista,
                ListaPrecioProducto.id_producto,
                ListaPrecioProducto.precio,
                Producto.nombre.label("nombre_producto"),
            )
            .join(Producto, Producto.id_producto == ListaPrecioProducto.id_producto)
            .where(ListaPrecioProducto.id_lista == id_lista)
            .order_by(Producto.nombre.asc())
        )
        rows = db.execute(stmt).all()
        return [LPPBasicOut(id_lista=r.id_lista, id_producto=r.id_producto, precio=r.precio) for r in rows]
    else:
        stmt = (
            select(ListaPrecioProducto)
            .where(ListaPrecioProducto.id_lista == id_lista)
            .order_by(ListaPrecioProducto.id_producto.asc())
        )
        return db.execute(stmt).scalars().all()


def upsert_precio(db: Session, id_lista: int, payload: LPPUpsert) -> LPPOut:
    _get_lista_or_404(db, id_lista)

    if payload.id_lista != id_lista:
        raise HTTPException(status_code=400, detail="Path y body no coinciden (id_lista).")

    stmt = insert(ListaPrecioProducto).values(
        id_lista=id_lista, id_producto=payload.id_producto, precio=payload.precio
    ).on_conflict_do_update(
        index_elements=[ListaPrecioProducto.id_lista, ListaPrecioProducto.id_producto],
        set_={"precio": payload.precio},
    )

    # transacción/commit en el service
    db.execute(stmt)
    db.commit()

    out = db.execute(
        select(ListaPrecioProducto).where(
            (ListaPrecioProducto.id_lista == id_lista) &
            (ListaPrecioProducto.id_producto == payload.id_producto)
        )
    ).scalars().first()

    return out


def upsert_precios_bulk(db: Session, id_lista: int, items: List[LPPUpsert]) -> List[LPPOut]:
    _get_lista_or_404(db, id_lista)
    if not items:
        return []

    if any(it.id_lista != id_lista for it in items):
        raise HTTPException(status_code=400, detail="Todos los items deben usar el mismo id_lista del path.")

    values = [{"id_lista": it.id_lista, "id_producto": it.id_producto, "precio": it.precio} for it in items]

    
    insert_stmt = insert(ListaPrecioProducto).values(values)

    upsert_stmt = insert_stmt.on_conflict_do_update(
    index_elements=[ListaPrecioProducto.id_lista, ListaPrecioProducto.id_producto],
    set_={"precio": insert_stmt.excluded.precio},)


    db.execute(upsert_stmt)
    db.commit()

    ids = [it.id_producto for it in items]
    rows = db.execute(
        select(ListaPrecioProducto).where(
            (ListaPrecioProducto.id_lista == id_lista) &
            (ListaPrecioProducto.id_producto.in_(ids))
        ).order_by(ListaPrecioProducto.id_producto.asc())
    ).scalars().all()
    return rows

def listar_productos_con_precio_por_lista(
    db: Session,
    id_lista: int,
) -> List[ProductoConPrecioOut]:
    # Verifico que la lista exista
    _get_lista_or_404(db, id_lista)

    # INNER JOIN Producto + ListaPrecioProducto filtrando por lista
    stmt = (
        select(
            Producto.id_producto,
            Producto.nombre,
            Producto.estado,
            Producto.litros,
            Producto.tipo_dispenser,
            Producto.observacion,
            ListaPrecioProducto.precio,
        )
        .join(ListaPrecioProducto, ListaPrecioProducto.id_producto == Producto.id_producto)
        .where(ListaPrecioProducto.id_lista == id_lista)
        .order_by(Producto.nombre.asc())
    )

    rows = db.execute(stmt).all()

    # Mapeo cada fila al schema de salida
    return [
        ProductoConPrecioOut(
            id_producto=row.id_producto,
            nombre=row.nombre,
            estado=row.estado,
            litros=row.litros,
            tipo_dispenser=row.tipo_dispenser,
            observacion=row.observacion,
            precio=row.precio,
            id_lista=id_lista,
        )
        for row in rows
    ]
