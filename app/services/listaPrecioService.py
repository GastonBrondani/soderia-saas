from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.listaDePrecios import ListaDePrecios
from sqlalchemy import select



from app.schemas.listaDePrecios import (
    ListaDePreciosCreate, ListaDePreciosUpdate, ListaDePreciosOut
)


def _get_lista_or_404(db: Session, id_lista: int) -> ListaDePrecios:
    lista = db.get(ListaDePrecios, id_lista)
    if not lista:
        raise HTTPException(status_code=404, detail="Lista de precios no encontrada")
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

#Utilizado para eliminar ahora y despues mas adelante capaz se habilite 
#from app.models.listaPrecioProducto import ListaPrecioProducto

#def eliminar_lista(db: Session, id_lista: int, cascade: bool = True) -> None:
    # 1) Verifico existencia
#    obj = _get_lista_or_404(db, id_lista)

#    if cascade:
        # 2) Borro primero los precios de esa lista (hijos)
#        db.execute(
#            delete(ListaPrecioProducto).where(
#                ListaPrecioProducto.id_lista == id_lista
#            )
#        )
        # 3) Borro la lista
#        db.execute(
#            delete(ListaDePrecios).where(
#                ListaDePrecios.id_lista == id_lista
#            )
#        )
#        db.commit()
#        return

    # Si no hago cascade, intento borrar directo y capturo FK violation
#    try:
#        db.execute(
#            delete(ListaDePrecios).where(ListaDePrecios.id_lista == id_lista)
#        )
#        db.commit()
#    except IntegrityError:
#        db.rollback()
#        raise HTTPException(
#            status_code=409,
#            detail="No se puede borrar la lista porque tiene precios asociados. "
#                  "Usá ?cascade=true o borrá los precios primero."
#        )
