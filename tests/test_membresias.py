"""Catálogo, generación de cuotas, exenciones y cambio de categoría.

Cubre CA-02, CA-03, CA-29 y las reglas de F-06, F-09, F-10 y RN-25.
"""

from __future__ import annotations

from datetime import date

import pytest

from app.models.membresia import (
    ESTADO_EXENTA,
    ESTADO_PAGADA,
    ESTADO_PENDIENTE,
    NIVEL_ACTIVA,
    NIVEL_ESTANDAR,
)
from app.models.miembro import (
    CATEGORIA_ACTIVO,
    CATEGORIA_MEMBRESIA,
    CONDICION_EXENTO,
    CONDICION_NORMAL,
)
from app.repositories import membresia as repo_membresia
from app.repositories import miembro as repo_miembro
from app.services import membresias as servicio_membresias


def test_catalogo_de_cuotas_rn01(niveles):
    """Matrícula 5.000 única; Estándar 5.000 y Activa 15.000 mensuales (CA-02)."""
    assert niveles["matricula"].monto_clp == 5_000
    assert niveles["matricula"].tipo == "unico"
    assert niveles["estandar"].monto_clp == 5_000
    assert niveles["estandar"].tipo == "mensual"
    assert niveles["activa"].monto_clp == 15_000
    assert niveles["activa"].tipo == "mensual"


def test_genera_cuotas_solo_activos_y_no_exentos(
    db, niveles, miembro_factory
):
    """La generación mensual cobra a activos no exentos, según su categoría."""
    activo = miembro_factory()
    pendiente = miembro_factory(activo=False)
    exento = miembro_factory(exento=True)
    membresia = miembro_factory(categoria=CATEGORIA_MEMBRESIA)

    creadas = servicio_membresias.generar_cuotas_del_periodo(db, 2026, 7)

    assert {cuota.miembro_id for cuota in creadas} == {activo.id, membresia.id}
    assert repo_membresia.obtener_cuota(
        db, activo.id, 2026, 7, niveles[NIVEL_ACTIVA].id
    ).monto_clp == 15_000
    assert repo_membresia.obtener_cuota(
        db, membresia.id, 2026, 7, niveles[NIVEL_ESTANDAR].id
    ).monto_clp == 5_000
    assert (
        repo_membresia.obtener_cuota(db, pendiente.id, 2026, 7, niveles[NIVEL_ACTIVA].id)
        is None
    )
    assert (
        repo_membresia.obtener_cuota(db, exento.id, 2026, 7, niveles[NIVEL_ACTIVA].id)
        is None
    )


def test_generacion_es_idempotente(db, niveles, miembro_factory):
    miembro_factory()
    primera = servicio_membresias.generar_cuotas_del_periodo(db, 2026, 7)
    segunda = servicio_membresias.generar_cuotas_del_periodo(db, 2026, 7)

    assert len(primera) == 1
    assert segunda == []


def test_exencion_marca_cuotas_y_excluye_del_cobro(
    db, niveles, miembro_factory, cuota_factory
):
    """CA-03: al eximir, sus cuotas quedan exentas y no se le generan cobros."""
    miembro = miembro_factory()
    cuota = cuota_factory(miembro, niveles[NIVEL_ACTIVA], 2026, 7)

    servicio_membresias.marcar_exencion(db, miembro, "Becado")

    assert miembro.condicion_especial == CONDICION_EXENTO
    assert miembro.motivo_exencion == "Becado"
    db.refresh(cuota)
    assert cuota.estado == ESTADO_EXENTA
    assert cuota.monto_pagado_clp == 0
    assert miembro not in servicio_membresias.miembros_facturables(db)

    servicio_membresias.quitar_exencion(db, miembro)
    assert miembro.condicion_especial == CONDICION_NORMAL
    assert miembro.motivo_exencion is None


def test_motivo_de_exencion_invalido(db, niveles, miembro_factory):
    miembro = miembro_factory()
    with pytest.raises(ValueError):
        servicio_membresias.marcar_exencion(db, miembro, "Otro motivo")


def test_cambio_de_categoria_registra_historial_y_ajusta_cuota(
    db, niveles, miembro_factory, cuota_factory
):
    """CA-29: Activo → Membresía deja historial y ajusta la cuota a 5.000."""
    miembro = miembro_factory(fecha_incorporacion=date.today())
    hoy = date.today()
    cuota = cuota_factory(miembro, niveles[NIVEL_ACTIVA], hoy.year, hoy.month)

    registro = servicio_membresias.cambiar_categoria(
        db, miembro, CATEGORIA_MEMBRESIA
    )

    assert miembro.categoria == CATEGORIA_MEMBRESIA
    assert registro.categoria_anterior == CATEGORIA_ACTIVO
    assert registro.categoria_nueva == CATEGORIA_MEMBRESIA

    db.refresh(cuota)
    assert cuota.nivel_cuota_id == niveles[NIVEL_ESTANDAR].id
    assert cuota.monto_clp == 5_000

    historial = repo_miembro.listar_historial(db, miembro.id)
    assert len(historial) == 1
    assert historial[0].id == registro.id


def test_cambio_de_categoria_no_ajusta_cuotas_pagadas(
    db, niveles, miembro_factory, cuota_factory
):
    miembro = miembro_factory(fecha_incorporacion=date.today())
    hoy = date.today()
    pagada = cuota_factory(
        miembro,
        niveles[NIVEL_ACTIVA],
        hoy.year,
        hoy.month,
        estado=ESTADO_PAGADA,
        pagado=15_000,
    )

    servicio_membresias.cambiar_categoria(db, miembro, CATEGORIA_MEMBRESIA)

    db.refresh(pagada)
    assert pagada.nivel_cuota_id == niveles[NIVEL_ACTIVA].id
    assert pagada.monto_clp == 15_000
    assert pagada.estado == ESTADO_PAGADA


def test_categoria_invalida_o_repetida(db, niveles, miembro_factory):
    miembro = miembro_factory()
    with pytest.raises(ValueError):
        servicio_membresias.cambiar_categoria(db, miembro, "otra")
    with pytest.raises(ValueError):
        servicio_membresias.cambiar_categoria(db, miembro, CATEGORIA_ACTIVO)


def test_cuota_pendiente_se_mantiene_pendiente_al_generar(
    db, niveles, miembro_factory
):
    """La generación no duplica una cuota ya existente del periodo."""
    miembro_factory()
    creadas = servicio_membresias.generar_cuotas_del_periodo(db, 2026, 7)
    assert len(creadas) == 1
    assert creadas[0].estado == ESTADO_PENDIENTE
