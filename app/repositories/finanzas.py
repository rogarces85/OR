"""Consultas y persistencia de finanzas: categorías, egresos y gastos fijos."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core import cache
from app.models.finanzas import (
    PERIODICIDAD_MENSUAL,
    TIPO_GENERAL,
    CategoriaEgreso,
    Egreso,
    GastoFijo,
)


def _consultar_categorias(
    db: Session, solo_activas: bool
) -> list[CategoriaEgreso]:
    consulta = select(CategoriaEgreso).order_by(
        CategoriaEgreso.es_base.desc(), CategoriaEgreso.nombre
    )
    if solo_activas:
        consulta = consulta.where(CategoriaEgreso.activo.is_(True))
    return list(db.scalars(consulta))


def listar_categorias(db: Session, *, solo_activas: bool = True) -> list[CategoriaEgreso]:
    """Lista las categorías de egreso (base y personalizadas, RN-10).

    Se cachea el catálogo porque se repite en formularios y listados (T9.4).
    """
    return list(
        cache.obtener(
            db,
            f"categorias_egreso:{solo_activas}",
            lambda: _consultar_categorias(db, solo_activas),
        )
    )


def invalidar_categorias(db: Session) -> None:
    """Invalida el catálogo cacheado de categorías de egreso."""
    cache.invalidar(
        db, "categorias_egreso:True", "categorias_egreso:False"
    )


def obtener_categoria(db: Session, categoria_id: int) -> CategoriaEgreso | None:
    """Devuelve una categoría de egreso por su identificador."""
    return db.get(CategoriaEgreso, categoria_id)


def obtener_categoria_por_nombre(db: Session, nombre: str) -> CategoriaEgreso | None:
    """Devuelve una categoría por su nombre."""
    return db.scalar(
        select(CategoriaEgreso).where(CategoriaEgreso.nombre == nombre.strip())
    )


def crear_categoria(
    db: Session, *, nombre: str, es_base: bool = False, activo: bool = True
) -> CategoriaEgreso:
    """Crea una categoría de egreso (personalizada o base)."""
    categoria = CategoriaEgreso(nombre=nombre.strip(), es_base=es_base, activo=activo)
    db.add(categoria)
    invalidar_categorias(db)
    return categoria


def listar_egresos(
    db: Session,
    *,
    desde: date | None = None,
    hasta: date | None = None,
    categoria_id: int | None = None,
) -> list[Egreso]:
    """Lista egresos aplicando filtros de periodo y categoría (F-16)."""
    consulta = (
        select(Egreso)
        .options(selectinload(Egreso.categoria))
        .order_by(Egreso.fecha.desc(), Egreso.id.desc())
    )
    if desde is not None:
        consulta = consulta.where(Egreso.fecha >= desde)
    if hasta is not None:
        consulta = consulta.where(Egreso.fecha <= hasta)
    if categoria_id is not None:
        consulta = consulta.where(Egreso.categoria_egreso_id == categoria_id)
    return list(db.scalars(consulta))


def crear_egreso(
    db: Session,
    *,
    monto_clp: int,
    concepto: str,
    categoria_egreso_id: int,
    fecha: date | None = None,
    tipo: str = TIPO_GENERAL,
    miembro_responsable_id: int | None = None,
    registrado_por: int | None = None,
) -> Egreso:
    """Registra un egreso asociado a una categoría válida (RN-10)."""
    egreso = Egreso(
        monto_clp=monto_clp,
        concepto=concepto.strip(),
        categoria_egreso_id=categoria_egreso_id,
        fecha=fecha or date.today(),
        tipo=tipo,
        miembro_responsable_id=miembro_responsable_id,
        registrado_por=registrado_por,
    )
    db.add(egreso)
    return egreso


def crear_gasto_fijo(
    db: Session,
    *,
    concepto: str,
    monto_clp: int,
    periodicidad: str = PERIODICIDAD_MENSUAL,
) -> GastoFijo:
    """Registra un gasto fijo operativo recurrente (F-18)."""
    gasto = GastoFijo(
        concepto=concepto.strip(), monto_clp=monto_clp, periodicidad=periodicidad
    )
    db.add(gasto)
    return gasto


def listar_gastos_fijos(db: Session, *, solo_activos: bool = True) -> list[GastoFijo]:
    """Lista los gastos fijos del club."""
    consulta = select(GastoFijo).order_by(GastoFijo.concepto)
    if solo_activos:
        consulta = consulta.where(GastoFijo.activo.is_(True))
    return list(db.scalars(consulta))


def obtener_egreso(db: Session, egreso_id: int) -> Egreso | None:
    """Devuelve un egreso por su identificador."""
    return db.get(Egreso, egreso_id)


def guardar_categoria(db: Session, categoria: CategoriaEgreso) -> CategoriaEgreso:
    """Confirma los cambios de una categoría de egreso."""
    db.add(categoria)
    db.commit()
    db.refresh(categoria)
    invalidar_categorias(db)
    return categoria


def guardar_egreso(db: Session, egreso: Egreso) -> Egreso:
    """Confirma un egreso."""
    db.add(egreso)
    db.commit()
    db.refresh(egreso)
    return egreso


def guardar_gasto_fijo(db: Session, gasto: GastoFijo) -> GastoFijo:
    """Confirma un gasto fijo."""
    db.add(gasto)
    db.commit()
    db.refresh(gasto)
    return gasto
