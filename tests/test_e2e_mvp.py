"""T10.5 · Recorrido end-to-end del MVP.

Ejercita el flujo completo sobre una base aislada (SQLite en memoria por
defecto): alta → activación → pago → mora → negociación → egresos → compras →
reportes → landing.  Complementa las pruebas unitarias y de integración de las
fases anteriores con un recorrido único y verificable.
"""

from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_db
from app.main import app
from app.models.compras import ESTADO_CARGO_PAGADO
from app.models.membresia import NIVEL_ACTIVA
from app.models.miembro import ACTIVACION_ACTIVO, ACTIVACION_PENDIENTE
from app.repositories import compras as repo_compras
from app.repositories import membresia as repo_membresia
from app.services import compras as servicio_compras
from app.services import exportacion as servicio_exportacion
from app.services import finanzas as servicio_finanzas
from app.services import membresias as servicio_membresias
from app.services import morosidad as servicio_morosidad
from app.services import negociacion as servicio_negociacion
from app.services import pagos as servicio_pagos
from app.services import reportes as servicio_reportes


@pytest.fixture()
def cliente(db):
    """TestClient con la sesión de prueba inyectada (landing pública)."""

    def _get_db():
        yield db

    app.dependency_overrides[get_db] = _get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _periodo_desplazado(anio: int, mes: int, atras: int) -> tuple[int, int]:
    """Devuelve el periodo ``atras`` meses antes de (año, mes)."""
    total = int(anio) * 12 + (int(mes) - 1) - atras
    return total // 12, total % 12 + 1


