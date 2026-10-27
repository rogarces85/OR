"""Reglas de morosidad: cálculo de deuda y clasificación por color.

Cubre F-11, F-22, RN-04, RN-21, P-5 (solo meses cerrados) y T5.17/T5.18.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from app.models.membresia import (
    ESTADO_EXENTA,
    ESTADO_PAGADA,
    TIPO_MENSUAL,
    CuotaMensual,
)
from app.models.miembro import ACTIVACION_ACTIVO, Miembro
from app.repositories import membresia as repo_membresia
from app.repositories import miembro as repo_miembro

COLOR_VERDE = "verde"
COLOR_NARANJO = "naranjo"
COLOR_ROJO = "rojo"

# Umbrales de RN-21 / D-17: naranjo hasta 3 meses, rojo más de 3.
MESES_HASTA_NARANJO = 3


@dataclass
class MorosidadInfo:
    """Resultado del cálculo de morosidad de un miembro (derivado, no persistido)."""

    miembro_id: int
    meses_deuda: int
    monto_deuda_clp: int
    color: str

    @property
    def al_dia(self) -> bool:
        return self.meses_deuda == 0


def clasificar_color(meses_deuda: int) -> str:
    """Clasifica la morosidad por color según RN-21 / D-17."""
    if meses_deuda <= 0:
        return COLOR_VERDE
    if meses_deuda <= MESES_HASTA_NARANJO:
        return COLOR_NARANJO
    return COLOR_ROJO


def es_mes_cerrado(anio: int, mes: int, referencia: date) -> bool:
    """Indica si el periodo (año/mes) ya cerró respecto de la fecha de referencia.

    El mes en curso no cuenta como deuda (P-5).
    """
    return (anio, mes) < (referencia.year, referencia.month)


def calcular_morosidad(
    miembro: Miembro,
    cuotas: list[CuotaMensual],
    referencia: date | None = None,
    deuda_excluida_clp: int = 0,
) -> MorosidadInfo:
    """Calcula meses y monto de deuda considerando solo meses cerrados (P-5).

    Solo se consideran **cuotas mensuales** (la Matrícula es un cargo único de
    incorporación, no una cuota del ciclo) y **miembros con la membresía activa**,
    porque el ciclo de cobro mensual aplica a los miembros activos y no exentos
    (F-10). Las cuotas exentas no generan deuda (RN-05).

    ``deuda_excluida_clp`` descuenta, desde la deuda más antigua, el monto de las
    negociaciones ya aceptadas (P-6): esa deuda deja de contar para el color.
    """
    if miembro.situacion_activacion != ACTIVACION_ACTIVO:
        return MorosidadInfo(
            miembro_id=miembro.id,
            meses_deuda=0,
            monto_deuda_clp=0,
            color=COLOR_VERDE,
        )
    fecha_referencia = referencia or date.today()
    meses_deuda = 0
    monto_deuda = 0
    excluir = max(int(deuda_excluida_clp), 0)
    for cuota in cuotas:
        if not es_mes_cerrado(cuota.anio, cuota.mes, fecha_referencia):
            continue
        if cuota.estado in (ESTADO_PAGADA, ESTADO_EXENTA):
            continue
        if cuota.nivel is not None and cuota.nivel.tipo != TIPO_MENSUAL:
            continue
        saldo = cuota.monto_clp - cuota.monto_pagado_clp
        if saldo <= 0:
            continue
        if excluir >= saldo:
            # Mes cubierto por la deuda negociada aceptada (P-6).
            excluir -= saldo
            continue
        saldo_efectivo = saldo - excluir
        excluir = 0
        meses_deuda += 1
        monto_deuda += saldo_efectivo
    return MorosidadInfo(
        miembro_id=miembro.id,
        meses_deuda=meses_deuda,
        monto_deuda_clp=monto_deuda,
        color=clasificar_color(meses_deuda),
    )


def listar_miembros_con_morosidad(
    db: Session,
    *,
    texto: str | None = None,
    categoria: str | None = None,
    situacion: str | None = None,
    color: str | None = None,
    referencia: date | None = None,
    incluir_bajas: bool = False,
) -> list[tuple[Miembro, MorosidadInfo]]:
    """Lista miembros con su morosidad calculada, aplicando filtros (T5.2).

    Solo se consideran las cuotas mensuales (no la Matrícula), conforme a F-11.
    La deuda negociada aceptada se excluye del color (P-6, T5.22).
    """
    miembros = repo_miembro.listar(
        db,
        texto=texto,
        categoria=categoria,
        situacion=situacion,
        incluir_bajas=incluir_bajas,
    )
    ids = [miembro.id for miembro in miembros]
    cuotas_por_miembro = repo_membresia.cuotas_por_miembros(
        db, ids, solo_mensuales=True
    )
    deudas_excluidas = repo_membresia.deudas_negociadas_por_miembros(db, ids)
    filas: list[tuple[Miembro, MorosidadInfo]] = []
    for miembro in miembros:
        info = calcular_morosidad(
            miembro,
            cuotas_por_miembro.get(miembro.id, []),
            referencia,
            deuda_excluida_clp=deudas_excluidas.get(miembro.id, 0),
        )
        if color and info.color != color:
            continue
        filas.append((miembro, info))
    return filas
