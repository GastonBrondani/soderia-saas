# app/services/productoService.py
from __future__ import annotations

from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.producto import Producto
from app.models.listaPrecioProducto import ListaPrecioProducto
from app.schemas.producto import ProductoWithPreciosOut
from app.schemas.listaPrecioProducto import LPPBasicOut


def listar_productos_con_precios(
    db: Session,
    *,
    limit: int = 50,
    offset: int = 0,
) -> List[ProductoWithPreciosOut]:
    """
    Devuelve productos (con paginación) + sus precios de lista_precio_producto.
    No hace commit; sólo lectura.
    """

    # 1) Traer productos
    productos = (
        db.execute(
            select(Producto)
            .offset(offset)
            .limit(limit)
        )
        .scalars()
        .all()
    )

    if not productos:
        return []

    # 2) Traer todos los precios para esos productos
    ids_productos = [p.id_producto for p in productos]

    precios_rows = (
        db.execute(
            select(ListaPrecioProducto).where(
                ListaPrecioProducto.id_producto.in_(ids_productos)
            )
        )
        .scalars()
        .all()
    )

    # 3) Agrupar precios por id_producto -> List[LPPBasicOut]
    precios_por_producto: dict[int, List[LPPBasicOut]] = {pid: [] for pid in ids_productos}

    for row in precios_rows:
        precios_por_producto[row.id_producto].append(
            LPPBasicOut.model_validate(row, from_attributes=True)
        )

    # 4) Mapear cada Producto -> ProductoWithPreciosOut
    resultado: List[ProductoWithPreciosOut] = []

    for producto in productos:
        prod_schema = ProductoWithPreciosOut.model_validate(
            producto,
            from_attributes=True,
        )
        prod_schema.precios = precios_por_producto.get(producto.id_producto, [])
        resultado.append(prod_schema)

    return resultado
