from __future__ import annotations
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .empresa import Empresa

from sqlalchemy import Integer, String, Boolean, ForeignKey, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

#SCHEMA = "soderia"


class CuentaBancariaEmpresa(Base):
    __tablename__ = "cuenta_bancaria_empresa"
    #__table_args__ = ({"schema": SCHEMA},)

    #PK
    id_cuenta: Mapped[int] = mapped_column(Integer, primary_key=True)

    #FK
    id_empresa: Mapped[int] = mapped_column(
        ForeignKey("empresa.id_empresa"),
        nullable=False,
    )

    #Campos
    titular_cuenta: Mapped[Optional[str]] = mapped_column(String(150))
    cbu: Mapped[Optional[str]] = mapped_column(String(30))
    alias: Mapped[Optional[str]] = mapped_column(String(50))
    numero_de_cuenta: Mapped[Optional[str]] = mapped_column(String(40))
    tipo_cuenta: Mapped[Optional[str]] = mapped_column(String(40))
    banco: Mapped[Optional[str]] = mapped_column(String(80))
    activa: Mapped[Optional[bool]] = mapped_column(Boolean, server_default=text("true"))

    #Relación
    empresa: Mapped["Empresa"] = relationship(
        "Empresa",back_populates="cuentas_bancarias"
    )

    def __repr__(self) -> str:
        return f"<CuentaBancariaEmpresa id={self.id_cuenta} empresa={self.id_empresa} cbu={self.cbu}>"
