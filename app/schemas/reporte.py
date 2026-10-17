"""Esquema de entrada del rango de fechas de reportes (T6.1, UI-09)."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, field_validator

from app.schemas.comunes import fecha_opcional


class RangoFechasEntrada(BaseModel):
    """Rango de fechas del reporte consolidado (F-19, sección 9 de SPECS)."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="ignore")

    desde: date | None = None
    hasta: date | None = None

    @field_validator("desde", "hasta", mode="before")
    @classmethod
    def _fecha_desde_texto(cls, valor: object) -> object:
        return fecha_opcional(valor)
