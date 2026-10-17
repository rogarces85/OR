"""Consultas y persistencia de membresías: niveles, cuotas y negociaciones."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.membresia import (
    ESTADO_PENDIENTE,
    CuotaMensual,
    NegociacionDeuda,
    NivelCuota,
)


def listar_niveles(db: Session, *, solo_activos: bool = True) -> list[NivelCuota]:
    """Lista el catálogo de cuotas (Matrícula, Estándar y Activa)."""
    consulta = select(NivelCuota).order_by(NivelCuota.id)
    if solo_activos:
        consulta = consulta.where(NivelCuota.activo.is_(True))
    return list(db.scalars(consulta))


def obtener_nivel_por_codigo(db: Session, codigo: str) -> NivelCuota | None:
    """Devuelve un nivel del catálogo por su código (``matricula``, etc.)."""
    return db.scalar(select(NivelCuota).where(NivelCuota.codigo == codigo))


def cuotas_de_miembro(
    db: Session, miembro_id: int, *, desde_anio: int | None = None
) -> list[CuotaMensual]:
    """Lista las cuotas de un miembro, de la más antigua a la más reciente."""
    consulta = (
        select(CuotaMensual)
        .where(CuotaMensual.miembro_id == miembro_id)
        .order_by(CuotaMensual.anio, CuotaMensual.mes)
    )
    if desde_anio is not None:
        consulta = consulta.where(CuotaMensual.anio >= desde_anio)
    return list(db.scalars(consulta))


def cuotas_por_miembros(
    db: Session, miembros_ids: list[int]
) -> dict[int, list[CuotaMensual]]:
    """Agrupa las cuotas de varios miembros en una sola consulta (evita N+1)."""
    agrupadas: dict[int, list[CuotaMensual]] = {mid: [] for mid in miembros_ids}
    if not miembros_ids:
        return agrupadas
    consulta = (
        select(CuotaMensual)
        .where(CuotaMensual.miembro_id.in_(miembros_ids))
        .order_by(CuotaMensual.miembro_id, CuotaMensual.anio, CuotaMensual.mes)
    )
    for cuota in db.scalars(consulta):
        agrupadas.setdefault(cuota.miembro_id, []).append(cuota)
    return agrupadas


def obtener_cuota(
    db: Session, miembro_id: int, anio: int, mes: int
) -> CuotaMensual | None:
    """Busca la cuota de un miembro para un periodo concreto."""
    return db.scalar(
        select(CuotaMensual).where(
            CuotaMensual.miembro_id == miembro_id,
            CuotaMensual.anio == anio,
            CuotaMensual.mes == mes,
        )
    )


def crear_cuota(
    db: Session,
    *,
    miembro_id: int,
    anio: int,
    mes: int,
    nivel_cuota_id: int,
    monto_clp: int,
    monto_pagado_clp: int = 0,
    estado: str = ESTADO_PENDIENTE,
) -> CuotaMensual:
    """Crea la cuota de un miembro para un periodo (sin confirmar la transacción)."""
    cuota = CuotaMensual(
        miembro_id=miembro_id,
        anio=anio,
        mes=mes,
        nivel_cuota_id=nivel_cuota_id,
        monto_clp=monto_clp,
        monto_pagado_clp=monto_pagado_clp,
        estado=estado,
    )
    db.add(cuota)
    return cuota


def negociaciones_aceptadas(db: Session, miembro_id: int) -> list[NegociacionDeuda]:
    """Lista las negociaciones en estado "aceptada" de un miembro (P-6)."""
    return list(
        db.scalars(
            select(NegociacionDeuda).where(
                NegociacionDeuda.miembro_id == miembro_id,
                NegociacionDeuda.estado == "aceptada",
            )
        )
    )


def guardar(db: Session, cuota: CuotaMensual) -> CuotaMensual:
    """Confirma los cambios de una cuota."""
    db.add(cuota)
    db.commit()
    db.refresh(cuota)
    return cuota
