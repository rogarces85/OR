"""Tests para el modal de edición completa de miembros (respuestas JSON)."""

from __future__ import annotations

import re
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_db
from app.main import app

PATRON_CSRF = re.compile(r'name="csrf_token" value="([^"]+)"')


@pytest.fixture()
def cliente(db):
    """TestClient con la sesión de prueba inyectada como dependencia."""

    def _get_db():
        yield db

    app.dependency_overrides[get_db] = _get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _csrf(html: str) -> str:
    encontrado = PATRON_CSRF.search(html)
    assert encontrado is not None, "La página no incluye el token CSRF"
    return encontrado.group(1)


def _sesion_admin(cliente, usuario_factory):
    usuario_factory(email="admin@example.com", password="Clave1234")
    respuesta = cliente.get("/ingresar")
    assert respuesta.status_code == 200
    respuesta = cliente.post(
        "/ingresar",
        data={
            "email": "admin@example.com",
            "password": "Clave1234",
            "csrf_token": _csrf(respuesta.text),
        },
        follow_redirects=False,
    )
    assert respuesta.status_code == 303


def test_modal_edicion_devuelve_errores_json(db, cliente, usuario_factory):
    """El modal con datos inválidos devuelve 422 y errores de campo en JSON."""
    from app.services import membresias as servicio_membresias

    _sesion_admin(cliente, usuario_factory)
    miembro = servicio_membresias.crear_miembro(
        db,
        nombre_completo="Para Editar",
        email="editar@example.com",
        categoria="activo",
        fecha_incorporacion=date(2025, 1, 1),
    )

    ficha = cliente.get(f"/miembros/{miembro.id}")
    assert ficha.status_code == 200

    respuesta = cliente.post(
        f"/miembros/{miembro.id}/editar",
        data={
            "csrf_token": _csrf(ficha.text),
            "modal": "1",
            "nombre_completo": "",  # inválido: muy corto
            "email": "no-es-un-email",  # inválido
            "telefono": "123",  # inválido
            "rut": "123456789",
            "fecha_nacimiento": "1990-01-01",
            "fecha_incorporacion": "2025-01-01",
            "direccion": "Calle",
            "contacto_emergencia": "Contacto",
            "matriculado": "false",
            "categoria": "activo",
        },
    )
    assert respuesta.status_code == 422
    datos = respuesta.json()
    assert "errores" in datos
    assert "nombre_completo" in datos["errores"]
    assert "email" in datos["errores"]
    assert "telefono" in datos["errores"]


def test_modal_edicion_guarda_y_devuelve_ok(db, cliente, usuario_factory):
    """El modal con datos válidos devuelve 200 y ok=true."""
    from app.services import membresias as servicio_membresias

    _sesion_admin(cliente, usuario_factory)
    miembro = servicio_membresias.crear_miembro(
        db,
        nombre_completo="Para Guardar",
        email="guardar@example.com",
        categoria="activo",
        fecha_incorporacion=date(2025, 1, 1),
    )

    ficha = cliente.get(f"/miembros/{miembro.id}")
    assert ficha.status_code == 200

    respuesta = cliente.post(
        f"/miembros/{miembro.id}/editar",
        data={
            "csrf_token": _csrf(ficha.text),
            "modal": "1",
            "nombre_completo": "Juan Guardado",
            "email": "guardar@example.com",
            "telefono": "+56 9 1234 5678",
            "rut": "12.345.678-9",
            "fecha_nacimiento": "1990-01-01",
            "fecha_incorporacion": "2025-01-01",
            "direccion": "Calle Falsa 123",
            "contacto_emergencia": "María 9 9999 9999",
            "matriculado": "false",
            "categoria": "activo",
        },
    )
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos.get("ok") is True

    # verificar que se guardó en la base
    from app.models.miembro import Miembro
    actualizado = db.get(Miembro, miembro.id)
    assert actualizado.nombre_completo == "Juan Guardado"
