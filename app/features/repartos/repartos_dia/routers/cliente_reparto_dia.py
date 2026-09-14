# app/routers/cliente_reparto_dia.py
from __future__ import annotations

from typing import List, Optional,Literal

from fastapi import APIRouter, Depends, Query, status
from app.core.security import get_current_user
from sqlalchemy.orm import Session

# Ajustá este import según tu proyecto (sé que en tu repo usás core.database)
from app.core.database import get_db

#from app.features.repartos.repartos_dia.schemas.cliente_reparto_dia import (ClienteRepartoDiaCreate,ClienteRepartoDiaUpdate,ClienteRepartoDiaOut,)
#from app.features.repartos.repartos_dia.services.cliente_reparto_dia import ClienteRepartoDiaService

router = APIRouter(prefix="/repartos-dia/{id_repartodia}/clientes", tags=["RepartoDia - Clientes"],dependencies=[Depends(get_current_user)],)


