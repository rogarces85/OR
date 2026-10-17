"""Rutas de inicio y cierre de sesión (UI-02, F-02, T4.3)."""

from __future__ import annotations

from fastapi import APIRouter, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse

from app.core.seguridad import (
    cerrar_sesion,
    flash,
    iniciar_sesion,
    obtener_usuario_actual,
    validar_csrf,
    verify_password,
)
from app.dependencies import SesionBD, templates
from app.models.usuario import ROLES_GESTION
from app.repositories import usuario as repo_usuario

router = APIRouter(tags=["autenticación"])


def destino_por_rol(rol: str) -> str:
    """Devuelve la vista inicial según el rol del usuario (UI-03, UI-05)."""
    return "/miembros" if rol in ROLES_GESTION else "/mi/estado"


def _login_con_error(
    request: Request, email: str, mensaje: str
) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="auth/login.html",
        context={
            "email": email,
            "mensajes": [{"tipo": "error", "texto": mensaje}],
        },
    )


@router.get("/ingresar", response_class=HTMLResponse, response_model=None)
async def mostrar_login(
    request: Request, db: SesionBD
) -> HTMLResponse | RedirectResponse:
    """Muestra el formulario de acceso (UI-02)."""
    usuario = obtener_usuario_actual(request, db)
    if usuario is not None:
        return RedirectResponse(
            destino_por_rol(usuario.rol), status_code=status.HTTP_303_SEE_OTHER
        )
    return templates.TemplateResponse(
        request=request, name="auth/login.html", context={"email": ""}
    )


@router.post("/ingresar", response_class=HTMLResponse, response_model=None)
async def procesar_login(
    request: Request,
    db: SesionBD,
    email: str = Form(""),
    password: str = Form(""),
    csrf_token: str = Form(""),
) -> HTMLResponse | RedirectResponse:
    """Valida las credenciales y abre la sesión (F-02, CA-21)."""
    if not validar_csrf(request, csrf_token):
        return _login_con_error(
            request, email, "Tu sesión expiró. Inténtalo nuevamente."
        )

    usuario = repo_usuario.obtener_por_email(db, email)
    if (
        usuario is None
        or not usuario.activo
        or not verify_password(password, usuario.password_hash)
    ):
        # Mensaje genérico: no revela si el correo existe (F-02).
        return _login_con_error(request, email, "Correo o contraseña incorrectos.")

    iniciar_sesion(request, usuario)
    return RedirectResponse(
        destino_por_rol(usuario.rol), status_code=status.HTTP_303_SEE_OTHER
    )


@router.post("/salir")
async def salir(
    request: Request, csrf_token: str = Form("")
) -> RedirectResponse:
    """Cierra la sesión del usuario y vuelve a la landing."""
    if validar_csrf(request, csrf_token):
        cerrar_sesion(request)
        flash(request, "ok", "Sesión cerrada correctamente.")
    return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
