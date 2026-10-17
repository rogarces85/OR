"""Semilla inicial del sistema (T3.9) y comando de esquema + semilla (T3.10).

Uso::

    python -m app.seed

El comando crea el esquema (si no existe) y carga la semilla de forma
**idempotente**: volver a ejecutarlo no duplica datos.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.seguridad import hash_password
from app.database import SessionLocal, crear_esquema
from app.models.compras import CargoAlumno
from app.models.finanzas import CATEGORIAS_BASE
from app.models.membresia import (
    ESTADO_EXENTA,
    ESTADO_PAGADA,
    ESTADO_PENDIENTE,
    NIVEL_ACTIVA,
    NIVEL_ESTANDAR,
    NIVEL_MATRICULA,
    TIPO_MENSUAL,
    TIPO_UNICO,
    NivelCuota,
)
from app.models.miembro import (
    ACTIVACION_ACTIVO,
    ACTIVACION_PENDIENTE,
    CATEGORIA_ACTIVO,
    CATEGORIA_MEMBRESIA,
    CONDICION_EXENTO,
    CONDICION_NORMAL,
)
from app.models.usuario import ROL_ADMIN, ROL_MIEMBRO, ROL_TESORERO, Usuario
from app.repositories import compras as repo_compras
from app.repositories import configuracion as repo_configuracion
from app.repositories import finanzas as repo_finanzas
from app.repositories import membresia as repo_membresia
from app.repositories import miembro as repo_miembro
from app.repositories import usuario as repo_usuario
from app.services import activacion as servicio_activacion

# --- Catálogos de la semilla ------------------------------------------------- #

NIVELES_SEMILLA: tuple[tuple[str, str, int, str], ...] = (
    (NIVEL_MATRICULA, "Matrícula", 5_000, TIPO_UNICO),
    (NIVEL_ESTANDAR, "Membresía Estándar", 5_000, TIPO_MENSUAL),
    (NIVEL_ACTIVA, "Membresía Activa", 15_000, TIPO_MENSUAL),
)

CUENTA_SEMILLA: dict[str, str] = {
    "titular": "Olimpia Runners Osorno",
    "banco": "Banco Santander",
    "numero_cuenta": "72769929",
    "rut": "65.161.804-5",
    "correo": "tesoreriaor@gmail.com",
}

PLANTILLA_SEMILLA: dict[str, str] = {
    "nombre": "Aviso de morosidad",
    "asunto": "Recordatorio de cuota pendiente · Osorno Runners",
    "cuerpo": (
        "Hola {nombre}:\n\n"
        "Te escribimos porque mantienes una deuda pendiente de {meses} mes(es) "
        "con el club, por un total de {adeudado}.\n\n"
        "Detalle: {detalle}\n\n"
        "Puedes regularizar tu situación con una transferencia a:\n"
        "Titular: {titular}\nBanco: {banco}\nCuenta corriente: {cuenta}\n"
        "RUT: {rut}\nCorreo: {correo}\n\n"
        "Gracias por ser parte de Osorno Runners."
    ),
}

USUARIOS_SEMILLA: tuple[tuple[str, str, str], ...] = (
    ("admin@osornorunners.cl", "Admin1234", ROL_ADMIN),
    ("tesorero@osornorunners.cl", "Tesorero1234", ROL_TESORERO),
    ("ana.saldivar@example.com", "Miembro1234", ROL_MIEMBRO),
)

# Cantidad de meses ya cerrados para los datos de ejemplo.
MESES_SEMILLA = 6


def _periodos_cerrados(cantidad: int, referencia: date) -> list[tuple[int, int]]:
    """Devuelve los ``cantidad`` meses ya cerrados antes del mes de referencia."""
    periodos: list[tuple[int, int]] = []
    for atras in range(cantidad, 0, -1):
        total = referencia.year * 12 + (referencia.month - 1) - atras
        periodos.append((total // 12, total % 12 + 1))
    return periodos


def _asegurar_niveles(db: Session) -> dict[str, NivelCuota]:
    """Crea el catálogo de cuotas si falta y lo devuelve indexado por código."""
    for codigo, nombre, monto, tipo in NIVELES_SEMILLA:
        if repo_membresia.obtener_nivel_por_codigo(db, codigo) is None:
            db.add(NivelCuota(codigo=codigo, nombre=nombre, monto_clp=monto, tipo=tipo))
    db.flush()
    niveles: dict[str, NivelCuota] = {}
    for codigo, _, _, _ in NIVELES_SEMILLA:
        nivel = repo_membresia.obtener_nivel_por_codigo(db, codigo)
        if nivel is not None:
            niveles[codigo] = nivel
    return niveles


def _asegurar_categorias(db: Session) -> None:
    for nombre in CATEGORIAS_BASE:
        if repo_finanzas.obtener_categoria_por_nombre(db, nombre) is None:
            repo_finanzas.crear_categoria(db, nombre=nombre, es_base=True)


def _asegurar_cuenta(db: Session) -> None:
    if repo_configuracion.obtener_cuenta(db) is None:
        repo_configuracion.crear_cuenta(db, **CUENTA_SEMILLA)


def _asegurar_plantilla(db: Session) -> None:
    if repo_configuracion.obtener_plantilla(db, PLANTILLA_SEMILLA["nombre"]) is None:
        repo_configuracion.crear_plantilla(db, **PLANTILLA_SEMILLA)


def _asegurar_usuarios(db: Session) -> dict[str, Usuario]:
    usuarios: dict[str, Usuario] = {}
    for email, clave, rol in USUARIOS_SEMILLA:
        usuario = repo_usuario.obtener_por_email(db, email)
        if usuario is None:
            usuario = repo_usuario.crear(
                db, email=email, password_hash=hash_password(clave), rol=rol
            )
        usuarios[email] = usuario
    db.flush()
    return usuarios


def _asegurar_cuota(
    db: Session,
    *,
    miembro_id: int,
    nivel_id: int,
    anio: int,
    mes: int,
    monto: int,
    estado: str,
) -> None:
    if repo_membresia.obtener_cuota(db, miembro_id, anio, mes, nivel_id) is not None:
        return
    repo_membresia.crear_cuota(
        db,
        miembro_id=miembro_id,
        anio=anio,
        mes=mes,
        nivel_cuota_id=nivel_id,
        monto_clp=monto,
        monto_pagado_clp=monto if estado == ESTADO_PAGADA else 0,
        estado=estado,
    )
    # La sesión no usa autoflush: se confirma la cuota para que las búsquedas
    # siguientes (por ejemplo, la obligación inicial) la encuentren.
    db.flush()


def _asegurar_obligacion_inicial(
    db: Session,
    *,
    miembro: Any,
    niveles: dict[str, NivelCuota],
    estado_matricula: str,
) -> None:
    """Crea la obligación inicial (Matrícula + cuota de la categoría; Flujo 1).

    Deja la Matrícula en el estado indicado para que la semilla refleje el caso de
    un miembro que ya pagó su incorporación, uno exento y uno pendiente.
    """
    servicio_activacion.registrar_obligacion_inicial(db, miembro)
    matricula = repo_membresia.obtener_cuota(
        db,
        miembro.id,
        miembro.fecha_incorporacion.year,
        miembro.fecha_incorporacion.month,
        niveles[NIVEL_MATRICULA].id,
    )
    if matricula is None or matricula.estado == estado_matricula:
        return
    matricula.estado = estado_matricula
    matricula.monto_pagado_clp = (
        matricula.monto_clp if estado_matricula == ESTADO_PAGADA else 0
    )
    db.add(matricula)


def _asegurar_miembro(db: Session, **datos: Any):
    existente = repo_miembro.obtener_por_email(db, str(datos["email"]))
    if existente is not None:
        return existente
    miembro = repo_miembro.crear(db, **datos)
    db.flush()
    return miembro


def _sembrar_cuotas_de_ejemplo(db: Session, niveles: dict[str, NivelCuota]) -> None:
    """Crea miembros y cuotas que cubren los cuatro estados de morosidad."""
    hoy = date.today()
    activa = niveles[NIVEL_ACTIVA]
    estandar = niveles[NIVEL_ESTANDAR]
    periodos = _periodos_cerrados(MESES_SEMILLA, hoy)
    mes_actual = (hoy.year, hoy.month)
    # Los miembros de ejemplo se incorporaron al comenzar la ventana de meses cerrados.
    anio_inc, mes_inc = periodos[0]
    fecha_incorporacion = date(anio_inc, mes_inc, 1)

    # Ana: al día (todas las cuotas cerradas pagadas).
    ana = _asegurar_miembro(
        db,
        nombre_completo="Ana Saldívar",
        email="ana.saldivar@example.com",
        telefono="+56 9 1111 1111",
        rut="11.111.111-1",
        categoria=CATEGORIA_ACTIVO,
        situacion_activacion=ACTIVACION_ACTIVO,
        condicion_especial=CONDICION_NORMAL,
        fecha_incorporacion=fecha_incorporacion,
        usuario_id=repo_usuario.obtener_por_email(
            db, "ana.saldivar@example.com"
        ).id,
    )
    for anio, mes in [*periodos, mes_actual]:
        pagada = (anio, mes) in periodos
        _asegurar_cuota(
            db, miembro_id=ana.id, nivel_id=activa.id, anio=anio, mes=mes,
            monto=activa.monto_clp,
            estado=ESTADO_PAGADA if pagada else ESTADO_PENDIENTE,
        )
    _asegurar_obligacion_inicial(
        db, miembro=ana, niveles=niveles, estado_matricula=ESTADO_PAGADA
    )

    # Bruno: 2 meses cerrados impagos -> naranjo.
    bruno = _asegurar_miembro(
        db,
        nombre_completo="Bruno Mora",
        email="bruno.mora@example.com",
        telefono="+56 9 2222 2222",
        rut="22.222.222-2",
        categoria=CATEGORIA_ACTIVO,
        situacion_activacion=ACTIVACION_ACTIVO,
        condicion_especial=CONDICION_NORMAL,
        fecha_incorporacion=fecha_incorporacion,
    )
    impagos_bruno = set(periodos[-2:])
    for anio, mes in [*periodos, mes_actual]:
        impago = (anio, mes) in impagos_bruno or (anio, mes) == mes_actual
        _asegurar_cuota(
            db, miembro_id=bruno.id, nivel_id=activa.id, anio=anio, mes=mes,
            monto=activa.monto_clp,
            estado=ESTADO_PENDIENTE if impago else ESTADO_PAGADA,
        )
    _asegurar_obligacion_inicial(
        db, miembro=bruno, niveles=niveles, estado_matricula=ESTADO_PAGADA
    )

    # Carla: 5 meses cerrados impagos -> rojo.
    carla = _asegurar_miembro(
        db,
        nombre_completo="Carla Deudora",
        email="carla.deudora@example.com",
        telefono="+56 9 3333 3333",
        rut="33.333.333-3",
        categoria=CATEGORIA_ACTIVO,
        situacion_activacion=ACTIVACION_ACTIVO,
        condicion_especial=CONDICION_NORMAL,
        fecha_incorporacion=fecha_incorporacion,
    )
    impagos_carla = set(periodos[-5:])
    for anio, mes in [*periodos, mes_actual]:
        impago = (anio, mes) in impagos_carla or (anio, mes) == mes_actual
        _asegurar_cuota(
            db, miembro_id=carla.id, nivel_id=activa.id, anio=anio, mes=mes,
            monto=activa.monto_clp,
            estado=ESTADO_PENDIENTE if impago else ESTADO_PAGADA,
        )
    _asegurar_obligacion_inicial(
        db, miembro=carla, niveles=niveles, estado_matricula=ESTADO_PAGADA
    )

    # Diego: miembro de apoyo exento (no genera cobros ni avisos).
    diego = _asegurar_miembro(
        db,
        nombre_completo="Diego Exento",
        email="diego.exento@example.com",
        telefono="+56 9 4444 4444",
        rut="44.444.444-4",
        categoria=CATEGORIA_MEMBRESIA,
        situacion_activacion=ACTIVACION_ACTIVO,
        condicion_especial=CONDICION_EXENTO,
        motivo_exencion="Becado",
        fecha_incorporacion=fecha_incorporacion,
    )
    for anio, mes in [*periodos, mes_actual]:
        _asegurar_cuota(
            db, miembro_id=diego.id, nivel_id=estandar.id, anio=anio, mes=mes,
            monto=estandar.monto_clp, estado=ESTADO_EXENTA,
        )
    _asegurar_obligacion_inicial(
        db, miembro=diego, niveles=niveles, estado_matricula=ESTADO_EXENTA
    )

    # Elena: incorporación pendiente del pago inicial (obligación inicial impaga).
    elena = _asegurar_miembro(
        db,
        nombre_completo="Elena Pendiente",
        email="elena.pendiente@example.com",
        telefono="+56 9 5555 5555",
        rut="55.555.555-5",
        categoria=CATEGORIA_ACTIVO,
        situacion_activacion=ACTIVACION_PENDIENTE,
        condicion_especial=CONDICION_NORMAL,
    )
    _asegurar_obligacion_inicial(
        db, miembro=elena, niveles=niveles, estado_matricula=ESTADO_PENDIENTE
    )

    # Una compra del club con un cargo separado a un alumno (RN-23).
    if not db.scalar(select(func.count()).select_from(CargoAlumno)):
        compra = repo_compras.crear_compra(
            db,
            descripcion="Compra de polerones de entrenamiento",
            proveedor="Textiles Osorno",
            monto_total_clp=250_000,
        )
        db.flush()
        item = repo_compras.crear_item(
            db,
            compra_id=compra.id,
            descripcion="Polerón del club",
            precio_unitario_clp=25_000,
            cantidad=10,
        )
        db.flush()
        repo_compras.crear_cargo(
            db, miembro_id=ana.id, compra_item_id=item.id, monto_clp=25_000
        )


def sembrar(db: Session) -> None:
    """Carga la semilla completa de forma idempotente."""
    niveles = _asegurar_niveles(db)
    _asegurar_categorias(db)
    _asegurar_cuenta(db)
    _asegurar_plantilla(db)
    _asegurar_usuarios(db)
    _sembrar_cuotas_de_ejemplo(db, niveles)
    db.commit()


def main() -> None:
    """Crea el esquema y carga la semilla (comando único, T3.10)."""
    crear_esquema()
    with SessionLocal() as db:
        sembrar(db)
    print("Esquema y semilla listos (idempotente).")
    print("Credenciales de prueba:")
    for email, clave, rol in USUARIOS_SEMILLA:
        print(f"  {rol:<9} {email} / {clave}")


if __name__ == "__main__":
    main()
