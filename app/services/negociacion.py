"""Negociación de deuda de morosos de más de 6 meses (F-24, RN-22, P-6).

Cubre T5.21 (elegibilidad y cálculo del descuento), T5.22 (crear/aceptar y efecto
en el color) y T5.23 (registro del pago de la negociación).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.membresia import (
    ESTADO_ACEPTADA,
    ESTADO_NEGOCIACION_PAGADA,
    ESTADO_PROPUESTA,
    NegociacionDeuda,
)
from app.models.miembro import Miembro
from app.models.pago import MEDIO_TRANSFERENCIA, Pago
from app.repositories import membresia as repo_membresia
from app.repositories import pago as repo_pago
from app.services.morosidad import MorosidadInfo

# La negociación aplica a morosos de **más de** 6 meses de deuda (RN-22).
MESES_MINIMOS = 6

ETIQUETAS_ESTADO: dict[str, str] = {
    ESTADO_PROPUESTA: "Propuesta",
    ESTADO_ACEPTADA: "Aceptada",
    ESTADO_NEGOCIACION_PAGADA: "Pagada",
}


class ErrorNegociacion(ValueError):
    """Error de validación de una negociación, con mensaje en español."""


def puede_negociar(info: MorosidadInfo) -> bool:
    """Indica si el miembro es elegible: moroso de más de 6 meses (RN-22)."""
    return info.meses_deuda > MESES_MINIMOS


def calcular_monto_negociado(deuda_total_clp: int, descuento_pct: int) -> int:
    """Calcula el monto negociado aplicando el descuento (0–100) sobre la deuda."""
    if descuento_pct is None or not 0 <= int(descuento_pct) <= 100:
        raise ErrorNegociacion("El descuento debe estar entre 0 y 100 (%).")
    deuda = max(int(deuda_total_clp), 0)
    monto = round(deuda * (100 - int(descuento_pct)) / 100)
    return int(monto)


def crear_negociacion(
    db: Session,
    *,
    miembro: Miembro,
    info: MorosidadInfo,
    descuento_pct: int,
    usuario: Any | None = None,
) -> NegociacionDeuda:
    """Registra una negociación en estado "propuesta" para un moroso elegible."""
    if not puede_negociar(info):
        raise ErrorNegociacion(
            "Solo se puede negociar la deuda de morosos de más de 6 meses (RN-22)."
        )
    monto = calcular_monto_negociado(info.monto_deuda_clp, descuento_pct)
    negociacion = repo_membresia.crear_negociacion(
        db,
        miembro_id=miembro.id,
        deuda_total_clp=int(info.monto_deuda_clp),
        descuento_pct=int(descuento_pct),
        monto_negociado_clp=monto,
        usuario_id=getattr(usuario, "id", None),
    )
    db.commit()
    db.refresh(negociacion)
    return negociacion


def aceptar_negociacion(
    db: Session, negociacion: NegociacionDeuda
) -> NegociacionDeuda:
    """Marca la negociación como **aceptada**: su deuda deja de contar (P-6)."""
    if negociacion.estado != ESTADO_PROPUESTA:
        raise ErrorNegociacion("Solo una negociación propuesta puede aceptarse.")
    negociacion.estado = ESTADO_ACEPTADA
    return repo_membresia.guardar_negociacion(db, negociacion)


def registrar_pago_negociacion(
    db: Session,
    *,
    negociacion: NegociacionDeuda,
    medio: str = MEDIO_TRANSFERENCIA,
    observaciones: str | None = None,
    usuario: Any | None = None,
) -> Pago:
    """Registra el pago de la negociación y descarga la deuda (T5.23).

    El pago se guarda como ingreso del miembro (no se imputa a las cuotas: es el
    pago del monto negociado) y la negociación pasa a "pagada".
    """
    if negociacion.estado == ESTADO_NEGOCIACION_PAGADA:
        raise ErrorNegociacion("Esta negociación ya fue pagada.")
    pago = repo_pago.crear(
        db,
        miembro_id=negociacion.miembro_id,
        monto_clp=int(negociacion.monto_negociado_clp),
        medio=medio,
        observaciones=(
            observaciones or f"Pago de deuda negociada #{negociacion.id}"
        ),
        registrado_por=getattr(usuario, "id", None),
    )
    negociacion.estado = ESTADO_NEGOCIACION_PAGADA
    db.add(negociacion)
    db.commit()
    db.refresh(pago)
    db.refresh(negociacion)
    return pago


def deuda_excluida_clp(db: Session, miembro_id: int) -> int:
    """Deuda que no cuenta para el color por negociaciones aceptadas/pagadas."""
    return repo_membresia.deuda_negociada_clp(db, miembro_id)
