from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.schemas.bootstrap import CatalogoBootstrapOut
from app.services.bootstrapService import catalogo_bootstrap

router = APIRouter(
    prefix="/catalogo",
    tags=["Catálogo"],
    dependencies=[Depends(get_current_user)],
)


# Offline sync: baja en una sola request todo el catálogo (listas de precios con
# sus items, productos, combos y medios de pago).
@router.get("/bootstrap", response_model=CatalogoBootstrapOut)
def bootstrap_catalogo(
    id_empresa: Optional[int] = Query(None, description="Empresa (opcional, filtra combos)"),
    db: Session = Depends(get_db),
):
    return catalogo_bootstrap(db, id_empresa=id_empresa)
