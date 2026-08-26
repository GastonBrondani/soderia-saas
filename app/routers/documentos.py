from fastapi import APIRouter, Depends
from fastapi import HTTPException, status
from app.core.security import get_current_user
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.database import get_db
from app.models.documentos import Documentos
from app.services.comprobantePedidoService import ComprobantePedidoService

router = APIRouter(prefix="/documentos", tags=["Documentos"],dependencies=[Depends(get_current_user)],)


@router.get("/cliente/{legajo}")
def listar_documentos_cliente(
    legajo: int,
    db: Session = Depends(get_db),
):
    docs = db.execute(
        select(Documentos)
        .where(Documentos.legajo == legajo)
        .order_by(Documentos.fecha_carga.desc())
    ).scalars().all()

    return [
        {
            "id_documento": d.id_documento,
            "nombre_archivo": d.nombre_archivo,
            "tipo_archivo": d.tipo_archivo,
            "url": d.url_archivo,
            "fecha": d.fecha_carga,
            "observacion": d.observacion,
        }
        for d in docs
    ]
    
@router.post("/pedidos/{id_pedido}", status_code=status.HTTP_201_CREATED)
def generar_documento_pedido(id_pedido: int, db: Session = Depends(get_db)):
    try:
        doc = ComprobantePedidoService.generar_y_guardar(db, id_pedido=id_pedido)
        return {
            "id_documento": doc.id_documento,
            "nombre_archivo": doc.nombre_archivo,
            "tipo_archivo": doc.tipo_archivo,
            "url": doc.url_archivo,
            "fecha": doc.fecha_carga,
            "observacion": doc.observacion,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando comprobante de pedido: {e}")
