"""Punto de entrada de la aplicación FastAPI."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.core.errores import registrar_manejadores
from app.dependencies import templates

settings = get_settings()

DIRECTORIO_ESTATICOS = Path(__file__).resolve().parent / "static"

app = FastAPI(title=settings.app_name)

app.mount(
    "/static",
    StaticFiles(directory=str(DIRECTORIO_ESTATICOS)),
    name="static",
)

registrar_manejadores(app)


@app.get("/", response_class=HTMLResponse)
async def inicio(request: Request) -> HTMLResponse:
    """Página de inicio provisional (la landing oficial llega en H2)."""
    return templates.TemplateResponse(
        request=request,
        name="inicio.html",
    )


@app.get("/salud")
async def salud() -> dict[str, str]:
    """Ruta de salud: confirma que la aplicación está en pie."""
    return {
        "estado": "ok",
        "app": settings.app_name,
        "entorno": settings.entorno,
    }
