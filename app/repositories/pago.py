"""Consultas y persistencia de pagos, imputaciones y abonos (T3.8)."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.membresia import CuotaMensual, NivelCuota
from app.models.miembro import Miembro
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
    consulta = (
        select(Pago)
        .options(selectinload(Pago.miembro))
        .order_by(Pago.fecha_pago.desc(), Pago.id.desc())
    )
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


def abonos_disponibles(db: Session, miembro_id: int) -> list[Abono]:
    """Lista los abonos con saldo disponible de un miembro (RN-18)."""
    return list(
        db.scalars(
            select(Abono)
            .where(
                Abono.miembro_id == miembro_id,
                Abono.estado == ESTADO_DISPONIBLE,
                Abono.saldo_disponible_clp > 0,
            )
            .order_by(Abono.id)
        )
    )


def saldo_a_favor(db: Session, miembro_id: int) -> int:
    """Suma el saldo a favor disponible de un miembro."""
    return sum(
        abono.saldo_disponible_clp
        for abono in abonos_disponibles(db, miembro_id)
    )


def obtener(db: Session, pago_id: int) -> Pago | None:
    """Devuelve un pago por su identificador."""
    return db.get(Pago, pago_id)


def imputaciones_de_pago(db: Session, pago_id: int) -> list[ImputacionPago]:
    """Lista las imputaciones de un pago, en el orden en que se aplicaron."""
    return list(
        db.scalars(
            select(ImputacionPago)
            .where(ImputacionPago.pago_id == pago_id)
            .order_by(ImputacionPago.orden, ImputacionPago.id)
        )
    )


def listar_ingresos(
    db: Session,
    *,
    desde: date | None = None,
    hasta: date | None = None,
    nivel_codigo: str | None = None,
    situacion: str | None = None,
) -> list[Pago]:
    """Lista los ingresos (pagos) filtrando por periodo, tipo de cuota y estado.

    Cubre F-15 (ingresos filtrados por tipo de cuota y por estado del usuario).
    """
    consulta = (
        select(Pago)
        .options(selectinload(Pago.miembro))
        .join(Miembro, Pago.miembro_id == Miembro.id)
    )
    if desde is not None:
        consulta = consulta.where(Pago.fecha_pago >= desde)
    if hasta is not None:
        consulta = consulta.where(Pago.fecha_pago <= hasta)
    if nivel_codigo:
        consulta = (
            consulta.join(ImputacionPago, ImputacionPago.pago_id == Pago.id)
            .join(CuotaMensual, ImputacionPago.cuota_id == CuotaMensual.id)
            .join(NivelCuota, CuotaMensual.nivel_cuota_id == NivelCuota.id)
            .where(NivelCuota.codigo == nivel_codigo)
        )
    if situacion:
        consulta = consulta.where(Miembro.situacion_activacion == situacion)
    return list(
        db.scalars(
            consulta.distinct().order_by(Pago.fecha_pago.desc(), Pago.id.desc())
        )
    )
