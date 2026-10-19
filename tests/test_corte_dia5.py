"""T8.7 · Regla del corte al día 5 (RN-03, CA-04)."""

from __future__ import annotations

from datetime import date

import pytest

from app.services import membresias as servicio_membresias
from app.services import pagos as servicio_pagos


@pytest.mark.parametrize(
    ("fecha", "esperado"),
    [
        (date(2026, 3, 1), (2026, 3)),
        (date(2026, 3, 5), (2026, 3)),
        (date(2026, 3, 6), (2026, 4)),
        (date(2026, 3, 31), (2026, 4)),
    ],
)
def test_pago_posterior_al_dia_5_pasa_al_siguiente_ciclo(fecha, esperado):
    assert servicio_pagos.periodo_de_cobro(fecha, 2026, 3) == esperado
    assert servicio_membresias.periodo_imputado(fecha, 2026, 3) == esperado


def test_diciembre_pasa_a_enero_del_anio_siguiente():
    assert servicio_pagos.periodo_de_cobro(date(2026, 12, 6), 2026, 12) == (
        2027,
        1,
    )


def test_meses_anteriores_no_se_desplazan():
    """Un mes anterior indicado explícitamente representa deuda y no se mueve."""
    assert servicio_pagos.periodo_de_cobro(date(2026, 3, 20), 2026, 1) == (2026, 1)
    assert servicio_pagos.periodo_de_cobro(date(2026, 3, 20), 2025, 12) == (
        2025,
        12,
    )


def test_meses_futuros_no_se_desplazan():
    assert servicio_pagos.periodo_de_cobro(date(2026, 3, 20), 2026, 8) == (2026, 8)


def test_limite_exacto_del_dia_5():
    assert servicio_pagos.DIA_CORTE == 5
