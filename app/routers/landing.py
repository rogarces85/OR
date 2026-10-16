"""Rutas públicas de la landing page (UI-01)."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.dependencies import templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def portada(request: Request) -> HTMLResponse:
    """Landing page pública del club (F-28, UI-01)."""
    return templates.TemplateResponse(request=request, name="landing/index.html")
