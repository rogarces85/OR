"""Pagos personalizados: registro, imputación y abonos.

Cubre T5.11 (formulario), T5.12 (registro atómico), T5.13 (orden de imputación
**deuda más antigua → meses/año indicados → abono**, RN-17), T5.14 (abono
automático a la siguiente cuota, RN-18) y T5.16 (listado de ingresos, F-15).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from app.core.periodos import siguiente_periodo
from app.models.membresia import (
    ESTADO_PAGADA,
    ESTADO_PARCIAL,
    CuotaMensual,
)
from app.models.miembro import ACTIVACION_ACTIVO, Miembro
from app.models.pago import (
    ESTADO_APLICADO,
    MEDIO_TRANSFERENCIA,
    MEDIOS_PAGO,
    Abono,
    ImputacionPago,
    Pago,
)
from app.repositories import membresia as repo_membresia
from app.repositories import pago as repo_pago
from app.services import activacion as servicio_activacion
from app.services import membresias as servicio_membresias

DIA_CORTE = servicio_membresias.DIA_CORTE
ORDEN_ABONO = 1000


class ErrorPago(ValueError):
    """Error de validación de un pago, con mensaje en español para el usuario."""


@dataclass
class ResultadoPago:
    """Resultado observable del registro de un pago (T5.12)."""

    pago: Pago
    imputaciones: list[ImputacionPago] = field(default_factory=list)
    monto_imputado_clp: int = 0
    abono_clp: int = 0
    activado: bool = False


# --------------------------------------------------------------------------- #
# Validaciones (CA-21, RN-19)
# --------------------------------------------------------------------------- #


def validar_pago(
    *, monto_clp: int, medio: str, anio: int, meses: list[int]
) -> None:
    """Valida la entrada del formulario de pago; lanza ``ErrorPago`` si falla."""
    if monto_clp is None or int(monto_clp) <= 0:
        raise ErrorPago("El monto debe ser un entero positivo.")
    if medio not in MEDIOS_PAGO:
        raise ErrorPago(
            "El medio de pago debe ser transferencia o efectivo (RN-19)."
        )
    if not 2000 <= int(anio) <= 2100:
        raise ErrorPago("El año indicado no es válido.")
    if not meses:
        raise ErrorPago("Selecciona al menos un mes a cubrir.")
    if len(set(meses)) != len(meses):
        raise ErrorPago("No se pueden repetir meses: la selección no es válida.")
    if any(int(mes) not in range(1, 13) for mes in meses):
        raise ErrorPago("Los meses deben estar entre 1 y 12.")


def periodo_de_cobro(fecha_pago: date, anio: int, mes: int) -> tuple[int, int]:
    """Aplica la regla de corte al día 5 (RN-03, CA-04).

    Un pago posterior al día 5, referido al **mes en curso**, se imputa al ciclo
    siguiente. Los meses anteriores o futuros indicados explícitamente no se
    desplazan (representan deuda o prepago de un ciclo concreto).
    """
    if (
        fecha_pago.day > DIA_CORTE
        and (int(anio), int(mes)) == (fecha_pago.year, fecha_pago.month)
    ):
        return siguiente_periodo(anio, mes)
    return int(anio), int(mes)


# --------------------------------------------------------------------------- #
# Registro de pago (T5.12, T5.13, T5.14)
# --------------------------------------------------------------------------- #


def _aplicar(
    db: Session,
    pago: Pago,
    cuota: CuotaMensual,
    disponible: int,
    orden: int,
) -> tuple[int, ImputacionPago | None]:
    """Aplica parte del pago a una cuota y registra la imputación."""
    aplicar = min(disponible, cuota.saldo_clp)
    if aplicar <= 0:
        return 0, None
    cuota.monto_pagado_clp = int(cuota.monto_pagado_clp) + aplicar
    cuota.estado = ESTADO_PAGADA if cuota.saldo_clp == 0 else ESTADO_PARCIAL
    db.add(cuota)
    imputacion = repo_pago.imputar(
        db, pago_id=pago.id, cuota_id=cuota.id, monto_clp=aplicar, orden=orden
    )
    return aplicar, imputacion


def registrar_pago(
    db: Session,
    *,
    miembro: Miembro,
    monto_clp: int,
    anio: int,
    meses: list[int],
    fecha_pago: date | None = None,
    medio: str = MEDIO_TRANSFERENCIA,
    observaciones: str | None = None,
    usuario: Any | None = None,
) -> ResultadoPago:
    """Registra un pago y sus imputaciones en una **única transacción** (T5.12).

    Orden de imputación (RN-17): deuda más antigua → meses/año indicados → abono.
    Si queda excedente, se genera un abono que se aplica a la siguiente cuota
    (RN-18). Si el miembro estaba **pendiente** y con este pago completa su
    obligación inicial, queda **Activo** (Flujo 1, CA-01).
    """
    fecha = fecha_pago or date.today()
    validar_pago(
        monto_clp=int(monto_clp), medio=medio, anio=anio, meses=list(meses)
    )
    if miembro.esta_exento:
        raise ErrorPago(
            "El miembro está exento (becado, invitado/influencer o retirado): "
            "no genera obligación de pago (RN-05)."
        )

    monto = int(monto_clp)
    _validar_ciclos_no_duplicados(db, miembro, fecha, anio, meses)
    try:
        pago = repo_pago.crear(
            db,
            miembro_id=miembro.id,
            monto_clp=monto,
            fecha_pago=fecha,
            medio=medio,
            observaciones=(observaciones or None),
            registrado_por=getattr(usuario, "id", None),
        )
        db.flush()

        restante = monto
        imputaciones: list[ImputacionPago] = []
        aplicadas: set[int] = set()
        orden = 0

        # 1) Deuda más antigua (incluye la obligación inicial).
        for cuota in repo_membresia.cuotas_impagas(db, miembro.id):
            if restante <= 0:
                break
            orden += 1
            aplicado, imputacion = _aplicar(db, pago, cuota, restante, orden)
            if aplicado:
                restante -= aplicado
                aplicadas.add(cuota.id)
                imputaciones.append(imputacion)  # type: ignore[arg-type]

        # 2) Meses del año indicados explícitamente.
        nivel = repo_membresia.nivel_de_categoria(db, miembro.categoria)
        for mes in sorted({int(m) for m in meses}):
            if restante <= 0 or nivel is None:
                break
            anio_cobro, mes_cobro = periodo_de_cobro(fecha, int(anio), mes)
            cuota = repo_membresia.obtener_cuota(
                db, miembro.id, anio_cobro, mes_cobro, nivel.id
            )
            if cuota is None or cuota.id in aplicadas:
                continue
            orden += 1
            aplicado, imputacion = _aplicar(db, pago, cuota, restante, orden)
            if aplicado:
                restante -= aplicado
                aplicadas.add(cuota.id)
                imputaciones.append(imputacion)  # type: ignore[arg-type]

        # 3) Abono automático (RN-18).
        abono_clp = 0
        if restante > 0:
            abono = repo_pago.crear_abono(
                db, miembro_id=miembro.id, monto_clp=restante, origen_pago_id=pago.id
            )
            db.flush()
            abono_clp = restante
            imputaciones.extend(_aplicar_abono(db, miembro, abono))

        activado = _activar_si_completo(db, miembro)
        db.commit()
        db.refresh(pago)
    except Exception:
        db.rollback()
        raise

    return ResultadoPago(
        pago=pago,
        imputaciones=imputaciones,
        monto_imputado_clp=monto - abono_clp,
        abono_clp=abono_clp,
        activado=activado,
    )


def _validar_ciclos_no_duplicados(
    db: Session, miembro: Miembro, fecha: date, anio: int, meses: list[int]
) -> None:
    """Impide registrar de nuevo un pago de un ciclo ya pagado (RN-08, CA-20).

    Solo bloquea cuando *todos* los meses indicados ya están pagados **y** el
    miembro no tiene deuda pendiente (no habría nada que imputar).
    """
    if repo_membresia.cuotas_impagas(db, miembro.id):
        return
    nivel = repo_membresia.nivel_de_categoria(db, miembro.categoria)
    if nivel is None:
        return
    for mes in {int(m) for m in meses}:
        anio_cobro, mes_cobro = periodo_de_cobro(fecha, anio, mes)
        cuota = repo_membresia.obtener_cuota(
            db, miembro.id, anio_cobro, mes_cobro, nivel.id
        )
        if cuota is None or cuota.estado != ESTADO_PAGADA:
            return
    raise ErrorPago(
        "Ya existe un pago registrado para ese ciclo. No se permite duplicarlo "
        "(RN-08)."
    )


def _activar_si_completo(db: Session, miembro: Miembro) -> bool:
    """Activa al miembro si con el pago quedó completa su obligación (CA-01)."""
    if miembro.situacion_activacion == ACTIVACION_ACTIVO:
        return False
    estado = servicio_activacion.evaluar_activacion(db, miembro)
    if estado.completo:
        miembro.situacion_activacion = ACTIVACION_ACTIVO
        db.add(miembro)
        return True
    return False


def aplicar_abono(db: Session, miembro: Miembro, abono: Abono) -> list[ImputacionPago]:
    """Aplica el saldo disponible de un abono a la siguiente cuota (RN-18)."""
    imputaciones = _aplicar_abono(db, miembro, abono)
    db.commit()
    return imputaciones


def _aplicar_abono(
    db: Session, miembro: Miembro, abono: Abono
) -> list[ImputacionPago]:
    """Consume el abono en la siguiente cuota impaga (sin confirmar transacción)."""
    imputaciones: list[ImputacionPago] = []
    if abono is None or int(abono.saldo_disponible_clp) <= 0:
        return imputaciones
    cuota = repo_membresia.siguiente_cuota_impaga(db, miembro.id)
    if cuota is None:
        return imputaciones
    aplicar = min(int(abono.saldo_disponible_clp), cuota.saldo_clp)
    if aplicar <= 0:
        return imputaciones
    cuota.monto_pagado_clp = int(cuota.monto_pagado_clp) + aplicar
    cuota.estado = ESTADO_PAGADA if cuota.saldo_clp == 0 else ESTADO_PARCIAL
    db.add(cuota)
    abono.saldo_disponible_clp = int(abono.saldo_disponible_clp) - aplicar
    if abono.saldo_disponible_clp <= 0:
        abono.estado = ESTADO_APLICADO
    db.add(abono)
    if abono.origen_pago_id:
        imputaciones.append(
            repo_pago.imputar(
                db,
                pago_id=abono.origen_pago_id,
                cuota_id=cuota.id,
                monto_clp=aplicar,
                orden=ORDEN_ABONO,
            )
        )
    return imputaciones


# --------------------------------------------------------------------------- #
# Consultas de apoyo
# --------------------------------------------------------------------------- #


def obtener_deuda(db: Session, miembro: Miembro) -> list[CuotaMensual]:
    """Lista las cuotas impagas de un miembro (deuda vigente)."""
    return repo_membresia.cuotas_impagas(db, miembro.id)


def saldo_a_favor(db: Session, miembro: Miembro) -> int:
    """Saldo a favor (abono) disponible de un miembro."""
    return repo_pago.saldo_a_favor(db, miembro.id)
