"""T8.8 · Integración: flujo de pago completo y transacción atómica."""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import func, select

from app.models.membresia import (
    ESTADO_PAGADA,
    ESTADO_PENDIENTE,
    NIVEL_ACTIVA,
    NIVEL_MATRICULA,
)
from app.models.miembro import ACTIVACION_ACTIVO
from app.models.pago import ImputacionPago, Pago
from app.repositories import membresia as repo_membresia
from app.repositories import pago as repo_pago
from app.services import membresias as servicio_membresias
from app.services import pagos as servicio_pagos


def test_flujo_pago_completo_actualiza_estado_de_cuenta(db, niveles):
    """Alta → pago inicial → imputaciones → estado de cuenta y activación."""
    miembro = servicio_membresias.crear_miembro(
        db,
        nombre_completo="Flujo Completo",
        email="flujo@example.com",
        categoria="activo",
        fecha_incorporacion=date(2026, 2, 1),
    )

    resultado = servicio_pagos.registrar_pago(
        db,
        miembro=miembro,
        monto_clp=20_000,
        anio=2026,
        meses=[2],
        fecha_pago=date(2026, 2, 1),
        observaciones="Pago inicial",
    )

    assert resultado.activado is True
    assert len(resultado.imputaciones) == 2
    assert resultado.monto_imputado_clp == 20_000
    assert sum(imp.monto_clp for imp in resultado.imputaciones) == 20_000

    imputaciones = repo_pago.imputaciones_de_pago(db, resultado.pago.id)
    assert len(imputaciones) == 2
    assert [imp.orden for imp in imputaciones] == [1, 2]

    matricula = repo_membresia.obtener_cuota(
        db, miembro.id, 2026, 2, niveles[NIVEL_MATRICULA].id
    )
    cuota = repo_membresia.obtener_cuota(
        db, miembro.id, 2026, 2, niveles[NIVEL_ACTIVA].id
    )
    assert matricula.estado == ESTADO_PAGADA
    assert cuota.estado == ESTADO_PAGADA

    db.refresh(miembro)
    assert miembro.situacion_activacion == ACTIVACION_ACTIVO
    assert servicio_pagos.saldo_a_favor(db, miembro) == 0


def test_pago_es_atomico_si_falla_la_imputacion(
    db, niveles, miembro_factory, cuota_factory, monkeypatch
):
    """Si falla la imputación no queda un pago parcial guardado (T5.12)."""
    miembro = miembro_factory()
    cuota = cuota_factory(miembro, niveles[NIVEL_ACTIVA], 2026, 1)

    def _falla(*_args, **_kwargs):
        raise RuntimeError("fallo simulado al generar el abono")

    monkeypatch.setattr(repo_pago, "crear_abono", _falla)

    with pytest.raises(RuntimeError):
        servicio_pagos.registrar_pago(
            db,
            miembro=miembro,
            monto_clp=20_000,
            anio=2026,
            meses=[1],
            fecha_pago=date(2026, 1, 3),
        )

    assert db.scalar(select(func.count()).select_from(Pago)) == 0
    assert db.scalar(select(func.count()).select_from(ImputacionPago)) == 0

    db.refresh(cuota)
    assert cuota.estado == ESTADO_PENDIENTE
    assert cuota.monto_pagado_clp == 0


def test_rechaza_segundo_pago_del_mismo_ciclo(
    db, niveles, miembro_factory, cuota_factory
):
    """No se permite duplicar el pago de un ciclo ya pagado (RN-08, CA-20)."""
    miembro = miembro_factory()
    cuota_factory(
        miembro, niveles[NIVEL_ACTIVA], 2026, 1, estado=ESTADO_PAGADA, pagado=15_000
    )

    with pytest.raises(servicio_pagos.ErrorPago):
        servicio_pagos.registrar_pago(
            db,
            miembro=miembro,
            monto_clp=15_000,
            anio=2026,
            meses=[1],
            fecha_pago=date(2026, 1, 3),
        )


def test_rechaza_pago_de_miembro_exento(
    db, niveles, miembro_factory, cuota_factory
):
    """Un miembro exento no genera obligación de pago (RN-05)."""
    miembro = miembro_factory(exento=True)
    cuota_factory(
        miembro, niveles[NIVEL_ACTIVA], 2026, 1, estado="exenta"
    )

    with pytest.raises(servicio_pagos.ErrorPago):
        servicio_pagos.registrar_pago(
            db,
            miembro=miembro,
            monto_clp=15_000,
            anio=2026,
            meses=[1],
            fecha_pago=date(2026, 1, 3),
        )
