"""Reportes: consolidado por periodo, informe calendario y sus exportaciones.

Cubre F-19, F-21 y UI-09 (T5.32-T5.34) y la exportación XLSX/PDF (T7.2, T7.3).
"""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from pydantic import ValidationError

from app.core.seguridad import flash, requiere_rol
from app.dependencies import SesionBD, templates
from app.models.usuario import ROLES_GESTION, Usuario
from app.repositories import miembro as repo_miembro
from app.schemas.reporte import RangoFechasEntrada
from app.services import exportacion as servicio_exportacion
from app.services import reportes as servicio_reportes

router = APIRouter(tags=["reportes"])


def _anio(texto: str) -> int:
    try:
        valor = int(texto)
    except (TypeError, ValueError):
        return date.today().year
    return valor if 2000 <= valor <= 2100 else date.today().year


def _rango(desde: str, hasta: str) -> tuple[date, date, list[dict[str, str]]]:
    """Resuelve el rango pedido, aplicando el periodo por defecto y avisos.

    Reutilizado por el panel y por la exportación para que ambos coincidan
    (CA-10, CA-11). Devuelve las fechas normalizadas y los mensajes de aviso.
    """
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
    return fecha_desde, fecha_hasta, mensajes


def _descarga(contenido: bytes, tipo: str, nombre: str) -> Response:
    """Construye una respuesta de descarga con el tipo y nombre indicados."""
    return Response(
        content=contenido,
        media_type=tipo,
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )


@router.get("/reportes", response_class=HTMLResponse)
async def panel_reportes(
    request: Request,
    db: SesionBD,
    usuario: Annotated[Usuario, Depends(requiere_rol(*ROLES_GESTION))],
    desde: str = "",
    hasta: str = "",
) -> HTMLResponse:
    """Reporte consolidado de ingresos contra egresos por periodo (T5.32, T5.34)."""
    fecha_desde, fecha_hasta, mensajes = _rango(desde, hasta)
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


@router.get("/reportes/exportar.xlsx")
async def exportar_reporte_xlsx(
    request: Request,
    db: SesionBD,
    usuario: Annotated[Usuario, Depends(requiere_rol(*ROLES_GESTION))],
    desde: str = "",
    hasta: str = "",
) -> Response:
    """Descarga el reporte consolidado en XLSX (F-20, T7.2, P-3).

    Si el periodo no tiene movimientos se informa en pantalla y se vuelve al
    panel, en lugar de descargar un archivo vacío (sección 9 de SPECS).
    """
    fecha_desde, fecha_hasta, _ = _rango(desde, hasta)
    reporte = servicio_reportes.reporte_consolidado(
        db, desde=fecha_desde, hasta=fecha_hasta
    )
    if reporte.sin_movimientos:
        flash(
            request,
            "error",
            "No hay contenido para exportar en el periodo seleccionado.",
        )
        return RedirectResponse(
            url=(
                f"/reportes?desde={fecha_desde.isoformat()}"
                f"&hasta={fecha_hasta.isoformat()}"
            ),
            status_code=status.HTTP_303_SEE_OTHER,
        )
    contenido = servicio_exportacion.exportar_reporte_xlsx(reporte)
    nombre = (
        f"reporte_consolidado_{fecha_desde.isoformat()}_"
        f"{fecha_hasta.isoformat()}.xlsx"
    )
    return _descarga(contenido, servicio_exportacion.CONTENIDO_XLSX, nombre)


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


@router.get("/reportes/informe/{miembro_id}/exportar.pdf")
async def exportar_informe_pdf(
    db: SesionBD,
    usuario: Annotated[Usuario, Depends(requiere_rol(*ROLES_GESTION))],
    miembro_id: int,
    anio: str = "",
) -> Response:
    """Descarga el informe calendario en PDF (F-21, T7.3, P-3)."""
    miembro = repo_miembro.obtener(db, miembro_id)
    if miembro is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="El miembro no existe."
        )
    anio_valor = _anio(anio)
    informe = servicio_reportes.informe_calendario(db, miembro, anio_valor)
    contenido = servicio_exportacion.exportar_informe_pdf(informe)
    nombre = f"informe_{miembro_id}_{anio_valor}.pdf"
    return _descarga(contenido, servicio_exportacion.CONTENIDO_PDF, nombre)
