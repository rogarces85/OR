"""Seguridad: hash de contraseñas, sesiones, roles (RBAC) y CSRF.

Cubre F-02, F-03, RN-06, RN-07 y la decisión de seguridad Q-2.
"""

from __future__ import annotations

import secrets
from collections.abc import Callable
from typing import Any

from fastapi import HTTPException, Request, status
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.dependencies import SesionBD
from app.models.usuario import Usuario

_contexto_criptografico = CryptContext(schemes=["bcrypt"], deprecated="auto")

CLAVE_USUARIO = "usuario_id"
CLAVE_CSRF = "csrf_token"
CLAVE_FLASH = "flash"

# --------------------------------------------------------------------------- #
# Contraseñas (T4.1)
# --------------------------------------------------------------------------- #


def hash_password(plano: str) -> str:
    """Devuelve el hash bcrypt de una contraseña en texto plano."""
    return _contexto_criptografico.hash(plano)


def verify_password(plano: str, hash_guardado: str) -> bool:
    """Comprueba una contraseña contra su hash; nunca revela por qué falla."""
    try:
        return _contexto_criptografico.verify(plano, hash_guardado)
    except ValueError:
        return False


# --------------------------------------------------------------------------- #
# Sesiones (T4.2)
# --------------------------------------------------------------------------- #


def iniciar_sesion(request: Request, usuario: Usuario) -> None:
    """Guarda la identidad y el rol del usuario en la sesión firmada."""
    request.session.clear()
    request.session[CLAVE_USUARIO] = usuario.id
    request.session["rol"] = usuario.rol
    request.session["nombre"] = usuario.email
    # Se renueva el token CSRF al iniciar sesión (evita fijación de sesión).
    request.session[CLAVE_CSRF] = secrets.token_urlsafe(32)


def cerrar_sesion(request: Request) -> None:
    """Elimina por completo la sesión actual."""
    request.session.clear()


def datos_sesion(request: Request) -> dict[str, Any]:
    """Resumen de la sesión para las plantillas (sin tocar la base de datos)."""
    sesion = getattr(request, "session", None) or {}
    return {
        "autenticado": bool(sesion.get(CLAVE_USUARIO)),
        "rol": sesion.get("rol"),
        "nombre": sesion.get("nombre"),
        "usuario_id": sesion.get(CLAVE_USUARIO),
    }


def obtener_usuario_actual(request: Request, db: Session) -> Usuario | None:
    """Devuelve el usuario autenticado, o ``None`` si no hay sesión válida."""
    usuario_id = (getattr(request, "session", None) or {}).get(CLAVE_USUARIO)
    if not usuario_id:
        return None
    usuario = db.get(Usuario, usuario_id)
    if usuario is None or not usuario.activo:
        return None
    return usuario


# --------------------------------------------------------------------------- #
# RBAC (T4.4)
# --------------------------------------------------------------------------- #


def requiere_rol(*roles: str) -> Callable[..., Usuario]:
    """Dependencia de FastAPI que restringe el acceso por rol (D-7, RN-07).

    Si no hay sesión, redirige al inicio de sesión; si el rol no está permitido,
    responde 403 con la página de "acceso denegado".
    """

    def dependencia(request: Request, db: SesionBD) -> Usuario:
        usuario = obtener_usuario_actual(request, db)
        if usuario is None:
            raise HTTPException(
                status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/ingresar"}
            )
        if roles and usuario.rol not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para acceder a esta sección.",
            )
        return usuario

    return dependencia


# --------------------------------------------------------------------------- #
# CSRF (T4.5)
# --------------------------------------------------------------------------- #


def token_csrf(request: Request) -> str:
    """Devuelve el token CSRF de la sesión, creándolo si aún no existe."""
    sesion = getattr(request, "session", None)
    if sesion is None:
        return ""
    token = sesion.get(CLAVE_CSRF)
    if not token:
        token = secrets.token_urlsafe(32)
        sesion[CLAVE_CSRF] = token
    return token


def validar_csrf(request: Request, token: str | None) -> bool:
    """Comprueba que el token enviado coincida con el de la sesión."""
    esperado = (getattr(request, "session", None) or {}).get(CLAVE_CSRF)
    if not esperado or not token:
        return False
    return secrets.compare_digest(str(esperado), str(token))


# --------------------------------------------------------------------------- #
# Mensajes flash (UI-12)
# --------------------------------------------------------------------------- #


def flash(request: Request, tipo: str, texto: str) -> None:
    """Guarda un mensaje para mostrarlo una sola vez en la próxima vista."""
    request.session[CLAVE_FLASH] = {"tipo": tipo, "texto": texto}
