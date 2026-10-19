"""T8.4 · Abono y aplicación automática a la siguiente cuota (RN-18, CA-23)."""

from __future__ import annotations

from datetime import date

from app.models.membresia import NIVEL_ACTIVA
from app.repositories import membresia as repo_membresia
from app.services import membresias as servicio_membresias
from app.services import pagos as servicio_pagos


def test_excedente_que_no_alcanza_una_cuota_genera_abono(
    db, niveles, miembro_factory, cuota_factory
):
    """El excedente se guarda como saldo a favor (D-15)."""
    miembro = miembro_factory()
    activa = niveles[NIVEL_ACTIVA]
    cuota_factory(miembro, activa, 2026, 1)

    resultado = servicio_pagos.registrar_pago(
        db,
        miembro=miembro,
        monto_clp=20_000,
        anio=2026,
        meses=[1],
        fecha_pago=date(2026, 1, 3),
    )

    assert resultado.monto_imputado_clp == 15_000
    assert resultado.abono_clp == 5_000
    assert servicio_pagos.saldo_a_favor(db, miembro) == 5_000


def test_abono_se_aplica_al_generar_la_siguiente_cuota(
    db, niveles, miembro_factory, cuota_factory
):
    """Al generar la cuota siguiente, el abono se descuenta automáticamente."""
    miembro = miembro_factory()
    activa = niveles[NIVEL_ACTIVA]
    cuota_factory(miembro, activa, 2026, 1)

    servicio_pagos.registrar_pago(
        db,
        miembro=miembro,
        monto_clp=20_000,
        anio=2026,
        meses=[1],
        fecha_pago=date(2026, 1, 3),
    )
    assert servicio_pagos.saldo_a_favor(db, miembro) == 5_000

    creadas = servicio_membresias.generar_cuotas_del_periodo(db, 2026, 2)
    assert len(creadas) == 1

    febrero = repo_membresia.obtener_cuota(db, miembro.id, 2026, 2, activa.id)
    assert febrero.monto_pagado_clp == 5_000
    assert febrero.estado == "parcial"
    assert febrero.saldo_clp == 10_000
    assert servicio_pagos.saldo_a_favor(db, miembro) == 0


def test_abono_mayor_que_la_cuota_deja_saldo_disponible(
    db, niveles, miembro_factory, cuota_factory
):
    """Si el abono supera la cuota, el remanente queda disponible (RN-18)."""
    miembro = miembro_factory()
    activa = niveles[NIVEL_ACTIVA]
    cuota_factory(miembro, activa, 2026, 1)

    servicio_pagos.registrar_pago(
        db,
        miembro=miembro,
        monto_clp=40_000,
        anio=2026,
        meses=[1],
        fecha_pago=date(2026, 1, 3),
    )
    assert servicio_pagos.saldo_a_favor(db, miembro) == 25_000

    servicio_membresias.generar_cuotas_del_periodo(db, 2026, 2)
    febrero = repo_membresia.obtener_cuota(db, miembro.id, 2026, 2, activa.id)
    assert febrero.monto_pagado_clp == 15_000
    assert febrero.estado == "pagada"
    assert servicio_pagos.saldo_a_favor(db, miembro) == 10_000


def test_sin_siguiente_cuota_el_abono_permanece_disponible(
    db, niveles, miembro_factory, cuota_factory
):
    """Sin cuota posterior, el abono no se pierde: queda a favor del miembro."""
    miembro = miembro_factory()
    activa = niveles[NIVEL_ACTIVA]
    cuota_factory(miembro, activa, 2026, 1)

    servicio_pagos.registrar_pago(
        db,
        miembro=miembro,
        monto_clp=20_000,
        anio=2026,
        meses=[1],
        fecha_pago=date(2026, 1, 3),
    )

    assert repo_membresia.siguiente_cuota_impaga(db, miembro.id) is None
    assert servicio_pagos.saldo_a_favor(db, miembro) == 5_000
    assert (
        repo_membresia.obtener_cuota(db, miembro.id, 2026, 1, activa.id).estado
        == "pagada"
    )
    assert (
        repo_membresia.obtener_cuota(db, miembro.id, 2026, 2, activa.id) is None
    )
