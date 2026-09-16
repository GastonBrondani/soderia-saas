# Contexto de la migración

Este archivo es la fuente de verdad del trabajo en curso. Leelo entero antes
de tocar nada.

---

## Estado actual

**Los pasos 0, 1 y 2 están hechos**, y el paso 3 (limpieza) tuvo una primera
tanda grande ya cerrada — ver el detalle de cada uno más abajo y la "Deuda
técnica conocida". Lo que sigue abierto son los ítems de esa sección y los
que vaya agregando cada revisión cruzada con el frontend.

El material original de la migración (los archivos de `core/`, `db/`, los
scripts y los tests) vino de un scaffold armado aparte en
`../soderia-saas-scaffold/`. Ya no hace falta: todo lo que aportaba está
copiado y evolucionado en este repo.

---

## Qué es este repo

Backend FastAPI + SQLAlchemy + PostgreSQL de un sistema de gestión para una
sodería: clientes, cuentas corrientes, pedidos, pagos, caja, stock, envases
retornables, repartos diarios y comprobantes en PDF. El frontend es una app
Flutter (web y tablet) que trabaja **offline** y sincroniza después, así que
hay endpoints de bootstrap y manejo de idempotencia en pagos.

Está andando en producción para **un** cliente.

## Qué estamos haciendo

Convertirlo en un producto multi-cliente (SaaS). Dos cambios grandes:

1. **Aislamiento por sodería: una base de datos por cliente.** Ya está
   decidido, no lo re-discutas. El tenant se resuelve por subdominio o por
   el header `X-Tenant`, y una base de control (`soderia_control`) registra
   qué soderías existen y dónde vive la base de cada una.
2. **Reorganizar de capas técnicas a features.** Hoy es
   `app/models/`, `app/routers/`, `app/services/`, `app/schemas/`. Va a ser
   `app/features/<dominio>/` con todo junto adentro.

## Los tres pasos, en orden

El orden no es negociable. Cada paso se termina y se commitea antes de
empezar el siguiente.

### Paso 0 — Red de seguridad (HECHO, 2026-09-14)

Se corre sobre el código **sin modificar**. Copiar
`../soderia-saas-scaffold/scripts/snapshot_openapi.py` a `scripts/` y
ejecutarlo. Genera `tests/snapshots/openapi_baseline.json`: una foto del
contrato de la API.

Después, `tests/test_api_contract.py` compara contra esa foto y detecta
rutas que desaparecieron, parámetros que cambiaron, campos caídos de una
respuesta y endpoints que perdieron autenticación.

La salida del script también lista las rutas duplicadas y los endpoints sin
autenticación que hay hoy. Hay que leerla y pegarla en la sección "Deuda
técnica conocida" de este archivo.

Commit propio: `paso 0: snapshot del contrato de la API`.

**A partir de acá, este test tiene que estar en verde antes y después de
cada paso.**

### Paso 1 — Núcleo multi-tenant (HECHO, 2026-09-14)

Copiado desde `../soderia-saas-scaffold/`: todo `app/core/`, todo `app/db/`,
`app/main.py`, `alembic/env.py`, `scripts/`, `tests/`, `.env.example`,
`requirements.txt`, `Makefile`. `README.md` ya estaba (identico al del
scaffold). Varios de esos **reemplazaron** archivos existentes (`database.py`,
`security.py`, `scheduler.py`, `main.py`, `alembic/env.py`): es lo esperado.

**`app/core/settings.py` NO se borró.** El scaffold no tiene reemplazo para
`COMPROBANTES_BASE_PATH`/`COMPROBANTES_BASE_URL`, que siguen usando
`comprobantePedidoService.py` y `comprobantePagoService.py` (el equivalente
nuevo es `core/storage.py`, una abstracción distinta con carpeta por tenant).
Migrar esos dos services es tocar lógica real, así que queda para el paso 3.
Mientras tanto, `settings.py` llama su propio `load_dotenv()` porque el
`database.py` nuevo ya no lo hace por él.

Ajustes a mano, terminaron siendo más de los 3 que preveía este archivo:

1. `app/routers/auth.py`: se sacó la función local `create_access_token`
   (ahora está en `core/security.py`), se importa de ahí y se le pasa
   `tenant_codigo=tenant_actual().codigo` en las dos llamadas. También se
   agregó el rehash automático de contraseñas viejas (`necesita_rehash`).
2. Los imports de `require_roles` y `require_admin` (en `pago.py` y
   `clienteCuenta.py`) pasaron de `app.core.security` a `app.core.permissions`.
3. **Nuevo, no estaba anotado:** `core/security.py`, en `get_current_user`,
   traía `from app.features.usuarios.models import Usuario` — ruta que recién
   existe después del paso 2. Se apuntó a `app.models.usuario` (ubicación
   actual) con un comentario `TODO migracion paso 2`; el script de ese paso
   debería reescribirlo solo al mover el modelo.
4. **Nuevo, no estaba anotado:** el `scheduler.py` nuevo asumía que
   `crear_repartos_del_dia_automaticos` y `ensure_usuario_sis` ya vivían en
   `app/features/repartos/repartos_dia/service.py`. Esa lógica vivía inline
   en el `core/scheduler.py` viejo (nunca se había extraído a un service).
   Se movió tal cual a `app/services/repartosSchedulerService.py` (sin
   cambiar una línea de lógica) y se actualizó el import del scheduler.
5. **Bug nuevo encontrado y arreglado, no de la migración:** en
   `core/scheduler.py`, `_sincronizar_jobs()` borraba el job
   `repartos:arranque` (el catch-up de repartos faltantes al iniciar, una
   sola vez a los 10s) porque corre primero, a los 5s, y su filtro trata
   cualquier `repartos:*` que no sea una zona horaria conocida como job
   huérfano. Se agregó una excepción explícita para ese id. Verificado: sin
   el fix, el catch-up nunca llegaba a dispararse; con el fix, corre (y en el
   tenant demo falla porque no tiene usuario `sis`, esperado).
6. Los `id_empresa` por query param **se dejan como están**. Se limpian en
   el paso 3.

`.env` armado a partir de `.env.example` (agregado un bloque para los dos
`COMPROBANTES_PEDIDOS_*` legacy), con `SECRET_KEY` generada. El Postgres de
`.env.local` (puerto 5433, contenedor `soderia_db` de otro trabajo) no
aceptó esas credenciales, así que se levantó un Postgres nuevo y limpio
(`docker run postgres:17`, puerto 5434, `postgres`/`postgres`) solo para este
entorno. Control plane inicializado, tenant `demo` dado de alta con
`scripts/crear_tenant.py` (contraseña de `admin` no guardada en ningún
archivo, se mostró una sola vez).

`tests/test_api_contract.py::test_sin_rutas_duplicadas` es un test nuevo que
falla por los 3 duplicados de la Deuda técnica de abajo. Se marcó
`xfail(strict=True)` referenciando esta sección, en vez de arreglar los
duplicados fuera del paso 3.

Verificación hecha: `/health` (200, visible en el schema — se le sacó un
`include_in_schema=False` que el `main.py` nuevo le agregaba de más y que
tumbaba `test_no_desaparecieron_operaciones`), `/health/ready` (`ready`),
`X-Tenant: demo` sin token (401), login devuelve token con el claim `ten`.
`pytest tests/` en verde (6 passed, 2 skipped esperando el paso 2, 1 xfailed).

Commit propio: `paso 1: nucleo multi-tenant`.

Archivos que aporta este paso:

