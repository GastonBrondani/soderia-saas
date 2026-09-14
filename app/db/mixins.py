"""
Mixins reutilizables para los modelos.

Ninguno es obligatorio, pero aplicar TimestampMixin a todas las tablas
nuevas te ahorra dolor: cuando un cliente pregunte "quien cambió el precio
de la bidón de 20 litros el martes", vas a querer tener las fechas.

Fijate que no hay TenantMixin: con una base por sodería, el aislamiento lo
da la conexion, no una columna. Esa es la ventaja principal del modelo que
elegiste. `id_empresa` sigue existiendo donde lo necesites para separar
sucursales o depositos dentro de una misma sodería.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column


class TimestampMixin:
    """Agrega creado_en y actualizado_en, manejados por la base."""

    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class SoftDeleteMixin:
    """Baja logica.

    Ya lo venis haciendo a mano en listas de precios ("soft delete" via
    estado='inactivo'). Esto lo estandariza para el resto.
    """

    eliminado: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false", index=True
    )
    eliminado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    def marcar_eliminado(self) -> None:
        self.eliminado = True
        self.eliminado_en = datetime.now()


class AuditoriaMixin(TimestampMixin):
    """Ademas de las fechas, quien creo y quien modifico."""

    creado_por: Mapped[int | None] = mapped_column(Integer)
    actualizado_por: Mapped[int | None] = mapped_column(Integer)


class DescripcionMixin:
    """Campos que se repiten en las tablas de catalogo."""

    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    observacion: Mapped[str | None] = mapped_column(String(500))
