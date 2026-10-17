"""Finanzas: egresos, activos, gastos fijos y categorías (F-16, F-17, F-18)."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import ValidationError

from app.core.seguridad import flash, requiere_rol
from app.core.web import csrf_ok, redirigir
from app.dependencies import SesionBD, templates
from app.models.usuario import ROLES_GESTION, Usuario
from app.repositories import finanzas as repo_finanzas
from app.repositories import miembro as repo_miembro
from app.schemas.comunes import primer_mensaje
from app.schemas.finanzas import (
    ActivoEntrada,
    CategoriaEntrada,
    EgresoEntrada,
    GastoFijoEntrada,
)
from app.services import finanzas as servicio_finanzas

router = APIRouter(tags=["finanzas"])


def _fecha(texto: str) -> date | None:
    limpio = (texto or "").strip()
    if not limpio:
        return None
    try:
        return date.fromisoformat(limpio)
    except ValueError:
        return None


@router.get("/finanzas", response_class=HTMLResponse)
async def panel_finanzas(
    request: Request,
    db: SesionBD,
    usuario: Annotated[Usuario, Depends(requiere_rol(*ROLES_GESTION))],
    desde: str = "",
    hasta: str = "",
    categoria: str = "",
) -> HTMLResponse:
    """Panel de egresos, activos, gastos fijos y categorías (UI-04)."""
    categoria_id = int(categoria) if categoria.isdigit() else None
    egresos = servicio_finanzas.listar_egresos(
        db,
        desde=_fecha(desde),
        hasta=_fecha(hasta),
        categoria_id=categoria_id,
    )
    return templates.TemplateResponse(
        request=request,
        name="finanzas/panel.html",
        context={
            "egresos": egresos,
            "total_egresos_clp": sum(int(e.monto_clp) for e in egresos),
            "categorias": repo_finanzas.listar_categorias(db, solo_activas=False),
            "categorias_activas": repo_finanzas.listar_categorias(db),
            "gastos_fijos": repo_finanzas.listar_gastos_fijos(db, solo_activos=False),
            "miembros": repo_miembro.listar(db),
            "filtros": {"desde": desde, "hasta": hasta, "categoria": categoria},
        },
    )


@router.post("/finanzas/egresos", response_model=None)
async def crear_egreso(
    request: Request,
    db: SesionBD,
    usuario: Annotated[Usuario, Depends(requiere_rol(*ROLES_GESTION))],
    csrf_token: str = Form(""),
    monto: str = Form(""),
    concepto: str = Form(""),
    categoria_id: str = Form(""),
    fecha: str = Form(""),
) -> RedirectResponse:
    """Registra un egreso con su categoría (T5.25, CA-07)."""
    if not csrf_ok(request, csrf_token):
        return redirigir("/finanzas")
    try:
        entrada = EgresoEntrada(
            monto=monto,
            concepto=concepto,
            categoria_id=categoria_id,
            fecha=fecha,
        )
    except ValidationError as exc:
        flash(request, "error", primer_mensaje(exc))
        return redirigir("/finanzas")
    try:
        servicio_finanzas.registrar_egreso(
            db,
            monto_clp=entrada.monto,
            concepto=entrada.concepto,
            categoria_id=entrada.categoria_id,
            fecha=entrada.fecha or date.today(),
            usuario=usuario,
        )
    except servicio_finanzas.ErrorFinanzas as exc:
        flash(request, "error", str(exc))
    else:
        flash(request, "ok", "Egreso registrado correctamente.")
    return redirigir("/finanzas")


@router.post("/finanzas/activos", response_model=None)
async def crear_activo(
    request: Request,
    db: SesionBD,
    usuario: Annotated[Usuario, Depends(requiere_rol(*ROLES_GESTION))],
    csrf_token: str = Form(""),
    costo: str = Form(""),
    descripcion: str = Form(""),
    miembro_responsable_id: str = Form(""),
    fecha: str = Form(""),
) -> RedirectResponse:
    """Registra la adquisición de un activo con su responsable (T5.26, CA-08)."""
    if not csrf_ok(request, csrf_token):
        return redirigir("/finanzas")
    try:
        entrada = ActivoEntrada(
            costo=costo,
            descripcion=descripcion,
            miembro_responsable_id=miembro_responsable_id,
            fecha=fecha,
        )
    except ValidationError as exc:
        flash(request, "error", primer_mensaje(exc))
        return redirigir("/finanzas")
    try:
        servicio_finanzas.registrar_activo(
            db,
            costo_clp=entrada.costo,
            descripcion=entrada.descripcion,
            miembro_responsable_id=entrada.miembro_responsable_id,
            fecha=entrada.fecha or date.today(),
            usuario=usuario,
        )
    except servicio_finanzas.ErrorFinanzas as exc:
        flash(request, "error", str(exc))
    else:
        flash(request, "ok", "Activo registrado con su responsable de compra.")
    return redirigir("/finanzas")


@router.post("/finanzas/gastos-fijos", response_model=None)
async def crear_gasto_fijo(
    request: Request,
    db: SesionBD,
    usuario: Annotated[Usuario, Depends(requiere_rol(*ROLES_GESTION))],
    csrf_token: str = Form(""),
    monto: str = Form(""),
    concepto: str = Form(""),
    fecha: str = Form(""),
) -> RedirectResponse:
    """Registra un gasto fijo operativo mensual (T5.27, CA-09)."""
    if not csrf_ok(request, csrf_token):
        return redirigir("/finanzas")
    try:
        entrada = GastoFijoEntrada(monto=monto, concepto=concepto, fecha=fecha)
    except ValidationError as exc:
        flash(request, "error", primer_mensaje(exc))
        return redirigir("/finanzas")
    try:
        servicio_finanzas.registrar_gasto_fijo(
            db,
            concepto=entrada.concepto,
            monto_clp=entrada.monto,
            fecha=entrada.fecha or date.today(),
            usuario=usuario,
        )
    except servicio_finanzas.ErrorFinanzas as exc:
        flash(request, "error", str(exc))
    else:
        flash(request, "ok", "Gasto fijo registrado como egreso recurrente.")
    return redirigir("/finanzas")


@router.post("/finanzas/categorias", response_model=None)
async def crear_categoria(
    request: Request,
    db: SesionBD,
    usuario: Annotated[Usuario, Depends(requiere_rol(*ROLES_GESTION))],
    csrf_token: str = Form(""),
    nombre: str = Form(""),
) -> RedirectResponse:
    """Crea una categoría de egreso personalizada (T5.24, CA-07)."""
    if not csrf_ok(request, csrf_token):
        return redirigir("/finanzas")
    try:
        entrada = CategoriaEntrada(nombre=nombre)
    except ValidationError as exc:
        flash(request, "error", primer_mensaje(exc))
        return redirigir("/finanzas")
    try:
        servicio_finanzas.crear_categoria_egreso(
            db, nombre=entrada.nombre, usuario=usuario
        )
    except servicio_finanzas.ErrorFinanzas as exc:
        flash(request, "error", str(exc))
    else:
        flash(request, "ok", "Categoría de egreso creada.")
    return redirigir("/finanzas")


@router.post("/finanzas/categorias/{categoria_id}/estado", response_model=None)
async def cambiar_estado_categoria(
    request: Request,
    db: SesionBD,
    usuario: Annotated[Usuario, Depends(requiere_rol(*ROLES_GESTION))],
    categoria_id: int,
    csrf_token: str = Form(""),
    activo: str = Form("1"),
) -> RedirectResponse:
    """Activa o desactiva una categoría de egreso (P-7)."""
    if not csrf_ok(request, csrf_token):
        return redirigir("/finanzas")
    categoria = repo_finanzas.obtener_categoria(db, categoria_id)
    if categoria is None:
        flash(request, "error", "La categoría indicada no existe.")
        return redirigir("/finanzas")
    servicio_finanzas.cambiar_estado_categoria(
        db, categoria, activo=(activo not in ("0", "false", "False", ""))
    )
    flash(request, "ok", "Estado de la categoría actualizado.")
    return redirigir("/finanzas")
