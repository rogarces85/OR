"""Reportes: consolidado por periodo e informe calendario por miembro.

Cubre T5.32 (reporte consolidado, F-19), T5.33 (informe calendario, F-21) y
T5.34 (selección de periodo, UI-09). La exportación a XLSX/PDF es de la Fase 7.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from sqlalchemy.orm import Session

from app.models.finanzas import Egreso
from app.models.membresia import ESTADO_EXENTA, ESTADO_PAGADA, CuotaMensual
from app.models.miembro import Miembro
from app.models.pago import Pago
from app.repositories import finanzas as repo_finanzas
from app.repositories import membresia as repo_membresia
from app.repositories import pago as repo_pago


@dataclass
class ReporteConsolidado:
    """Ingresos contra egresos en un rango de fechas (F-19, CA-10)."""

    desde: date
    hasta: date
    ingresos: list[Pago] = field(default_factory=list)
    egresos: list[Egreso] = field(default_factory=list)

    @property
    def total_ingresos_clp(self) -> int:
        return sum(int(pago.monto_clp) for pago in self.ingresos)

    @property
    def total_egresos_clp(self) -> int:
        return sum(int(egreso.monto_clp) for egreso in self.egresos)

    @property
    def neto_clp(self) -> int:
        return self.total_ingresos_clp - self.total_egresos_clp

    @property
    def sin_movimientos(self) -> bool:
        """Indica si el periodo no tiene ingresos ni egresos (sección 9)."""
        return not self.ingresos and not self.egresos


def reporte_consolidado(
    db: Session, *, desde: date, hasta: date
) -> ReporteConsolidado:
    """Consolida ingresos y egresos de un rango de fechas (T5.32)."""
    return ReporteConsolidado(
        desde=desde,
        hasta=hasta,
        ingresos=repo_pago.listar(db, desde=desde, hasta=hasta),
        egresos=repo_finanzas.listar_egresos(db, desde=desde, hasta=hasta),
    )


@dataclass
class MesInforme:
    """Estado de la cuota de un mes dentro del informe calendario (UI-06)."""

    anio: int
    mes: int
    cuota: CuotaMensual | None

    @property
    def tiene_cuota(self) -> bool:
        return self.cuota is not None

    @property
    def estado(self) -> str:
        return self.cuota.estado if self.cuota is not None else "sin_cuota"

    @property
    def monto_clp(self) -> int:
        return int(self.cuota.monto_clp) if self.cuota is not None else 0

    @property
    def pagado_clp(self) -> int:
        return int(self.cuota.monto_pagado_clp) if self.cuota is not None else 0

    @property
    def es_pagada(self) -> bool:
        return self.cuota is not None and self.cuota.estado == ESTADO_PAGADA

    @property
    def es_exenta(self) -> bool:
        return self.cuota is not None and self.cuota.estado == ESTADO_EXENTA


@dataclass
class InformeCalendario:
    """Cuotas de un miembro a lo largo de un año, en formato calendario (F-21)."""

    miembro: Miembro
    anio: int
    meses: list[MesInforme] = field(default_factory=list)

    @property
    def total_monto_clp(self) -> int:
        return sum(mes.monto_clp for mes in self.meses)

    @property
    def total_pagado_clp(self) -> int:
        return sum(mes.pagado_clp for mes in self.meses)

    @property
    def total_pendiente_clp(self) -> int:
        return sum(
            mes.monto_clp - mes.pagado_clp
            for mes in self.meses
            if mes.cuota is not None
            and mes.cuota.estado not in (ESTADO_PAGADA, ESTADO_EXENTA)
        )


def informe_calendario(
    db: Session, miembro: Miembro, anio: int
) -> InformeCalendario:
    """Construye el informe calendario de un miembro para un año (T5.33)."""
    cuotas = repo_membresia.cuotas_mensuales_de_miembro(db, miembro.id)
    por_mes = {cuota.mes: cuota for cuota in cuotas if cuota.anio == int(anio)}
    meses = [
        MesInforme(anio=int(anio), mes=mes, cuota=por_mes.get(mes))
        for mes in range(1, 13)
    ]
    return InformeCalendario(miembro=miembro, anio=int(anio), meses=meses)