| archivo                                               | qué hace                                                           |
| ----------------------------------------------------- | ------------------------------------------------------------------ |
| `core/config.py`                                      | configuración con pydantic-settings, validada al arrancar          |
| `core/control_plane.py`                               | registro de soderías; engine perezoso                              |
| `core/tenancy.py`                                     | resuelve el tenant por subdominio/header, ContextVar + middleware  |
| `core/database.py`                                    | caché LRU de engines, uno por sodería (reemplaza el engine global) |
| `core/security.py`                                    | hashing + JWT con claim `ten`                                      |
| `core/permissions.py`                                 | `require_roles`, `require_admin` (salieron de security)            |
| `core/storage.py`                                     | archivos aislados por sodería                                      |
| `core/exceptions.py`                                  | errores de dominio + handlers globales                             |
| `core/scheduler.py`                                   | jobs por tenant con advisory lock de Postgres                      |
| `core/logging.py`                                     | logs con tenant y request id                                       |
| `db/base.py`, `db/mixins.py`, `db/models_registry.py` | soporte de modelos                                                 |

Scripts: `crear_tenant.py` (alta completa de una sodería),
`migrate_all_tenants.py` (Alembic sobre todas las bases),
`snapshot_openapi.py`, `migrar_estructura.py`.

### Paso 2 — Mover a features

Lo hace `scripts/migrar_estructura.py`. **No muevas archivos a mano.**

```bash
python scripts/migrar_estructura.py --dry-run   # plan + archivos sin asignar
python scripts/migrar_estructura.py             # ejecutar
```

El script mueve con `git mv` (preserva historial), renombra a snake_case,
reescribe imports resolviendo los agregados con AST, y genera los
`__init__.py`, el `models_registry.py` y el `api/router.py`.

Si lista archivos sin asignar: agregalos al diccionario `ASIGNACION` dentro
del script y volvé a correr el dry-run. **No inventes destinos**: si un
archivo va al feature equivocado se descubre semanas después.

Este paso **no cambia una sola línea de lógica**. Solo mueve archivos y
ajusta imports.

**HECHO, 2026-09-14.** 141 archivos movidos (los 136 originales + los 5 que
faltaban en `ASIGNACION`: `clienteDetalle`→clientes, `stockDetalle`→
inventario/stock, `enums_cliente`→clientes, `enumsStock`→
inventario/movimientos, `repartosScheduler`→repartos/repartos_dia — esto
último decidido con el usuario porque el script no tiene noción de
`app/shared/`, ver Deuda técnica). De paso se encontraron dos bugs en el
propio script, arreglados a mano después de mover:

1. `app/db/base.py` quedó con `from app.db.base import Base` (auto-import,
   circular). El rewriter de imports no distingue este archivo puente del
   resto: reescribe *cualquier* `from app.core.database import Base`,
   incluido el suyo propio. Se volvió a `from app.core.database import Base`.
2. `app/features/catalogo/combos/router.py` tenía
   `from app.services import comboService` (import de submódulo como
   namespace, no de un símbolo). El rewriter solo resuelve
   `from app.X import simbolo`, no este patrón. Se cambió a
   `from app.features.catalogo.combos import service as comboService`.

Manual, como indica el propio script al terminar: `get_cliente_or_404_dep`
se movió de `app/api/deps.py` a `app/features/clientes/dependencies.py`
(único contenido del archivo); `app/api/deps.py` se borró. Carpetas viejas
(`app/models`, `app/routers`, `app/services`, `app/schemas`) borradas,
quedaron vacías. Verificado: `pytest tests/` en verde (8 passed, 1 xfailed
— ya no hay skipped, `app/features` existe y `test_models_registry.py`
corre de verdad), `import app.main` sin errores, y en vivo: login +
`/empresas/` + `/clientes/` con token devuelven 200.

Commit propio: `paso 2: mover a estructura por features`.

### Paso 3 — Limpieza, un feature por commit

Recién acá se toca comportamiento. Ver "Deuda técnica conocida" abajo.

---

## Estructura destino

```
app/
├── main.py
├── api/router.py              generado por el script
├── core/                      config, database, security, tenancy, ...
├── shared/                    pagination, enums, utils
├── db/                        base, mixins, models_registry
└── features/
    ├── auth/  usuarios/  personas/  empresas/  empleados/  maestros/
    ├── clientes/
    ├── catalogo/{productos,combos,servicios,listas_precios}/
    ├── inventario/{stock,movimientos,envases}/
    ├── pedidos/  pagos/  caja/
    ├── repartos/{agenda,camiones,recorridos,repartos_dia,visitas}/
    ├── sincronizacion/        bootstrap offline
    ├── documentos/  auditoria/  reportes/
```

Contrato de cada feature: `router.py`, `schemas.py`, `models/`,
`repository.py`, `service.py`, `dependencies.py`, `exceptions.py`.
Si algo pasa de ~200 líneas, se convierte en paquete.

`service.py` para reglas de un solo agregado. `use_cases/` solo cuando se
orquestan varios en una transacción (confirmar pedido toca stock, cuenta,
caja y envases: ese sí).

---

## Deuda técnica conocida

Esta lista es **preliminar**: sale de una revisión parcial del código, no de
un barrido completo. Cuando corras el paso 0, la salida de
`snapshot_openapi.py` te va a dar las rutas duplicadas y los endpoints sin
autenticación reales. Actualizá esta sección con esos datos.

**No arregles nada de esto fuera del paso 3**, y no mezcles estos arreglos
con movimientos de archivos.

**Bugs criticos de pérdida silenciosa de datos, encontrados por los tests
de integración del punto 7 (2026-09-15).** Esto es lo más serio que salió
de toda la revisión cruzada: tres endpoints devolvían 200 (o, en un caso,
directamente reventaban) sin persistir nada, y ningún test lo detectaba
porque ninguno pegaba contra un Postgres real end-to-end.

- ~~`POST /pagos` (`crear_pago`) nunca commiteaba.~~ **Arreglado.**
  `PagoService.crear()` intenta detectar si "ya está anidado" en la
  transacción de otro caller con `started_tx = not db.in_transaction()`, y
  si es así usa `nullcontext()` en vez de `db.begin()` (para no commitear
  antes de tiempo si lo llama `pedidos/service.py::crear_pedido`, que sí
  commitea al final). El problema: `get_current_user` ya hace
  `db.get(Usuario, ...)` sobre la misma sesión antes de que el handler
  corra (FastAPI cachea `Depends(get_db)` por request), así que
  `db.in_transaction()` es casi siempre `True` **aunque no haya ningún
  caller anidado real**. `crear_pago` no tenía ningún `db.commit()` propio
  confiando en que el service lo resolvía solo. Resultado: el pago se
  creaba, se devolvía 200 con un `id_pago` real, y desaparecía en silencio
  al cerrarse la sesión — exactamente el endpoint que usa
  `_syncPago` de la cola offline. Arreglo: `crear_pago` ahora hace
  `db.commit()` + `db.refresh()` explícito, igual que ya hacían
  `crear_ingreso`/`crear_egreso`. `PagoService.crear()` no se tocó (sigue
  sirviendo bien al caso anidado real de `crear_pedido`), pero quedó
  documentado en el propio método que el caller es responsable de
  commitear.
