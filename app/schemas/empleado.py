from typing import Optional
from datetime import date
from pydantic import BaseModel,ConfigDict,model_validator
from app.schemas.persona import PersonaCreate,PersonaOut,PersonaUpdate

class EmpleadoBase(BaseModel):
    fecha_ingreso: Optional[date] = None

class EmpleadoCreate(EmpleadoBase):
    # Pasamos el dni para crearlo
    dni: Optional[int] = None
    # o pasamos a la persona completa para crearlo
    persona: Optional[PersonaCreate] = None

    @model_validator(mode="after")
    def _check_persona_or_dni(self):
        if not self.dni and not self.persona:
            raise ValueError("Debes enviar 'dni' de una persona existente o 'persona' completa para crearla.")
        if self.dni and self.persona and self.dni != self.persona.dni:
            raise ValueError("Si envías 'dni' y 'persona', ambos deben coincidir.")
        return self

class EmpleadoUpdate(BaseModel):
    fecha_ingreso: Optional[date] = None    
    persona: Optional[PersonaUpdate] = None

class EmpleadoOut(EmpleadoBase):
    model_config = ConfigDict(from_attributes=True)
    legajo: int
    dni: int
    persona: Optional[PersonaOut] = None
    

