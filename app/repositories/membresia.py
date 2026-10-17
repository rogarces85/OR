"""Consultas y persistencia de membresías: niveles, cuotas y negociaciones."""

from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.membresia import (
    ESTADO_ACEPTADA,
    ESTADO_EXENTA,
    ESTADO_NEGOCIACION_PAGADA,
    ESTADO_PARCIAL,
    ESTADO_PENDIENTE,
    ESTADO_PROPUESTA,
    NIVEL_ACTIVA,
    NIVEL_MATRICULA,
    NIVEL_POR_CATEGORIA,
    TIPO_MENSUAL,
    CuotaMensual,
    NegociacionDeuda,
    NivelCuota,
)

# Estados en los que una cuota todavía puede ajustarse por cambio de categoría.
ESTADOS_AJUSTABLES: tuple[str, ...] = (ESTADO_PENDIENTE, "parcial")


def listar_niveles(db: Session, *, solo_activos: bool = True) -> list[NivelCuota]:
    """Lista el catálogo de cuotas (Matrícula, Estándar y Activa)."""
    consulta = select(NivelCuota).order_by(NivelCuota.id)
    if solo_activos:
        consulta = consulta.where(NivelCuota.activo.is_(True))
    return list(db.scalars(consulta))


def obtener_nivel_por_codigo(db: Session, codigo: str) -> NivelCuota | None:
    """Devuelve un nivel del catálogo por su código (``matricula``, etc.)."""
    return db.scalar(select(NivelCuota).where(NivelCuota.codigo == codigo))


def nivel_de_categoria(db: Session, categoria: str) -> NivelCuota | None:
    """Devuelve el nivel de cuota mensual que corresponde a una categoría (RN-01)."""
    codigo = NIVEL_POR_CATEGORIA.get(categoria, NIVEL_ACTIVA)
    return obtener_nivel_por_codigo(db, codigo)


def nivel_matricula(db: Session) -> NivelCuota | None:
    """Devuelve el nivel de la Matrícula (pago único de incorporación)."""
    return obtener_nivel_por_codigo(db, NIVEL_MATRICULA)


def cuotas_de_miembro(db: Session, miembro_id: int) -> list[CuotaMensual]:
    """Lista todas las cuotas de un miembro (incluida la Matrícula)."""
    return list(
        db.scalars(
            select(CuotaMensual)
            .where(CuotaMensual.miembro_id == miembro_id)
            .order_by(CuotaMensual.anio, CuotaMensual.mes, CuotaMensual.nivel_cuota_id)
        )
    )


def cuotas_mensuales_de_miembro(db: Session, miembro_id: int) -> list[CuotaMensual]:
    """Lista solo las **cuotas mensuales** de un miembro (excluye la Matrícula)."""
    return list(
        db.scalars(
            select(CuotaMensual)
            .join(NivelCuota, CuotaMensual.nivel_cuota_id == NivelCuota.id)
            .where(
                CuotaMensual.miembro_id == miembro_id,
                NivelCuota.tipo == TIPO_MENSUAL,
            )
            .order_by(CuotaMensual.anio, CuotaMensual.mes)
        )
    )


def cuotas_por_miembros(
    db: Session, miembros_ids: list[int], *, solo_mensuales: bool = False
) -> dict[int, list[CuotaMensual]]:
    """Agrupa las cuotas de varios miembros en una sola consulta (evita N+1).

    Con ``solo_mensuales=True`` excluye la Matrícula, como requiere el cálculo de
    morosidad (la mora aplica a las cuotas mensuales; ver F-11 y RN-04).
    """
    agrupadas: dict[int, list[CuotaMensual]] = {mid: [] for mid in miembros_ids}
    if not miembros_ids:
        return agrupadas
    consulta = (
        select(CuotaMensual)
        .where(CuotaMensual.miembro_id.in_(miembros_ids))
        .order_by(CuotaMensual.miembro_id, CuotaMensual.anio, CuotaMensual.mes)
    )
    if solo_mensuales:
        consulta = consulta.join(
            NivelCuota, CuotaMensual.nivel_cuota_id == NivelCuota.id
        ).where(NivelCuota.tipo == TIPO_MENSUAL)
    for cuota in db.scalars(consulta):
        agrupadas.setdefault(cuota.miembro_id, []).append(cuota)
    return agrupadas


def listar_por_periodo(db: Session, anio: int, mes: int) -> list[CuotaMensual]:
    """Lista las cuotas de un periodo concreto (para la generación mensual)."""
    return list(
        db.scalars(
            select(CuotaMensual)
            .where(CuotaMensual.anio == anio, CuotaMensual.mes == mes)
            .order_by(CuotaMensual.miembro_id)
        )
    )


def obtener_cuota(
    db: Session,
    miembro_id: int,
    anio: int,
    mes: int,
    nivel_cuota_id: int | None = None,
) -> CuotaMensual | None:
    """Busca la cuota de un miembro para un periodo (y nivel, si se indica)."""
    consulta = select(CuotaMensual).where(
        CuotaMensual.miembro_id == miembro_id,
        CuotaMensual.anio == anio,
        CuotaMensual.mes == mes,
    )
    if nivel_cuota_id is not None:
        consulta = consulta.where(CuotaMensual.nivel_cuota_id == nivel_cuota_id)
    return db.scalar(consulta)


