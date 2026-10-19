"""Caché en proceso para catálogos estáticos (T9.4).

Los catálogos que cambian muy poco (niveles de cuota, cuenta bancaria y
categorías de egreso) se leen en casi todas las pantallas. Para no consultarlos
en cada request se guardan en memoria con un TTL corto. La clave incluye el
motor de base de datos, de modo que sesiones y bases de prueba no comparten
entradas.

Las operaciones de escritura sobre esos catálogos invalidan las entradas
correspondientes; además, la semilla limpia la caché al comenzar y al terminar.
"""

from __future__ import annotations

from collections.abc import Callable, Hashable
from time import monotonic
from typing import TypeVar

from sqlalchemy.orm import Session

T = TypeVar("T")

TTL_SEGUNDOS = 60.0

_cache: dict[Hashable, tuple[float, object]] = {}


def _clave(db: Session, nombre: str) -> tuple[int, str]:
    """Identifica la entrada por motor de base de datos y nombre lógico."""
    return (id(db.get_bind()), nombre)


def obtener(
    db: Session,
    nombre: str,
    fabrica: Callable[[], T],
    *,
    ttl: float = TTL_SEGUNDOS,
) -> T:
    """Devuelve el valor cacheado o lo construye con ``fabrica``."""
    clave = _clave(db, nombre)
    ahora = monotonic()
    entrada = _cache.get(clave)
    if entrada is not None and entrada[0] > ahora:
        return entrada[1]  # type: ignore[return-value]
    valor = fabrica()
    _cache[clave] = (ahora + ttl, valor)
    return valor


def invalidar(db: Session, *nombres: str) -> None:
    """Elimina las entradas indicadas para el motor de ``db``."""
    for nombre in nombres:
        _cache.pop(_clave(db, nombre), None)


def limpiar() -> None:
    """Vacía toda la caché (semilla, pruebas y cambios masivos)."""
    _cache.clear()
