"""T8.2 · Activación de la membresía (RN-02, CA-01)."""

from __future__ import annotations

from datetime import date

import pytest

from app.models.membresia import (
    ESTADO_PAGADA,
    ESTADO_PENDIENTE,
    NIVEL_ACTIVA,
    NIVEL_MATRICULA,
)
from app.models.miembro import ACTIVACION_ACTIVO, ACTIVACION_PENDIENTE
from app.repositories import membresia as repo_membresia
from app.services import activacion as servicio_activacion
from app.services import membresias as servicio_membresias
from app.services import pagos as servicio_pagos


@pytest.fixture()
def miembro_pendiente(db, niveles):
    """Alta real de un miembro: crea la obligación Matrícula + cuota de categoría."""
    return servicio_membresias.crear_miembro(
        db,
        nombre_completo="Nuevo Alumno",
        email="nuevo.alumno@example.com",
        categoria="activo",
        fecha_incorporacion=date(2026, 1, 10),
    )


def test_alta_genera_obligacion_inicial(miembro_pendiente, db, niveles):
    """El alta deja al miembro pendiente con Matrícula + cuota de su categoría."""
    miembro = miembro_pendiente
    assert miembro.situacion_activacion == ACTIVACION_PENDIENTE

    cuotas = repo_membresia.cuotas_de_miembro(db, miembro.id)
    assert len(cuotas) == 2
    assert {cuota.nivel.codigo for cuota in cuotas} == {
        NIVEL_MATRICULA,
        NIVEL_ACTIVA,
    }

    estado = servicio_activacion.evaluar_activacion(db, miembro)
    assert estado.requerido_clp == 20_000
    assert estado.pagado_clp == 0
    assert estado.saldo_clp == 20_000
    assert estado.completo is False


def test_pago_parcial_mantiene_pendiente(miembro_pendiente, db, niveles):
    """Con pago parcial el miembro sigue pendiente (RN-02)."""
    miembro = miembro_pendiente
    resultado = servicio_pagos.registrar_pago(
        db,
        miembro=miembro,
        monto_clp=5_000,
        anio=2026,
        meses=[1],
        fecha_pago=date(2026, 1, 10),
    )

    assert resultado.activado is False
    db.refresh(miembro)
    assert miembro.situacion_activacion == ACTIVACION_PENDIENTE
    assert servicio_activacion.evaluar_activacion(db, miembro).completo is False


def test_pago_completo_activa(miembro_pendiente, db, niveles):
    """Matrícula + cuota de la categoría completas activan al miembro (CA-01)."""
    miembro = miembro_pendiente
    resultado = servicio_pagos.registrar_pago(
        db,
        miembro=miembro,
        monto_clp=20_000,
        anio=2026,
        meses=[1],
        fecha_pago=date(2026, 1, 10),
    )

    assert resultado.activado is True
    db.refresh(miembro)
    assert miembro.situacion_activacion == ACTIVACION_ACTIVO
    assert servicio_activacion.evaluar_activacion(db, miembro).completo is True

    cuotas = repo_membresia.cuotas_de_miembro(db, miembro.id)
    assert all(cuota.estado == ESTADO_PAGADA for cuota in cuotas)
    assert all(cuota.monto_pagado_clp == cuota.monto_clp for cuota in cuotas)


def test_pagar_solo_la_matricula_no_activa(miembro_pendiente, db, niveles):
    """Pagar únicamente la Matrícula no alcanza para activar (RN-02)."""
    miembro = miembro_pendiente
    servicio_pagos.registrar_pago(
        db,
        miembro=miembro,
        monto_clp=5_000,
        anio=2026,
        meses=[1],
        fecha_pago=date(2026, 1, 10),
    )

    matricula = repo_membresia.obtener_cuota(
        db, miembro.id, 2026, 1, niveles[NIVEL_MATRICULA].id
    )
    cuota_activa = repo_membresia.obtener_cuota(
        db, miembro.id, 2026, 1, niveles[NIVEL_ACTIVA].id
    )
    assert matricula.estado == ESTADO_PAGADA
    assert cuota_activa.estado == ESTADO_PENDIENTE
    assert miembro.situacion_activacion == ACTIVACION_PENDIENTE


def test_miembro_antiguo_matriculado_no_genera_matricula(db, niveles):
    """Un miembro marcado como matriculado no vuelve a generar la Matrícula."""
    miembro = servicio_membresias.crear_miembro(
        db,
        nombre_completo="Antiguo Matriculado",
        email="antiguo.matriculado@example.com",
        categoria="activo",
        fecha_incorporacion=date(2026, 1, 10),
        matriculado=True,
    )

    cuotas = repo_membresia.cuotas_de_miembro(db, miembro.id)
    assert len(cuotas) == 1
    assert {cuota.nivel.codigo for cuota in cuotas} == {NIVEL_ACTIVA}

    estado = servicio_activacion.evaluar_activacion(db, miembro)
    assert [concepto.etiqueta for concepto in estado.conceptos] == [
        "Membresía Activa"
    ]
    assert estado.requerido_clp == 15_000


def test_matricula_se_cobra_desde_septiembre_2025(db, niveles):
    """La matrícula solo se genera desde el 01/09/2025 para miembros nuevos."""
    anterior = servicio_membresias.crear_miembro(
        db,
        nombre_completo="Ingreso Anterior",
        email="ingreso.anterior@example.com",
        categoria="activo",
        fecha_incorporacion=date(2025, 8, 31),
    )
    desde = servicio_membresias.crear_miembro(
        db,
        nombre_completo="Ingreso Septiembre",
        email="ingreso.septiembre@example.com",
        categoria="activo",
        fecha_incorporacion=date(2025, 9, 1),
    )

    assert [c.nivel.codigo for c in repo_membresia.cuotas_de_miembro(db, anterior.id)] == [
        NIVEL_ACTIVA
    ]
    assert {
        c.nivel.codigo for c in repo_membresia.cuotas_de_miembro(db, desde.id)
    } == {NIVEL_MATRICULA, NIVEL_ACTIVA}
