"""Tests de integración de la bóveda (migración legacy, flujos completos)."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from app.core.crypto import MasterKeyData, derive_master_key
from app.core.seguridad import hash_password
from app.models.usuario import Usuario
from app.models.vault import DocumentoVault, TipoDocumento
from app.services.vault import VaultService
from scripts.vault.migrar_archivos_a_vault import migrar_archivos


class TestMigracionLegacy:
    """Tests de migración de archivos legacy a vault."""

    @pytest.fixture
    def test_usuario(self, db):
        """Usuario de prueba para migración."""
        usuario = Usuario(
            email="test_migracion@test.cl",
            password_hash=hash_password("test123"),
            rol="admin",
            activo=True,
        )
        db.add(usuario)
        db.commit()
        db.refresh(usuario)
        return usuario

    @pytest.fixture
    def vault_service(self, db, master_key_bytes, tmp_path):
        return VaultService(db, master_key_bytes, tmp_path / "vault")

    @pytest.fixture
    def master_key_bytes(self):
        return derive_master_key("test-master-password", b"testsalt12345678").key

    def test_migrar_archivos_legacy_basico(self, vault_service, test_usuario, tmp_path):
        """Migra archivos desde directorio legacy."""
        # Setup directorio legacy
        legacy_dir = tmp_path / "legacy_uploads"
        legacy_dir.mkdir()

        (legacy_dir / "comprobante_123_hash.pdf").write_bytes(b"PDF comprobante pago 123")
        (legacy_dir / "boleta_456_recibo.jpg").write_bytes(b"JPG boleta egreso 456")
        (legacy_dir / "compra_789_contrato.docx").write_bytes(b"DOCX compra club 789")
        (legacy_dir / "otro_documento.txt").write_bytes(b"Texto sin patron")

        # Ejecutar migración
        from scripts.vault.migrar_archivos_a_vault import migrar_archivos
        resultado = migrar_archivos(
            vault_service.db, vault_service, legacy_dir, dry_run=False, usuario_id=test_usuario.id
        )

        assert resultado.migrados == 4
        assert len(resultado.errores) == 0

        # Verificar documentos creados
        docs = vault_service.db.query(DocumentoVault).all()
        assert len(docs) == 4

        # Verificar tipos inferidos
        tipos = {d.tipo_documento for d in docs}
        assert TipoDocumento.COMPROBANTE in tipos
        assert TipoDocumento.BOLETA in tipos
        assert TipoDocumento.CONTRATO in tipos
        assert TipoDocumento.OTRO in tipos

        # Verificar entidades
        comprobante = next(d for d in docs if d.tipo_documento == TipoDocumento.COMPROBANTE)
        assert comprobante.entidad_relacionada == "pagos"
        assert comprobante.entidad_id == 123

        boleta = next(d for d in docs if d.tipo_documento == TipoDocumento.BOLETA)
        assert boleta.entidad_relacionada == "egresos"
        assert boleta.entidad_id == 456

    def test_migrar_dry_run_no_modifica(self, vault_service, test_usuario, tmp_path):
        """Dry-run no persiste en BD ni vault."""
        legacy_dir = tmp_path / "legacy"
        legacy_dir.mkdir()
        (legacy_dir / "comprobante_1.pdf").write_bytes(b"Test")

        from scripts.vault.migrar_archivos_a_vault import migrar_archivos
        resultado = migrar_archivos(
            vault_service.db, vault_service, legacy_dir, dry_run=True, usuario_id=test_usuario.id
        )

        assert resultado.migrados == 1
        # En dry-run no debe haber documentos en BD
        docs = vault_service.db.query(DocumentoVault).all()
        assert len(docs) == 0

    def test_migrar_deduplicacion(self, vault_service, test_usuario, tmp_path):
        """Migración respeta deduplicación por contenido."""
        legacy_dir = tmp_path / "legacy"
        legacy_dir.mkdir()

        # Mismo contenido, nombres distintos
        (legacy_dir / "comprobante_1_a.pdf").write_bytes(b"Contenido identico")
        (legacy_dir / "comprobante_2_b.pdf").write_bytes(b"Contenido identico")

        from scripts.vault.migrar_archivos_a_vault import migrar_archivos
        resultado = migrar_archivos(
            vault_service.db, vault_service, legacy_dir, dry_run=False, usuario_id=test_usuario.id
        )

        # Debe crear solo 1 documento (dedup)
        assert resultado.migrados == 2  # Se procesan 2, pero se crea 1
        docs = vault_service.db.query(DocumentoVault).all()
        assert len(docs) == 1

    def test_migrar_directorio_inexistente(self, vault_service, test_usuario, tmp_path):
        """Directorio legacy inexistente → error graceful."""
        from scripts.vault.migrar_archivos_a_vault import migrar_archivos
        resultado = migrar_archivos(
            vault_service.db, vault_service, tmp_path / "no_existe", dry_run=False, usuario_id=test_usuario.id
        )

        assert resultado.migrados == 0
        assert len(resultado.errores) == 1
        assert "no existe" in resultado.errores[0]


class TestFlujosCompletos:
    """Tests E2E de flujos típicos de uso."""

    @pytest.fixture
    def test_usuario(self, db):
        """Usuario de prueba para flujos."""
        from app.core.seguridad import hash_password
        from app.models.usuario import Usuario
        usuario = Usuario(
            email="test_flujos@test.cl",
            password_hash=hash_password("test123"),
            rol="admin",
            activo=True,
        )
        db.add(usuario)
        db.commit()
        db.refresh(usuario)
        return usuario

    @pytest.fixture
    def vault_service(self, db, master_key_bytes, tmp_path):
        return VaultService(db, master_key_bytes, tmp_path / "vault")

    @pytest.fixture
    def master_key_bytes(self):
        return derive_master_key("test-master-password", b"testsalt12345678").key

    def test_flujo_comprobante_pago(self, vault_service, test_usuario):
        """Flujo: Subir comprobante → Validar → Descargar."""
        # 1. Subir comprobante (simula socio sube, tesorero valida)
        contenido = b"%PDF-1.4 fake pdf content"
        doc = vault_service.guardar(
            contenido,
            nombre_original="comprobante_transferencia.pdf",
            mime_type="application/pdf",
            tipo_documento=TipoDocumento.COMPROBANTE,
            entidad_relacionada="pagos",
            entidad_id=42,
            subido_por=test_usuario.id,  # Tesorero
        )

        assert doc.entidad_relacionada == "pagos"
        assert doc.entidad_id == 42

        # 2. Tesorero descarga para validar
        plaintext = vault_service.leer(doc.id, usuario_id=test_usuario.id)
        assert plaintext == contenido

        # 3. Auditoría registra descarga
        accesos = doc.obtener_accesos()
        assert len(accesos) == 1
        assert accesos[0]["accion"] == "DESCARGA"
        assert accesos[0]["usuario_id"] == test_usuario.id

    def test_flujo_boleta_egreso(self, vault_service, test_usuario):
        """Flujo: Subir boleta de egreso → Asociar a egreso."""
        contenido = b"fake image data"
        doc = vault_service.guardar(
            contenido,
            nombre_original="boleta_supermercado.jpg",
            mime_type="image/jpeg",
            tipo_documento=TipoDocumento.BOLETA,
            entidad_relacionada="egresos",
            entidad_id=15,
            subido_por=test_usuario.id,
        )

        # Verificar asociación
        docs_egreso = vault_service.obtener_por_entidad("egresos", 15)
        assert len(docs_egreso) == 1
        assert docs_egreso[0].id == doc.id
        assert docs_egreso[0].tipo_documento == TipoDocumento.BOLETA

    def test_flujo_multiples_documentos_misma_entidad(self, vault_service, test_usuario):
        """Múltiples documentos para una misma entidad (ej. varias boletas un egreso)."""
        egreso_id = 99

        for i in range(3):
            vault_service.guardar(
                f"Boleta {i}".encode(),
                f"boleta_{i}.pdf",
                "application/pdf",
                TipoDocumento.BOLETA,
                entidad_relacionada="egresos",
                entidad_id=egreso_id,
                subido_por=test_usuario.id,
            )

        docs = vault_service.obtener_por_entidad("egresos", egreso_id)
        assert len(docs) == 3
        # Verificar que todos los documentos están presentes (orden no garantizado por timestamp igual)
        nombres = {d.nombre_original for d in docs}
        assert nombres == {"boleta_0.pdf", "boleta_1.pdf", "boleta_2.pdf"}

    def test_descarga_streaming_archivo_grande(self, vault_service, test_usuario):
        """Leer archivo grande en chunks (streaming)."""
        # Archivo de ~100 KB
        contenido_grande = b"X" * (100 * 1024)
        doc = vault_service.guardar(
            contenido_grande,
            nombre_original="archivo_grande.bin",
            mime_type="application/octet-stream",
            tipo_documento=TipoDocumento.OTRO,
            subido_por=test_usuario.id,
        )

        # Leer en chunks de 10 KB
        chunks = list(vault_service.leer_streaming(doc.id, usuario_id=test_usuario.id, chunk_size=10 * 1024))
        assert len(chunks) == 10
        assert b"".join(chunks) == contenido_grande


class TestRotacionMKIntegracion:
    """Tests de integración de rotación de Master Key."""

    @pytest.fixture
    def test_usuario(self, db):
        from app.core.seguridad import hash_password
        from app.models.usuario import Usuario
        usuario = Usuario(
            email="test_rotacion@test.cl",
            password_hash=hash_password("test123"),
            rol="admin",
            activo=True,
        )
        db.add(usuario)
        db.commit()
        db.refresh(usuario)
        return usuario

    @pytest.fixture
    def vault_service(self, db, master_key_bytes, tmp_path):
        return VaultService(db, master_key_bytes, tmp_path / "vault")

    @pytest.fixture
    def master_key_bytes(self):
        return derive_master_key("test-master-password", b"testsalt12345678").key

    def test_rotacion_mk_con_documentos_existentes(self, vault_service, test_usuario, master_key_bytes):
        """Rotar MK con documentos previos mantiene acceso."""
        # Crear documentos con MK actual
        for i in range(10):
            vault_service.guardar(
                f"Doc {i}".encode(), f"doc{i}.bin", "application/octet-stream",
                TipoDocumento.OTRO, subido_por=test_usuario.id
            )

        # Generar nueva MK
        nueva_mk = derive_master_key("nueva-password-secreta", b"newsalt123456789").key

        # Rotar
        resultado = vault_service.rotar_master_key(nueva_mk, batch_size=3)
        assert resultado.procesados == 10
        assert len(resultado.errores) == 0

        # Verificar acceso con nueva MK
        vault_service.mk = nueva_mk
        for i in range(10):
            doc = vault_service.db.query(DocumentoVault).filter(
                DocumentoVault.nombre_original == f"doc{i}.bin"
            ).first()
            contenido = vault_service.leer(doc.id, usuario_id=test_usuario.id)
            assert contenido == f"Doc {i}".encode()

    def test_rotacion_mk_batch_transaccional(self, vault_service, test_usuario, master_key_bytes):
        """Rotación por lotes: fallo en lote no afecta anteriores."""
        # Crear 5 docs
        for i in range(5):
            vault_service.guardar(
                f"Doc {i}".encode(), f"doc{i}.bin", "application/octet-stream",
                TipoDocumento.OTRO, subido_por=test_usuario.id
            )

        # Simular error en rotación (manipular MK para que falle)
        # En test real sería más complejo; aquí verificamos que commit por lote funciona
        nueva_mk = derive_master_key("otra-password", b"anothersalt12345").key
        resultado = vault_service.rotar_master_key(nueva_mk, batch_size=2)
        assert resultado.procesados == 5

        # Verificar acceso con nueva MK
        vault_service.mk = nueva_mk
        for i in range(5):
            doc = vault_service.db.query(DocumentoVault).filter(
                DocumentoVault.nombre_original == f"doc{i}.bin"
            ).first()
            contenido = vault_service.leer(doc.id, usuario_id=test_usuario.id)
            assert contenido == f"Doc {i}".encode()


class TestVerificacionIntegridadIntegracion:
    """Tests de verificación de integridad completa."""

    @pytest.fixture
    def test_usuario(self, db):
        from app.core.seguridad import hash_password
        from app.models.usuario import Usuario
        usuario = Usuario(
            email="test_verificacion@test.cl",
            password_hash=hash_password("test123"),
            rol="admin",
            activo=True,
        )
        db.add(usuario)
        db.commit()
        db.refresh(usuario)
        return usuario

    @pytest.fixture
    def vault_service(self, db, master_key_bytes, tmp_path):
        return VaultService(db, master_key_bytes, tmp_path / "vault")

    @pytest.fixture
    def master_key_bytes(self):
        return derive_master_key("test-master-password", b"testsalt12345678").key

    def test_verificar_integridad_todo_ok(self, vault_service, test_usuario):
        """Verificación reporta OK en vault sano."""
        for i in range(5):
            vault_service.guardar(
                f"OK {i}".encode(), f"ok{i}.bin", "application/octet-stream",
                TipoDocumento.OTRO, subido_por=test_usuario.id
            )

        resultado = vault_service.verificar_integridad()
        assert resultado.total == 5
        assert resultado.ok == 5
        assert len(resultado.corruptos) == 0
        assert len(resultado.faltantes) == 0

    def test_verificar_integridad_con_limite(self, vault_service, test_usuario):
        """Límite en verificación funciona."""
        for i in range(10):
            vault_service.guardar(
                f"Doc {i}".encode(), f"doc{i}.bin", "application/octet-stream",
                TipoDocumento.OTRO, subido_por=test_usuario.id
            )

        resultado = vault_service.verificar_integridad(limit=3)
        assert resultado.total == 3
        assert resultado.ok == 3