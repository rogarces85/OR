"""Reportes: consolidado por periodo e informe calendario (F-19, F-21, UI-09)."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from pydantic import ValidationError

from app.core.seguridad import requiere_rol
from app.dependencies import SesionBD, templates
from app.models.usuario import ROLES_GESTION, Usuario
from app.repositories import miembro as repo_miembro
from app.schemas.reporte import RangoFechasEntrada
from app.services import reportes as servicio_reportes

router = APIRouter(tags=["reportes"])


def _anio(texto: str) -> int:
    try:
        valor = int(texto)
    except (TypeError, ValueError):
        return date.today().year
    return valor if 2000 <= valor <= 2100 else date.today().year


@router.get("/reportes", response_class=HTMLResponse)
async def panel_reportes(
    request: Request,
    db: SesionBD,
    usuario: Annotated[Usuario, Depends(requiere_rol(*ROLES_GESTION))],
    desde: str = "",
    hasta: str = "",
) -> HTMLResponse:
    """Reporte consolidado de ingresos contra egresos por periodo (T5.32, T5.34)."""
    hoy = date.today()
    mensajes: list[dict[str, str]] = []
    try:
        rango = RangoFechasEntrada(desde=desde, hasta=hasta)
    except ValidationError:
        rango = RangoFechasEntrada()
        mensajes.append(
            {
                "tipo": "error",
                "texto": "El rango de fechas no es válido (formato AAAA-MM-DD): "
                "se usó el periodo por defecto.",
            }
        )
    fecha_desde = rango.desde or date(hoy.year, 1, 1)
    fecha_hasta = rango.hasta or hoy
    if fecha_desde > fecha_hasta:
        fecha_desde, fecha_hasta = fecha_hasta, fecha_desde
        mensajes.append(
            {
                "tipo": "error",
                "texto": "El rango estaba invertido: se corrigió el orden "
                "de las fechas.",
            }
        )
    reporte = servicio_reportes.reporte_consolidado(
        db, desde=fecha_desde, hasta=fecha_hasta
    )
    return templates.TemplateResponse(
        request=request,
        name="reportes/panel.html",
        context={
            "reporte": reporte,
            "filtros": {
                "desde": fecha_desde.isoformat(),
                "hasta": fecha_hasta.isoformat(),
            },
            "mensajes": mensajes,
        },
    )


@router.get("/reportes/informe/{miembro_id}", response_class=HTMLResponse)
async def informe_calendario(
    request: Request,
    db: SesionBD,
    usuario: Annotated[Usuario, Depends(requiere_rol(*ROLES_GESTION))],
    miembro_id: int,
    anio: str = "",
) -> HTMLResponse:
    """Informe mensual en formato calendario de un miembro (T5.33, UI-06)."""
    miembro = repo_miembro.obtener(db, miembro_id)
    if miembro is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="El miembro no existe."
        )
    anio_valor = _anio(anio)
    informe = servicio_reportes.informe_calendario(db, miembro, anio_valor)
    return templates.TemplateResponse(
        request=request,
        name="reportes/informe.html",
        context={"miembro": miembro, "informe": informe, "anio": anio_valor},
    )
