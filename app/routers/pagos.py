"""Pagos: registro del pago personalizado e ingresos filtrados.

Cubre T5.11 (formulario UI-07), T5.12 (registro atómico) y T5.16 (listado de
ingresos con filtros, F-15).
"""

from __future__ import annotations

import io
from datetime import date
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from pydantic import ValidationError

from app.core.formato import formatear_clp
from app.core.periodos import ANIO_MAXIMO, ANIO_MINIMO, MESES_NOMBRES
from app.core.seguridad import flash, requiere_rol
from app.core.web import csrf_ok, redirigir
from app.dependencies import SesionBD, templates
from app.models.miembro import Miembro
from app.models.pago import MEDIOS_PAGO
from app.models.usuario import ROLES_GESTION, Usuario
from app.repositories import membresia as repo_membresia
from app.repositories import miembro as repo_miembro
from app.repositories import pago as repo_pago
from app.schemas.comunes import primer_mensaje
from app.schemas.pago import PagoEntrada
from app.services import pagos as servicio_pagos

router = APIRouter(tags=["pagos"])

MESES_VALIDOS = tuple(range(1, 13))


def _obtener_miembro(db, miembro_id: int) -> Miembro | None:
    return repo_miembro.obtener(db, miembro_id)


def _datos_formulario(
    *, miembro: Miembro | None, form: dict | None = None
) -> dict:
    """Contexto común de la plantilla del formulario de pago."""
    hoy = date.today()
    datos = dict(form or {})
    # La plantilla recorre la selección de meses; normaliza el vacío a lista.
    if not datos.get("meses"):
        datos["meses"] = []
    return {
        "miembro": miembro,
        "datos": datos,
        "meses": MESES_VALIDOS,
        "meses_nombres": MESES_NOMBRES,
        "medios": MEDIOS_PAGO,
        "anio_actual": hoy.year,
        "anio_min": ANIO_MINIMO,
        "anio_max": ANIO_MAXIMO,
    }


# --------------------------------------------------------------------------- #
# Ingresos (T5.16, F-15)
# --------------------------------------------------------------------------- #


@router.get("/pagos", response_class=HTMLResponse)
async def listar_pagos(
    request: Request,
    db: SesionBD,
    usuario: Annotated[Usuario, Depends(requiere_rol(*ROLES_GESTION))],
    desde: str = "",
    hasta: str = "",
    nivel: str = "",
    situacion: str = "",
) -> HTMLResponse:
    """Lista los ingresos y los filtra por tipo de cuota y estado (F-15, CA-06)."""
    fecha_desde = _fecha(desde)
    fecha_hasta = _fecha(hasta)
    filas = repo_pago.listar_ingresos(
        db,
        desde=fecha_desde,
        hasta=fecha_hasta,
        nivel_codigo=nivel or None,
        situacion=situacion or None,
    )
    total = sum(int(pago.monto_clp) for pago in filas)
    return templates.TemplateResponse(
        request=request,
        name="pagos/lista.html",
        context={
            "pagos": filas,
            "total_clp": total,
            "niveles": repo_membresia.listar_niveles(db),
            "filtros": {
                "desde": desde,
                "hasta": hasta,
                "nivel": nivel,
                "situacion": situacion,
            },
        },
    )


def _fecha(texto: str) -> date | None:
    """Convierte un texto AAAA-MM-DD en fecha; devuelve ``None`` si no es válida."""
    limpio = (texto or "").strip()
    if not limpio:
        return None
    try:
        return date.fromisoformat(limpio)
    except ValueError:
        return None


# --------------------------------------------------------------------------- #
# Registro de un pago (T5.11, T5.12)
# --------------------------------------------------------------------------- #


@router.get("/pagos/nuevo", response_class=HTMLResponse)
async def mostrar_pago(
    request: Request,
    db: SesionBD,
    usuario: Annotated[Usuario, Depends(requiere_rol(*ROLES_GESTION))],
    miembro_id: int | None = None,
) -> HTMLResponse:
    """Muestra el formulario del pago personalizado (UI-07, T5.11)."""
    miembro = _obtener_miembro(db, miembro_id) if miembro_id else None
    contexto = _datos_formulario(miembro=miembro)
    contexto["miembros"] = repo_miembro.listar(db)
    if miembro is not None:
        contexto["deuda"] = servicio_pagos.obtener_deuda(db, miembro)
        contexto["saldo_a_favor"] = servicio_pagos.saldo_a_favor(db, miembro)
    return templates.TemplateResponse(
        request=request, name="pagos/formulario.html", context=contexto
    )


@router.get("/miembros/{miembro_id}/pagos/nuevo", response_class=HTMLResponse)
async def mostrar_pago_miembro(
    request: Request,
    db: SesionBD,
    usuario: Annotated[Usuario, Depends(requiere_rol(*ROLES_GESTION))],
    miembro_id: int,
) -> HTMLResponse:
    """Formulario de pago para un miembro concreto (UI-07)."""
    miembro = _obtener_miembro(db, miembro_id)
    if miembro is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    contexto = _datos_formulario(miembro=miembro)
    contexto["miembros"] = repo_miembro.listar(db)
    contexto["deuda"] = servicio_pagos.obtener_deuda(db, miembro)
    contexto["saldo_a_favor"] = servicio_pagos.saldo_a_favor(db, miembro)
    return templates.TemplateResponse(
        request=request, name="pagos/formulario.html", context=contexto
    )


