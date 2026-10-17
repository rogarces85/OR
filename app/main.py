"""Punto de entrada de la aplicación FastAPI."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.config import get_settings
from app.core.errores import registrar_manejadores
from app.routers import auth, cuenta, landing, miembros

settings = get_settings()

DIRECTORIO_ESTATICOS = Path(__file__).resolve().parent / "static"

app = FastAPI(title=settings.app_name)

# Sesión firmada en cookie HttpOnly + SameSite=Lax (Q-2).
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    session_cookie=settings.session_cookie,
    max_age=settings.session_max_age,
    same_site="lax",
    https_only=False,
)

app.mount(
    "/static",
    StaticFiles(directory=str(DIRECTORIO_ESTATICOS)),
    name="static",
)

registrar_manejadores(app)
app.include_router(landing.router)
app.include_router(auth.router)
app.include_router(miembros.router)
app.include_router(cuenta.router)


@app.get("/salud")
async def salud() -> dict[str, str]:
    """Ruta de salud: confirma que la aplicación está en pie."""
    return {
        "estado": "ok",
        "app": settings.app_name,
        "entorno": settings.entorno,
    }
