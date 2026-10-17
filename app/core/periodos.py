"""Utilidades de periodo (año/mes) compartidas por los módulos del sistema."""

from __future__ import annotations

# Nombres de los meses en español (RN-16), indexables desde 1.
MESES_NOMBRES: tuple[str, ...] = (
    "Enero",
    "Febrero",
    "Marzo",
    "Abril",
    "Mayo",
    "Junio",
    "Julio",
    "Agosto",
    "Septiembre",
    "Octubre",
    "Noviembre",
    "Diciembre",
)

ANIO_MINIMO = 2000
ANIO_MAXIMO = 2100


def nombre_mes(mes: int) -> str:
    """Devuelve el nombre del mes (1–12) en español."""
    if 1 <= mes <= 12:
        return MESES_NOMBRES[mes - 1]
    return str(mes)


def periodo_valido(anio: int, mes: int) -> bool:
    """Indica si el par año/mes es un periodo admisible."""
    return ANIO_MINIMO <= int(anio) <= ANIO_MAXIMO and 1 <= int(mes) <= 12


def siguiente_periodo(anio: int, mes: int) -> tuple[int, int]:
    """Devuelve el periodo inmediatamente siguiente (año/mes)."""
    total = int(anio) * 12 + (int(mes) - 1) + 1
    return total // 12, total % 12 + 1
