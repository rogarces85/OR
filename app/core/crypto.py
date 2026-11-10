"""Utilidades criptográficas para la bóveda de documentos.

Provee:
- Derivación de Master Key (PBKDF2-HMAC-SHA256, 100k iteraciones)
- Generación de Document Keys (32 bytes aleatorios)
- Cifrado/descifrado AES-256-GCM (authenticated encryption)
- Hash SHA-256 para integridad y deduplicación
"""

from __future__ import annotations

import hashlib
import os
import secrets
from base64 import b64decode, b64encode
from dataclasses import dataclass

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

# Constantes
PBKDF2_ITERATIONS = 100_000
SALT_BYTES = 16
DK_BYTES = 32
NONCE_BYTES = 12
TAG_BYTES = 16
MASTER_KEY_BYTES = 32


class VaultCryptoError(Exception):
    """Error base de operaciones criptográficas del vault."""
    pass


class ClaveInvalidaError(VaultCryptoError):
    """Master Key o Document Key inválida."""
    pass


class ArchivoCorruptoError(VaultCryptoError):
    """Fallo de integridad (tag GCM inválido) al descifrar."""
    pass


@dataclass(frozen=True)
class MasterKeyData:
    """Master Key derivado + salt para almacenamiento/rotación."""
    key: bytes           # 32 bytes
    salt: bytes          # 16 bytes
    iterations: int = PBKDF2_ITERATIONS

    def to_b64(self) -> str:
        """Serializa MK+salt+iteraciones en base64 para .env"""
        return b64encode(self.salt + self.key).decode()

    @classmethod
    def from_b64(cls, b64_string: str) -> MasterKeyData:
        """Deserializa desde base64 (formato: salt(16) + key(32))"""
        raw = b64decode(b64_string)
        if len(raw) != SALT_BYTES + MASTER_KEY_BYTES:
            raise ClaveInvalidaError(
                f"Master Key B64 inválida: se esperaban {SALT_BYTES + MASTER_KEY_BYTES} bytes, got {len(raw)}"
            )
        return cls(salt=raw[:SALT_BYTES], key=raw[SALT_BYTES:])


def derive_master_key(password: str, salt: bytes | None = None) -> MasterKeyData:
    """Deriva una Master Key desde una contraseña usando PBKDF2-HMAC-SHA256.

    Args:
        password: Contraseña maestra (string fuerte, ej. 32+ chars aleatorios)
        salt: Salt de 16 bytes (si None, genera uno nuevo)

    Returns:
        MasterKeyData con key (32 bytes), salt (16 bytes), iterations
    """
    if salt is None:
        salt = secrets.token_bytes(SALT_BYTES)
    elif len(salt) != SALT_BYTES:
        raise ClaveInvalidaError(f"Salt debe ser {SALT_BYTES} bytes")

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=MASTER_KEY_BYTES,
        salt=salt,
        iterations=PBKDF2_ITERATIONS,
    )
    key = kdf.derive(password.encode("utf-8"))
    return MasterKeyData(key=key, salt=salt)


def generate_document_key() -> bytes:
    """Genera una Document Key aleatoria de 32 bytes (AES-256)."""
    return secrets.token_bytes(DK_BYTES)


def encrypt_aes_gcm(key: bytes, plaintext: bytes, associated_data: bytes | None = None) -> tuple[bytes, bytes]:
    """Cifra con AES-256-GCM.

    Args:
        key: Clave de 32 bytes
        plaintext: Datos a cifrar
        associated_data: Datos adicionales autenticados (AAD) - opcional

    Returns:
        Tupla (nonce: 12 bytes, ciphertext_con_tag: bytes)
        El ciphertext incluye el tag GCM de 16 bytes al final.
    """
    if len(key) != DK_BYTES:
        raise ClaveInvalidaError(f"Clave debe ser {DK_BYTES} bytes")
    nonce = secrets.token_bytes(NONCE_BYTES)
    cipher = AESGCM(key)
    ciphertext = cipher.encrypt(nonce, plaintext, associated_data)
    return nonce, ciphertext  # ciphertext ya incluye tag al final (len + 16)


