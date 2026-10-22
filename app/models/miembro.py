"""Modelos de miembros del club y su historial de categoría (F-01, F-05, D-6)."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

CATEGORIA_ACTIVO = "activo"
CATEGORIA_MEMBRESIA = "membresia"
CATEGORIAS: tuple[str, ...] = (CATEGORIA_ACTIVO, CATEGORIA_MEMBRESIA)

ACTIVACION_PENDIENTE = "pendiente"
ACTIVACION_ACTIVO = "activo"

CONDICION_NORMAL = "normal"
CONDICION_EXENTO = "exento"

MOTIVOS_EXENCION: tuple[str, ...] = (
    "Becado",
    "Invitado/influencer",
    "Retirado",
)


class Miembro(Base):
    """Ficha ampliada del miembro (D-6) con categoría y condición (D-26)."""

    __tablename__ = "miembros"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nombre_completo: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    telefono: Mapped[str | None] = mapped_column(String(40))
    rut: Mapped[str | None] = mapped_column(String(20))
    fecha_nacimiento: Mapped[date | None] = mapped_column(Date)
    direccion: Mapped[str | None] = mapped_column(String(255))
    contacto_emergencia: Mapped[str | None] = mapped_column(String(200))
    fecha_incorporacion: Mapped[date] = mapped_column(
        Date, nullable=False, default=date.today
    )
    matriculado: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    categoria: Mapped[str] = mapped_column(
        String(20), nullable=False, default=CATEGORIA_ACTIVO
    )
    situacion_activacion: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ACTIVACION_PENDIENTE
    )
    condicion_especial: Mapped[str] = mapped_column(
        String(20), nullable=False, default=CONDICION_NORMAL
    )
    motivo_exencion: Mapped[str | None] = mapped_column(String(50))
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))

    usuario = relationship("Usuario", back_populates="miembro")
    cuotas = relationship(
        "CuotaMensual", back_populates="miembro", cascade="all, delete-orphan"
    )
    historial = relationship(
        "HistorialCategoria", back_populates="miembro", cascade="all, delete-orphan"
    )
    pagos = relationship("Pago", back_populates="miembro")
    abonos = relationship("Abono", back_populates="miembro")
    cargos = relationship("CargoAlumno", back_populates="miembro")
    negociaciones = relationship("NegociacionDeuda", back_populates="miembro")
    avisos = relationship("AvisoMorosidad", back_populates="miembro")
    egresos_como_responsable = relationship(
        "Egreso", back_populates="miembro_responsable"
    )

    @property
    def esta_exento(self) -> bool:
        """Indica si el miembro está excluido de cobros y avisos (RN-05)."""
        return self.condicion_especial == CONDICION_EXENTO

    def __repr__(self) -> str:
        return f"<Miembro {self.nombre_completo!r}>"


class HistorialCategoria(Base):
    """Registro de cada cambio de categoría de un miembro (F-05, RN-25)."""

    __tablename__ = "historial_categorias"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    miembro_id: Mapped[int] = mapped_column(
        ForeignKey("miembros.id"), nullable=False, index=True
    )
    categoria_anterior: Mapped[str] = mapped_column(String(20), nullable=False)
    categoria_nueva: Mapped[str] = mapped_column(String(20), nullable=False)
    fecha: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))

    miembro = relationship("Miembro", back_populates="historial")
    usuario = relationship("Usuario")

    def __repr__(self) -> str:
        return (
            f"<HistorialCategoria {self.categoria_anterior}->{self.categoria_nueva}>"
        )
