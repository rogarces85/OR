"""Capa de acceso a la base de datos: motor, sesión y base declarativa."""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import get_settings

settings = get_settings()

engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """Base declarativa de todos los modelos del ORM."""


def crear_esquema() -> None:
    """Crea las tablas del esquema según los modelos registrados.

    En el MVP se usa la creación directa del esquema (PLAN §9); Alembic queda
    como opción si el modelo crece. Después de crear las tablas se agregan los
    índices que falten en una base ya existente (T9.1), de forma idempotente.
    """
    import app.models  # noqa: F401  (registra los modelos en Base.metadata)

    Base.metadata.create_all(bind=engine)
    crear_indices_faltantes()


def crear_indices_faltantes(bind=None) -> None:
    """Crea los índices declarados y columnas que falten en la base.

    ``create_all`` no modifica tablas ya creadas, por lo que este paso permite
    aplicar los índices y columnas nuevas del MVP sin incorporar Alembic. Es
    seguro ejecutarlo repetidamente: ``checkfirst`` omite los que ya están.
    """
    from sqlalchemy import inspect, text
    motor = bind or engine

    # 1) Índices declarados en modelos
    for tabla in Base.metadata.sorted_tables:
        for indice in tabla.indexes:
            indice.create(bind=motor, checkfirst=True)

    # 2) Migraciones idempotentes de columnas (MySQL/MariaDB)
    inspector = inspect(motor)
    columnas_miembros = {c["name"] for c in inspector.get_columns("miembros")}

    with motor.begin() as conn:
        # fecha_baja
        if "fecha_baja" not in columnas_miembros:
            conn.execute(text("ALTER TABLE miembros ADD COLUMN fecha_baja DATE NULL"))
            print("Columna 'fecha_baja' agregada a miembros")
        # motivo_baja
        if "motivo_baja" not in columnas_miembros:
            conn.execute(text("ALTER TABLE miembros ADD COLUMN motivo_baja VARCHAR(200) NULL"))
            print("Columna 'motivo_baja' agregada a miembros")

        # Índice para filtrar por fecha_baja
        indices = {idx["name"] for idx in inspector.get_indexes("miembros")}
        if "ix_miembros_fecha_baja" not in indices:
            conn.execute(text("CREATE INDEX ix_miembros_fecha_baja ON miembros (fecha_baja)"))
            print("Índice 'ix_miembros_fecha_baja' creado")


if __name__ == "__main__":
    crear_esquema()
    print("Esquema creado (o ya existente).")