def cuotas_ajustables_desde(
    db: Session, miembro_id: int, anio: int, mes: int
) -> list[CuotaMensual]:
    """Cuotas mensuales no pagadas de un miembro desde un periodo (RN-25)."""
    return list(
        db.scalars(
            select(CuotaMensual)
            .join(NivelCuota, CuotaMensual.nivel_cuota_id == NivelCuota.id)
            .where(
                CuotaMensual.miembro_id == miembro_id,
                NivelCuota.tipo == TIPO_MENSUAL,
                CuotaMensual.estado.in_(ESTADOS_AJUSTABLES),
                (CuotaMensual.anio > anio)
                | ((CuotaMensual.anio == anio) & (CuotaMensual.mes >= mes)),
            )
            .order_by(CuotaMensual.anio, CuotaMensual.mes)
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


def marcar_exenta(db: Session, cuota: CuotaMensual) -> CuotaMensual:
    """Deja una cuota como **exenta** (sin deuda) al eximir al miembro (RN-05)."""
    cuota.estado = ESTADO_EXENTA
    cuota.monto_pagado_clp = 0
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


# --------------------------------------------------------------------------- #
# Imputación de pagos y abonos (F-13, RN-17, RN-18)
# --------------------------------------------------------------------------- #

# Estados en los que una cuota aún tiene saldo por cubrir.
ESTADOS_IMPAGOS: tuple[str, ...] = (ESTADO_PENDIENTE, ESTADO_PARCIAL)


def cuotas_impagas(db: Session, miembro_id: int) -> list[CuotaMensual]:
    """Cuotas no pagadas de un miembro, de la más antigua a la más reciente.

    Incluye la Matrícula para que el pago inicial cubra la obligación completa
    (Matrícula + la cuota de la categoría; Flujo 1, RN-17).
    """
    return list(
        db.scalars(
            select(CuotaMensual)
            .where(
                CuotaMensual.miembro_id == miembro_id,
                CuotaMensual.estado.in_(ESTADOS_IMPAGOS),
            )
            .order_by(
                CuotaMensual.anio, CuotaMensual.mes, CuotaMensual.nivel_cuota_id
            )
        )
    )


def siguiente_cuota_impaga(db: Session, miembro_id: int) -> CuotaMensual | None:
    """Primera cuota **mensual** impaga de un miembro (destino del abono, RN-18)."""
    return db.scalar(
        select(CuotaMensual)
        .join(NivelCuota, CuotaMensual.nivel_cuota_id == NivelCuota.id)
        .where(
            CuotaMensual.miembro_id == miembro_id,
            CuotaMensual.estado.in_(ESTADOS_IMPAGOS),
            NivelCuota.tipo == TIPO_MENSUAL,
        )
        .order_by(CuotaMensual.anio, CuotaMensual.mes)
    )


def deuda_negociada_clp(db: Session, miembro_id: int) -> int:
    """Deuda excluida del color por negociaciones aceptadas o pagadas (P-6)."""
    total = db.scalar(
        select(func.coalesce(func.sum(NegociacionDeuda.deuda_total_clp), 0)).where(
            NegociacionDeuda.miembro_id == miembro_id,
            NegociacionDeuda.estado.in_(
                (ESTADO_ACEPTADA, ESTADO_NEGOCIACION_PAGADA)
            ),
        )
    )
    return int(total or 0)


# --------------------------------------------------------------------------- #
# Negociaciones de deuda (F-24)
# --------------------------------------------------------------------------- #


def obtener_negociacion(db: Session, negociacion_id: int) -> NegociacionDeuda | None:
    """Devuelve una negociación por su identificador."""
    return db.get(NegociacionDeuda, negociacion_id)


def listar_negociaciones(
    db: Session, *, miembro_id: int | None = None
) -> list[NegociacionDeuda]:
    """Lista las negociaciones registradas, de la más reciente a la más antigua."""
    consulta = select(NegociacionDeuda).order_by(
        NegociacionDeuda.fecha.desc(), NegociacionDeuda.id.desc()
    )
    if miembro_id is not None:
        consulta = consulta.where(NegociacionDeuda.miembro_id == miembro_id)
    return list(db.scalars(consulta))


def crear_negociacion(
    db: Session,
    *,
    miembro_id: int,
    deuda_total_clp: int,
    descuento_pct: int,
    monto_negociado_clp: int,
    fecha: date | None = None,
    usuario_id: int | None = None,
) -> NegociacionDeuda:
    """Registra una negociación de deuda en estado "propuesta" (F-24)."""
    negociacion = NegociacionDeuda(
        miembro_id=miembro_id,
        deuda_total_clp=deuda_total_clp,
        descuento_pct=descuento_pct,
        monto_negociado_clp=monto_negociado_clp,
        fecha=fecha or date.today(),
        usuario_id=usuario_id,
        estado=ESTADO_PROPUESTA,
    )
    db.add(negociacion)
    return negociacion


def guardar_negociacion(
    db: Session, negociacion: NegociacionDeuda
) -> NegociacionDeuda:
    """Confirma los cambios de una negociación."""
    db.add(negociacion)
    db.commit()
    db.refresh(negociacion)
    return negociacion
