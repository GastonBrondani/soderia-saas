from __future__ import annotations
from decimal import Decimal
from typing import TYPE_CHECKING
from sqlalchemy import ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

if TYPE_CHECKING:
    from .listaDePrecios import ListaDePrecios
    from .combo import Combo


class ListaPrecioCombo(Base):
    __tablename__ = "lista_precio_combo"

    id_lista: Mapped[int] = mapped_column(ForeignKey("lista_de_precios.id_lista", ondelete="CASCADE"), primary_key=True)
    id_combo: Mapped[int] = mapped_column(ForeignKey("combo.id_combo", ondelete="CASCADE"), primary_key=True)

    precio: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

    lista: Mapped["ListaDePrecios"] = relationship("ListaDePrecios", back_populates="listas_precios_combos")
    combo: Mapped["Combo"] = relationship("Combo", back_populates="listas_precios")
