from fastapi import APIRouter, Depends, HTTPException, status,Query
from app.core.security import get_current_user
from typing import List, Dict, Optional
from sqlalchemy import update, func
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import and_
from app.core.database import get_db
from app.models.cliente import Cliente
from app.models.persona import Persona
from app.models.direccionCliente import DireccionCliente
from app.models.telefonoCliente import TelefonoCliente
from app.models.emailCliente import MailCliente
from app.models.clienteDiaSemana import ClienteDiaSemana
from app.models.diaSemana import DiaSemana
from sqlalchemy import select
from app.schemas.cliente import (
    ClienteCreate,
    ClienteOut,
    ClienteUpdate,
    ClienteListOut,
)
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.services.clienteService import ClienteService
from app.schemas.clienteDetalle import ClienteDetalleOut, ClienteDetalleUpdate

#Para que se cree una cuenta de forma automatica un vez creado el cliente. hay que pasarlo a un service.
from app.models.clienteCuenta import ClienteCuenta
from app.schemas.clienteCuenta import ClienteCuentaCreate


#--------------------- pasarlo a logica de servicio ---------------------





#------------------------------------EMMA------------------------------------------------
from app.models.historico import Historico
from app.schemas.historico import HistoricoOut
from app.models.pedido import Pedido
from app.schemas.pedido import PedidoOutCorto
from app.models.productoCliente import ProductoCliente
from app.models.producto import Producto
from app.schemas.productoCliente import (
    ProductoClienteOut,
    ProductoClienteUpsert,
    ProductoClientePatch,
)
#------------------------------------EMMA------------------------------------------------


# --------------------- pasarlo a logica de servicio ---------------------


router = APIRouter(prefix="/clientes", tags=["Clientes"],dependencies=[Depends(get_current_user)],)

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
    turno_val: Optional[str],  # "manana"|"tarde"|"noche"|None
    posicion: str,  # "inicio"|"final"|"despues"
    despues_de_legajo: Optional[int] = None,
) -> int:
    """
    Devuelve el orden a asignar al nuevo registro y corre los existentes de ser necesario.
    Bloquea el conjunto (día/turno) para evitar carreras.
    """
    # Filtro base por día y turno (permitiendo NULL)
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
        # Todos +1, nuevo en 1
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
        raise HTTPException(
            status_code=400,
            detail="Falta 'despues_de_legajo' para posicion='despues'."
        )

    ref_orden = db.execute(
        select(ClienteDiaSemana.orden).where(
            and_(filtro_base, ClienteDiaSemana.id_cliente == despues_de_legajo)
        )
    ).scalar_one_or_none()

    if ref_orden is None:
        raise HTTPException(
            status_code=404,
            detail="Cliente de referencia no existe en ese día/turno."
        )

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




@router.post("/", response_model=ClienteDetalleOut, status_code=status.HTTP_201_CREATED)
def CrearCliente(payload: ClienteCreate, db: Session = Depends(get_db)):
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
                raise HTTPException(
                    status_code=404,
                    detail="La persona (dni) no existe. Enviá 'persona' para crearla.",
                )

        # 2) Duplicado por empresa
        existe = (
            db.query(Cliente)
            .filter(and_(Cliente.dni == dni_final, Cliente.id_empresa == 1))
            .first()
        )
        if existe:
            raise HTTPException(
                status_code=409,
                detail="Ya existe un cliente para ese DNI en esta empresa.",
            )

        # 3) Crear cliente
        nuevo = Cliente(id_empresa=1, observacion=payload.observacion)
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
                    raise HTTPException(
                        status_code=400, detail=f"Día no encontrado: {f.dia.value}"
                    )

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
                    raise HTTPException(
                        status_code=400, detail=f"Día no encontrado: {dia.value}"
                    )

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
        # Si querés, refrescás por si luego usás la cuenta:
        db.refresh(cuenta)
        
        return ClienteService.get_detalle_cliente(db, nuevo.legajo)

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creando cliente: {e}")

# Get masivo que trae todo lo relacionado al cliente mediante el legajo.
@router.get(
    "/{legajo}/detalle",
    response_model=ClienteDetalleOut,
    status_code=status.HTTP_200_OK,
)
def ObtenerDetalleCliente(legajo: int, db: Session = Depends(get_db)):
    return ClienteService.get_detalle_cliente(db, legajo)

@router.get("/", response_model=List[ClienteListOut], status_code=status.HTTP_200_OK)
def ListarClientes(db: Session = Depends(get_db)):
    clientes = (
        db.query(Cliente)
        .options(
            selectinload(Cliente.persona),
            selectinload(Cliente.telefonos),
        )
        .filter(Cliente.id_empresa == 1)
        .all()
    )
    return clientes

@router.put("/{legajo}", response_model=ClienteOut)
def ActualizarCliente(
    legajo: int, payload: ClienteUpdate, db: Session = Depends(get_db)
):
    try:
        cliente = db.get(Cliente, legajo)
        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")

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
                raise HTTPException(
                    status_code=409,
                    detail="Inconsistencia: el cliente no tiene persona asociada.",
                )
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

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error actualizando cliente: {e}") 
    


