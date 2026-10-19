"""T8.9 · Integración: alta de miembro → pago inicial → activo (CA-01)."""

from __future__ import annotations

from datetime import date

from app.models.membresia import ESTADO_PAGADA, ESTADO_PENDIENTE
from app.models.miembro import ACTIVACION_ACTIVO, ACTIVACION_PENDIENTE
from app.repositories import membresia as repo_membresia
from app.services import membresias as servicio_membresias
from app.services import pagos as servicio_pagos


def test_alta_y_activacion_end_to_end(db, niveles):
    miembro = servicio_membresias.crear_miembro(
        db,
        nombre_completo="Elena Integración",
        email="elena.integracion@example.com",
        telefono="+56 9 9999 9999",
        rut="99.999.999-9",
        categoria="activo",
        fecha_incorporacion=date(2026, 4, 12),
    )

    # 1. El alta crea la obligación inicial y deja pendiente.
    assert miembro.situacion_activacion == ACTIVACION_PENDIENTE
    assert miembro.fecha_incorporacion == date(2026, 4, 12)
    obligacion = repo_membresia.cuotas_de_miembro(db, miembro.id)
    assert len(obligacion) == 2
    assert all(cuota.estado == ESTADO_PENDIENTE for cuota in obligacion)

    # 2. Un pago parcial no activa.
    servicio_pagos.registrar_pago(
        db,
        miembro=miembro,
        monto_clp=5_000,
        anio=2026,
        meses=[4],
        fecha_pago=date(2026, 4, 12),
    )
    db.refresh(miembro)
    assert miembro.situacion_activacion == ACTIVACION_PENDIENTE

    # 3. El pago restante completa la obligación y activa.
    resultado = servicio_pagos.registrar_pago(
        db,
        miembro=miembro,
        monto_clp=15_000,
        anio=2026,
        meses=[4],
        fecha_pago=date(2026, 4, 13),
    )
    db.refresh(miembro)
    assert resultado.activado is True
    assert miembro.situacion_activacion == ACTIVACION_ACTIVO
    assert all(
        cuota.estado == ESTADO_PAGADA
        for cuota in repo_membresia.cuotas_de_miembro(db, miembro.id)
    )
