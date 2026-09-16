from sqlalchemy import and_, func, select, update
from sqlalchemy.orm import Session, joinedload, selectinload
from typing import Any, Dict, List, Optional

from app.core.exceptions import AppError, Conflict, NotFound, ValidationFailed
from app.features.empresas.service import EmpresaService


#Modelos utilizados
from app.features.clientes.models.cliente import Cliente
from app.features.personas.models.persona import Persona
from app.features.clientes.models.direccion_cliente import DireccionCliente
from app.features.clientes.models.telefono_cliente import TelefonoCliente
from app.features.clientes.models.email_cliente import MailCliente
from app.features.clientes.models.cliente_cuenta import ClienteCuenta
from app.features.clientes.models.producto_cliente import ProductoCliente
from app.features.repartos.agenda.models.cliente_dia_semana import ClienteDiaSemana
from app.features.maestros.models.dia_semana import DiaSemana
from app.features.catalogo.productos.models.producto import Producto
from app.features.auditoria.models.historico import Historico
from app.features.pedidos.models.pedido import Pedido

#Schemas utilizados
from app.features.clientes.schemas.cliente import ClienteCreate, ClienteUpdate
from app.features.clientes.schemas.cliente_detalle import ClienteDetalleOut, ClienteDetalleUpdate
from app.features.clientes.schemas.cliente_cuenta import ClienteCuentaCreate
from app.features.clientes.schemas.producto_cliente import (
    ProductoClienteOut,
    ProductoClienteUpsert,
    ProductoClientePatch,
)
from app.features.auditoria.schemas.historico import HistoricoOut
from app.features.pedidos.schemas.pedido import PedidoOutCorto

#Utilizados para guardar un historico del cliente
from app.features.auditoria.service import registrar_evento_cliente
from app.features.auditoria.schemas.enums_historico import TipoEventoCodigoEnum


def _idx_dias(db: Session) -> Dict[str, int]:
    """Devuelve {'lun': id_dia, ...} en base a tabla dia_semana."""
    dias_db = db.execute(select(DiaSemana)).scalars().all()
    idx: Dict[str, int] = {}
    for d in dias_db:
        nombre = (d.nombre_dia or "").strip().lower()
        if nombre.startswith("lu"):
            idx["lun"] = d.id_dia
        elif nombre.startswith("ma") and "r" in nombre:
            idx["mar"] = d.id_dia
        elif nombre.startswith("mi"):
            idx["mie"] = d.id_dia
        elif nombre.startswith("ju"):
            idx["jue"] = d.id_dia
        elif nombre.startswith("vi"):
            idx["vie"] = d.id_dia
        elif nombre.startswith("sa"):
            idx["sab"] = d.id_dia
        elif nombre.startswith("do"):
            idx["dom"] = d.id_dia
    return idx


def _calcular_orden_y_correr(
    db: Session,
    id_dia: int,
    turno_val: Optional[str],
    posicion: str,
    despues_de_legajo: Optional[int] = None,
) -> int:
    """
    Devuelve el orden a asignar al nuevo registro y corre los existentes de ser necesario.
    Bloquea el conjunto (día/turno) para evitar carreras.
    """
    filtro_base = and_(
        ClienteDiaSemana.id_dia == id_dia,
        (
            ClienteDiaSemana.turno_visita.is_(None)
            if turno_val is None
            else ClienteDiaSemana.turno_visita == turno_val
        ),
    )

    # Lock del set afectado
    db.execute(select(ClienteDiaSemana.id_cliente).where(filtro_base).with_for_update())

    if posicion == "inicio":
        db.execute(
            update(ClienteDiaSemana)
            .where(filtro_base)
            .values(orden=func.coalesce(ClienteDiaSemana.orden, 0) + 1)
        )
        return 1

    if posicion == "final":
        max_orden = db.execute(
            select(func.coalesce(func.max(ClienteDiaSemana.orden), 0)).where(
                filtro_base
            )
        ).scalar_one()
        return max_orden + 1

    # posicion == "despues"
    if not despues_de_legajo:
        raise AppError("Falta 'despues_de_legajo' para posicion='despues'.")

    ref_orden = db.execute(
        select(ClienteDiaSemana.orden).where(
            and_(filtro_base, ClienteDiaSemana.id_cliente == despues_de_legajo)
        )
    ).scalar_one_or_none()

    if ref_orden is None:
        raise NotFound("Cliente de referencia no existe en ese día/turno.")

    db.execute(
        update(ClienteDiaSemana)
        .where(
            and_(
                filtro_base,
                ClienteDiaSemana.orden >= ref_orden + 1,
            )
        )
        .values(orden=ClienteDiaSemana.orden + 1)
    )

    return ref_orden + 1


