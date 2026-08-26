from __future__ import annotations
from typing import List

from fastapi import APIRouter, Body, Depends,  Response, status
from app.core.security import get_current_user
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.combo import ComboCreate, ComboUpdate, ComboOut, ComboDetalleOut
from app.services import comboService
from app.schemas.comboProducto import ComboProductoIn


router = APIRouter(prefix="/combos", tags=["Combo"],dependencies=[Depends(get_current_user)],)


@router.post("/", response_model=ComboOut, status_code=status.HTTP_201_CREATED)
def crear_combo(payload: ComboCreate, db: Session = Depends(get_db)):
    return comboService.crear_combo(db, payload)


@router.get("/", response_model=list[ComboOut])
def listar_combos(
    db: Session = Depends(get_db),
    limit: int = 50,
    offset: int = 0,
    id_empresa: int | None = None,
):
    return comboService.listar_combos(db, id_empresa=id_empresa, limit=limit, offset=offset)


@router.get("/{id_combo}", response_model=ComboDetalleOut)
def obtener_combo_detalle(id_combo: int, db: Session = Depends(get_db)):
    return comboService.obtener_combo_detalle(db, id_combo)


@router.put("/{id_combo}", response_model=ComboOut)
def actualizar_combo(id_combo: int, payload: ComboUpdate, db: Session = Depends(get_db)):
    return comboService.actualizar_combo(db, id_combo, payload)


@router.put("/{id_combo}/productos", response_model=ComboDetalleOut)
def actualizar_productos_combo(
    id_combo: int,
    productos: List[ComboProductoIn] = Body(...),
    db: Session = Depends(get_db),
):
    return comboService.actualizar_composicion(db, id_combo, productos)


@router.delete("/{id_combo}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_combo(id_combo: int, db: Session = Depends(get_db)):
    comboService.eliminar_combo(db, id_combo)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

