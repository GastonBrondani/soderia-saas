from typing import Optional
from pydantic import BaseModel, ConfigDict

class CamionRepartoBase(BaseModel):
    patente: str
    id_empresa: int = 1             
    activo: bool = True

    model_config = ConfigDict(from_attributes=True)

class CamionRepartoCreate(CamionRepartoBase):
    """Datos necesarios para crear un camión de reparto."""
    pass

class CamionRepartoUpdate(BaseModel):   
    activo: Optional[bool] = None

class CamionRepartoOut(CamionRepartoBase):
    model_config = ConfigDict(from_attributes=True)
    

 