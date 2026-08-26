from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .cajaEmpresa import CajaEmpresa

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

#SCHEMA = "soderia"


class TipoMovimientoCaja(Base):
    __tablename__ = "tipo_movimiento_caja"
    #__table_args__ = ({"schema": SCHEMA},)

    #PK
    id_tipo_movimiento: Mapped[int] = mapped_column(Integer, primary_key=True)

    #Campos
    descripcion: Mapped[str] = mapped_column(String(100), nullable=False)

    #Relaciones
    caja_empresa: Mapped["CajaEmpresa"] = relationship(
        "CajaEmpresa",back_populates="tipo_movimiento"
    )

    def __repr__(self) -> str:
        return f"<TipoMovimientoCaja id={self.id_tipo_movimiento} descripcion={self.descripcion}>"
