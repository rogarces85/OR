#!/usr/bin/env python3
"""Genera una Master Key para la bóveda y muestra cómo configurarla.

Uso:
    python scripts/vault/generar_master_key.py

Genera:
- Master Key (32 bytes) derivada de password aleatorio + salt
- Output en formato B64 (salt + key) para .env
- Guarda .env.vault.example con la variable MASTER_KEY_B64
"""

from __future__ import annotations

import secrets
from pathlib import Path

from app.core.crypto import MasterKeyData, derive_master_key

VAULT_DIR = Path(__file__).resolve().parent.parent.parent / "scripts" / "vault"
ENV_EXAMPLE = VAULT_DIR / ".env.vault.example"


def main() -> None:
    print("=" * 60)
    print("GENERADOR DE MASTER KEY - BÓVEDA OSORNO RUNNERS")
    print("=" * 60)
    print()

    # 1. Generar password aleatorio fuerte (para derivación PBKDF2)
    password = secrets.token_urlsafe(48)  # 64 chars aprox
    print(f"Password generado (guárdalo en gestor de contraseñas):")
    print(f"  {password}")
    print()

    # 2. Derivar Master Key
    mk_data = derive_master_key(password)
    print(f"Master Key derivada:")
    print(f"  Key (hex):     {mk_data.key.hex()}")
    print(f"  Salt (hex):    {mk_data.salt.hex()}")
    print(f"  Iteraciones:   {mk_data.iterations:,}")
    print()

    # 3. Formato B64 para .env (salt + key)
    mk_b64 = mk_data.to_b64()
    print(f"MASTER_KEY_B64 (para .env):")
    print(f"  {mk_b64}")
    print()

    # 4. Guardar .env.vault.example
    contenido = f"""# Master Key de la bóveda - GENERADA AUTOMÁTICAMENTE
# Ejecutar: python scripts/vault/generar_master_key.py
# ¡NO COMMITEAR ESTE ARCHIVO! Copiar MASTER_KEY_B64 a tu .env real

MASTER_KEY_B64={mk_b64}

# Ruta de la bóveda (relativa al root del proyecto)
VAULT_PATH=./vault

# Deduplicación por contenido (SHA-256)
VAULT_DEDUP_ENABLED=True
"""
    ENV_EXAMPLE.write_text(contenido)
    print(f"Archivo de ejemplo guardado en: {ENV_EXAMPLE}")
    print()

    # 5. Instrucciones
    print("PRÓXIMOS PASOS:")
    print("  1. Copia MASTER_KEY_B64 a tu archivo .env")
    print("  2. Guarda el PASSWORD en tu gestor de contraseñas (Bitwarden, 1Password, etc.)")
    print("  3. Ejecuta la migración: alembic upgrade head (o python -m app.database)")
    print("  4. Verifica: python scripts/vault/verificar_integridad.py")
    print()
    print("IMPORTANTE:")
    print("  - La Master Key NUNCA debe ir en logs, repositorio, ni BD")
    print("  - Haz backup del password en 2 ubicaciones físicas + 1 digital cifrada")
    print("  - Rotación anual: python scripts/vault/rotar_master_key.py --nueva-mk <NUEVA_B64>")
    print()
    print("=" * 60)


if __name__ == "__main__":
    main()