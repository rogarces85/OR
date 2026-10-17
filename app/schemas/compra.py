"""Esquemas de entrada de compras y cargos a alumnos (T6.1, F-25/RN-23)."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.pago import MEDIO_TRANSFERENCIA, MEDIOS_PAGO
from app.schemas.comunes import (
    entero,
    entero_positivo,
    fecha_opcional,
    monto_clp,
)


class _BaseEntrada(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="ignore")


class ItemCompraEntrada(_BaseEntrada):
    """Ítem de una compra: descripción, precio unitario y cantidad."""

    descripcion: str = Field(min_length=1, max_length=200)
    precio_unitario_clp: int
    cantidad: int = 1

    @field_validator("precio_unitario_clp", mode="before")
    @classmethod
    def _precio_desde_texto(cls, valor: object) -> int:
        return monto_clp(valor)

    @field_validator("precio_unitario_clp")
    @classmethod
    def _precio_positivo(cls, valor: int) -> int:
        if int(valor) <= 0:
            raise ValueError(
                "El precio unitario debe ser un entero positivo."
            )
        return int(valor)

    @field_validator("cantidad", mode="before")
    @classmethod
    def _cantidad_desde_texto(cls, valor: object) -> int:
        if valor is None or (isinstance(valor, str) and not valor.strip()):
            return 1
        return entero(valor)

    @field_validator("cantidad")
    @classmethod
    def _cantidad_positiva(cls, valor: int) -> int:
        if int(valor) <= 0:
            raise ValueError("La cantidad debe ser al menos 1.")
        return int(valor)


class CompraEntrada(_BaseEntrada):
    """Compra del club con al menos un ítem (F-25, T5.29)."""

    descripcion: str = Field(min_length=1, max_length=200)
    proveedor: str = Field(default="", max_length=200)
    fecha: date | None = None
    items: list[ItemCompraEntrada] = Field(default_factory=list)

    @field_validator("items")
    @classmethod
    def _items_obligatorios(cls, valor: list[ItemCompraEntrada]) -> list:
        if not valor:
            raise ValueError("La compra debe tener al menos un ítem.")
        return valor

    @field_validator("fecha", mode="before")
    @classmethod
    def _fecha_desde_texto(cls, valor: object) -> object:
        return fecha_opcional(valor)


class AsignacionCargoEntrada(_BaseEntrada):
    """Asignación de un ítem de la compra a un alumno (F-25, CA-27)."""

    compra_item_id: int
    miembro_id: int
    cantidad: int = 1

    @field_validator("compra_item_id", "miembro_id", mode="before")
    @classmethod
    def _identificador(cls, valor: object) -> int:
        return entero_positivo(valor)

    @field_validator("cantidad", mode="before")
    @classmethod
    def _cantidad_desde_texto(cls, valor: object) -> int:
        if valor is None or (isinstance(valor, str) and not valor.strip()):
            return 1
        return entero(valor)

    @field_validator("cantidad")
    @classmethod
    def _cantidad_positiva(cls, valor: int) -> int:
        return entero_positivo(valor)


class SaldarCargoEntrada(_BaseEntrada):
    """Pago de un cargo de alumno con un medio válido (RN-19)."""

    medio: str = MEDIO_TRANSFERENCIA

    @field_validator("medio")
    @classmethod
    def _medio_valido(cls, valor: str) -> str:
        if valor not in MEDIOS_PAGO:
            raise ValueError("El medio de pago no es válido (RN-19).")
        return valor
