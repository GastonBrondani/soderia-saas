import io
from datetime import datetime
from enum import Enum
from typing import Optional

import openpyxl
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import and_, extract, func, select
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.cliente import Cliente
from app.models.clienteDiaSemana import ClienteDiaSemana
from app.models.diaSemana import DiaSemana
from app.models.pedido import Pedido
from app.models.pedidoProducto import PedidoProducto
from app.models.producto import Producto


class DiaSemanaFiltro(str, Enum):
    lunes = "lunes"
    martes = "martes"
    miercoles = "miercoles"
    jueves = "jueves"
    viernes = "viernes"
    sabado = "sabado"
    domingo = "domingo"

router = APIRouter(
    prefix="/reportes",
    tags=["Reportes"],
    dependencies=[Depends(get_current_user)],
)

_MORA_MSG = (
    "\nQueríamos recordarte que tenés un saldo pendiente a la fecha.\n"
    "A partir de agosto, todo pago vencido genera un recargo por mora:\n\n"
    "➡️ +30 días: 10 %\n"
    "➡️ +60 días: 20 %\n\n"
    "Te invitamos a regularizarlo para evitar cargos adicionales y así poder "
    "seguir ofreciéndote un servicio confiable y de calidad 💧🚚.\n\n"
    "Muchas gracias por tu atención 🙏"
)

_PRECIO_AGUA12 = 3500
_PRECIO_AGUA20 = 5000
_PRECIO_SODA = 1100
_PRECIO_JUGO = 6000
_PRECIO_ENVASE = 7500

_HEADERS = [
    None, "orden", "cliente", "teléfono", "numero concatenado",
    "saldo anterior", 0.1, "agua de 12", "agua de 20",
    "sodas", "jugo", "envase", "extra", "saldo mes en curso",
    "total", "saludo", "cálculo", "mensaje concatenado", "procesados",
    "saludo", "mensaje", "mensaje concatenado", "procesado",
]


def _fmt_ar(value: float) -> str:
    """Formato moneda argentina: $1.234,56"""
    s = f"{value:,.2f}"
    return "$" + s.replace(",", "X").replace(".", ",").replace("X", ".")


def _grupo_dias(dias_rows) -> str:
    nombres = [
        cds.dia_semana.nombre_dia.lower()
        for cds in sorted(dias_rows, key=lambda x: x.id_dia)
        if cds.dia_semana
    ]
    if not nombres:
        return ""
    if len(nombres) == 1:
        return nombres[0]
    return " y ".join(nombres)


def _clasificar_producto(nombre: str, litros, es_envase: bool) -> Optional[str]:
    if es_envase:
        return "envase"
    litros_val = float(litros) if litros is not None else None
    if litros_val == 12:
        return "agua12"
    if litros_val == 20:
        return "agua20"
    n = (nombre or "").lower()
    if "soda" in n or "sif" in n:
        return "sodas"
    if "jugo" in n:
        return "jugo"
    return None


