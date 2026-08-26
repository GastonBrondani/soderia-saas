from __future__ import annotations
from typing import TYPE_CHECKING, List, Optional
from decimal import Decimal

if TYPE_CHECKING:
    from .empleado import Empleado
    from .repartoDia import RepartoDia
    from .camionReparto import CamionReparto
    from .movimientoStock import MovimientoStock

from sqlalchemy import Integer, String, Numeric, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

#SCHEMA = "soderia"


class Recorrido(Base):
    __tablename__ = "recorrido"
    #__table_args__ = ({"schema": SCHEMA},)

    #PK
    id_recorrido: Mapped[int] = mapped_column(Integer, primary_key=True)

    #FKs
    id_empleado: Mapped[int] = mapped_column(
        ForeignKey("empleado.legajo"), nullable=False
    )
    id_repartodia: Mapped[int] = mapped_column(     
        ForeignKey("reparto_dia.id_repartodia"), nullable=False
    )
    id_camion: Mapped[str] = mapped_column(         
        String(20),
        ForeignKey("camion_reparto.patente"),
        nullable=False,
    )

    #Campos
    dinero_inicial: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2))
    stock_inicial: Mapped[Optional[int]] = mapped_column(Integer)
    observacion: Mapped[Optional[str]] = mapped_column(Text)

    #Relaciones
    empleado: Mapped["Empleado"] = relationship(
        "Empleado", back_populates="recorrido"
    )

    reparto_dia: Mapped["RepartoDia"] = relationship(
        "RepartoDia", back_populates="recorridos"
    )

    camion_reparto: Mapped["CamionReparto"] = relationship(
        "CamionReparto", back_populates="recorridos"
    )
    
    movimientos_stock: Mapped[List["MovimientoStock"]] = relationship(
        "MovimientoStock", back_populates="recorrido"
    )

    def __repr__(self) -> str:
        return (
            f"<Recorrido id={self.id_recorrido} emp={self.id_empleado} "
            f"reparto={self.id_repartodia} camion={self.id_camion}>"
        )