def _get_producto_cliente_con_producto(db: Session, legajo: int, id_producto: int) -> ProductoCliente:
    """Recarga el producto_cliente con la relación producto (para el response)."""
    return db.execute(
        select(ProductoCliente)
        .where(
            ProductoCliente.legajo == legajo,
            ProductoCliente.id_producto == id_producto,
        )
        .options(joinedload(ProductoCliente.producto))
    ).scalar_one()



class ClienteService:

    @staticmethod
    def crear_cliente(db: Session, payload: ClienteCreate) -> ClienteDetalleOut:
        try:
            # 1) DNI / Persona
            dni_final = payload.persona.dni if payload.persona else payload.dni
            persona = db.get(Persona, dni_final)

            if payload.persona:
                if not persona:
                    persona = Persona(**payload.persona.model_dump())
                    db.add(persona)
                    db.flush()
            else:
                if not persona:
                    raise NotFound(
                        "La persona (dni) no existe. Enviá 'persona' para crearla.",
                    )

            # 2) Duplicado por empresa
            id_empresa = EmpresaService.get_id_empresa_actual(db)
            existe = (
                db.query(Cliente)
                .filter(and_(Cliente.dni == dni_final, Cliente.id_empresa == id_empresa))
                .first()
            )
            if existe:
                raise Conflict("Ya existe un cliente para ese DNI en esta empresa.")

            # 3) Crear cliente
            nuevo = Cliente(id_empresa=id_empresa, observacion=payload.observacion)
            nuevo.persona = persona
            db.add(nuevo)
            db.flush()  # genera legajo

            # 4) Hijos anidados
            if payload.direcciones:
                db.add_all(
                    [
                        DireccionCliente(
                            legajo=nuevo.legajo,
                            direccion=d.direccion,
                            entre_calle1=d.entre_calle1,
                            entre_calle2=d.entre_calle2,
                            zona=d.zona,
                        )
                        for d in payload.direcciones
                    ]
                )

            if payload.telefonos:
                db.add_all(
                    [
                        TelefonoCliente(legajo=nuevo.legajo, nro_telefono=t.nro_telefono)
                        for t in payload.telefonos
                    ]
                )

            if payload.emails:
                db.add_all(
                    [MailCliente(legajo=nuevo.legajo, mail=e.mail) for e in payload.emails]
                )

            # 5) Días + turno → cliente_dia_semana (con ORDEN)
            registros: List[ClienteDiaSemana] = []
            idx = _idx_dias(db)

            if payload.frecuencias and len(payload.frecuencias) > 0:
                # Versión rica por día
                for f in payload.frecuencias:
                    id_dia = idx.get(f.dia.value)
                    if not id_dia:
                        raise AppError(f"Día no encontrado: {f.dia.value}")

                    turno_val = f.turno.value if hasattr(f.turno, "value") else f.turno
                    posicion_val = (
                        f.posicion.value
                        if hasattr(f.posicion, "value")
                        else str(f.posicion)
                    )

                    orden_nuevo = _calcular_orden_y_correr(
                        db=db,
                        id_dia=id_dia,
                        turno_val=turno_val,
                        posicion=posicion_val,
                        despues_de_legajo=f.despues_de_legajo,
                    )

                    registros.append(
                        ClienteDiaSemana(
                            id_cliente=nuevo.legajo,
                            id_dia=id_dia,
                            turno_visita=turno_val,
                            orden=orden_nuevo,
                        )
                    )
            elif payload.dias_visita:
                # Compatibilidad: solo 'dias_visita' (+ opcional turno_visita) -> agrega al final
                turno_val = (
                    payload.turno_visita.value
                    if hasattr(payload.turno_visita, "value")
                    else payload.turno_visita
                )
                for dia in dict.fromkeys(payload.dias_visita):  # únicos, en orden
                    id_dia = idx.get(dia.value)
                    if not id_dia:
                        raise AppError(f"Día no encontrado: {dia.value}")

                    orden_nuevo = _calcular_orden_y_correr(
                        db=db,
                        id_dia=id_dia,
                        turno_val=turno_val,
                        posicion="final",
                    )
                    registros.append(
                        ClienteDiaSemana(
                            id_cliente=nuevo.legajo,
                            id_dia=id_dia,
                            turno_visita=turno_val,
                            orden=orden_nuevo,
                        )
                    )

            if registros:
                db.add_all(registros)

            # 6) Crear cuenta por defecto para el cliente
            #    Usa los defaults del schema: saldo=0, deuda=0, numero_bidones=0
            cuenta_payload = ClienteCuentaCreate()
            cuenta_data = cuenta_payload.model_dump(exclude_unset=True)
            cuenta = ClienteCuenta(legajo=nuevo.legajo, **cuenta_data)
            db.add(cuenta)

            # 7) Commit y retorno
            db.commit()
            db.refresh(cuenta)

            return ClienteService.get_detalle_cliente(db, nuevo.legajo)

        except AppError:
            raise
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def listar_clientes(db: Session) -> List[Cliente]:
        return (
            db.query(Cliente)
            .options(
                selectinload(Cliente.persona),
                selectinload(Cliente.telefonos),
            )
            .filter(Cliente.id_empresa == 1)
            .all()
        )

    @staticmethod
    def actualizar_cliente(db: Session, legajo: int, payload: ClienteUpdate) -> Cliente:
        try:
            cliente = db.get(Cliente, legajo)
            if not cliente:
                raise NotFound("Cliente no encontrado")

            # dump parcial, EXCLUYENDO id_empresa para que jamás lo toquemos
            data_cliente = payload.model_dump(exclude_unset=True, exclude={"id_empresa"})
            persona_patch = data_cliente.pop("persona", None)

            # setear solo campos con valor NO None (evita overwrites a NULL)
            for campo, valor in data_cliente.items():
                if valor is not None:
                    setattr(cliente, campo, valor)

            if persona_patch:
                persona = db.get(Persona, cliente.dni)
                if not persona:
                    raise Conflict("Inconsistencia: el cliente no tiene persona asociada.")
                for campo, valor in persona_patch.items():
                    if valor is not None:
                        setattr(persona, campo, valor)

            db.commit()
            # asegurar persona en salida
            cliente = (
                db.query(Cliente)
                .options(selectinload(Cliente.persona))
                .filter(Cliente.legajo == legajo)
                .first()
            )
            return cliente

        except AppError:
            raise
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def eliminar_cliente(db: Session, legajo: int) -> None:
        try:
            cliente = db.get(Cliente, legajo)
            if not cliente:
                raise NotFound("Cliente no encontrado")
            db.delete(cliente)
            db.commit()
        except NotFound:
            raise
        except Exception as e:
            db.rollback()
            # Si hay FKs (pedidos, usuarios, etc.) puede fallar por restricción
            raise Conflict(f"No se pudo eliminar el cliente (referencias activas): {e}")

    @staticmethod
    def listar_historico_cliente(db: Session, legajo: int, limit: int) -> List[HistoricoOut]:
        cliente = db.get(Cliente, legajo)
        if not cliente:
            raise NotFound("Cliente no encontrado")

        stmt = (
            select(Historico)
            .where(Historico.legajo == legajo)
            .order_by(Historico.fecha.desc())
            .limit(limit)
            .options(selectinload(Historico.tipo_evento))
        )
        rows = db.execute(stmt).scalars().all()
        return [HistoricoOut.model_validate(h) for h in rows]

    @staticmethod
    def listar_pedidos_cliente(db: Session, legajo: int, limit: int) -> List[PedidoOutCorto]:
        cliente = db.get(Cliente, legajo)
        if not cliente:
            raise NotFound("Cliente no encontrado")

        stmt = (
            select(Pedido)
            .where(Pedido.legajo == legajo)
            .order_by(Pedido.fecha.desc())
            .limit(limit)
        )
        rows = db.execute(stmt).scalars().all()
        return [PedidoOutCorto.model_validate(p) for p in rows]

    @staticmethod
    def listar_productos_cliente(db: Session, legajo: int) -> List[ProductoClienteOut]:
        cliente = db.get(Cliente, legajo)
        if not cliente:
            raise NotFound("Cliente no encontrado")

        stmt = (
            select(ProductoCliente)
            .where(ProductoCliente.legajo == legajo)
            .options(joinedload(ProductoCliente.producto))
        )
        rows = db.execute(stmt).scalars().all()
        return [ProductoClienteOut.model_validate(r) for r in rows]

    @staticmethod
    def upsert_producto_cliente(
        db: Session, legajo: int, id_producto: int, payload: ProductoClienteUpsert
    ) -> ProductoClienteOut:
        """
        Crea o reemplaza por completo el producto del cliente (PUT idempotente).
        Si no existía la fila, la crea; si existía, sobreescribe todos los campos.
        """
        if not db.get(Cliente, legajo):
            raise NotFound("Cliente no encontrado")
        if not db.get(Producto, id_producto):
            raise NotFound("Producto no encontrado")

        fila = db.get(ProductoCliente, {"legajo": legajo, "id_producto": id_producto})
        if fila is None:
            fila = ProductoCliente(legajo=legajo, id_producto=id_producto)
            db.add(fila)

        fila.cantidad = payload.cantidad
        fila.estado = payload.estado
        fila.fecha_entrega = payload.fecha_entrega

        db.commit()
        return ProductoClienteOut.model_validate(
            _get_producto_cliente_con_producto(db, legajo, id_producto)
        )

    @staticmethod
    def actualizar_producto_cliente(
        db: Session, legajo: int, id_producto: int, payload: ProductoClientePatch
    ) -> ProductoClienteOut:
        """
        Actualiza parcialmente el producto del cliente (PATCH).
        Solo modifica los campos enviados; la fila debe existir (404 si no).
        """
        fila = db.get(ProductoCliente, {"legajo": legajo, "id_producto": id_producto})
        if fila is None:
            raise NotFound("El cliente no tiene ese producto asignado.")

        cambios = payload.model_dump(exclude_unset=True)
        if not cambios:
            raise ValidationFailed("No se enviaron campos para actualizar.")

        for campo, valor in cambios.items():
            setattr(fila, campo, valor)

        db.commit()
        return ProductoClienteOut.model_validate(
            _get_producto_cliente_con_producto(db, legajo, id_producto)
        )

    #Muestro todo lo detallado al cliente.
    @staticmethod
    def get_detalle_cliente(db:Session,legajo:int) ->ClienteDetalleOut:
        stmt = (select(Cliente).options(joinedload(Cliente.persona),
                                        selectinload(Cliente.direcciones),
                                        selectinload(Cliente.telefonos),
                                        selectinload(Cliente.emails),
                                        selectinload(Cliente.productos),
                                        selectinload(Cliente.cuentas),
                                        selectinload(Cliente.dias_semanas),
                                        selectinload(Cliente.historicos),
                                        )
                                        .where(Cliente.legajo == legajo))
        cliente=db.execute(stmt).scalars().first()
        if not cliente:
            raise NotFound("Cliente no encontrado")
        
        return ClienteDetalleOut.model_validate(cliente)
    
    #Actualizo todo lo relacionado al cliente.
    @staticmethod
    def update_detalle_cliente(
        db: Session, legajo: int, data: ClienteDetalleUpdate
    ) -> ClienteDetalleOut:
        # 1) Traer cliente con todas las relaciones que vamos a tocar
        stmt = (
            select(Cliente)
            .options(
                joinedload(Cliente.persona),
                selectinload(Cliente.direcciones),
                selectinload(Cliente.telefonos),
                selectinload(Cliente.emails),
                selectinload(Cliente.cuentas),
                selectinload(Cliente.dias_semanas),
            )
            .where(Cliente.legajo == legajo)
        )
        cliente = db.execute(stmt).scalars().first()
        if not cliente:
            raise NotFound("Cliente no encontrado")

        # Acumulador de cambios para el histórico
        cambios: dict[str, Any] = {}

        # 2) Actualizar persona (y registrar diferencias)
        if data.persona is not None:
            persona_data = data.persona.model_dump(exclude_unset=True)
            if cliente.persona is None:
                # Crear una nueva persona ligada al cliente
                persona = Persona(**persona_data)
                db.add(persona)
                cliente.persona = persona
                cambios["persona"] = {
                    "creado": persona_data
                }
            else:
                persona_cambios: dict[str, Any] = {}
                for field, value in persona_data.items():
                    old_value = getattr(cliente.persona, field)
                    if old_value != value:
                        persona_cambios[field] = {
                            "antes": old_value,
                            "despues": value,
                        }
                        setattr(cliente.persona, field, value)
                if persona_cambios:
                    cambios["persona"] = {
                        "actualizados": persona_cambios
                    }

        # helper genérico para colecciones 1–N, con registro de cambios
        def sync_collection(
            existing_list,
            incoming_list,
            id_attr: str,
            model_cls,
            key_hist: str,
        ):
            existing_by_id = {
                getattr(obj, id_attr): obj
                for obj in existing_list
                if getattr(obj, id_attr) is not None
            }

            result = []
            col_cambios = {
                "creados": [],
                "actualizados": [],
                "eliminados": [],
            }

            for item in incoming_list:
                payload = item.model_dump(exclude_unset=True)
                obj_id = payload.pop(id_attr, None)

                if obj_id is not None and obj_id in existing_by_id:
                    # UPDATE
                    obj = existing_by_id.pop(obj_id)
                    campos_cambiados = {}
                    for field, value in payload.items():
                        old_value = getattr(obj, field)
                        if old_value != value:
                            campos_cambiados[field] = {
                                "antes": old_value,
                                "despues": value,
                            }
                            setattr(obj, field, value)

                    if campos_cambiados:
                        col_cambios["actualizados"].append(
                            {
                                id_attr: obj_id,
                                "campos": campos_cambiados,
                            }
                        )

                else:
                    # INSERT
                    obj = model_cls(**payload, legajo=cliente.legajo)
                    db.add(obj)
                    col_cambios["creados"].append(
                        {
                            **payload,
                            id_attr: None,  # todavía no tiene ID
                        }
                    )

                result.append(obj)

            # DELETE: lo que quedó en existing_by_id no vino en el payload
            for obj in existing_by_id.values():
                col_cambios["eliminados"].append(
                    {
                        id_attr: getattr(obj, id_attr),
                    }
                )
                db.delete(obj)

            # Solo guardamos en cambios si hubo algo
            if (
                col_cambios["creados"]
                or col_cambios["actualizados"]
                or col_cambios["eliminados"]
            ):
                cambios[key_hist] = col_cambios

            return result

        # 3) Direcciones
        if data.direcciones is not None:
            cliente.direcciones = sync_collection(
                cliente.direcciones,
                data.direcciones,
                "id_direccion",
                DireccionCliente,
                "direcciones",
            )

        # 4) Teléfonos
        if data.telefonos is not None:
            cliente.telefonos = sync_collection(
                cliente.telefonos,
                data.telefonos,
                "id_telefono",
                TelefonoCliente,
                "telefonos",
            )

        # 5) Emails
        if data.emails is not None:
            cliente.emails = sync_collection(
                cliente.emails,
                data.emails,
                "id_mail",
                MailCliente,
                "emails",
            )

        # 6) Cuentas
        if data.cuentas is not None:
            cliente.cuentas = sync_collection(
                cliente.cuentas,
                data.cuentas,
                "id_cuenta",
                ClienteCuenta,
                "cuentas",
            )

        if cambios:
            try:
                registrar_evento_cliente(
                    db,
                    legajo=legajo,
                    codigo_evento=TipoEventoCodigoEnum.CLIENTE_ACTUALIZADO,
                    observacion="Datos del cliente actualizados",
                    datos=cambios,
                )
            except RuntimeError:
                pass

        db.commit()
        db.refresh(cliente)

        return ClienteDetalleOut.model_validate(cliente)
        


    



    
    
