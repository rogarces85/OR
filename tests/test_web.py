"""Rutas web: landing, salud, sesión, CSRF y control de acceso por rol.

Cubre CA-12, CA-13, CA-16, CA-18 y CA-21.
"""

from __future__ import annotations

import re
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_db
from app.main import app
from app.models.membresia import NIVEL_ACTIVA
from app.models.usuario import ROL_MIEMBRO, ROL_TESORERO
from app.repositories import pago as repo_pago

PATRON_CSRF = re.compile(r'name="csrf_token" value="([^"]+)"')

FICHA = {
    "nombre_completo": "Persona de Prueba",
    "email": "persona.prueba@example.com",
    "telefono": "+56 9 1234 5678",
    "rut": "12.345.678-9",
    "fecha_nacimiento": "1990-01-01",
    "direccion": "Calle Falsa 123",
    "contacto_emergencia": "Contacto de Emergencia",
    "categoria": "activo",
}


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
    assert encontrado is not None, "El formulario no incluye el token CSRF"
    return encontrado.group(1)


def _sesion(cliente, email: str, password: str):
    """Inicia sesión y devuelve la respuesta del POST (sin seguir redirección)."""
    respuesta = cliente.get("/ingresar")
    assert respuesta.status_code == 200
    token = _csrf(respuesta.text)
    return cliente.post(
        "/ingresar",
        data={"email": email, "password": password, "csrf_token": token},
        follow_redirects=False,
    )


# --------------------------------------------------------------------------- #
# Público y salud
# --------------------------------------------------------------------------- #


def test_landing_publica(cliente):
    """CA-18: la landing existe y carga con sus secciones."""
    respuesta = cliente.get("/")
    assert respuesta.status_code == 200
    assert "Osorno Runners" in respuesta.text
    assert "Membres" in respuesta.text


def test_ruta_de_salud(cliente):
    respuesta = cliente.get("/salud")
    assert respuesta.status_code == 200
    assert respuesta.json()["base_de_datos"] == "ok"


def test_pagina_404(cliente):
    respuesta = cliente.get("/ruta-que-no-existe")
    assert respuesta.status_code == 404
    assert "no" in respuesta.text.lower()


# --------------------------------------------------------------------------- #
# Sesión y CSRF
# --------------------------------------------------------------------------- #


def test_acceso_anonimo_redirige_al_login(cliente):
    respuesta = cliente.get("/miembros", follow_redirects=False)
    assert respuesta.status_code == 303
    assert respuesta.headers["location"] == "/ingresar"


def test_login_valido_redirige_al_panel(cliente, usuario_factory):
    usuario_factory(email="admin@example.com", password="Clave1234")
    respuesta = _sesion(cliente, "admin@example.com", "Clave1234")

    assert respuesta.status_code == 303
    assert respuesta.headers["location"] == "/miembros"


def test_login_invalido_no_revela_si_el_correo_existe(cliente, usuario_factory):
    usuario_factory(email="admin@example.com", password="Clave1234")
    respuesta = cliente.get("/ingresar")
    token = _csrf(respuesta.text)
    respuesta = cliente.post(
        "/ingresar",
        data={
            "email": "admin@example.com",
            "password": "incorrecta",
            "csrf_token": token,
        },
    )

    assert respuesta.status_code == 200
    assert "Correo o contraseña incorrectos." in respuesta.text


def test_login_sin_csrf_se_rechaza(cliente, usuario_factory):
    usuario_factory(email="admin@example.com", password="Clave1234")
    cliente.get("/ingresar")
    respuesta = cliente.post(
        "/ingresar",
        data={
            "email": "admin@example.com",
            "password": "Clave1234",
            "csrf_token": "token-invalido",
        },
    )

    assert respuesta.status_code == 200
    assert "sesión expiró" in respuesta.text.lower()


def test_admin_accede_al_panel(cliente, usuario_factory):
    usuario_factory(email="admin@example.com", password="Clave1234")
    _sesion(cliente, "admin@example.com", "Clave1234")

    respuesta = cliente.get("/miembros", follow_redirects=False)
    assert respuesta.status_code == 200


def test_tesorero_tiene_las_mismas_acciones_que_admin(
    cliente, usuario_factory
):
    """CA-13: Admin y Tesorero comparten los módulos de gestión."""
    usuario_factory(
        email="tesorero@example.com", password="Clave1234", rol=ROL_TESORERO
    )
    _sesion(cliente, "tesorero@example.com", "Clave1234")

    assert cliente.get("/miembros", follow_redirects=False).status_code == 200
    assert cliente.get("/reportes", follow_redirects=False).status_code == 200