@router.get(
    "/excel-cuentas",
    summary="Exportar planilla de envío de cuentas",
    response_class=StreamingResponse,
    responses={
        200: {
            "content": {
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {}
            },
            "description": "Archivo Excel (.xlsx) con la planilla de cuentas del mes",
        }
    },
)
def exportar_excel_cuentas(
    mes: Optional[int] = Query(default=None, ge=1, le=12, description="Mes (1-12). Por defecto el mes actual."),
    anio: Optional[int] = Query(default=None, ge=2020, description="Año. Por defecto el año actual."),
    dia: Optional[DiaSemanaFiltro] = Query(default=None, description="Filtrar por día de visita (lunes, martes, ...)."),
    db: Session = Depends(get_db),
):
    hoy = datetime.now()
    mes_q = mes or hoy.month
    anio_q = anio or hoy.year

    # Clientes con todas las relaciones necesarias
    stmt_clientes = (
        select(Cliente)
        .options(
            selectinload(Cliente.persona),
            selectinload(Cliente.telefonos),
            selectinload(Cliente.cuentas),
            selectinload(Cliente.dias_semanas).selectinload(ClienteDiaSemana.dia_semana),
        )
        .order_by(Cliente.legajo)
    )

    if dia is not None:
        stmt_clientes = (
            stmt_clientes
            .join(ClienteDiaSemana, Cliente.legajo == ClienteDiaSemana.id_cliente)
            .join(DiaSemana, ClienteDiaSemana.id_dia == DiaSemana.id_dia)
            .where(func.lower(DiaSemana.nombre_dia).startswith(dia.value[:2]))
            .distinct()
        )

    clientes = db.execute(stmt_clientes).scalars().all()

    # Totales de productos entregados por cliente en el mes
    stmt_prods = (
        select(
            Pedido.legajo,
            Producto.nombre,
            Producto.litros,
            Producto.es_envase,
            func.sum(PedidoProducto.cantidad).label("total"),
        )
        .join(PedidoProducto, Pedido.id_pedido == PedidoProducto.id_pedido)
        .join(Producto, PedidoProducto.id_producto == Producto.id_producto)
        .where(
            and_(
                extract("month", Pedido.fecha) == mes_q,
                extract("year", Pedido.fecha) == anio_q,
                PedidoProducto.id_producto.is_not(None),
            )
        )
        .group_by(Pedido.legajo, Producto.nombre, Producto.litros, Producto.es_envase)
    )
    prod_totales: dict = {}
    for row in db.execute(stmt_prods).all():
        leg = row.legajo
        if leg not in prod_totales:
            prod_totales[leg] = {"agua12": 0, "agua20": 0, "sodas": 0, "jugo": 0, "envase": 0}
        cat = _clasificar_producto(row.nombre, row.litros, row.es_envase)
        if cat:
            prod_totales[leg][cat] += int(row.total)

    # Construir Excel
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Hoja2"
    ws.append(_HEADERS)

    for idx, cliente in enumerate(clientes, start=1):
        if not cliente.persona:
            continue

        nombre = f"{cliente.persona.nombre} {cliente.persona.apellido}".strip()

        telefono = next(
            (t.nro_telefono for t in cliente.telefonos if t.nro_telefono),
            None,
        )

        deuda = 0.0
        for cuenta in cliente.cuentas:
            deuda = float(cuenta.deuda or 0)
            break

        grupo = _grupo_dias(cliente.dias_semanas)

        prods = prod_totales.get(
            cliente.legajo,
            {"agua12": 0, "agua20": 0, "sodas": 0, "jugo": 0, "envase": 0},
        )
        agua12 = prods["agua12"]
        agua20 = prods["agua20"]
        sodas = prods["sodas"]
        jugo = prods["jugo"]
        envase = prods["envase"]
        extra = 0

        saldo_con_recargo = deuda * 1.1
        saldo_mes = (
            agua12 * _PRECIO_AGUA12
            + agua20 * _PRECIO_AGUA20
            + sodas * _PRECIO_SODA
            + jugo * _PRECIO_JUGO
            + envase * _PRECIO_ENVASE
        )
        total = saldo_con_recargo + saldo_mes + extra

        saludo1 = f"_Buen día {nombre}! Le paso el saldo pendiente:_"
        calculo = (
            f"*DETALLE DE CUENTA:*\n"
            f"{agua12} bidones de 12l\n"
            f"{agua20} bidones de 20l\n"
            f"{sodas} sodas\n"
            f"{jugo} jugo\n"
            f"{envase} envase\n"
            f"{extra} extra\n\n"
            f"*TOTAL:*{_fmt_ar(saldo_mes)}\n\n"
            f"*SALDO ANTERIOR:*{_fmt_ar(saldo_con_recargo)}\n"
            f"*MONTO TOTAL ADEUDADO:*{_fmt_ar(total)}"
        )
        msg1 = saludo1 + "\n" + calculo

        saludo2 = f"_Buen día {nombre}_"
        # Solo incluir mensaje de mora si el cliente tiene deuda anterior
        mora_msg = _MORA_MSG if deuda > 0 else None
        msg2 = (saludo2 + mora_msg) if mora_msg else None

        ws.append([
            grupo,
            idx,
            nombre,
            telefono,
            f"549{telefono}" if telefono else None,
            deuda,
            saldo_con_recargo,
            agua12,
            agua20,
            sodas,
            jugo,
            envase,
            extra,
            saldo_mes,
            total,
            saludo1,
            calculo,
            msg1,
            None,           # procesados (columna manual)
            saludo2,
            mora_msg,
            msg2,
            None,           # procesado (columna manual)
        ])

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    sufijo_dia = f"_{dia.value}" if dia else ""
    filename = f"cuentas_{anio_q}_{mes_q:02d}{sufijo_dia}.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
