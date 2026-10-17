"""Activación de la membresía: obligación inicial y evaluación del pago inicial.

Cubre F-07, RN-02, CA-01 y la decisión D-11: un miembro solo queda **Activo**
cuando completó el pago de **Matrícula + la cuota de su categoría elegida**
(Activa para alumnos, Estándar para miembros de apoyo). Con pago parcial queda
**pendiente**.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.models.membresia import CuotaMensual, NivelCuota
from app.models.miembro import ACTIVACION_ACTIVO, Miembro
from app.repositories import membresia as repo_membresia


@dataclass
class ConceptoObligacion:
    """Concepto que compone la obligación inicial (Matrícula o cuota de categoría)."""

    etiqueta: str
    requerido_clp: int
    pagado_clp: int

    @property
    def completo(self) -> bool:
        return self.pagado_clp >= self.requerido_clp

    @property
    def saldo_clp(self) -> int:
        return max(self.requerido_clp - self.pagado_clp, 0)


@dataclass
class EstadoActivacion:
    """Resultado de evaluar la obligación inicial (RN-02, D-11)."""

    conceptos: list[ConceptoObligacion] = field(default_factory=list)

    @property
    def requerido_clp(self) -> int:
        return sum(concepto.requerido_clp for concepto in self.conceptos)

    @property
    def pagado_clp(self) -> int:
        return sum(concepto.pagado_clp for concepto in self.conceptos)

    @property
    def saldo_clp(self) -> int:
        return max(self.requerido_clp - self.pagado_clp, 0)

    @property
    def completo(self) -> bool:
        return self.requerido_clp > 0 and self.saldo_clp == 0


def nivel_de_categoria_actual(
    db: Session, miembro: Miembro
) -> NivelCuota | None:
    """Nivel mensual que corresponde a la categoría actual del miembro (RN-01)."""
    return repo_membresia.nivel_de_categoria(db, miembro.categoria)


def obligacion_inicial(
    db: Session,
    miembro: Miembro,
    *,
    nivel_matricula: NivelCuota,
    nivel_categoria: NivelCuota,
) -> list[ConceptoObligacion]:
    """Compone la obligación inicial del Flujo 1 (RN-02, D-11).

    El monto pagado de cada concepto se toma de la cuota registrada en el mes de
    incorporación; si el pago aún no se ha registrado, se informa 0.
    """
    anio = miembro.fecha_incorporacion.year
    mes = miembro.fecha_incorporacion.month
    conceptos: list[ConceptoObligacion] = []
    for etiqueta, nivel in (
        ("Matrícula", nivel_matricula),
        (nivel_categoria.nombre, nivel_categoria),
    ):
        cuota = repo_membresia.obtener_cuota(db, miembro.id, anio, mes, nivel.id)
        conceptos.append(
            ConceptoObligacion(
                etiqueta=etiqueta,
                requerido_clp=int(nivel.monto_clp),
                pagado_clp=int(cuota.monto_pagado_clp) if cuota is not None else 0,
            )
        )
    return conceptos


def evaluar_activacion(db: Session, miembro: Miembro) -> EstadoActivacion:
    """Decide si el pago inicial (Matrícula + cuota de la categoría) está completo.

    Nota: el monto pagado proviene de las cuotas de la obligación inicial, es
    decir, de los pagos efectivamente aplicados a esos conceptos (RN-02).
    """
    nivel_matricula = repo_membresia.nivel_matricula(db)
    nivel_categoria = nivel_de_categoria_actual(db, miembro)
    if nivel_matricula is None or nivel_categoria is None:
        return EstadoActivacion()
    conceptos = obligacion_inicial(
        db,
        miembro,
        nivel_matricula=nivel_matricula,
        nivel_categoria=nivel_categoria,
    )
    return EstadoActivacion(conceptos=conceptos)


def aplicar_activacion(db: Session, miembro: Miembro) -> Miembro:
    """Marca al miembro como **Activo** una vez completo el pago inicial (F-07)."""
    miembro.situacion_activacion = ACTIVACION_ACTIVO
    db.add(miembro)
    db.commit()
    db.refresh(miembro)
    return miembro


def registrar_obligacion_inicial(db: Session, miembro: Miembro) -> list[CuotaMensual]:
    """Genera la obligación inicial: Matrícula + la cuota de la categoría (Flujo 1).

    Es idempotente: no vuelve a crear un concepto que ya exista para ese periodo.
    """
    anio = miembro.fecha_incorporacion.year
    mes = miembro.fecha_incorporacion.month
    niveles = [
        repo_membresia.nivel_matricula(db),
        repo_membresia.nivel_de_categoria(db, miembro.categoria),
    ]
    creadas: list[CuotaMensual] = []
    for nivel in niveles:
        if nivel is None:
            continue
        if repo_membresia.obtener_cuota(db, miembro.id, anio, mes, nivel.id) is not None:
            continue
        creadas.append(
            repo_membresia.crear_cuota(
                db,
                miembro_id=miembro.id,
                anio=anio,
                mes=mes,
                nivel_cuota_id=nivel.id,
                monto_clp=int(nivel.monto_clp),
            )
        )
    db.flush()
    return creadas
