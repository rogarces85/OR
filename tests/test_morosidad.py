"""T8.5 · Morosidad y colores: solo meses cerrados (P-5, RN-21, CA-24)."""

from __future__ import annotations

from datetime import date

import pytest

from app.models.membresia import (
    ESTADO_EXENTA,
    ESTADO_PAGADA,
    ESTADO_PARCIAL,
    ESTADO_PENDIENTE,
    NIVEL_ACTIVA,
    NIVEL_MATRICULA,
    CuotaMensual,
)
from app.models.miembro import ACTIVACION_PENDIENTE
from app.services.morosidad import (
    COLOR_NARANJO,
    COLOR_ROJO,
    COLOR_VERDE,
    calcular_morosidad,
    clasificar_color,
    es_mes_cerrado,
)

REFERENCIA = date(2026, 6, 15)


def _cuotas_mensuales(factory, miembro, nivel, meses, **kwargs):
    return [
        factory(miembro, nivel, 2026, mes, **kwargs)
        for mes in meses
    ]


@pytest.mark.parametrize(
    ("meses_deuda", "color"),
    [
        (0, COLOR_VERDE),
        (1, COLOR_NARANJO),
        (2, COLOR_NARANJO),
        (3, COLOR_NARANJO),
        (4, COLOR_ROJO),
        (6, COLOR_ROJO),
    ],
)
def test_clasificacion_por_color(meses_deuda, color):
    assert clasificar_color(meses_deuda) == color


def test_mes_en_curso_no_cuenta_como_deuda(
    db, niveles, miembro_factory, cuota_factory
):
    """Enero a mayo impagos y junio (en curso) impago: 5 meses de deuda."""
    miembro = miembro_factory()
    activa = niveles[NIVEL_ACTIVA]
    cuotas = _cuotas_mensuales(cuota_factory, miembro, activa, range(1, 7))

    info = calcular_morosidad(miembro, cuotas, REFERENCIA)

    assert info.meses_deuda == 5
    assert info.monto_deuda_clp == 75_000
    assert info.color == COLOR_ROJO


def test_cuota_pagada_no_cuenta(db, niveles, miembro_factory, cuota_factory):
    """Solo las cuotas con saldo pendiente generan deuda."""
    miembro = miembro_factory()
    activa = niveles[NIVEL_ACTIVA]
    cuotas = [
        cuota_factory(miembro, activa, 2026, 1, estado=ESTADO_PAGADA, pagado=15_000),
        cuota_factory(miembro, activa, 2026, 2),
    ]

    info = calcular_morosidad(miembro, cuotas, REFERENCIA)

    assert info.meses_deuda == 1
    assert info.monto_deuda_clp == 15_000
    assert info.color == COLOR_NARANJO


def test_cuota_exenta_no_cuenta(db, niveles, miembro_factory, cuota_factory):
    """Las cuotas exentas no generan deuda (RN-05)."""
    miembro = miembro_factory(exento=True)
    activa = niveles[NIVEL_ACTIVA]
    cuotas = _cuotas_mensuales(
        cuota_factory, miembro, activa, range(1, 4), estado=ESTADO_EXENTA
    )

    info = calcular_morosidad(miembro, cuotas, REFERENCIA)

    assert info.meses_deuda == 0
    assert info.monto_deuda_clp == 0
    assert info.color == COLOR_VERDE


def test_cuota_parcial_suma_su_saldo(db, niveles, miembro_factory, cuota_factory):
    """Una cuota parcial cuenta como deuda por el saldo que falta pagar."""
    miembro = miembro_factory()
    activa = niveles[NIVEL_ACTIVA]
    cuotas = [
        cuota_factory(
            miembro, activa, 2026, 1, pagado=5_000, estado=ESTADO_PARCIAL
        )
    ]

    info = calcular_morosidad(miembro, cuotas, REFERENCIA)

    assert info.meses_deuda == 1
    assert info.monto_deuda_clp == 10_000


def test_matricula_no_cuenta_para_la_morosidad(
    db, niveles, miembro_factory, cuota_factory
):
    """La Matrícula es un cargo único: no forma parte de la deuda mensual (F-11)."""
    miembro = miembro_factory()
    cuotas = [cuota_factory(miembro, niveles[NIVEL_MATRICULA], 2026, 1)]

    info = calcular_morosidad(miembro, cuotas, REFERENCIA)

    assert info.meses_deuda == 0
    assert info.monto_deuda_clp == 0


def test_miembro_pendiente_no_es_moroso(
    db, niveles, miembro_factory, cuota_factory
):
    """Un miembro que aún no se activa no se clasifica como moroso."""
    miembro = miembro_factory(activo=False)
    assert miembro.situacion_activacion == ACTIVACION_PENDIENTE
    cuotas = _cuotas_mensuales(
        cuota_factory, miembro, niveles[NIVEL_ACTIVA], range(1, 6)
    )

    info = calcular_morosidad(miembro, cuotas, REFERENCIA)

    assert info.meses_deuda == 0
    assert info.color == COLOR_VERDE


def test_deuda_negociada_descuenta_desde_la_mas_antigua(
    db, niveles, miembro_factory, cuota_factory
):
    """La deuda excluida (negociación aceptada) se descuenta de la más antigua (P-6)."""
    miembro = miembro_factory()
    cuotas = _cuotas_mensuales(
        cuota_factory, miembro, niveles[NIVEL_ACTIVA], range(1, 6)
    )

    info = calcular_morosidad(miembro, cuotas, REFERENCIA, deuda_excluida_clp=30_000)

    assert info.meses_deuda == 3
    assert info.monto_deuda_clp == 45_000
    assert info.color == COLOR_NARANJO


def test_es_mes_cerrado():
    assert es_mes_cerrado(2026, 5, REFERENCIA) is True
    assert es_mes_cerrado(2026, 6, REFERENCIA) is False
    assert es_mes_cerrado(2026, 7, REFERENCIA) is False
    assert es_mes_cerrado(2025, 12, REFERENCIA) is True


def test_cuota_pendiente_sin_saldo_no_cuenta(
    db, niveles, miembro_factory
):
    """Una cuota pendiente con monto ya cubierto no aporta deuda."""
    miembro = miembro_factory()
    cuota = CuotaMensual(
        miembro_id=miembro.id,
        anio=2026,
        mes=1,
        nivel_cuota_id=niveles[NIVEL_ACTIVA].id,
        monto_clp=15_000,
        monto_pagado_clp=15_000,
        estado=ESTADO_PENDIENTE,
    )

    info = calcular_morosidad(miembro, [cuota], REFERENCIA)

    assert info.meses_deuda == 0
