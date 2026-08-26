from fastapi import APIRouter, Depends, status
from app.core.security import get_current_user
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.empresa import Empresa
from app.schemas.empresa import EmpresaCreate, EmpresaRead

router = APIRouter(prefix="/empresas", tags=["Empresa"],dependencies=[Depends(get_current_user)],)

@router.post("/", response_model=EmpresaRead, status_code=status.HTTP_201_CREATED)
def CrearEmpresa(data: EmpresaCreate, db: Session = Depends(get_db)):
    empresa = Empresa(**data.model_dump())
    db.add(empresa)
    db.commit()
    db.refresh(empresa)
    return empresa  # Pydantic lo transforma según EmpresaRead

@router.get("/", response_model=list[EmpresaRead], status_code=status.HTTP_200_OK)
def ObtenerEmpresas(db: Session = Depends(get_db)):
    empresas = db.query(Empresa).all()
    return empresas