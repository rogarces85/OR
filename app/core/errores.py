"""Manejo centralizado de errores con páginas propias (T6.3, CA-13, CA-21).

Las respuestas 400, 403, 404, 409, 422 y 500 muestran una página coherente con
la identidad del sitio y un mensaje en español (RN-16). Los errores de
validación de FastAPI se traducen a 400 para no exponer mensajes en inglés.
"""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse

from app.dependencies import templates

# Título y mensaje por defecto de cada código de estado.
PAGINAS_ERROR: dict[int, tuple[str, str]] = {
    status.HTTP_400_BAD_REQUEST: (
        "Solicitud no válida",
        (
            "Los datos enviados no son válidos. Revisa el formulario e "
            "inténtalo nuevamente."
        ),
    ),
    status.HTTP_403_FORBIDDEN: (
        "Acceso denegado",
        "No tienes permisos para acceder a esta sección.",
    ),
    status.HTTP_404_NOT_FOUND: (
        "Página no encontrada",
        "La página que buscas no existe o fue movida.",
    ),
    status.HTTP_409_CONFLICT: (
        "Conflicto",
        (
            "La operación no se puede completar porque el registro ya existe "
            "o entra en conflicto con otro."
        ),
    ),
    422: (
        "Datos no válidos",
        (
            "Los datos enviados no son válidos. Revisa el formulario e "
            "inténtalo nuevamente."
        ),
    ),
    status.HTTP_500_INTERNAL_SERVER_ERROR: (
        "Error interno",
        "Ocurrió un error inesperado. Inténtalo nuevamente.",
    ),
}

# Detalles por defecto de Starlette/FastAPI que no deben mostrarse (están en inglés).
_DETALLES_GENERICOS = {
    "Bad Request",
    "Unauthorized",
    "Forbidden",
    "Not Found",
    "Method Not Allowed",
    "Conflict",
    "Unprocessable Entity",
    "Internal Server Error",
}


def _render_error(
    request: Request, codigo: int, titulo: str, mensaje: str
) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="errores/error.html",
        context={"codigo": codigo, "titulo": titulo, "mensaje": mensaje},
        status_code=codigo,
    )


def _respuesta(request: Request, codigo: int, detalle: object = None) -> HTMLResponse:
    """Compone la página de error, priorizando un detalle propio en español."""
    titulo, mensaje = PAGINAS_ERROR.get(
        codigo, ("Error", "Ocurrió un error al procesar la solicitud.")
    )
    if isinstance(detalle, str):
        limpio = detalle.strip()
        if limpio and limpio not in _DETALLES_GENERICOS:
            mensaje = limpio
    return _render_error(request, codigo, titulo, mensaje)


async def _manejador_http(request: Request, exc: Exception) -> HTMLResponse:
    """Responde a las ``HTTPException`` con la página del código recibido."""
    codigo = int(getattr(exc, "status_code", status.HTTP_500_INTERNAL_SERVER_ERROR))
    return _respuesta(request, codigo, getattr(exc, "detail", None))


async def _manejador_validacion(
    request: Request, _exc: RequestValidationError
) -> HTMLResponse:
    """Traduce los errores de validación de FastAPI a un 400 en español."""
    return _respuesta(request, status.HTTP_400_BAD_REQUEST)


async def _manejador_inesperado(
    request: Request, _exc: Exception
) -> HTMLResponse:
    """Responde a los errores no controlados con la página 500."""
    return _respuesta(request, status.HTTP_500_INTERNAL_SERVER_ERROR)


def registrar_manejadores(app: FastAPI) -> None:
    """Registra las páginas de error de la aplicación."""
    for codigo in PAGINAS_ERROR:
        app.add_exception_handler(codigo, _manejador_http)
    app.add_exception_handler(RequestValidationError, _manejador_validacion)
    app.add_exception_handler(Exception, _manejador_inesperado)
