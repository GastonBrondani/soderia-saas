import os
from datetime import datetime
from decimal import Decimal


from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.settings import COMPROBANTES_BASE_PATH, COMPROBANTES_BASE_URL
from app.models.documentos import Documentos
from app.models.pedido import Pedido
from app.models.medioPago import MedioPago
from app.utils.pdf.comprobante_pedido import generar_comprobante_pedido_pdf

DEFAULT_BASE_PATH = "/data/comprobantes/pedidos"
DEFAULT_BASE_URL = "/docs/comprobantes/pedidos"


def _dec(v) -> Decimal:
    if v is None:
        return Decimal("0")
    if isinstance(v, Decimal):
        return v
    return Decimal(str(v))


class ComprobantePedidoService:
    @staticmethod
    def generar_pdf_bytes(db: Session, *, id_pedido: int) -> bytes:
        try:
            pedido: Pedido = db.execute(
                select(Pedido).where(Pedido.id_pedido == id_pedido)
            ).scalar_one()

            print(f"[ComprobantePedido] pedido={pedido.id_pedido} legajo={pedido.legajo}")
            print(f"[ComprobantePedido] pedido.id_medio_pago={pedido.id_medio_pago} (type={type(pedido.id_medio_pago)})")

            # Empresa
            empresa_nombre = (
                pedido.empresa.razon_social
                if getattr(pedido, "empresa", None) is not None
                else "SODERÍA"
            )
            print(f"[ComprobantePedido] empresa={empresa_nombre}")

            # Cliente
            if pedido.cliente is not None and getattr(pedido.cliente, "persona", None) is not None:
                cliente_nombre = f"{pedido.cliente.persona.nombre} {pedido.cliente.persona.apellido}".strip()
            else:
                cliente_nombre = f"Cliente {pedido.legajo}"
            print(f"[ComprobantePedido] cliente={cliente_nombre}")

            # ✅ Medio de pago (NO usar pedido.medio_pagos)
            medio_pago_txt = "-"

            mp = db.execute(
                select(MedioPago).where(MedioPago.id_medio_pago == pedido.id_medio_pago)
            ).scalar_one_or_none()

            if mp is not None:
                medio_pago_txt = mp.nombre

            # Items (pedido_producto)
            items = []
            total_calc = Decimal("0")

            pps = pedido.pedidos_productos or []
            print(f"[ComprobantePedido] pedidos_productos={len(pps)}")

            for pp in pps:
                if pp.producto is not None:
                    nombre = pp.producto.nombre
                elif pp.combo is not None:
                    nombre = f"Combo: {pp.combo.nombre}"
                else:
                    nombre = "Item"

                cant = int(pp.cantidad or 0)
                pu = _dec(pp.precio_unitario)
                sub = pu * Decimal(cant)
                total_calc += sub

                items.append(
                    {
                        "producto": nombre,
                        "cantidad": cant,
                        "precio_unitario": pu,
                        "subtotal": sub,
                    }
                )

            total = _dec(pedido.monto_total)
            if total == 0 and total_calc > 0:
                total = total_calc

            abonado = _dec(pedido.monto_abonado)

            return generar_comprobante_pedido_pdf(
                empresa=empresa_nombre,
                pedido_id=pedido.id_pedido,
                cliente_nombre=cliente_nombre,
                cliente_legajo=pedido.legajo,
                fecha=pedido.fecha,
                items=items,
                total=total,
                monto_abonado=abonado,
                medio_pago=medio_pago_txt,
                estado=pedido.estado,
                observacion=pedido.observacion,
            )

        except Exception as e:
            print(f"[ComprobantePedido] ERROR en generar_pdf_bytes id={id_pedido}: {repr(e)}")
            raise

    @staticmethod
    def generar_y_guardar(db: Session, *, id_pedido: int) -> Documentos:
        pdf_bytes = ComprobantePedidoService.generar_pdf_bytes(db, id_pedido=id_pedido)

        filename = f"pedido_{id_pedido}.pdf"
        base_path = (COMPROBANTES_BASE_PATH or DEFAULT_BASE_PATH).rstrip("/")
        base_url = (COMPROBANTES_BASE_URL or DEFAULT_BASE_URL).rstrip("/")

        os.makedirs(base_path, exist_ok=True)

        file_path = os.path.join(base_path, filename)
        url_archivo = f"{base_url}/{filename}"

        with open(file_path, "wb") as f:
            f.write(pdf_bytes)

        pedido: Pedido = db.execute(
            select(Pedido).where(Pedido.id_pedido == id_pedido)
        ).scalar_one()

        doc = Documentos(
            legajo=pedido.legajo,
            nombre_archivo=filename,
            tipo_archivo="COMPROBANTE_PEDIDO",
            url_archivo=url_archivo,
            fecha_carga=datetime.utcnow(),
            observacion=f"Comprobante de pedido #{id_pedido}",
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        return doc