- ~~`POST /pagos/cancelar-deuda` (`cancelar_deuda`) fallaba siempre que se
  llamaba autenticado de verdad.~~ **Arreglado.** Mismo problema de fondo,
  peor síntoma: esta función envolvía todo su cuerpo en
  `with db.begin():`. Por la misma razón de arriba (`get_current_user` ya
  autobegin-ea la sesión), ese `db.begin()` explícito chocaba con la
  transacción ya iniciada y tiraba `InvalidRequestError: A transaction is
  already begun on this Session` — capturado como `SQLAlchemyError` y
  relanzado, es decir, **este endpoint no funcionaba nunca** en uso real
  (solo "andaba" en una llamada manual con sesión nueva, como una prueba
  aislada sin pasar por `get_current_user`). Arreglo: se sacó el
  `with db.begin():`, se dejó el cuerpo con `try/except` plano y
  `db.commit()` explícito al final (mismo patrón que
  `crear_pedido`, en el mismo archivo).
- ~~`RecorridoService.abrir_recorrido` con `detalle_stock_inicial` vacío
  perdía el recorrido.~~ **Arreglado.** El comentario del código decía "el
  último `ajustar_stock` ya hizo commit" — cierto si hay al menos un ítem,
  falso si la lista viene vacía (el `for` nunca corre). Se agregó un
  `db.commit()` explícito después del loop, sin depender de que haya
  ítems.

Los tres se encontraron con `tests/test_multi_tenant.py`, que crea
soderías de prueba de verdad contra Postgres y pega HTTP autenticado de
punta a punta — exactamente el tipo de test que "es una sesión nueva, sin
`get_current_user` de por medio" que las pruebas manuales anteriores en
este documento (con `usar_tenant()`/`sesion_tenant()` directo) no
reproducían. Ojo con este patrón en cualquier código nuevo: **una sesión
recién creada por `get_db()` casi nunca llega "limpia" a tu service**, la
comparten todas las `Depends()` del request. No asumas `started_tx`/
`in_transaction()` como señal confiable de si sos el primero en tocar la
sesión; y no envuelvas un service en `with db.begin():` si en algún
momento puede correr detrás de `get_current_user` (o sea, siempre).

**Rompen el contrato de la API** (coordinar con Flutter antes):

- ~~`id_empresa: Optional[int]/int = Query(...)` en `caja/router.py` (4
  endpoints), `catalogo/router.py` (bootstrap), `inventario/stock/router.py`
  (3 endpoints) y `repartos_dia/routers/reparto_dia.py` (3 endpoints).~~
  **Arreglado (2026-09-15).** Frontend confirmó que no existe (ni está
  planeado) el concepto de sucursal — cada sodería tiene una sola empresa.
  Se sacó el query param de los GET/PUT y se agregó
  `EmpresaService.get_id_empresa_actual(db)`
  (`app/features/empresas/service.py`) que la infiere de la base del tenant
  actual. ~~El `POST /repartos-dia/` que recibe `id_empresa` en el body
  no se tocó (no estaba en el pedido de Flutter).~~ Contrato regenerado
  (`python scripts/snapshot_openapi.py --salida tests/snapshots/openapi_baseline.json`);
  el único cambio visible para el cliente es que esos parámetros ya no
  existen (si los sigue mandando, FastAPI los ignora por no estar declarados).
  **Corregido (2026-09-15), revisión cruzada con el front:** ese "no
  tocado" era un error de alcance. El pedido de Flutter miró los GET; el
  cliente que manda **bodies** con `id_empresa` es el de sincronización
  offline (`PagoCreate`, `PedidoCreate`, `POST /repartos-dia/`), y ese
  nunca mandó `id_empresa` — por eso `pago_repository.dart` y
  `pedido_repository.dart` daban 422 (`id_empresa: Field required`) en
  **toda** venta y todo cobro hechos desde `venta_screen.dart`, que pasa
  siempre por la cola offline. Se aplicó el mismo criterio que a los GET:
  - `PagoCreate.id_empresa` y `PagoLibreIn.id_empresa`: `int` obligatorio →
    `Optional[int] = None`. El router (`crear_pago`, `crear_pago_libre`)
    ignora el valor si llega y usa `EmpresaService.get_id_empresa_actual(db)`
    siempre.
  - `PedidoBase.id_empresa`: `int = 1` hardcodeado → `Optional[int] = None`.
    `PedidoCreate` ya no lo redeclara obligatorio. `PedidoService.crear_pedido`
    excluye `id_empresa` del `model_dump()` y lo resuelve con
    `EmpresaService.get_id_empresa_actual(db)`.
  - `RepartoDiaBase.id_empresa`: `int = 1` → `Optional[int] = None`;
    `crear_reparto_dia` ya resolvía mal el valor del cliente, ahora usa
    `EmpresaService.get_id_empresa_actual(db)`.
  - Ninguno de los tres confía en el `id_empresa` del cliente aunque lo
    mande: siempre se ignora y se infiere del tenant, igual que en los GET.
  Contrato regenerado de nuevo (cambia el body esperado de `POST /pagos`,
  `POST /pagos/libre` y `POST /pedidos/`). Verificado en vivo contra el
  tenant `demo`: un pago con `id_cuenta` y sin `id_empresa` baja la deuda
  de la cuenta correcta.

  ~~De paso, un bug real encontrado (no reportado por el front):
  `pago_repository.dart` manda `tipo_pago: "cobro_reparto"`, que no
  matchea ninguno de los valores que `PagoService.crear` reconoce
  (`COBRO_PEDIDO`, `PAGO_DEUDA`, `EGRESO_EMPRESA`) para impactar la cuenta
  del cliente y la recaudación del reparto. Con ese valor, el pago se
  crea y aparece en caja, pero no descuenta deuda ni suma a la
  recaudación del reparto — falla en silencio. `tipo_pago` es texto libre
  (`str`, sin enum) del lado del backend.~~ **Decidido y arreglado
  (2026-09-15, segunda revisión cruzada).** El valor correcto es
  `PAGO_DEUDA`, no `COBRO_PEDIDO`: el payload de pago offline no lleva
  `id_pedido` (lleva `legajo` + `id_cuenta` + `id_repartodia`), es la
  forma de un cobro de cuenta sin pedido asociado — la misma que usa
  `cancelar_deuda` (`pedidos/service.py:669`), no la de
  `pedidos/service.py:346` (que sí tiene un pedido detrás). Y no se agregó
  `cobro_reparto` como alias: eso es lo que originó el bug (dos nombres
  para lo mismo). En cambio, `tipo_pago` pasó a ser un enum real
  (`TipoPago` en `app/features/pagos/schemas.py`, con los 5 valores que
  usa el código: `COBRO_PEDIDO`, `PAGO_DEUDA`, `INGRESO_EMPRESA`,
  `EGRESO_EMPRESA`, `SERVICIO`); `PagoCreate.tipo_pago` — lo único que un
  cliente puede mandar — quedó restringido a
  `Literal["COBRO_PEDIDO", "PAGO_DEUDA"]`, así que un valor inventado da
  422 en el schema en vez de crear un pago que no impacta nada. Los 4
  lugares que ya usaban las otras 3 constantes internas
  (`INGRESO_EMPRESA`/`EGRESO_EMPRESA`/`SERVICIO`) se migraron al enum para
  que no haya un string literal repetido en ningún lado.
  **Corregido (2026-09-16):** el enum se armó auditando los literales del
  código, no datos reales de producción, y `PagoOut.tipo_pago` había
  quedado tipado como `TipoPago` — un valor histórico fuera de esos 5 en
  producción rompería la lectura con 500. Se revirtió: `PagoOut.tipo_pago`
  es `str` de nuevo (tolerante en la salida), `PagoCreate.tipo_pago` sigue
  en `Literal["COBRO_PEDIDO", "PAGO_DEUDA"]` (estricto en la entrada). El
  `SELECT DISTINCT tipo_pago FROM pago` sobre datos reales se hace al
  diseñar la importación del cliente actual, no antes.
