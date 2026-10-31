"""Panel de gestión de miembros: listado, alta, edición, categoría y exenciones.

Cubre T4.9 (shell del panel), T5.1 (alta), T5.2 (listado y búsqueda), T5.3
(edición), T5.4 (cambio de categoría), T5.5 (activación de la membresía) y
T5.10 (exención de cobros y avisos).
"""

from __future__ import annotations

from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.formato import formatear_clp
from app.core.seguridad import flash, requiere_rol, validar_csrf
from app.dependencies import SesionBD, templates
from app.models.miembro import (
    CATEGORIA_ACTIVO,
    CATEGORIA_MEMBRESIA,
    CATEGORIAS,
    MOTIVOS_EXENCION,
    Miembro,
)
from app.models.usuario import ROLES_GESTION, Usuario
from app.repositories import membresia as repo_membresia
from app.repositories import miembro as repo_miembro
from app.repositories import pago as repo_pago
from app.schemas.comunes import mensajes_por_campo
from app.schemas.miembro import ETIQUETAS_CAMPO, MiembroEntrada
from app.services import activacion as servicio_activacion
from app.services import membresias as servicio_membresias
from app.services.morosidad import calcular_morosidad, listar_miembros_con_morosidad

router = APIRouter(tags=["miembros"])

ETIQUETAS_SITUACION = {"pendiente": "Pendiente", "activo": "Activo"}
ETIQUETAS_CATEGORIA = {
    CATEGORIA_ACTIVO: "Activo (alumno)",
    CATEGORIA_MEMBRESIA: "Membresía (apoyo)",
}


def _redirigir(destino: str) -> RedirectResponse:
    """Redirección 303 típica después de un POST (patrón POST-Redirect-GET)."""
    return RedirectResponse(destino, status_code=status.HTTP_303_SEE_OTHER)


def _csrf_ok(request: Request, token: str) -> bool:
    """Valida el token CSRF y deja un aviso si no es válido (F-02, T4.5)."""
    if validar_csrf(request, token):
        return True
    flash(request, "error", "Tu sesión expiró. Inténtalo nuevamente.")
    return False


def _datos_ficha(
    *,
    nombre_completo: str,
    email: str,
    telefono: str,
    rut: str,
    fecha_nacimiento: str,
    fecha_incorporacion: str,
    direccion: str,
    contacto_emergencia: str,
    matriculado: bool = False,
) -> dict[str, Any]:
    """Arma el diccionario de la ficha ampliada recibido del formulario (D-6)."""
    return {
        "nombre_completo": nombre_completo,
        "email": email,
        "telefono": telefono,
        "rut": rut,
        "fecha_nacimiento": fecha_nacimiento,
        "fecha_incorporacion": fecha_incorporacion,
        "direccion": direccion,
        "contacto_emergencia": contacto_emergencia,
        "matriculado": matriculado,
    }


def _datos_desde_miembro(miembro: Miembro) -> dict[str, str]:
    """Convierte la ficha guardada al formato que espera el formulario."""
    return {
        "nombre_completo": miembro.nombre_completo,
        "email": miembro.email,
        "telefono": miembro.telefono or "",
        "rut": miembro.rut or "",
        "fecha_nacimiento": (
            miembro.fecha_nacimiento.isoformat() if miembro.fecha_nacimiento else ""
        ),
        "fecha_incorporacion": miembro.fecha_incorporacion.isoformat(),
        "direccion": miembro.direccion or "",
        "contacto_emergencia": miembro.contacto_emergencia or "",
    }


def _validar_ficha(
    datos: dict[str, Any],
) -> tuple[MiembroEntrada | None, dict[str, str]]:
    """Valida la ficha y devuelve la entrada junto con los errores por campo."""
    try:
        return MiembroEntrada(**datos), {}
    except ValidationError as exc:
        return None, mensajes_por_campo(exc)


def _resumen_errores(errores: dict[str, str]) -> str:
    """Une los errores por campo en un mensaje legible (CA-16)."""
    return " ".join(
        f"{ETIQUETAS_CAMPO.get(campo, campo)}: {texto}"
        for campo, texto in errores.items()
    )


def _obtener_miembro(db: Session, miembro_id: int) -> Miembro:
    """Devuelve el miembro o responde 404 si no existe."""
    miembro = repo_miembro.obtener(db, miembro_id)
    if miembro is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El miembro indicado no existe.",
        )
    return miembro


# --------------------------------------------------------------------------- #
# Listado (T5.2)
# --------------------------------------------------------------------------- #


