"""Reglas de membresías: catálogo, generación de cuotas, categoría y exenciones.

Cubre F-06, F-09, F-10 (sección 6 del PLAN): montos del catálogo, generación de
cuotas del periodo para miembros activos y no exentos, cambio de categoría con
historial, exenciones y la regla del corte al día 5.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from app.models.membresia import (
    CuotaMensual,
    NivelCuota,
)
from app.models.miembro import (
    ACTIVACION_ACTIVO,
    CATEGORIA_ACTIVO,
    CATEGORIA_MEMBRESIA,
    CONDICION_EXENTO,
    CONDICION_NORMAL,
    MOTIVOS_EXENCION,
    HistorialCategoria,
    Miembro,
)
from app.models.pago import Pago
from app.repositories import membresia as repo_membresia
from app.repositories import miembro as repo_miembro
from app.services import activacion as servicio_activacion

CATEGORIAS_VALIDAS: tuple[str, ...] = (CATEGORIA_ACTIVO, CATEGORIA_MEMBRESIA)

# Corte de cobro: un pago posterior a este día del mes se imputa al ciclo siguiente (RN-03).
DIA_CORTE = 5


def monto_cuota(nivel: NivelCuota) -> int:
    """Devuelve el monto en CLP de un nivel del catálogo (RN-01)."""
    return int(nivel.monto_clp)


def crear_miembro(db: Session, **datos: Any) -> Miembro:
    """Crea la ficha del miembro y genera su obligación inicial (F-01, Flujo 1).

    La **fecha de incorporación** se captura automáticamente como la fecha de alta
    en el sistema (D-3, RN-14). El miembro queda **pendiente** hasta completar el
    pago inicial (RN-02) y el sistema registra la obligación: Matrícula + la cuota
    de la categoría elegida.
    """
    datos.setdefault("fecha_incorporacion", date.today())
    miembro = repo_miembro.crear(db, **datos)
    db.flush()
    servicio_activacion.registrar_obligacion_inicial(db, miembro)
    db.commit()
    db.refresh(miembro)
    return miembro


def editar_miembro(db: Session, miembro: Miembro, **datos: Any) -> Miembro:
    """Actualiza los datos de la ficha ampliada sin tocar el historial (T5.3)."""
    for campo, valor in datos.items():
        setattr(miembro, campo, valor)
    db.add(miembro)
    db.commit()
    db.refresh(miembro)
    return miembro


def miembros_facturables(db: Session) -> list[Miembro]:
    """Miembros que entran al ciclo de cobro: activos y no exentos (F-10, RN-05)."""
    return [
        miembro
        for miembro in repo_miembro.listar(db)
        if miembro.situacion_activacion == ACTIVACION_ACTIVO and not miembro.esta_exento
    ]


def generar_cuotas_del_periodo(
    db: Session, anio: int, mes: int
) -> list[CuotaMensual]:
    """Crea la cuota del periodo para los miembros activos y no exentos (F-10).

    El monto corresponde a la categoría del miembro (Activa o Estándar; RN-01) y la
    operación es idempotente: no duplica una cuota ya existente de ese periodo.
    """
    creadas: list[CuotaMensual] = []
    for miembro in miembros_facturables(db):
        nivel = repo_membresia.nivel_de_categoria(db, miembro.categoria)
        if nivel is None:
            continue
        if (
            repo_membresia.obtener_cuota(db, miembro.id, anio, mes, nivel.id)
            is not None
        ):
            continue
        creadas.append(
            repo_membresia.crear_cuota(
                db,
                miembro_id=miembro.id,
                anio=anio,
                mes=mes,
                nivel_cuota_id=nivel.id,
                monto_clp=monto_cuota(nivel),
            )
        )
    db.commit()
    return creadas


def cambiar_categoria(
    db: Session,
    miembro: Miembro,
    nueva_categoria: str,
    usuario: Any | None = None,
) -> HistorialCategoria:
    """Cambia la categoría, registra el historial y ajusta las cuotas (RN-25, D-26).

    Se ajustan las cuotas mensuales no pagadas del periodo en curso en adelante y,
    si el miembro aún no está activo, también la cuota de su categoría elegida
    (obligación inicial), tal como exige la activación según D-11.
    """
    if nueva_categoria not in CATEGORIAS_VALIDAS:
        raise ValueError("La categoría debe ser Activo o Membresía.")
    if nueva_categoria == miembro.categoria:
        raise ValueError("El miembro ya pertenece a esa categoría.")

    nivel = repo_membresia.nivel_de_categoria(db, nueva_categoria)
    if nivel is None:
        raise ValueError("Falta el nivel de cuota de la nueva categoría.")

    anterior = miembro.categoria
    miembro.categoria = nueva_categoria
    db.add(miembro)

    registro = repo_miembro.crear_historial(
        db,
        miembro_id=miembro.id,
        categoria_anterior=anterior,
        categoria_nueva=nueva_categoria,
        usuario_id=getattr(usuario, "id", None),
    )

    hoy = date.today()
    desde = (hoy.year, hoy.month)
    if miembro.situacion_activacion != ACTIVACION_ACTIVO:
        desde = (miembro.fecha_incorporacion.year, miembro.fecha_incorporacion.month)
    for cuota in repo_membresia.cuotas_ajustables_desde(db, miembro.id, *desde):
        cuota.nivel_cuota_id = nivel.id
        cuota.monto_clp = monto_cuota(nivel)
        db.add(cuota)

    db.commit()
    db.refresh(miembro)
    db.refresh(registro)
    return registro


def marcar_exencion(db: Session, miembro: Miembro, motivo: str) -> Miembro:
    """Exime al miembro de cobros y avisos, y deja sus cuotas como exentas (RN-05).

    Los motivos admitidos son becado, invitado/influencer y retirado (F-09, CA-03).
    """
    if motivo not in MOTIVOS_EXENCION:
        raise ValueError("El motivo de exención no es válido.")
    miembro.condicion_especial = CONDICION_EXENTO
    miembro.motivo_exencion = motivo
    db.add(miembro)
    for cuota in repo_membresia.cuotas_de_miembro(db, miembro.id):
        if cuota.estado in repo_membresia.ESTADOS_AJUSTABLES:
            repo_membresia.marcar_exenta(db, cuota)
    db.commit()
    db.refresh(miembro)
    return miembro


def quitar_exencion(db: Session, miembro: Miembro) -> Miembro:
    """Devuelve al miembro a la condición normal; vuelve a entrar al ciclo (RN-05)."""
    miembro.condicion_especial = CONDICION_NORMAL
    miembro.motivo_exencion = None
    db.add(miembro)
    db.commit()
    db.refresh(miembro)
    return miembro


def periodo_imputado(fecha_pago: date, anio: int, mes: int) -> tuple[int, int]:
    """Periodo al que se imputa un pago: el siguiente ciclo si es posterior al día 5.

    Regla del corte de cobro (RN-03, F-10).
    """
    if fecha_pago.day > DIA_CORTE:
        total = anio * 12 + (mes - 1) + 1
        return total // 12, total % 12 + 1
    return anio, mes


def aplicar_corte_dia_5(
    db: Session, pago: Pago, cuota: CuotaMensual
) -> CuotaMensual | None:
    """Devuelve la cuota del ciclo al que corresponde imputar el pago (RN-03, T5.9).

    Si el pago se realizó hasta el día 5, se mantiene el ciclo indicado; si fue
    posterior, se devuelve la cuota del ciclo siguiente (o ``None`` si no existe).
    """
    anio, mes = periodo_imputado(pago.fecha_pago, cuota.anio, cuota.mes)
    if (anio, mes) == (cuota.anio, cuota.mes):
        return cuota
    return repo_membresia.obtener_cuota(
        db, cuota.miembro_id, anio, mes, cuota.nivel_cuota_id
    )
