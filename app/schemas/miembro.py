"""Validación de los formularios de miembros (D-6, RN-11, CA-16; T5.1 y T5.3).

La ficha ampliada del miembro exige nombre completo, correo electrónico
(identificador único), teléfono, RUT, fecha de nacimiento, dirección y contacto
de emergencia. Los mensajes de validación se entregan en español para mostrarlos
en el formulario.
"""

from __future__ import annotations

import re
from datetime import date

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
)

# Etiquetas visibles de cada campo, usadas en los mensajes de error (CA-16).
ETIQUETAS_CAMPO: dict[str, str] = {
    "nombre_completo": "Nombre completo",
    "email": "Correo electrónico",
    "telefono": "Teléfono",
    "rut": "RUT",
    "fecha_nacimiento": "Fecha de nacimiento",
    "direccion": "Dirección",
    "contacto_emergencia": "Contacto de emergencia",
}

_PATRON_RUT = re.compile(r"^\d{6,9}[0-9kK]$")
_PATRON_TELEFONO = re.compile(r"^[+\d][\d\s.-]{5,}$")


class MiembroEntrada(BaseModel):
    """Ficha ampliada del miembro (D-6): todos sus campos son obligatorios."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="ignore")

    nombre_completo: str = Field(min_length=3, max_length=200)
    email: EmailStr
    telefono: str = Field(min_length=6, max_length=40)
    rut: str = Field(min_length=3, max_length=20)
    fecha_nacimiento: date
    direccion: str = Field(min_length=3, max_length=255)
    contacto_emergencia: str = Field(min_length=3, max_length=200)

    @field_validator("fecha_nacimiento")
    @classmethod
    def fecha_no_futura(cls, valor: date) -> date:
        """Rechaza una fecha de nacimiento posterior a hoy (sección 9 de SPECS)."""
        if valor > date.today():
            raise ValueError("La fecha no puede ser futura.")
        return valor

    @field_validator("rut")
    @classmethod
    def rut_valido(cls, valor: str) -> str:
        """Normaliza el RUT (sin puntos ni guion) y valida su formato básico."""
        normalizado = (
            valor.replace(".", "").replace("-", "").replace(" ", "").upper()
        )
        if not _PATRON_RUT.match(normalizado):
            raise ValueError("Ingresa un RUT válido (por ejemplo 12.345.678-9).")
        return valor

    @field_validator("telefono")
    @classmethod
    def telefono_valido(cls, valor: str) -> str:
        """Valida que el teléfono tenga dígitos suficientes."""
        if not _PATRON_TELEFONO.match(valor):
            raise ValueError("Ingresa un teléfono válido.")
        return valor

