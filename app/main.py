"""Punto de entrada de la aplicación FastAPI."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Response, status
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.sessions import SessionMiddleware

from app.config import get_settings
from app.core.errores import registrar_manejadores
from app.dependencies import SesionBD
from app.routers import (
    auth,
    compras,
    cuenta,
    finanzas,
    landing,
    membresias,
    miembros,
    morosidad,
    negociaciones,
    pagos,
    reportes,
)

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
app.include_router(membresias.router)
app.include_router(pagos.router)
app.include_router(morosidad.router)
app.include_router(negociaciones.router)
app.include_router(finanzas.router)
app.include_router(compras.router)
app.include_router(reportes.router)
app.include_router(cuenta.router)


@app.get("/salud")
async def salud(db: SesionBD, response: Response) -> dict[str, str]:
    """Ruta de salud: confirma la app y la conexión a MySQL/MariaDB (T7.1).

    Si la base de datos no responde, se reporta el estado degradado con un
    503 para que un monitor externo pueda detectarlo.
    """
    try:
        db.execute(text("SELECT 1"))
        base_de_datos = "ok"
    except SQLAlchemyError:
        base_de_datos = "error"
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {
        "estado": "ok" if base_de_datos == "ok" else "degradado",
        "app": settings.app_name,
        "entorno": settings.entorno,
        "base_de_datos": base_de_datos,
    }
