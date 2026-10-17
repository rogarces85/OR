"""Modelos de pagos, imputaciones y abonos (F-08, F-12, F-13)."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

MEDIO_TRANSFERENCIA = "transferencia"
MEDIO_EFECTIVO = "efectivo"
MEDIOS_PAGO: tuple[str, ...] = (MEDIO_TRANSFERENCIA, MEDIO_EFECTIVO)

ESTADO_DISPONIBLE = "disponible"
ESTADO_APLICADO = "aplicado"


class Pago(Base):
    """Pago recibido de un miembro, con monto libre y observaciones (F-12, F-14)."""

    __tablename__ = "pagos"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    miembro_id: Mapped[int] = mapped_column(
        ForeignKey("miembros.id"), nullable=False, index=True
    )
    monto_clp: Mapped[int] = mapped_column(Integer, nullable=False)
    fecha_pago: Mapped[date] = mapped_column(
        Date, nullable=False, default=date.today
    )
    medio: Mapped[str] = mapped_column(
        String(20), nullable=False, default=MEDIO_TRANSFERENCIA
    )
    observaciones: Mapped[str | None] = mapped_column(Text)
    registrado_por: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    creado_en: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    miembro = relationship("Miembro", back_populates="pagos")
    usuario_registro = relationship("Usuario")
    imputaciones = relationship(
        "ImputacionPago", back_populates="pago", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Pago {self.id} {self.monto_clp} CLP>"


class ImputacionPago(Base):
    """Aplicación de una parte de un pago a una cuota concreta (F-13, RN-17)."""

    __tablename__ = "imputaciones_pago"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    pago_id: Mapped[int] = mapped_column(
        ForeignKey("pagos.id"), nullable=False, index=True
    )
    cuota_id: Mapped[int | None] = mapped_column(ForeignKey("cuotas_mensuales.id"))
    monto_clp: Mapped[int] = mapped_column(Integer, nullable=False)
    orden: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    pago = relationship("Pago", back_populates="imputaciones")
    cuota = relationship("CuotaMensual", back_populates="imputaciones")

    def __repr__(self) -> str:
        return f"<ImputacionPago pago={self.pago_id} monto={self.monto_clp}>"


class Abono(Base):
    """Saldo a favor de un miembro que se aplica a la siguiente cuota (D-15)."""

    __tablename__ = "abonos"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    miembro_id: Mapped[int] = mapped_column(
        ForeignKey("miembros.id"), nullable=False, index=True
    )
    monto_clp: Mapped[int] = mapped_column(Integer, nullable=False)
    saldo_disponible_clp: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    origen_pago_id: Mapped[int | None] = mapped_column(ForeignKey("pagos.id"))
    creado_en: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    estado: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ESTADO_DISPONIBLE
    )

    miembro = relationship("Miembro", back_populates="abonos")
    origen = relationship("Pago")

    def __repr__(self) -> str:
        return f"<Abono miembro={self.miembro_id} saldo={self.saldo_disponible_clp}>"
