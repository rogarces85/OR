"""T8.10 · Integración: compra → cargo a alumno sin alterar la mora (RN-23)."""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import select

from app.models.compras import ESTADO_CARGO_PAGADO, ESTADO_CARGO_PENDIENTE
from app.models.finanzas import TIPO_COMPRA, Egreso
from app.models.membresia import NIVEL_ACTIVA
from app.repositories import compras as repo_compras
from app.repositories import membresia as repo_membresia
from app.services import compras as servicio_compras
from app.services.morosidad import calcular_morosidad

REFERENCIA = date(2026, 6, 15)


def _cuotas_del_miembro(db, miembro) -> list:
    return repo_membresia.cuotas_mensuales_de_miembro(db, miembro.id)


def test_compra_genera_cargos_sin_alterar_morosidad(
    db, niveles, categorias, miembro_factory, cuota_factory
):
    miembro = miembro_factory()
    activa = niveles[NIVEL_ACTIVA]
    for mes in range(1, 6):
        cuota_factory(miembro, activa, 2026, mes)

    antes = calcular_morosidad(miembro, _cuotas_del_miembro(db, miembro), REFERENCIA)
    assert antes.meses_deuda == 5

    compra = servicio_compras.registrar_compra(
        db,
        descripcion="Polerones de entrenamiento",
        proveedor="Textiles Osorno",
        items=[
            {"descripcion": "Polerón", "precio_unitario_clp": 25_000, "cantidad": 4}
        ],
        fecha=date(2026, 6, 10),
    )

    assert compra.monto_total_clp == 100_000
    items = repo_compras.items_de_compra(db, compra.id)
    assert len(items) == 1

    egreso = db.scalar(select(Egreso).where(Egreso.concepto == compra.descripcion))
    assert egreso is not None
    assert egreso.tipo == TIPO_COMPRA
    assert egreso.monto_clp == 100_000

    cargos = servicio_compras.generar_cargos_alumnos(
        db,
        compra=compra,
        asignaciones=[
            {
                "compra_item_id": items[0].id,
                "miembro_id": miembro.id,
                "cantidad": 1,
            }
        ],
        fecha=date(2026, 6, 11),
    )

    assert len(cargos) == 1
    cargo = cargos[0]
    assert cargo.monto_clp == 25_000
    assert cargo.estado == ESTADO_CARGO_PENDIENTE

    despues = calcular_morosidad(
        miembro, _cuotas_del_miembro(db, miembro), REFERENCIA
    )
    assert despues == antes

    # Saldar el cargo tampoco altera la morosidad de cuotas.
    pago = servicio_compras.saldar_cargo(db, cargo=cargo)
    assert cargo.estado == ESTADO_CARGO_PAGADO
    assert cargo.pago_id == pago.id
    assert pago.monto_clp == 25_000

    final = calcular_morosidad(miembro, _cuotas_del_miembro(db, miembro), REFERENCIA)
    assert final == antes


def test_no_permite_item_de_otra_compra(db, niveles, categorias, miembro_factory):
    miembro = miembro_factory()
    compra_a = servicio_compras.registrar_compra(
        db,
        descripcion="Compra A",
        items=[{"descripcion": "Item A", "precio_unitario_clp": 1_000, "cantidad": 1}],
    )
    compra_b = servicio_compras.registrar_compra(
        db,
        descripcion="Compra B",
        items=[{"descripcion": "Item B", "precio_unitario_clp": 2_000, "cantidad": 1}],
    )
    item_b = repo_compras.items_de_compra(db, compra_b.id)[0]

    with pytest.raises(servicio_compras.ErrorCompras):
        servicio_compras.generar_cargos_alumnos(
            db,
            compra=compra_a,
            asignaciones=[
                {"compra_item_id": item_b.id, "miembro_id": miembro.id, "cantidad": 1}
            ],
        )
