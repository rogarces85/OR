"""Modelos de compras del club y cobro separado a alumnos (F-25, RN-23)."""

from __future__ import annotations

from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

ESTADO_COMPRA_REGISTRADA = "registrada"

ESTADO_CARGO_PENDIENTE = "pendiente"
ESTADO_CARGO_PAGADO = "pagado"


class CompraClub(Base):
    """Compra del club (por ejemplo, polerones) registrada como depósito (F-25)."""

    __tablename__ = "compras_club"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    descripcion: Mapped[str] = mapped_column(String(200), nullable=False)
    proveedor: Mapped[str | None] = mapped_column(String(200))
    fecha: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    monto_total_clp: Mapped[int] = mapped_column(Integer, nullable=False)
    estado: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ESTADO_COMPRA_REGISTRADA
    )

    items = relationship(
        "CompraItem", back_populates="compra", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<CompraClub {self.descripcion!r} {self.monto_total_clp} CLP>"


class CompraItem(Base):
    """Ítem de una compra del club, con precio unitario y cantidad (F-25)."""

    __tablename__ = "compras_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    compra_id: Mapped[int] = mapped_column(
        ForeignKey("compras_club.id"), nullable=False, index=True
    )
    descripcion: Mapped[str] = mapped_column(String(200), nullable=False)
    precio_unitario_clp: Mapped[int] = mapped_column(Integer, nullable=False)
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    compra = relationship("CompraClub", back_populates="items")
    cargos = relationship("CargoAlumno", back_populates="compra_item")

    def __repr__(self) -> str:
        return f"<CompraItem {self.descripcion!r} x{self.cantidad}>"


class CargoAlumno(Base):
    """Cargo separado a un alumno por un ítem de compra (D-19, RN-23)."""

    __tablename__ = "cargos_alumno"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    miembro_id: Mapped[int] = mapped_column(
        ForeignKey("miembros.id"), nullable=False, index=True
    )
    compra_item_id: Mapped[int | None] = mapped_column(ForeignKey("compras_items.id"))
    monto_clp: Mapped[int] = mapped_column(Integer, nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    estado: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ESTADO_CARGO_PENDIENTE
    )
    pago_id: Mapped[int | None] = mapped_column(ForeignKey("pagos.id"))

    miembro = relationship("Miembro", back_populates="cargos")
    compra_item = relationship("CompraItem", back_populates="cargos")
    pago = relationship("Pago")

    def __repr__(self) -> str:
        return f"<CargoAlumno miembro={self.miembro_id} {self.monto_clp} CLP>"
