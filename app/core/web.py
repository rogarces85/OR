"""Ayudas de interfaz reutilizables por los routers (POST-Redirect-GET y CSRF)."""

from __future__ import annotations

from fastapi import Request, status
from fastapi.responses import RedirectResponse

from app.core.seguridad import flash, validar_csrf


def redirigir(destino: str) -> RedirectResponse:
    """Redirección 303 típica después de un POST (patrón POST-Redirect-GET)."""
    return RedirectResponse(destino, status_code=status.HTTP_303_SEE_OTHER)


def csrf_ok(request: Request, token: str) -> bool:
    """Valida el token CSRF y deja un aviso en español si no es válido (T4.5)."""
    if validar_csrf(request, token):
        return True
    flash(request, "error", "Tu sesión expiró. Inténtalo nuevamente.")
    return False
