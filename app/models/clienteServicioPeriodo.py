from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, Numeric, func
from sqlalchemy.orm import relationship
from app.core.database import Base

class ClienteServicioPeriodo(Base):
    __tablename__ = "cliente_servicio_periodo"

    id_periodo = Column(Integer, primary_key=True, index=True)
    id_cliente_servicio = Column(Integer, ForeignKey("cliente_servicio.id_cliente_servicio", ondelete="CASCADE"), nullable=False, index=True)

    periodo = Column(Date, nullable=False)  # 1er día del mes
    monto = Column(Numeric(12, 2), nullable=False)
    monto_pendiente = Column(Numeric(10, 2), nullable=False)
    estado = Column(String(20), nullable=False, default="PENDIENTE")  # PENDIENTE/PAGADO/VENCIDO
    fecha_vencimiento = Column(Date, nullable=False)
    fecha_pago = Column(Date, nullable=True)
    

    created_at = Column(DateTime, nullable=False, server_default=func.now())

    servicio = relationship("ClienteServicio", back_populates="periodos")
