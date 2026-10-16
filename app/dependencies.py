"""Dependencias compartidas: sesión de base de datos y motor de plantillas."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import SessionLocal

settings = get_settings()

DIRECTORIO_PLANTILLAS = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(DIRECTORIO_PLANTILLAS))
templates.env.globals["app_name"] = settings.app_name


def get_db() -> Iterator[Session]:
    """Entrega una sesión de base de datos y la cierra al terminar la petición."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
