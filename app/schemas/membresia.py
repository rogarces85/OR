"""Esquema de entrada de la generación de cuotas (T6.1, T5.8)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator

from app.core.periodos import ANIO_MAXIMO, ANIO_MINIMO
from app.schemas.comunes import MESES_VALIDOS, entero


class GeneracionCuotasEntrada(BaseModel):
    """Periodo (año y mes) para generar las cuotas mensuales."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="ignore")

    anio: int
    mes: int

    @field_validator("anio", "mes", mode="before")
    @classmethod
    def _entero_desde_texto(cls, valor: object) -> int:
        return entero(valor)

    @field_validator("anio")
    @classmethod
    def _anio_en_rango(cls, valor: int) -> int:
        if not ANIO_MINIMO <= int(valor) <= ANIO_MAXIMO:
            raise ValueError("Indica un periodo válido para generar las cuotas.")
        return int(valor)

    @field_validator("mes")
    @classmethod
    def _mes_valido(cls, valor: int) -> int:
        if int(valor) not in MESES_VALIDOS:
            raise ValueError("Indica un periodo válido para generar las cuotas.")
        return int(valor)