@router.get("/miembros", response_class=HTMLResponse)
async def listar_miembros(
    request: Request,
    db: SesionBD,
    usuario: Annotated[Usuario, Depends(requiere_rol(*ROLES_GESTION))],
    q: str = "",
    categoria: str = "",
    situacion: str = "",
    color: str = "",
    incluir_bajas: str = "",
) -> HTMLResponse:
    """Lista los miembros con su color de morosidad y filtros combinables (T5.2)."""
    ver_bajas = incluir_bajas in {"1", "on", "true", "si"}
    filas = listar_miembros_con_morosidad(
        db,
        texto=q or None,
        categoria=categoria or None,
        situacion=situacion or None,
        color=color or None,
        incluir_bajas=ver_bajas,
    )
    return templates.TemplateResponse(
        request=request,
        name="miembros/lista.html",
        context={
            "filas": filas,
            "filtros": {
                "q": q,
                "categoria": categoria,
                "situacion": situacion,
                "color": color,
                "incluir_bajas": ver_bajas,
            },
            "categorias": CATEGORIAS,
            "situaciones": tuple(ETIQUETAS_SITUACION),
            "etiqueta_categoria_activa": CATEGORIA_ACTIVO,
            "total": len(filas),
        },
    )


# --------------------------------------------------------------------------- #
# Alta de miembro (T5.1)
# --------------------------------------------------------------------------- #


@router.get("/miembros/nuevo", response_class=HTMLResponse)
async def mostrar_alta(
    request: Request,
    db: SesionBD,
    usuario: Annotated[Usuario, Depends(requiere_rol(*ROLES_GESTION))],
) -> HTMLResponse:
    """Muestra el formulario de alta con la ficha ampliada del miembro (T5.1)."""
    return templates.TemplateResponse(
        request=request,
        name="miembros/formulario.html",
        context={
            "accion": "/miembros/nuevo",
            "titulo": "Nuevo miembro",
            "datos": {"fecha_incorporacion": date.today().isoformat()},
            "errores": {},
            "categorias": CATEGORIAS,
            "categoria": CATEGORIA_ACTIVO,
            "edicion": False,
            "matriculado": False,
            "cancelar_url": "/miembros",
        },
    )


@router.post("/miembros/nuevo", response_class=HTMLResponse, response_model=None)
async def crear_miembro(
    request: Request,
    db: SesionBD,
    usuario: Annotated[Usuario, Depends(requiere_rol(*ROLES_GESTION))],
    csrf_token: str = Form(""),
    nombre_completo: str = Form(""),
    email: str = Form(""),
    telefono: str = Form(""),
    rut: str = Form(""),
    fecha_nacimiento: str = Form(""),
    fecha_incorporacion: str = Form(""),
    direccion: str = Form(""),
    contacto_emergencia: str = Form(""),
    categoria: str = Form(CATEGORIA_ACTIVO),
    matriculado: bool = Form(False),
) -> HTMLResponse | RedirectResponse:
    """Registra un miembro nuevo y su obligación inicial (F-01, Flujo 1, CA-16)."""
    datos = _datos_ficha(
        nombre_completo=nombre_completo,
        email=email,
        telefono=telefono,
        rut=rut,
        fecha_nacimiento=fecha_nacimiento,
        fecha_incorporacion=fecha_incorporacion or date.today().isoformat(),
        direccion=direccion,
        contacto_emergencia=contacto_emergencia,
        matriculado=matriculado,
    )
    if not _csrf_ok(request, csrf_token):
        return _redirigir("/miembros/nuevo")

    entrada, errores = _validar_ficha(datos)
    if categoria not in CATEGORIAS:
        errores["categoria"] = "Selecciona una categoría válida."
    if entrada is not None and repo_miembro.obtener_por_email(
        db, str(entrada.email)
    ) is not None:
        # El correo es el identificador único del miembro (RN-11, CA-16).
        errores["email"] = "Ya existe un miembro registrado con este correo electrónico."

    if entrada is None or errores:
        return templates.TemplateResponse(
            request=request,
            name="miembros/formulario.html",
            context={
                "accion": "/miembros/nuevo",
                "titulo": "Nuevo miembro",
                "datos": datos,
                "errores": errores,
                "categorias": CATEGORIAS,
                "categoria": categoria,
                "edicion": False,
                "matriculado": matriculado,
                "cancelar_url": "/miembros",
                "mensajes": [
                    {
                        "tipo": "error",
                        "texto": "No se pudo registrar el miembro. "
                        + _resumen_errores(errores),
                    }
                ],
            },
        )

    miembro = servicio_membresias.crear_miembro(
        db,
        nombre_completo=entrada.nombre_completo,
        email=str(entrada.email),
        telefono=entrada.telefono,
        rut=entrada.rut,
        fecha_nacimiento=entrada.fecha_nacimiento,
        fecha_incorporacion=entrada.fecha_incorporacion,
        matriculado=entrada.matriculado,
        direccion=entrada.direccion,
        contacto_emergencia=entrada.contacto_emergencia,
        categoria=categoria,
        usuario_id=usuario.id,
    )
    if entrada.matriculado:
        mensaje = (
            f"Miembro {miembro.nombre_completo} registrado y marcado como matriculado. "
            "No se generará cobro de matrícula."
        )
    else:
        mensaje = (
            f"Miembro {miembro.nombre_completo} registrado. Queda pendiente hasta "
            "completar el pago inicial (Matrícula + la cuota de su categoría)."
        )
    flash(request, "ok", mensaje)
    return _redirigir(f"/miembros/{miembro.id}")


