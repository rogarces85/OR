"""Consultas y persistencia de usuarios (T3.8)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.usuario import ROL_MIEMBRO, Usuario


def obtener(db: Session, usuario_id: int) -> Usuario | None:
    """Devuelve un usuario por su identificador."""
    return db.get(Usuario, usuario_id)


def obtener_por_email(db: Session, email: str) -> Usuario | None:
    """Devuelve un usuario por su correo (identificador único)."""
    return db.scalar(select(Usuario).where(Usuario.email == email.strip().lower()))


def listar(db: Session) -> list[Usuario]:
    """Lista todos los usuarios ordenados por correo."""
    return list(db.scalars(select(Usuario).order_by(Usuario.email)))


def crear(
    db: Session,
    *,
    email: str,
    password_hash: str,
    rol: str = ROL_MIEMBRO,
    activo: bool = True,
) -> Usuario:
    """Crea un usuario y lo deja listo para usar (sin confirmar la transacción)."""
    usuario = Usuario(
        email=email.strip().lower(),
        password_hash=password_hash,
        rol=rol,
        activo=activo,
    )
    db.add(usuario)
    return usuario


def guardar(db: Session, usuario: Usuario) -> Usuario:
    """Confirma los cambios de un usuario."""
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario
