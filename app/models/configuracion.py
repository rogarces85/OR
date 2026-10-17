"""Modelos de configuración y comunicación (F-23, F-26, D-21, D-22)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

ESTADO_AVISO_PENDIENTE = "pendiente"
ESTADO_AVISO_ENVIADO = "enviado"


class CuentaBancaria(Base):
    """Datos de la cuenta para transferencias (D-22, RN-26)."""

    __tablename__ = "cuentas_bancarias"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    titular: Mapped[str] = mapped_column(String(200), nullable=False)
    banco: Mapped[str] = mapped_column(String(120), nullable=False)
    numero_cuenta: Mapped[str] = mapped_column(String(40), nullable=False)
    rut: Mapped[str] = mapped_column(String(20), nullable=False)
    correo: Mapped[str] = mapped_column(String(255), nullable=False)

    def __repr__(self) -> str:
        return f"<CuentaBancaria {self.banco!r} {self.numero_cuenta!r}>"


class PlantillaCorreo(Base):
    """Plantilla del correo de morosidad que envía manualmente el Tesorero (D-21)."""

    __tablename__ = "plantillas_correo"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    asunto: Mapped[str] = mapped_column(String(255), nullable=False)
    cuerpo: Mapped[str] = mapped_column(Text, nullable=False)
    activa: Mapped[bool] = mapped_column(nullable=False, default=True)

    avisos = relationship("AvisoMorosidad", back_populates="plantilla")

    def __repr__(self) -> str:
        return f"<PlantillaCorreo {self.nombre!r}>"


class AvisoMorosidad(Base):
    """Alerta de morosidad para el Tesorero; el correo se envía a mano (F-23)."""

    __tablename__ = "avisos_morosidad"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    miembro_id: Mapped[int] = mapped_column(
        ForeignKey("miembros.id"), nullable=False, index=True
    )
    plantilla_id: Mapped[int | None] = mapped_column(
        ForeignKey("plantillas_correo.id")
    )
    generado_en: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    detalle: Mapped[str | None] = mapped_column(Text)
    estado: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ESTADO_AVISO_PENDIENTE
    )
    enviado_por: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    enviado_en: Mapped[datetime | None] = mapped_column(DateTime)

    miembro = relationship("Miembro", back_populates="avisos")
    plantilla = relationship("PlantillaCorreo", back_populates="avisos")
    usuario_envio = relationship("Usuario")

    def __repr__(self) -> str:
        return f"<AvisoMorosidad miembro={self.miembro_id} {self.estado}>"
