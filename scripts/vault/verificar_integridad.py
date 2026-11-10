#!/usr/bin/env python3
"""Verifica la integridad de todos los documentos en la bóveda.

Uso:
    python scripts/vault/verificar_integridad.py [--limit 100] [--json]

Verifica:
- Descifrado exitoso con MK actual
- Hash SHA-256 coincide con el registrado
- Archivo físico existe en filesystem
"""

from __future__ import annotations

import argparse
import json
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
        description="Verifica integridad de la bóveda de documentos",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="Límite de documentos a verificar (default: todos)"
    )
    parser.add_argument(
        "--json", action="store_true", help="Salida en JSON para parsing"
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

        print(f"Verificando integridad de la bóveda en {vault_path}...")
        if args.limit:
            print(f"Límite: {args.limit} documentos")

        resultado = vault.verificar_integridad(limit=args.limit)

        if args.json:
            output = {
                "total": resultado.total,
                "ok": resultado.ok,
                "corruptos": resultado.corruptos,
                "faltantes": resultado.faltantes,
                "porcentaje_ok": round(resultado.ok / resultado.total * 100, 2) if resultado.total else 100,
            }
            print(json.dumps(output, ensure_ascii=False, indent=2))
        else:
            print()
            print("=" * 50)
            print("RESULTADO VERIFICACIÓN INTEGRIDAD")
            print("=" * 50)
            print(f"Total documentos:     {resultado.total}")
            print(f"OK (integridad OK):   {resultado.ok}")
            print(f"Corruptos:            {len(resultado.corruptos)}")
            print(f"Archivos faltantes:   {len(resultado.faltantes)}")
            pct = round(resultado.ok / resultado.total * 100, 2) if resultado.total else 100
            print(f"Porcentaje OK:        {pct}%")

            if resultado.corruptos:
                print()
                print("DOCUMENTOS CORRUPTOS:")
                for c in resultado.corruptos:
                    print(f"  Doc {c['doc_id']}: {c['error']}")

            if resultado.faltantes:
                print()
                print("ARCHIVOS FÍSICOS FALTANTES:")
                for f in resultado.faltantes:
                    print(f"  Doc {f['doc_id']}: {f['ruta']}")

            print()
            if resultado.corruptos or resultado.faltantes:
                print("❌ HAY PROBLEMAS DE INTEGRIDAD")
                return 1
            else:
                print("✅ TODOS LOS DOCUMENTOS ÍNTEGROS")
                return 0

    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())