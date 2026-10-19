"""Formato CLP (RN-24, CA-26)."""

from __future__ import annotations

import pytest

from app.core.formato import formatear_clp, parsear_clp
from app.dependencies import templates


@pytest.mark.parametrize(
    ("monto", "texto"),
    [
        (0, "0"),
        (5_000, "5.000"),
        (45_000, "45.000"),
        (1_250_000, "1.250.000"),
        (None, ""),
    ],
)
def test_formatear_clp(monto, texto):
    assert formatear_clp(monto) == texto


@pytest.mark.parametrize(
    ("texto", "monto"),
    [
        ("45.000", 45_000),
        ("$ 45.000", 45_000),
        (" 1.250.000 ", 1_250_000),
        (45000, 45_000),
    ],
)
def test_parsear_clp(texto, monto):
    assert parsear_clp(str(texto)) == monto


@pytest.mark.parametrize("texto", ["", "   ", "abc", "45.000,50"])
def test_parsear_clp_invalido(texto):
    with pytest.raises(ValueError):
        parsear_clp(texto)


def test_filtro_jinja_clp():
    assert templates.env.filters["clp"](45_000) == "45.000"
