"""
Arma un texto legible ("detalle") para cada evento del histórico, a partir
del campo `datos` (JSONB) que guarda cada evento.

La idea es que el front pueda mostrar una línea descriptiva sin tener que
conocer la estructura interna de `datos` de cada tipo de evento.
"""
from __future__ import annotations

from typing import Any, Mapping, Optional


def _money(valor: Any) -> str:
    """Formatea un monto guardado como string/Decimal -> '$1234.50'."""
    if valor is None:
        return "$0"
    return f"${valor}"


def _periodo(valor: Any) -> str:
    """De un ISO date ('2026-04-01') deja solo el período 'YYYY-MM'."""
    if not valor:
        return ""
    return str(valor)[:7]


def _fecha(valor: Any) -> str:
    """De un ISO datetime/date deja solo 'YYYY-MM-DD'."""
    if not valor:
        return ""
    return str(valor)[:10]


def _detalle_pedido_creado(d: Mapping[str, Any]) -> str:
    return (
        f"Pedido #{d.get('id_pedido')} creado · "
        f"Total {_money(d.get('monto_total'))} · "
        f"Abonado {_money(d.get('monto_abonado'))}"
    )


def _detalle_pedido_confirmado(d: Mapping[str, Any]) -> str:
    partes = [
        f"Pedido #{d.get('id_pedido')} confirmado",
        f"Total {_money(d.get('monto_total'))}",
        f"Abonado {_money(d.get('monto_abonado'))}",
    ]
    envases = d.get("envases") or []
    if envases:
        entregados = sum((e.get("entregados") or 0) for e in envases)
        devueltos = sum((e.get("devueltos") or 0) for e in envases)
        partes.append(f"{entregados} entregados, {devueltos} devueltos")
    return " · ".join(partes)


def _detalle_cliente_actualizado(d: Mapping[str, Any]) -> str:
    secciones = ", ".join(d.keys()) if d else ""
    if secciones:
        return f"Datos actualizados: {secciones}"
    return "Datos del cliente actualizados"


def _detalle_visita(d: Mapping[str, Any]) -> str:
    return f"Visita registrada · estado: {d.get('estado')}"


def _detalle_interes(d: Mapping[str, Any]) -> str:
    return (
        f"Interés {d.get('porcentaje')}% · "
        f"Deuda {_money(d.get('deuda_anterior'))} → {_money(d.get('deuda_nueva'))} "
        f"(+{_money(d.get('interes_aplicado'))})"
    )


def _detalle_pago_deuda(d: Mapping[str, Any]) -> str:
    partes = [f"Pago {_money(d.get('monto'))}"]
    if d.get("deuda_restante") is not None:
        partes.append(f"Deuda restante {_money(d.get('deuda_restante'))}")
    if d.get("saldo_actual") is not None:
        partes.append(f"Saldo {_money(d.get('saldo_actual'))}")
    return " · ".join(partes)


def _detalle_deuda_cancelada(d: Mapping[str, Any]) -> str:
    return f"Deuda saldada · Pago {_money(d.get('monto_pagado'))}"


def _detalle_dispenser_alta(d: Mapping[str, Any]) -> str:
    return (
        f"Alta dispenser {_money(d.get('monto_mensual'))}/mes · "
        f"desde {_fecha(d.get('fecha_inicio'))}"
    )


def _detalle_dispenser_pago(d: Mapping[str, Any]) -> str:
    txt = (
        f"Pago dispenser {_periodo(d.get('periodo'))} · "
        f"{_money(d.get('monto'))}"
    )
    if d.get("usando_saldo"):
        txt += " (con saldo)"
    return txt


def _detalle_dispenser_baja(d: Mapping[str, Any]) -> str:
    return f"Baja dispenser ({_money(d.get('monto_mensual'))}/mes)"


def _detalle_cambio_precio(d: Mapping[str, Any]) -> str:
    return (
        f"Precio dispenser {_money(d.get('monto_anterior'))} → "
        f"{_money(d.get('monto_nuevo'))} · desde {_periodo(d.get('aplicar_desde'))}"
    )


def _detalle_periodo_vencido(d: Mapping[str, Any]) -> str:
    return (
        f"Período {_periodo(d.get('periodo'))} vencido · "
        f"Pendiente {_money(d.get('monto_pendiente'))}"
    )


# Mapa código de evento -> función que arma el detalle.
_FORMATTERS = {
    "PEDIDO_CREADO": _detalle_pedido_creado,
    "PEDIDO_CONFIRMADO": _detalle_pedido_confirmado,
    "CLIENTE_ACTUALIZADO": _detalle_cliente_actualizado,
    "VISITA_REGISTRADA": _detalle_visita,
    "INTERES_APLICADO": _detalle_interes,
    "PAGO_DEUDA_REGISTRADO": _detalle_pago_deuda,
    "DEUDA_CANCELADA_TOTAL": _detalle_deuda_cancelada,
    "DISPENSER_ALTA": _detalle_dispenser_alta,
    "DISPENSER_PAGO": _detalle_dispenser_pago,
    "DISPENSER_DADO_DE_BAJA": _detalle_dispenser_baja,
    "CAMBIO_PRECIO_DISPENSER": _detalle_cambio_precio,
    "PERIODO_VENCIDO": _detalle_periodo_vencido,
}


# Mapa código de evento -> clave dentro de `datos` que representa el monto
# "principal" del evento. Para los pedidos es el total del pedido.
_MONTO_KEYS = {
    "PEDIDO_CREADO": "monto_total",
    "PEDIDO_CONFIRMADO": "monto_total",
    "PAGO_DEUDA_REGISTRADO": "monto",
    "DEUDA_CANCELADA_TOTAL": "monto_pagado",
    "DISPENSER_ALTA": "monto_mensual",
    "DISPENSER_PAGO": "monto",
    "DISPENSER_DADO_DE_BAJA": "monto_mensual",
    "CAMBIO_PRECIO_DISPENSER": "monto_nuevo",
    "INTERES_APLICADO": "interes_aplicado",
    "PERIODO_VENCIDO": "monto_pendiente",
}


def extraer_monto(
    codigo_evento: Optional[str],
    datos: Optional[Mapping[str, Any]],
) -> Optional[float]:
    """
    Devuelve el monto numérico "principal" del evento (p. ej. el total del
    pedido) para que el front lo pueda usar sin parsear el texto del detalle.

    - Si el evento no tiene un monto asociado o `datos` viene vacío -> None.
    - Ante un valor no convertible a número -> None (nunca rompe la respuesta).
    """
    if not datos:
        return None
    clave = _MONTO_KEYS.get(codigo_evento or "")
    if clave is None:
        return None
    valor = datos.get(clave)
    if valor is None:
        return None
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def construir_detalle(
    codigo_evento: Optional[str],
    datos: Optional[Mapping[str, Any]],
    observacion: Optional[str] = None,
) -> Optional[str]:
    """
    Devuelve un texto legible para el evento.

    - Si hay un formateador para el código y `datos`, lo usa.
    - Si falla o no hay datos, cae a `observacion`.
    """
    formatter = _FORMATTERS.get(codigo_evento or "")
    if formatter and datos:
        try:
            return formatter(datos)
        except Exception:
            # Ante datos inesperados nunca rompemos la respuesta del histórico.
            return observacion
    return observacion
