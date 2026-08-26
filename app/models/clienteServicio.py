from sqlalchemy import Column, Integer, String, Boolean, Date, DateTime, ForeignKey, Numeric, func
from sqlalchemy.orm import relationship
from app.core.database import Base

class ClienteServicio(Base):
    __tablename__ = "cliente_servicio"

    id_cliente_servicio = Column(Integer, primary_key=True, index=True)
    legajo = Column(Integer, ForeignKey("cliente.legajo", ondelete="CASCADE"), nullable=False, index=True)

    tipo_servicio = Column(String(50), nullable=False)  # "ALQUILER_DISPENSER"
    monto_mensual = Column(Numeric(12, 2), nullable=False)
    fecha_inicio = Column(Date, nullable=False)
    activo = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime, nullable=False, server_default=func.now())

    periodos = relationship("ClienteServicioPeriodo", back_populates="servicio", cascade="all, delete-orphan")
