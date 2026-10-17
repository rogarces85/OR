"""Membresías: catálogo de cuotas y generación de las cuotas mensuales.

Cubre T5.7 (catálogo de cuotas con los tres niveles, CA-02) y T5.8 (generación
de las cuotas del periodo para los miembros activos y no exentos, F-10).
"""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import ValidationError

from app.core.seguridad import flash, requiere_rol, validar_csrf
from app.dependencies import SesionBD, templates
from app.models.usuario import ROLES_GESTION, Usuario
from app.repositories import membresia as repo_membresia
from app.schemas.membresia import GeneracionCuotasEntrada
from app.services import membresias as servicio_membresias

router = APIRouter(tags=["membresías"])

ANIO_MINIMO = 2000
ANIO_MAXIMO = 2100
MESES_VALIDOS = tuple(range(1, 13))
MESES_NOMBRES = (
    "Enero",
    "Febrero",
    "Marzo",
    "Abril",
    "Mayo",
    "Junio",
    "Julio",
    "Agosto",
    "Septiembre",
    "Octubre",
    "Noviembre",
    "Diciembre",
)


def _periodo_desde(request: Request) -> tuple[int, int]:
    """Lee el periodo (año/mes) de la consulta, con el mes en curso por omisión."""
    hoy = date.today()
    anio_txt = (request.query_params.get("anio") or "").strip()
    mes_txt = (request.query_params.get("mes") or "").strip()
    try:
        anio = int(anio_txt) if anio_txt else hoy.year
    except ValueError:
        anio = hoy.year
    try:
        mes = int(mes_txt) if mes_txt else hoy.month
    except ValueError:
        mes = hoy.month
    if not ANIO_MINIMO <= anio <= ANIO_MAXIMO:
        anio = hoy.year
    if mes not in MESES_VALIDOS:
        mes = hoy.month
    return anio, mes


@router.get("/membresias", response_class=HTMLResponse)
async def mostrar_catalogo(
    request: Request,
    db: SesionBD,
    usuario: Annotated[Usuario, Depends(requiere_rol(*ROLES_GESTION))],
) -> HTMLResponse:
    """Muestra el catálogo de cuotas y la generación del periodo (T5.7, T5.8)."""
    anio, mes = _periodo_desde(request)
    niveles = repo_membresia.listar_niveles(db)
    facturables = servicio_membresias.miembros_facturables(db)
    cuotas_periodo = repo_membresia.listar_por_periodo(db, anio, mes)
    return templates.TemplateResponse(
        request=request,
        name="membresias/catalogo.html",
        context={
            "niveles": niveles,
            "anio": anio,
            "mes": mes,
            "meses": MESES_VALIDOS,
            "meses_nombres": MESES_NOMBRES,
            "total_facturables": len(facturables),
            "cuotas_periodo": cuotas_periodo,
        },
    )


@router.post("/membresias/generar", response_model=None)
async def generar_cuotas(
    request: Request,
    db: SesionBD,
    usuario: Annotated[Usuario, Depends(requiere_rol(*ROLES_GESTION))],
    csrf_token: str = Form(""),
    anio: str = Form(""),
    mes: str = Form(""),
) -> RedirectResponse:
    """Genera las cuotas del periodo para los miembros activos y no exentos (T5.8)."""
    try:
        entrada = GeneracionCuotasEntrada(anio=anio, mes=mes)
    except ValidationError:
        flash(request, "error", "Indica un periodo válido para generar las cuotas.")
        return RedirectResponse("/membresias", status_code=status.HTTP_303_SEE_OTHER)

    if not validar_csrf(request, csrf_token):
        flash(request, "error", "Tu sesión expiró. Inténtalo nuevamente.")
        return RedirectResponse("/membresias", status_code=status.HTTP_303_SEE_OTHER)

    creadas = servicio_membresias.generar_cuotas_del_periodo(
        db, entrada.anio, entrada.mes
    )
    destino = f"/membresias?anio={entrada.anio}&mes={entrada.mes}"
    if creadas:
        flash(
            request,
            "ok",
            f"Se generaron {len(creadas)} cuota(s) para el periodo "
            f"{entrada.mes:02d}/{entrada.anio}.",
        )
    else:
        flash(
            request,
            "ok",
            f"No había cuotas por generar en el periodo {entrada.mes:02d}/{entrada.anio}: "
            "todos los miembros activos y no exentos ya tienen la suya.",
        )
    return RedirectResponse(destino, status_code=status.HTTP_303_SEE_OTHER)
