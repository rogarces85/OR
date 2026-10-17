"""Modelos ORM del sistema.

Importarlos registra todas las entidades en ``Base.metadata`` para que
``app.database.crear_esquema`` pueda crear las tablas (PLAN §9).
"""

from app.models.compras import CargoAlumno, CompraClub, CompraItem
from app.models.configuracion import (
    AvisoMorosidad,
    CuentaBancaria,
    PlantillaCorreo,
)
from app.models.finanzas import CategoriaEgreso, Egreso, GastoFijo
from app.models.membresia import (
    CuotaMensual,
    NegociacionDeuda,
    NivelCuota,
)
from app.models.miembro import HistorialCategoria, Miembro
from app.models.pago import Abono, ImputacionPago, Pago
from app.models.usuario import (
    ROL_ADMIN,
    ROL_MIEMBRO,
    ROL_TESORERO,
    ROLES,
    ROLES_GESTION,
    Usuario,
)

__all__ = [
    "ROLES",
    "ROLES_GESTION",
    "ROL_ADMIN",
    "ROL_MIEMBRO",
    "ROL_TESORERO",
    "Abono",
    "AvisoMorosidad",
    "CargoAlumno",
    "CategoriaEgreso",
    "CompraClub",
    "CompraItem",
    "CuentaBancaria",
    "CuotaMensual",
    "Egreso",
    "GastoFijo",
    "HistorialCategoria",
    "ImputacionPago",
    "Miembro",
    "NegociacionDeuda",
    "NivelCuota",
    "Pago",
    "PlantillaCorreo",
    "Usuario",
]
