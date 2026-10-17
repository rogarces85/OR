"""Compras del club y cobro separado a alumnos (F-25, RN-23)."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import ValidationError

from app.core.seguridad import flash, requiere_rol
from app.core.web import csrf_ok, redirigir
from app.dependencies import SesionBD, templates
from app.models.compras import ESTADO_CARGO_PENDIENTE
from app.models.pago import MEDIOS_PAGO
from app.models.usuario import ROLES_GESTION, Usuario
from app.repositories import compras as repo_compras
from app.repositories import miembro as repo_miembro
from app.schemas.compra import (
    AsignacionCargoEntrada,
    CompraEntrada,
    ItemCompraEntrada,
    SaldarCargoEntrada,
)
from app.schemas.comunes import primer_mensaje
from app.services import compras as servicio_compras

router = APIRouter(tags=["compras"])

MAX_ITEMS = 5


@router.get("/compras", response_class=HTMLResponse)
async def panel_compras(
    request: Request,
    db: SesionBD,
    usuario: Annotated[Usuario, Depends(requiere_rol(*ROLES_GESTION))],
) -> HTMLResponse:
    """Panel de compras del club y de cargos a alumnos (UI-04, F-25)."""
    return templates.TemplateResponse(
        request=request,
        name="compras/panel.html",
        context={
            "compras": repo_compras.listar_compras(db),
            "cargos": servicio_compras.listar_cargos(db),
            "cargos_pendientes": servicio_compras.cargos_pendientes(db),
            "miembros": repo_miembro.listar(db),
            "medios": MEDIOS_PAGO,
            "max_items": MAX_ITEMS,
            "estado_pendiente": ESTADO_CARGO_PENDIENTE,
        },
    )


@router.post("/compras", response_model=None)
async def crear_compra(
    request: Request,
    db: SesionBD,
    usuario: Annotated[Usuario, Depends(requiere_rol(*ROLES_GESTION))],
    csrf_token: str = Form(""),
    descripcion: str = Form(""),
    proveedor: str = Form(""),
    fecha: str = Form(""),
    item_descripcion: Annotated[list[str] | None, Form()] = None,
    item_precio: Annotated[list[str] | None, Form()] = None,
    item_cantidad: Annotated[list[str] | None, Form()] = None,
) -> RedirectResponse:
    """Registra una compra del club con sus ítems (T5.29)."""
    if not csrf_ok(request, csrf_token):
        return redirigir("/compras")

    items: list[ItemCompraEntrada] = []
    for desc, precio_txt, cant_txt in zip(
        item_descripcion or [], item_precio or [], item_cantidad or []
    ):
        if not (desc or "").strip():
            continue
        try:
            items.append(
                ItemCompraEntrada(
                    descripcion=desc,
                    precio_unitario_clp=precio_txt,
                    cantidad=cant_txt,
                )
            )
        except ValidationError as exc:
            flash(request, "error", f"Ítem «{desc}»: {primer_mensaje(exc)}")
            return redirigir("/compras")

    try:
        entrada = CompraEntrada(
            descripcion=descripcion,
            proveedor=proveedor,
            fecha=fecha,
            items=items,
        )
    except ValidationError as exc:
        flash(request, "error", primer_mensaje(exc))
        return redirigir("/compras")

    try:
        compra = servicio_compras.registrar_compra(
            db,
            descripcion=entrada.descripcion,
            proveedor=entrada.proveedor,
            fecha=entrada.fecha or date.today(),
            items=[item.model_dump() for item in entrada.items],
            usuario=usuario,
        )
    except servicio_compras.ErrorCompras as exc:
        flash(request, "error", str(exc))
    else:
        flash(
            request,
            "ok",
            f"Compra #{compra.id} registrada por $ {compra.monto_total_clp}.",
        )
    return redirigir("/compras")


@router.post("/compras/{compra_id}/cargos", response_model=None)
async def generar_cargos(
    request: Request,
    db: SesionBD,
    usuario: Annotated[Usuario, Depends(requiere_rol(*ROLES_GESTION))],
    compra_id: int,
    csrf_token: str = Form(""),
    asig_item: Annotated[list[str] | None, Form()] = None,
    asig_miembro: Annotated[list[str] | None, Form()] = None,
    asig_cantidad: Annotated[list[str] | None, Form()] = None,
) -> RedirectResponse:
    """Genera cargos separados a los alumnos por ítem (T5.30, CA-27)."""
    if not csrf_ok(request, csrf_token):
        return redirigir("/compras")
    compra = repo_compras.obtener_compra(db, compra_id)
    if compra is None:
        flash(request, "error", "La compra indicada no existe.")
        return redirigir("/compras")

    asignaciones = []
    for item_txt, miembro_txt, cant_txt in zip(
        asig_item or [], asig_miembro or [], asig_cantidad or []
    ):
        if not (miembro_txt or "").strip():
            continue
        try:
            asignacion = AsignacionCargoEntrada(
                compra_item_id=item_txt,
                miembro_id=miembro_txt,
                cantidad=cant_txt,
            )
        except ValidationError as exc:
            flash(request, "error", primer_mensaje(exc))
            return redirigir("/compras")
        asignaciones.append(asignacion.model_dump())

    try:
        cargos = servicio_compras.generar_cargos_alumnos(
            db, compra=compra, asignaciones=asignaciones, usuario=usuario
        )
    except servicio_compras.ErrorCompras as exc:
        flash(request, "error", str(exc))
    else:
        flash(
            request,
            "ok",
            f"Se generaron {len(cargos)} cargo(s) separado(s) a alumnos (RN-23).",
        )
    return redirigir("/compras")


@router.post("/compras/cargos/{cargo_id}/saldar", response_model=None)
async def saldar_cargo(
    request: Request,
    db: SesionBD,
    usuario: Annotated[Usuario, Depends(requiere_rol(*ROLES_GESTION))],
    cargo_id: int,
    csrf_token: str = Form(""),
    medio: str = Form("transferencia"),
) -> RedirectResponse:
    """Registra el pago de un cargo de alumno (T5.31)."""
    if not csrf_ok(request, csrf_token):
        return redirigir("/compras")
    cargo = repo_compras.obtener_cargo(db, cargo_id)
    if cargo is None:
        flash(request, "error", "El cargo indicado no existe.")
        return redirigir("/compras")
    if medio not in MEDIOS_PAGO:
        flash(request, "error", "El medio de pago no es válido (RN-19).")
        return redirigir("/compras")
    try:
        entrada = SaldarCargoEntrada(medio=medio)
    except ValidationError as exc:
        flash(request, "error", primer_mensaje(exc))
        return redirigir("/compras")
    try:
        servicio_compras.saldar_cargo(
            db, cargo=cargo, medio=entrada.medio, usuario=usuario
        )
    except servicio_compras.ErrorCompras as exc:
        flash(request, "error", str(exc))
    else:
        flash(request, "ok", "Cargo saldado: quedó marcado como pagado.")
    return redirigir("/compras")
