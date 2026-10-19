"""T8.6 · Negociación de deuda (RN-22, P-6, CA-25)."""

from __future__ import annotations

from datetime import date

import pytest

from app.models.membresia import (
    ESTADO_ACEPTADA,
    ESTADO_NEGOCIACION_PAGADA,
    ESTADO_PROPUESTA,
    NIVEL_ACTIVA,
)
from app.models.pago import Pago
from app.repositories import membresia as repo_membresia
from app.services import negociacion as servicio_negociacion
from app.services.morosidad import (
    COLOR_ROJO,
    COLOR_VERDE,
    calcular_morosidad,
)

REFERENCIA = date(2026, 6, 15)


def _periodos_cerrados(cantidad: int) -> list[tuple[int, int]]:
    """Últimos ``cantidad`` meses cerrados respecto de ``REFERENCIA``."""
    total_ref = REFERENCIA.year * 12 + (REFERENCIA.month - 1)
    return [
        ((total_ref - cantidad + indice) // 12, (total_ref - cantidad + indice) % 12 + 1)
        for indice in range(cantidad)
    ]


def _miembro_con_deuda(db, niveles, miembro_factory, cuota_factory, meses: int):
    """Crea un miembro activo con ``meses`` cuotas cerradas impagas."""
    miembro = miembro_factory()
    activa = niveles[NIVEL_ACTIVA]
    for anio, mes in _periodos_cerrados(meses):
        cuota_factory(miembro, activa, anio, mes)
    cuotas = repo_membresia.cuotas_mensuales_de_miembro(db, miembro.id)
    return miembro, cuotas


def test_elegibilidad_mas_de_seis_meses():
    """Solo los morosos de más de 6 meses pueden negociar (RN-22)."""
    from app.services.morosidad import MorosidadInfo

    assert servicio_negociacion.puede_negociar(
        MorosidadInfo(miembro_id=1, meses_deuda=6, monto_deuda_clp=90_000, color=COLOR_ROJO)
    ) is False
    assert servicio_negociacion.puede_negociar(
        MorosidadInfo(miembro_id=1, meses_deuda=7, monto_deuda_clp=105_000, color=COLOR_ROJO)
    ) is True


def test_crear_negociacion_bloquea_menos_de_seis_meses(
    db, niveles, miembro_factory, cuota_factory
):
    miembro, cuotas = _miembro_con_deuda(
        db, niveles, miembro_factory, cuota_factory, meses=5
    )
    info = calcular_morosidad(miembro, cuotas, REFERENCIA)

    with pytest.raises(servicio_negociacion.ErrorNegociacion):
        servicio_negociacion.crear_negociacion(
            db, miembro=miembro, info=info, descuento_pct=10
        )


@pytest.mark.parametrize("descuento", [-1, 101, None])
def test_descuento_fuera_de_rango(descuento):
    with pytest.raises(servicio_negociacion.ErrorNegociacion):
        servicio_negociacion.calcular_monto_negociado(100_000, descuento)


@pytest.mark.parametrize(
    ("deuda", "descuento", "esperado"),
    [
        (100_000, 0, 100_000),
        (100_000, 20, 80_000),
        (105_000, 30, 73_500),
        (100_000, 100, 0),
    ],
)
def test_calculo_del_monto_negociado(deuda, descuento, esperado):
    assert servicio_negociacion.calcular_monto_negociado(deuda, descuento) == esperado


def test_crear_negociacion_propuesta(
    db, niveles, miembro_factory, cuota_factory
):
    """Un moroso de 7 meses puede negociar con un % editable (CA-25)."""
    miembro, cuotas = _miembro_con_deuda(
        db, niveles, miembro_factory, cuota_factory, meses=7
    )
    info = calcular_morosidad(miembro, cuotas, REFERENCIA)
    assert info.meses_deuda == 7

    negociacion = servicio_negociacion.crear_negociacion(
        db, miembro=miembro, info=info, descuento_pct=25
    )

    assert negociacion.estado == ESTADO_PROPUESTA
    assert negociacion.deuda_total_clp == 105_000
    assert negociacion.descuento_pct == 25
    assert negociacion.monto_negociado_clp == 78_750


def test_efecto_en_el_color_al_aceptar(
    db, niveles, miembro_factory, cuota_factory
):
    """En "propuesta" la deuda cuenta; al aceptar, deja de contar (P-6)."""
    miembro, cuotas = _miembro_con_deuda(
        db, niveles, miembro_factory, cuota_factory, meses=7
    )
    info = calcular_morosidad(miembro, cuotas, REFERENCIA)
    assert info.color == COLOR_ROJO

    negociacion = servicio_negociacion.crear_negociacion(
        db, miembro=miembro, info=info, descuento_pct=20
    )
    # Aún en propuesta: la deuda sigue contando.
    excluida = repo_membresia.deuda_negociada_clp(db, miembro.id)
    assert excluida == 0
    assert calcular_morosidad(
        miembro, cuotas, REFERENCIA, deuda_excluida_clp=excluida
    ).color == COLOR_ROJO

    servicio_negociacion.aceptar_negociacion(db, negociacion)
    assert negociacion.estado == ESTADO_ACEPTADA

    excluida = repo_membresia.deuda_negociada_clp(db, miembro.id)
    assert excluida == 105_000
    assert calcular_morosidad(
        miembro, cuotas, REFERENCIA, deuda_excluida_clp=excluida
    ).color == COLOR_VERDE


def test_solo_una_propuesta_puede_aceptarse(
    db, niveles, miembro_factory, cuota_factory
):
    miembro, cuotas = _miembro_con_deuda(
        db, niveles, miembro_factory, cuota_factory, meses=7
    )
    info = calcular_morosidad(miembro, cuotas, REFERENCIA)
    negociacion = servicio_negociacion.crear_negociacion(
        db, miembro=miembro, info=info, descuento_pct=10
    )
    servicio_negociacion.aceptar_negociacion(db, negociacion)

    with pytest.raises(servicio_negociacion.ErrorNegociacion):
        servicio_negociacion.aceptar_negociacion(db, negociacion)


def test_pago_de_la_negociacion_la_marca_pagada(
    db, niveles, miembro_factory, cuota_factory
):
    """Registrar el pago descarga la deuda y actualiza el estado (T5.23)."""
    miembro, cuotas = _miembro_con_deuda(
        db, niveles, miembro_factory, cuota_factory, meses=7
    )
    info = calcular_morosidad(miembro, cuotas, REFERENCIA)
    negociacion = servicio_negociacion.crear_negociacion(
        db, miembro=miembro, info=info, descuento_pct=20
    )
    servicio_negociacion.aceptar_negociacion(db, negociacion)

    pago = servicio_negociacion.registrar_pago_negociacion(db, negociacion=negociacion)

    assert isinstance(pago, Pago)
    assert pago.monto_clp == 84_000
    assert pago.miembro_id == miembro.id
    assert negociacion.estado == ESTADO_NEGOCIACION_PAGADA
    assert repo_membresia.deuda_negociada_clp(db, miembro.id) == 105_000

    with pytest.raises(servicio_negociacion.ErrorNegociacion):
        servicio_negociacion.registrar_pago_negociacion(db, negociacion=negociacion)
