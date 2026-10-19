"""Validaciones de entrada del pago y observaciones (CA-17, CA-21, CA-28, CA-31)."""

from __future__ import annotations

from datetime import date

import pytest

from app.models.membresia import NIVEL_ACTIVA
from app.models.pago import MEDIO_EFECTIVO, MEDIO_TRANSFERENCIA
from app.services import pagos as servicio_pagos


@pytest.mark.parametrize("monto", [0, -1])
def test_monto_invalido(monto):
    with pytest.raises(servicio_pagos.ErrorPago):
        servicio_pagos.validar_pago(
            monto_clp=monto, medio=MEDIO_TRANSFERENCIA, anio=2026, meses=[1]
        )


@pytest.mark.parametrize("medio", ["cheque", "tarjeta", ""])
def test_medio_no_permitido(medio):
    """CA-28: solo se admite transferencia (principal) o efectivo (excepcional)."""
    with pytest.raises(servicio_pagos.ErrorPago):
        servicio_pagos.validar_pago(
            monto_clp=10_000, medio=medio, anio=2026, meses=[1]
        )


@pytest.mark.parametrize("medio", [MEDIO_TRANSFERENCIA, MEDIO_EFECTIVO])
def test_medios_permitidos(medio):
    servicio_pagos.validar_pago(
        monto_clp=10_000, medio=medio, anio=2026, meses=[1]
    )


def test_anio_y_meses_invalidos():
    with pytest.raises(servicio_pagos.ErrorPago):
        servicio_pagos.validar_pago(
            monto_clp=10_000, medio=MEDIO_TRANSFERENCIA, anio=1999, meses=[1]
        )
    with pytest.raises(servicio_pagos.ErrorPago):
        servicio_pagos.validar_pago(
            monto_clp=10_000, medio=MEDIO_TRANSFERENCIA, anio=2026, meses=[]
        )
    with pytest.raises(servicio_pagos.ErrorPago):
        servicio_pagos.validar_pago(
            monto_clp=10_000, medio=MEDIO_TRANSFERENCIA, anio=2026, meses=[1, 1]
        )
    with pytest.raises(servicio_pagos.ErrorPago):
        servicio_pagos.validar_pago(
            monto_clp=10_000, medio=MEDIO_TRANSFERENCIA, anio=2026, meses=[13]
        )


def test_monto_distinto_a_la_cuota_y_observaciones(
    db, niveles, miembro_factory, cuota_factory
):
    """CA-17 y CA-31: monto libre aceptado y observaciones guardadas."""
    miembro = miembro_factory()
    cuota = cuota_factory(miembro, niveles[NIVEL_ACTIVA], 2026, 1)

    resultado = servicio_pagos.registrar_pago(
        db,
        miembro=miembro,
        monto_clp=17_000,
        anio=2026,
        meses=[1],
        fecha_pago=date(2026, 1, 3),
        medio=MEDIO_EFECTIVO,
        observaciones="Pago en efectivo autorizado por Tesorería",
    )

    assert resultado.pago.monto_clp == 17_000
    assert (
        resultado.pago.observaciones
        == "Pago en efectivo autorizado por Tesorería"
    )
    assert resultado.pago.medio == MEDIO_EFECTIVO
    db.refresh(cuota)
    assert cuota.estado == "pagada"
    assert cuota.monto_pagado_clp == 15_000
    assert resultado.abono_clp == 2_000
