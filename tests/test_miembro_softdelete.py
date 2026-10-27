"""Tests para soft-delete / retiro de miembros (fecha_baja)."""

from __future__ import annotations

import re
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_db
from app.main import app
from app.models.miembro import ACTIVACION_ACTIVO
from app.repositories import miembro as repo_miembro
from app.services import membresias as servicio_membresias

PATRON_CSRF = re.compile(r'name="csrf_token" value="([^"]+)"')


def test_miembro_soft_delete_excluye_de_listado(db, usuario_factory):
    """Un miembro con fecha_baja no aparece en listar() por defecto."""
    usuario_factory(email="admin@example.com", password="Clave1234")
    miembro = servicio_membresias.crear_miembro(
        db,
        nombre_completo="Para Retirar",
        email="pararetirar@example.com",
        categoria="activo",
        fecha_incorporacion=date(2025, 1, 1),
    )

    # Por defecto no aparece en listar (fecha_baja IS NULL)
    assert miembro in repo_miembro.listar(db)

    # Marcar baja
    miembro.fecha_baja = date(2025, 6, 15)
    miembro.motivo_baja = "Mudanza"
    db.add(miembro)
    db.commit()

    # Ahora NO aparece en listar() por defecto
    assert miembro not in repo_miembro.listar(db)

    # Pero SÍ aparece con incluir_bajas=True
    assert miembro in repo_miembro.listar(db, incluir_bajas=True)

    # Y en listar_todos()
    assert miembro in repo_miembro.listar_todos(db)


def test_miembro_reactivar_limpia_fecha_baja(db, usuario_factory):
    """Reactivar un miembro limpia fecha_baja y motivo_baja."""
    usuario_factory(email="admin@example.com", password="Clave1234")
    miembro = servicio_membresias.crear_miembro(
        db,
        nombre_completo="Para Reactivar",
        email="parareactivar@example.com",
        categoria="activo",
        fecha_incorporacion=date(2025, 1, 1),
    )

    # Dar de baja
    miembro.fecha_baja = date(2025, 6, 15)
    miembro.motivo_baja = "Lesión"
    db.add(miembro)
    db.commit()

    # Reactivar
    miembro.fecha_baja = None
    miembro.motivo_baja = None
    db.add(miembro)
    db.commit()
    db.refresh(miembro)

    assert miembro.fecha_baja is None
    assert miembro.motivo_baja is None
    assert miembro.esta_activo is True
    assert miembro in repo_miembro.listar(db)


def test_property_esta_activo(db):
    """La property esta_activo refleja fecha_baja."""
    from app.models.miembro import Miembro

    m1 = Miembro(
        nombre_completo="Activo",
        email="activo@example.com",
        fecha_incorporacion=date.today(),
    )
    assert m1.esta_activo is True

    m2 = Miembro(
        nombre_completo="Baja",
        email="baja@example.com",
        fecha_incorporacion=date.today(),
        fecha_baja=date.today(),
    )
    assert m2.esta_activo is False


# --------------------------------------------------------------------------- #
# Servicio: dar de baja y reactivar
# --------------------------------------------------------------------------- #


def _miembro(db, email: str = "socio@example.com"):
    return servicio_membresias.crear_miembro(
        db,
        nombre_completo="Socio de Prueba",
        email=email,
        categoria="activo",
        fecha_incorporacion=date(2025, 1, 1),
    )


def test_dar_de_baja_guarda_fecha_y_motivo(db):
    """La baja registra la fecha indicada y el motivo recortado."""
    miembro = _miembro(db)
    servicio_membresias.dar_de_baja(
        db, miembro, fecha=date(2025, 6, 15), motivo="  Mudanza  "
    )

    assert miembro.fecha_baja == date(2025, 6, 15)
    assert miembro.motivo_baja == "Mudanza"
    assert miembro.esta_activo is False


def test_dar_de_baja_sin_fecha_usa_hoy_y_motivo_vacio(db):
    """Sin fecha, la baja queda con la fecha del día y sin motivo."""
    miembro = _miembro(db, email="sinfecha@example.com")
    servicio_membresias.dar_de_baja(db, miembro, motivo="   ")

    assert miembro.fecha_baja == date.today()
    assert miembro.motivo_baja is None


def test_dar_de_baja_dos_veces_falla(db):
    """Una segunda baja del mismo miembro es un error de negocio."""
    miembro = _miembro(db, email="doble@example.com")
    servicio_membresias.dar_de_baja(db, miembro)
    with pytest.raises(ValueError):
        servicio_membresias.dar_de_baja(db, miembro)


def test_dar_de_baja_motivo_muy_largo_falla(db):
    """El motivo no puede superar el ancho de la columna (200)."""
    miembro = _miembro(db, email="motivo@example.com")
    with pytest.raises(ValueError):
        servicio_membresias.dar_de_baja(db, miembro, motivo="x" * 201)


def test_reactivar_sin_baja_falla(db):
    """Reactivar a un miembro que no está de baja es un error de negocio."""
    miembro = _miembro(db, email="activado@example.com")
    with pytest.raises(ValueError):
        servicio_membresias.reactivar_miembro(db, miembro)


def test_baja_saca_al_miembro_del_ciclo_de_cobro(db):
    """Un miembro de baja no entra en ``miembros_facturables`` (F-10)."""
    miembro = _miembro(db, email="cobro@example.com")
    miembro.situacion_activacion = ACTIVACION_ACTIVO
    db.add(miembro)
    db.commit()

    assert miembro in servicio_membresias.miembros_facturables(db)

    servicio_membresias.dar_de_baja(db, miembro)

    assert miembro not in servicio_membresias.miembros_facturables(db)


# --------------------------------------------------------------------------- #
# Web: POST de baja y reactivación desde la ficha
# --------------------------------------------------------------------------- #


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


def test_web_baja_y_reactivacion(db, cliente, usuario_factory):
    """CA: la baja oculta al miembro del panel y la reactivación lo devuelve."""
    _sesion_admin(cliente, usuario_factory)
    miembro = _miembro(db, email="web@example.com")

    ficha = cliente.get(f"/miembros/{miembro.id}")
    assert ficha.status_code == 200

    baja = cliente.post(
        f"/miembros/{miembro.id}/baja",
        data={
            "csrf_token": _csrf(ficha.text),
            "fecha_baja": "2025-06-15",
            "motivo_baja": "Se mudó de ciudad",
        },
        follow_redirects=False,
    )
    assert baja.status_code == 303
    db.refresh(miembro)
    assert miembro.fecha_baja == date(2025, 6, 15)

    listado = cliente.get("/miembros")
    assert "web@example.com" not in listado.text

    con_bajas = cliente.get("/miembros?incluir_bajas=1")
    assert "web@example.com" in con_bajas.text

    ficha = cliente.get(f"/miembros/{miembro.id}")
    assert "Dado de baja" in ficha.text

    reactivar = cliente.post(
        f"/miembros/{miembro.id}/reactivar",
        data={"csrf_token": _csrf(ficha.text)},
        follow_redirects=False,
    )
    assert reactivar.status_code == 303
    db.refresh(miembro)
    assert miembro.fecha_baja is None
    assert "web@example.com" in cliente.get("/miembros").text