- ~~`empleado.py` tiene `id_empresa=1` hardcodeado en dos lugares.~~
  ~~`pago.py` también: `crear_ingreso` y `crear_egreso` tienen `id_empresa=1`
  hardcodeado.~~ **Arreglado (2026-09-15).** Los tres reemplazados por
  `EmpresaService.get_id_empresa_actual(db)`. No rompe contrato (nunca fue
  un parámetro expuesto al cliente).
- ~~`ComboCreate.id_empresa` seguía `int` obligatorio: crear un combo daba
  422 apenas el front dejó de mandarlo.~~ **Arreglado (2026-09-16),
  barrido completo.** Se grepeó `id_empresa` en todos los `schemas/` del
  repo y se aplicó el mismo tratamiento a todo lo que quedaba sin tocar:
  - Bodies de request que todavía exigían `id_empresa` del cliente:
    `ComboCreate` (`catalogo/combos/schemas/combo.py`),
    `CamionRepartoCreate` (`repartos/camiones/schemas.py`, tenía
    `= 1` de default, igual se sacó), `StockCreate` y
    `EnvaseMovimientoManualIn` (estos dos sin router que los use hoy —
    arreglados igual, por si el día de mañana alguien los cablea sin
    revisar esto).
  - Hardcodeos de `id_empresa=1` que quedaban sueltos (no eran bodies,
    pero mismo problema de fondo): `clientes/service.py` (alta de
    cliente, incluye el chequeo de duplicado por DNI+empresa),
    `catalogo/servicios/service.py` (pago de período de servicio),
    `inventario/movimientos/router.py` (`POST /movimientos-stock/`),
    `repartos/recorridos/service.py` (`abrir_recorrido`, egreso de stock
    inicial).
  - Todos resueltos con `EmpresaService.get_id_empresa_actual(db)`.
    Contrato regenerado (solo `POST /combos/` cambió de forma visible:
    los demás ya tenían default o no eran bodies). Verificado en vivo:
    crear un combo sin `id_empresa` ya no da 422.

**Bugs silenciosos** (se pueden arreglar sin tocar el contrato):

- ~~`listaPrecios.py`: `obtener_lista` y `listar_productos_con_precio`
  definidas dos veces cada una.~~ **Arreglado en el paso 3 (2026-09-14).**
  Se borraron las segundas definiciones (código muerto).
- ~~`stock.py`: `listar_detalle` (`GET /stock/detalle`) definida dos
  veces.~~ **Arreglado en el paso 3 (2026-09-14).** De paso apareció un
  tercer duplicado no anotado: `StockDetalleOut` estaba definida también en
  `schemas/stock.py` además de `schemas/stock_detalle.py`; el router
  importaba las dos y la segunda pisaba a la primera. Se borró la de
  `schemas/stock.py`. La corrección hizo que `GET /stock/detalle` cambiara
  de forma en el contrato: el `response_model` real siempre fue el de la
  primera definición (con schema), pero el snapshot de OpenAPI reflejaba el
  de la *segunda* (sin `response_model`, por eso aparecía `"200": null`) —
  FastAPI arma el `openapi.json` con la última definición de una ruta
  duplicada aunque el routing use la primera. El JSON que devuelve el
  endpoint a un cliente real **no cambió** (siempre fue el de la primera
  definición); solo se corrigió la documentación. Snapshot regenerado y
  commiteado junto con el fix.
- ~~`TipoMovimiento` definido dos veces: en `schemas/enumsStock.py` y en
  `schemas/movimientoStock.py`.~~ **Arreglado en el paso 3 (2026-09-14).**
  `movimiento_stock.py` ahora importa el enum desde `enums_stock.py` en vez
  de redefinirlo.
- ~~`clienteDiaSemana.py`: importa `ClienteDiaVisitaOut` desde `schemas` y
  después redefine la misma clase en el archivo.~~ **Arreglado en el paso 3
  (2026-09-14).** La del router (con `model_config = ConfigDict(from_attributes=True)`)
  era la que corría; se sacó el import muerto y se borró la definición
  duplicada en `schemas/cliente_dia_semana.py` (ya no la usaba nadie más).

**Confirmado por `snapshot_openapi.py` (paso 0, 2026-09-14):** 128 operaciones
en el contrato. Sin autenticación: `POST /auth/login`, `POST /auth/token`,
`GET /health` — son las esperadas, ninguna otra quedó sin proteger.

**Inconsistencias de capas:**

- ~~`app/core/settings.py` sigue vivo... `comprobantePedidoService.py` y
  `comprobantePagoService.py` siguen escribiendo archivos a mano.~~
  **Arreglado en el paso 3 (2026-09-14).** Los dos services ahora usan
  `core/storage.py` (`get_storage().guardar(...)` / `.url_publica(...)`),
  `settings.py` se borró, y `python-dotenv` salió de `requirements.txt`
  (ya no lo necesitaba nadie). De paso se encontró que esto no era solo
  prolijar: desde el paso 1, `main.py` ya no monta `StaticFiles` en
  `/docs/comprobantes/...` (lo reemplazó el endpoint `/archivos/{clave}`),
  así que cualquier comprobante generado entre el paso 1 y ahora quedaba
  con una `url_archivo` que apuntaba a una ruta que ya no existía —
  comprobantes nuevos, rotos en silencio. Este cambio lo arregla.
  ~~Sigue pendiente, y sí necesita Flutter: si hay que migrar datos del
  cliente actual, las URLs viejas en `documentos` (formato
  `/docs/comprobantes/...`) hay que reescribirlas al formato nuevo
  (`/archivos/<codigo>/comprobantes/.../AAAA/MM/archivo.pdf`).~~
  **Script listo (2026-09-15):** `scripts/migrar_urls_comprobantes.py`.
  Copia los archivos de la carpeta plana vieja (`<origen>/comprobantes/
  pagos|pedidos/<archivo>`) a `<tenant>/comprobantes/<categoria>/AAAA/MM/
  <archivo>` (año/mes de `documentos.fecha_carga`) y reescribe
  `url_archivo`. Tiene `--dry-run`, es idempotente (una fila ya migrada no
  vuelve a tocarse) y no borra los originales. Probado con un documento y
  cliente de prueba contra el tenant `demo` (insertados y borrados en la
  misma verificación). **No requiere nada de Flutter**: el campo `url` que
  ve el cliente sigue siendo una ruta relativa al endpoint `/archivos/...`,
  como ya viene desde el paso 1 — esto es puramente una migración de datos
  del lado del servidor. Falta correrlo de verdad el día que se decida
  importar los datos del cliente actual (con `--origen` apuntando a la
  carpeta real del sistema viejo).
