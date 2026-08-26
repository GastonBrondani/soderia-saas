# app/services/clienteRepartoDiaService.py
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.clienteRepartoDia import ClienteRepartoDia


#from app.schemas.clienteRepartoDia import (ClienteRepartoDiaCreate,ClienteRepartoDiaUpdate,)


class ClienteRepartoDiaService:

    @staticmethod
    def upsert_desde_pedido(db:Session,id_repartodia:int,legajo:int,monto_abonado:Decimal,observacion: Optional[str]= None,bidones_entregado: Optional[str]=None)->ClienteRepartoDia:
        """
        Upsert de ClienteRepartoDia a partir de un pedido confirmado.

        - Si existe (id_repartodia, legajo), bloquea la fila y:
            * suma `monto_abonado`,
            * acumula `bidones_entregado` (si viene),
            * concatena `observacion` (si viene).
        - Si no existe, crea el registro con los datos provistos.   
        """
        
        #normalizar a decimal
        monto_abonado = Decimal("0.00") if monto_abonado is None else Decimal(monto_abonado)

        # Lock por (id_repartodia, legajo) para evitar duplicados en concurrencia
        crd =db.execute(select(ClienteRepartoDia)
                        .where(
                            ClienteRepartoDia.id_repartodia == id_repartodia,
                            ClienteRepartoDia.legajo == legajo,
                        )
                        .with_for_update()
                        ).scalar_one_or_none()
        
        if crd:
            crd.monto_abonado =(crd.monto_abonado or Decimal("0.00")) + monto_abonado
            if bidones_entregado is not None:
                crd.bidones_entregado = (crd.bidones_entregado or 0) + int(bidones_entregado)
            if observacion:
                prev = (crd.observacion or "").strip()
                obs = observacion.strip()
                crd.observacion = f"{prev} | {obs}" if prev else obs
            return crd
        
        crd=ClienteRepartoDia(
            id_repartodia=id_repartodia,
            legajo=legajo,
            monto_abonado=monto_abonado,
            bidones_entregado=int(bidones_entregado or 0),
            observacion=(observacion or "").strip() or None,
            )
        
        db.add(crd)
        return crd


    