# --------------------------------------------------------------------------- #
# Ficha, activación, categoría y exención (T5.3, T5.4, T5.5, T5.10)
# --------------------------------------------------------------------------- #


@router.get("/miembros/{miembro_id}", response_class=HTMLResponse)
async def ver_miembro(
    request: Request,
    db: SesionBD,
    usuario: Annotated[Usuario, Depends(requiere_rol(*ROLES_GESTION))],
    miembro_id: int,
) -> HTMLResponse:
    """Muestra la ficha, la activación, la categoría y las cuotas del miembro."""
    miembro = _obtener_miembro(db, miembro_id)
    cuotas = repo_membresia.cuotas_de_miembro(db, miembro.id)
    cuotas_mensuales = repo_membresia.cuotas_mensuales_de_miembro(db, miembro.id)
    return templates.TemplateResponse(
        request=request,
        name="miembros/detalle.html",
        context={
            "miembro": miembro,
            "cuotas": cuotas,
            "informacion": calcular_morosidad(miembro, cuotas_mensuales),
            "estado_activacion": servicio_activacion.evaluar_activacion(db, miembro),
            "historial": repo_miembro.listar_historial(db, miembro.id),
            "saldo_a_favor": repo_pago.saldo_a_favor(db, miembro.id),
            "motivos_exencion": MOTIVOS_EXENCION,
            "categorias": CATEGORIAS,
            "etiquetas_categoria": ETIQUETAS_CATEGORIA,
            "hoy": date.today().isoformat(),
        },
    )


@router.get("/miembros/{miembro_id}/editar", response_class=HTMLResponse)
async def mostrar_edicion(
    request: Request,
    db: SesionBD,
    usuario: Annotated[Usuario, Depends(requiere_rol(*ROLES_GESTION))],
    miembro_id: int,
) -> HTMLResponse:
    """Muestra el formulario de edición de la ficha del miembro (T5.3)."""
    miembro = _obtener_miembro(db, miembro_id)
    return templates.TemplateResponse(
        request=request,
        name="miembros/formulario.html",
        context={
            "accion": f"/miembros/{miembro.id}/editar",
            "titulo": "Editar miembro",
            "datos": _datos_desde_miembro(miembro),
            "errores": {},
            "categorias": CATEGORIAS,
            "categoria": miembro.categoria,
            "edicion": True,
            "matriculado": miembro.matriculado,
            "cancelar_url": f"/miembros/{miembro.id}",
            "miembro": miembro,
        },
    )


