"""Rutas de la bóveda de documentos (FT-06).

Endpoints para Tesorero/Admin:
- POST /vault/subir           : Subir archivo (multipart)
- GET  /vault/{doc_id}/descargar : Descarga streaming (attachment)
- GET  /vault/{doc_id}/ver       : Vista inline (inline)
- DELETE /vault/{doc_id}         : Soft delete (Admin)
- GET  /vault/auditoria/{doc_id} : Historial accesos (Admin)
- POST /vault/rotar-master-key   : Iniciar rotación MK (Admin, async)
- GET  /vault/rotar-master-key/{task_id} : Estado rotación
"""

from __future__ import annotations

import io
import threading
import uuid
from datetime import datetime
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.seguridad import requiere_rol
from app.dependencies import SesionBD
from app.models.usuario import ROLES_GESTION, Usuario
from app.models.vault import DocumentoVault, TipoDocumento
from app.services.vault import (
    ArchivoCorruptoError,
    DocumentoNoEncontrado,
    VaultService,
    get_vault_service,
)

router = APIRouter(prefix="/vault", tags=["vault"])

settings = get_settings()

# Configuración
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "text/plain",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


def validar_archivo(file: UploadFile) -> None:
    """Valida tamaño y MIME type real (python-magic)."""
    import magic

    # Leer primeros bytes para detectar MIME real
    file.file.seek(0)
    header = file.file.read(8192)
    file.file.seek(0)

    mime_real = magic.from_buffer(header, mime=True)
    
    # Verificación adicional por extensión para casos edge (ej. .exe detectado como text/plain)
    filename = file.filename or ""
    ext = filename.lower().split(".")[-1] if "." in filename else ""
    dangerous_extensions = {"exe", "bat", "cmd", "com", "scr", "pif", "msi", "dll", "sys"}
    if ext in dangerous_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Extensión de archivo no permitida: .{ext}. Permitidos: PDF, imágenes, texto, Office.",
        )

    if mime_real not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo de archivo no permitido: {mime_real}. Permitidos: PDF, imágenes, texto, Office.",
        )

    # Validar tamaño (seek al final)
    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)
    if size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Archivo demasiado grande: {size} bytes (máx {MAX_FILE_SIZE}).",
        )


# --------------------------------------------------------------------------- #
# Dependencias
# --------------------------------------------------------------------------- #

TesoreroAdminDep = Annotated[Usuario, Depends(requiere_rol(*ROLES_GESTION))]


def get_vault(db: SesionBD) -> VaultService:
    """Crea instancia de VaultService para la request actual."""
    return get_vault_service(db)


# --------------------------------------------------------------------------- #
# Endpoints
# --------------------------------------------------------------------------- #

