"""Vista restringida del miembro: su perfil, estado de cuenta e informe (UI-05).

El miembro solo puede ver su propia información (RN-06, CA-12). Incluye el
estado de cuenta con abono y el informe mensual en formato calendario (UI-06,
T5.15 y T5.33).
"""

from __future__ import annotations

from datetime import date
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
from app.services import reportes as servicio_reportes
from app.services.morosidad import calcular_morosidad

router = APIRouter(tags=["cuenta"])


def _contexto_miembro(db, usuario: Usuario, anio: int | None = None):
    """Arma el contexto del estado de cuenta del propio miembro (RN-06)."""
    miembro = repo_miembro.obtener_por_usuario(db, usuario.id)
    contexto = {
        "miembro": miembro,
        "cuotas": [],
        "avisos": [],
        "informacion": None,
        "saldo_a_favor": 0,
        "informe": None,
        "anio": anio or date.today().year,
    }
    if miembro is None:
        return contexto
    cuotas_mensuales = repo_membresia.cuotas_mensuales_de_miembro(db, miembro.id)
    contexto["cuotas"] = repo_membresia.cuotas_de_miembro(db, miembro.id)
    contexto["informacion"] = calcular_morosidad(
        miembro,
        cuotas_mensuales,
        deuda_excluida_clp=repo_membresia.deuda_negociada_clp(db, miembro.id),
    )
    contexto["avisos"] = repo_configuracion.avisos_de_miembro(db, miembro.id)
    contexto["saldo_a_favor"] = repo_pago.saldo_a_favor(db, miembro.id)
    contexto["informe"] = servicio_reportes.informe_calendario(
        db, miembro, contexto["anio"]
    )
    return contexto


@router.get("/mi/estado", response_class=HTMLResponse)
async def mi_estado(
    request: Request,
    db: SesionBD,
    usuario: Annotated[Usuario, Depends(requiere_rol(ROL_MIEMBRO))],
    anio: str = "",
) -> HTMLResponse:
    """Muestra el perfil, el estado de cuenta, el informe y los avisos propios."""
    try:
        anio_valor = int(anio) if anio else date.today().year
    except ValueError:
        anio_valor = date.today().year
    contexto = _contexto_miembro(db, usuario, anio_valor)
    return templates.TemplateResponse(
        request=request, name="cuenta/estado.html", context=contexto
    )
