from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.cliente import Cliente

#Funcion usada para verificar si el cliente existe en la base de datos
#y evitar repetir el mismo codigo en varios routers
def get_cliente_or_404_dep(legajo: int, db: Session = Depends(get_db)) -> Cliente:
    obj = db.get(Cliente, legajo)
    if not obj:
        raise HTTPException(status_code=404, detail="Cliente no encontrado.")
    return obj

