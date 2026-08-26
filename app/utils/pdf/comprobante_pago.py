import io
from datetime import datetime
from decimal import Decimal

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


def money(v: Decimal | float | int) -> str:
    return f"$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def generar_comprobante_pago_pdf(
    *,
    empresa: str,
    pago_id: int,
    cliente_nombre: str,
    cliente_legajo: int,
    fecha: datetime,
    monto: Decimal,
    medio_pago: str,
    tipo_pago: str,
    deuda_actual: Decimal,
    saldo_actual: Decimal,
    observacion: str | None = None,
) -> bytes:
    # 🔑 CLAVE: usar BytesIO, NUNCA None
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)

    width, height = A4
    y = height - 30 * mm

    c.setFont("Helvetica-Bold", 16)
    c.drawString(20 * mm, y, empresa)

    y -= 8 * mm
    c.setFont("Helvetica", 12)
    c.drawString(20 * mm, y, "COMPROBANTE DE PAGO")

    y -= 12 * mm
    c.setFont("Helvetica", 10)
    c.drawString(20 * mm, y, f"Comprobante N°: {pago_id}")
    c.drawRightString(
        width - 20 * mm,
        y,
        f"Fecha: {fecha.strftime('%d/%m/%Y %H:%M')}",
    )

    y -= 10 * mm
    c.line(20 * mm, y, width - 20 * mm, y)

    y -= 10 * mm
    c.drawString(20 * mm, y, f"Cliente: {cliente_nombre}")
    y -= 6 * mm
    c.drawString(20 * mm, y, f"Legajo: {cliente_legajo}")

    y -= 12 * mm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(20 * mm, y, "Detalle del pago")

    y -= 8 * mm
    c.setFont("Helvetica", 10)
    c.drawString(20 * mm, y, f"Tipo de pago: {tipo_pago}")
    y -= 6 * mm
    c.drawString(20 * mm, y, f"Medio de pago: {medio_pago}")
    y -= 6 * mm
    c.drawString(20 * mm, y, f"Monto pagado: {money(monto)}")

    y -= 12 * mm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(20 * mm, y, "Estado de cuenta luego del pago")

    y -= 8 * mm
    c.setFont("Helvetica", 10)
    c.drawString(20 * mm, y, f"Deuda actual: {money(deuda_actual)}")
    y -= 6 * mm
    c.drawString(20 * mm, y, f"Saldo a favor: {money(saldo_actual)}")

    if observacion:
        y -= 12 * mm
        c.setFont("Helvetica-Bold", 11)
        c.drawString(20 * mm, y, "Observación")
        y -= 6 * mm
        c.setFont("Helvetica", 10)
        c.drawString(20 * mm, y, observacion)

    y = 20 * mm
    c.setFont("Helvetica", 8)
    c.drawString(
        20 * mm,
        y,
        "Documento generado automáticamente por el sistema",
    )

    c.showPage()
    c.save()

    # 🔑 CLAVE: devolver bytes reales
    buffer.seek(0)
    return buffer.read()

