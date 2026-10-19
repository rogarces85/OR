"""Consultas y persistencia de compras y cargos a alumnos (T3.8)."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.compras import (
    ESTADO_CARGO_PENDIENTE,
    CargoAlumno,
    CompraClub,
    CompraItem,
)


def listar_compras(db: Session) -> list[CompraClub]:
    """Lista las compras del club, de la más reciente a la más antigua."""
    return list(
        db.scalars(
            select(CompraClub)
            .options(selectinload(CompraClub.items))
            .order_by(CompraClub.fecha.desc(), CompraClub.id.desc())
        )
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


def obtener_compra(db: Session, compra_id: int) -> CompraClub | None:
    """Devuelve una compra del club por su identificador."""
    return db.get(CompraClub, compra_id)


def obtener_item(db: Session, item_id: int) -> CompraItem | None:
    """Devuelve un ítem de compra por su identificador."""
    return db.get(CompraItem, item_id)


def items_de_compra(db: Session, compra_id: int) -> list[CompraItem]:
    """Lista los ítems de una compra."""
    return list(
        db.scalars(
            select(CompraItem)
            .where(CompraItem.compra_id == compra_id)
            .order_by(CompraItem.id)
        )
    )


def obtener_cargo(db: Session, cargo_id: int) -> CargoAlumno | None:
    """Devuelve un cargo a alumno por su identificador."""
    return db.get(CargoAlumno, cargo_id)


def listar_cargos(
    db: Session, *, miembro_id: int | None = None, estado: str | None = None
) -> list[CargoAlumno]:
    """Lista los cargos a alumnos, del más reciente al más antiguo."""
    consulta = (
        select(CargoAlumno)
        .options(selectinload(CargoAlumno.miembro))
        .order_by(CargoAlumno.fecha.desc(), CargoAlumno.id.desc())
    )
    if miembro_id is not None:
        consulta = consulta.where(CargoAlumno.miembro_id == miembro_id)
    if estado:
        consulta = consulta.where(CargoAlumno.estado == estado)
    return list(db.scalars(consulta))


def guardar_cargo(db: Session, cargo: CargoAlumno) -> CargoAlumno:
    """Confirma los cambios de un cargo a alumno."""
    db.add(cargo)
    db.commit()
    db.refresh(cargo)
    return cargo
