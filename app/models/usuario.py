"""Modelo de usuarios del sistema (F-02, D-7)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

ROL_ADMIN = "admin"
ROL_TESORERO = "tesorero"
ROL_MIEMBRO = "miembro"
ROLES_GESTION: tuple[str, ...] = (ROL_ADMIN, ROL_TESORERO)
ROLES: tuple[str, ...] = (ROL_ADMIN, ROL_TESORERO, ROL_MIEMBRO)


class Usuario(Base):
    """Usuario que inicia sesión en el sistema (Admin, Tesorero o Miembro)."""

    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    rol: Mapped[str] = mapped_column(String(20), nullable=False, default=ROL_MIEMBRO)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    miembro = relationship("Miembro", back_populates="usuario", uselist=False)

    def __repr__(self) -> str:
        return f"<Usuario {self.email!r} rol={self.rol!r}>"
