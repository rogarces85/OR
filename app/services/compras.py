"""Compras del club y cobro separado a alumnos (F-25, RN-23).

Cubre T5.29 (registro de la compra y sus ítems), T5.30 (generación de cargos
separados a alumnos) y T5.31 (saldar un cargo).
"""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from app.models.compras import (
    ESTADO_CARGO_PAGADO,
    ESTADO_CARGO_PENDIENTE,
    CargoAlumno,
    CompraClub,
)
from app.models.finanzas import TIPO_COMPRA
from app.models.pago import MEDIO_TRANSFERENCIA, Pago
from app.repositories import compras as repo_compras
from app.repositories import finanzas as repo_finanzas
from app.repositories import miembro as repo_miembro
from app.repositories import pago as repo_pago

CATEGORIA_COMPRAS = "Otros"


class ErrorCompras(ValueError):
    """Error de validación de compras, con mensaje en español."""


def registrar_compra(
    db: Session,
    *,
    descripcion: str,
    items: list[dict[str, Any]],
    proveedor: str | None = None,
    fecha: date | None = None,
    usuario: Any | None = None,
) -> CompraClub:
    """Registra una compra del club con sus ítems (F-25, T5.29).

    La compra queda además como **egreso** (tipo compra) para que se refleje en
    los reportes consolidados (Flujo 9).
    """
    limpio = (descripcion or "").strip()
    if not limpio:
        raise ErrorCompras("La descripción de la compra es obligatoria.")
    if not items:
        raise ErrorCompras("La compra debe tener al menos un ítem.")

    normalizados: list[dict[str, Any]] = []
    total = 0
    for item in items:
        item_desc = str(item.get("descripcion") or "").strip()
        try:
            precio = int(item.get("precio_unitario_clp") or 0)
            cantidad = int(item.get("cantidad") or 0)
        except (TypeError, ValueError) as exc:
            raise ErrorCompras("El precio y la cantidad deben ser enteros.") from exc
        if not item_desc:
            raise ErrorCompras("Cada ítem necesita una descripción.")
        if precio <= 0:
            raise ErrorCompras("El precio unitario debe ser un entero positivo.")
        if cantidad <= 0:
            raise ErrorCompras("La cantidad debe ser al menos 1.")
        normalizados.append(
            {
                "descripcion": item_desc,
                "precio_unitario_clp": precio,
                "cantidad": cantidad,
            }
        )
        total += precio * cantidad

    fecha_compra = fecha or date.today()
    compra = repo_compras.crear_compra(
        db,
        descripcion=limpio,
        monto_total_clp=total,
        proveedor=(proveedor or None),
        fecha=fecha_compra,
    )
    db.flush()
    for item in normalizados:
        repo_compras.crear_item(db, compra_id=compra.id, **item)
    db.flush()

    # Reflejo como egreso (tipo compra) para los reportes consolidados.
    categoria = repo_finanzas.obtener_categoria_por_nombre(db, CATEGORIA_COMPRAS)
    if categoria is not None and categoria.activo:
        repo_finanzas.crear_egreso(
            db,
            monto_clp=total,
            concepto=limpio,
            categoria_egreso_id=categoria.id,
            fecha=fecha_compra,
            tipo=TIPO_COMPRA,
            registrado_por=getattr(usuario, "id", None),
        )
    db.commit()
    db.refresh(compra)
    return compra


def generar_cargos_alumnos(
    db: Session,
    *,
    compra: CompraClub,
    asignaciones: list[dict[str, Any]],
    fecha: date | None = None,
    usuario: Any | None = None,
) -> list[CargoAlumno]:
    """Genera los **cargos separados** de los ítems a los alumnos (F-25, RN-23).

    El cargo por compra **no afecta** la morosidad de las cuotas mensuales
    (D-19): es un registro independiente del ciclo de cuotas.
    """
    if not asignaciones:
        raise ErrorCompras("Debes asignar al menos un ítem a un alumno.")
    cargos: list[CargoAlumno] = []
    for asignacion in asignaciones:
        try:
            item_id = int(asignacion.get("compra_item_id"))
            miembro_id = int(asignacion.get("miembro_id"))
            cantidad = int(asignacion.get("cantidad") or 1)
        except (TypeError, ValueError) as exc:
            raise ErrorCompras("La asignación de ítem no es válida.") from exc
        if cantidad <= 0:
            raise ErrorCompras("La cantidad del cargo debe ser al menos 1.")
        item = repo_compras.obtener_item(db, item_id)
        if item is None or item.compra_id != compra.id:
            raise ErrorCompras("El ítem indicado no pertenece a la compra.")
        if repo_miembro.obtener(db, miembro_id) is None:
            raise ErrorCompras("El alumno indicado no existe.")
        monto = int(item.precio_unitario_clp) * cantidad
        cargos.append(
            repo_compras.crear_cargo(
                db,
                miembro_id=miembro_id,
                compra_item_id=item.id,
                monto_clp=monto,
                fecha=fecha or date.today(),
            )
        )
    db.commit()
    for cargo in cargos:
        db.refresh(cargo)
    return cargos


def saldar_cargo(
    db: Session,
    *,
    cargo: CargoAlumno,
    medio: str = MEDIO_TRANSFERENCIA,
    observaciones: str | None = None,
    usuario: Any | None = None,
) -> Pago:
    """Registra el pago de un cargo de alumno y lo marca como pagado (T5.31).

    El pago se guarda como ingreso independiente: **no** se imputa a las cuotas
    mensuales y por lo tanto no altera la morosidad de cuotas (RN-23).
    """
    if cargo.estado == ESTADO_CARGO_PAGADO:
        raise ErrorCompras("Este cargo ya está pagado.")
    pago = repo_pago.crear(
        db,
        miembro_id=cargo.miembro_id,
        monto_clp=int(cargo.monto_clp),
        medio=medio,
        observaciones=(observaciones or f"Pago de cargo por compra #{cargo.id}"),
        registrado_por=getattr(usuario, "id", None),
    )
    db.flush()
    cargo.estado = ESTADO_CARGO_PAGADO
    cargo.pago_id = pago.id
    db.add(cargo)
    db.commit()
    db.refresh(cargo)
    db.refresh(pago)
    return pago


def listar_cargos(
    db: Session, *, miembro_id: int | None = None, estado: str | None = None
) -> list[CargoAlumno]:
    """Lista los cargos a alumnos (T5.30)."""
    return repo_compras.listar_cargos(db, miembro_id=miembro_id, estado=estado)


def cargos_pendientes(db: Session) -> list[CargoAlumno]:
    """Cargos de alumno aún pendientes de pago."""
    return repo_compras.listar_cargos(db, estado=ESTADO_CARGO_PENDIENTE)
