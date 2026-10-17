"""Comunicación: aviso de morosidad y plantilla de correo (F-23, RN-13, D-21).

El sistema **no** envía correo automático: arma el texto con los datos del
alumno, el detalle de la morosidad, lo adeudado y los datos de la cuenta, y
ofrece un enlace ``mailto:`` para que el Tesorero lo envíe (P-2, T5.20, T7.4).
"""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from sqlalchemy.orm import Session

from app.core.formato import formatear_clp
from app.models.configuracion import (
    ESTADO_AVISO_ENVIADO,
    AvisoMorosidad,
    CuentaBancaria,
    PlantillaCorreo,
)
from app.models.miembro import Miembro
from app.repositories import configuracion as repo_configuracion
from app.services.morosidad import MorosidadInfo

ASUNTO_POR_DEFECTO = "Recordatorio de cuota pendiente · Osorno Runners"


def detalle_morosidad(info: MorosidadInfo) -> str:
    """Describe en una línea la morosidad del miembro."""
    if info.meses_deuda <= 0:
        return "Sin deuda de cuotas mensuales."
    return (
        f"{info.meses_deuda} mes(es) impago(s) por un total de "
        f"$ {formatear_clp(info.monto_deuda_clp)}."
    )


def datos_de_plantilla(
    miembro: Miembro,
    info: MorosidadInfo,
    cuenta: CuentaBancaria | None,
) -> dict[str, str]:
    """Datos que rellenan los marcadores de la plantilla de correo (D-21)."""
    return {
        "nombre": miembro.nombre_completo,
        "meses": str(info.meses_deuda),
        "adeudado": f"$ {formatear_clp(info.monto_deuda_clp)}",
        "detalle": detalle_morosidad(info),
        "titular": cuenta.titular if cuenta else "",
        "banco": cuenta.banco if cuenta else "",
        "cuenta": cuenta.numero_cuenta if cuenta else "",
        "rut": cuenta.rut if cuenta else "",
        "correo": cuenta.correo if cuenta else "",
    }


def _formatear(texto: str, datos: dict[str, str]) -> str:
    """Rellena los marcadores de la plantilla, tolerando marcadores faltantes."""
    try:
        return texto.format(**datos)
    except (KeyError, IndexError, ValueError):
        return texto


def cuerpo_por_defecto(datos: dict[str, str]) -> str:
    """Cuerpo de correo de respaldo si no hay plantilla configurada."""
    return (
        f"Hola {datos['nombre']}:\n\n"
        f"Te escribimos porque mantienes una deuda pendiente de {datos['meses']} "
        f"mes(es) con el club, por un total de {datos['adeudado']}.\n\n"
        f"Detalle: {datos['detalle']}\n\n"
        "Puedes regularizar tu situación con una transferencia a:\n"
        f"Titular: {datos['titular']}\nBanco: {datos['banco']}\n"
        f"Cuenta corriente: {datos['cuenta']}\nRUT: {datos['rut']}\n"
        f"Correo: {datos['correo']}\n\n"
        "Gracias por ser parte de Osorno Runners."
    )


def renderizar_plantilla(
    plantilla: PlantillaCorreo | None,
    miembro: Miembro,
    info: MorosidadInfo,
    cuenta: CuentaBancaria | None,
) -> tuple[str, str]:
    """Devuelve (asunto, cuerpo) del correo de morosidad ya rellenados (T5.20)."""
    datos = datos_de_plantilla(miembro, info, cuenta)
    if plantilla is None:
        return ASUNTO_POR_DEFECTO, cuerpo_por_defecto(datos)
    asunto = _formatear(plantilla.asunto, datos) if plantilla.asunto else ASUNTO_POR_DEFECTO
    cuerpo = (
        _formatear(plantilla.cuerpo, datos)
        if plantilla.cuerpo
        else cuerpo_por_defecto(datos)
    )
    return asunto, cuerpo


def generar_enlace_correo(destinatario: str, asunto: str, cuerpo: str) -> str:
    """Compone el enlace ``mailto:`` que abre el cliente de correo del Tesorero."""
    return (
        f"mailto:{quote(destinatario or '')}"
        f"?subject={quote(asunto or '')}&body={quote(cuerpo or '')}"
    )


def marcar_aviso_enviado(
    db: Session, aviso: AvisoMorosidad, usuario: Any | None = None
) -> AvisoMorosidad:
    """Marca un aviso como enviado por el Tesorero (declarativo; P-2)."""
    from datetime import datetime

    aviso.estado = ESTADO_AVISO_ENVIADO
    aviso.enviado_por = getattr(usuario, "id", None)
    aviso.enviado_en = datetime.now()
    return repo_configuracion.guardar_aviso(db, aviso)
