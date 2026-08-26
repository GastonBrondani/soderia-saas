from __future__ import annotations
from datetime import date
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import select, update, and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from fastapi import HTTPException

from app.models.repartoDia import RepartoDia


class RepartoDiaService:
    """
    Reglas de negocio para RepartoDia.
    Mantiene las operaciones atómicas y la validación de invariantes.
    """

    # ---------- Lectura ----------
    @staticmethod
    def get(db: Session, id_repartodia: int) -> RepartoDia:
        entity = db.get(RepartoDia, id_repartodia)
        if not entity:
            raise HTTPException(status_code=404, detail="Reparto día no encontrado.")
        return entity

    
    @staticmethod
    def get_by_fecha(
        db: Session,
        *,
        fecha: date,
        id_empresa: Optional[int] = None,
        id_usuario: Optional[int] = None,
    ) -> RepartoDia:
        stmt = select(RepartoDia).where(RepartoDia.fecha == fecha)

        if id_empresa is not None:
            stmt = stmt.where(RepartoDia.id_empresa == id_empresa)

        if id_usuario is not None:
            stmt = stmt.where(RepartoDia.id_usuario == id_usuario)

        entity = db.execute(stmt).scalars().first()
        if not entity:
            raise HTTPException(
                status_code=404,
                detail="Reparto día no encontrado para esa fecha.",
            )
        return entity

    # ---------- Escritura ----------
    @staticmethod
    def create(
        db: Session,
        *,
        id_usuario: int,
        id_empresa: int,
        fecha: date,
        observacion: Optional[str] = None,
        # Si tu modelo exige unicidad (empresa+usuario+fecha), podés hacer create_or_get
        ensure_unique: bool = True,
    ) -> RepartoDia:
        if ensure_unique:
            # Verificamos que no exista otro para misma (empresa, usuario, fecha)
            dup = db.execute(
                select(RepartoDia.id_repartodia).where(
                    RepartoDia.id_empresa == id_empresa,
                    RepartoDia.id_usuario == id_usuario,
                    RepartoDia.fecha == fecha,
                )
            ).first()
            if dup:
                raise HTTPException(
                    status_code=409,
                    detail="Ya existe un reparto para ese usuario y fecha en esa empresa.",
                )

        entity = RepartoDia(
            id_usuario=id_usuario,
            id_empresa=id_empresa,
            fecha=fecha,
            observacion=(observacion or "").strip() or None,
        )
        try:
            db.add(entity)
            db.commit()
            db.refresh(entity)
        except IntegrityError as e:
            db.rollback()
            raise HTTPException(
                status_code=409,
                detail="No se pudo crear el reparto del día (FK o duplicado).",
            ) from e
        return entity

    @staticmethod
    def update(
        db: Session,
        *,
        id_repartodia: int,
        id_usuario: Optional[int] = None,
        id_empresa: Optional[int] = None,
        fecha: Optional[date] = None,
        observacion: Optional[str] = None,
    ) -> RepartoDia:
        entity = RepartoDiaService.get(db, id_repartodia)

        if id_usuario is not None:
            entity.id_usuario = id_usuario
        if id_empresa is not None:
            entity.id_empresa = id_empresa
        if fecha is not None:
            entity.fecha = fecha
        if observacion is not None:
            entity.observacion = observacion.strip() or None

        try:
            db.commit()
            db.refresh(entity)
        except IntegrityError as e:
            db.rollback()
            raise HTTPException(
                status_code=409,
                detail="No se pudo actualizar el reparto (FK o unicidad).",
            ) from e
        return entity

    @staticmethod
    def delete(db: Session, *, id_repartodia: int) -> None:
        entity = RepartoDiaService.get(db, id_repartodia)
        try:
            db.delete(entity)
            db.commit()
        except IntegrityError as e:
            db.rollback()
            raise HTTPException(
                status_code=409,
                detail="No se puede eliminar: existen registros relacionados.",
            ) from e

    # ---------- Operaciones de negocio ----------
    @staticmethod
    def registrar_cobro(
        db: Session,
        *,
        id_repartodia: int,
        efectivo: Decimal,
        virtual: Decimal,
    ) -> RepartoDia:
        """
        Suma efectivo/virtual y total en una sola sentencia SQL (atómico).
        """
        if efectivo < 0 or virtual < 0:
            raise HTTPException(status_code=400, detail="Los importes no pueden ser negativos.")

        total = efectivo + virtual

        # UPDATE ... RETURNING mantiene atomicidad y evita race conditions entre readers/writers.
        stmt = (
            update(RepartoDia)
            .where(RepartoDia.id_repartodia == id_repartodia)
            .values(
                total_efectivo=(RepartoDia.total_efectivo + efectivo),
                total_virtual=(RepartoDia.total_virtual + virtual),
                total_recaudado=(RepartoDia.total_recaudado + total),
            )
            .returning(RepartoDia)
        )
        try:
            row = db.execute(stmt).first()
            db.commit()
        except IntegrityError as e:
            db.rollback()
            raise HTTPException(status_code=409, detail="No se pudo registrar el cobro.") from e

        if not row:
            # Si no había filas, no existía el id
            raise HTTPException(status_code=404, detail="Reparto día no encontrado.")
        return row[0]

    @staticmethod
    def cerrar(db: Session,*,id_repartodia: int,) -> RepartoDia:
        e = RepartoDiaService.get(db, id_repartodia)

        e.total_efectivo = (e.total_efectivo or Decimal("0.00"))
        e.total_virtual  = (e.total_virtual  or Decimal("0.00"))
        # total_recaudado = suma de buckets que ya tenés
        e.total_recaudado = e.total_efectivo + e.total_virtual
        db.commit()
        db.refresh(e)
        return e  
    
    @staticmethod
    def listar_por_rango(
        db,
        *,
        fecha_desde: date,
        fecha_hasta: date,
        id_empresa: Optional[int] = None,
        id_usuario: Optional[int] = None,
    ) -> List[RepartoDia]:
        stmt = select(RepartoDia).where(
            and_(
                RepartoDia.fecha >= fecha_desde,
                RepartoDia.fecha <= fecha_hasta,
            )
        )

        if id_empresa is not None:
            stmt = stmt.where(RepartoDia.id_empresa == id_empresa)

        if id_usuario is not None:
            stmt = stmt.where(RepartoDia.id_usuario == id_usuario)

        stmt = stmt.order_by(RepartoDia.fecha.desc(), RepartoDia.id_repartodia.desc())

        return db.execute(stmt).scalars().all()

   
