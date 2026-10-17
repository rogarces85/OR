"""Esquemas de entrada de los formularios de finanzas (T6.1, RN-10)."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.comunes import (
    entero,
    entero_opcional,
    fecha_opcional,
    monto_clp,
    monto_positivo,
)


class _BaseEntrada(BaseModel):
    """Configuración común: recorta espacios e ignora campos desconocidos."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="ignore")


class EgresoEntrada(_BaseEntrada):
    """Egreso con monto, concepto, categoría y fecha (F-16, CA-07)."""

    monto: int
    concepto: str = Field(min_length=1, max_length=200)
    categoria_id: int
    fecha: date | None = None

    @field_validator("monto", mode="before")
    @classmethod
    def _monto_desde_texto(cls, valor: object) -> int:
        return monto_clp(valor)

    @field_validator("monto")
    @classmethod
    def _monto_positivo(cls, valor: int) -> int:
        return monto_positivo(valor)

    @field_validator("categoria_id", mode="before")
    @classmethod
    def _categoria(cls, valor: object) -> int:
        if valor is None or (isinstance(valor, str) and not valor.strip()):
            raise ValueError(
                "Debes seleccionar una categoría de egreso válida (RN-10)."
            )
        return entero(valor)

    @field_validator("fecha", mode="before")
    @classmethod
    def _fecha_desde_texto(cls, valor: object) -> object:
        return fecha_opcional(valor)


class ActivoEntrada(_BaseEntrada):
    """Activo adquirido por el club con su responsable de compra (F-17)."""

    costo: int
    descripcion: str = Field(min_length=1, max_length=200)
    miembro_responsable_id: int | None = None
    fecha: date | None = None

    @field_validator("costo", mode="before")
    @classmethod
    def _costo_desde_texto(cls, valor: object) -> int:
        return monto_clp(valor)

    @field_validator("costo")
    @classmethod
    def _costo_positivo(cls, valor: int) -> int:
        return monto_positivo(valor)

    @field_validator("miembro_responsable_id", mode="before")
    @classmethod
    def _responsable(cls, valor: object) -> int | None:
        return entero_opcional(valor)

    @field_validator("fecha", mode="before")
    @classmethod
    def _fecha_desde_texto(cls, valor: object) -> object:
        return fecha_opcional(valor)


class GastoFijoEntrada(_BaseEntrada):
    """Gasto fijo operativo mensual (F-18, CA-09)."""

    monto: int
    concepto: str = Field(min_length=1, max_length=200)
    fecha: date | None = None

    @field_validator("monto", mode="before")
    @classmethod
    def _monto_desde_texto(cls, valor: object) -> int:
        return monto_clp(valor)

    @field_validator("monto")
    @classmethod
    def _monto_positivo(cls, valor: int) -> int:
        return monto_positivo(valor)

    @field_validator("fecha", mode="before")
    @classmethod
    def _fecha_desde_texto(cls, valor: object) -> object:
        return fecha_opcional(valor)


class CategoriaEntrada(_BaseEntrada):
    """Nombre de una categoría de egreso personalizada (RN-10, P-7)."""

    nombre: str = Field(min_length=3, max_length=100)