def decrypt_aes_gcm(key: bytes, nonce: bytes, ciphertext_with_tag: bytes, associated_data: bytes | None = None) -> bytes:
    """Descifra con AES-256-GCM y verifica integridad.

    Args:
        key: Clave de 32 bytes
        nonce: Nonce de 12 bytes usado al cifrar
        ciphertext_with_tag: Texto cifrado + tag GCM (16 bytes al final)
        associated_data: Datos adicionales autenticados (AAD) - opcional

    Returns:
        Plaintext original

    Raises:
        ArchivoCorruptoError: Si el tag GCM no coincide (integridad violada)
        ClaveInvalidaError: Si la clave o nonce tienen tamaños incorrectos
    """
    if len(key) != DK_BYTES:
        raise ClaveInvalidaError(f"Clave debe ser {DK_BYTES} bytes")
    if len(nonce) != NONCE_BYTES:
        raise ClaveInvalidaError(f"Nonce debe ser {NONCE_BYTES} bytes")
    if len(ciphertext_with_tag) < TAG_BYTES:
        raise ArchivoCorruptoError("Ciphertext demasiado corto para contener tag GCM")

    try:
        cipher = AESGCM(key)
        return cipher.decrypt(nonce, ciphertext_with_tag, associated_data)
    except Exception as e:
        # cryptography lanza InvalidTag en fallo de integridad
        raise ArchivoCorruptoError("Falló verificación de integridad (tag GCM inválido)") from e


def encrypt_dk_with_mk(master_key: bytes, document_key: bytes) -> tuple[bytes, bytes]:
    """Cifra una Document Key con la Master Key.

    Returns:
        (nonce_dk: 12 bytes, dk_enc: 48 bytes = 32 cipher + 16 tag)
    """
    return encrypt_aes_gcm(master_key, document_key)


def decrypt_dk_with_mk(master_key: bytes, nonce_dk: bytes, dk_enc: bytes) -> bytes:
    """Descifra una Document Key con la Master Key."""
    return decrypt_aes_gcm(master_key, nonce_dk, dk_enc)


def sha256_bytes(data: bytes) -> str:
    """Calcula SHA-256 hex digest de bytes (para deduplicación e integridad)."""
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str) -> str:
    """Calcula SHA-256 de un archivo en disco (streaming, bajo memoria)."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


# Utilidades para archivos en vault
VAULT_DIR_MODE = 0o700
VAULT_FILE_MODE = 0o600


def ensure_vault_path(base_path: str, sha256_hex: str) -> str:
    """Genera la ruta relativa en vault: {año}/{mes}/{sha256_primeros4}/{sha256_hex}"""
    from datetime import datetime
    now = datetime.now()
    prefix = sha256_hex[:4]
    rel_path = f"{now.year}/{now.month:02d}/{prefix}/{sha256_hex}"
    abs_path = os.path.join(base_path, rel_path)
    os.makedirs(os.path.dirname(abs_path), mode=VAULT_DIR_MODE, exist_ok=True)
    return rel_path


def write_vault_file(base_path: str, rel_path: str, nonce: bytes, ciphertext: bytes) -> None:
    """Escribe archivo cifrado en vault: [nonce:12][ciphertext+tag]"""
    abs_path = os.path.join(base_path, rel_path)
    with open(abs_path, "wb") as f:
        f.write(nonce + ciphertext)
    os.chmod(abs_path, VAULT_FILE_MODE)


def read_vault_file(base_path: str, rel_path: str) -> tuple[bytes, bytes]:
    """Lee archivo cifrado del vault: retorna (nonce:12, ciphertext_with_tag)"""
    abs_path = os.path.join(base_path, rel_path)
    with open(abs_path, "rb") as f:
        data = f.read()
    if len(data) < NONCE_BYTES + TAG_BYTES:
        raise ArchivoCorruptoError(f"Archivo vault corrupto: {abs_path}")
    return data[:NONCE_BYTES], data[NONCE_BYTES:]