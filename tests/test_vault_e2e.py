"""Tests E2E de endpoints HTTP de la bóveda (router /vault)."""

from __future__ import annotations

import io
import re
import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_db
from app.main import app
from app.models.usuario import ROL_ADMIN, ROL_TESORERO, Usuario
from app.models.vault import DocumentoVault, TipoDocumento
from app.core.seguridad import hash_password


PATRON_CSRF = re.compile(r'name="csrf_token" value="([^"]+)"')


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


@pytest.fixture()
def cliente(db):
    """TestClient con la sesión de prueba inyectada como dependencia."""

    def _get_db():
        yield db

    app.dependency_overrides[get_db] = _get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def admin_user(db):
    """Usuario Admin autenticado."""
    usuario = Usuario(
        email="admin@test.cl",
        password_hash=hash_password("admin123"),
        rol="admin",
        activo=True,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


@pytest.fixture
def tesorero_user(db):
    """Usuario Tesorero autenticado."""
    usuario = Usuario(
        email="tesorero@test.cl",
        password_hash=hash_password("tesorero123"),
        rol="tesorero",
        activo=True,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


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


@pytest.fixture
def auth_headers(cliente, admin_user):
    """Headers con sesión autenticada como admin."""
    resp = _sesion(cliente, admin_user.email, "admin123")
    assert resp.status_code == 303
    cookie = resp.headers.get("set-cookie", "")
    return {"Cookie": cookie}


@pytest.fixture
def tesorero_headers(cliente, tesorero_user):
    """Headers con sesión autenticada como tesorero."""
    resp = _sesion(cliente, tesorero_user.email, "tesorero123")
    assert resp.status_code == 303
    cookie = resp.headers.get("set-cookie", "")
    return {"Cookie": cookie}


class TestVaultEndpoints:
    """Tests de endpoints /vault/*."""

    def test_subir_documento_pdf_tesorero(self, cliente, tesorero_headers, db):
        """Tesorero puede subir PDF a la bóveda."""
        pdf_content = b"%PDF-1.4 fake pdf content for testing"
        files = {"archivo": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")}
        data = {
            "tipo_documento": "COMPROBANTE",
            "entidad_relacionada": "pagos",
            "entidad_id": "1",
        }

        resp = cliente.post("/vault/subir", files=files, data=data, headers=tesorero_headers)
        assert resp.status_code == 201

        result = resp.json()
        assert result["id"] > 0
        assert result["sha256"]  # hash real
        assert result["tipo_documento"] == "COMPROBANTE"
        assert result["entidad_relacionada"] == "pagos"
        assert result["entidad_id"] == 1

        # Verificar en BD
        doc = db.query(DocumentoVault).get(result["id"])
        assert doc is not None
        assert doc.tipo_documento == TipoDocumento.COMPROBANTE

    def test_subir_documento_imagen_tesorero(self, cliente, tesorero_headers, db):
        """Tesorero puede subir imagen (JPG/PNG)."""
        # Fake JPEG header
        jpg_content = b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"X" * 1000
        files = {"archivo": ("foto.jpg", io.BytesIO(jpg_content), "image/jpeg")}
        data = {"tipo_documento": "BOLETA"}

        resp = cliente.post("/vault/subir", files=files, data=data, headers=tesorero_headers)
        assert resp.status_code == 201
        assert resp.json()["mime_type"] == "image/jpeg"

    def test_subir_archivo_tipo_no_permitido(self, cliente, tesorero_headers):
        """Rechaza archivos con MIME no permitido (ej. .exe)."""
        exe_content = b"MZ\x90\x00"  # PE header
        files = {"archivo": ("malware.exe", io.BytesIO(exe_content), "application/octet-stream")}
        data = {"tipo_documento": "OTRO"}

        resp = cliente.post("/vault/subir", files=files, data=data, headers=tesorero_headers)
        assert resp.status_code == 400
        assert "no permitida" in resp.json()["detail"].lower()

    def test_subir_archivo_muy_grande(self, cliente, tesorero_headers):
        """Rechaza archivos > 50 MB."""
        large_content = b"X" * (51 * 1024 * 1024)  # 51 MB
        files = {"archivo": ("grande.pdf", io.BytesIO(large_content), "application/pdf")}
        data = {"tipo_documento": "COMPROBANTE"}

        resp = cliente.post("/vault/subir", files=files, data=data, headers=tesorero_headers)
        assert resp.status_code == 400
        assert "demasiado grande" in resp.json()["detail"].lower()

    def test_subir_sin_autenticacion(self, cliente):
        """Sin login → 403/redirect a login."""
        pdf_content = b"%PDF-1.4 test"
        files = {"archivo": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")}
        data = {"tipo_documento": "COMPROBANTE"}

        resp = cliente.post("/vault/subir", files=files, data=data)
        # El endpoint requiere autenticación → redirige a login (303)
        # TestClient sigue la redirección automáticamente, verificamos en history
        assert any(r.status_code == 303 for r in resp.history)
        # La respuesta final es la página de login (200)
        assert resp.status_code == 200
        assert "Ingresar" in resp.text

    def test_descargar_documento_propietario(self, cliente, tesorero_headers, db):
        """Tesorero puede descargar documento que subió."""
        # Subir
        pdf_content = b"%PDF-1.4 contenido original"
        files = {"archivo": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")}
        data = {"tipo_documento": "COMPROBANTE"}
        resp = cliente.post("/vault/subir", files=files, data=data, headers=tesorero_headers)
        doc_id = resp.json()["id"]

        # Descargar
        resp = cliente.get(f"/vault/{doc_id}/descargar", headers=tesorero_headers)
        assert resp.status_code == 200
        assert resp.content == pdf_content
        assert resp.headers["content-type"] == "application/pdf"
        assert "attachment" in resp.headers["content-disposition"]

    def test_ver_documento_inline(self, cliente, tesorero_headers, db):
        """Vista inline (Content-Disposition: inline)."""
        pdf_content = b"%PDF-1.4 inline test"
        files = {"archivo": ("inline.pdf", io.BytesIO(pdf_content), "application/pdf")}
        data = {"tipo_documento": "COMPROBANTE"}
        resp = cliente.post("/vault/subir", files=files, data=data, headers=tesorero_headers)
        doc_id = resp.json()["id"]

        resp = cliente.get(f"/vault/{doc_id}/ver", headers=tesorero_headers)
        assert resp.status_code == 200
        assert resp.content == pdf_content
        assert "inline" in resp.headers["content-disposition"]

    def test_descargar_documento_inexistente(self, cliente, tesorero_headers):
        """Descargar ID inexistente → 404."""
        resp = cliente.get("/vault/99999/descargar", headers=tesorero_headers)
        assert resp.status_code == 404

    def test_auditoria_documento(self, cliente, tesorero_headers, db):
        """Endpoint auditoría retorna historial de accesos."""
        pdf_content = b"%PDF-1.4 audit test"
        files = {"archivo": ("audit.pdf", io.BytesIO(pdf_content), "application/pdf")}
        data = {"tipo_documento": "COMPROBANTE"}
        resp = cliente.post("/vault/subir", files=files, data=data, headers=tesorero_headers)
        doc_id = resp.json()["id"]

        # Descargar un par de veces
        cliente.get(f"/vault/{doc_id}/descargar", headers=tesorero_headers)
        cliente.get(f"/vault/{doc_id}/descargar", headers=tesorero_headers)

        # Consultar auditoría
        resp = cliente.get(f"/vault/auditoria/{doc_id}", headers=tesorero_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["documento_id"] == doc_id
        assert len(data["accesos"]) >= 2
        for acceso in data["accesos"]:
            assert "usuario_id" in acceso
            assert "accion" in acceso
            assert "timestamp" in acceso

    def test_eliminar_documento_soft_tesorero(self, cliente, tesorero_headers, db):
        """Tesorero puede soft-delete (marca auditoría)."""
        pdf_content = b"%PDF-1.4 to delete"
        files = {"archivo": ("delete.pdf", io.BytesIO(pdf_content), "application/pdf")}
        data = {"tipo_documento": "OTRO"}
        resp = cliente.post("/vault/subir", files=files, data=data, headers=tesorero_headers)
        doc_id = resp.json()["id"]

        resp = cliente.delete(f"/vault/{doc_id}", headers=tesorero_headers)
        assert resp.status_code == 204

        # Verificar que existe pero tiene auditoría de eliminación
        doc = db.query(DocumentoVault).get(doc_id)
        assert doc is not None
        accesos = doc.obtener_accesos()
        assert any(a["accion"] == "ELIMINACION" for a in accesos)

    def test_eliminar_hard_solo_admin(self, cliente, admin_user, tesorero_user, db):
        """Hard delete solo para Admin."""
        # Login as admin
        resp = _sesion(cliente, admin_user.email, "admin123")
        assert resp.status_code == 303
        admin_cookie = resp.headers.get("set-cookie", "")
        admin_headers = {"Cookie": admin_cookie}

        # Tesorero sube archivo
        tesorero_resp = _sesion(cliente, tesorero_user.email, "tesorero123")
        assert tesorero_resp.status_code == 303
        tesorero_cookie = tesorero_resp.headers.get("set-cookie", "")
        tesorero_headers = {"Cookie": tesorero_cookie}

        pdf_content = b"%PDF-1.4 hard delete"
        files = {"archivo": ("hard.pdf", io.BytesIO(pdf_content), "application/pdf")}
        data = {"tipo_documento": "OTRO"}
        resp = cliente.post("/vault/subir", files=files, data=data, headers=tesorero_headers)
        doc_id = resp.json()["id"]

        # Tesorero intenta hard delete → 403
        resp = cliente.delete(f"/vault/{doc_id}?hard=true", headers=tesorero_headers)
        assert resp.status_code == 403

        # Admin hace hard delete → 204
        resp = cliente.delete(f"/vault/{doc_id}?hard=true", headers=admin_headers)
        assert resp.status_code == 204

        # Verificar que ya no existe en BD
        doc = db.query(DocumentoVault).get(doc_id)
        assert doc is None


class TestRotacionMasterKeyEndpoints:
    """Tests de rotación de MK via API (Admin only)."""

    def test_rotar_master_key_invalida(self, cliente, admin_user):
        """MK B64 inválida → 400."""
        resp = _sesion(cliente, admin_user.email, "admin123")
        assert resp.status_code == 303
        admin_cookie = resp.headers.get("set-cookie", "")
        admin_headers = {"Cookie": admin_cookie}

        resp = cliente.post("/vault/rotar-master-key", data={"nueva_mk_b64": "invalido"}, headers=admin_headers)
        assert resp.status_code == 400

    def test_rotar_master_key_valida_inicia_task(self, cliente, admin_user, db):
        """MK válida inicia task y retorna task_id."""
        from app.core.crypto import derive_master_key, MasterKeyData

        resp = _sesion(cliente, admin_user.email, "admin123")
        assert resp.status_code == 303
        admin_cookie = resp.headers.get("set-cookie", "")
        admin_headers = {"Cookie": admin_cookie}

        # Generar MK válida
        mk_data = derive_master_key("nueva-password-para-test", b"newsalt123456789")
        nueva_mk_b64 = mk_data.to_b64()

        resp = cliente.post("/vault/rotar-master-key", data={"nueva_mk_b64": nueva_mk_b64}, headers=admin_headers)
        assert resp.status_code == 202
        data = resp.json()
        assert "task_id" in data
        assert data["estado"] == "iniciando"

        # Consultar estado
        task_id = data["task_id"]
        resp = cliente.get(f"/vault/rotar-master-key/{task_id}", headers=admin_headers)
        assert resp.status_code == 200
        # Estado puede ser completado o ejecutando (async)


class TestVerificacionIntegridadEndpoint:
    """Tests de verificación de integridad via API."""

    def test_verificar_integridad_admin(self, cliente, admin_user, db):
        """Admin puede verificar integridad."""
        resp = _sesion(cliente, admin_user.email, "admin123")
        assert resp.status_code == 303
        admin_cookie = resp.headers.get("set-cookie", "")
        admin_headers = {"Cookie": admin_cookie}

        # Crear algunos docs via service para test
        from app.services.vault import get_vault_service
        vault = get_vault_service(db)
        for i in range(3):
            vault.guardar(
                f"Doc {i}".encode(), f"doc{i}.bin", "application/octet-stream",
                TipoDocumento.OTRO, subido_por=admin_user.id
            )

        resp = cliente.post("/vault/verificar-integridad", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 3
        assert data["ok"] >= 3
        assert "porcentaje_ok" in data

    def test_verificar_integridad_con_limite(self, cliente, admin_user, db):
        """Límite en verificación funciona via API."""
        resp = _sesion(cliente, admin_user.email, "admin123")
        assert resp.status_code == 303
        admin_cookie = resp.headers.get("set-cookie", "")
        admin_headers = {"Cookie": admin_cookie}

        # Crear 3 documentos para probar el límite
        from app.services.vault import get_vault_service
        vault = get_vault_service(db)
        for i in range(3):
            vault.guardar(
                f"Doc {i}".encode(), f"doc{i}.bin", "application/octet-stream",
                TipoDocumento.OTRO, subido_por=admin_user.id
            )

        resp = cliente.post("/vault/verificar-integridad?limit=2", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2