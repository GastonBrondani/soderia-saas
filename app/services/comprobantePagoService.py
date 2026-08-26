import os

DEFAULT_BASE_PATH = "/data/comprobantes/pagos"
DEFAULT_BASE_URL = "/docs/comprobantes/pagos"

from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.pago import Pago
from app.models.clienteCuenta import ClienteCuenta
from app.models.documentos import Documentos
from app.utils.pdf.comprobante_pago import generar_comprobante_pago_pdf
from app.core.settings import (
    COMPROBANTES_BASE_PATH,
    COMPROBANTES_BASE_URL,
)


class ComprobantePagoService:

    @staticmethod
    def generar_pdf_bytes(db: Session, *, id_pago: int) -> bytes:
        pago = db.execute(
            select(Pago).where(Pago.id_pago == id_pago)
        ).scalar_one()

        if pago.legajo is None or pago.cliente is None:
            raise ValueError("El pago no está asociado a un cliente.")

        # ✅ Buscar la cuenta exacta usada en el pago
        if getattr(pago, "id_cuenta", None) is None:
            # fallback: si no tenés id_cuenta en Pago, evitá romper (elige una)
            cuenta = db.execute(
                select(ClienteCuenta)
                .where(ClienteCuenta.legajo == pago.legajo)
                .order_by(ClienteCuenta.id_cuenta.asc())
            ).scalars().first()
            if cuenta is None:
                raise ValueError("El cliente no tiene cuenta asociada.")
        else:
            cuenta = db.execute(
            select(ClienteCuenta).where(ClienteCuenta.id_cuenta == pago.id_cuenta)
            ).scalar_one_or_none()

            if cuenta is None:
                raise ValueError("La cuenta asociada al pago no existe.")


        empresa_nombre = pago.empresa.razon_social
        cliente_nombre = (
            f"{pago.cliente.persona.nombre} {pago.cliente.persona.apellido}"
        )

        return generar_comprobante_pago_pdf(
            empresa=empresa_nombre,
            pago_id=pago.id_pago,
            cliente_nombre=cliente_nombre,
            cliente_legajo=pago.legajo,
            fecha=pago.fecha,
            monto=pago.monto,
            medio_pago=pago.medio_pago.nombre,
            tipo_pago=pago.tipo_pago,
            deuda_actual=cuenta.deuda or Decimal("0"),
            saldo_actual=cuenta.saldo or Decimal("0"),
            observacion=pago.observacion,
        )

    @staticmethod
    def generar_y_guardar(db: Session, *, id_pago: int) -> Documentos:
        # 1. Generar PDF
        pdf_bytes = ComprobantePagoService.generar_pdf_bytes(
            db, id_pago=id_pago
        )

        # 2. Guardar archivo
        filename = f"pago_{id_pago}.pdf"
        base_path = COMPROBANTES_BASE_PATH or DEFAULT_BASE_PATH
        base_url = COMPROBANTES_BASE_URL or DEFAULT_BASE_URL

        os.makedirs(base_path, exist_ok=True)
        
        url_archivo = f"{base_url}/{filename}"


        file_path = os.path.join(base_path, filename)


        with open(file_path, "wb") as f:
            f.write(pdf_bytes)

        # 3. Obtener legajo
        legajo = db.execute(
            select(Pago.legajo).where(Pago.id_pago == id_pago)
        ).scalar_one()

        # 4. Registrar documento
        doc = Documentos(
            legajo=legajo,
            nombre_archivo=filename,
            tipo_archivo="COMPROBANTE_PAGO",
            url_archivo=url_archivo,
            fecha_carga=datetime.utcnow(),
            observacion=f"Comprobante de pago #{id_pago}",
        )

        db.add(doc)
        db.commit()
        db.refresh(doc)

        return doc
