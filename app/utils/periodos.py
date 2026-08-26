from __future__ import annotations
from datetime import date

VENCIMIENTO_DIA = 15  # regla de negocio (cambiable)


def mes_inicio(d: date) -> date:
    """Devuelve el 1er día del mes de la fecha d."""
    return date(d.year, d.month, 1)


def vencimiento_mes(periodo: date) -> date:
    """Recibe un 'periodo' (1er día del mes) y devuelve su vencimiento el mes siguiente."""
    year = periodo.year
    month = periodo.month + 1
    if month > 12:
        month = 1
        year += 1
    return date(year, month, VENCIMIENTO_DIA)


def periodo_yyyymm(periodo: date) -> str:
    """Formatea a 'YYYY-MM' para mostrar en UI."""
    return periodo.strftime("%Y-%m")
