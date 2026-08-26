from sqlalchemy.orm import Session
from app.models.recorrido import Recorrido
from app.schemas.recorrido import RecorridoCreate
from app.services.stockService import StockService, TipoMovimiento

class RecorridoService:
    @staticmethod
    def abrir_recorrido(db: Session, payload: RecorridoCreate) -> Recorrido:
        # 1) Crear el recorrido
        rec = Recorrido(
            id_empleado=payload.id_empleado,
            id_repartodia=payload.id_repartodia,
            id_camion=payload.id_camion,
            dinero_inicial=payload.dinero_inicial or 0,
            stock_inicial=sum(i.cantidad for i in payload.detalle_stock_inicial),
            observacion=payload.observacion,
        )
        db.add(rec)
        db.flush()  # necesito id_recorrido para los movimientos

        # 2) Por cada ítem, egreso de stock usando TU StockService
        #    Nota: delta negativo para egreso.
        try:
            for item in payload.detalle_stock_inicial:
                StockService.ajustar_stock(
                    db,
                    id_producto=item.id_producto,
                    id_empresa=1,      # viene en el payload
                    delta=-item.cantidad,               # EGRESO => negativo
                    tipo=TipoMovimiento.egreso,
                    observacion="Carga inicial de recorrido",
                    id_recorrido=rec.id_recorrido,
                )
            # si todo ok, el último ajustar_stock ya hizo commit,
            # pero por claridad cerramos refrescando el recorrido:
            db.refresh(rec)
            return rec

        except Exception:
            # si algo falla en medio, que no quede el recorrido “abierto” sin stock movido
            db.rollback()
            raise
