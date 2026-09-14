from pydantic import BaseModel, ConfigDict

class EmpresaBase(BaseModel):
    razon_social: str

class EmpresaCreate(EmpresaBase):
    pass

class EmpresaRead(EmpresaBase):
    model_config = ConfigDict(from_attributes=True)
    id_empresa: int
    