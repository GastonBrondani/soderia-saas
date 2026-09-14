from typing import Optional
from pydantic import BaseModel,field_validator,ConfigDict



class TelefonoClienteBase(BaseModel):
    nro_telefono: Optional[str] = None
    estado: Optional[str] = None
    observacion: Optional[str] = None

    #Esto es para que si viene un string vacio o con espacios, lo convierta a None
    @field_validator("observacion")
    @classmethod
    def trim_obs(cls, v):
        if v is None:
            return v
        v = v.strip()
        return v or None
    
class TelefonoClienteCreate(TelefonoClienteBase):
    pass


class TelefonoClienteUpdate(TelefonoClienteBase):
    id_telefono: Optional[int] = None
    
class TelefonoClienteOut(TelefonoClienteBase):
    model_config = ConfigDict(from_attributes=True)
    id_telefono: int
    legajo: int



