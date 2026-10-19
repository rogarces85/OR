"""Consultas y persistencia de configuración y comunicación (T3.8)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import cache
from app.models.configuracion import (
    ESTADO_AVISO_PENDIENTE,
    AvisoMorosidad,
    CuentaBancaria,
    PlantillaCorreo,
)


def obtener_cuenta(db: Session) -> CuentaBancaria | None:
    """Devuelve la cuenta bancaria configurada para transferencias (D-22).

    Se cachea porque se muestra en la landing, los avisos y las instrucciones
    de pago (T9.4).
    """
    return cache.obtener(
        db,
        "cuenta_bancaria",
        lambda: db.scalar(select(CuentaBancaria).order_by(CuentaBancaria.id)),
    )


def obtener_plantilla(db: Session, nombre: str | None = None) -> PlantillaCorreo | None:
    """Devuelve la plantilla de correo activa (o la de nombre indicado)."""
    consulta = select(PlantillaCorreo)
    if nombre:
        consulta = consulta.where(PlantillaCorreo.nombre == nombre)
    else:
        consulta = consulta.where(PlantillaCorreo.activa.is_(True))
    return db.scalar(consulta.order_by(PlantillaCorreo.id))


def crear_cuenta(
    db: Session,
    *,
    titular: str,
    banco: str,
    numero_cuenta: str,
    rut: str,
    correo: str,
) -> CuentaBancaria:
    """Registra los datos de la cuenta bancaria del club."""
    cuenta = CuentaBancaria(
        titular=titular.strip(),
        banco=banco.strip(),
        numero_cuenta=numero_cuenta.strip(),
        rut=rut.strip(),
        correo=correo.strip(),
    )
    db.add(cuenta)
    cache.invalidar(db, "cuenta_bancaria")
    return cuenta


def crear_plantilla(
    db: Session, *, nombre: str, asunto: str, cuerpo: str
) -> PlantillaCorreo:
    """Registra una plantilla de correo de morosidad."""
    plantilla = PlantillaCorreo(
        nombre=nombre.strip(), asunto=asunto.strip(), cuerpo=cuerpo
    )
    db.add(plantilla)
    return plantilla


def avisos_de_miembro(db: Session, miembro_id: int) -> list[AvisoMorosidad]:
    """Lista los avisos de morosidad de un miembro, del más reciente al más antiguo."""
    return list(
        db.scalars(
            select(AvisoMorosidad)
            .where(AvisoMorosidad.miembro_id == miembro_id)
            .order_by(AvisoMorosidad.generado_en.desc(), AvisoMorosidad.id.desc())
        )
    )


def crear_aviso(
    db: Session,
    *,
    miembro_id: int,
    detalle: str | None = None,
    plantilla_id: int | None = None,
) -> AvisoMorosidad:
    """Genera una alerta de morosidad para el Tesorero (F-23)."""
    aviso = AvisoMorosidad(
        miembro_id=miembro_id,
        detalle=detalle,
        plantilla_id=plantilla_id,
        estado=ESTADO_AVISO_PENDIENTE,
    )
    db.add(aviso)
    return aviso


def obtener_aviso(db: Session, aviso_id: int) -> AvisoMorosidad | None:
    """Devuelve un aviso de morosidad por su identificador."""
    return db.get(AvisoMorosidad, aviso_id)


def listar_avisos(
    db: Session, *, miembro_id: int | None = None, estado: str | None = None
) -> list[AvisoMorosidad]:
    """Lista los avisos de morosidad, del más reciente al más antiguo."""
    consulta = select(AvisoMorosidad).order_by(
        AvisoMorosidad.generado_en.desc(), AvisoMorosidad.id.desc()
    )
    if miembro_id is not None:
        consulta = consulta.where(AvisoMorosidad.miembro_id == miembro_id)
    if estado:
        consulta = consulta.where(AvisoMorosidad.estado == estado)
    return list(db.scalars(consulta))


def guardar_aviso(db: Session, aviso: AvisoMorosidad) -> AvisoMorosidad:
    """Confirma los cambios de un aviso de morosidad."""
    db.add(aviso)
    db.commit()
    db.refresh(aviso)
    return aviso
