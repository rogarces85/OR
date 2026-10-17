"""Negociación de deuda (F-24, RN-22, P-6): listado, creación, aceptación y pago."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import ValidationError

from app.core.seguridad import flash, requiere_rol
from app.core.web import csrf_ok, redirigir
from app.dependencies import SesionBD, templates
from app.models.pago import MEDIOS_PAGO
from app.models.usuario import ROLES_GESTION, Usuario
from app.repositories import membresia as repo_membresia
from app.repositories import miembro as repo_miembro
from app.schemas.comunes import primer_mensaje
from app.schemas.negociacion import NegociacionEntrada
from app.services import morosidad as servicio_morosidad
from app.services import negociacion as servicio_negociacion

router = APIRouter(tags=["negociaciones"])


def _info_miembro(db, miembro):
    """Calcula la morosidad vigente de un miembro (con efecto de negociación)."""
    cuotas = repo_membresia.cuotas_mensuales_de_miembro(db, miembro.id)
    return servicio_morosidad.calcular_morosidad(
        miembro,
        cuotas,
        deuda_excluida_clp=repo_membresia.deuda_negociada_clp(db, miembro.id),
    )


@router.get("/negociaciones", response_class=HTMLResponse)
async def panel_negociaciones(
    request: Request,
    db: SesionBD,
    usuario: Annotated[Usuario, Depends(requiere_rol(*ROLES_GESTION))],
) -> HTMLResponse:
    """Lista las negociaciones y los morosos elegibles (>6 meses) (F-24, T5.21)."""
    elegibles = []
    for miembro, info in servicio_morosidad.listar_miembros_con_morosidad(db):
        if servicio_negociacion.puede_negociar(info):
            elegibles.append((miembro, info))
    elegibles.sort(key=lambda par: -par[1].monto_deuda_clp)
    return templates.TemplateResponse(
        request=request,
        name="negociaciones/panel.html",
        context={
            "negociaciones": repo_membresia.listar_negociaciones(db),
            "elegibles": elegibles,
            "estados": servicio_negociacion.ETIQUETAS_ESTADO,
        },
    )


@router.post("/negociaciones", response_model=None)
async def crear_negociacion(
    request: Request,
    db: SesionBD,
    usuario: Annotated[Usuario, Depends(requiere_rol(*ROLES_GESTION))],
    csrf_token: str = Form(""),
    miembro_id: int = Form(...),
    descuento_pct: str = Form("0"),
) -> RedirectResponse:
    """Crea una negociación con el descuento indicado (T5.21, CA-25)."""
    if not csrf_ok(request, csrf_token):
        return redirigir("/negociaciones")
    try:
        entrada = NegociacionEntrada(
            miembro_id=miembro_id, descuento_pct=descuento_pct
        )
    except ValidationError as exc:
        flash(request, "error", primer_mensaje(exc))
        return redirigir("/negociaciones")
    miembro = repo_miembro.obtener(db, entrada.miembro_id)
    if miembro is None:
        flash(request, "error", "El miembro indicado no existe.")
        return redirigir("/negociaciones")

    info = _info_miembro(db, miembro)
    try:
        servicio_negociacion.crear_negociacion(
            db,
            miembro=miembro,
            info=info,
            descuento_pct=entrada.descuento_pct,
            usuario=usuario,
        )
    except servicio_negociacion.ErrorNegociacion as exc:
        flash(request, "error", str(exc))
    else:
        flash(
            request,
            "ok",
            "Negociación propuesta: la deuda sigue contando para el color hasta "
            "aceptarla (P-6).",
        )
    return redirigir("/negociaciones")


@router.post("/negociaciones/{negociacion_id}/aceptar", response_model=None)
async def aceptar_negociacion(
    request: Request,
    db: SesionBD,
    usuario: Annotated[Usuario, Depends(requiere_rol(*ROLES_GESTION))],
    negociacion_id: int,
    csrf_token: str = Form(""),
) -> RedirectResponse:
    """Acepta la negociación: su deuda deja de contar para el color (P-6)."""
    if not csrf_ok(request, csrf_token):
        return redirigir("/negociaciones")
    negociacion = repo_membresia.obtener_negociacion(db, negociacion_id)
    if negociacion is None:
        flash(request, "error", "La negociación indicada no existe.")
        return redirigir("/negociaciones")
    try:
        servicio_negociacion.aceptar_negociacion(db, negociacion)
    except servicio_negociacion.ErrorNegociacion as exc:
        flash(request, "error", str(exc))
    else:
        flash(
            request,
            "ok",
            "Negociación aceptada: la deuda se excluye del color de morosidad (P-6).",
        )
    return redirigir("/negociaciones")


@router.post("/negociaciones/{negociacion_id}/pagar", response_model=None)
async def pagar_negociacion(
    request: Request,
    db: SesionBD,
    usuario: Annotated[Usuario, Depends(requiere_rol(*ROLES_GESTION))],
    negociacion_id: int,
    csrf_token: str = Form(""),
    medio: str = Form("transferencia"),
) -> RedirectResponse:
    """Registra el pago de la negociación y descarga la deuda (T5.23)."""
    if not csrf_ok(request, csrf_token):
        return redirigir("/negociaciones")
    negociacion = repo_membresia.obtener_negociacion(db, negociacion_id)
    if negociacion is None:
        flash(request, "error", "La negociación indicada no existe.")
        return redirigir("/negociaciones")
    if medio not in MEDIOS_PAGO:
        flash(request, "error", "El medio de pago no es válido (RN-19).")
        return redirigir("/negociaciones")
    try:
        servicio_negociacion.registrar_pago_negociacion(
            db, negociacion=negociacion, medio=medio, usuario=usuario
        )
    except servicio_negociacion.ErrorNegociacion as exc:
        flash(request, "error", str(exc))
    else:
        flash(request, "ok", "Pago de la negociación registrado: deuda regularizada.")
    return redirigir("/negociaciones")
