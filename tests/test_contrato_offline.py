"""
Contrato de los payloads que manda la app Flutter, validados contra los
schemas Pydantic reales. Dos grupos:

1. Cola de sincronizacion offline (pago_repository.dart,
   pedido_repository.dart, visita_repository.dart) -- los JSON de esos son
   copia exacta de lo que paso el equipo de Flutter. Si cambian del lado
   del front, este archivo es el que hay que actualizar -- y viceversa: es
   el contrato escrito entre los dos repos, no una aproximacion.

2. Payloads "online" (llamadas directas, no encoladas) que tocan
   `id_empresa` -- agregado 2026-09-16 porque `ComboCreate.id_empresa`
   quedo sin arreglar en la primera pasada (solo se tocaron los 3 de la
   cola) y crear un combo empezo a dar 422 en cuanto el front dejo de
   mandarlo. **Ojo**: a diferencia del grupo 1, estos NO son copias
   literales de un payload real de Flutter -- no tengo acceso al repo del
   front para confirmar el JSON exacto. Son la reconstruccion minima
   valida contra el schema actual. Sirven para no repetir esta clase de
   regresion, pero conviene reemplazarlos por el payload literal cuando
   alguien del lado de Flutter lo pueda confirmar.

Nace de la revision cruzada del 2026-09-15: dos de los tres bugs bloqueantes
que encontro esa revision (id_empresa obligatorio en PagoCreate/PedidoCreate,
que rompia toda venta y todo cobro offline) los habria detectado un test
como este antes de llegar a produccion.

Actualizado 2026-09-15 (segunda revisión): `tipo_pago` dejó de ser un `str`
libre. `PagoCreate.tipo_pago` ahora es `Literal["COBRO_PEDIDO",
"PAGO_DEUDA"]` -- los dos únicos valores que un cliente puede elegir. La
decisión con el equipo de Flutter fue `PAGO_DEUDA` (un cobro sin pedido
asociado, la forma de este payload -- ver `TipoPago`/`TipoPagoCliente` en
`app/features/pagos/schemas.py` para el razonamiento completo). El valor
viejo que mandaba la tablet, `"cobro_reparto"`, nunca matcheaba ningún
tipo que la lógica de negocio reconocía (`COBRO_PEDIDO`, `PAGO_DEUDA`,
`EGRESO_EMPRESA`): el pago se creaba y aparecía en caja, pero no
descontaba deuda ni sumaba a la recaudación del reparto. Ahora ese valor
da 422 en el schema, antes de tocar ninguna lógica de negocio.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.features.pagos.schemas import PagoCreate
from app.features.pedidos.schemas.pedido import PedidoCreate
from app.features.repartos.visitas.schemas import VisitaCreate
from app.features.catalogo.combos.schemas.combo import ComboCreate
from app.features.repartos.camiones.schemas import CamionRepartoCreate

# ----------------------------------------------------------------------
# Payloads literales, tal como los arma la tablet.
#
# Ojo: NINGUNO manda id_empresa. Ese es justo el bug que se encontro: el
# front nunca lo mando, y el schema lo exigia. Si algun dia hay que
# volver a exigirlo, hay que coordinar el cambio con Flutter primero.
# ----------------------------------------------------------------------

PAGO_OFFLINE = {
    "client_uuid": "5b1f7e2a-2222-4a11-9c11-111111111111",
    "idempotency_key": "5b1f7e2a-2222-4a11-9c11-222222222222",
    "legajo": 1,
    "id_cuenta": 2,
    "id_repartodia": 3,
    "id_medio_pago": 1,
    "fecha": "2026-09-15T10:00:00",
    "monto": 100.0,
    "tipo_pago": "PAGO_DEUDA",
    "observacion": None,
}

PEDIDO_OFFLINE = {
    "client_uuid": "5b1f7e2a-3333-4a11-9c11-111111111111",
    "idempotency_key": "5b1f7e2a-3333-4a11-9c11-222222222222",
    "legajo": 1,
    "id_cuenta": 2,
    "id_repartodia": 3,
    "id_medio_pago": 1,
    "fecha": "2026-09-15T10:00:00",
    "monto_total": 100.0,
    "observacion": None,
    "items": [
        {"id_producto": 1, "id_combo": None, "cantidad": 2, "precio_unitario": 50.0}
    ],
}

VISITA_OFFLINE = {
    "client_uuid": "5b1f7e2a-4444-4a11-9c11-111111111111",
    "idempotency_key": "5b1f7e2a-4444-4a11-9c11-222222222222",
    "fecha": "2026-09-15T10:00:00",
    "estado": "cliente_compra",
    "id_repartodia": 3,
}


def test_pago_offline_valida_contra_pago_create():
    pago = PagoCreate.model_validate(PAGO_OFFLINE)
    assert pago.id_empresa is None
    assert pago.id_cuenta == 2
    assert pago.legajo == 1


def test_pedido_offline_valida_contra_pedido_create():
    pedido = PedidoCreate.model_validate(PEDIDO_OFFLINE)
    assert pedido.id_empresa is None
    assert pedido.id_cuenta == 2
    assert len(pedido.items) == 1


def test_visita_offline_valida_contra_visita_create():
    visita = VisitaCreate.model_validate(VISITA_OFFLINE)
    assert visita.estado == "cliente_compra"
    assert visita.id_repartodia == 3


def test_pago_offline_sin_id_empresa_no_falla():
    """Regresion puntual del bug bloqueante: esto daba 422 antes del fix."""
    payload = dict(PAGO_OFFLINE)
    assert "id_empresa" not in payload
    PagoCreate.model_validate(payload)  # no debe levantar ValidationError


def test_pedido_offline_sin_id_empresa_no_falla():
    payload = dict(PEDIDO_OFFLINE)
    assert "id_empresa" not in payload
    PedidoCreate.model_validate(payload)  # no debe levantar ValidationError


def test_pago_create_todavia_exige_id_medio_pago():
    """Contraparte: el fix no aflojo de mas. Sigue exigiendo lo que debe."""
    payload = dict(PAGO_OFFLINE)
    del payload["id_medio_pago"]
    with pytest.raises(ValidationError):
        PagoCreate.model_validate(payload)


def test_tipo_pago_viejo_de_la_tablet_ahora_da_422():
    """Regresion puntual: "cobro_reparto" (el valor que mandaba la tablet
    antes de la decision de usar PAGO_DEUDA) ya no pasa la validacion.
    Antes de este fix, este mismo payload daba 200 y creaba un pago que no
    impactaba ni la cuenta del cliente ni la recaudacion del reparto."""
    payload = dict(PAGO_OFFLINE, tipo_pago="cobro_reparto")
    with pytest.raises(ValidationError):
        PagoCreate.model_validate(payload)


def test_tipo_pago_cobro_pedido_tambien_es_valido():
    """El otro valor que un cliente puede elegir (pago atado a un pedido)."""
    payload = dict(PAGO_OFFLINE, tipo_pago="COBRO_PEDIDO")
    PagoCreate.model_validate(payload)


# ----------------------------------------------------------------------
# Payloads online (no offline-sync) que tocan id_empresa.
#
# Reconstruccion minima valida contra el schema, no copia literal del
# front (ver nota en el docstring del modulo).
# ----------------------------------------------------------------------

COMBO_ONLINE = {
    "nombre": "Combo docena",
    "descripcion": None,
    "estado": True,
    "productos": [],
}

CAMION_ONLINE = {
    "patente": "AB123CD",
    "activo": True,
}


def test_combo_sin_id_empresa_no_falla():
    """Regresion puntual: ComboCreate.id_empresa quedo sin arreglar en la
    primera pasada del fix de id_empresa (solo se tocaron los 3 payloads
    de la cola offline) y crear un combo empezo a dar 422 en cuanto el
    front dejo de mandarlo."""
    assert "id_empresa" not in COMBO_ONLINE
    combo = ComboCreate.model_validate(COMBO_ONLINE)
    assert combo.id_empresa is None


def test_camion_sin_id_empresa_no_falla():
    assert "id_empresa" not in CAMION_ONLINE
    camion = CamionRepartoCreate.model_validate(CAMION_ONLINE)
    assert camion.id_empresa is None
