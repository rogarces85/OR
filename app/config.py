"""Configuración central de la aplicación.

Lee las variables de entorno (archivo ``.env``) para evitar credenciales en el
código. Ver ``.env.example`` para la plantilla de variables.
"""

from __future__ import annotations

from functools import lru_cache
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Parámetros de configuración del sistema."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Aplicación ---
    app_name: str = "Sistema Gestión Pagos Osorno Runners"
    entorno: str = "desarrollo"
    secret_key: str = "cambiar-esta-clave-en-tu-entorno"

    # --- Base de datos MySQL/MariaDB (P-1, Q-4) ---
    db_host: str = "localhost"
    db_port: int = 3306
    db_name: str = "osorno_runners"
    db_user: str = "root"
    db_password: str = ""

    # --- Sesión (Q-2) ---
    session_cookie: str = "or_sesion"
    session_max_age: int = 60 * 60 * 8  # 8 horas

    @property
    def database_url(self) -> str:
        """Cadena de conexión de SQLAlchemy para MySQL/MariaDB (driver PyMySQL)."""
        usuario = quote_plus(self.db_user)
        clave = quote_plus(self.db_password)
        return (
            f"mysql+pymysql://{usuario}:{clave}@{self.db_host}:{self.db_port}"
            f"/{self.db_name}?charset=utf8mb4"
        )


@lru_cache
def get_settings() -> Settings:
    """Devuelve la configuración de la aplicación (cacheada)."""
    return Settings()
