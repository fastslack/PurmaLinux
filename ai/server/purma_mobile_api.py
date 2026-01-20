"""
PurmaLinux - Mobile Sync API
============================
Author: Matías Aguirre
Company: Matware

API REST para sincronización con dispositivos móviles (Android/iOS).
Diseñada para ser consumida por apps nativas o Flutter.
"""

import os
import json
import hashlib
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import logging
import secrets
import base64

from fastapi import APIRouter, HTTPException, Depends, Header, UploadFile, File, Query
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from purma_sync import get_sync_engine, SyncedFolder, SyncedFile, Device

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("purma.mobile")


# ============================================
# Configuration
# ============================================

PURMA_HOME = Path.home() / ".purma"
MOBILE_CONFIG = PURMA_HOME / "mobile" / "config.json"
MOBILE_TOKENS = PURMA_HOME / "mobile" / "tokens.json"

MOBILE_CONFIG.parent.mkdir(parents=True, exist_ok=True)


# ============================================
# Authentication
# ============================================

class MobileAuth:
    """Autenticación simple para dispositivos móviles"""

    def __init__(self):
        self._tokens: Dict[str, Dict] = {}
        self._load_tokens()

    def _load_tokens(self):
        """Cargar tokens guardados"""
        if MOBILE_TOKENS.exists():
            self._tokens = json.loads(MOBILE_TOKENS.read_text())

    def _save_tokens(self):
        """Guardar tokens"""
        MOBILE_TOKENS.write_text(json.dumps(self._tokens, indent=2))

    def generate_pairing_code(self) -> str:
        """Genera un código de emparejamiento de 6 dígitos"""
        code = secrets.randbelow(1000000)
        return f"{code:06d}"

    def create_device_token(self, device_id: str, device_name: str, device_type: str) -> str:
        """Crea un token de acceso para un dispositivo"""
        token = secrets.token_urlsafe(32)
        self._tokens[token] = {
            "device_id": device_id,
            "device_name": device_name,
            "device_type": device_type,
            "created_at": datetime.now().isoformat(),
            "last_used": datetime.now().isoformat()
        }
        self._save_tokens()
        return token

    def validate_token(self, token: str) -> Optional[Dict]:
        """Valida un token y retorna info del dispositivo"""
        if token in self._tokens:
            self._tokens[token]["last_used"] = datetime.now().isoformat()
            self._save_tokens()
            return self._tokens[token]
        return None

    def revoke_token(self, token: str) -> bool:
        """Revoca un token"""
        if token in self._tokens:
            del self._tokens[token]
            self._save_tokens()
            return True
        return False

    def list_devices(self) -> List[Dict]:
        """Lista dispositivos autorizados"""
        return [
            {**info, "token_prefix": token[:8] + "..."}
            for token, info in self._tokens.items()
        ]


mobile_auth = MobileAuth()


# ============================================
# Dependency for token validation
# ============================================

