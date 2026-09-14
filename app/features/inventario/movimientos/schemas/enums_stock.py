from enum import Enum

class TipoMovimiento(str, Enum):
    ingreso = "ingreso"
    egreso = "egreso"
    ajuste = "ajuste"