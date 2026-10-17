"""Vista restringida del miembro: su perfil y su estado de cuenta (T4.10, UI-05).

El miembro solo puede ver su propia información (RN-06, CA-12).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from app.core.seguridad import requiere_rol
from app.dependencies import SesionBD, templates
from app.models.usuario import ROL_MIEMBRO, Usuario
from app.repositories import configuracion as repo_configuracion
from app.repositories import membresia as repo_membresia
from app.repositories import miembro as repo_miembro
from app.repositories import pago as repo_pago
from app.services.morosidad import calcular_morosidad

router = APIRouter(tags=["cuenta"])


@router.get("/mi/estado", response_class=HTMLResponse)
async def mi_estado(
    request: Request,
    db: SesionBD,
    usuario: Annotated[Usuario, Depends(requiere_rol(ROL_MIEMBRO))],
) -> HTMLResponse:
    """Muestra el perfil, el estado de cuenta y la morosidad del propio miembro."""
    miembro = repo_miembro.obtener_por_usuario(db, usuario.id)
    informacion = None
    cuotas: list = []
    avisos: list = []
    saldo_a_favor = 0
    if miembro is not None:
        cuotas = repo_membresia.cuotas_de_miembro(db, miembro.id)
        informacion = calcular_morosidad(miembro, cuotas)
        avisos = repo_configuracion.avisos_de_miembro(db, miembro.id)
        saldo_a_favor = repo_pago.saldo_a_favor(db, miembro.id)

    return templates.TemplateResponse(
        request=request,
        name="cuenta/estado.html",
        context={
            "miembro": miembro,
            "cuotas": cuotas,
            "avisos": avisos,
            "informacion": informacion,
            "saldo_a_favor": saldo_a_favor,
        },
    )