def test_miembro_no_accede_a_modulos_de_gestion(
    cliente, usuario_factory, miembro_factory
):
    """CA-12 / CA-13: el miembro solo ve su propia información."""
    usuario = usuario_factory(
        email="miembro@example.com", password="Clave1234", rol=ROL_MIEMBRO
    )
    miembro = miembro_factory(usuario_id=usuario.id, email="miembro@example.com")
    _sesion(cliente, "miembro@example.com", "Clave1234")

    assert cliente.get("/miembros", follow_redirects=False).status_code == 403
    assert (
        cliente.get(f"/miembros/{miembro.id}", follow_redirects=False).status_code
        == 403
    )
    assert cliente.get("/reportes", follow_redirects=False).status_code == 403
    assert cliente.get("/mi/estado", follow_redirects=False).status_code == 200


def test_miembro_ve_su_deuda_en_el_estado_de_cuenta(
    cliente, niveles, usuario_factory, miembro_factory, cuota_factory
):
    """CA-05: al cerrarse un mes impago, el miembro ve su deuda en su estado."""
    usuario = usuario_factory(
        email="miembro@example.com", password="Clave1234", rol=ROL_MIEMBRO
    )
    miembro = miembro_factory(usuario_id=usuario.id, email="miembro@example.com")
    total = date.today().year * 12 + (date.today().month - 1) - 1
    cuota_factory(
        miembro, niveles[NIVEL_ACTIVA], total // 12, total % 12 + 1
    )
    _sesion(cliente, "miembro@example.com", "Clave1234")

    respuesta = cliente.get("/mi/estado")

    assert respuesta.status_code == 200
    assert "$ 15.000" in respuesta.text
    assert "Deuda de hasta 3 meses · 1 mes" in respuesta.text


def test_descarga_del_reporte_xlsx(
    cliente, db, niveles, usuario_factory, miembro_factory
):
    """CA-11: la descarga del reporte entrega un XLSX válido."""
    usuario_factory(email="admin@example.com", password="Clave1234")
    miembro = miembro_factory()
    repo_pago.crear(
        db,
        miembro_id=miembro.id,
        monto_clp=15_000,
        fecha_pago=date(2026, 7, 5),
    )
    db.commit()
    _sesion(cliente, "admin@example.com", "Clave1234")

    respuesta = cliente.get(
        "/reportes/exportar.xlsx",
        params={"desde": "2026-07-01", "hasta": "2026-07-31"},
    )

    assert respuesta.status_code == 200
    assert respuesta.content.startswith(b"PK")
    assert "spreadsheetml" in respuesta.headers["content-type"]


def test_descarga_del_informe_pdf(
    cliente, db, niveles, usuario_factory, miembro_factory, cuota_factory
):
    """CA-14: la descarga del informe entrega un PDF válido."""
    usuario_factory(email="admin@example.com", password="Clave1234")
    miembro = miembro_factory()
    cuota_factory(miembro, niveles[NIVEL_ACTIVA], 2026, 7)
    _sesion(cliente, "admin@example.com", "Clave1234")

    respuesta = cliente.get(f"/reportes/informe/{miembro.id}/exportar.pdf")

    assert respuesta.status_code == 200
    assert respuesta.content.startswith(b"%PDF")


def test_exportacion_sin_datos_no_descarga_archivo(
    cliente, db, niveles, usuario_factory
):
    """Sección 9: sin movimientos se informa y no se descarga un archivo vacío."""
    usuario_factory(email="admin@example.com", password="Clave1234")
    _sesion(cliente, "admin@example.com", "Clave1234")

    respuesta = cliente.get(
        "/reportes/exportar.xlsx",
        params={"desde": "2026-09-01", "hasta": "2026-09-30"},
        follow_redirects=False,
    )

    assert respuesta.status_code == 303
    assert respuesta.headers["location"].startswith("/reportes?")


# --------------------------------------------------------------------------- #
# Alta de miembros (CA-16, CA-21)
# --------------------------------------------------------------------------- #


