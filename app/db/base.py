"""
Base declarativa de los modelos de negocio.

Hoy tus modelos hacen `from app.core.database import Base`. Eso genera un
acoplamiento incomodo: para definir una tabla hay que importar el modulo
que maneja engines, pools y sesiones.

Se re-exporta desde aca para que los modelos importen
    from app.db.base import Base
y no sepan nada de conexiones. El script de migracion reescribe ese import
automaticamente en los ~40 archivos de modelos.

El import viejo sigue funcionando durante la transicion.
"""

from __future__ import annotations

from app.core.database import Base

__all__ = ["Base"]
