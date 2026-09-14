from typing import Optional
from pydantic import BaseModel,field_validator,ConfigDict



class DireccionClienteBase(BaseModel):
    localidad: Optional[str] = None
    direccion: Optional[str] = None
    zona: Optional[str] = None
    entre_calle1: Optional[str] = None
    entre_calle2: Optional[str] = None
    observacion: Optional[str] = None
    tipo: Optional[str] = None
    latitud_longitud: Optional[str] = None


    #Esto es para que si viene un string vacio o con espacios, lo convierta a None
    @field_validator("observacion")
    @classmethod
    def trim_obs(cls, v):
        if v is None:
            return v
        v = v.strip()
        return v or None
    
class DireccionClienteCreate(DireccionClienteBase):
    pass


class DireccionClienteUpdate(DireccionClienteBase):    
    id_direccion: Optional[int] = None

class DireccionClienteOut(DireccionClienteBase):
    model_config = ConfigDict(from_attributes=True)
    id_direccion: int
    legajo: int