- ~~`persona.py`, `camionReparto.py`, `empleado.py` hacen queries y
  `db.commit()` directo en el router.~~ **Arreglado en el paso 3
  (2026-09-14).** Cada uno con su `service.py` nuevo. ~~`clienteDiaSemana.py`
  quedó parcial~~: **terminado el mismo día.** Las 4 consultas de reporte
  (`listar_clientes_por_fecha`, `_con_datos`, `_por_rango`, `_por_id_dia`,
  con subqueries y window functions) se movieron a `agenda/service.py`; el
  router quedó fino. Los schemas de respuesta que vivían adentro del router
  (`ClientePorDiaItem`, `ClientesPorDiaOut`, `ClientesPorDiaSinFechaOut`,
  `AgendaRangoDiaOut`, `AgendaRangoOut`) se movieron a
  `schemas/cliente_dia_semana.py`. De paso se borraron `ClienteDiaVisitaIn`
  y `ClienteDiasVisitaUpsert`, dos clases que ya no usaba nadie desde que
  se borraron los endpoints comentados en un commit anterior. Probado en
  vivo con datos reales (cliente con dirección, teléfono y cuenta): las
  4 consultas devuelven exactamente lo mismo que antes, joins y todo.
- Los services levantaban `HTTPException` directamente. **Migrado en el
  paso 3 (2026-09-14)** en: `auth`/`personas`/`empleados`/`camiones` (ya no
  aplica, no tenían o se movieron a service nuevo), `repartos/agenda`,
  `catalogo/combos`, `catalogo/listas_precios` (5 archivos),
  `catalogo/servicios`, `clientes/service.py`, `inventario/envases`,
  `inventario/stock`, `pagos/services/pago.py`, `repartos/repartos_dia`
  (2 archivos), y `pedidos/service.py` (44 usos en 793 líneas, se hizo en
  una pasada aparte el mismo día por el tamaño). Con esto, **toda la capa
  de service quedó migrada.**
  - Los **16 routers** (no services) que también levantaban
    `HTTPException` directo (56 usos en total) también se migraron el
    mismo día:
    - Los 15 chicos (`auditoria`, `auth`, `documentos`, `pagos` router,
      `pedidos` router, `usuarios`, `maestros/medio_pago`,
      `catalogo/productos`, `inventario/stock` router,
      `repartos/recorridos`, `repartos/visitas`,
      `clientes/routers/{cliente_cuenta,direccion_cliente,email_cliente,
      telefono_cliente}`): solo cambio de excepción, mismos status codes.
      De paso, `auth.py` gana el header `WWW-Authenticate: Bearer` en el
      401 (lo agrega el handler global, el `HTTPException` viejo no lo
      ponía). Se encontró y arregló una regresión real: en
      `repartos/visitas/router.py` un `except HTTPException` que envolvía
      la llamada a `EnvaseClienteService.registrar_movimiento` ya no
      atrapaba nada desde que ese service se migró a errores de dominio
      antes en esta misma sesión — el rollback explícito dejaba de
      ejecutarse (lo tapaba el rollback implícito de `Session.close()`,
      por eso no se notó antes).
    - `clientes/routers/cliente.py` (560 líneas, 19 usos, lógica de
      negocio mezclada) recibió el tratamiento completo: toda la lógica
      (`CrearCliente`, `ActualizarCliente`, `BorrarCliente`,
      históricos/pedidos/productos del cliente, `_idx_dias`,
      `_calcular_orden_y_correr`) se movió a `ClienteService` en
      `clientes/service.py`. De paso se encontró que ese archivo **ya
      tenía** una implementación de ordenamiento (`calcular_orden`/
      `normalizar_orden`) que **nadie llamaba** — un algoritmo distinto y
      muerto conviviendo con el que el router realmente usaba. Se borró
      la muerta y quedó una sola (`_calcular_orden_y_correr`, la que
      corría de verdad). Probado en vivo de punta a punta: alta de
      cliente con persona nueva + frecuencias (día/turno/orden) + cuenta
      automática, duplicado (409), actualizar (200), producto
      inexistente (404), baja (204).
- ~~Hay bloques grandes de código comentado en `repartoDia.py`,
  `clienteDiaSemana.py`, `listaPrecios.py` y `pago.py`.~~ **Borrados en el
  paso 3 (2026-09-14).** Junto con imports que solo usaban esos bloques
  (`pg_insert` duplicado dos veces en `clienteDiaSemana.py`,
  `RepartoDiaUpdate`/`RegistrarCobroIn` en `reparto_dia.py`). Ninguno estaba
  registrado como ruta activa (los de `listaPrecios.py` y `clienteDiaSemana.py`
  eran bloques `"""..."""`, invisibles para FastAPI), así que no cambia
  comportamiento.

**Producción / infraestructura** (revisión cruzada con el front, 2026-09-15):

- ~~`backend-prod` de `docker-compose.yml` no montaba ningún volumen:
  `STORAGE_LOCAL_PATH=/data` vivía en el filesystem del contenedor y
  desaparecía en cada recreate/deploy, junto con todo lo que escribe
  `core/storage.py` (incluido el destino de
  `scripts/migrar_urls_comprobantes.py`).~~ **Arreglado (2026-09-15).**
  Volumen nombrado `data:/data` en `backend-prod` y en `backend` (dev, para
  reproducir el mismo comportamiento). Además `docker-compose.yml` pedía
  `POSTGRES_DB`/`POSTGRES_USER`/`POSTGRES_PASSWORD`, variables que
  `.env.example` ya no define (las reemplazó `TENANT_DB_*`): un
  `docker compose up` con un `.env` nuevo levantaba un Postgres sin
  contraseña configurada. El servicio `db` ahora deriva esas tres de
  `TENANT_DB_USER`/`TENANT_DB_PASSWORD`/`TENANT_DB_MAINTENANCE_DB` (falla
  fuerte si `TENANT_DB_PASSWORD` no está seteada, en vez de arrancar mal
  configurado). Queda anotado en `.env.example` que `TENANT_DB_HOST` y
  `CONTROL_PLANE_DATABASE_URL` tienen que apuntar al nombre del servicio
  (`db`), no a `localhost`, cuando se corre vía `docker compose up` — no se
  fuerza ese valor porque no se sabe si la topología real de producción usa
  este `db` de compose o un Postgres administrado aparte.
- ~~Un tenant nuevo (`scripts/crear_tenant.py`) no tenía fila en `empresa`,
  y el alta no lo avisaba: `sembrar_maestros()` hacía
  `from scripts.seed_maestros import sembrar`, ese archivo no existe, caía
  en el `except ImportError`, imprimía un aviso y seguía como si nada. El
  tenant quedaba ACTIVO pero roto: `EmpresaService.get_id_empresa_actual`
  tira 404 en stock/caja/pagos de ingreso-egreso/alta de empleados, y
  `crear_repartos_del_dia_automaticos` no crea ningún reparto (itera
  `Empresa` vacía) sin que el scheduler lo reporte como error.~~
  **Arreglado (2026-09-15).** Las tablas maestras de verdad (día de semana,
  medio de pago, rol, tipo de movimiento/evento) ya venían de la migración
  de seed (`409913c99187`), independiente de cualquier flag — eso nunca
  fue el problema. Lo que faltaba era la fila de `empresa`, que es dato del
  cliente (razón social) y no pertenece a una migración: se agregó
  `crear_empresa()` en `crear_tenant.py`, que la inserta con la
  `--razon-social` que ya recibía el script. Se borró `sembrar_maestros()`
  (dead code: nunca hizo nada desde que existe). Se agregó
  `verificar_alta()`: chequea que exista `empresa`, el rol ADMIN y el
  usuario admin con ese rol; si falta algo, el alta corta con error y el
  tenant queda en PROVISIONANDO (no ACTIVO roto). Probado en vivo: alta
  completa de un tenant de prueba (verificación en verde,
  `EmpresaService.get_id_empresa_actual` resuelve bien); dado de baja con
  `--rollback` al terminar.
  ~~`--sin-seed` ahora controla este paso (antes no controlaba nada
  real).~~ **Borrado (2026-09-15, segunda revisión cruzada).** Un flag
  cuyo único efecto posible era saltear la creación de `empresa` —y por lo
  tanto garantizar que `verificar_alta()` fallara y el tenant quedara en
  PROVISIONANDO— no tiene variante útil. El alta de un cliente no necesita
  opciones: se borró el flag entero.
  De paso: la lista de subdominios/códigos que ninguna sodería puede tener
  vivía duplicada en `tenancy.py` (`{"www","api","admin","app"}`, usada
  para resolver el tenant por subdominio) y en `crear_tenant.py`
  (`RESERVADOS`, una lista más larga que también bloquea nombres
  reservados de Postgres). Unificadas en `CODIGOS_RESERVADOS`
  (`app/core/tenancy.py`); `crear_tenant.py` la importa en vez de tener su
  propia copia.