@router.post("/miembros/{miembro_id}/editar", response_model=None)
async def editar_miembro(
    request: Request,
    db: SesionBD,
    usuario: Annotated[Usuario, Depends(requiere_rol(*ROLES_GESTION))],
    miembro_id: int,
    csrf_token: str = Form(""),
    nombre_completo: str = Form(""),
    email: str = Form(""),
    telefono: str = Form(""),
    rut: str = Form(""),
    fecha_nacimiento: str = Form(""),
    fecha_incorporacion: str = Form(""),
    direccion: str = Form(""),
    contacto_emergencia: str = Form(""),
    matriculado: bool = Form(False),
    categoria: str = Form(CATEGORIA_ACTIVO),
    modal: str = Form(""),
) -> HTMLResponse | RedirectResponse | JSONResponse:
    """Modifica la ficha del miembro sin alterar su historial (T5.3).

    Acepta la categoría para editar todos los datos desde el modal.
    Cuando ``modal == "1"`` devuelve JSON para mostrar errores dentro del
    modal sin salir de la página.
    """
    miembro = _obtener_miembro(db, miembro_id)
    if categoria not in CATEGORIAS:
        categoria = miembro.categoria
    datos = _datos_ficha(
        nombre_completo=nombre_completo,
        email=email,
        telefono=telefono,
        rut=rut,
        fecha_nacimiento=fecha_nacimiento,
        fecha_incorporacion=(
            fecha_incorporacion or miembro.fecha_incorporacion.isoformat()
        ),
        direccion=direccion,
        contacto_emergencia=contacto_emergencia,
        matriculado=matriculado,
    )
    if not _csrf_ok(request, csrf_token):
        if modal == "1":
            return JSONResponse(
                {"errores": {"csrf": "Sesión expirada. Inténtalo nuevamente."}},
                status_code=422,
            )
        return _redirigir(f"/miembros/{miembro.id}")

    entrada, errores = _validar_ficha(datos)
    if entrada is not None:
        existente = repo_miembro.obtener_por_email(db, str(entrada.email))
        if existente is not None and existente.id != miembro.id:
            errores["email"] = (
                "Ya existe otro miembro registrado con este correo electrónico."
            )
    if entrada is None or errores:
        if modal == "1":
            return JSONResponse({"errores": errores}, status_code=422)
        return templates.TemplateResponse(
            request=request,
            name="miembros/formulario.html",
            context={
                "accion": f"/miembros/{miembro.id}/editar",
                "titulo": "Editar miembro",
                "datos": datos,
                "errores": errores,
                "categorias": CATEGORIAS,
                "categoria": categoria,
                "edicion": True,
                "matriculado": matriculado,
                "cancelar_url": f"/miembros/{miembro.id}",
                "miembro": miembro,
                "mensajes": [
                    {
                        "tipo": "error",
                        "texto": "No se guardaron los cambios. "
                        + _resumen_errores(errores),
                    }
                ],
            },
        )

    servicio_membresias.editar_miembro(
        db,
        miembro,
        nombre_completo=entrada.nombre_completo,
        email=str(entrada.email),
        telefono=entrada.telefono,
        rut=entrada.rut,
        fecha_nacimiento=entrada.fecha_nacimiento,
        fecha_incorporacion=entrada.fecha_incorporacion,
        matriculado=entrada.matriculado,
        direccion=entrada.direccion,
        contacto_emergencia=entrada.contacto_emergencia,
    )
    if categoria != miembro.categoria:
        servicio_membresias.cambiar_categoria(db, miembro, categoria, usuario)
    if modal == "1":
        return JSONResponse({"ok": True})
    flash(request, "ok", "Datos del miembro actualizados.")
    return _redirigir(f"/miembros/{miembro.id}")


@router.post("/miembros/{miembro_id}/categoria", response_model=None)
async def cambiar_categoria_miembro(
    request: Request,
    db: SesionBD,
    usuario: Annotated[Usuario, Depends(requiere_rol(*ROLES_GESTION))],
    miembro_id: int,
    csrf_token: str = Form(""),
    categoria: str = Form(""),
) -> RedirectResponse:
    """Cambia la categoría del miembro, registra el cambio y ajusta la cuota (T5.4)."""
    miembro = _obtener_miembro(db, miembro_id)
    if not _csrf_ok(request, csrf_token):
        return _redirigir(f"/miembros/{miembro.id}")
    try:
        registro = servicio_membresias.cambiar_categoria(db, miembro, categoria, usuario)
    except ValueError as exc:
        flash(request, "error", str(exc))
    else:
        etiqueta = ETIQUETAS_CATEGORIA.get(registro.categoria_nueva, categoria)
        flash(
            request,
            "ok",
            f"Categoría actualizada a {etiqueta}; la cuota mensual quedó ajustada.",
        )
    return _redirigir(f"/miembros/{miembro.id}")


@router.post("/miembros/{miembro_id}/activar", response_model=None)
async def activar_miembro(
    request: Request,
    db: SesionBD,
    usuario: Annotated[Usuario, Depends(requiere_rol(*ROLES_GESTION))],
    miembro_id: int,
    csrf_token: str = Form(""),
) -> RedirectResponse:
    """Evalúa el pago inicial y activa al miembro si está completo (T5.5, CA-01)."""
    miembro = _obtener_miembro(db, miembro_id)
    if not _csrf_ok(request, csrf_token):
        return _redirigir(f"/miembros/{miembro.id}")
    estado = servicio_activacion.evaluar_activacion(db, miembro)
    if estado.completo:
        servicio_activacion.aplicar_activacion(db, miembro)
        flash(
            request,
            "ok",
            "El pago inicial está completo: la membresía quedó activa.",
        )
    else:
        flash(
            request,
            "error",
            "El pago inicial está incompleto: falta "
            f"$ {formatear_clp(estado.saldo_clp)}. El miembro sigue pendiente.",
        )
    return _redirigir(f"/miembros/{miembro.id}")


