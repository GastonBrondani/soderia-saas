from __future__ import annotations
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from app.features.caja.models.caja_empresa import CajaEmpresa
    from app.features.repartos.camiones.models.camion_reparto import CamionReparto
    from app.features.clientes.models.cliente import Cliente
    from app.features.empleados.models.empleado import Empleado
    from app.features.empresas.models.cuenta_bancaria_empresa import CuentaBancariaEmpresa
    from app.features.pedidos.models.pedido import Pedido
    from app.features.repartos.repartos_dia.models.reparto_dia import RepartoDia
    from app.features.inventario.stock.models.stock import Stock

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
#SCHEMA = "soderia"


class Empresa(Base):
    __tablename__ = "empresa"
    #__table_args__ = ({"schema": SCHEMA},)

    #PK
    id_empresa: Mapped[int] = mapped_column(Integer, primary_key=True)

    #Campos
    razon_social: Mapped[str] = mapped_column(String(150), nullable=False)

    #Relaciones
    caja_empresas: Mapped[List["CajaEmpresa"]] = relationship(
        "CajaEmpresa", back_populates="empresa"
    )
    camiones_reparto: Mapped[List["CamionReparto"]] = relationship(
        "CamionReparto", back_populates="empresa"
    )
    clientes: Mapped[List["Cliente"]] = relationship(
        "Cliente", back_populates="empresa"
    )
    empleados: Mapped[List["Empleado"]] = relationship(
        "Empleado", back_populates="empresa"
    )
    cuentas_bancarias: Mapped[List["CuentaBancariaEmpresa"]] = relationship(
        "CuentaBancariaEmpresa", back_populates="empresa"
    )
    pedidos: Mapped[List["Pedido"]] = relationship(
        "Pedido", back_populates="empresa"
    )
    repartos_dias: Mapped[List["RepartoDia"]] = relationship(
        "RepartoDia", back_populates="empresa"
    )
    stocks: Mapped[List["Stock"]] = relationship(
        "Stock", back_populates="empresa"
    )
    combos = relationship("Combo", back_populates="empresa")


    def __repr__(self) -> str:
        return f"<Empresa id={self.id_empresa} razon_social={self.razon_social}>"
