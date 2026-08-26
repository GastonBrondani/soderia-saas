from typing import List
from sqlalchemy import select
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.listaDePrecios import ListaDePrecios
from app.models.listaPrecioServicio import ListaPrecioServicio
from app.models.clienteServicio import ClienteServicio
from app.schemas.listaPrecioServicio import LPSUpsert, LPSOut, LPSBasicOut


def upsert_precio_servicio(db: Session, id_lista: int, payload: LPSUpsert) -> LPSOut:
    # 1. Verificar Lista
    lista = db.get(ListaDePrecios, id_lista)
    if not lista:
        raise HTTPException(status_code=404, detail="Lista de precios no encontrada")

    # 2. Verificar Servicio (ClienteServicio)
    if payload.id_cliente_servicio is None:
        raise HTTPException(status_code=400, detail="Falta id_cliente_servicio")

    servicio = db.get(ClienteServicio, payload.id_cliente_servicio)
    if not servicio:
        raise HTTPException(status_code=404, detail="Servicio (contrato) no encontrado")

    # 3. Upsert
    item = db.get(ListaPrecioServicio, (id_lista, payload.id_cliente_servicio))
    if item:
        item.precio = payload.precio
    else:
        item = ListaPrecioServicio(
            id_lista=id_lista,
            id_cliente_servicio=payload.id_cliente_servicio,
            precio=payload.precio,
        )
        db.add(item)

    db.commit()
    db.refresh(item)
    return LPSOut.model_validate(item)


def listar_precios_de_lista_servicio(
    db: Session, id_lista: int, include_tipo: bool = True
) -> List[LPSBasicOut]:
    """
    Lista todos los precios de servicios configurados para esta lista.
    """
    stmt = select(ListaPrecioServicio).where(ListaPrecioServicio.id_lista == id_lista)
    if include_tipo:
        pass
        # Si quisiéramos traer info extra del servicio, haríamos join.
        # Por ahora ListaPrecioServicio no tiene el "tipo" como string,
        # sino que hay que ir a buscarlo a ClienteServicio
        # stmt = stmt.join(ClienteServicio).add_columns(ClienteServicio.tipo_servicio) ...

    rows = db.execute(stmt).scalars().all()

    # Mapeo manual si necesitamos inyectar datos extra
    results = []
    for r in rows:
        out = LPSBasicOut.model_validate(r)
        # Si incluimos tipo, podemos hacer un fetch lazy o join arriba
        if include_tipo:
            # Pequeño hack lazy para demo, idealmente hacer join en la query
            # Pero como ClienteServicio ya está en la session por FK relation, puede ser rápido
            if r.cliente_servicio:
                out.servicio_tipo = r.cliente_servicio.tipo_servicio
        results.append(out)

    return results