@router.post("/miembros/{miembro_id}/exencion", response_model=None)
async def marcar_exencion_miembro(
    request: Request,
    db: SesionBD,
    usuario: Annotated[Usuario, Depends(requiere_rol(*ROLES_GESTION))],
    miembro_id: int,
    csrf_token: str = Form(""),
    motivo: str = Form(""),
) -> RedirectResponse:
    """Exime al miembro de cobros y avisos, dejando su cuota como exenta (T5.10)."""
    miembro = _obtener_miembro(db, miembro_id)
    if not _csrf_ok(request, csrf_token):
        return _redirigir(f"/miembros/{miembro.id}")
    try:
        servicio_membresias.marcar_exencion(db, miembro, motivo)
    except ValueError as exc:
        flash(request, "error", str(exc))
    else:
        flash(
            request,
            "ok",
            f"Miembro exento por {motivo}: no se generarán cobros ni avisos (RN-05).",
        )
    return _redirigir(f"/miembros/{miembro.id}")


@router.post("/miembros/{miembro_id}/exencion/quitar", response_model=None)
async def quitar_exencion_miembro(
    request: Request,
    db: SesionBD,
    usuario: Annotated[Usuario, Depends(requiere_rol(*ROLES_GESTION))],
    miembro_id: int,
    csrf_token: str = Form(""),
) -> RedirectResponse:
    """Devuelve al miembro a la condición normal, reincorporándolo al ciclo (T5.10)."""
    miembro = _obtener_miembro(db, miembro_id)
    if not _csrf_ok(request, csrf_token):
        return _redirigir(f"/miembros/{miembro.id}")
    servicio_membresias.quitar_exencion(db, miembro)
    flash(request, "ok", "Exención retirada: el miembro vuelve al ciclo de cobro.")
    return _redirigir(f"/miembros/{miembro.id}")


# --------------------------------------------------------------------------- #
# Baja y reactivación (soft-delete)
# --------------------------------------------------------------------------- #


@router.post("/miembros/{miembro_id}/baja", response_model=None)
async def dar_de_baja_miembro(
    request: Request,
    db: SesionBD,
    usuario: Annotated[Usuario, Depends(requiere_rol(*ROLES_GESTION))],
    miembro_id: int,
    csrf_token: str = Form(""),
    fecha_baja: str = Form(""),
    motivo_baja: str = Form(""),
) -> RedirectResponse:
    """Da de baja al miembro sin borrar la ficha ni su historial (soft-delete)."""
    miembro = _obtener_miembro(db, miembro_id)
    if not _csrf_ok(request, csrf_token):
        return _redirigir(f"/miembros/{miembro.id}")
    fecha = date.fromisoformat(fecha_baja) if fecha_baja else None
    try:
        servicio_membresias.dar_de_baja(
            db, miembro, fecha=fecha, motivo=motivo_baja
        )
    except ValueError as exc:
        flash(request, "error", str(exc))
    else:
        flash(
            request,
            "ok",
            "Miembro dado de baja: deja de aparecer en el panel y no se le "
            "generarán nuevas cuotas.",
        )
    return _redirigir(f"/miembros/{miembro.id}")


@router.post("/miembros/{miembro_id}/reactivar", response_model=None)
async def reactivar_miembro(
    request: Request,
    db: SesionBD,
    usuario: Annotated[Usuario, Depends(requiere_rol(*ROLES_GESTION))],
    miembro_id: int,
    csrf_token: str = Form(""),
) -> RedirectResponse:
    """Reincorpora al miembro dado de baja al panel y al ciclo de cobro."""
    miembro = _obtener_miembro(db, miembro_id)
    if not _csrf_ok(request, csrf_token):
        return _redirigir(f"/miembros/{miembro.id}")
    try:
        servicio_membresias.reactivar_miembro(db, miembro)
    except ValueError as exc:
        flash(request, "error", str(exc))
    else:
        flash(request, "ok", "Miembro reactivado: vuelve al panel y al ciclo de cobro.")
    return _redirigir(f"/miembros/{miembro.id}")
