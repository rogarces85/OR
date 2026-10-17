"""Consultas y persistencia de compras y cargos a alumnos (T3.8)."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.compras import (
    ESTADO_CARGO_PENDIENTE,
    CargoAlumno,
    CompraClub,
    CompraItem,
)


def listar_compras(db: Session) -> list[CompraClub]:
    """Lista las compras del club, de la más reciente a la más antigua."""
    return list(
        db.scalars(select(CompraClub).order_by(CompraClub.fecha.desc(), CompraClub.id.desc()))
    )


def crear_compra(
    db: Session,
    *,
    descripcion: str,
    monto_total_clp: int,
    proveedor: str | None = None,
    fecha: date | None = None,
) -> CompraClub:
    """Registra una compra del club (sin confirmar la transacción)."""
    compra = CompraClub(
        descripcion=descripcion.strip(),
        proveedor=proveedor,
        monto_total_clp=monto_total_clp,
        fecha=fecha or date.today(),
    )
    db.add(compra)
    return compra


def crear_item(
    db: Session,
    *,
    compra_id: int,
    descripcion: str,
    precio_unitario_clp: int,
    cantidad: int = 1,
) -> CompraItem:
    """Agrega un ítem a una compra del club."""
    item = CompraItem(
        compra_id=compra_id,
        descripcion=descripcion.strip(),
        precio_unitario_clp=precio_unitario_clp,
        cantidad=cantidad,
    )
    db.add(item)
    return item


def crear_cargo(
    db: Session,
    *,
    miembro_id: int,
    monto_clp: int,
    compra_item_id: int | None = None,
    fecha: date | None = None,
) -> CargoAlumno:
    """Genera un cargo separado a un alumno (D-19, RN-23)."""
    cargo = CargoAlumno(
        miembro_id=miembro_id,
        compra_item_id=compra_item_id,
        monto_clp=monto_clp,
        fecha=fecha or date.today(),
        estado=ESTADO_CARGO_PENDIENTE,
    )
    db.add(cargo)
    return cargo


def cargos_de_miembro(db: Session, miembro_id: int) -> list[CargoAlumno]:
    """Lista los cargos de compra de un alumno."""
    return list(
        db.scalars(
            select(CargoAlumno)
            .where(CargoAlumno.miembro_id == miembro_id)
            .order_by(CargoAlumno.fecha.desc())
        )
    )