def test_alta_rechaza_correo_duplicado(
    cliente, db, niveles, usuario_factory
):
    """CA-16: el correo es único y el formulario explica el rechazo."""
    usuario_factory(email="admin@example.com", password="Clave1234")
    _sesion(cliente, "admin@example.com", "Clave1234")

    respuesta = cliente.get("/miembros/nuevo")
    token = _csrf(respuesta.text)
    datos = {**FICHA, "csrf_token": token}

    primera = cliente.post("/miembros/nuevo", data=datos, follow_redirects=False)
    assert primera.status_code == 303
    assert primera.headers["location"].startswith("/miembros/")

    respuesta = cliente.get("/miembros/nuevo")
    datos["csrf_token"] = _csrf(respuesta.text)
    segunda = cliente.post("/miembros/nuevo", data=datos)

    assert segunda.status_code == 200
    assert "Ya existe un miembro registrado" in segunda.text


def test_alta_con_datos_invalidos_no_guarda(
    cliente, db, niveles, usuario_factory
):
    """CA-21: datos inválidos no se guardan y muestran un mensaje comprensible."""
    usuario_factory(email="admin@example.com", password="Clave1234")
    _sesion(cliente, "admin@example.com", "Clave1234")

    respuesta = cliente.get("/miembros/nuevo")
    token = _csrf(respuesta.text)
    respuesta = cliente.post(
        "/miembros/nuevo",
        data={
            "csrf_token": token,
            "nombre_completo": "AB",
            "email": "no-es-un-correo",
            "telefono": "1",
            "rut": "x",
            "fecha_nacimiento": "2999-01-01",
            "direccion": "",
            "contacto_emergencia": "",
            "categoria": "activo",
        },
    )

    assert respuesta.status_code == 200
    assert "No se pudo registrar el miembro" in respuesta.text
    from sqlalchemy import func, select

    from app.models.miembro import Miembro

    assert db.scalar(select(func.count()).select_from(Miembro)) == 0


def test_listado_enlaza_a_edicion_y_muestra_matricula(
    cliente, usuario_factory, miembro_factory
):
    """El nombre del atleta abre el formulario de edición y muestra matrícula."""
    usuario_factory(email="admin@example.com", password="Clave1234")
    miembro = miembro_factory(nombre="Atleta Editable", matriculado=True)
    _sesion(cliente, "admin@example.com", "Clave1234")

    respuesta = cliente.get("/miembros")

    assert respuesta.status_code == 200
    assert f'href="/miembros/{miembro.id}/editar"' in respuesta.text
    assert "Atleta Editable" in respuesta.text
    assert "Matrícula" in respuesta.text
    assert "Ver ficha" in respuesta.text


def test_admin_abre_formulario_de_edicion(
    cliente, usuario_factory, miembro_factory
):
    """Admin y Tesorero pueden abrir la edición completa desde el listado."""
    usuario_factory(email="admin@example.com", password="Clave1234")
    miembro = miembro_factory(
        nombre="Atleta Editable",
        fecha_incorporacion=date(2025, 9, 1),
        matriculado=True,
    )
    _sesion(cliente, "admin@example.com", "Clave1234")

    respuesta = cliente.get(f"/miembros/{miembro.id}/editar")

    assert respuesta.status_code == 200
    assert "Editar miembro" in respuesta.text
    assert "Fecha de ingreso" in respuesta.text
    assert "Ya está matriculado" in respuesta.text
    assert 'value="2025-09-01"' in respuesta.text


def test_edicion_guarda_fecha_de_ingreso_y_matricula(
    cliente, db, usuario_factory, miembro_factory
):
    """La ficha de edición actualiza fecha de ingreso y estado de matrícula."""
    usuario_factory(email="admin@example.com", password="Clave1234")
    miembro = miembro_factory(
        nombre="Atleta Editable",
        fecha_incorporacion=date(2026, 1, 1),
    )
    _sesion(cliente, "admin@example.com", "Clave1234")
    respuesta = cliente.get(f"/miembros/{miembro.id}/editar")
    token = _csrf(respuesta.text)

    guardado = cliente.post(
        f"/miembros/{miembro.id}/editar",
        data={
            **FICHA,
            "csrf_token": token,
            "fecha_incorporacion": "2025-09-01",
            "matriculado": "true",
        },
        follow_redirects=False,
    )

    assert guardado.status_code == 303
    db.refresh(miembro)
    assert miembro.fecha_incorporacion == date(2025, 9, 1)
    assert miembro.matriculado is True
