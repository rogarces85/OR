"""Esquema de entrada del formulario de pago (T6.1, RN-08/RN-17/RN-19)."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.periodos import ANIO_MAXIMO, ANIO_MINIMO
from app.models.pago import MEDIO_TRANSFERENCIA, MEDIOS_PAGO
from app.schemas.comunes import (
    MESES_VALIDOS,
    entero,
    fecha_opcional,
    lista_enteros,
    monto_clp,
    monto_positivo,
)


class PagoEntrada(BaseModel):
    """Datos del pago personalizado: monto libre, periodo y medio (UI-07)."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="ignore")

    monto: int
    medio: str = MEDIO_TRANSFERENCIA
    anio: int
    meses: list[int] = Field(default_factory=list)
    fecha_pago: date | None = None
    observaciones: str = Field(default="", max_length=500)

    @field_validator("monto", mode="before")
    @classmethod
    def _monto_desde_texto(cls, valor: object) -> int:
        return monto_clp(valor)

    @field_validator("monto")
    @classmethod
    def _monto_positivo(cls, valor: int) -> int:
        return monto_positivo(valor)

    @field_validator("anio", mode="before")
    @classmethod
    def _anio_desde_texto(cls, valor: object) -> int:
        if valor is None or (isinstance(valor, str) and not valor.strip()):
            return date.today().year
        return entero(valor)

    @field_validator("anio")
    @classmethod
    def _anio_en_rango(cls, valor: int) -> int:
        if not ANIO_MINIMO <= int(valor) <= ANIO_MAXIMO:
            raise ValueError("El año indicado no es válido.")
        return int(valor)

    @field_validator("meses", mode="before")
    @classmethod
    def _meses_desde_texto(cls, valor: object) -> list[int]:
        return lista_enteros(valor)

    @field_validator("meses")
    @classmethod
    def _meses_validos(cls, valor: list[int]) -> list[int]:
        if not valor:
            raise ValueError("Selecciona al menos un mes a cubrir.")
        if len(set(valor)) != len(valor):
            raise ValueError(
                "No se pueden repetir meses: la selección no es válida."
            )
        if any(int(mes) not in MESES_VALIDOS for mes in valor):
            raise ValueError("Los meses deben estar entre 1 y 12.")
        return [int(mes) for mes in valor]

    @field_validator("medio")
    @classmethod
    def _medio_valido(cls, valor: str) -> str:
        if valor not in MEDIOS_PAGO:
            raise ValueError(
                "El medio de pago debe ser transferencia o efectivo (RN-19)."
            )
        return valor

    @field_validator("fecha_pago", mode="before")
    @classmethod
    def _fecha_desde_texto(cls, valor: object) -> object:
        return fecha_opcional(valor)
