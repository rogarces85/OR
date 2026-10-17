"""Modelos de membresías: catálogo de cuotas, cuota mensual y negociación.

Cubre F-06, F-10 y F-24 (T3.3).
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

# Códigos del catálogo de cuotas (F-06, RN-01).
NIVEL_MATRICULA = "matricula"
NIVEL_ESTANDAR = "estandar"
NIVEL_ACTIVA = "activa"

TIPO_UNICO = "unico"
TIPO_MENSUAL = "mensual"

# Estados de una cuota mensual.
ESTADO_PENDIENTE = "pendiente"
ESTADO_PAGADA = "pagada"
ESTADO_PARCIAL = "parcial"
ESTADO_EXENTA = "exenta"

# Estados de una negociación de deuda (F-24).
ESTADO_PROPUESTA = "propuesta"
ESTADO_ACEPTADA = "aceptada"
ESTADO_NEGOCIACION_PAGADA = "pagada"


class NivelCuota(Base):
    """Nivel del catálogo de cuotas: Matrícula, Estándar o Activa (RN-01)."""

    __tablename__ = "niveles_cuota"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    codigo: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False, index=True
    )
    nombre: Mapped[str] = mapped_column(String(80), nullable=False)
    monto_clp: Mapped[int] = mapped_column(Integer, nullable=False)
    tipo: Mapped[str] = mapped_column(
        String(20), nullable=False, default=TIPO_MENSUAL
    )
    activo: Mapped[bool] = mapped_column(nullable=False, default=True)

    cuotas = relationship("CuotaMensual", back_populates="nivel")

    def __repr__(self) -> str:
        return f"<NivelCuota {self.codigo!r} {self.monto_clp} CLP>"


class CuotaMensual(Base):
    """Cuota de un miembro para un periodo (año/mes) con su estado de pago."""

    __tablename__ = "cuotas_mensuales"
    __table_args__ = (
        UniqueConstraint(
            "miembro_id", "anio", "mes", name="uq_cuota_miembro_periodo"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    miembro_id: Mapped[int] = mapped_column(
        ForeignKey("miembros.id"), nullable=False, index=True
    )
    anio: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    mes: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    nivel_cuota_id: Mapped[int] = mapped_column(
        ForeignKey("niveles_cuota.id"), nullable=False
    )
    monto_clp: Mapped[int] = mapped_column(Integer, nullable=False)
    monto_pagado_clp: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    estado: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ESTADO_PENDIENTE
    )

    miembro = relationship("Miembro", back_populates="cuotas")
    nivel = relationship("NivelCuota", back_populates="cuotas")
    imputaciones = relationship("ImputacionPago", back_populates="cuota")

    @property
    def saldo_clp(self) -> int:
        """Monto que aún queda por pagar de la cuota."""
        return max(self.monto_clp - self.monto_pagado_clp, 0)

    @property
    def esta_pagada(self) -> bool:
        return self.estado == ESTADO_PAGADA

    def __repr__(self) -> str:
        return f"<CuotaMensual miembro={self.miembro_id} {self.anio}-{self.mes:02d}>"


class NegociacionDeuda(Base):
    """Negociación de la deuda de un moroso de más de 6 meses (F-24, RN-22)."""

    __tablename__ = "negociaciones_deuda"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    miembro_id: Mapped[int] = mapped_column(
        ForeignKey("miembros.id"), nullable=False, index=True
    )
    deuda_total_clp: Mapped[int] = mapped_column(Integer, nullable=False)
    descuento_pct: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    monto_negociado_clp: Mapped[int] = mapped_column(Integer, nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    estado: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ESTADO_PROPUESTA
    )

    miembro = relationship("Miembro", back_populates="negociaciones")
    usuario = relationship("Usuario")

    def __repr__(self) -> str:
        return f"<NegociacionDeuda miembro={self.miembro_id} {self.estado}>"
