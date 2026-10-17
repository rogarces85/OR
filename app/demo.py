"""Datos adicionales para el demo guiado (ver ``specs/DEMO.md``).

La semilla deja a **Carla Deudora** con 5 meses de deuda cerrada (color rojo).
La negociación exige **más de 6 meses** (RN-22), así que este comando agrega dos
cuotas mensuales impagas anteriores para dejarla elegible y poder demostrar el
flujo completo de negociación.

Es **idempotente**: volver a ejecutarlo no duplica cuotas.

Uso::

    python -m app.demo
"""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.membresia import ESTADO_PENDIENTE, NIVEL_ACTIVA
from app.models.miembro import Miembro
from app.repositories import membresia as repo_membresia
from app.repositories import miembro as repo_miembro
from app.services import morosidad as servicio_morosidad
from app.services import negociacion as servicio_negociacion
from app.services.morosidad import MorosidadInfo

EMAIL_DEMO = "carla.deudora@example.com"
# La negociación exige *más de* 6 meses (RN-22), así que el objetivo es 7.
OBJETIVO_MESES = servicio_negociacion.MESES_MINIMOS + 1


def _mes_desplazado(anio: int, mes: int, atras: int) -> tuple[int, int]:
    """Devuelve el periodo ``atras`` meses antes de (año, mes)."""
    total = int(anio) * 12 + (int(mes) - 1) - atras
    return total // 12, total % 12 + 1


def _morosidad(db: Session, miembro: Miembro) -> MorosidadInfo:
    """Calcula la morosidad actual del miembro con sus cuotas y negociaciones."""
    return servicio_morosidad.calcular_morosidad(
        miembro,
        repo_membresia.cuotas_mensuales_de_miembro(db, miembro.id),
        deuda_excluida_clp=repo_membresia.deuda_negociada_clp(db, miembro.id),
    )


def preparar(db: Session) -> MorosidadInfo:
    """Deja a Carla elegible para negociar y devuelve su morosidad resultante.

    Es idempotente: agrega solo los meses que faltan para superar los 6 meses
    (RN-22) y, una vez alcanzado el objetivo, no vuelve a tocar la base.
    """
    miembro = repo_miembro.obtener_por_email(db, EMAIL_DEMO)
    if miembro is None:
        raise SystemExit(
            "No se encontró el miembro de demo. Ejecuta antes: python -m app.seed"
        )

    nivel = repo_membresia.obtener_nivel_por_codigo(db, NIVEL_ACTIVA)
    if nivel is None:
        raise SystemExit(
            "Falta el catálogo de cuotas. Ejecuta antes: python -m app.seed"
        )

    cuotas = repo_membresia.cuotas_mensuales_de_miembro(db, miembro.id)
    if not cuotas:
        raise SystemExit(
            "El miembro de demo no tiene cuotas mensuales; revisa la semilla."
        )

    faltantes = max(0, OBJETIVO_MESES - _morosidad(db, miembro).meses_deuda)
    if faltantes:
        mas_antigua = min((cuota.anio, cuota.mes) for cuota in cuotas)
        for atras in range(faltantes, 0, -1):
            anio, mes = _mes_desplazado(*mas_antigua, atras)
            if (
                repo_membresia.obtener_cuota(db, miembro.id, anio, mes, nivel.id)
                is None
            ):
                repo_membresia.crear_cuota(
                    db,
                    miembro_id=miembro.id,
                    anio=anio,
                    mes=mes,
                    nivel_cuota_id=nivel.id,
                    monto_clp=nivel.monto_clp,
                    monto_pagado_clp=0,
                    estado=ESTADO_PENDIENTE,
                )
                db.flush()
        # Coherencia: la incorporación no puede ser posterior a la cuota nueva.
        anio_min, mes_min = _mes_desplazado(*mas_antigua, faltantes)
        miembro.fecha_incorporacion = min(
            miembro.fecha_incorporacion, date(anio_min, mes_min, 1)
        )

    db.commit()
    return _morosidad(db, miembro)


def main() -> None:
    """Prepara los datos de demo e informa el resultado."""
    with SessionLocal() as db:
        info = preparar(db)
    elegible = "sí" if servicio_negociacion.puede_negociar(info) else "no"
    print("Datos de demo preparados (idempotente).")
    print(
        f"{EMAIL_DEMO}: {info.meses_deuda} mes(es) de deuda, "
        f"color {info.color}, elegible para negociar: {elegible}."
    )


if __name__ == "__main__":
    main()
