"""Panel de gestión: listado y búsqueda de miembros con morosidad.

Cubre T4.9 (shell del panel) y T5.2 (listado y búsqueda).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from app.core.seguridad import requiere_rol
from app.dependencies import SesionBD, templates
from app.models.miembro import CATEGORIA_ACTIVO, CATEGORIAS
from app.models.usuario import ROLES_GESTION, Usuario
from app.services.morosidad import listar_miembros_con_morosidad

router = APIRouter(tags=["miembros"])

ETIQUETAS_SITUACION = {"pendiente": "Pendiente", "activo": "Activo"}


@router.get("/miembros", response_class=HTMLResponse)
async def listar_miembros(
    request: Request,
    db: SesionBD,
    usuario: Annotated[Usuario, Depends(requiere_rol(*ROLES_GESTION))],
    q: str = "",
    categoria: str = "",
    situacion: str = "",
    color: str = "",
) -> HTMLResponse:
    """Lista los miembros con su color de morosidad y filtros combinables (T5.2)."""
    filas = listar_miembros_con_morosidad(
        db,
        texto=q or None,
        categoria=categoria or None,
        situacion=situacion or None,
        color=color or None,
    )
    return templates.TemplateResponse(
        request=request,
        name="miembros/lista.html",
        context={
            "filas": filas,
            "filtros": {
                "q": q,
                "categoria": categoria,
                "situacion": situacion,
                "color": color,
            },
            "categorias": CATEGORIAS,
            "situaciones": tuple(ETIQUETAS_SITUACION),
            "etiqueta_categoria_activa": CATEGORIA_ACTIVO,
            "total": len(filas),
        },
    )
