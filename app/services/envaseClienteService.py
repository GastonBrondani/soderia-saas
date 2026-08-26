from __future__ import annotations
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.productoCliente import ProductoCliente
from app.models.movimientoEnvaseCliente import MovimientoEnvaseCliente
from app.models.producto import Producto
from app.models.stock import Stock
from app.models.movimientoStock import MovimientoStock
from app.schemas.enumsStock import TipoMovimiento


class EnvaseClienteService:

    @staticmethod
    def _get_producto_envase(db: Session, id_producto: int) -> Producto:
        prod = db.get(Producto, id_producto)
        if prod is None:
            raise HTTPException(status_code=404, detail=f"Producto {id_producto} inexistente.")
        if not prod.es_envase:
            raise HTTPException(status_code=400, detail=f"El producto {id_producto} no es un envase.")
        return prod

    @staticmethod
    def ajustar_saldo(
        db: Session,
        *,
        legajo: int,
        id_producto: int,
        delta: int,
        tipo: str,                          # "ENTREGA" | "RETIRO" | "COBRO" | "PERDIDA"
        id_repartodia: Optional[int] = None,
        id_pedido: Optional[int] = None,
        observacion: Optional[str] = None,
        fecha: Optional[datetime] = None,
        validar_envase: bool = True,        # False cuando lo llama confirmar_pedido (ya validó antes)
    ) -> ProductoCliente:

        if delta == 0:
            raise HTTPException(status_code=400, detail="El delta no puede ser 0.")

        now = fecha or datetime.now()

        if validar_envase:
            EnvaseClienteService._get_producto_envase(db, id_producto)

        # 1) Upsert saldo
        row = db.execute(
            select(ProductoCliente).where(
                ProductoCliente.legajo == legajo,
                ProductoCliente.id_producto == id_producto,
            ).with_for_update()
        ).scalar_one_or_none()

        if row is None:
            if delta < 0:
                raise HTTPException(
                    status_code=409,
                    detail="No se puede retirar un envase que el cliente nunca recibió."
                )
            row = ProductoCliente(
                legajo=legajo,
                id_producto=id_producto,
                cantidad=0,
                estado="activo",
                fecha_entrega=now.date(),
            )
            db.add(row)
            db.flush()

        nuevo = row.cantidad + delta
        if nuevo < 0:
            raise HTTPException(
                status_code=409,
                detail=f"Saldo insuficiente. El cliente tiene {row.cantidad} unidad/es del envase {id_producto}."
            )

        row.cantidad = nuevo
        if delta > 0:
            row.fecha_entrega = now.date()

        # Estado automático
        if nuevo == 0:
            row.estado = "sin_envases"
        else:
            row.estado = "activo"

        # 2) Historial
        db.add(MovimientoEnvaseCliente(
            legajo=legajo,
            id_producto=id_producto,
            id_repartodia=id_repartodia,
            id_pedido=id_pedido,
            fecha=now,
            tipo=tipo,
            cantidad=abs(delta),
            observacion=observacion,
        ))

        return row

    @staticmethod
    def get_saldo_cliente(db: Session, legajo: int) -> list[ProductoCliente]:
        return db.execute(
            select(ProductoCliente).where(
                ProductoCliente.legajo == legajo,
                ProductoCliente.cantidad > 0,
            )
        ).scalars().all()

    @staticmethod
    def get_historial_cliente(
        db: Session,
        legajo: int,
        id_producto: Optional[int] = None,
    ) -> list[MovimientoEnvaseCliente]:
        stmt = select(MovimientoEnvaseCliente).where(
            MovimientoEnvaseCliente.legajo == legajo
        )
        if id_producto is not None:
            stmt = stmt.where(MovimientoEnvaseCliente.id_producto == id_producto)
        stmt = stmt.order_by(MovimientoEnvaseCliente.fecha.desc())
        return db.execute(stmt).scalars().all()
    
    @staticmethod
    def registrar_movimiento(
        db: Session,
        *,
        legajo: int,
        id_producto: int,
        id_empresa: int,
        entregados: int = 0,
        devueltos: int = 0,
        id_repartodia: Optional[int] = None,
        id_pedido: Optional[int] = None,
        observacion: Optional[str] = None,
        fecha: Optional[datetime] = None,
    ) -> ProductoCliente | None:

        if entregados < 0 or devueltos < 0:
            raise HTTPException(
                status_code=400,
                detail="entregados y devueltos no pueden ser negativos.",
            )

        if entregados == 0 and devueltos == 0:
            raise HTTPException(
                status_code=400,
                detail="Debe venir al menos un envase entregado o devuelto.",
            )

        now = fecha or datetime.now()

        # Validar producto envase una sola vez
        EnvaseClienteService._get_producto_envase(db, id_producto)

        saldo_resultante: ProductoCliente | None = None

        # 1) Si la empresa entregó envases al cliente
        if entregados > 0:
            # Baja stock empresa
            stock = db.execute(
                select(Stock)
                .where(
                    Stock.id_empresa == id_empresa,
                    Stock.id_producto == id_producto,
                )
                .with_for_update()
            ).scalar_one_or_none()

            if stock is None:
                raise HTTPException(
                    status_code=409,
                    detail=f"No hay stock para el envase {id_producto}.",
                )

            if stock.cantidad < entregados:
                raise HTTPException(
                    status_code=409,
                    detail=f"Stock insuficiente para el envase {id_producto}.",
                )

            stock.cantidad -= entregados

            db.add(
                MovimientoStock(
                    id_producto=id_producto,
                    id_pedido=id_pedido,
                    fecha=now,
                    tipo_movimiento=TipoMovimiento.egreso.value,
                    cantidad=entregados,
                    observacion=observacion or f"Entrega de envase a cliente {legajo}",
                )
            )

            saldo_resultante = EnvaseClienteService.ajustar_saldo(
                db,
                legajo=legajo,
                id_producto=id_producto,
                delta=entregados,
                tipo="ENTREGA",
                id_repartodia=id_repartodia,
                id_pedido=id_pedido,
                observacion=observacion,
                fecha=now,
                validar_envase=False,
            )

        # 2) Si el cliente devolvió envases a la empresa
        if devueltos > 0:
            # Primero baja saldo cliente. Si no tiene saldo suficiente, falla acá.
            saldo_resultante = EnvaseClienteService.ajustar_saldo(
                db,
                legajo=legajo,
                id_producto=id_producto,
                delta=-devueltos,
                tipo="RETIRO",
                id_repartodia=id_repartodia,
                id_pedido=id_pedido,
                observacion=observacion,
                fecha=now,
                validar_envase=False,
            )

            # Sube stock empresa
            stock = db.execute(
                select(Stock)
                .where(
                    Stock.id_empresa == id_empresa,
                    Stock.id_producto == id_producto,
                )
                .with_for_update()
            ).scalar_one_or_none()

            if stock is None:
                stock = Stock(
                    id_empresa=id_empresa,
                    id_producto=id_producto,
                    cantidad=0,
                )
                db.add(stock)
                db.flush()

            stock.cantidad += devueltos

            db.add(
                MovimientoStock(
                    id_producto=id_producto,
                    id_pedido=id_pedido,
                    fecha=now,
                    tipo_movimiento=TipoMovimiento.ingreso.value,
                    cantidad=devueltos,
                    observacion=observacion or f"Retiro/devolución de envase cliente {legajo}",
                )
            )

        return saldo_resultante