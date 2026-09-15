# Contexto de la migración

Este archivo es la fuente de verdad del trabajo en curso. Leelo entero antes
de tocar nada.

---

## Estado actual

**Nada de la migración está hecho todavía.** Este repo es una copia exacta
del backend que corre en producción para la sodería, con un solo commit
inicial y sin cambios.

El material de la migración (los archivos de `core/`, `db/`, los scripts y
los tests) viene de un scaffold armado aparte, descomprimido en
`../soderia-saas-scaffold/` (ajustar la ruta si está en otro lado). **Ese
scaffold no se toca**: de ahí se copian archivos hacia este repo.

El paso 0 es lo primero que hay que hacer, antes de tocar una sola línea.

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

### Paso 0 — Red de seguridad (PENDIENTE, es lo primero)

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

**Rompen el contrato de la API** (coordinar con Flutter antes):

- ~~`id_empresa: Optional[int]/int = Query(...)` en `caja/router.py` (4
  endpoints), `catalogo/router.py` (bootstrap), `inventario/stock/router.py`
  (3 endpoints) y `repartos_dia/routers/reparto_dia.py` (3 endpoints).~~
  **Arreglado (2026-09-15).** Frontend confirmó que no existe (ni está
  planeado) el concepto de sucursal — cada sodería tiene una sola empresa.
  Se sacó el query param de los GET/PUT y se agregó
  `EmpresaService.get_id_empresa_actual(db)`
  (`app/features/empresas/service.py`) que la infiere de la base del tenant
  actual. El `POST /repartos-dia/` que recibe `id_empresa` en el body
  **no se tocó** (no estaba en el pedido de Flutter). Contrato regenerado
  (`python scripts/snapshot_openapi.py --salida tests/snapshots/openapi_baseline.json`);
  el único cambio visible para el cliente es que esos parámetros ya no
  existen (si los sigue mandando, FastAPI los ignora por no estar declarados).
- ~~`empleado.py` tiene `id_empresa=1` hardcodeado en dos lugares.~~
  ~~`pago.py` también: `crear_ingreso` y `crear_egreso` tienen `id_empresa=1`
  hardcodeado.~~ **Arreglado (2026-09-15).** Los tres reemplazados por
  `EmpresaService.get_id_empresa_actual(db)`. No rompe contrato (nunca fue
  un parámetro expuesto al cliente).

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
  Sigue pendiente, y sí necesita Flutter: si hay que migrar datos del
  cliente actual, las URLs viejas en `documentos` (formato
  `/docs/comprobantes/...`) hay que reescribirlas al formato nuevo
  (`/archivos/<codigo>/comprobantes/.../AAAA/MM/archivo.pdf`).
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

- **Conexiones:** cada sodería activa abre su pool.
  `TENANT_ENGINE_CACHE_SIZE × (POOL_SIZE + MAX_OVERFLOW)`. Con los defaults
  son 150 contra un Postgres de 100. Pasando ~10 clientes activos hay que
  meter PgBouncer y bajar el pool a 2.
- **El control plane es punto único de falla.** Si esa base se cae, no se
  resuelve ningún tenant.
- **Reportes agregados entre soderías no son posibles directamente.** Es el
  costo del modelo elegido.
- **Sincronización offline:** cualquier cambio en `features/sincronizacion/`
  o en la idempotencia de pagos rompe tablets en la calle. Máximo cuidado.

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
