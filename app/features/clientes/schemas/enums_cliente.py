# app/schemas/enums_cliente.py
from enum import StrEnum

class DiaSemanaEnum(StrEnum):
    lun = "lun"; mar = "mar"; mie = "mie"; jue = "jue"
    vie = "vie"; sab = "sab"; dom = "dom"

class TurnoVisitaEnum(StrEnum):
    manana = "manana"; tarde = "tarde"; noche = "noche"

class PosicionEnum(StrEnum):
    inicio = "inicio"; final = "final"; despues = "despues"