@router.post("/miembros/{miembro_id}/pagos", response_model=None)
async def registrar_pago(
    request: Request,
    db: SesionBD,
    usuario: Annotated[Usuario, Depends(requiere_rol(*ROLES_GESTION))],
    miembro_id: int,
    csrf_token: str = Form(""),
    monto: str = Form(""),
    medio: str = Form("transferencia"),
    anio: str = Form(""),
    meses: Annotated[list[str] | None, Form()] = None,
    fecha_pago: str = Form(""),
    observaciones: str = Form(""),
) -> HTMLResponse | RedirectResponse:
    """Registra un pago del miembro en una única transacción (T5.12)."""
    miembro = _obtener_miembro(db, miembro_id)
    if miembro is None:
        return redirigir("/pagos/nuevo")
    if not csrf_ok(request, csrf_token):
        return redirigir(f"/miembros/{miembro.id}/pagos/nuevo")

    form = {
        "monto": monto,
        "medio": medio,
        "anio": anio,
        "meses": meses,
        "fecha_pago": fecha_pago,
        "observaciones": observaciones,
    }
    try:
        entrada = PagoEntrada(
            monto=monto,
            medio=medio,
            anio=anio or date.today().year,
            meses=meses,
            fecha_pago=fecha_pago,
            observaciones=observaciones,
        )
    except ValidationError as exc:
        return _formulario_con_error(db, request, miembro, form, primer_mensaje(exc))

    try:
        resultado = servicio_pagos.registrar_pago(
            db,
            miembro=miembro,
            monto_clp=entrada.monto,
            anio=entrada.anio,
            meses=entrada.meses,
            fecha_pago=entrada.fecha_pago or date.today(),
            medio=entrada.medio,
            observaciones=entrada.observaciones,
            usuario=usuario,
        )
    except servicio_pagos.ErrorPago as exc:
        return _formulario_con_error(db, request, miembro, form, str(exc))

    partes = [f"Pago de $ {formatear_clp(resultado.pago.monto_clp)} registrado."]
    if resultado.imputaciones:
        partes.append(
            f"Imputado a {len(resultado.imputaciones)} cuota(s)."
        )
    if resultado.abono_clp:
        partes.append(
            f"Abono a favor de $ {formatear_clp(resultado.abono_clp)} "
            "(aplicado a la siguiente cuota)."
        )
    if resultado.activado:
        partes.append("El miembro quedó Activo: completó su pago inicial.")
    flash(request, "ok", " ".join(partes))
    return redirigir(f"/miembros/{miembro.id}")


def _formulario_con_error(
    db, request: Request, miembro: Miembro, form: dict, mensaje: str
) -> HTMLResponse:
    """Vuelve a mostrar el formulario de pago con el error indicado (CA-21)."""
    contexto = _datos_formulario(miembro=miembro, form=form)
    contexto["miembros"] = repo_miembro.listar(db)
    contexto["deuda"] = servicio_pagos.obtener_deuda(db, miembro)
    contexto["saldo_a_favor"] = servicio_pagos.saldo_a_favor(db, miembro)
    contexto["mensajes"] = [{"tipo": "error", "texto": mensaje}]
    return templates.TemplateResponse(
        request=request, name="pagos/formulario.html", context=contexto
    )


# --------------------------------------------------------------------------- #
# Exportación e importación de pagos (T5.17, T5.18)
# --------------------------------------------------------------------------- #


@router.get("/pagos/exportar")
async def exportar_pagos(
    request: Request,
    db: SesionBD,
    usuario: Annotated[Usuario, Depends(requiere_rol(*ROLES_GESTION))],
    desde: str = "",
    hasta: str = "",
) -> StreamingResponse:
    """Exporta los pagos a un archivo XLSX (T5.17)."""
    fecha_desde = _fecha(desde) if desde else None
    fecha_hasta = _fecha(hasta) if hasta else None
    datos = servicio_pagos.exportar_pagos_a_xlsx(
        db, desde=fecha_desde, hasta=fecha_hasta
    )
    nombre = "pagos_exportados.xlsx"
    return StreamingResponse(
        io.BytesIO(datos),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )


@router.get("/pagos/importar", response_class=HTMLResponse)
async def mostrar_importar_pagos(
    request: Request,
    db: SesionBD,
    usuario: Annotated[Usuario, Depends(requiere_rol(*ROLES_GESTION))],
) -> HTMLResponse:
    """Muestra el formulario para importar pagos masivamente (T5.18)."""
    return templates.TemplateResponse(
        request=request,
        name="pagos/importar.html",
        context={"csrf_token": ""},
    )


@router.post("/pagos/importar", response_class=HTMLResponse)
async def importar_pagos(
    request: Request,
    db: SesionBD,
    usuario: Annotated[Usuario, Depends(requiere_rol(*ROLES_GESTION))],
    archivo: UploadFile = File(...),  # noqa: B008
) -> HTMLResponse:
    """Importa pagos desde un archivo XLSX o CSV (T5.18)."""
    nombre_archivo = archivo.filename or ""
    contenido = await archivo.read()
    buffer = io.BytesIO(contenido)

    try:
        resultado = servicio_pagos.importar_pagos_desde_archivo(
            db,
            archivo=buffer,
            nombre_archivo=nombre_archivo,
            usuario=usuario,
        )
    except ValueError as exc:
        return templates.TemplateResponse(
            request=request,
            name="pagos/importar.html",
            context={
                "csrf_token": "",
                "mensajes": [{"tipo": "error", "texto": str(exc)}],
            },
        )

    partes = [
        f"Importación completada: {resultado.exitosos} pago(s) importado(s)."
    ]
    if resultado.fallidos:
        partes.append(f"{resultado.fallidos} pago(s) no se pudieron importar.")
    flash(request, "ok", " ".join(partes))

    return templates.TemplateResponse(
        request=request,
        name="pagos/importar.html",
        context={
            "resultado": resultado,
            "mensajes": [{"tipo": "ok", "texto": " ".join(partes)}],
        },
    )
