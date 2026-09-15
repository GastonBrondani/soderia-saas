from __future__ import annotations
from typing import TYPE_CHECKING, List, Optional
from decimal import Decimal

if TYPE_CHECKING:
    from app.features.catalogo.listas_precios.models.lista_precio_producto import ListaPrecioProducto
    from app.features.inventario.movimientos.models.movimiento_stock import MovimientoStock
    from app.features.pedidos.models.pedido_producto import PedidoProducto
    from app.features.clientes.models.producto_cliente import ProductoCliente
    from app.features.inventario.stock.models.stock import Stock
    from app.features.catalogo.combos.models.combo_producto import ComboProducto
    from app.features.inventario.envases.models.movimiento_envase_cliente import MovimientoEnvaseCliente
    
from sqlalchemy import Integer, String, Numeric, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
#SCHEMA = "soderia"


class Producto(Base):
    __tablename__ = "producto"
    #__table_args__ = {"schema": SCHEMA}

    #PK
    id_producto: Mapped[int] = mapped_column(Integer, primary_key=True)

    #Campos
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    estado: Mapped[Optional[str]] = mapped_column(String(20))          
    litros: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    tipo_dispenser: Mapped[Optional[str]] = mapped_column(String(50))
    observacion: Mapped[Optional[str]] = mapped_column(Text)
    descuenta_stock: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    es_envase: Mapped[bool] = mapped_column(
    Boolean,
    nullable=False,
    default=False,
    server_default="false",
    )
    #Relaciones
    listas_precios: Mapped[List["ListaPrecioProducto"]] = relationship(
        "ListaPrecioProducto", back_populates="producto"
    )
    movimientos_stock: Mapped[List["MovimientoStock"]] = relationship(
        "MovimientoStock", back_populates="producto"
    )

    pedidos_productos: Mapped[List["PedidoProducto"]] = relationship(
        "PedidoProducto", back_populates="producto"
    )
    productos_cliente: Mapped[List["ProductoCliente"]] = relationship(
        "ProductoCliente", back_populates="producto"
    )
    stocks: Mapped[List["Stock"]] = relationship(
        "Stock", back_populates="producto"
    )
    combos_productos: Mapped[List["ComboProducto"]] = relationship("ComboProducto", back_populates="producto")
    movimientos_envase_cliente: Mapped[List["MovimientoEnvaseCliente"]] = relationship(
    "MovimientoEnvaseCliente", back_populates="producto")
    

    def __repr__(self) -> str:
        return f"<Producto id={self.id_producto} nombre={self.nombre} estado={self.estado}>"