@router.post("/subir", status_code=status.HTTP_201_CREATED)
async def subir_documento(
    request: Request,
    db: SesionBD,
    current_user: Annotated[Usuario, Depends(requiere_rol(*ROLES_GESTION))],
    archivo: Annotated[UploadFile, File(description="Archivo a subir")],
    tipo_documento: Annotated[TipoDocumento, Form()],
    entidad_relacionada: Annotated[str | None, Form()] = None,
    entidad_id: Annotated[int | None, Form()] = None,
):
    """Sube un archivo a la bóveda cifrada.

    - Valida MIME type real con python-magic
    - Cifra con AES-256-GCM (DK única + MK)
    - Deduplicación por SHA-256 del contenido
    - Registra metadatos en BD
    """
    try:
        validar_archivo(archivo)
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})

    contenido = await archivo.read()
    await archivo.close()

    vault = get_vault(db)
    try:
        doc = vault.guardar(
            contenido,
            nombre_original=archivo.filename or "sin_nombre",
            mime_type=archivo.content_type or "application/octet-stream",
            tipo_documento=tipo_documento,
            entidad_relacionada=entidad_relacionada,
            entidad_id=entidad_id,
            subido_por=current_user.id,
        )
    except ArchivoCorruptoError as e:
        return JSONResponse(status_code=500, content={"detail": f"Error cifrando archivo: {e}"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": f"Error guardando: {e}"})

    return {
        "id": doc.id,
        "sha256": doc.sha256,
        "nombre_original": doc.nombre_original,
        "mime_type": doc.mime_type,
        "tamano_bytes": doc.tamano_bytes,
        "tipo_documento": doc.tipo_documento.value,
        "entidad_relacionada": doc.entidad_relacionada,
        "entidad_id": doc.entidad_id,
        "subido_en": doc.subido_en.isoformat() if doc.subido_en else None,
    }


@router.get("/{doc_id}/descargar")
def descargar_documento(
    doc_id: int,
    db: SesionBD,
    current_user: Annotated[Usuario, Depends(requiere_rol(*ROLES_GESTION))],
):
    """Descarga un documento (Content-Disposition: attachment).

    - Descifra streaming
    - Registra auditoría
    - Fuerza descarga en navegador
    """
    vault = get_vault(db)
    try:
        plaintext = vault.leer(doc_id, current_user.id)
    except DocumentoNoEncontrado:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    except ArchivoCorruptoError as e:
        raise HTTPException(status_code=500, detail=f"Archivo corrupto: {e}")

    doc = db.get(DocumentoVault, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    return StreamingResponse(
        io.BytesIO(plaintext),
        media_type=doc.mime_type,
        headers={
            "Content-Disposition": f'attachment; filename="{doc.nombre_original}"',
            "Content-Length": str(doc.tamano_bytes),
        },
    )


@router.get("/{doc_id}/ver")
def ver_documento(
    doc_id: int,
    db: SesionBD,
    current_user: Annotated[Usuario, Depends(requiere_rol(*ROLES_GESTION))],
):
    """Vista inline del documento (Content-Disposition: inline).

    Para imágenes y PDFs que el navegador puede mostrar directamente.
    """
    vault = get_vault(db)
    try:
        plaintext = vault.leer(doc_id, current_user.id)
    except DocumentoNoEncontrado:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    except ArchivoCorruptoError as e:
        raise HTTPException(status_code=500, detail=f"Archivo corrupto: {e}")

    doc = db.get(DocumentoVault, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    return StreamingResponse(
        io.BytesIO(plaintext),
        media_type=doc.mime_type,
        headers={
            "Content-Disposition": f'inline; filename="{doc.nombre_original}"',
            "Content-Length": str(doc.tamano_bytes),
        },
    )


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_documento(
    doc_id: int,
    db: SesionBD,
    current_user: Annotated[Usuario, Depends(requiere_rol(*ROLES_GESTION))],
    hard: bool = False,
):
    """Elimina un documento (soft delete por defecto).

    Solo Admin puede hacer hard delete (borra archivo físico).
    """
    vault = get_vault(db)
    # Verificar que es Admin para hard delete
    if hard and current_user.rol != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo Admin puede eliminar permanentemente",
        )

    ok = vault.eliminar(doc_id, current_user.id, hard=hard)
    if not ok:
        raise HTTPException(status_code=404, detail="Documento no encontrado")


@router.get("/auditoria/{doc_id}")
def auditoria_documento(
    doc_id: int,
    db: SesionBD,
    current_user: Annotated[Usuario, Depends(requiere_rol(*ROLES_GESTION))],
):
    """Historial de accesos a un documento."""
    vault = get_vault(db)
    try:
        accesos = vault.obtener_auditoria(doc_id)
    except DocumentoNoEncontrado:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    return {"documento_id": doc_id, "accesos": accesos}


# --------------------------------------------------------------------------- #
# Rotación de Master Key (Admin only)
# --------------------------------------------------------------------------- #

# Almacenamiento simple en memoria para tareas async (en producción: Redis/DB)
_rotacion_tasks: dict[str, dict] = {}


@router.post("/rotar-master-key", status_code=status.HTTP_202_ACCEPTED)
def iniciar_rotacion_master_key(
    request: Request,
    db: SesionBD,
    current_user: Annotated[Usuario, Depends(requiere_rol("admin"))],
    nueva_mk_b64: Annotated[str, Form(description="Nueva Master Key en base64 (salt+key)")],
):
    """Inicia rotación de Master Key (operación async, batch).

    La nueva MK debe generarse con `scripts/vault/generar_master_key.py`.
    Retorna task_id para consultar progreso.
    """
    from app.core.crypto import MasterKeyData

    try:
        nueva_mk_data = MasterKeyData.from_b64(nueva_mk_b64)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Master Key B64 inválida: {e}")

    task_id = str(uuid.uuid4())[:8]
    _rotacion_tasks[task_id] = {
        "estado": "iniciando",
        "iniciado_en": datetime.utcnow().isoformat() + "Z",
        "iniciado_por": current_user.id,
        "nueva_mk_b64": nueva_mk_b64,
        "progreso": 0,
        "total": 0,
        "procesados": 0,
        "errores": [],
    }

    # Ejecutar en background (en producción: task queue Celery/RQ)
    # Aquí lo hacemos síncrono por simplicidad, pero retornamos 202

    def _rotar():
        vault = get_vault(db)
        _rotacion_tasks[task_id]["estado"] = "ejecutando"
        try:
            # Contar total primero
            from sqlalchemy import select
            total = len(list(db.execute(select(DocumentoVault)).scalars().all()))
            _rotacion_tasks[task_id]["total"] = total

            resultado = vault.rotar_master_key(nueva_mk_data.key)

            _rotacion_tasks[task_id].update({
                "estado": "completado" if not resultado.errores else "completado_con_errores",
                "finalizado_en": datetime.utcnow().isoformat() + "Z",
                "procesados": resultado.procesados,
                "errores": resultado.errores,
                "duracion_segundos": resultado.duracion_segundos,
            })
        except Exception as e:
            _rotacion_tasks[task_id].update({
                "estado": "fallido",
                "finalizado_en": datetime.utcnow().isoformat() + "Z",
                "errores": [f"Error fatal: {e}"],
            })

    thread = threading.Thread(target=_rotar, daemon=True)
    thread.start()

    return {"task_id": task_id, "estado": "iniciando", "mensaje": "Rotación iniciada en background"}


@router.get("/rotar-master-key/{task_id}")
def estado_rotacion_master_key(
    task_id: str,
    current_user: Annotated[Usuario, Depends(requiere_rol("admin"))],
):
    """Consulta el estado de una rotación de Master Key."""
    task = _rotacion_tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task no encontrada")
    return task


# --------------------------------------------------------------------------- #
# Verificación de integridad (Admin)
# --------------------------------------------------------------------------- #

@router.post("/verificar-integridad")
def verificar_integridad_vault(
    db: SesionBD,
    current_user: Annotated[Usuario, Depends(requiere_rol("admin"))],
    limit: int | None = None,
):
    """Verifica integridad de todos los documentos en el vault."""
    vault = get_vault(db)
    resultado = vault.verificar_integridad(limit=limit)
    return {
        "total": resultado.total,
        "ok": resultado.ok,
        "corruptos": resultado.corruptos,
        "faltantes": resultado.faltantes,
        "porcentaje_ok": round(resultado.ok / resultado.total * 100, 2) if resultado.total else 100,
    }