#Nuevo put que actualiza todo lo relacionado al cliente.
@router.put("/{legajo}/detalle", response_model=ClienteDetalleOut)
def update_cliente_detalle(
    legajo: int,
    payload: ClienteDetalleUpdate,
    db: Session = Depends(get_db),
):
    return ClienteService.update_detalle_cliente(db, legajo, payload)

@router.delete("/{legajo}", status_code=status.HTTP_204_NO_CONTENT)
def BorrarCliente(legajo: int, db: Session = Depends(get_db)):
    try:
        cliente = db.get(Cliente, legajo)
        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")
        db.delete(cliente)
        db.commit()
        return None
    except Exception as e:
        db.rollback()
        # Si hay FKs (pedidos, usuarios, etc.) puede fallar por restricción
        raise HTTPException(
            status_code=409,
            detail=f"No se pudo eliminar el cliente (referencias activas): {e}",
        )
    

#------------------------------------EMMA------------------------------------------------
@router.get(
    "/{legajo}/historicos",
    response_model=List[HistoricoOut],
    status_code=status.HTTP_200_OK,
)
def listar_historico_cliente(
    legajo: int,
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    # validar que exista el cliente
    cliente = db.get(Cliente, legajo)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    stmt = (
        select(Historico)
        .where(Historico.legajo == legajo)
        .order_by(Historico.fecha.desc())
        .limit(limit)
        .options(selectinload(Historico.tipo_evento))   # si querés el nombre del evento
    )
    rows = db.execute(stmt).scalars().all()

    # si usás evento como string, convertí aquí:
    # por ahora dejamos HistoricoOut.from_orm que tomará evento como __str__ si definís __repr__/__str__
    return [HistoricoOut.model_validate(h) for h in rows]

@router.get(
    "/{legajo}/pedidos",
    response_model=List[PedidoOutCorto],
    status_code=status.HTTP_200_OK,
)
def listar_pedidos_cliente(
    legajo: int,
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    # validar que exista el cliente
    cliente = db.get(Cliente, legajo)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    stmt = (
        select(Pedido)
        .where(Pedido.legajo == legajo)
        .order_by(Pedido.fecha.desc())
        .limit(limit)
    )
    rows = db.execute(stmt).scalars().all()
    return [PedidoOutCorto.model_validate(p) for p in rows]

#------------------------------------EMMA------------------------------------------------

@router.get(
    "/{legajo}/productos",
    response_model=List[ProductoClienteOut],
    status_code=status.HTTP_200_OK,
)
def listar_productos_cliente(legajo: int, db: Session = Depends(get_db)):
    cliente = db.get(Cliente, legajo)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    from sqlalchemy.orm import joinedload as jl
    stmt = (
        select(ProductoCliente)
        .where(ProductoCliente.legajo == legajo)
        .options(jl(ProductoCliente.producto))
    )
    rows = db.execute(stmt).scalars().all()
    return [ProductoClienteOut.model_validate(r) for r in rows]


def _get_producto_cliente_con_producto(db: Session, legajo: int, id_producto: int) -> ProductoCliente:
    """Recarga el producto_cliente con la relación producto (para el response)."""
    from sqlalchemy.orm import joinedload as jl
    return db.execute(
        select(ProductoCliente)
        .where(
            ProductoCliente.legajo == legajo,
            ProductoCliente.id_producto == id_producto,
        )
        .options(jl(ProductoCliente.producto))
    ).scalar_one()


@router.put(
    "/{legajo}/productos/{id_producto}",
    response_model=ProductoClienteOut,
    status_code=status.HTTP_200_OK,
)
def upsert_producto_cliente(
    legajo: int,
    id_producto: int,
    payload: ProductoClienteUpsert,
    db: Session = Depends(get_db),
):
    """
    Crea o reemplaza por completo el producto del cliente (PUT idempotente).
    Si no existía la fila, la crea; si existía, sobreescribe todos los campos.
    """
    if not db.get(Cliente, legajo):
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    if not db.get(Producto, id_producto):
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    fila = db.get(ProductoCliente, {"legajo": legajo, "id_producto": id_producto})
    if fila is None:
        fila = ProductoCliente(legajo=legajo, id_producto=id_producto)
        db.add(fila)

    fila.cantidad = payload.cantidad
    fila.estado = payload.estado
    fila.fecha_entrega = payload.fecha_entrega

    db.commit()
    return _get_producto_cliente_con_producto(db, legajo, id_producto)


@router.patch(
    "/{legajo}/productos/{id_producto}",
    response_model=ProductoClienteOut,
    status_code=status.HTTP_200_OK,
)
def actualizar_producto_cliente(
    legajo: int,
    id_producto: int,
    payload: ProductoClientePatch,
    db: Session = Depends(get_db),
):
    """
    Actualiza parcialmente el producto del cliente (PATCH).
    Solo modifica los campos enviados; la fila debe existir (404 si no).
    """
    fila = db.get(ProductoCliente, {"legajo": legajo, "id_producto": id_producto})
    if fila is None:
        raise HTTPException(
            status_code=404,
            detail="El cliente no tiene ese producto asignado.",
        )

    cambios = payload.model_dump(exclude_unset=True)
    if not cambios:
        raise HTTPException(status_code=422, detail="No se enviaron campos para actualizar.")

    for campo, valor in cambios.items():
        setattr(fila, campo, valor)

    db.commit()
    return _get_producto_cliente_con_producto(db, legajo, id_producto)



