"""Consultas y persistencia de miembros (T3.8)."""

from __future__ import annotations

from datetime import date

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.miembro import (
    ACTIVACION_PENDIENTE,
    CATEGORIA_ACTIVO,
    CONDICION_NORMAL,
    Miembro,
)


def obtener(db: Session, miembro_id: int) -> Miembro | None:
    """Devuelve un miembro por su identificador."""
    return db.get(Miembro, miembro_id)


def obtener_por_email(db: Session, email: str) -> Miembro | None:
    """Devuelve un miembro por su correo (identificador único, RN-11)."""
    return db.scalar(select(Miembro).where(Miembro.email == email.strip().lower()))


def obtener_por_usuario(db: Session, usuario_id: int) -> Miembro | None:
    """Devuelve el miembro asociado a un usuario (o ``None`` si no hay ficha)."""
    return db.scalar(select(Miembro).where(Miembro.usuario_id == usuario_id))


def listar(
    db: Session,
    *,
    texto: str | None = None,
    categoria: str | None = None,
    situacion: str | None = None,
) -> list[Miembro]:
    """Lista miembros aplicando filtros de búsqueda, categoría y activación."""
    consulta = select(Miembro).order_by(Miembro.nombre_completo)
    if texto:
        patron = f"%{texto.strip()}%"
        consulta = consulta.where(
            or_(
                Miembro.nombre_completo.ilike(patron),
                Miembro.email.ilike(patron),
                Miembro.rut.ilike(patron),
            )
        )
    if categoria:
        consulta = consulta.where(Miembro.categoria == categoria)
    if situacion:
        consulta = consulta.where(Miembro.situacion_activacion == situacion)
    return list(db.scalars(consulta))


def contar(db: Session) -> int:
    """Cuenta los miembros registrados."""
    return int(db.scalar(select(func.count()).select_from(Miembro)) or 0)


def crear(
    db: Session,
    *,
    nombre_completo: str,
    email: str,
    telefono: str | None = None,
    rut: str | None = None,
    fecha_nacimiento: date | None = None,
    direccion: str | None = None,
    contacto_emergencia: str | None = None,
    fecha_incorporacion: date | None = None,
    categoria: str = CATEGORIA_ACTIVO,
    situacion_activacion: str = ACTIVACION_PENDIENTE,
    condicion_especial: str = CONDICION_NORMAL,
    motivo_exencion: str | None = None,
    usuario_id: int | None = None,
) -> Miembro:
    """Crea un miembro; la fecha de incorporación se captura automáticamente (D-3)."""
    miembro = Miembro(
        nombre_completo=nombre_completo.strip(),
        email=email.strip().lower(),
        telefono=telefono,
        rut=rut,
        fecha_nacimiento=fecha_nacimiento,
        direccion=direccion,
        contacto_emergencia=contacto_emergencia,
        fecha_incorporacion=fecha_incorporacion or date.today(),
        categoria=categoria,
        situacion_activacion=situacion_activacion,
        condicion_especial=condicion_especial,
        motivo_exencion=motivo_exencion,
        usuario_id=usuario_id,
    )
    db.add(miembro)
    return miembro


def guardar(db: Session, miembro: Miembro) -> Miembro:
    """Confirma los cambios de un miembro."""
    db.add(miembro)
    db.commit()
    db.refresh(miembro)
    return miembro
