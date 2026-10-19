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
    """Crea los índices declarados que aún no existan en la base.

    ``create_all`` no modifica tablas ya creadas, por lo que este paso permite
    aplicar los índices nuevos del MVP sin incorporar Alembic. Es seguro
    ejecutarlo repetidamente: ``checkfirst`` omite los que ya están.
    """
    motor = bind or engine
    for tabla in Base.metadata.sorted_tables:
        for indice in tabla.indexes:
            indice.create(bind=motor, checkfirst=True)


if __name__ == "__main__":
    crear_esquema()
    print("Esquema creado (o ya existente).")
