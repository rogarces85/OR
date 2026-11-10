"""Modelos de la bóveda de documentos cifrados (FT-06).

Cifrado AES-256-GCM por documento con Document Key única,
cifrada a su vez con Master Key rotativa (PBKDF2 100k iter).
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, LargeBinary, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.usuario import Usuario


class TipoDocumento(str, enum.Enum):
    """Tipo de documento almacenado en la bóveda."""
    COMPROBANTE = "COMPROBANTE"
    BOLETA = "BOLETA"
    CONTRATO = "CONTRATO"
    OTRO = "OTRO"


class DocumentoVault(Base):
    """Documento almacenado en la bóveda cifrada.

    Cada archivo tiene:
    - SHA-256 del plaintext (identidad + deduplicación)
    - Document Key (DK) única cifrada con Master Key (MK)
    - Archivo cifrado con su DK (AES-256-GCM)
    - Auditoría JSON de accesos
    """

    __tablename__ = "documentos_vault"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Identidad del contenido (plaintext) - para deduplicación
    sha256: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True
    )
    nombre_original: Mapped[str] = mapped_column(String(300), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    tamano_bytes: Mapped[int] = mapped_column(Integer, nullable=False)

    # Cifrado: Document Key cifrada con Master Key (AES-GCM)
    nonce_dk: Mapped[bytes] = mapped_column(LargeBinary(12), nullable=False)
    dk_enc: Mapped[bytes] = mapped_column(LargeBinary(48), nullable=False)  # 32 + 16 tag

    # Cifrado: Archivo cifrado con Document Key (AES-GCM)
    tag_archivo: Mapped[bytes] = mapped_column(LargeBinary(16), nullable=False)
    ruta_archivo: Mapped[str] = mapped_column(String(500), nullable=False)

    # Metadatos
    tipo_documento: Mapped[TipoDocumento] = mapped_column(
        Enum(TipoDocumento), nullable=False, index=True
    )
    entidad_relacionada: Mapped[str | None] = mapped_column(
        String(50), nullable=True, index=True
    )  # "miembros", "pagos", "egresos", "compras"
    entidad_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    subido_por: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id"), nullable=False
    )
    subido_en: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    # Auditoría de accesos (JSON array serializado como TEXT)
    accesos: Mapped[str] = mapped_column(
        Text, default="[]", nullable=False
    )  # JSON string: [{"usuario_id": 1, "accion": "DESCARGA", "timestamp": "..."}]

    # Relaciones
    subido_por_usuario: Mapped["Usuario"] = relationship(
        "Usuario", foreign_keys=[subido_por]
    )

    __table_args__ = (
        Index("ix_vault_entidad", "entidad_relacionada", "entidad_id"),
        Index("ix_vault_subido_en", "subido_en"),
        Index("ix_vault_tipo_entidad", "tipo_documento", "entidad_relacionada"),
    )

    def __repr__(self) -> str:
        return f"<DocumentoVault {self.id} {self.nombre_original} ({self.tipo_documento})>"

    def registrar_acceso(self, usuario_id: int, accion: str) -> None:
        """Añade una entrada a la auditoría de accesos."""
        import json
        from datetime import datetime as dt

        entrada = {
            "usuario_id": usuario_id,
            "accion": accion,
            "timestamp": dt.utcnow().isoformat() + "Z",
        }
        try:
            actual = json.loads(self.accesos) if self.accesos else []
        except (json.JSONDecodeError, TypeError):
            actual = []
        actual.append(entrada)
        self.accesos = json.dumps(actual, ensure_ascii=False)

    def obtener_accesos(self) -> list[dict]:
        """Retorna la lista de accesos parseada."""
        import json
        try:
            return json.loads(self.accesos) if self.accesos else []
        except (json.JSONDecodeError, TypeError):
            return []