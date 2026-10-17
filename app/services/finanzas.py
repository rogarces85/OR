"""Finanzas: egresos, categorías, activos y gastos fijos (F-15, F-16, F-17, F-18).

Cubre T5.24 (categorías base y personalizadas), T5.25 (registro de egresos),
T5.26 (activos), T5.27 (gastos fijos) y T5.28 (listados y filtros).
"""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from app.models.finanzas import (
    TIPO_ACTIVO,
    TIPO_GASTO_FIJO,
    TIPO_GENERAL,
    CategoriaEgreso,
    Egreso,
    GastoFijo,
)
from app.models.pago import Pago
from app.repositories import finanzas as repo_finanzas
from app.repositories import pago as repo_pago

CATEGORIA_ACTIVOS = "Activos"
CATEGORIA_GASTOS_FIJOS = "Gastos fijos"


class ErrorFinanzas(ValueError):
    """Error de validación financiera, con mensaje en español."""


# --------------------------------------------------------------------------- #
# Validaciones
# --------------------------------------------------------------------------- #


def _validar_monto(monto_clp: int) -> int:
    if monto_clp is None or int(monto_clp) <= 0:
        raise ErrorFinanzas("El monto debe ser un entero positivo.")
    return int(monto_clp)


def _categoria_por_nombre(db: Session, nombre: str) -> CategoriaEgreso:
    categoria = repo_finanzas.obtener_categoria_por_nombre(db, nombre)
    if categoria is None or not categoria.activo:
        raise ErrorFinanzas(
            f"Falta la categoría de egreso «{nombre}». Ejecuta la semilla."
        )
    return categoria


# --------------------------------------------------------------------------- #
# Egresos (T5.25)
# --------------------------------------------------------------------------- #


def registrar_egreso(
    db: Session,
    *,
    monto_clp: int,
    concepto: str,
    categoria_id: int,
    fecha: date | None = None,
    tipo: str = TIPO_GENERAL,
    miembro_responsable_id: int | None = None,
    usuario: Any | None = None,
) -> Egreso:
    """Registra un egreso asociado a una categoría válida (RN-10, CA-07)."""
    monto = _validar_monto(monto_clp)
    if not (concepto or "").strip():
        raise ErrorFinanzas("El concepto del egreso es obligatorio.")
    categoria = repo_finanzas.obtener_categoria(db, int(categoria_id))
    if categoria is None or not categoria.activo:
        raise ErrorFinanzas("Debes seleccionar una categoría de egreso válida (RN-10).")
    egreso = repo_finanzas.crear_egreso(
        db,
        monto_clp=monto,
        concepto=concepto,
        categoria_egreso_id=categoria.id,
        fecha=fecha or date.today(),
        tipo=tipo,
        miembro_responsable_id=miembro_responsable_id,
        registrado_por=getattr(usuario, "id", None),
    )
    return repo_finanzas.guardar_egreso(db, egreso)


def registrar_activo(
    db: Session,
    *,
    costo_clp: int,
    descripcion: str,
    miembro_responsable_id: int | None = None,
    fecha: date | None = None,
    usuario: Any | None = None,
) -> Egreso:
    """Registra la adquisición de un activo del club (F-17, CA-08).

    El **miembro responsable** es quien gestiona la compra (D-9), sin que ello
    implique un cobro a su persona.
    """
    monto = _validar_monto(costo_clp)
    if not (descripcion or "").strip():
        raise ErrorFinanzas("La descripción del activo es obligatoria.")
    categoria = _categoria_por_nombre(db, CATEGORIA_ACTIVOS)
    egreso = repo_finanzas.crear_egreso(
        db,
        monto_clp=monto,
        concepto=descripcion,
        categoria_egreso_id=categoria.id,
        fecha=fecha or date.today(),
        tipo=TIPO_ACTIVO,
        miembro_responsable_id=miembro_responsable_id,
        registrado_por=getattr(usuario, "id", None),
    )
    return repo_finanzas.guardar_egreso(db, egreso)


def registrar_gasto_fijo(
    db: Session,
    *,
    concepto: str,
    monto_clp: int,
    fecha: date | None = None,
    usuario: Any | None = None,
) -> GastoFijo:
    """Registra un gasto fijo operativo y su egreso recurrente (F-18, CA-09)."""
    monto = _validar_monto(monto_clp)
    if not (concepto or "").strip():
        raise ErrorFinanzas("El concepto del gasto fijo es obligatorio.")
    gasto = repo_finanzas.crear_gasto_fijo(
        db, concepto=concepto, monto_clp=monto
    )
    categoria = _categoria_por_nombre(db, CATEGORIA_GASTOS_FIJOS)
    repo_finanzas.crear_egreso(
        db,
        monto_clp=monto,
        concepto=concepto,
        categoria_egreso_id=categoria.id,
        fecha=fecha or date.today(),
        tipo=TIPO_GASTO_FIJO,
        registrado_por=getattr(usuario, "id", None),
    )
    return repo_finanzas.guardar_gasto_fijo(db, gasto)


# --------------------------------------------------------------------------- #
# Categorías de egreso (T5.24)
# --------------------------------------------------------------------------- #


def crear_categoria_egreso(
    db: Session, *, nombre: str, usuario: Any | None = None
) -> CategoriaEgreso:
    """Crea una categoría de egreso personalizada (RN-10, P-7)."""
    limpio = (nombre or "").strip()
    if len(limpio) < 3:
        raise ErrorFinanzas("El nombre de la categoría es demasiado corto.")
    if repo_finanzas.obtener_categoria_por_nombre(db, limpio) is not None:
        raise ErrorFinanzas("Ya existe una categoría con ese nombre.")
    categoria = repo_finanzas.crear_categoria(db, nombre=limpio, es_base=False)
    return repo_finanzas.guardar_categoria(db, categoria)


def cambiar_estado_categoria(
    db: Session, categoria: CategoriaEgreso, *, activo: bool
) -> CategoriaEgreso:
    """Activa o desactiva una categoría (las base no se eliminan; P-7)."""
    categoria.activo = bool(activo)
    return repo_finanzas.guardar_categoria(db, categoria)


# --------------------------------------------------------------------------- #
# Listados (T5.28, F-15)
# --------------------------------------------------------------------------- #


def listar_ingresos(
    db: Session,
    *,
    desde: date | None = None,
    hasta: date | None = None,
    nivel_codigo: str | None = None,
    situacion: str | None = None,
) -> list[Pago]:
    """Lista los ingresos con filtros de tipo de cuota y estado (F-15, CA-06)."""
    return repo_pago.listar_ingresos(
        db, desde=desde, hasta=hasta, nivel_codigo=nivel_codigo, situacion=situacion
    )


def listar_egresos(
    db: Session,
    *,
    desde: date | None = None,
    hasta: date | None = None,
    categoria_id: int | None = None,
) -> list[Egreso]:
    """Lista los egresos con filtros de periodo y categoría (F-16)."""
    return repo_finanzas.listar_egresos(
        db, desde=desde, hasta=hasta, categoria_id=categoria_id
    )
