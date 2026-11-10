"""Servicio de la bóveda de documentos cifrados (FT-06).

Provee operaciones de alto nivel:
- guardar(): cifra, deduplica (SHA-256), persiste en FS + BD
- leer(): descifra streaming, registra auditoría
- eliminar(): soft delete (marca + mantiene auditoría)
- rotar_master_key(): batch re-cifra todas las DKs con nueva MK
"""

from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, BinaryIO, Iterator, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.crypto import (
    ArchivoCorruptoError,
    ClaveInvalidaError,
    VaultCryptoError,
    decrypt_aes_gcm,
    decrypt_dk_with_mk,
    encrypt_aes_gcm,
    encrypt_dk_with_mk,
    ensure_vault_path,
    generate_document_key,
    read_vault_file,
    sha256_bytes,
    write_vault_file,
)
from app.config import get_settings
from app.models.vault import DocumentoVault, TipoDocumento

if TYPE_CHECKING:
    from app.models.usuario import Usuario

settings = get_settings()


class VaultError(Exception):
    """Error base del servicio de vault."""
    pass


class DocumentoNoEncontrado(VaultError):
    """Documento no existe en la bóveda."""
    pass


class VaultService:
    """Servicio principal de la bóveda cifrada."""

    def __init__(
        self,
        db: Session,
        master_key: bytes,
        vault_path: Optional[Path] = None,
    ):
        """
        Args:
            db: Sesión de base de datos
            master_key: Master Key de 32 bytes (derivada de MASTER_KEY_B64)
            vault_path: Ruta base del vault (default: settings.vault_path o ./vault)
        """
        self.db = db
        self.mk = master_key
        self.vault_path = vault_path or Path(settings.vault_path).resolve()
        self.vault_path.mkdir(mode=0o700, parents=True, exist_ok=True)

    # -------------------------------------------------------------------------
    # Operaciones principales
    # -------------------------------------------------------------------------

    def guardar(
        self,
        archivo_bytes: bytes,
        nombre_original: str,
        mime_type: str,
        tipo_documento: TipoDocumento,
        *,
        entidad_relacionada: Optional[str] = None,
        entidad_id: Optional[int] = None,
        subido_por: int,
    ) -> DocumentoVault:
        """Guarda un archivo en la bóveda.

        - Calcula SHA-256 del plaintext
        - Si ya existe (deduplicación), retorna el existente
        - Genera DK aleatoria, cifra archivo con DK (AES-GCM)
        - Cifra DK con MK (AES-GCM)
        - Persiste archivo en FS y metadatos en BD

        Args:
            archivo_bytes: Contenido del archivo (plaintext)
            nombre_original: Nombre original del archivo
            mime_type: MIME type detectado (no confiar en extensión)
            tipo_documento: Tipo de documento (enum)
            entidad_relacionada: Tabla relacionada ("pagos", "egresos", etc.)
            entidad_id: ID en la tabla relacionada
            subido_por: ID de usuario que sube

        Returns:
            DocumentoVault creado o existente (deduplicado)
        """
        # 1. Hash del plaintext para deduplicación
        sha256_hash = sha256_bytes(archivo_bytes)
        tamano = len(archivo_bytes)

        # 2. Verificar duplicado por contenido
        existing = self.db.execute(
            select(DocumentoVault).where(DocumentoVault.sha256 == sha256_hash)
        ).scalar_one_or_none()
        if existing:
            return existing

        # 3. Generar Document Key y cifrar archivo
        dk = generate_document_key()
        nonce_archivo, ciphertext = encrypt_aes_gcm(dk, archivo_bytes)
        # ciphertext ya incluye tag GCM al final

        # 4. Cifrar DK con Master Key
        nonce_dk, dk_enc = encrypt_dk_with_mk(self.mk, dk)
        # dk_enc = 32 cipher + 16 tag = 48 bytes
        tag_archivo = ciphertext[-16:]  # GCM tag son los últimos 16 bytes

        # 5. Guardar archivo en vault filesystem
        rel_path = ensure_vault_path(str(self.vault_path), sha256_hash)
        abs_path = self.vault_path / rel_path
        abs_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        write_vault_file(str(self.vault_path), rel_path, nonce_archivo, ciphertext)

        # 6. Registrar en BD
        doc = DocumentoVault(
            sha256=sha256_hash,
            nombre_original=nombre_original,
            mime_type=mime_type,
            tamano_bytes=tamano,
            nonce_dk=nonce_dk,
            dk_enc=dk_enc,
            tag_archivo=tag_archivo,
            ruta_archivo=rel_path,
            tipo_documento=tipo_documento,
            entidad_relacionada=entidad_relacionada,
            entidad_id=entidad_id,
            subido_por=subido_por,
        )
        self.db.add(doc)
        self.db.commit()
        self.db.refresh(doc)
        return doc

    def leer(self, doc_id: int, usuario_id: int) -> bytes:
        """Lee y descifra un documento, registrando auditoría.

        Args:
            doc_id: ID del documento en BD
            usuario_id: ID del usuario que accede (para auditoría)

        Returns:
            Contenido descifrado (plaintext)

        Raises:
            DocumentoNoEncontrado: Si no existe
            ArchivoCorruptoError: Si falla verificación de integridad
        """
        doc = self.db.get(DocumentoVault, doc_id)
        if not doc:
            raise DocumentoNoEncontrado(f"Documento {doc_id} no existe")

        # 1. Descifrar DK con MK
        try:
            dk = decrypt_dk_with_mk(self.mk, doc.nonce_dk, doc.dk_enc)
        except ArchivoCorruptoError as e:
            raise ArchivoCorruptoError(f"Falló descifrado DK del documento {doc_id}") from e

        # 2. Leer archivo cifrado del FS
        try:
            nonce_archivo, ciphertext = read_vault_file(str(self.vault_path), doc.ruta_archivo)
        except FileNotFoundError as e:
            raise DocumentoNoEncontrado(f"Archivo físico no encontrado: {doc.ruta_archivo}") from e

        # 3. Descifrar archivo con DK
        try:
            plaintext = decrypt_aes_gcm(dk, nonce_archivo, ciphertext)
        except ArchivoCorruptoError as e:
            raise ArchivoCorruptoError(f"Falló verificación integridad archivo {doc_id}") from e

        # 4. Verificar integridad (SHA-256 match)
        if sha256_bytes(plaintext) != doc.sha256:
            raise ArchivoCorruptoError(
                f"Hash mismatch documento {doc_id}: contenido alterado"
            )

        # 5. Registrar auditoría
        doc.registrar_acceso(usuario_id, "DESCARGA")
        self.db.commit()

        return plaintext

    def leer_streaming(self, doc_id: int, usuario_id: int, chunk_size: int = 8192) -> Iterator[bytes]:
        """Lee un documento en chunks (streaming) para archivos grandes.

        Nota: AES-GCM requiere descifrar todo el archivo de una vez para
        verificar el tag. Para streaming real se usaría AES-CTR + HMAC,
        pero AES-GCM es aceptable para tamaños típicos (< 50 MB).
        Esta implementación descifra completo y yield chunks.
        """
        plaintext = self.leer(doc_id, usuario_id)
        for i in range(0, len(plaintext), chunk_size):
            yield plaintext[i:i + chunk_size]

    def eliminar(self, doc_id: int, usuario_id: int, *, hard: bool = False) -> bool:
        """Elimina un documento (soft delete por defecto).

        Args:
            doc_id: ID del documento
            usuario_id: ID del usuario que elimina (auditoría)
            hard: Si True, borra archivo físico + registro BD (irreversible)

        Returns:
            True si se eliminó, False si no existía
        """
        doc = self.db.get(DocumentoVault, doc_id)
        if not doc:
            return False

        # Registrar auditoría antes de borrar
        doc.registrar_acceso(usuario_id, "ELIMINACION")
        self.db.commit()

        if hard:
            # Borrar archivo físico
            abs_path = self.vault_path / doc.ruta_archivo
            if abs_path.exists():
                abs_path.unlink()
            # Borrar registro BD
            self.db.delete(doc)
            self.db.commit()
        else:
            # Soft delete: marcar en nombre o añadir flag (aquí solo auditoría)
            # En producción se añadiría columna 'eliminado_en' al modelo
            pass

        return True

    def obtener_por_entidad(
        self, entidad_relacionada: str, entidad_id: int
    ) -> list[DocumentoVault]:
        """Obtiene todos los documentos vinculados a una entidad."""
        return list(self.db.execute(
            select(DocumentoVault).where(
                DocumentoVault.entidad_relacionada == entidad_relacionada,
                DocumentoVault.entidad_id == entidad_id,
            ).order_by(DocumentoVault.subido_en.desc())
        ).scalars().all())

    def obtener_por_tipo(self, tipo: TipoDocumento, limit: int = 100) -> list[DocumentoVault]:
        """Obtiene documentos por tipo (paginado)."""
        return list(self.db.execute(
            select(DocumentoVault)
            .where(DocumentoVault.tipo_documento == tipo)
            .order_by(DocumentoVault.subido_en.desc())
            .limit(limit)
        ).scalars().all())

    def obtener_auditoria(self, doc_id: int) -> list[dict]:
        """Retorna la auditoría de accesos de un documento."""
        doc = self.db.get(DocumentoVault, doc_id)
        if not doc:
            raise DocumentoNoEncontrado(f"Documento {doc_id} no existe")
        return doc.obtener_accesos()

    # -------------------------------------------------------------------------
    # Rotación de Master Key
    # -------------------------------------------------------------------------

    @dataclass
    class RotacionResultado:
        """Resultado de rotación de Master Key."""
        procesados: int
        errores: list[str]
        duracion_segundos: float

    def rotar_master_key(self, nueva_mk: bytes, batch_size: int = 100) -> RotacionResultado:
        """Rota la Master Key: re-cifra todas las DKs con la nueva MK.

        Operación batch, transaccional por lote. La MK actual (self.mk)
        NO se modifica aquí; el caller debe actualizarla tras éxito.

        Args:
            nueva_mk: Nueva Master Key de 32 bytes
            batch_size: Documentos por transacción

        Returns:
            RotacionResultado con estadísticas
        """
        import time
        inicio = time.time()
        errores = []
        procesados = 0

        # Obtener todos los documentos
        docs = list(self.db.execute(
            select(DocumentoVault).order_by(DocumentoVault.id)
        ).scalars().all())

        for i in range(0, len(docs), batch_size):
            lote = docs[i:i + batch_size]
            for doc in lote:
                try:
                    # Descifrar DK con MK actual
                    dk = decrypt_dk_with_mk(self.mk, doc.nonce_dk, doc.dk_enc)
                    # Cifrar DK con nueva MK
                    nonce_dk_nuevo, dk_enc_nuevo = encrypt_dk_with_mk(nueva_mk, dk)
                    # Actualizar en BD
                    doc.nonce_dk = nonce_dk_nuevo
                    doc.dk_enc = dk_enc_nuevo
                    procesados += 1
                except Exception as e:
                    errores.append(f"Doc {doc.id}: {e}")

            # Commit por lote
            self.db.commit()

        duracion = time.time() - inicio
        return self.RotacionResultado(
            procesados=procesados,
            errores=errores,
            duracion_segundos=duracion,
        )

    # -------------------------------------------------------------------------
    # Verificación de integridad
    # -------------------------------------------------------------------------

    @dataclass
    class IntegridadResultado:
        """Resultado de verificación de integridad del vault."""
        total: int
        ok: int
        corruptos: list[dict]
        faltantes: list[dict]

    def verificar_integridad(self, limit: Optional[int] = None) -> IntegridadResultado:
        """Verifica integridad de todos los documentos en el vault.

        - Descifra cada archivo y verifica SHA-256
        - Reporta corruptos (tag GCM fail o hash mismatch)
        - Reporta archivos físicos faltantes

        Args:
            limit: Límite de documentos a verificar (None = todos)

        Returns:
            IntegridadResultado con estadísticas
        """
        query = select(DocumentoVault).order_by(DocumentoVault.id)
        if limit:
            query = query.limit(limit)

        docs = list(self.db.execute(query).scalars().all())
        ok = 0
        corruptos = []
        faltantes = []

        for doc in docs:
            try:
                # Intentar leer (descifra + verifica hash)
                self.leer(doc.id, usuario_id=0)  # usuario_id=0 para no ensuciar auditoría
                ok += 1
            except DocumentoNoEncontrado:
                faltantes.append({"doc_id": doc.id, "ruta": doc.ruta_archivo})
            except ArchivoCorruptoError as e:
                corruptos.append({"doc_id": doc.id, "error": str(e)})
            except Exception as e:
                corruptos.append({"doc_id": doc.id, "error": f"Error inesperado: {e}"})

        return self.IntegridadResultado(
            total=len(docs),
            ok=ok,
            corruptos=corruptos,
            faltantes=faltantes,
        )

    # -------------------------------------------------------------------------
    # Backup / Restore
    # -------------------------------------------------------------------------

    def exportar_backup(
        self,
        destino: Path,
        *,
        incluir_archivos: bool = True,
        cifrar_mk_con: Optional[bytes] = None,  # age/GPG public key para cifrar MK
    ) -> Path:
        """Exporta backup completo del vault.

        Crea un tarball con:
        - manifest.json (lista documentos + metadatos)
        - master_key.enc (MK cifrada con clave pública, opcional)
        - archivos/ (estructura vault/...) si incluir_archivos=True
        """
        import tarfile
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            archivos_dir = tmp_path / "archivos"
            if incluir_archivos:
                archivos_dir.mkdir()

            # 1. Manifest
            docs = list(self.db.execute(select(DocumentoVault)).scalars().all())
            manifest = {
                "version": 1,
                "exportado_en": datetime.utcnow().isoformat() + "Z",
                "total_documentos": len(docs),
                "documentos": [
                    {
                        "id": d.id,
                        "sha256": d.sha256,
                        "nombre_original": d.nombre_original,
                        "mime_type": d.mime_type,
                        "tamano_bytes": d.tamano_bytes,
                        "tipo_documento": d.tipo_documento.value,
                        "entidad_relacionada": d.entidad_relacionada,
                        "entidad_id": d.entidad_id,
                        "subido_por": d.subido_por,
                        "subido_en": d.subido_en.isoformat() if d.subido_en else None,
                        "ruta_archivo": d.ruta_archivo,
                    }
                    for d in docs
                ],
            }
            (tmp_path / "manifest.json").write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2)
            )

            # 2. Master Key cifrada (opcional)
            if cifrar_mk_con:
                # Placeholder: aquí se usaría age/GPG
                # Por ahora solo guardamos aviso
                (tmp_path / "master_key.enc").write_text(
                    "MK_CIFRADA_CON_AGE_O_GPG\n"
                )

            # 3. Archivos físicos
            if incluir_archivos:
                for doc in docs:
                    src = self.vault_path / doc.ruta_archivo
                    if src.exists():
                        dst = archivos_dir / doc.ruta_archivo
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src, dst)

            # 4. Crear tarball
            destino.parent.mkdir(parents=True, exist_ok=True)
            with tarfile.open(destino, "w:gz") as tar:
                tar.add(tmp_path / "manifest.json", arcname="manifest.json")
                if cifrar_mk_con:
                    tar.add(tmp_path / "master_key.enc", arcname="master_key.enc")
                if incluir_archivos:
                    tar.add(archivos_dir, arcname="archivos")

        return destino


def get_vault_service(db: Session) -> VaultService:
    """Factory para obtener VaultService configurado desde settings."""
    from app.core.crypto import MasterKeyData

    settings = get_settings()
    mk_data = MasterKeyData.from_b64(settings.master_key_b64)
    vault_path = Path(settings.vault_path).resolve()
    return VaultService(db, mk_data.key, vault_path)