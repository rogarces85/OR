"""Formato y parseo de montos en CLP (F-27, RN-24, D-23)."""

from __future__ import annotations


def formatear_clp(monto: int | None) -> str:
    """Devuelve el monto en CLP con separador de miles por punto y sin decimales.

    >>> formatear_clp(45000)
    '45.000'
    """
    if monto is None:
        return ""
    return f"{int(monto):,}".replace(",", ".")


def parsear_clp(texto: str | None) -> int:
    """Convierte un monto escrito por el usuario (por ejemplo ``"45.000"``) a entero.

    Lanza ``ValueError`` si el texto no representa un número entero.
    """
    limpio = (texto or "").strip().replace("$", "").replace(".", "").replace(" ", "")
    if not limpio:
        raise ValueError("El monto es obligatorio.")
    try:
        return int(limpio)
    except ValueError as exc:
        raise ValueError("El monto debe ser un número entero, sin decimales.") from exc