---

## Reglas duras

1. **Un paso por commit.** Nunca mezclar movimiento de archivos con cambios
   de lógica. Si algo se rompe en dos semanas, tiene que quedar claro qué
   commit tocó comportamiento y cuál no.
2. **`pytest tests/test_api_contract.py` en verde antes de commitear.** Si
   falla, mirá primero el orden de `include_router` en `app/api/router.py`.
3. **El orden de los `include_router` no se reordena alfabéticamente.**
   FastAPI resuelve por primera coincidencia: `/repartos-dia/bootstrap`
   registrado después de `/repartos-dia/{id_repartodia}` queda inalcanzable,
   y el test del contrato **no** lo detecta porque las dos rutas siguen en el
   OpenAPI.
4. **Ningún modelo nuevo sin agregarlo a `app/db/models_registry.py`.** Si
   Alembic no lo ve en la metadata pero sí en la base, autogenerate escribe
   un `drop_table`. Corré `pytest tests/test_models_registry.py`.
5. **Leé toda migración autogenerada antes de aplicarla.** Si tiene un
   `drop_table` que no pediste, algo quedó fuera del registry.
6. **Nunca `SECRET_KEY` ni credenciales en el código.** Todo por `.env`, y
   el `.env` no se commitea.
7. **No toques el repo original de la sodería.** Este es una copia; aquel
   sigue en producción.

## Convenciones

- Código, nombres de archivo y comentarios en **español**. Archivos en
  `snake_case` (el script renombra los camelCase que quedan).
- Las tablas y columnas de la base **no se renombran**: hay datos en
  producción y la app de Flutter depende de los nombres.
- El hashing de contraseñas es pbkdf2 con `hashlib` puro. Los hashes viejos
  de 100.000 iteraciones tienen que seguir validando: hay usuarios reales.
  `necesita_rehash()` los migra solos en el login.
- Tipos con `from __future__ import annotations` y sintaxis moderna
  (`str | None`, no `Optional[str]`) en código nuevo.

## Cosas a tener en la cabeza

- **Conexiones.** El caché de engines de `core/database.py` es **por
  proceso**, y `Dockerfile.prod` corre `gunicorn --workers ${WEB_CONCURRENCY:-2}`:
  la fórmula real es `WEB_CONCURRENCY × TENANT_ENGINE_CACHE_SIZE ×
  (TENANT_POOL_SIZE + TENANT_MAX_OVERFLOW)`. **Corregido (2026-09-15,
  revisión cruzada con el front):** con los defaults viejos (15 × (5+5),
  sin contar workers) daba 150 contra un Postgres de 100 — pero el número
  real, con los entonces-4-workers-fijos, era 600. Los defaults de
  `.env.example`/`config.py` bajaron a `TENANT_ENGINE_CACHE_SIZE=10`,
  `TENANT_POOL_SIZE=2`, `TENANT_MAX_OVERFLOW=2`.
  **Actualizado (2026-09-16):** el "4 workers" pasó a ser
  `WEB_CONCURRENCY` (variable de Railway, default `2` en el Dockerfile,
  no fijo — ver el punto de Railway más abajo), así que con los defaults
  actuales es `2 × 10 × 4 = 80`, dentro de `max_connections=100`. Si se
  sube `WEB_CONCURRENCY` en Railway, hay que recalcular esta cuenta —
  con 4 workers otra vez sería `4 × 10 × 4 = 160`, arriba del límite: subí
  `max_connections` en Postgres o meté PgBouncer antes de subir
  `WEB_CONCURRENCY` sin más.
- **El control plane es punto único de falla.** Si esa base se cae, no se
  resuelve ningún tenant.
- **Reportes agregados entre soderías no son posibles directamente.** Es el
  costo del modelo elegido.
- **Sincronización offline:** cualquier cambio en `features/sincronizacion/`
  o en la idempotencia de pagos rompe tablets en la calle. Máximo cuidado.
- **CI (2026-09-15, segunda revisión cruzada):** el repo no tenía ningún
  workflow. Se agregó `.github/workflows/tests.yml`: corre `pytest tests/`
  completo (contrato + los 4 de `test_multi_tenant.py`) en cada push/PR a
  `main`, con un `postgres:17` como service. Sin variables de entorno
  propias a propósito — `tests/conftest.py` ya trae defaults pensados para
  un Postgres en `localhost:5432` con `postgres`/`postgres`, que es
  justo lo que ese service expone. Los tests de integración eran los que
  encontraron los 3 bugs de pérdida silenciosa de datos: si corrían solo
  en la máquina de quien los escribió, el hallazgo no se protegía a
  futuro.
- **Topología de dominios (2026-09-15, segunda revisión cruzada): decidida
  la opción A** — cada sodería en `<codigo>.tuapp.com`, mismo host sirve
  el bundle Flutter y proxea `/api/*` al backend, tenant resuelto por
  `Host` sin que el cliente mande nada. El nginx y el cliente los
  implementa el front; de este lado se auditó lo que hacía falta y **no
  requirió cambios de código**, solo confirmar:
  - `_codigo_desde_subdominio()` ya lee `request.headers.get("host", "")`
    — el header `Host` tal cual llega a uvicorn/gunicorn. Funciona bien
    **si** nginx manda `proxy_set_header Host $host;` (el host original,
    no el del upstream). Si nginx no lo setea explícitamente, reescribe el
    `Host` al del upstream y el tenant deja de resolver — es una línea del
    `nginx.conf` del front, no algo para arreglar acá.
  - Ninguna ruta del backend tiene el prefijo `/api` hardcodeado (`/pagos`,
    `/pedidos`, `/catalogo`, etc., todos sin prefijo). Recomendado:
    strippear `/api` en nginx (`location /api/ { proxy_pass
    http://backend/; }`, con la barra final) para no tener que tocar
    `TENANT_EXEMPT_PATHS` ni ningún router.
  - `DEFAULT_TENANT` y `CORS_ORIGINS`/`CORS_ORIGIN_REGEX` ya validan
    correctamente en `ENV=prod` (`config.py::_validar_coherencia`): no se
    tocó nada. Con mismo origen, CORS deja de ejercer pero la validación
    sigue pidiendo que se declare uno de los dos — no se relajó a
    propósito (sigue siendo una red de seguridad legítima si algún día hay
    un origen distinto, ej. un panel de admin aparte). Falta setear los
    valores reales (`BASE_DOMAIN=tuapp.com`,
    `CORS_ORIGIN_REGEX=https://.*\.tuapp\.com`) en el `.env` de producción
    real — eso es un valor de infraestructura, no algo que este repo
    pueda decidir.
  - `TENANT_RESOLUTION=both` (default) ya deja el header `X-Tenant` como
    fallback funcionando; no se tocó, sigue sirviendo para `curl`/scripts
    de mantenimiento.
