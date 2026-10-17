"""Morosidad: panel con colores y aviso manual al Tesorero.

Cubre T5.19 (panel UI-08) y T5.20 (aviso y plantilla de correo con enlace
``mailto:`` y marca de enviado; F-23, RN-13).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse

from app.core.seguridad import flash, requiere_rol
from app.core.web import csrf_ok, redirigir
from app.dependencies import SesionBD, templates
from app.models.usuario import ROLES_GESTION, Usuario
from app.repositories import configuracion as repo_configuracion
from app.repositories import membresia as repo_membresia
from app.repositories import miembro as repo_miembro
from app.services import correo as servicio_correo
from app.services import morosidad as servicio_morosidad
from app.services.morosidad import COLOR_NARANJO, COLOR_ROJO, COLOR_VERDE

router = APIRouter(tags=["morosidad"])


@router.get("/morosidad", response_class=HTMLResponse)
async def panel_morosidad(
    request: Request,
    db: SesionBD,
    usuario: Annotated[Usuario, Depends(requiere_rol(*ROLES_GESTION))],
    q: str = "",
    color: str = "",
) -> HTMLResponse:
    """Panel de morosidad con colores y filtros (UI-08, T5.19)."""
    filas = servicio_morosidad.listar_miembros_con_morosidad(
        db, texto=q or None, color=color or None
    )
    filas.sort(key=lambda par: (-par[1].meses_deuda, par[0].nombre_completo))
    resumen = {
        COLOR_VERDE: sum(1 for _, info in filas if info.color == COLOR_VERDE),
        COLOR_NARANJO: sum(1 for _, info in filas if info.color == COLOR_NARANJO),
        COLOR_ROJO: sum(1 for _, info in filas if info.color == COLOR_ROJO),
        "deuda_total_clp": sum(info.monto_deuda_clp for _, info in filas),
    }
    return templates.TemplateResponse(
        request=request,
        name="morosidad/panel.html",
        context={
            "filas": filas,
            "resumen": resumen,
            "filtros": {"q": q, "color": color},
        },
    )


@router.post("/morosidad/aviso", response_model=None)
async def generar_aviso(
    request: Request,
    db: SesionBD,
    usuario: Annotated[Usuario, Depends(requiere_rol(*ROLES_GESTION))],
    csrf_token: str = Form(""),
    miembro_id: int = Form(...),
) -> RedirectResponse:
    """Genera el aviso de morosidad para el Tesorero (F-23, CA-15)."""
    if not csrf_ok(request, csrf_token):
        return redirigir("/morosidad")
    miembro = repo_miembro.obtener(db, miembro_id)
    if miembro is None:
        flash(request, "error", "El miembro indicado no existe.")
        return redirigir("/morosidad")

    cuotas = repo_membresia.cuotas_mensuales_de_miembro(db, miembro.id)
    info = servicio_morosidad.calcular_morosidad(
        miembro,
        cuotas,
        deuda_excluida_clp=repo_membresia.deuda_negociada_clp(db, miembro.id),
    )
    if info.meses_deuda <= 0:
        flash(
            request,
            "error",
            "El miembro está al día: no corresponde generar un aviso de morosidad.",
        )
        return redirigir("/morosidad")

    plantilla = repo_configuracion.obtener_plantilla(db)
    aviso = repo_configuracion.crear_aviso(
        db,
        miembro_id=miembro.id,
        detalle=servicio_correo.detalle_morosidad(info),
        plantilla_id=plantilla.id if plantilla else None,
    )
    repo_configuracion.guardar_aviso(db, aviso)
    flash(
        request,
        "ok",
        "Aviso generado. Revisa el texto y envíalo desde tu cliente de correo.",
    )
    return redirigir(f"/morosidad/avisos/{aviso.id}")


@router.get("/morosidad/avisos", response_class=HTMLResponse)
async def listar_avisos(
    request: Request,
    db: SesionBD,
    usuario: Annotated[Usuario, Depends(requiere_rol(*ROLES_GESTION))],
) -> HTMLResponse:
    """Lista los avisos de morosidad generados (F-23)."""
    return templates.TemplateResponse(
        request=request,
        name="morosidad/avisos.html",
        context={"avisos": repo_configuracion.listar_avisos(db)},
    )


def _obtener_aviso(db, aviso_id: int):
    aviso = repo_configuracion.obtener_aviso(db, aviso_id)
    if aviso is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="El aviso no existe."
        )
    return aviso


@router.get("/morosidad/avisos/{aviso_id}", response_class=HTMLResponse)
async def ver_aviso(
    request: Request,
    db: SesionBD,
    usuario: Annotated[Usuario, Depends(requiere_rol(*ROLES_GESTION))],
    aviso_id: int,
) -> HTMLResponse:
    """Muestra el aviso con el texto y el enlace ``mailto:`` (UI-11, T5.20)."""
    aviso = _obtener_aviso(db, aviso_id)
    miembro = aviso.miembro
    cuotas = repo_membresia.cuotas_mensuales_de_miembro(db, miembro.id)
    info = servicio_morosidad.calcular_morosidad(
        miembro,
        cuotas,
        deuda_excluida_clp=repo_membresia.deuda_negociada_clp(db, miembro.id),
    )
    plantilla = aviso.plantilla or repo_configuracion.obtener_plantilla(db)
    cuenta = repo_configuracion.obtener_cuenta(db)
    asunto, cuerpo = servicio_correo.renderizar_plantilla(
        plantilla, miembro, info, cuenta
    )
    enlace = servicio_correo.generar_enlace_correo(miembro.email, asunto, cuerpo)
    return templates.TemplateResponse(
        request=request,
        name="morosidad/aviso.html",
        context={
            "aviso": aviso,
            "miembro": miembro,
            "informacion": info,
            "cuenta": cuenta,
            "asunto": asunto,
            "cuerpo": cuerpo,
            "enlace": enlace,
        },
    )


@router.post("/morosidad/avisos/{aviso_id}/enviado", response_model=None)
async def marcar_enviado(
    request: Request,
    db: SesionBD,
    usuario: Annotated[Usuario, Depends(requiere_rol(*ROLES_GESTION))],
    aviso_id: int,
    csrf_token: str = Form(""),
) -> RedirectResponse:
    """Marca el aviso como enviado por el Tesorero (F-23, declarativo)."""
    if not csrf_ok(request, csrf_token):
        return redirigir(f"/morosidad/avisos/{aviso_id}")
    aviso = _obtener_aviso(db, aviso_id)
    servicio_correo.marcar_aviso_enviado(db, aviso, usuario)
    flash(request, "ok", "Aviso marcado como enviado.")
    return redirigir(f"/morosidad/avisos/{aviso.id}")
