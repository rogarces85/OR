"""Finanzas: categorías, egresos, activos, gastos fijos y reportes.

Cubre CA-06, CA-07, CA-08, CA-09 y CA-10 (F-15 a F-19).
"""

from __future__ import annotations

from datetime import date

import pytest

from app.models.finanzas import (
    TIPO_ACTIVO,
    TIPO_GASTO_FIJO,
    TIPO_GENERAL,
)
from app.models.membresia import NIVEL_ACTIVA, NIVEL_ESTANDAR
from app.models.miembro import CATEGORIA_MEMBRESIA
from app.repositories import finanzas as repo_finanzas
from app.repositories import pago as repo_pago
from app.services import finanzas as servicio_finanzas
from app.services import reportes as servicio_reportes


def test_egreso_con_categoria_base_y_personalizada(db, categorias):
    """CA-07: se registra un egreso con categoría base o personalizada."""
    base = servicio_finanzas.registrar_egreso(
        db,
        monto_clp=12_000,
        concepto="Transferencia a proveedor",
        categoria_id=categorias["Transferencias"].id,
        fecha=date(2026, 7, 1),
    )
    assert base.tipo == TIPO_GENERAL
    assert base.categoria.nombre == "Transferencias"

    propia = servicio_finanzas.crear_categoria_egreso(db, nombre="Arriendo")
    egreso = servicio_finanzas.registrar_egreso(
        db,
        monto_clp=50_000,
        concepto="Arriendo de sede",
        categoria_id=propia.id,
        fecha=date(2026, 7, 2),
    )
    assert egreso.categoria_egreso_id == propia.id
    assert propia.es_base is False


def test_categoria_personalizada_duplicada_o_corta(db, categorias):
    with pytest.raises(servicio_finanzas.ErrorFinanzas):
        servicio_finanzas.crear_categoria_egreso(db, nombre="AB")
    servicio_finanzas.crear_categoria_egreso(db, nombre="Arriendo")
    with pytest.raises(servicio_finanzas.ErrorFinanzas):
        servicio_finanzas.crear_categoria_egreso(db, nombre="Arriendo")


def test_egreso_invalido(db, categorias):
    with pytest.raises(servicio_finanzas.ErrorFinanzas):
        servicio_finanzas.registrar_egreso(
            db, monto_clp=0, concepto="X", categoria_id=categorias["Otros"].id
        )
    with pytest.raises(servicio_finanzas.ErrorFinanzas):
        servicio_finanzas.registrar_egreso(
            db, monto_clp=1_000, concepto="  ", categoria_id=categorias["Otros"].id
        )
    with pytest.raises(servicio_finanzas.ErrorFinanzas):
        servicio_finanzas.registrar_egreso(
            db, monto_clp=1_000, concepto="X", categoria_id=999_999
        )


def test_categoria_inactiva_no_se_puede_usar(db, categorias):
    categoria = categorias["Otros"]
    servicio_finanzas.cambiar_estado_categoria(db, categoria, activo=False)
    with pytest.raises(servicio_finanzas.ErrorFinanzas):
        servicio_finanzas.registrar_egreso(
            db, monto_clp=1_000, concepto="X", categoria_id=categoria.id
        )


def test_registro_de_activo_con_responsable(
    db, categorias, miembro_factory
):
    """CA-08: el activo guarda costo y miembro encargado."""
    encargado = miembro_factory()
    activo = servicio_finanzas.registrar_activo(
        db,
        costo_clp=250_000,
        descripcion="Compra de arcos de entrenamiento",
        miembro_responsable_id=encargado.id,
        fecha=date(2026, 7, 3),
    )

    assert activo.tipo == TIPO_ACTIVO
    assert activo.monto_clp == 250_000
    assert activo.miembro_responsable_id == encargado.id
    assert activo.categoria.nombre == "Activos"


def test_registro_de_gasto_fijo(db, categorias):
    """CA-09: el gasto fijo se refleja como egreso recurrente."""
    gasto = servicio_finanzas.registrar_gasto_fijo(
        db, concepto="Internet de la sede", monto_clp=25_000, fecha=date(2026, 7, 4)
    )

    assert gasto.monto_clp == 25_000
    egresos = repo_finanzas.listar_egresos(db)
    assert len(egresos) == 1
    assert egresos[0].tipo == TIPO_GASTO_FIJO
    assert egresos[0].concepto == "Internet de la sede"


