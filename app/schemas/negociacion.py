"""Esquema de entrada de la negociación de deuda (T6.1, RN-22)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator

from app.schemas.comunes import entero, entero_positivo


class NegociacionEntrada(BaseModel):
    """Miembro elegible y descuento editable en porcentaje (CA-25)."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="ignore")

    miembro_id: int
    descuento_pct: int = 0

    @field_validator("miembro_id", mode="before")
    @classmethod
    def _miembro(cls, valor: object) -> int:
        return entero_positivo(valor)

    @field_validator("descuento_pct", mode="before")
    @classmethod
    def _descuento_desde_texto(cls, valor: object) -> int:
        if valor is None or (isinstance(valor, str) and not valor.strip()):
            return 0
        return entero(valor)

    @field_validator("descuento_pct")
    @classmethod
    def _descuento_en_rango(cls, valor: int) -> int:
        if not 0 <= int(valor) <= 100:
            raise ValueError("El descuento debe estar entre 0 y 100 (%).")
        return int(valor)
