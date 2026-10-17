"""Manejo de errores con páginas propias.

Cubre la página de "acceso denegado" (T4.4). En la fase de calidad (T6.3) se
completa con los códigos 400 y 409 y mensajes uniformes.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

from app.dependencies import templates


def _render_error(
    request: Request, codigo: int, titulo: str, mensaje: str
) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="errores/error.html",
        context={"codigo": codigo, "titulo": titulo, "mensaje": mensaje},
        status_code=codigo,
    )


def registrar_manejadores(app: FastAPI) -> None:
    """Registra las páginas de error de la aplicación."""

    @app.exception_handler(403)
    async def acceso_denegado(request: Request, _exc: Exception) -> HTMLResponse:
        return _render_error(
            request,
            403,
            "Acceso denegado",
            "No tienes permisos para acceder a esta sección.",
        )

    @app.exception_handler(404)
    async def no_encontrado(request: Request, _exc: Exception) -> HTMLResponse:
        return _render_error(
            request,
            404,
            "Página no encontrada",
            "La página que buscas no existe o fue movida.",
        )

    @app.exception_handler(500)
    async def error_interno(request: Request, _exc: Exception) -> HTMLResponse:
        return _render_error(
            request,
            500,
            "Error interno",
            "Ocurrió un error inesperado. Inténtalo nuevamente.",
        )
