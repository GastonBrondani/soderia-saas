from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING,List

if TYPE_CHECKING:
    from .empresa import Empresa
    from .tipoMovimientoCaja import TipoMovimientoCaja
    from .medioPago import MedioPago

from sqlalchemy import (
    Integer,
    String,
    Text,
    Numeric,
    DateTime,    
    ForeignKey,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship


from app.core.database import Base

##SCHEMA = "soderia"


class CajaEmpresa(Base):
    
    __tablename__ = "caja_empresa"
    ##__table_args__ = ({"schema": SCHEMA},)

    #PK 
    id_movimiento: Mapped[int] = mapped_column(Integer, primary_key=True)

    #FKs 
    id_empresa: Mapped[int] = mapped_column(
        ForeignKey("empresa.id_empresa"),
        nullable=False,
    )
    id_tipo_movimiento: Mapped[int] = mapped_column(
        ForeignKey("tipo_movimiento_caja.id_tipo_movimiento"),
        nullable=False,
    )
    id_medio_pago: Mapped[int] = mapped_column(
        ForeignKey("medio_pago.id_medio_pago"),
        nullable=False,
    )

    #Campos
    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=text("now()"),
        nullable=False,
    )
    tipo: Mapped[str] = mapped_column(
        String(15), nullable=False
    )  
    monto: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    
    observacion: Mapped[str | None] = mapped_column(Text)

    #Relaciones.
    empresa: Mapped["Empresa"] = relationship(
        "Empresa", back_populates="caja_empresas"
    )
    tipo_movimiento: Mapped[List["TipoMovimientoCaja"]] = relationship(
        "TipoMovimientoCaja", back_populates="caja_empresa"
    )
    medio_pago: Mapped[List["MedioPago"]] = relationship(
        "MedioPago", back_populates="caja_empresa"
    )

    def __repr__(self) -> str:
        return f"<CajaEmpresa id_mov={self.id_movimiento} tipo={self.tipo} monto={self.monto}>"
