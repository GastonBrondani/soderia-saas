# app/services/comboService.py
from __future__ import annotations

from contextlib import contextmanager
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.combo import Combo
from app.models.comboProducto import ComboProducto
from app.models.producto import Producto

from app.schemas.combo import ComboCreate, ComboUpdate, ComboDetalleOut
from app.schemas.comboProducto import ComboProductoDetalleOut, ComboProductoIn, ProductoMiniOut


# ----------------- helpers -----------------

@contextmanager
def _tx(db: Session):
    """
    Maneja transacciones de forma segura con SQLAlchemy 2.0 (autobegin).
    - Si la sesión ya tiene transacción iniciada (por un SELECT previo o por otra capa),
      usamos begin_nested() para no romper.
    - Si no, begin() normal.
    """
    if db.in_transaction():
        with db.begin_nested():
            yield
    else:
        with db.begin():
            yield


def _get_combo_or_404(db: Session, id_combo: int) -> Combo:
    obj = db.get(Combo, id_combo)
    if not obj:
        raise HTTPException(status_code=404, detail="Combo no encontrado")
    return obj


def _validar_sin_duplicados(ids_productos: List[int]) -> None:
    repetidos = sorted({x for x in ids_productos if ids_productos.count(x) > 1})
    if repetidos:
        raise HTTPException(
            status_code=400,
            detail=f"Productos repetidos en la composición del combo: {repetidos}",
        )


def _validar_productos_existentes(db: Session, ids_productos: List[int]) -> None:
    if not ids_productos:
        return

    existentes = db.execute(
        select(Producto.id_producto).where(Producto.id_producto.in_(ids_productos))
    ).scalars().all()

    faltantes = sorted(set(ids_productos) - set(existentes))
    if faltantes:
        raise HTTPException(
            status_code=400,
            detail=f"Productos inexistentes: {faltantes}",
        )


# ----------------- CRUD -----------------

def crear_combo(db: Session, payload: ComboCreate) -> Combo:
    try:
        with _tx(db):
            ids = [p.id_producto for p in payload.productos]
            _validar_sin_duplicados(ids)
            _validar_productos_existentes(db, ids)

            obj = Combo(
                id_empresa=payload.id_empresa,
                nombre=payload.nombre,
                descripcion=payload.descripcion,
                estado=payload.estado,
            )
            db.add(obj)
            db.flush()

            for item in payload.productos:
                db.add(
                    ComboProducto(
                        id_combo=obj.id_combo,
                        id_producto=item.id_producto,
                        cantidad=item.cantidad,
                    )
                )

        db.commit()
        db.refresh(obj)
        return obj

    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creando combo: {e}")


def listar_combos(
    db: Session,
    *,
    id_empresa: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[Combo]:
    stmt = select(Combo).offset(offset).limit(limit)
    if id_empresa is not None:
        stmt = stmt.where(Combo.id_empresa == id_empresa)

    return db.execute(stmt).scalars().all()


def obtener_combo(db: Session, id_combo: int) -> Combo:
    return _get_combo_or_404(db, id_combo)


def obtener_combo_detalle(db: Session, id_combo: int) -> ComboDetalleOut:
    """
    Devuelve:
    - Combo (header)
    - productos: [{id_producto, cantidad, producto:{id_producto,nombre,descuenta_stock}}]
    """
    combo = _get_combo_or_404(db, id_combo)

    rows = db.execute(
        select(ComboProducto, Producto)
        .join(Producto, Producto.id_producto == ComboProducto.id_producto)
        .where(ComboProducto.id_combo == id_combo)
    ).all()

    out = ComboDetalleOut.model_validate(combo, from_attributes=True)
    out.productos = [
        ComboProductoDetalleOut(
            id_producto=cp.id_producto,
            cantidad=cp.cantidad,
            producto=ProductoMiniOut.model_validate(prod, from_attributes=True),
        )
        for (cp, prod) in rows
    ]
    return out


def actualizar_combo(db: Session, id_combo: int, payload: ComboUpdate) -> Combo:
    obj = _get_combo_or_404(db, id_combo)
    updates = payload.model_dump(exclude_unset=True)

    try:
        with _tx(db):
            for k in ("nombre", "descripcion", "estado"):
                if k in updates:
                    setattr(obj, k, updates[k])

            if "productos" in updates and updates["productos"] is not None:
                nuevos = updates["productos"]

                ids = [p["id_producto"] for p in nuevos]
                _validar_sin_duplicados(ids)
                _validar_productos_existentes(db, ids)

                db.query(ComboProducto).filter(
                    ComboProducto.id_combo == id_combo
                ).delete(synchronize_session=False)

                for item in nuevos:
                    db.add(
                        ComboProducto(
                            id_combo=id_combo,
                            id_producto=item["id_producto"],
                            cantidad=item["cantidad"],
                        )
                    )

            db.add(obj)

        db.commit()
        db.refresh(obj)
        return obj

    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error actualizando combo: {e}")


def eliminar_combo(db: Session, id_combo: int) -> None:
    """
    Elimina combo. Por FK ondelete='CASCADE' se borran combo_producto y lista_precio_combo.
    """
    obj = _get_combo_or_404(db, id_combo)
    try:
        db.delete(obj)
        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error eliminando combo: {e}")
    
def actualizar_composicion(
    db: Session,
    id_combo: int,
    productos: List[ComboProductoIn],
):
    _get_combo_or_404(db, id_combo)

    try:
        with _tx(db):
            ids = [p.id_producto for p in productos]
            _validar_sin_duplicados(ids)
            _validar_productos_existentes(db, ids)

            db.query(ComboProducto).filter(
                ComboProducto.id_combo == id_combo
            ).delete(synchronize_session=False)

            for p in productos:
                db.add(
                    ComboProducto(
                        id_combo=id_combo,
                        id_producto=p.id_producto,
                        cantidad=p.cantidad,
                    )
                )

        # 🔥 ESTE COMMIT ES CLAVE
        db.commit()

        return obtener_combo_detalle(db, id_combo)

    except Exception:
        db.rollback()
        raise