def test_recorrido_completo_del_mvp(db, niveles, categorias, cliente):
    """Un solo recorrido cubre las funcionalidades del MVP sin errores.

    La fecha de incorporación se fija ocho meses atrás para que, tras activar
    al miembro, existan siete cuotas cerradas impagas y sea elegible para una
    negociación (> 6 meses, RN-22). Las fechas se calculan a partir de hoy para
    que la prueba no dependa de un mes concreto del calendario.
    """
    hoy = date.today()
    anio_alta, mes_alta = _periodo_desplazado(hoy.year, hoy.month, 8)
    fecha_alta = date(anio_alta, mes_alta, 1)
    fecha_pago_inicial = date(anio_alta, mes_alta, 3)  # antes del corte del día 5

    # 1. Alta: ficha, obligación inicial (Matrícula + cuota) y estado pendiente.
    miembro = servicio_membresias.crear_miembro(
        db,
        nombre_completo="Recorrido E2E",
        email="recorrido.e2e@example.com",
        telefono="+56 9 1111 2222",
        rut="11.111.111-1",
        fecha_nacimiento=date(1995, 5, 10),
        direccion="Av. Siempre Viva 742",
        contacto_emergencia="Contacto E2E · +56 9 3333 4444",
        categoria="activo",
        fecha_incorporacion=fecha_alta,
    )
    assert miembro.situacion_activacion == ACTIVACION_PENDIENTE
    obligacion = repo_membresia.cuotas_de_miembro(db, miembro.id)
    assert len(obligacion) == 2
    assert {cuota.monto_clp for cuota in obligacion} == {5_000, 15_000}

    # 2. Pago parcial: no activa; el pago restante completa y activa (CA-01).
    parcial = servicio_pagos.registrar_pago(
        db,
        miembro=miembro,
        monto_clp=10_000,
        anio=anio_alta,
        meses=[mes_alta],
        fecha_pago=fecha_pago_inicial,
        observaciones="Primera parte del pago inicial",
    )
    assert parcial.activado is False
    db.refresh(miembro)
    assert miembro.situacion_activacion == ACTIVACION_PENDIENTE

    completo = servicio_pagos.registrar_pago(
        db,
        miembro=miembro,
        monto_clp=10_000,
        anio=anio_alta,
        meses=[mes_alta],
        fecha_pago=fecha_pago_inicial,
    )
    assert completo.activado is True
    db.refresh(miembro)
    assert miembro.situacion_activacion == ACTIVACION_ACTIVO

    # 3. Ciclo mensual: se generan las cuotas cerradas posteriores al alta.
    total_alta = anio_alta * 12 + (mes_alta - 1)
    total_actual = hoy.year * 12 + (hoy.month - 1)
    for offset in range(1, total_actual - total_alta):
        total = total_alta + offset
        servicio_membresias.generar_cuotas_del_periodo(
            db, total // 12, total % 12 + 1
        )

    # 4. Mora: siete meses cerrados sin pago → rojo y elegible para negociar.
    cuotas = repo_membresia.cuotas_mensuales_de_miembro(db, miembro.id)
    info = servicio_morosidad.calcular_morosidad(miembro, cuotas)
    assert info.meses_deuda == 7
    assert info.monto_deuda_clp == 105_000
    assert info.color == servicio_morosidad.COLOR_ROJO
    assert servicio_negociacion.puede_negociar(info) is True

    # 5. Negociación: propuesta, aceptación (deja de contar para el color) y pago.
    negociacion = servicio_negociacion.crear_negociacion(
        db, miembro=miembro, info=info, descuento_pct=20
    )
    assert negociacion.monto_negociado_clp == 84_000
    info_antes = servicio_morosidad.calcular_morosidad(miembro, cuotas)
    assert info_antes.color == servicio_morosidad.COLOR_ROJO

    servicio_negociacion.aceptar_negociacion(db, negociacion)
    excluida = repo_membresia.deuda_negociada_clp(db, miembro.id)
    info_despues = servicio_morosidad.calcular_morosidad(
        miembro, cuotas, deuda_excluida_clp=excluida
    )
    assert info_despues.color == servicio_morosidad.COLOR_VERDE

    pago_negociacion = servicio_negociacion.registrar_pago_negociacion(
        db, negociacion=negociacion
    )
    assert pago_negociacion.monto_clp == 84_000
    assert negociacion.estado == servicio_negociacion.ESTADO_NEGOCIACION_PAGADA

    # 6. Finanzas: egreso, activo, gasto fijo y categoría personalizada.
    servicio_finanzas.registrar_egreso(
        db,
        monto_clp=30_000,
        concepto="Arriendo sede E2E",
        categoria_id=categorias["Transferencias"].id,
        fecha=hoy,
    )
    activo = servicio_finanzas.registrar_activo(
        db,
        costo_clp=50_000,
        descripcion="Arnés de entrenamiento E2E",
        miembro_responsable_id=miembro.id,
        fecha=hoy,
    )
    assert activo.miembro_responsable_id == miembro.id

    gasto_fijo = servicio_finanzas.registrar_gasto_fijo(
        db,
        concepto="Mantención cuenta corriente E2E",
        monto_clp=20_000,
        fecha=hoy,
    )
    assert gasto_fijo.monto_clp == 20_000

    categoria_custom = servicio_finanzas.crear_categoria_egreso(
        db, nombre="Arriendo E2E"
    )
    servicio_finanzas.registrar_egreso(
        db,
        monto_clp=10_000,
        concepto="Bodega E2E",
        categoria_id=categoria_custom.id,
        fecha=hoy,
    )

    # 7. Compras: compra del club, cargo separado y saldo del cargo (RN-23).
    compra = servicio_compras.registrar_compra(
        db,
        descripcion="Compra de polerones E2E",
        proveedor="Proveedor E2E",
        items=[
            {"descripcion": "Polerón", "precio_unitario_clp": 25_000, "cantidad": 4}
        ],
        fecha=hoy,
    )
    item = repo_compras.items_de_compra(db, compra.id)[0]
    cargos = servicio_compras.generar_cargos_alumnos(
        db,
        compra=compra,
        asignaciones=[
            {"compra_item_id": item.id, "miembro_id": miembro.id, "cantidad": 1}
        ],
        fecha=hoy,
    )
    assert len(cargos) == 1
    cargo = cargos[0]
    assert cargo.monto_clp == 25_000

    antes_del_cargo = servicio_morosidad.calcular_morosidad(
        miembro, cuotas, deuda_excluida_clp=excluida
    )
    servicio_compras.saldar_cargo(db, cargo=cargo)
    assert cargo.estado == ESTADO_CARGO_PAGADO
    despues_del_cargo = servicio_morosidad.calcular_morosidad(
        miembro, cuotas, deuda_excluida_clp=excluida
    )
    assert despues_del_cargo == antes_del_cargo

    # 8. Reportes: consolidado, XLSX e informe calendario en PDF.
    reporte = servicio_reportes.reporte_consolidado(
        db, desde=fecha_alta, hasta=hoy
    )
    assert reporte.total_ingresos_clp == 129_000
    assert reporte.total_egresos_clp == 210_000
    assert reporte.neto_clp == -81_000
    assert not reporte.sin_movimientos

    xlsx = servicio_exportacion.exportar_reporte_xlsx(reporte)
    assert xlsx.startswith(b"PK")

    informe = servicio_reportes.informe_calendario(db, miembro, anio_alta)
    pdf = servicio_exportacion.exportar_informe_pdf(informe)
    assert pdf.startswith(b"%PDF")

    # 9. Landing pública integrada.
    respuesta = cliente.get("/")
    assert respuesta.status_code == 200
    assert "Osorno Runners" in respuesta.text

    # 10. Fecha de incorporación automática para un alta sin fecha (RN-14).
    sin_fecha = servicio_membresias.crear_miembro(
        db,
        nombre_completo="Alta sin fecha E2E",
        email="sin.fecha.e2e@example.com",
        categoria="membresia",
    )
    assert sin_fecha.fecha_incorporacion == date.today()
    assert repo_membresia.nivel_de_categoria(db, sin_fecha.categoria).codigo == (
        "estandar"
    )
    assert niveles[NIVEL_ACTIVA].monto_clp == 15_000
