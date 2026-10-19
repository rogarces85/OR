"""T8.3 · Imputación de pagos: deuda antigua → mes/año → abono (RN-17, CA-22)."""

from __future__ import annotations

from datetime import date

from app.models.membresia import ESTADO_PAGADA, ESTADO_PENDIENTE, NIVEL_ACTIVA
from app.repositories import membresia as repo_membresia
from app.services import pagos as servicio_pagos


def _cuota(db, miembro_id, anio, mes, nivel):
    return repo_membresia.obtener_cuota(db, miembro_id, anio, mes, nivel.id)


def test_imputa_primero_la_deuda_mas_antigua(
    db, niveles, miembro_factory, cuota_factory
):
    """Un pago de 45.000 salda 30.000 del año anterior y cubre enero del actual."""
    miembro = miembro_factory()
    activa = niveles[NIVEL_ACTIVA]

    # Deuda del año anterior: 30.000 (nov y dic 2025).
    cuota_factory(miembro, activa, 2025, 11)
    cuota_factory(miembro, activa, 2025, 12)
    # Un mes del año anterior ya pagado (no debe tocarse).
    cuota_factory(miembro, activa, 2025, 10, estado=ESTADO_PAGADA, pagado=15_000)
    # Meses del año en curso.
    cuota_factory(miembro, activa, 2026, 1)
    cuota_factory(miembro, activa, 2026, 2)
    cuota_factory(miembro, activa, 2026, 3)

    resultado = servicio_pagos.registrar_pago(
        db,
        miembro=miembro,
        monto_clp=45_000,
        anio=2026,
        meses=[1, 2],
        fecha_pago=date(2026, 3, 3),
    )

    assert resultado.monto_imputado_clp == 45_000
    assert resultado.abono_clp == 0
    assert [imp.monto_clp for imp in resultado.imputaciones] == [
        15_000,
        15_000,
        15_000,
    ]

    assert _cuota(db, miembro.id, 2025, 10, activa).estado == ESTADO_PAGADA
    assert _cuota(db, miembro.id, 2025, 11, activa).estado == ESTADO_PAGADA
    assert _cuota(db, miembro.id, 2025, 12, activa).estado == ESTADO_PAGADA
    assert _cuota(db, miembro.id, 2026, 1, activa).estado == ESTADO_PAGADA
    # Los meses indicados quedan pendientes: primero se cubre la deuda antigua.
    assert _cuota(db, miembro.id, 2026, 2, activa).estado == ESTADO_PENDIENTE
    assert _cuota(db, miembro.id, 2026, 3, activa).estado == ESTADO_PENDIENTE


def test_pago_prioriza_los_meses_mas_antiguos(
    db, niveles, miembro_factory, cuota_factory
):
    """Aunque se seleccione un mes, primero se cubren los meses más antiguos."""
    miembro = miembro_factory()
    activa = niveles[NIVEL_ACTIVA]
    enero = cuota_factory(miembro, activa, 2026, 1)
    febrero = cuota_factory(miembro, activa, 2026, 2)
    abril = cuota_factory(miembro, activa, 2026, 4)

    resultado = servicio_pagos.registrar_pago(
        db,
        miembro=miembro,
        monto_clp=25_000,
        anio=2026,
        meses=[4],
        fecha_pago=date(2026, 6, 1),
    )

    assert resultado.monto_imputado_clp == 25_000
    assert enero.estado == ESTADO_PAGADA
    assert febrero.monto_pagado_clp == 10_000
    assert febrero.estado == "parcial"
    assert abril.estado == ESTADO_PENDIENTE


def test_pago_parcial_deja_cuota_en_estado_parcial(
    db, niveles, miembro_factory, cuota_factory
):
    """Un pago menor al saldo deja la cuota como parcial, no pagada."""
    miembro = miembro_factory()
    activa = niveles[NIVEL_ACTIVA]
    enero = cuota_factory(miembro, activa, 2026, 1)

    servicio_pagos.registrar_pago(
        db,
        miembro=miembro,
        monto_clp=7_000,
        anio=2026,
        meses=[1],
        fecha_pago=date(2026, 1, 2),
    )

    db.refresh(enero)
    assert enero.monto_pagado_clp == 7_000
    assert enero.estado == "parcial"
    assert enero.saldo_clp == 8_000
