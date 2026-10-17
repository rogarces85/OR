"""Consultas y persistencia de pagos, imputaciones y abonos (T3.8)."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.pago import (
    ESTADO_DISPONIBLE,
    MEDIO_TRANSFERENCIA,
    Abono,
    ImputacionPago,
    Pago,
)


def listar(
    db: Session, *, desde: date | None = None, hasta: date | None = None
) -> list[Pago]:
    """Lista pagos, opcionalmente acotados a un rango de fechas (F-15)."""
    consulta = select(Pago).order_by(Pago.fecha_pago.desc(), Pago.id.desc())
    if desde is not None:
        consulta = consulta.where(Pago.fecha_pago >= desde)
    if hasta is not None:
        consulta = consulta.where(Pago.fecha_pago <= hasta)
    return list(db.scalars(consulta))


def pagos_de_miembro(db: Session, miembro_id: int) -> list[Pago]:
    """Lista los pagos de un miembro, del más reciente al más antiguo."""
    return list(
        db.scalars(
            select(Pago)
            .where(Pago.miembro_id == miembro_id)
            .order_by(Pago.fecha_pago.desc(), Pago.id.desc())
        )
    )


def crear(
    db: Session,
    *,
    miembro_id: int,
    monto_clp: int,
    fecha_pago: date | None = None,
    medio: str = MEDIO_TRANSFERENCIA,
    observaciones: str | None = None,
    registrado_por: int | None = None,
) -> Pago:
    """Crea un pago (sin confirmar la transacción; la imputación la hace el servicio)."""
    pago = Pago(
        miembro_id=miembro_id,
        monto_clp=monto_clp,
        fecha_pago=fecha_pago or date.today(),
        medio=medio,
        observaciones=observaciones,
        registrado_por=registrado_por,
    )
    db.add(pago)
    return pago


def imputar(
    db: Session, *, pago_id: int, cuota_id: int | None, monto_clp: int, orden: int = 0
) -> ImputacionPago:
    """Registra la imputación de parte de un pago a una cuota (F-13)."""
    imputacion = ImputacionPago(
        pago_id=pago_id, cuota_id=cuota_id, monto_clp=monto_clp, orden=orden
    )
    db.add(imputacion)
    return imputacion


def crear_abono(
    db: Session,
    *,
    miembro_id: int,
    monto_clp: int,
    origen_pago_id: int | None = None,
) -> Abono:
    """Crea un abono (saldo a favor) para un miembro (D-15)."""
    abono = Abono(
        miembro_id=miembro_id,
        monto_clp=monto_clp,
        saldo_disponible_clp=monto_clp,
        origen_pago_id=origen_pago_id,
        estado=ESTADO_DISPONIBLE,
    )
    db.add(abono)
    return abono


def saldo_a_favor(db: Session, miembro_id: int) -> int:
    """Suma el saldo a favor disponible de un miembro."""
    abonos = db.scalars(
        select(Abono).where(
            Abono.miembro_id == miembro_id, Abono.estado == ESTADO_DISPONIBLE
        )
    )
    return sum(abono.saldo_disponible_clp for abono in abonos)
