from sqlalchemy import func, select, delete, update
from sqlalchemy.orm import Session, joinedload, selectinload
from fastapi import HTTPException
from typing import Any, Optional


#Modelos utilizados
from app.models.cliente import Cliente
from app.models.persona import Persona
from app.models.direccionCliente import DireccionCliente
from app.models.telefonoCliente import TelefonoCliente
from app.models.emailCliente import MailCliente
from app.models.clienteCuenta import ClienteCuenta
from app.models.clienteDiaSemana import ClienteDiaSemana

#Schemas utilizados
from app.schemas.clienteDetalle import ClienteDetalleOut, ClienteDetalleUpdate

#Utilizados para guardar un historico del cliente
from app.services.historicoService import registrar_evento_cliente
from app.schemas.enumsHistorico import TipoEventoCodigoEnum



class ClienteService:

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
            raise HTTPException(status_code=404, detail="Cliente no encontrado")
        
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
            raise HTTPException(status_code=404, detail="Cliente no encontrado")

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
        


    
# ================= ORDENAMIENTO =================

def normalizar_orden(
    db: Session,
    *,
    id_dia: int,
    turno: Optional[str],
):
    filas = db.execute(
        select(
            ClienteDiaSemana.id_cliente
        )
        .where(
            ClienteDiaSemana.id_dia == id_dia,
            ClienteDiaSemana.turno_visita == turno,
        )
        .order_by(ClienteDiaSemana.orden)
        .with_for_update()
    ).scalars().all()

    for idx, id_cliente in enumerate(filas, start=1):
        db.execute(
            update(ClienteDiaSemana)
            .where(
                ClienteDiaSemana.id_dia == id_dia,
                ClienteDiaSemana.turno_visita == turno,
                ClienteDiaSemana.id_cliente == id_cliente,
            )
            .values(orden=idx)
        )

    
def calcular_orden(
    db: Session,
    *,
    id_dia: int,
    turno: Optional[str],
    posicion: str,
    despues_de_legajo: Optional[int],
) -> int:

    # 🔒 BLOQUEO + NORMALIZACIÓN
    normalizar_orden(db, id_dia=id_dia, turno=turno)

    if posicion == "inicio":
        db.execute(
            update(ClienteDiaSemana)
            .where(
                ClienteDiaSemana.id_dia == id_dia,
                ClienteDiaSemana.turno_visita == turno,
            )
            .values(orden=ClienteDiaSemana.orden + 1)
        )
        return 1

    if posicion == "despues":
        if not despues_de_legajo:
            raise HTTPException(400, "Falta despues_de_legajo")

        orden_ref = db.execute(
            select(ClienteDiaSemana.orden)
            .where(
                ClienteDiaSemana.id_dia == id_dia,
                ClienteDiaSemana.turno_visita == turno,
                ClienteDiaSemana.id_cliente == despues_de_legajo,
            )
            .with_for_update()
        ).scalar_one()

        db.execute(
            update(ClienteDiaSemana)
            .where(
                ClienteDiaSemana.id_dia == id_dia,
                ClienteDiaSemana.turno_visita == turno,
                ClienteDiaSemana.orden > orden_ref,
            )
            .values(orden=ClienteDiaSemana.orden + 1)
        )

        return orden_ref + 1

    # final
    max_orden = db.execute(
        select(func.coalesce(func.max(ClienteDiaSemana.orden), 0))
        .where(
            ClienteDiaSemana.id_dia == id_dia,
            ClienteDiaSemana.turno_visita == turno,
        )
    ).scalar_one()

    return max_orden + 1



    
    