def test_filtros_de_egresos(db, categorias):
    servicio_finanzas.registrar_egreso(
        db,
        monto_clp=10_000,
        concepto="Egreso julio",
        categoria_id=categorias["Transferencias"].id,
        fecha=date(2026, 7, 10),
    )
    servicio_finanzas.registrar_egreso(
        db,
        monto_clp=20_000,
        concepto="Egreso agosto",
        categoria_id=categorias["Otros"].id,
        fecha=date(2026, 8, 10),
    )

    julio = servicio_finanzas.listar_egresos(
        db, desde=date(2026, 7, 1), hasta=date(2026, 7, 31)
    )
    assert [egreso.concepto for egreso in julio] == ["Egreso julio"]

    otros = servicio_finanzas.listar_egresos(
        db, categoria_id=categorias["Otros"].id
    )
    assert [egreso.concepto for egreso in otros] == ["Egreso agosto"]


def test_filtros_de_ingresos_por_tipo_y_estado(
    db, niveles, miembro_factory, cuota_factory
):
    """CA-06: filtros coherentes por tipo de cuota y estado del usuario."""
    activo = miembro_factory()
    apoyo = miembro_factory(categoria=CATEGORIA_MEMBRESIA)
    pendiente = miembro_factory(activo=False)

    cuota_activa = cuota_factory(activo, niveles[NIVEL_ACTIVA], 2026, 7)
    cuota_estandar = cuota_factory(apoyo, niveles[NIVEL_ESTANDAR], 2026, 7)

    for indice, (miembro, cuota, monto) in enumerate(
        [(activo, cuota_activa, 15_000), (apoyo, cuota_estandar, 5_000)]
    ):
        pago = repo_pago.crear(
            db,
            miembro_id=miembro.id,
            monto_clp=monto,
            fecha_pago=date(2026, 7, 5 + indice),
        )
        db.flush()
        repo_pago.imputar(db, pago_id=pago.id, cuota_id=cuota.id, monto_clp=monto)

    # Un miembro pendiente sin cuotas no debe aparecer en el filtro de activos.
    assert pendiente.situacion_activacion == "pendiente"
    db.commit()

    activas = servicio_finanzas.listar_ingresos(db, nivel_codigo=NIVEL_ACTIVA)
    assert [pago.monto_clp for pago in activas] == [15_000]

    estandares = servicio_finanzas.listar_ingresos(db, nivel_codigo=NIVEL_ESTANDAR)
    assert [pago.monto_clp for pago in estandares] == [5_000]

    de_activos = servicio_finanzas.listar_ingresos(db, situacion="activo")
    assert [pago.monto_clp for pago in de_activos] == [5_000, 15_000]

    sin_pendientes = servicio_finanzas.listar_ingresos(db, situacion="pendiente")
    assert sin_pendientes == []


def test_reporte_consolidado_suma_movimientos(
    db, categorias, miembro_factory
):
    """CA-10: los totales coinciden con la suma de los movimientos del periodo."""
    miembro = miembro_factory()
    repo_pago.crear(
        db,
        miembro_id=miembro.id,
        monto_clp=30_000,
        fecha_pago=date(2026, 7, 5),
    )
    repo_pago.crear(
        db,
        miembro_id=miembro.id,
        monto_clp=10_000,
        fecha_pago=date(2026, 8, 5),
    )
    repo_finanzas.crear_egreso(
        db,
        monto_clp=12_000,
        concepto="Egreso julio",
        categoria_egreso_id=categorias["Otros"].id,
        fecha=date(2026, 7, 8),
    )
    db.commit()

    reporte = servicio_reportes.reporte_consolidado(
        db, desde=date(2026, 7, 1), hasta=date(2026, 7, 31)
    )

    assert reporte.total_ingresos_clp == 30_000
    assert reporte.total_egresos_clp == 12_000
    assert reporte.neto_clp == 18_000
    assert reporte.sin_movimientos is False


def test_reporte_sin_movimientos(db, categorias):
    reporte = servicio_reportes.reporte_consolidado(
        db, desde=date(2026, 9, 1), hasta=date(2026, 9, 30)
    )
    assert reporte.sin_movimientos is True
    assert reporte.neto_clp == 0
