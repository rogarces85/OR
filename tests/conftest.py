"""Fixtures compartidas de la suite de pruebas (T8.1).

Por defecto las pruebas corren sobre **SQLite en memoria**, de modo que no
requieren XAMPP ni una base MySQL levantada. Para ejecutarlas contra MySQL se
puede exportar ``TEST_DATABASE_URL`` antes de invocar ``pytest``::

    $env:TEST_DATABASE_URL = "mysql+pymysql://root:@localhost:3306/osorno_runners_test"
    .\\venv\\Scripts\\python.exe -m pytest

La base indicada se crea y se destruye por prueba; nunca debe apuntar a la base
real de desarrollo.
"""

from __future__ import annotations

import itertools
import os

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  (registra todos los modelos en Base.metadata)
from app.core.seguridad import hash_password
from app.database import Base
from app.models.finanzas import CATEGORIAS_BASE
from app.models.membresia import (
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
    CONDICION_EXENTO,
    CONDICION_NORMAL,
    MOTIVOS_EXENCION,
)
from app.models.usuario import ROL_ADMIN, Usuario
from app.repositories import finanzas as repo_finanzas
from app.repositories import membresia as repo_membresia
from app.repositories import miembro as repo_miembro

URL_PRUEBAS = os.getenv("TEST_DATABASE_URL", "sqlite+pysqlite:///:memory:")


def _crear_engine():
    """Crea el motor de pruebas según la URL configurada."""
    if URL_PRUEBAS.startswith("sqlite"):
        engine = create_engine(
            URL_PRUEBAS,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            future=True,
        )

        @event.listens_for(engine, "connect")
        def _activar_claves_foraneas(conexion, _registro):
            cursor = conexion.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        return engine
    return create_engine(URL_PRUEBAS, pool_pre_ping=True, future=True)


@pytest.fixture()
def db():
    """Sesión de base de datos aislada: esquema limpio por cada prueba."""
    engine = _crear_engine()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    fabrica = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    sesion = fabrica()
    try:
        yield sesion
    finally:
        sesion.rollback()
        sesion.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture()
def niveles(db):
    """Catálogo de cuotas de RN-01: Matrícula 5.000, Estándar 5.000, Activa 15.000."""
    definiciones = {
        NIVEL_MATRICULA: ("Matrícula", 5_000, TIPO_UNICO),
        NIVEL_ESTANDAR: ("Membresía Estándar", 5_000, TIPO_MENSUAL),
        NIVEL_ACTIVA: ("Membresía Activa", 15_000, TIPO_MENSUAL),
    }
    creados: dict[str, NivelCuota] = {}
    for codigo, (nombre, monto, tipo) in definiciones.items():
        nivel = NivelCuota(codigo=codigo, nombre=nombre, monto_clp=monto, tipo=tipo)
        db.add(nivel)
        creados[codigo] = nivel
    db.commit()
    return creados


@pytest.fixture()
def categorias(db):
    """Categorías base de egreso (D-5, D-12)."""
    creadas = {}
    for nombre in CATEGORIAS_BASE:
        categoria = repo_finanzas.crear_categoria(db, nombre=nombre, es_base=True)
        creadas[nombre] = categoria
    db.commit()
    return creadas


@pytest.fixture()
def miembro_factory(db):
    """Fábrica de miembros en cualquier estado (al día, moroso, exento, pendiente)."""
    contador = itertools.count(1)

    def _crear(
        *,
        nombre: str | None = None,
        email: str | None = None,
        categoria: str = CATEGORIA_ACTIVO,
        activo: bool = True,
        exento: bool = False,
        motivo_exencion: str | None = None,
        fecha_incorporacion=None,
        usuario_id: int | None = None,
    ):
        numero = next(contador)
        if exento and motivo_exencion is None:
            motivo_exencion = MOTIVOS_EXENCION[0]
        miembro = repo_miembro.crear(
            db,
            nombre_completo=nombre or f"Miembro de prueba {numero}",
            email=email or f"miembro{numero}@example.com",
            categoria=categoria,
            situacion_activacion=(
                ACTIVACION_ACTIVO if activo else ACTIVACION_PENDIENTE
            ),
            condicion_especial=CONDICION_EXENTO if exento else CONDICION_NORMAL,
            motivo_exencion=motivo_exencion,
            fecha_incorporacion=fecha_incorporacion,
            usuario_id=usuario_id,
        )
        db.commit()
        db.refresh(miembro)
        return miembro

    return _crear


@pytest.fixture()
def cuota_factory(db):
    """Fábrica de cuotas mensuales (o de Matrícula) para un miembro."""

    def _crear(
        miembro,
        nivel,
        anio: int,
        mes: int,
        *,
        estado: str = ESTADO_PENDIENTE,
        monto: int | None = None,
        pagado: int = 0,
    ):
        cuota = repo_membresia.crear_cuota(
            db,
            miembro_id=miembro.id,
            anio=anio,
            mes=mes,
            nivel_cuota_id=nivel.id,
            monto_clp=int(nivel.monto_clp if monto is None else monto),
            monto_pagado_clp=pagado,
            estado=estado,
        )
        db.commit()
        db.refresh(cuota)
        return cuota

    return _crear


@pytest.fixture()
def usuario_factory(db):
    """Fábrica de usuarios con contraseña hasheada (Admin por defecto)."""
    contador = itertools.count(1)

    def _crear(
        *,
        email: str | None = None,
        password: str = "Clave1234",
        rol: str = ROL_ADMIN,
        activo: bool = True,
    ) -> Usuario:
        numero = next(contador)
        usuario = Usuario(
            email=email or f"usuario{numero}@example.com",
            password_hash=hash_password(password),
            rol=rol,
            activo=activo,
        )
        db.add(usuario)
        db.commit()
        db.refresh(usuario)
        return usuario

    return _crear
