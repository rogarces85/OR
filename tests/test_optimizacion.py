"""Optimización: índices, consultas acotadas y caché de catálogos (Fase 9)."""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import event, inspect, text

from app.core import cache
from app.database import crear_indices_faltantes
from app.models.membresia import NIVEL_ACTIVA, NivelCuota
from app.repositories import configuracion as repo_configuracion
from app.repositories import finanzas as repo_finanzas
from app.repositories import membresia as repo_membresia
from app.services.morosidad import listar_miembros_con_morosidad


def _indices(db, tabla: str) -> set[str]:
    return {
        indice["name"]
        for indice in inspect(db.get_bind()).get_indexes(tabla)
        if indice.get("name")
    }


def _selects(db, accion):
    """Ejecuta ``accion`` y devuelve su resultado y las sentencias SELECT."""
    motor = db.get_bind()
    sentencias: list[str] = []

    def _registrar(_conn, _cursor, statement, _params, _context, _many):
        if statement.lstrip().upper().startswith("SELECT"):
            sentencias.append(statement)

    event.listen(motor, "before_cursor_execute", _registrar)
    try:
        resultado = accion()
    finally:
        event.remove(motor, "before_cursor_execute", _registrar)
    return resultado, sentencias


# --------------------------------------------------------------------------- #
# T9.1 · Índices
# --------------------------------------------------------------------------- #


def test_indices_de_miembro_cuota_pago_y_egreso(db):
    assert "ix_miembros_email" in _indices(db, "miembros")
    assert "ix_cuotas_mensuales_miembro_id" in _indices(db, "cuotas_mensuales")
    assert "ix_cuotas_mensuales_periodo" in _indices(db, "cuotas_mensuales")
    assert "ix_pagos_fecha_pago" in _indices(db, "pagos")
    assert "ix_egresos_fecha" in _indices(db, "egresos")


def test_indices_de_compras_y_negociaciones(db):
    assert "ix_compras_club_fecha" in _indices(db, "compras_club")
    assert "ix_cargos_alumno_fecha" in _indices(db, "cargos_alumno")
    assert "ix_negociaciones_deuda_fecha" in _indices(db, "negociaciones_deuda")


def test_crear_indices_faltantes_es_idempotente(db):
    crear_indices_faltantes(db.get_bind())
    crear_indices_faltantes(db.get_bind())
    assert "ix_cuotas_mensuales_periodo" in _indices(db, "cuotas_mensuales")


def test_consulta_de_periodo_usa_el_indice(db):
    if db.get_bind().dialect.name != "sqlite":
        pytest.skip("El plan de consulta se verifica sobre SQLite")
    plan = " ".join(
        str(fila)
        for fila in db.execute(
            text(
                "EXPLAIN QUERY PLAN "
                "SELECT * FROM cuotas_mensuales WHERE anio = 2026 AND mes = 7"
            )
        )
    )
    assert "ix_cuotas_mensuales_periodo" in plan


# --------------------------------------------------------------------------- #
# T9.2 · Consultas acotadas en listados
# --------------------------------------------------------------------------- #


def test_listado_de_miembros_no_hace_consultas_por_miembro(
    db, niveles, miembro_factory, cuota_factory
):
    """El listado con morosidad usa un número fijo de consultas (sin N+1)."""
    for indice in range(6):
        miembro = miembro_factory()
        for mes in range(1, 4):
            cuota_factory(miembro, niveles[NIVEL_ACTIVA], 2026, mes)
        if indice == 0:
            # Una negociación en propuesta también exige consultar exclusiones.
            repo_membresia.crear_negociacion(
                db,
                miembro_id=miembro.id,
                deuda_total_clp=45_000,
                descuento_pct=0,
                monto_negociado_clp=45_000,
            )
            db.commit()

    filas, sentencias = _selects(
        db, lambda: listar_miembros_con_morosidad(db, referencia=date(2026, 6, 15))
    )

    assert len(filas) == 6
    assert all(info.meses_deuda == 3 for _, info in filas)
    # miembros + cuotas + niveles (selectinload) + deudas negociadas.
    assert len(sentencias) <= 5


def test_listado_de_pagos_carga_al_miembro_sin_n_mas_uno(
    db, niveles, miembro_factory
):
    from app.repositories import pago as repo_pago

    for _ in range(5):
        miembro = miembro_factory()
        repo_pago.crear(
            db,
            miembro_id=miembro.id,
            monto_clp=15_000,
            fecha_pago=date(2026, 6, 1),
        )
    db.commit()

    pagos, sentencias = _selects(db, lambda: repo_pago.listar(db))

    assert len(pagos) == 5
    assert all(pago.miembro is not None for pago in pagos)
    assert len(sentencias) <= 2


# --------------------------------------------------------------------------- #
# T9.4 · Caché de catálogos
# --------------------------------------------------------------------------- #


def test_niveles_se_cachean(db, niveles):
    cache.limpiar()

    _, sentencias = _selects(
        db,
        lambda: (
            repo_membresia.listar_niveles(db),
            repo_membresia.listar_niveles(db),
            repo_membresia.obtener_nivel_por_codigo(db, NIVEL_ACTIVA),
            repo_membresia.obtener_nivel_por_codigo(db, NIVEL_ACTIVA),
        ),
    )

    assert len(sentencias) == 2


def test_categorias_se_cachean_y_se_invalidan_al_crear(db, categorias):
    cache.limpiar()

    _, primeras = _selects(
        db,
        lambda: (
            repo_finanzas.listar_categorias(db),
            repo_finanzas.listar_categorias(db),
        ),
    )
    assert len(primeras) == 1

    repo_finanzas.crear_categoria(db, nombre="Arriendo")
    db.commit()

    listado, segundas = _selects(
        db, lambda: repo_finanzas.listar_categorias(db)
    )
    assert len(segundas) == 1
    assert "Arriendo" in {categoria.nombre for categoria in listado}


def test_cuenta_bancaria_se_cachea(db):
    cache.limpiar()
    repo_configuracion.crear_cuenta(
        db,
        titular="Club",
        banco="Banco",
        numero_cuenta="123",
        rut="1-9",
        correo="club@example.com",
    )
    db.commit()

    cuentas, sentencias = _selects(
        db,
        lambda: (
            repo_configuracion.obtener_cuenta(db),
            repo_configuracion.obtener_cuenta(db),
        ),
    )

    assert cuentas[0].titular == "Club"
    assert cuentas[0] is cuentas[1]
    assert len(sentencias) == 1


def test_cache_se_puede_limpiar(db):
    """La caché se vacía de forma explícita (semilla y pruebas)."""
    nivel = NivelCuota(
        codigo="prueba", nombre="Prueba", monto_clp=1, tipo="mensual"
    )
    db.add(nivel)
    db.commit()

    cache.limpiar()
    primero = repo_membresia.obtener_nivel_por_codigo(db, "prueba")
    assert primero is not None

    cache.limpiar()
    segundo = repo_membresia.obtener_nivel_por_codigo(db, "prueba")
    assert segundo is not None
    assert segundo.id == primero.id
