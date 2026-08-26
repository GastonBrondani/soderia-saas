from pydantic import BaseModel,ConfigDict
from  typing import Optional

class PersonaBase(BaseModel):
    nombre : str
    apellido : str

class PersonaCreate(PersonaBase):
    dni: int #Pk, es obligatorio para la creacion.

class PersonaUpdate(BaseModel):
    nombre: Optional[str]
    apellido: Optional[str]

class PersonaOut(PersonaBase):
    model_config = ConfigDict(from_attributes=True)
    dni: int
    

