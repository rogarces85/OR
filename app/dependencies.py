"""Dependencias compartidas: sesión de base de datos y motor de plantillas."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.formato import formatear_clp
from app.core.periodos import MESES_NOMBRES
from app.database import SessionLocal

settings = get_settings()

DIRECTORIO_PLANTILLAS = Path(__file__).resolve().parent / "templates"


def _contexto_base(request: Request) -> dict[str, Any]:
    """Inyecta en todas las plantillas la sesión, el token CSRF y los mensajes."""
    # Import diferido: evita un ciclo entre ``dependencies`` y ``core.seguridad``.
    from app.core.seguridad import datos_sesion, token_csrf

    sesion = getattr(request, "session", None)
    flash = sesion.pop("flash", None) if sesion is not None else None
    return {
        "sesion": datos_sesion(request),
        "csrf_token": token_csrf(request),
        "flash": flash,
    }


templates = Jinja2Templates(
    directory=str(DIRECTORIO_PLANTILLAS),
    context_processors=[_contexto_base],
)
templates.env.globals["app_name"] = settings.app_name
templates.env.globals["meses_nombres"] = MESES_NOMBRES
templates.env.filters["clp"] = formatear_clp


def get_db() -> Iterator[Session]:
    """Entrega una sesión de base de datos y la cierra al terminar la petición."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Alias de dependencia reutilizable en las rutas (evita B008 de ruff).
SesionBD = Annotated[Session, Depends(get_db)]