- **Deploy target confirmado: Railway, front y backend los dos ahí
  (2026-09-16).** Con eso la duda sobre "el `Host` es confiable" del
  punto anterior queda resuelta: no hay un edge administrado en el medio
  reescribiendo cabeceras por su cuenta, así que la cautela sobre
  `X-Forwarded-Host` que se había planteado no aplica — nginx del front
  manda `proxy_set_header Host $host;` y listo. Dos cambios de este lado:
  - **`Dockerfile.prod` corregido para Railway.** El bind pasó de
    `0.0.0.0:8000` fijo a `[::]:${PORT:-8000}`: Railway asigna `$PORT` en
    runtime (no es fijo), y la red privada entre servicios (para que el
    front le pegue a `backend.railway.internal`) es IPv6 — uvicorn/gunicorn
    escuchando en `[::]` cubre IPv4 y IPv6 en el mismo socket (uvicorn
    suelto no hace ese dual-stack binding solo). El `--workers 4` fijo
    pasó a `--workers ${WEB_CONCURRENCY:-2}` (ver el punto de Conexiones
    más arriba, la fórmula de conexiones depende de este número). El
    `CMD` tuvo que pasar de forma exec (`["gunicorn", ...]`) a forma
    shell, porque la forma exec no expande variables de entorno.
    Verificado con un build y un run reales (no solo lectura de código):
    `docker build` + `docker run` con `PORT`/`WEB_CONCURRENCY` custom,
    logs confirmando `Listening at: http://[::]:8080` y la cantidad de
    workers pedida, y `GET /health` respondiendo 200 a través del puerto
    publicado.
  - **Encontrado de paso: no existía `.dockerignore`.** `COPY . .` en
    `Dockerfile.prod` empaquetaba todo el directorio de build sin
    excepciones — `.git/` completo (incluye el historial con el
    `.env.local` que se sacó del índice pero sigue en commits viejos) y,
    si existía un `.env` local al momento del build, ese archivo con
    secretos reales quedaba horneado dentro de la imagen. Se encontró
    corriendo el build de prueba de arriba (mi propio `.env` de dev
    apareció adentro de la imagen en el primer intento). Agregado
    `.dockerignore` excluyendo `.git/`, `.env*` y caches; verificado que
    la imagen reconstruida ya no los tiene (`ls /app/.env` y
    `ls /app/.git` fallan adentro del contenedor).
  - **Recomendado, no implementado (decisión de infraestructura, no de
    código): que el backend no tenga dominio público**, accesible solo
    vía `backend.railway.internal` a través del proxy del front. Sin URL
    pública, no hay forma de pegarle directo al backend con un `Host`
    falsificado para elegir tenant — el aislamiento deja de depender
    solo del claim `ten` del JWT. No requiere cambios acá: el backend ya
    resuelve el tenant del `Host` que le llegue, sea la request directa
    o vía el proxy interno del front, y ese `Host` sigue siendo el
    público real (`proxy_set_header Host $host` lo preserva aunque el
    upstream sea `.railway.internal`). Con esto, `CORS_ORIGINS` deja de
    ejercer del todo (mismo origen ya no alcanza para que el navegador
    haga cross-origin), pero se deja seteado igual como red de seguridad
    — mismo criterio que ya se documentó arriba para la opción A.
- **Convención de transacciones (2026-09-15, segunda revisión cruzada):
  los routers commitean, los services nunca.** Ningún service hace
  `db.begin()`/`with db.begin():` ni decide si commitear mirando
  `db.in_transaction()` — esa señal no es confiable (ver los tres bugs de
  pérdida silenciosa más arriba: `get_current_user` ya toca la sesión del
  request antes de que corra el handler, así que "recién empezada" nunca
  es cierto donde importaría). El service hace su trabajo (`add`/`flush`/
  queries) y, si algo sale mal, `db.rollback()` para dejar la sesión
  usable; el router es quien decide cuándo terminó la operación y hace
  `db.commit()`. Se sacó la lógica de `started_tx`/`nullcontext` de
  `PagoService.crear()` y el `_tx()` con `begin_nested()` de
  `catalogo/combos/service.py` (este último no tenía el bug — el
  `db.commit()` explícito después ya lo salvaba — pero es la misma trampa
  para el próximo que lo lea pensando que el context manager resuelve
  todo). Si escribís un service nuevo que puede ser llamado tanto standalone
  como anidado desde otro service (como `PagoService.crear` desde
  `crear_pedido`), no hay abstracción mágica: el nested caller simplemente
  no commitea (lo hace el que está más afuera), y punto.
- ~~`PLATFORM_ADMIN_TOKEN`, `require_platform_admin()` y el path exento
  `/admin` existían sin ningún router de administración detrás — config
  que prometía una API que nunca se escribió.~~ **Borrado (2026-09-15).**
  Si el día de mañana hace falta una API de alta/baja de soderías (hoy es
  `scripts/crear_tenant.py` a mano), se vuelve a agregar junto con los
  endpoints reales, no antes.
- **Credenciales del entorno de dev local rotadas (2026-09-16).**
  `SECRET_KEY` y la contraseña del rol `postgres` (usada tanto para
  `CONTROL_PLANE_DATABASE_URL` como `TENANT_DB_PASSWORD`) se regeneraron:
  nada del SaaS está en producción todavía, no hay sesiones activas ni
  cliente al que avisar, así que se hizo directo, sin runbook. Las que
  estaban en el `.env.local` commiteado (ya sacado del índice en
  `a62f72a`) se dan por comprometidas y no se usan en ningún lado — ese
  archivo ni siquiera lo lee la app (`config.py` solo carga `.env`). El
  día que haya un Postgres real de producción con datos reales atrás,
  cualquier rotación ahí sí necesita el runbook completo (coordinar
  timing, avisar, etc.) — esta rotación fue puramente del entorno de
  desarrollo.
