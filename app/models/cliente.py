from __future__ import annotations
from typing import TYPE_CHECKING, Optional, List

if TYPE_CHECKING:
    from .empresa import Empresa
    from .persona import Persona
    from .clienteCuenta import ClienteCuenta
    from .clienteDiaSemana import ClienteDiaSemana
    from .clienteRepartoDia import ClienteRepartoDia
    from .direccionCliente import DireccionCliente
    from .documentos import Documentos
    from .emailCliente import MailCliente
    from .historico import Historico
    from .pedido import Pedido
    from .productoCliente import ProductoCliente
    from .telefonoCliente import TelefonoCliente
    from .usuario import Usuario
    from .visita import Visita
    from .movimientoEnvaseCliente import MovimientoEnvaseCliente

from sqlalchemy import Integer, Text, ForeignKey, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

#SCHEMA = "soderia"


class Cliente(Base):
    __tablename__ = "cliente"
    #__table_args__ = ({"schema": SCHEMA},)

    #PK
    legajo: Mapped[int] = mapped_column(Integer, primary_key=True)

    #FKs
    id_empresa: Mapped[int] = mapped_column(
        ForeignKey("empresa.id_empresa"),
        nullable=False,
    )
    dni: Mapped[int] = mapped_column(            
        BigInteger,
        ForeignKey("persona.dni",ondelete="CASCADE"),
        nullable=False,
    )

    #Campos
    observacion: Mapped[Optional[str]] = mapped_column(Text)

    #Relaciones 
    empresa: Mapped["Empresa"] = relationship(
        "Empresa",back_populates="clientes"
    )
    
    persona: Mapped["Persona"] = relationship(
        "Persona",back_populates="clientes",passive_deletes=True    
    )
    
    cuentas: Mapped[List["ClienteCuenta"]] = relationship(
        "ClienteCuenta",
        back_populates="cliente",
        cascade="all, delete-orphan",
    )
    direcciones: Mapped[List["DireccionCliente"]] = relationship(
        "DireccionCliente",
        back_populates="cliente",        
        cascade="all, delete-orphan",
    )
    documentos: Mapped[List["Documentos"]] = relationship(
        "Documentos",
        back_populates="cliente",        
        cascade="all, delete-orphan",
    )
    emails: Mapped[List["MailCliente"]] = relationship(
        "MailCliente",
        back_populates="cliente",        
        cascade="all, delete-orphan",
    )
    historicos: Mapped[List["Historico"]] = relationship(
        "Historico",
        back_populates="cliente",        
        cascade="all, delete-orphan",
    )
    pedidos: Mapped[List["Pedido"]] = relationship(
        "Pedido",
        back_populates="cliente",        
        cascade="all, delete-orphan",
    )
    productos: Mapped[List["ProductoCliente"]] = relationship(
        "ProductoCliente",
        back_populates="cliente",        
        cascade="all, delete-orphan",
    )
    telefonos: Mapped[List["TelefonoCliente"]] = relationship(
        "TelefonoCliente",
        back_populates="cliente",        
        cascade="all, delete-orphan",
    )
    usuario: Mapped["Usuario"] = relationship(
        "Usuario",
        back_populates="cliente",        
        cascade="all, delete-orphan",
    )
    dias_semanas: Mapped[List["ClienteDiaSemana"]] = relationship(
        "ClienteDiaSemana",
        back_populates="cliente",        
        cascade="all, delete-orphan",
    )
    repartos_dias: Mapped[List["ClienteRepartoDia"]] = relationship(
        "ClienteRepartoDia",
        back_populates="cliente",        
        cascade="all, delete-orphan",
    )

    visitas: Mapped[List["Visita"]] = relationship(
        "Visita",
        back_populates="cliente",        
        passive_deletes=True,
    )
    movimientos_envase: Mapped[List["MovimientoEnvaseCliente"]] = relationship(
    "MovimientoEnvaseCliente", back_populates="cliente"
    )

    def __repr__(self) -> str:
        return f"<Cliente legajo={self.legajo} dni={self.dni} empresa={self.id_empresa}>"
