"""Modelos financieros: categorías de egreso, egresos y gastos fijos.

Cubre F-16, F-17, F-18 y RN-10.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

TIPO_GENERAL = "general"
TIPO_ACTIVO = "activo"
TIPO_GASTO_FIJO = "gasto_fijo"
TIPO_COMPRA = "compra"

# Base fija de categorías de egreso (D-5, D-12, P-7).
CATEGORIAS_BASE: tuple[str, ...] = (
    "Activos",
    "Gastos fijos",
    "Transferencias",
    "Tarjeta",
    "Otros",
)

PERIODICIDAD_MENSUAL = "mensual"


class CategoriaEgreso(Base):
    """Categoría de egreso, base o personalizada (RN-10)."""

    __tablename__ = "categorias_egreso"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    es_base: Mapped[bool] = mapped_column(nullable=False, default=False)
    activo: Mapped[bool] = mapped_column(nullable=False, default=True)

    egresos = relationship("Egreso", back_populates="categoria")

    def __repr__(self) -> str:
        return f"<CategoriaEgreso {self.nombre!r}>"


class Egreso(Base):
    """Salida de dinero del club, siempre asociada a una categoría (F-16)."""

    __tablename__ = "egresos"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    monto_clp: Mapped[int] = mapped_column(Integer, nullable=False)
    fecha: Mapped[date] = mapped_column(
        Date, nullable=False, default=date.today, index=True
    )
    concepto: Mapped[str] = mapped_column(String(200), nullable=False)
    categoria_egreso_id: Mapped[int] = mapped_column(
        ForeignKey("categorias_egreso.id"), nullable=False
    )
    tipo: Mapped[str] = mapped_column(String(20), nullable=False, default=TIPO_GENERAL)
    miembro_responsable_id: Mapped[int | None] = mapped_column(
        ForeignKey("miembros.id")
    )
    registrado_por: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))

    categoria = relationship("CategoriaEgreso", back_populates="egresos")
    miembro_responsable = relationship(
        "Miembro", back_populates="egresos_como_responsable"
    )
    usuario_registro = relationship("Usuario")

    def __repr__(self) -> str:
        return f"<Egreso {self.id} {self.monto_clp} CLP>"


class GastoFijo(Base):
    """Costo operativo mensual recurrente del club (F-18, RN-12)."""

    __tablename__ = "gastos_fijos"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    concepto: Mapped[str] = mapped_column(String(200), nullable=False)
    monto_clp: Mapped[int] = mapped_column(Integer, nullable=False)
    periodicidad: Mapped[str] = mapped_column(
        String(20), nullable=False, default=PERIODICIDAD_MENSUAL
    )
    activo: Mapped[bool] = mapped_column(nullable=False, default=True)

    def __repr__(self) -> str:
        return f"<GastoFijo {self.concepto!r} {self.monto_clp} CLP>"