- **Un rol de Postgres por tenant (2026-09-16, segunda revisión
  cruzada).** Hasta ahora todas las soderías compartían el mismo rol
  admin (`TENANT_DB_USER`) para leer y escribir en runtime: el
  aislamiento entre tenants dependía enteramente de que el código eligiera
  bien el engine (una base por sodería, pero un solo usuario de Postgres
  que puede conectarse a cualquiera). Se aprovechó que hoy solo hay un
  tenant real (`demo`) para hacerlo ahora — con diez clientes vivos esto
  es una migración coordinada, con uno es un `CREATE ROLE`/`GRANT`.
  - `scripts/crear_tenant.py`: nuevas `crear_rol_tenant()`/
    `borrar_rol_tenant()`. El alta crea un rol `tenant_<codigo>` con
    privilegios (`GRANT ALL` + `ALTER DEFAULT PRIVILEGES` para tablas
    futuras) limitados a su propia base, y lo guarda en
    `Tenant.dsn_override` — el campo ya existía, pensado originalmente
    para "esta sodería vive en otro servidor"; ahora también se usa para
    "esta sodería usa un rol restringido en el mismo servidor". `--rollback`
    borra el rol además de la base. `--dsn-override` salta la creación del
    rol (asume que ese servidor tiene su propio esquema de privilegios).
    `verificar_alta()` ahora corre contra el rol restringido, no el admin:
    de paso confirma que los GRANT quedaron bien.
  - `scripts/migrate_all_tenants.py`: las migraciones **siempre** necesitan
    el rol admin (`CREATE TABLE`/`ALTER TABLE` no están en los privilegios
    del rol de tenant a propósito). Se agregó `dsn_admin()` que reconstruye
    el DSN admin desde `settings` + `codigo` en vez de usar `tenant.dsn`
    (que ahora, para un tenant con rol restringido, apunta a ese rol).
    Documentado ahí mismo el límite: si algún día una sodería usa
    `--dsn-override` para vivir en otro servidor, este script no la va a
    alcanzar — no hay forma de distinguir los dos usos de `dsn_override`
    con lo que expone `TenantInfo` hoy. No es el caso de ninguna sodería
    actual.
  - `demo` (el único tenant existente) migrado al rol restringido
    (`tenant_demo`) a mano, sin script dedicado — es un caso único, no
    hacía falta una migración general.
  - Verificado en vivo: alta completa de un tenant de prueba por CLI
    (rol creado, login + `/catalogo/bootstrap` + `/stock/` funcionando
    a través del rol restringido), `--rollback` limpiando el rol sin
    dejar huérfanos, `migrate_all_tenants.py --dry-run` reportando bien
    la versión de `demo` (rol restringido) y de un tenant de prueba
    (admin) por igual, y la suite completa de tests de integración
    (login, bootstrap, stock, idempotencia, cancelar-deuda) pasando a
    través del rol nuevo — si algún `GRANT` hubiera quedado corto, esto
    lo habría mostrado como `permission denied`, no hizo falta un test
    aparte.
- **Timestamps pasan a UTC con timezone (2026-09-16, segunda revisión
  cruzada).** Convivían `datetime.now()` (hora local del proceso) y
  `datetime.utcnow()` (UTC) escribiendo a columnas `DateTime(timezone=False)`
  — un pago a las 22:00 en Córdoba quedaba guardado como la 01:00 del día
  siguiente, y un pedido creado en el mismo minuto por otro camino quedaba
  en las 22:00. El cierre de caja y los reportes diarios los contaban en
  días distintos. Se hizo ahora porque la base de cada sodería todavía
  está vacía de datos reales — no hay filas históricas ambiguas que
  interpretar; el día que se importen los datos del cliente actual, esa
  importación tiene que escribir directo en el formato nuevo.
  - **Convención**: toda columna "cuándo pasó esto" es
    `DateTime(timezone=True)`, escrita siempre con
    `datetime.now(timezone.utc)`. Nunca `datetime.now()` (hora local
    ambigua) ni `datetime.utcnow()` (deprecado en 3.12, devuelve naive).
    Mostrarle una fecha al usuario en su zona horaria es una conversión en
    el borde de salida (`.astimezone(ZoneInfo(tenant.timezone))`), no algo
    que se decide al guardar.
  - Migración `b2c3d4e5f6a7`: 9 columnas pasadas de `timestamp` a
    `timestamptz` — `pago.fecha`, `pedido.fecha`, `visita.fecha`
    (este no tenía ni `timezone=False` explícito, `DateTime` a secas ya es
    naive por default), `documentos.fecha_carga`, `caja_empresa.fecha`,
    `historico.fecha`, `movimiento_stock.fecha`,
    `movimiento_envase_cliente.fecha` (idem, sin `timezone=False`
    explícito) y `lista_de_precios.fecha_creacion`. `USING col AT TIME
    ZONE 'UTC'` reinterpreta cualquier valor naive existente como si ya
    fuera UTC — para los datos de prueba de este entorno alcanza, no está
    garantizado para datos reales (por eso hacerlo ahora, con la base
    vacía, y no después de importar).
  - 11 call sites con `datetime.now()`/`.replace(tzinfo=None)` migrados a
    `datetime.now(timezone.utc)`: `auditoria/service.py`,
    `catalogo/servicios/service.py`, `clientes/routers/cliente_cuenta.py`
    (2), `inventario/envases/service.py` (2), `pedidos/service.py` (3,
    incluido un `datetime.combine(rep.fecha, now.time())` que perdía el
    tzinfo — pasó a `now.timetz()`), `repartos/visitas/router.py`, y los
    5 que ya se habían arreglado con `.replace(tzinfo=None)` en un paso
    anterior (ya no hace falta pelarle el tzinfo).
  - **Excepción a la regla, a propósito**: `db/mixins.py::marcar_eliminado()`
    escribía `eliminado_en` (que ya era `timezone=True`, sin que nadie lo
    hubiera notado) con `datetime.now()` naive — un bug dormido, porque el
    mixin todavía no lo usa ningún modelo. Arreglado igual, para cuando se
    use.
  - **Excepción real, no un descuido**: `reportes/router.py` calculaba
    "mes/año actual" para el default de un reporte con `datetime.now()`.
    Esto no es un timestamp que se guarda — es "qué mes es hoy" para el
    usuario, y tiene que ser el mes actual en la zona del tenant, no en
    UTC (cerca de medianoche en Argentina, UTC ya está en el día
    siguiente). Se cambió a
    `datetime.now(ZoneInfo(tenant_actual().timezone))`, no a
    `datetime.now(timezone.utc)`. Regla completa: "cuándo pasó un evento
    que se guarda" → UTC siempre; "qué día/mes es hoy para una persona" →
    zona del tenant.
  - **Pendiente, fuera de alcance de este cambio**: varios `.date()` sobre
    un datetime ahora UTC-aware (ej. `ProductoCliente.fecha_entrega` en
    `envases/service.py`) heredan el mismo problema que `reportes/router.py`
    tenía — cerca de medianoche en Argentina, `.date()` de un datetime UTC
    puede dar el día siguiente. No se tocó: son columnas `Date` (no
    `DateTime`) que representan un día de calendario/negocio, no un
    instante, y requieren la misma decisión de "zona del tenant" que se
    tomó para el reporte — pero una por una, no en este barrido.
  - **Pendiente, necesita decisión con Flutter**: los payloads de sync
    offline mandan `fecha` como ISO 8601 sin offset (ej.
    `"2026-09-15T10:00:00"`), que Pydantic parsea como naive — hoy
    interpretado tal cual (sin conversión) por Postgres al guardar en la
    columna ahora `timestamptz`, igual que pasaba antes con la columna
    naive. Si esa hora es hora local del dispositivo (probable, es la
    hora que ve el repartidor en la tablet) y no UTC, sigue quedando mal
    interpretada — no se resolvió, porque no hay forma de saberlo desde
    acá con certeza sin confirmar con el front qué maneja el dispositivo.
    Lo correcto de fondo es que el cliente mande el offset (`Z` o
    `-03:00`) en el ISO 8601; mientras tanto, esto no es peor que el
    comportamiento de antes, solo que ahora la columna es honesta sobre
    ser `timestamptz`.
  - Verificado en vivo: migración aplicada contra `demo` (las 9 columnas
    quedaron `timestamp with time zone`), suite completa de tests (23)
    pasando contra Postgres real después de migrar.

---

## Cómo quiero que trabajes

- Antes de un cambio grande, decime el plan y esperá. No hagas refactors
  amplios por iniciativa propia.
- Si algo de este archivo contradice lo que ves en el código, **avisame**;
  no elijas por tu cuenta.
- Si una decisión tiene un costo que no está acá, decilo aunque no te lo
  pregunte.
- No agregues dependencias sin avisar.
- Nada de código comentado "por las dudas".
