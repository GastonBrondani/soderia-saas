from sqlalchemy.orm import Session
from app.core.exceptions import NotFound
from app.features.catalogo.listas_precios.models.lista_de_precios import ListaDePrecios
from sqlalchemy import select



from app.features.catalogo.listas_precios.schemas.lista_de_precios import (
    ListaDePreciosCreate, ListaDePreciosUpdate, ListaDePreciosOut
)


def _get_lista_or_404(db: Session, id_lista: int) -> ListaDePrecios:
    lista = db.get(ListaDePrecios, id_lista)
    if not lista:
        raise NotFound("Lista de precios no encontrada")
    return lista

# --- CRUD de ListaDePrecios ---

def crear_lista(db: Session, payload: ListaDePreciosCreate) -> ListaDePreciosOut:
    data = payload.model_dump(exclude_unset=True)
    obj = ListaDePrecios(**data)  # DB setea fecha_creacion=now() y estado=activo si no mandás nada
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

def listar_listas(db: Session, limit: int = 50, offset: int = 0) -> list[ListaDePreciosOut]:
    rows = db.execute(select(ListaDePrecios).offset(offset).limit(limit)).scalars().all()
    return rows

def obtener_lista(db: Session, id_lista: int) -> ListaDePreciosOut:
    return _get_lista_or_404(db, id_lista)

def actualizar_lista(db: Session, id_lista: int, payload: ListaDePreciosUpdate) -> ListaDePreciosOut:
    obj = _get_lista_or_404(db, id_lista)
    updates = payload.model_dump(exclude_unset=True)
    for k, v in updates.items():
        setattr(obj, k, v)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj
