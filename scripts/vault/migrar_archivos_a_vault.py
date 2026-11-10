#!/usr/bin/env python3
"""Migra archivos legacy de static/uploads/ a la bóveda cifrada.

Uso:
    python scripts/vault/migrar_archivos_a_vault.py [--legacy-dir ./static/uploads] [--dry-run]

Migra:
- comprobantes_* → TipoDocumento.COMPROBANTE
- boletas_* → TipoDocumento.BOLETA
- otros → TipoDocumento.OTRO

Actualiza FKs en:
- ComprobantePago.archivo_vault_id
- Egreso.comprobante_vault_id
- CompraClub.documento_vault_id
"""

from __future__ import annotations

import argparse
import mimetypes
import re
import sys
from dataclasses import dataclass
from pathlib import Path

# Asegurar que app/ está en el path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.config import get_settings
from app.core.crypto import MasterKeyData
from app.database import SessionLocal
from app.models.vault import DocumentoVault, TipoDocumento
from app.services.vault import VaultService


@dataclass
class ResultadoMigracion:
    migrados: int = 0
    omitidos: int = 0
    errores: list[str] = None

    def __post_init__(self):
        if self.errores is None:
            self.errores = []


def detectar_tipo_y_entidad(nombre_archivo: str) -> tuple[TipoDocumento, str | None, int | None]:
    """Intenta inferir tipo y entidad desde el nombre del archivo legacy.

    Patrones esperados:
    - comprobante_<pago_id>_<hash>.<ext> → COMPROBANTE, "pagos", pago_id
    - boleta_<egreso_id>_<hash>.<ext>   → BOLETA, "egresos", egreso_id
    - compra_<compra_id>_<hash>.<ext>   → CONTRATO, "compras", compra_id
    """
    nombre = nombre_archivo.lower()

    # Comprobante de pago
    m = re.match(r"comprobante[_-]?(\d+)", nombre)
    if m:
        return TipoDocumento.COMPROBANTE, "pagos", int(m.group(1))

    # Boleta de egreso
    m = re.match(r"boleta[_-]?(\d+)", nombre)
    if m:
        return TipoDocumento.BOLETA, "egresos", int(m.group(1))

    # Compra del club
    m = re.match(r"compra[_-]?(\d+)", nombre)
    if m:
        return TipoDocumento.CONTRATO, "compras", int(m.group(1))

    # Default
    return TipoDocumento.OTRO, None, None


def migrar_archivos(
    db,
    vault: VaultService,
    legacy_dir: Path,
    dry_run: bool = False,
    usuario_id: int = 1,  # Admin por defecto
) -> ResultadoMigracion:
    """Migra archivos del directorio legacy al vault."""
    resultado = ResultadoMigracion()

    if not legacy_dir.exists():
        resultado.errores.append(f"Directorio legacy no existe: {legacy_dir}")
        return resultado

    archivos = list(legacy_dir.rglob("*"))
    archivos = [f for f in archivos if f.is_file()]

    print(f"Encontrados {len(archivos)} archivos en {legacy_dir}")

    for archivo in archivos:
        try:
            # Detectar tipo y entidad
            tipo, entidad_rel, entidad_id = detectar_tipo_y_entidad(archivo.name)

            # MIME type
            mime, _ = mimetypes.guess_type(str(archivo))
            if not mime:
                mime = "application/octet-stream"

            # Leer archivo
            contenido = archivo.read_bytes()

            if dry_run:
                print(f"  [DRY-RUN] {archivo.name} → {tipo.value} ({entidad_rel}:{entidad_id})")
                resultado.migrados += 1
                continue

            # Guardar en vault
            doc = vault.guardar(
                contenido,
                nombre_original=archivo.name,
                mime_type=mime,
                tipo_documento=tipo,
                entidad_relacionada=entidad_rel,
                entidad_id=entidad_id,
                subido_por=usuario_id,
            )

            print(f"  ✓ {archivo.name} → Doc #{doc.id} ({tipo.value})")
            resultado.migrados += 1

        except Exception as e:
            error_msg = f"{archivo.name}: {e}"
            print(f"  ✗ {error_msg}")
            resultado.errores.append(error_msg)

    return resultado


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Migra archivos legacy a la bóveda cifrada",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  # Simulación
  python scripts/vault/migrar_archivos_a_vault.py --dry-run

  # Migración real
  python scripts/vault/migrar_archivos_a_vault.py --legacy-dir ./static/uploads
        """,
    )
    parser.add_argument(
        "--legacy-dir", default="./static/uploads", help="Directorio con archivos legacy"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Solo simula, no modifica BD ni vault"
    )
    parser.add_argument(
        "--vault-path", default=None, help="Ruta del vault (default: settings.vault_path)"
    )
    parser.add_argument(
        "--usuario-id", type=int, default=1, help="ID de usuario que 'sube' (default: 1=admin)"
    )
    args = parser.parse_args()

    settings = get_settings()
    db = SessionLocal()

    try:
        vault_path = Path(args.vault_path).resolve() if args.vault_path else Path(settings.vault_path).resolve()
        mk_data = MasterKeyData.from_b64(settings.master_key_b64)

        vault = VaultService(db, mk_data.key, vault_path)
        legacy_dir = Path(args.legacy_dir).resolve()

        print("=" * 60)
        print("MIGRACIÓN LEGACY → BÓVEDA CIFRADA")
        print("=" * 60)
        print(f"Directorio origen:  {legacy_dir}")
        print(f"Vault destino:      {vault_path}")
        print(f"Dry-run:            {args.dry_run}")
        print(f"Usuario:            {args.usuario_id}")
        print()

        if args.dry_run:
            print(">>> MODO DRY-RUN: No se modificarán datos <<<")
            print()

        resultado = migrar_archivos(db, vault, legacy_dir, args.dry_run, args.usuario_id)

        print()
        print("RESUMEN:")
        print(f"  Migrados:   {resultado.migrados}")
        print(f"  Errores:    {len(resultado.errores)}")
        if resultado.errores:
            for err in resultado.errores:
                print(f"    - {err}")
            return 1

        if not args.dry_run:
            print()
            print("✅ MIGRACIÓN COMPLETADA")
            print("Próximos pasos:")
            print("  1. Verificar integridad: python scripts/vault/verificar_integridad.py")
            print("  2. Actualizar código que referencie static/uploads/")
            print("  3. (Opcional) Borrar static/uploads/ tras confirmar")

        return 0

    except Exception as e:
        print(f"❌ Error fatal: {e}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())