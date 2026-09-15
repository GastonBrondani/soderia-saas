"""
Configuración central de la aplicación.

Reemplaza a:
  - app/core/settings.py  (COMPROBANTES_* con os.getenv sueltos)
  - los load_dotenv() / os.getenv() dispersos en database.py y security.py
  - las constantes hardcodeadas en main.py (CORS, rutas /data)

Todo se valida al arrancar. Si falta una variable obligatoria o SECRET_KEY
es insegura en produccion, la app NO levanta. Es intencional: es preferible
que falle en el deploy y no seis meses despues.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict
from sqlalchemy.engine import URL

# NoDecode le dice a pydantic-settings que NO intente parsear el valor del
# .env como JSON. Sin esto, un `CORS_ORIGINS=http://a,http://b` revienta con
# un JSONDecodeError antes de que llegue a correr nuestro validador.
ListaDeTexto = Annotated[list[str], NoDecode]

# Valor que traia el codigo viejo como fallback. Lo dejamos explicito para
# poder rechazarlo si alguien lo copia al .env de produccion.
_SECRET_KEY_INSEGURA = "CAMBIA_ESTA_CLAVE_POR_ALGO_LARGO_Y_SECRETO"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    # ------------------------------------------------------------------
    # Aplicacion
    # ------------------------------------------------------------------
    APP_NAME: str = "Soderia API"
    APP_VERSION: str = "2.0.0"
    ENV: Literal["dev", "staging", "prod"] = "dev"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # Exponer /docs y /redoc. En prod conviene apagarlo.
    ENABLE_DOCS: bool = True

    # ------------------------------------------------------------------
    # Control plane: la unica base fija del sistema.
    # Guarda que soderias existen y donde vive la base de cada una.
    # ------------------------------------------------------------------
    CONTROL_PLANE_DATABASE_URL: str

    # ------------------------------------------------------------------
    # Bases de tenants
    # ------------------------------------------------------------------
    TENANT_DB_HOST: str = "localhost"
    TENANT_DB_PORT: int = 5432
    TENANT_DB_USER: str
    TENANT_DB_PASSWORD: str
    TENANT_DB_DRIVER: str = "postgresql+psycopg2"

    # Prefijo de las bases: soderia_solmar, soderia_lacascada, etc.
    TENANT_DB_NAME_PREFIX: str = "soderia_"

    # Base "de mantenimiento" a la que conectarse para hacer CREATE DATABASE.
    TENANT_DB_MAINTENANCE_DB: str = "postgres"

    # Cuantos engines mantener vivos en memoria a la vez. Este cache es POR
    # PROCESO: con gunicorn --workers 4 (Dockerfile.prod) hay 4 caches
    # independientes. Cada engine abre su propio pool, asi que las
    # conexiones maximas reales son:
    #   GUNICORN_WORKERS * TENANT_ENGINE_CACHE_SIZE * (TENANT_POOL_SIZE + TENANT_MAX_OVERFLOW)
    # Con estos defaults y 4 workers: 4 * 10 * (2+2) = 160, todavia arriba
    # de un Postgres default (max_connections=100). Subi max_connections o
    # meté PgBouncer antes de sumar mas soderias activas.
    TENANT_ENGINE_CACHE_SIZE: int = 10
    TENANT_POOL_SIZE: int = 2
    TENANT_MAX_OVERFLOW: int = 2
    TENANT_POOL_RECYCLE: int = 1800

    # Cuantos segundos cachear la ficha de un tenant antes de releerla
    # del control plane. Si suspendes una sodería, tarda esto en cortar.
    TENANT_CACHE_TTL_SECONDS: int = 60

    # ------------------------------------------------------------------
    # Resolucion de tenant
    # ------------------------------------------------------------------
    # subdomain -> solmar.tuapp.com
    # header    -> X-Tenant: solmar
    # both      -> intenta subdominio, si no hay usa el header
    TENANT_RESOLUTION: Literal["subdomain", "header", "both"] = "both"
    TENANT_HEADER: str = "X-Tenant"
    BASE_DOMAIN: str = "localhost"

    # Tenant a usar cuando no se puede resolver. SOLO para desarrollo local:
    # con esto puesto, la app te deja entrar sin subdominio ni header.
    DEFAULT_TENANT: str | None = None

    # Rutas que no necesitan tenant resuelto (health checks, docs, admin).
    TENANT_EXEMPT_PATHS: ListaDeTexto = [
        "/health",
        "/health/ready",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/admin",
    ]

    # ------------------------------------------------------------------
    # Seguridad
    # ------------------------------------------------------------------
    SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 12

    # Clave separada para el panel de administracion de la plataforma
    # (el que usas vos para dar de alta soderias). No compartir con la de tenants.
    PLATFORM_ADMIN_TOKEN: str | None = None

    # ------------------------------------------------------------------
    # CORS
    # ------------------------------------------------------------------
    # En el .env va como lista separada por comas:
    #   CORS_ORIGINS=http://localhost:5173,https://app.tuapp.com
    CORS_ORIGINS: ListaDeTexto = Field(default_factory=list)
    # Util para multi-tenant por subdominio: https://.*\.tuapp\.com
    CORS_ORIGIN_REGEX: str | None = None
    CORS_ALLOW_CREDENTIALS: bool = True

    # ------------------------------------------------------------------
    # Storage de archivos (comprobantes, documentos)
    # ------------------------------------------------------------------
    STORAGE_BACKEND: Literal["local"] = "local"
    STORAGE_LOCAL_PATH: str = "/data"
    # Antes era "/docs", que choca con la documentacion de FastAPI.
    STORAGE_PUBLIC_URL_BASE: str = "/archivos"

    # ------------------------------------------------------------------
    # Scheduler
    # ------------------------------------------------------------------
    SCHEDULER_ENABLED: bool = True
    DEFAULT_TIMEZONE: str = "America/Argentina/Cordoba"
    # Hora a la que se crean los repartos del dia (por tenant se puede pisar)
    SCHEDULER_REPARTOS_HOUR: int = 0
    SCHEDULER_REPARTOS_MINUTE: int = 5

    # ==================================================================
    # Validaciones
    # ==================================================================

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _split_origins(cls, v):
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    @field_validator("TENANT_EXEMPT_PATHS", mode="before")
    @classmethod
    def _split_paths(cls, v):
        if isinstance(v, str):
            return [p.strip() for p in v.split(",") if p.strip()]
        return v

    @field_validator("SECRET_KEY")
    @classmethod
    def _validar_secret(cls, v: str) -> str:
        if v == _SECRET_KEY_INSEGURA:
            raise ValueError(
                "SECRET_KEY es el valor de ejemplo. Genera una con: "
                "python -c \"import secrets; print(secrets.token_urlsafe(64))\""
            )
        if len(v) < 32:
            raise ValueError("SECRET_KEY tiene que tener al menos 32 caracteres.")
        return v

    @model_validator(mode="after")
    def _validar_coherencia(self) -> "Settings":
        # El bug que tenias en main.py: allow_origins=["*"] junto con
        # allow_credentials=True. El navegador rechaza esa combinacion,
        # asi que las cookies/credenciales nunca llegaban.
        if "*" in self.CORS_ORIGINS and self.CORS_ALLOW_CREDENTIALS:
            raise ValueError(
                "CORS_ORIGINS='*' es incompatible con CORS_ALLOW_CREDENTIALS=true. "
                "Usa CORS_ORIGIN_REGEX para permitir varios subdominios, "
                "o apaga CORS_ALLOW_CREDENTIALS."
            )

        if self.ENV == "prod":
            if self.DEBUG:
                raise ValueError("DEBUG no puede estar activo con ENV=prod.")
            if self.DEFAULT_TENANT:
                raise ValueError(
                    "DEFAULT_TENANT es solo para desarrollo. En prod cada request "
                    "tiene que identificar su tenant."
                )
            if not self.CORS_ORIGINS and not self.CORS_ORIGIN_REGEX:
                raise ValueError(
                    "En prod tenes que definir CORS_ORIGINS o CORS_ORIGIN_REGEX."
                )
        return self

    # ==================================================================
    # Helpers
    # ==================================================================

    def tenant_db_name(self, codigo: str) -> str:
        """Nombre de base para el codigo de tenant. solmar -> soderia_solmar"""
        return f"{self.TENANT_DB_NAME_PREFIX}{codigo}"

    def tenant_dsn(self, db_name: str) -> str:
        """DSN completo apuntando a la base de un tenant.

        Con URL.create en vez de armar el string a mano: un usuario o
        contraseña con `@`, `:`, `/` o `#` (Postgres no los prohibe) rompia
        el DSN de forma confusa. render_as_string(hide_password=False)
        porque str(URL) enmascara la contraseña con "***".
        """
        return URL.create(
            self.TENANT_DB_DRIVER,
            username=self.TENANT_DB_USER,
            password=self.TENANT_DB_PASSWORD,
            host=self.TENANT_DB_HOST,
            port=self.TENANT_DB_PORT,
            database=db_name,
        ).render_as_string(hide_password=False)

    def maintenance_dsn(self) -> str:
        """DSN a la base de mantenimiento, para CREATE/DROP DATABASE."""
        return self.tenant_dsn(self.TENANT_DB_MAINTENANCE_DB)

    @property
    def is_prod(self) -> bool:
        return self.ENV == "prod"


@lru_cache
def get_settings() -> Settings:
    """
    Instancia unica. Se cachea para no releer el .env en cada import.
    En tests: get_settings.cache_clear() despues de tocar el environment.
    """
    return Settings()


settings = get_settings()
