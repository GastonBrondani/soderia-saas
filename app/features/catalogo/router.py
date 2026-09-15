from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.features.sincronizacion.schemas import CatalogoBootstrapOut
from app.features.sincronizacion.service import catalogo_bootstrap

router = APIRouter(
    prefix="/catalogo",
    tags=["Catálogo"],
    dependencies=[Depends(get_current_user)],
)


# Offline sync: baja en una sola request todo el catálogo (listas de precios con
# sus items, productos, combos y medios de pago).
@router.get("/bootstrap", response_model=CatalogoBootstrapOut)
def bootstrap_catalogo(
    db: Session = Depends(get_db),
):
    return catalogo_bootstrap(db)
