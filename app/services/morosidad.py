"""Reglas de morosidad: cálculo de deuda y clasificación por color.

Cubre F-11, F-22, RN-04, RN-21, P-5 (solo meses cerrados) y T5.17/T5.18.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from app.models.membresia import ESTADO_EXENTA, ESTADO_PAGADA, CuotaMensual
from app.models.miembro import Miembro
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
) -> MorosidadInfo:
    """Calcula meses y monto de deuda considerando solo meses cerrados (P-5)."""
    fecha_referencia = referencia or date.today()
    meses_deuda = 0
    monto_deuda = 0
    for cuota in cuotas:
        if not es_mes_cerrado(cuota.anio, cuota.mes, fecha_referencia):
            continue
        if cuota.estado in (ESTADO_PAGADA, ESTADO_EXENTA):
            continue
        saldo = cuota.monto_clp - cuota.monto_pagado_clp
        if saldo <= 0:
            continue
        meses_deuda += 1
        monto_deuda += saldo
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
) -> list[tuple[Miembro, MorosidadInfo]]:
    """Lista miembros con su morosidad calculada, aplicando filtros (T5.2).

    Nota: el efecto de la negociación aceptada (P-6) se aplicará cuando se
    implemente el módulo de negociación (Fase 5.E); en el MVP Nivel B no hay
    negociaciones registradas.
    """
    miembros = repo_miembro.listar(
        db, texto=texto, categoria=categoria, situacion=situacion
    )
    cuotas_por_miembro = repo_membresia.cuotas_por_miembros(
        db, [miembro.id for miembro in miembros]
    )
    filas: list[tuple[Miembro, MorosidadInfo]] = []
    for miembro in miembros:
        info = calcular_morosidad(
            miembro, cuotas_por_miembro.get(miembro.id, []), referencia
        )
        if color and info.color != color:
            continue
        filas.append((miembro, info))
    return filas
