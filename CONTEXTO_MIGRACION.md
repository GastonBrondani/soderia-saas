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

### Paso 1 — Núcleo multi-tenant (PENDIENTE)

Copiar desde `../soderia-saas-scaffold/`: todo `app/core/`, todo `app/db/`,
`app/main.py`, `alembic/env.py`, `scripts/`, `tests/`, `.env.example`,
`requirements.txt`, `Makefile` y `README.md`. Varios de esos **reemplazan**
archivos existentes (`database.py`, `security.py`, `scheduler.py`,
`main.py`, `alembic/env.py`): es lo esperado.

Borrar `app/core/settings.py`: su contenido ahora vive en `core/config.py`.

Ajustes a mano, son los únicos:

1. `app/routers/auth.py`: sacar la función local `create_access_token`
   (ahora está en `core/security.py`), importarla de ahí y pasarle
   `tenant_codigo=tenant_actual().codigo` en las dos llamadas.
2. Los imports de `require_roles` y `require_admin` pasan de
   `app.core.security` a `app.core.permissions`.
3. Los `id_empresa` por query param **se dejan como están**. Se limpian en
   el paso 3.

Configurar `.env` a partir de `.env.example`, con `SECRET_KEY` generada.
Crear la base `soderia_control`, inicializar el control plane y dar de alta
un tenant `demo` con `scripts/crear_tenant.py`.

Verificación: `/health/ready` responde `ready`; un request sin tenant da
400; con `X-Tenant: demo` y sin token da 401; el login devuelve un token con
el claim `ten`.

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

- `id_empresa: Optional[int] = Query(None)` repartido por `repartoDia.py`,
  `cajaEmpresa.py` y otros. Con una base por sodería ya no es la frontera de
  seguridad, pero sigue viniendo del cliente. Donde tenga sentido (sucursal),
  que salga del usuario autenticado.
- `empleado.py` tiene `id_empresa=1` hardcodeado en dos lugares.

**Bugs silenciosos** (se pueden arreglar sin tocar el contrato):

- `listaPrecios.py`: `obtener_lista` y `listar_productos_con_precio` están
  definidas **dos veces cada una**. FastAPI usa la primera; las segundas son
  código muerto que parece vivo.
- `stock.py`: `listar_detalle` (`GET /stock/detalle`) también está definida
  dos veces. Mismo bug que en `listaPrecios.py`, no estaba anotado acá.
- `clienteDiaSemana.py`: importa `ClienteDiaVisitaOut` desde `schemas` y
  después redefine la misma clase en el archivo. El import queda pisado.

**Confirmado por `snapshot_openapi.py` (paso 0, 2026-09-14):** 128 operaciones
en el contrato. Sin autenticación: `POST /auth/login`, `POST /auth/token`,
`GET /health` — son las esperadas, ninguna otra quedó sin proteger.

**Inconsistencias de capas:**

- `persona.py`, `camionReparto.py`, `empleado.py` y `clienteDiaSemana.py`
  hacen queries y `db.commit()` directo en el router. Otros usan Service.
- Los services levantan `HTTPException` directamente. Van migrando a los
  errores de dominio de `core/exceptions.py`, así se pueden usar desde un
  script o un job sin arrastrar FastAPI.
- Hay bloques grandes de código comentado en `repartoDia.py`,
  `clienteDiaSemana.py`, `listaPrecios.py` y `pago.py`. Se borran: git ya se
  acuerda.

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
