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
    como opción si el modelo crece.
    """
    import app.models  # noqa: F401  (registra los modelos en Base.metadata)

    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    crear_esquema()
    print("Esquema creado (o ya existente).")
