import io
from datetime import datetime
from decimal import Decimal

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


def money(v: Decimal | float | int) -> str:
    return f"$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def generar_comprobante_pedido_pdf(
    *,
    empresa: str,
    pedido_id: int,
    cliente_nombre: str,
    cliente_legajo: int,
    fecha: datetime,
    items: list[dict],
    total: Decimal,
    monto_abonado: Decimal,
    medio_pago: str,
    estado: str,
    observacion: str | None = None,
) -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)

    width, height = A4
    x0 = 20 * mm
    x1 = width - 20 * mm
    y = height - 25 * mm

    # Encabezado
    c.setFont("Helvetica-Bold", 16)
    c.drawString(x0, y, empresa)

    y -= 8 * mm
    c.setFont("Helvetica", 12)
    c.drawString(x0, y, "COMPROBANTE DE PEDIDO")

    y -= 12 * mm
    c.setFont("Helvetica", 10)
    c.drawString(x0, y, f"Pedido N°: {pedido_id}")
    c.drawRightString(x1, y, f"Fecha: {fecha.strftime('%d/%m/%Y %H:%M')}")

    y -= 8 * mm
    c.line(x0, y, x1, y)

    # Cliente
    y -= 10 * mm
    c.setFont("Helvetica", 10)
    c.drawString(x0, y, f"Cliente: {cliente_nombre}")
    y -= 6 * mm
    c.drawString(x0, y, f"Legajo: {cliente_legajo}")

    # Estado/Pago
    y -= 10 * mm
    c.drawString(x0, y, f"Estado: {estado}")
    y -= 6 * mm
    c.drawString(x0, y, f"Medio de pago: {medio_pago}")
    y -= 6 * mm
    c.drawString(x0, y, f"Monto abonado: {money(monto_abonado)}")

    # Tabla
    y -= 12 * mm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(x0, y, "Detalle del pedido")

    y -= 8 * mm
    c.setFont("Helvetica-Bold", 9)

    col_prod = x0
    col_cant = x0 + 95 * mm
    col_pu = x0 + 115 * mm
    col_sub = x0 + 150 * mm

    c.drawString(col_prod, y, "Producto/Combo")
    c.drawRightString(col_cant + 10 * mm, y, "Cant.")
    c.drawRightString(col_pu + 20 * mm, y, "P.Unit.")
    c.drawRightString(x1, y, "Subtotal")

    y -= 4 * mm
    c.line(x0, y, x1, y)
    y -= 6 * mm
    c.setFont("Helvetica", 9)

    def _new_page():
        nonlocal y
        c.showPage()
        y = height - 25 * mm
        c.setFont("Helvetica-Bold", 12)
        c.drawString(x0, y, f"Pedido N° {pedido_id} — Continuación")
        y -= 10 * mm
        c.setFont("Helvetica", 9)

    for it in items:
        nombre = (it.get("producto") or "Item").strip()
        cant = int(it.get("cantidad") or 0)
        pu = it.get("precio_unitario") or Decimal("0")
        sub = it.get("subtotal") or Decimal("0")

        if y < 35 * mm:
            _new_page()

        c.drawString(col_prod, y, nombre[:60])
        c.drawRightString(col_cant + 10 * mm, y, str(cant))
        c.drawRightString(col_pu + 20 * mm, y, money(pu))
        c.drawRightString(x1, y, money(sub))
        y -= 6 * mm

    # Total
    y -= 4 * mm
    c.line(x0, y, x1, y)
    y -= 10 * mm

    c.setFont("Helvetica-Bold", 11)
    c.drawRightString(x1, y, f"TOTAL: {money(total)}")

    if observacion:
        y -= 12 * mm
        c.setFont("Helvetica-Bold", 10)
        c.drawString(x0, y, "Observación")
        y -= 6 * mm
        c.setFont("Helvetica", 9)
        c.drawString(x0, y, observacion[:120])

    c.setFont("Helvetica", 8)
    c.drawString(x0, 15 * mm, "Documento generado automáticamente por el sistema")

    c.showPage()
    c.save()

    buffer.seek(0)
    return buffer.read()