async def verify_mobile_token(authorization: str = Header(None)) -> Dict:
    """Verificar token de autorización"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Token de autorización requerido")

    # Expect "Bearer <token>"
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Formato de autorización inválido")

    token = parts[1]
    device_info = mobile_auth.validate_token(token)

    if not device_info:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")

    return device_info


# ============================================
# API Models
# ============================================

class PairingRequest(BaseModel):
    code: str
    device_id: str
    device_name: str
    device_type: str  # "android" | "ios"


class SyncRequest(BaseModel):
    folder_id: str
    since: Optional[str] = None  # ISO timestamp


class FileUploadMeta(BaseModel):
    folder_id: str
    relative_path: str
    checksum: str


class FileChange(BaseModel):
    file_id: str
    action: str  # "created" | "modified" | "deleted"
    relative_path: str
    checksum: Optional[str] = None
    size: Optional[int] = None
    modified_at: str


# ============================================
# Router
# ============================================

mobile_router = APIRouter(prefix="/mobile", tags=["Mobile Sync"])
sync_engine = get_sync_engine()


# ============================================
# Pairing Endpoints
# ============================================

# Store for pairing codes (in-memory, expires quickly)
_pairing_codes: Dict[str, Dict] = {}


@mobile_router.post("/pairing/generate")
async def generate_pairing_code():
    """
    Genera un código de emparejamiento.
    Debe mostrarse en la pantalla del hub (Linux).
    El usuario ingresa este código en la app móvil.
    """
    code = mobile_auth.generate_pairing_code()
    _pairing_codes[code] = {
        "created_at": datetime.now().isoformat(),
        "expires_in": 300  # 5 minutos
    }

    return {
        "code": code,
        "expires_in": 300,
        "instructions": "Ingresa este código en la app móvil para emparejar"
    }


@mobile_router.post("/pairing/complete")
async def complete_pairing(request: PairingRequest):
    """
    Completa el emparejamiento usando el código.
    Llamado desde la app móvil.
    """
    if request.code not in _pairing_codes:
        raise HTTPException(status_code=400, detail="Código inválido o expirado")

    # Verificar expiración
    code_info = _pairing_codes[request.code]
    created = datetime.fromisoformat(code_info["created_at"])
    if (datetime.now() - created).seconds > code_info["expires_in"]:
        del _pairing_codes[request.code]
        raise HTTPException(status_code=400, detail="Código expirado")

    # Crear token y registrar dispositivo
    token = mobile_auth.create_device_token(
        request.device_id,
        request.device_name,
        request.device_type
    )

    # Registrar en sync engine
    sync_engine.register_device(
        request.device_id,
        request.device_name,
        request.device_type
    )

    # Limpiar código usado
    del _pairing_codes[request.code]

    return {
        "success": True,
        "access_token": token,
        "device_id": request.device_id,
        "message": "Dispositivo emparejado exitosamente"
    }


@mobile_router.get("/pairing/devices")
async def list_paired_devices():
    """Lista dispositivos emparejados (para mostrar en hub)"""
    return {"devices": mobile_auth.list_devices()}


@mobile_router.delete("/pairing/devices/{device_id}")
async def unpair_device(device_id: str):
    """Desemparejar un dispositivo"""
    # Find and revoke token
    for token, info in list(mobile_auth._tokens.items()):
        if info["device_id"] == device_id:
            mobile_auth.revoke_token(token)
            return {"success": True, "message": "Dispositivo desemparejado"}

    raise HTTPException(status_code=404, detail="Dispositivo no encontrado")


# ============================================
# Sync Metadata Endpoints
# ============================================

@mobile_router.get("/sync/folders")
async def get_sync_folders(device: Dict = Depends(verify_mobile_token)):
    """
    Obtiene las carpetas disponibles para sincronización.
    Solo retorna carpetas vinculadas a este dispositivo.
    """
    all_folders = sync_engine.list_folders()
    device_id = device["device_id"]

    # Filtrar carpetas del dispositivo
    device_folders = [
        f for f in all_folders
        if device_id in f.get("devices", []) or not f.get("devices")
    ]

    return {
        "folders": device_folders,
        "device_id": device_id
    }


@mobile_router.get("/sync/folders/{folder_id}")
async def get_folder_details(
    folder_id: str,
    device: Dict = Depends(verify_mobile_token)
):
    """Obtiene detalles de una carpeta"""
    folder = sync_engine.storage.get_folder(folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Carpeta no encontrada")

    return folder.to_dict()


@mobile_router.get("/sync/folders/{folder_id}/files")
async def get_folder_files(
    folder_id: str,
    since: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = Query(default=100, le=1000),
    offset: int = 0,
    device: Dict = Depends(verify_mobile_token)
):
    """
    Lista archivos de una carpeta.
    Soporta paginación y filtros.
    """
    files = sync_engine.storage.get_files_by_folder(folder_id)

    # Filtrar por fecha si se especifica
    if since:
        since_dt = datetime.fromisoformat(since)
        files = [f for f in files if datetime.fromisoformat(f.modified_at) > since_dt]

    # Filtrar por categoría
    if category:
        files = [f for f in files if f.category == category]

    # Paginación
    total = len(files)
    files = files[offset:offset + limit]

    return {
        "files": [f.to_dict() for f in files],
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": offset + limit < total
    }


@mobile_router.get("/sync/changes")
async def get_changes(
    since: str,
    folder_id: Optional[str] = None,
    device: Dict = Depends(verify_mobile_token)
):
    """
    Obtiene cambios desde una fecha específica.
    Usado para sincronización incremental.
    """
    since_dt = datetime.fromisoformat(since)

    changes = []
    folders = sync_engine.storage.get_all_folders()

    if folder_id:
        folders = [f for f in folders if f.folder_id == folder_id]

    for folder in folders:
        files = sync_engine.storage.get_files_by_folder(folder.folder_id)
        for file in files:
            file_modified = datetime.fromisoformat(file.modified_at)
            if file_modified > since_dt:
                changes.append({
                    "folder_id": folder.folder_id,
                    "file": file.to_dict(),
                    "action": "modified"
                })

    return {
        "changes": changes,
        "since": since,
        "until": datetime.now().isoformat(),
        "count": len(changes)
    }


# ============================================
# File Transfer Endpoints
# ============================================

@mobile_router.get("/files/{folder_id}/{file_path:path}")
async def download_file(
    folder_id: str,
    file_path: str,
    device: Dict = Depends(verify_mobile_token)
):
    """
    Descarga un archivo.
    El file_path es relativo a la carpeta sincronizada.
    """
    folder = sync_engine.storage.get_folder(folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Carpeta no encontrada")

    full_path = Path(folder.local_path) / file_path

    if not full_path.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")

    if not full_path.is_file():
        raise HTTPException(status_code=400, detail="No es un archivo")

    # Verificar que está dentro de la carpeta sync
    try:
        full_path.resolve().relative_to(Path(folder.local_path).resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Acceso denegado")

    return FileResponse(
        full_path,
        filename=full_path.name,
        media_type="application/octet-stream"
    )


@mobile_router.post("/files/{folder_id}")
async def upload_file(
    folder_id: str,
    file: UploadFile = File(...),
    relative_path: str = Query(...),
    device: Dict = Depends(verify_mobile_token)
):
    """
    Sube un archivo desde el móvil.
    """
    folder = sync_engine.storage.get_folder(folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Carpeta no encontrada")

    # Construir ruta destino
    dest_path = Path(folder.local_path) / relative_path

    # Verificar que está dentro de la carpeta
    try:
        dest_path.resolve().relative_to(Path(folder.local_path).resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Ruta inválida")

    # Crear directorios si no existen
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    # Guardar archivo
    content = await file.read()
    dest_path.write_bytes(content)

    # Calcular checksum
    checksum = hashlib.md5(content).hexdigest()

    # Indexar archivo
    category, subcategory = sync_engine.organizer.get_file_category(dest_path)
    tags = sync_engine.organizer.generate_ai_tags(dest_path)

    synced_file = SyncedFile(
        file_id=hashlib.md5(f"{folder_id}:{relative_path}".encode()).hexdigest()[:16],
        folder_id=folder_id,
        relative_path=relative_path,
        filename=dest_path.name,
        size=len(content),
        checksum=checksum,
        category=category,
        subcategory=subcategory,
        ai_tags=tags,
        status="synced",
        modified_at=datetime.now().isoformat(),
        synced_at=datetime.now().isoformat()
    )
    sync_engine.storage.add_file(synced_file)

    return {
        "success": True,
        "file": synced_file.to_dict(),
        "message": "Archivo subido exitosamente"
    }


@mobile_router.delete("/files/{folder_id}/{file_path:path}")
async def delete_file(
    folder_id: str,
    file_path: str,
    device: Dict = Depends(verify_mobile_token)
):
    """Elimina un archivo"""
    folder = sync_engine.storage.get_folder(folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Carpeta no encontrada")

    full_path = Path(folder.local_path) / file_path

    if not full_path.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")

    # Verificar que está dentro de la carpeta
    try:
        full_path.resolve().relative_to(Path(folder.local_path).resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Acceso denegado")

    # Eliminar
    full_path.unlink()

    return {"success": True, "message": "Archivo eliminado"}


# ============================================
# Organization Endpoints
# ============================================

@mobile_router.get("/organize/preview/{folder_id}")
async def preview_organization_mobile(
    folder_id: str,
    device: Dict = Depends(verify_mobile_token)
):
    """Vista previa de organización para móvil"""
    return sync_engine.suggest_organization(folder_id)


@mobile_router.post("/organize/execute/{folder_id}")
async def execute_organization_mobile(
    folder_id: str,
    device: Dict = Depends(verify_mobile_token)
):
    """Ejecutar organización desde móvil"""
    return sync_engine.organize_folder(folder_id, dry_run=False)


# ============================================
# Status Endpoints
# ============================================

@mobile_router.get("/status")
async def mobile_status(device: Dict = Depends(verify_mobile_token)):
    """Estado del hub para el móvil"""
    status = sync_engine.get_status()
    status["device"] = device
    status["server_time"] = datetime.now().isoformat()
    return status


@mobile_router.post("/ping")
async def mobile_ping(device: Dict = Depends(verify_mobile_token)):
    """Keep-alive ping desde móvil"""
    return {
        "pong": True,
        "server_time": datetime.now().isoformat(),
        "device_id": device["device_id"]
    }


# ============================================
# QR Code Generation (for easy pairing)
# ============================================

@mobile_router.get("/pairing/qr")
async def get_pairing_qr():
    """
    Genera datos para un QR de emparejamiento.
    El frontend puede usar esto para mostrar un QR scaneable.
    """
    import socket

    code = mobile_auth.generate_pairing_code()
    _pairing_codes[code] = {
        "created_at": datetime.now().isoformat(),
        "expires_in": 300
    }

    # Obtener IP local
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        local_ip = "127.0.0.1"

    # Datos para el QR
    qr_data = {
        "type": "purma_pairing",
        "version": 1,
        "code": code,
        "host": local_ip,
        "port": 11435,
        "expires_in": 300
    }

    return {
        "qr_data": json.dumps(qr_data),
        "code": code,
        "host": local_ip,
        "port": 11435,
        "expires_in": 300
    }


# ============================================
# Export router for main app
# ============================================

def get_mobile_router() -> APIRouter:
    """Obtener router para incluir en la app principal"""
    return mobile_router
