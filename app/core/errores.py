"""Manejo de errores con páginas propias.

Versión base (H1). En la Fase de calidad (T6.3) se amplía con los códigos
400, 403, 404 y 409 y mensajes uniformes.
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
    """Registra las páginas de error base de la aplicación."""

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
