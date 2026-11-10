#!/usr/bin/env python3
"""Exporta backup completo de la bóveda (tarball .tar.gz).

Uso:
    python scripts/vault/backup_vault.py --destino ./backups/vault_backup_20251110.tar.gz [--sin-archivos]

Incluye:
- manifest.json (metadatos de todos los documentos)
- master_key.enc (MK cifrada con age/GPG - placeholder)
- archivos/ (estructura completa del vault, opcional)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Asegurar que app/ está en el path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.config import get_settings
from app.core.crypto import MasterKeyData
from app.database import SessionLocal
from app.services.vault import VaultService


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Exporta backup de la bóveda",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--destino", required=True, help="Ruta del archivo .tar.gz de salida"
    )
    parser.add_argument(
        "--sin-archivos", action="store_true", help="Solo manifest + MK (sin archivos físicos)"
    )
    parser.add_argument(
        "--vault-path", default=None, help="Ruta del vault (default: settings.vault_path)"
    )
    args = parser.parse_args()

    settings = get_settings()
    db = SessionLocal()

    try:
        vault_path = Path(args.vault_path).resolve() if args.vault_path else Path(settings.vault_path).resolve()
        mk_data = MasterKeyData.from_b64(settings.master_key_b64)

        vault = VaultService(db, mk_data.key, vault_path)

        destino = Path(args.destino).resolve()
        destino.parent.mkdir(parents=True, exist_ok=True)

        print(f"Exportando backup a {destino}...")
        print(f"Vault: {vault_path}")
        print(f"Incluir archivos: {not args.sin_archivos}")

        # El service ya tiene el método exportar_backup
        archivo_backup = vault.exportar_backup(
            destino,
            incluir_archivos=not args.sin_archivos,
            cifrar_mk_con=None,  # TODO: implementar age/GPG
        )

        size_mb = archivo_backup.stat().st_size / (1024 * 1024)
        print(f"✅ Backup completado: {archivo_backup} ({size_mb:.2f} MB)")
        print()
        print("Para restaurar:")
        print("  1. Descomprime: tar -xzf vault_backup.tar.gz")
        print("  2. Desencripta MK (age/GPG)")
        print("  3. Copia archivos/ a vault_path")
        print("  4. Importa manifest.json a BD (script por hacer)")
        return 0

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())