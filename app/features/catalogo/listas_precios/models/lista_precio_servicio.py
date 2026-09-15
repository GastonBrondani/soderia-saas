from __future__ import annotations
from decimal import Decimal
from typing import TYPE_CHECKING
from sqlalchemy import ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
if TYPE_CHECKING:
    from app.features.catalogo.listas_precios.models.lista_de_precios import ListaDePrecios
    from app.features.catalogo.servicios.models.cliente_servicio import ClienteServicio


class ListaPrecioServicio(Base):
    __tablename__ = "lista_precio_servicio"

    # PK Compuesta: Lista + ClienteServicio (Instancia específica)
    id_lista: Mapped[int] = mapped_column(
        ForeignKey("lista_de_precios.id_lista", ondelete="CASCADE"), primary_key=True
    )
    id_cliente_servicio: Mapped[int] = mapped_column(
        ForeignKey("cliente_servicio.id_cliente_servicio", ondelete="CASCADE"),
        primary_key=True,
    )

    precio: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

    lista: Mapped["ListaDePrecios"] = relationship(
        "ListaDePrecios", back_populates="listas_precios_servicios"
    )
    cliente_servicio: Mapped["ClienteServicio"] = relationship("ClienteServicio")

    def __repr__(self) -> str:
        return f"<ListaPrecioServicio lista={self.id_lista} servicio={self.id_cliente_servicio} precio={self.precio}>"
