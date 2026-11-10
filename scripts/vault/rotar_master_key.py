#!/usr/bin/env python3
"""Rota la Master Key de la bóveda (re-cifra todas las Document Keys).

Uso:
    python scripts/vault/rotar_master_key.py --nueva-mk <NUEVA_MK_B64> [--dry-run] [--batch-size 100]

La nueva MK debe generarse con: python scripts/vault/generar_master_key.py
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

# Asegurar que app/ está en el path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.config import get_settings
from app.core.crypto import MasterKeyData
from app.database import SessionLocal, Base
from app.models.vault import DocumentoVault
from app.services.vault import VaultService


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Rota la Master Key de la bóveda (re-cifra todas las DKs)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  # Simulación (dry-run) - no modifica nada
  python scripts/vault/rotar_master_key.py --nueva-mk <B64> --dry-run

  # Rotación real con batch de 50
  python scripts/vault/rotar_master_key.py --nueva-mk <B64> --batch-size 50

  # Generar nueva MK primero:
  python scripts/vault/generar_master_key.py
  # Copiar MASTER_KEY_B64 y usarla aquí
        """,
    )
    parser.add_argument(
        "--nueva-mk", required=True, help="Nueva Master Key en base64 (salt+key)"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Solo simula, no modifica BD ni archivos"
    )
    parser.add_argument(
        "--batch-size", type=int, default=100, help="Documentos por transacción (default: 100)"
    )
    parser.add_argument(
        "--vault-path", default=None, help="Ruta del vault (default: settings.vault_path)"
    )
    args = parser.parse_args()

    # Validar nueva MK
    try:
        nueva_mk_data = MasterKeyData.from_b64(args.nueva_mk)
    except Exception as e:
        print(f"ERROR: Master Key B64 inválida: {e}", file=sys.stderr)
        return 1

    print("=" * 60)
    print("ROTACIÓN DE MASTER KEY - BÓVEDA OSORNO RUNNERS")
    print("=" * 60)
    print(f"Dry-run:        {args.dry_run}")
    print(f"Batch size:     {args.batch_size}")
    print(f"Nueva MK salt:  {nueva_mk_data.salt.hex()}")
    print(f"Nueva MK key:   {nueva_mk_data.key.hex()[:16]}... (truncado)")
    print()

    if args.dry_run:
        print(">>> MODO DRY-RUN: No se modificarán datos <<<")
        print()

    # Setup DB y Vault
    settings = get_settings()
    db = SessionLocal()
    try:
        vault_path = Path(args.vault_path).resolve() if args.vault_path else Path(settings.vault_path).resolve()
        print(f"Vault path: {vault_path}")
        print(f"DB URL:     {settings.database_url}")
        print()

        vault = VaultService(db, settings.master_key_b64 and MasterKeyData.from_b64(settings.master_key_b64).key or b"", vault_path)

        if not settings.master_key_b64:
            print("ERROR: MASTER_KEY_B64 no configurada en settings", file=sys.stderr)
            return 1

        mk_actual = MasterKeyData.from_b64(settings.master_key_b64).key
        vault.mk = mk_actual  # Asegurar MK actual

        # Contar documentos
        from sqlalchemy import select
        docs = list(db.execute(select(DocumentoVault)).scalars().all())
        total = len(docs)
        print(f"Documentos a procesar: {total}")
        print()

        if total == 0:
            print("No hay documentos en la bóveda. Nada que rotar.")
            return 0

        if args.dry_run:
            print(">>> DRY-RUN: Verificando que se pueden descifrar con MK actual...")
            ok = 0
            for doc in docs[:10]:  # Muestreo
                try:
                    _ = vault.leer(doc.id, usuario_id=0)
                    ok += 1
                except Exception as e:
                    print(f"  ERROR doc {doc.id}: {e}")
            print(f"  Muestreo OK: {ok}/10")
            print(">>> DRY-RUN completado. Ejecutar sin --dry-run para rotar realmente.")
            return 0

        # Rotación real
        print("Iniciando rotación...")
        inicio = time.time()
        resultado = vault.rotar_master_key(nueva_mk_data.key, batch_size=args.batch_size)
        duracion = time.time() - inicio

        print()
        print("RESULTADO:")
        print(f"  Procesados:     {resultado.procesados}/{total}")
        print(f"  Errores:        {len(resultado.errores)}")
        print(f"  Duración:       {resultado.duracion_segundos:.2f}s")
        if resultado.errores:
            print("  Detalle errores:")
            for err in resultado.errores[:10]:
                print(f"    - {err}")
            if len(resultado.errores) > 10:
                print(f"    ... y {len(resultado.errores) - 10} más")

        print()
        if resultado.errores:
            print("⚠️  HUBO ERRORES. Revisa antes de actualizar .env")
            return 1
        else:
            print("✅ ROTACIÓN EXITOSA")
            print()
            print("PRÓXIMOS PASOS OBLIGATORIOS:")
            print("  1. Actualiza MASTER_KEY_B64 en tu .env con la nueva:")
            print(f"     MASTER_KEY_B64={nueva_mk_data.to_b64()}")
            print("  2. Reinicia la aplicación para cargar la nueva MK")
            print("  3. Verifica integridad: python scripts/vault/verificar_integridad.py")
            print("  4. Guarda backup de la MK ANTERIOR en ubicación segura")
            return 0

    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())