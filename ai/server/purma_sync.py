"""
PurmaLinux - Purma Sync
========================
Author: Matías Aguirre
Company: Matware

Sistema de sincronización inteligente con:
- Sincronización de carpetas con dispositivos móviles
- Organización automática por IA
- Hub central para todos los dispositivos
"""

import os
import sys
import json
import asyncio
import hashlib
import shutil
import sqlite3
import subprocess
import mimetypes
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
import logging
import threading
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("purma.sync")


# ============================================
# Configuration
# ============================================

PURMA_HOME = Path.home() / ".purma"
SYNC_DIR = PURMA_HOME / "sync"
SYNC_DB = SYNC_DIR / "sync.db"
ORGANIZED_DIR = PURMA_HOME / "organized"
CONFIG_FILE = SYNC_DIR / "config.json"

# Create directories
SYNC_DIR.mkdir(parents=True, exist_ok=True)
ORGANIZED_DIR.mkdir(parents=True, exist_ok=True)


# ============================================
# File Categories for AI Organization
# ============================================

FILE_CATEGORIES = {
    "documents": {
        "extensions": [".pdf", ".doc", ".docx", ".odt", ".txt", ".rtf", ".xls",
                      ".xlsx", ".ppt", ".pptx", ".csv", ".md", ".rst"],
        "icon": "📄",
        "subcategories": {
            "work": ["invoice", "contract", "report", "meeting", "proposal"],
            "personal": ["receipt", "ticket", "reservation", "certificate"],
            "academic": ["thesis", "paper", "assignment", "notes", "lecture"],
            "financial": ["bank", "tax", "budget", "statement"],
        }
    },
    "images": {
        "extensions": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg",
                      ".webp", ".ico", ".tiff", ".raw", ".heic"],
        "icon": "🖼️",
        "subcategories": {
            "photos": ["photo", "camera", "dcim", "img_"],
            "screenshots": ["screenshot", "screen", "capture"],
            "design": ["design", "mockup", "wireframe", "ui", "ux"],
            "memes": ["meme", "funny", "reaction"],
        }
    },
    "videos": {
        "extensions": [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv",
                      ".webm", ".m4v", ".3gp"],
        "icon": "🎬",
        "subcategories": {
            "movies": ["movie", "film", "1080p", "720p", "4k"],
            "series": ["s01", "s02", "episode", "ep"],
            "personal": ["vid_", "video_", "recording"],
            "tutorials": ["tutorial", "course", "lesson", "howto"],
        }
    },
    "audio": {
        "extensions": [".mp3", ".wav", ".flac", ".aac", ".ogg",
                      ".wma", ".m4a", ".opus"],
        "icon": "🎵",
        "subcategories": {
            "music": ["album", "artist", "track"],
            "podcasts": ["podcast", "episode", "ep"],
            "recordings": ["voice", "recording", "memo"],
        }
    },
    "code": {
        "extensions": [".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css",
                      ".scss", ".json", ".yaml", ".yml", ".sh", ".bash",
                      ".go", ".rs", ".c", ".cpp", ".h", ".java", ".rb",
                      ".php", ".sql", ".swift", ".kt"],
        "icon": "💻",
        "subcategories": {
            "web": ["html", "css", "js", "react", "vue", "angular"],
            "backend": ["api", "server", "service", "handler"],
            "scripts": ["script", "util", "helper", "tool"],
            "config": ["config", "settings", "env", ".rc"],
        }
    },
    "archives": {
        "extensions": [".zip", ".tar", ".gz", ".rar", ".7z", ".bz2", ".xz"],
        "icon": "📦",
        "subcategories": {
            "backups": ["backup", "bak", "old"],
            "downloads": ["download", "dl"],
        }
    },
    "data": {
        "extensions": [".db", ".sqlite", ".json", ".xml", ".csv",
                      ".parquet", ".npy"],
        "icon": "🗃️",
        "subcategories": {
            "databases": ["db", "database", "data"],
            "exports": ["export", "dump", "backup"],
        }
    }
}


# ============================================
# Data Models
# ============================================

class SyncStatus(Enum):
    PENDING = "pending"
    SYNCING = "syncing"
    SYNCED = "synced"
    CONFLICT = "conflict"
    ERROR = "error"


class OrganizeMode(Enum):
    DISABLED = "disabled"
    MANUAL = "manual"
    AUTO = "auto"
    SMART = "smart"  # AI decides based on content


@dataclass
class SyncedFolder:
    """Carpeta sincronizada"""
    folder_id: str
    local_path: str
    name: str
    organize_mode: str = "disabled"
    sync_enabled: bool = True
    devices: List[str] = field(default_factory=list)
    last_sync: Optional[str] = None
    file_count: int = 0
    total_size: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class SyncedFile:
    """Archivo sincronizado"""
    file_id: str
    folder_id: str
    relative_path: str
    filename: str
    size: int
    checksum: str
    category: str = "unknown"
    subcategory: str = ""
    ai_tags: List[str] = field(default_factory=list)
    status: str = "pending"
    modified_at: str = ""
    synced_at: Optional[str] = None

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class Device:
    """Dispositivo conectado"""
    device_id: str
    name: str
    device_type: str  # linux, android, ios
    last_seen: str
    ip_address: str = ""
    sync_folders: List[str] = field(default_factory=list)
    is_online: bool = False

    def to_dict(self) -> Dict:
        return asdict(self)


# ============================================
# Database Storage
# ============================================

class SyncStorage:
    """Almacenamiento persistente para sync"""

    def __init__(self, db_path: Path = SYNC_DB):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Folders table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS folders (
                folder_id TEXT PRIMARY KEY,
                local_path TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                organize_mode TEXT DEFAULT 'disabled',
                sync_enabled INTEGER DEFAULT 1,
                devices TEXT DEFAULT '[]',
                last_sync TEXT,
                file_count INTEGER DEFAULT 0,
                total_size INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            )
        """)

        # Files table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS files (
                file_id TEXT PRIMARY KEY,
                folder_id TEXT NOT NULL,
                relative_path TEXT NOT NULL,
                filename TEXT NOT NULL,
                size INTEGER NOT NULL,
                checksum TEXT NOT NULL,
                category TEXT DEFAULT 'unknown',
                subcategory TEXT DEFAULT '',
                ai_tags TEXT DEFAULT '[]',
                status TEXT DEFAULT 'pending',
                modified_at TEXT NOT NULL,
                synced_at TEXT,
                FOREIGN KEY (folder_id) REFERENCES folders(folder_id),
                UNIQUE(folder_id, relative_path)
            )
        """)

        # Devices table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS devices (
                device_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                device_type TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                ip_address TEXT DEFAULT '',
                sync_folders TEXT DEFAULT '[]',
                is_online INTEGER DEFAULT 0
            )
        """)

        # Organization rules table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS organize_rules (
                rule_id TEXT PRIMARY KEY,
                folder_id TEXT NOT NULL,
                rule_type TEXT NOT NULL,
                pattern TEXT NOT NULL,
                destination TEXT NOT NULL,
                priority INTEGER DEFAULT 0,
                enabled INTEGER DEFAULT 1,
                FOREIGN KEY (folder_id) REFERENCES folders(folder_id)
            )
        """)

        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_folder ON files(folder_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_category ON files(category)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_status ON files(status)")

        conn.commit()
        conn.close()

    # Folder operations
    def add_folder(self, folder: SyncedFolder) -> bool:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO folders
                (folder_id, local_path, name, organize_mode, sync_enabled,
                 devices, last_sync, file_count, total_size, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                folder.folder_id, folder.local_path, folder.name,
                folder.organize_mode, folder.sync_enabled,
                json.dumps(folder.devices), folder.last_sync,
                folder.file_count, folder.total_size, folder.created_at
            ))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    def get_folder(self, folder_id: str) -> Optional[SyncedFolder]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM folders WHERE folder_id = ?", (folder_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return SyncedFolder(
                folder_id=row[0], local_path=row[1], name=row[2],
                organize_mode=row[3], sync_enabled=bool(row[4]),
                devices=json.loads(row[5]), last_sync=row[6],
                file_count=row[7], total_size=row[8], created_at=row[9]
            )
        return None

    def get_folder_by_path(self, path: str) -> Optional[SyncedFolder]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM folders WHERE local_path = ?", (path,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return SyncedFolder(
                folder_id=row[0], local_path=row[1], name=row[2],
                organize_mode=row[3], sync_enabled=bool(row[4]),
                devices=json.loads(row[5]), last_sync=row[6],
                file_count=row[7], total_size=row[8], created_at=row[9]
            )
        return None

    def get_all_folders(self) -> List[SyncedFolder]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM folders")
        rows = cursor.fetchall()
        conn.close()

        return [SyncedFolder(
            folder_id=row[0], local_path=row[1], name=row[2],
            organize_mode=row[3], sync_enabled=bool(row[4]),
            devices=json.loads(row[5]), last_sync=row[6],
            file_count=row[7], total_size=row[8], created_at=row[9]
        ) for row in rows]

    def update_folder(self, folder: SyncedFolder) -> bool:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE folders SET
                name = ?, organize_mode = ?, sync_enabled = ?,
                devices = ?, last_sync = ?, file_count = ?, total_size = ?
            WHERE folder_id = ?
        """, (
            folder.name, folder.organize_mode, folder.sync_enabled,
            json.dumps(folder.devices), folder.last_sync,
            folder.file_count, folder.total_size, folder.folder_id
        ))
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        return success

    def delete_folder(self, folder_id: str) -> bool:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM files WHERE folder_id = ?", (folder_id,))
        cursor.execute("DELETE FROM folders WHERE folder_id = ?", (folder_id,))
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        return success

    # File operations
    def add_file(self, file: SyncedFile) -> bool:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO files
                (file_id, folder_id, relative_path, filename, size, checksum,
                 category, subcategory, ai_tags, status, modified_at, synced_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                file.file_id, file.folder_id, file.relative_path, file.filename,
                file.size, file.checksum, file.category, file.subcategory,
                json.dumps(file.ai_tags), file.status, file.modified_at, file.synced_at
            ))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error adding file: {e}")
            return False
        finally:
            conn.close()

    def get_files_by_folder(self, folder_id: str) -> List[SyncedFile]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM files WHERE folder_id = ?", (folder_id,))
        rows = cursor.fetchall()
        conn.close()

        return [SyncedFile(
            file_id=row[0], folder_id=row[1], relative_path=row[2],
            filename=row[3], size=row[4], checksum=row[5],
            category=row[6], subcategory=row[7],
            ai_tags=json.loads(row[8]), status=row[9],
            modified_at=row[10], synced_at=row[11]
        ) for row in rows]

    # Device operations
    def add_device(self, device: Device) -> bool:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO devices
                (device_id, name, device_type, last_seen, ip_address, sync_folders, is_online)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                device.device_id, device.name, device.device_type,
                device.last_seen, device.ip_address,
                json.dumps(device.sync_folders), device.is_online
            ))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error adding device: {e}")
            return False
        finally:
            conn.close()

    def get_all_devices(self) -> List[Device]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM devices")
        rows = cursor.fetchall()
        conn.close()

        return [Device(
            device_id=row[0], name=row[1], device_type=row[2],
            last_seen=row[3], ip_address=row[4],
            sync_folders=json.loads(row[5]), is_online=bool(row[6])
        ) for row in rows]


# ============================================
# AI File Organizer
# ============================================

class AIFileOrganizer:
    """Organizador de archivos con IA"""

    def __init__(self):
        self.categories = FILE_CATEGORIES

    def get_file_category(self, filepath: Path) -> Tuple[str, str]:
        """Determina la categoría y subcategoría de un archivo"""
        ext = filepath.suffix.lower()
        filename_lower = filepath.name.lower()

        # Find category by extension
        for category, info in self.categories.items():
            if ext in info["extensions"]:
                # Try to find subcategory
                subcategory = self._detect_subcategory(filename_lower, info.get("subcategories", {}))
                return category, subcategory

        return "other", ""

    def _detect_subcategory(self, filename: str, subcategories: Dict[str, List[str]]) -> str:
        """Detecta subcategoría basada en el nombre del archivo"""
        for subcat, keywords in subcategories.items():
            for keyword in keywords:
                if keyword in filename:
                    return subcat
        return ""

    def generate_ai_tags(self, filepath: Path) -> List[str]:
        """Genera tags usando IA basados en el contenido/nombre"""
        tags = []
        filename = filepath.name.lower()

        # Date-based tags
        stat = filepath.stat()
        mod_time = datetime.fromtimestamp(stat.st_mtime)
        tags.append(f"year:{mod_time.year}")
        tags.append(f"month:{mod_time.strftime('%B').lower()}")

        # Size-based tags
        size_mb = stat.st_size / (1024 * 1024)
        if size_mb < 1:
            tags.append("size:small")
        elif size_mb < 100:
            tags.append("size:medium")
        else:
            tags.append("size:large")

        # Name-based tags
        if any(x in filename for x in ["final", "v2", "v3", "latest"]):
            tags.append("version:final")
        if any(x in filename for x in ["draft", "wip", "temp"]):
            tags.append("version:draft")
        if any(x in filename for x in ["backup", "bak", "old"]):
            tags.append("type:backup")

        return tags

    def suggest_organization(self, folder_path: Path) -> Dict[str, List[Dict]]:
        """Sugiere cómo organizar una carpeta"""
        suggestions = {category: [] for category in self.categories}
        suggestions["other"] = []

        for filepath in folder_path.iterdir():
            if filepath.is_file() and not filepath.name.startswith('.'):
                category, subcategory = self.get_file_category(filepath)
                tags = self.generate_ai_tags(filepath)

                suggestions[category].append({
                    "file": filepath.name,
                    "path": str(filepath),
                    "category": category,
                    "subcategory": subcategory,
                    "tags": tags,
                    "suggested_path": self._suggest_path(filepath, category, subcategory)
                })

        # Remove empty categories
        return {k: v for k, v in suggestions.items() if v}

    def _suggest_path(self, filepath: Path, category: str, subcategory: str) -> str:
        """Sugiere una ruta organizada para el archivo"""
        mod_time = datetime.fromtimestamp(filepath.stat().st_mtime)

        if subcategory:
            return f"{category}/{subcategory}/{mod_time.year}/{filepath.name}"
        else:
            return f"{category}/{mod_time.year}/{filepath.name}"

    def organize_folder(
        self,
        source_folder: Path,
        dest_folder: Path = None,
        dry_run: bool = True,
        by_date: bool = True
    ) -> Dict[str, Any]:
        """Organiza una carpeta moviendo archivos a categorías"""
        if dest_folder is None:
            dest_folder = source_folder / "_organized"

        results = {
            "moved": [],
            "skipped": [],
            "errors": [],
            "dry_run": dry_run
        }

        suggestions = self.suggest_organization(source_folder)

        for category, files in suggestions.items():
            for file_info in files:
                source_path = Path(file_info["path"])

                # Build destination path
                if by_date:
                    dest_path = dest_folder / file_info["suggested_path"]
                else:
                    if file_info["subcategory"]:
                        dest_path = dest_folder / category / file_info["subcategory"] / source_path.name
                    else:
                        dest_path = dest_folder / category / source_path.name

                try:
                    if not dry_run:
                        dest_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(source_path), str(dest_path))

                    results["moved"].append({
                        "from": str(source_path),
                        "to": str(dest_path),
                        "category": category,
                        "subcategory": file_info["subcategory"]
                    })
                except Exception as e:
                    results["errors"].append({
                        "file": str(source_path),
                        "error": str(e)
                    })

        return results


# ============================================
# Folder Watcher for Auto-Organization
# ============================================

class FolderWatcher:
    """Observador de carpetas para organización automática"""

    def __init__(self, storage: SyncStorage, organizer: AIFileOrganizer):
        self.storage = storage
        self.organizer = organizer
        self._watchers: Dict[str, Any] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self):
        """Iniciar observación de carpetas"""
        self._running = True
        self._thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._thread.start()
        logger.info("FolderWatcher iniciado")

    def stop(self):
        """Detener observación"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("FolderWatcher detenido")

    def _watch_loop(self):
        """Loop principal de observación"""
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler

            class PurmaHandler(FileSystemEventHandler):
                def __init__(handler_self, folder: SyncedFolder, organizer: AIFileOrganizer):
                    handler_self.folder = folder
                    handler_self.organizer = organizer

                def on_created(handler_self, event):
                    if event.is_directory:
                        return

                    filepath = Path(event.src_path)
                    if filepath.name.startswith('.'):
                        return

                    logger.info(f"Nuevo archivo detectado: {filepath}")

                    if handler_self.folder.organize_mode in ["auto", "smart"]:
                        # Auto-organize the file
                        category, subcategory = handler_self.organizer.get_file_category(filepath)

                        # Move to organized location
                        dest_folder = Path(handler_self.folder.local_path) / "_organized"
                        suggested = handler_self.organizer._suggest_path(filepath, category, subcategory)
                        dest_path = dest_folder / suggested

                        try:
                            dest_path.parent.mkdir(parents=True, exist_ok=True)
                            shutil.move(str(filepath), str(dest_path))
                            logger.info(f"Archivo organizado: {filepath} -> {dest_path}")
                        except Exception as e:
                            logger.error(f"Error organizando archivo: {e}")

            observer = Observer()

            # Watch all folders with auto-organization enabled
            for folder in self.storage.get_all_folders():
                if folder.organize_mode in ["auto", "smart"]:
                    path = Path(folder.local_path)
                    if path.exists():
                        handler = PurmaHandler(folder, self.organizer)
                        observer.schedule(handler, str(path), recursive=False)
                        self._watchers[folder.folder_id] = handler
                        logger.info(f"Observando carpeta: {path}")

            observer.start()

            while self._running:
                time.sleep(1)

            observer.stop()
            observer.join()

        except ImportError:
            logger.warning("watchdog no instalado, usando polling")
            self._poll_watch()

    def _poll_watch(self):
        """Fallback polling-based watching"""
        known_files: Dict[str, set] = {}

        while self._running:
            for folder in self.storage.get_all_folders():
                if folder.organize_mode not in ["auto", "smart"]:
                    continue

                path = Path(folder.local_path)
                if not path.exists():
                    continue

                folder_id = folder.folder_id
                if folder_id not in known_files:
                    known_files[folder_id] = set()

                current_files = set(f.name for f in path.iterdir() if f.is_file())
                new_files = current_files - known_files[folder_id]

                for filename in new_files:
                    if filename.startswith('.'):
                        continue

                    filepath = path / filename
                    logger.info(f"Nuevo archivo detectado (polling): {filepath}")

                    # Organize
                    category, subcategory = self.organizer.get_file_category(filepath)
                    dest_folder = path / "_organized"
                    suggested = self.organizer._suggest_path(filepath, category, subcategory)
                    dest_path = dest_folder / suggested

                    try:
                        dest_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(filepath), str(dest_path))
                        logger.info(f"Archivo organizado: {filepath} -> {dest_path}")
                    except Exception as e:
                        logger.error(f"Error organizando: {e}")

                known_files[folder_id] = current_files

            time.sleep(2)


# ============================================
# Sync Engine
# ============================================

class SyncEngine:
    """Motor principal de sincronización"""

    def __init__(self):
        self.storage = SyncStorage()
        self.organizer = AIFileOrganizer()
        self.watcher = FolderWatcher(self.storage, self.organizer)
        self._syncthing_running = False

    def get_status(self) -> Dict[str, Any]:
        """Obtener estado del sistema de sync"""
        folders = self.storage.get_all_folders()
        devices = self.storage.get_all_devices()

        return {
            "status": "active",
            "syncthing_running": self._check_syncthing(),
            "folders_count": len(folders),
            "devices_count": len(devices),
            "devices_online": sum(1 for d in devices if d.is_online),
            "auto_organize_folders": sum(
                1 for f in folders if f.organize_mode in ["auto", "smart"]
            ),
            "watcher_running": self.watcher._running
        }

    def _check_syncthing(self) -> bool:
        """Verificar si Syncthing está corriendo"""
        try:
            result = subprocess.run(
                ["pgrep", "-x", "syncthing"],
                capture_output=True, text=True
            )
            return result.returncode == 0
        except Exception:
            return False

    # Folder management
    def add_sync_folder(
        self,
        path: str,
        name: str = None,
        organize_mode: str = "disabled"
    ) -> Dict[str, Any]:
        """Añadir carpeta para sincronización"""
        path = os.path.expanduser(path)
        folder_path = Path(path)

        if not folder_path.exists():
            return {"error": f"La carpeta no existe: {path}"}

        if not folder_path.is_dir():
            return {"error": f"No es un directorio: {path}"}

        # Check if already added
        existing = self.storage.get_folder_by_path(path)
        if existing:
            return {"error": "La carpeta ya está sincronizada", "folder": existing.to_dict()}

        # Create folder entry
        folder_id = hashlib.md5(path.encode()).hexdigest()[:12]
        folder = SyncedFolder(
            folder_id=folder_id,
            local_path=str(folder_path.absolute()),
            name=name or folder_path.name,
            organize_mode=organize_mode
        )

        # Scan folder
        file_count, total_size = self._scan_folder(folder_path)
        folder.file_count = file_count
        folder.total_size = total_size

        if self.storage.add_folder(folder):
            # Index files
            self._index_folder(folder)

            # Start watching if auto-organize
            if organize_mode in ["auto", "smart"] and not self.watcher._running:
                self.watcher.start()

            return {"success": True, "folder": folder.to_dict()}

        return {"error": "Error al añadir carpeta"}

    def remove_sync_folder(self, folder_id: str) -> Dict[str, Any]:
        """Remover carpeta de sincronización"""
        folder = self.storage.get_folder(folder_id)
        if not folder:
            return {"error": "Carpeta no encontrada"}

        if self.storage.delete_folder(folder_id):
            return {"success": True, "message": f"Carpeta '{folder.name}' removida"}

        return {"error": "Error al remover carpeta"}

    def list_folders(self) -> List[Dict]:
        """Listar todas las carpetas sincronizadas"""
        return [f.to_dict() for f in self.storage.get_all_folders()]

    def set_organize_mode(self, folder_id: str, mode: str) -> Dict[str, Any]:
        """Cambiar modo de organización de una carpeta"""
        if mode not in ["disabled", "manual", "auto", "smart"]:
            return {"error": f"Modo inválido: {mode}"}

        folder = self.storage.get_folder(folder_id)
        if not folder:
            return {"error": "Carpeta no encontrada"}

        folder.organize_mode = mode
        self.storage.update_folder(folder)

        # Restart watcher if needed
        if mode in ["auto", "smart"] and not self.watcher._running:
            self.watcher.start()

        return {"success": True, "folder": folder.to_dict()}

    def _scan_folder(self, folder_path: Path) -> Tuple[int, int]:
        """Escanear carpeta y retornar conteo y tamaño"""
        file_count = 0
        total_size = 0

        for filepath in folder_path.rglob("*"):
            if filepath.is_file() and not filepath.name.startswith('.'):
                file_count += 1
                total_size += filepath.stat().st_size

        return file_count, total_size

    def _index_folder(self, folder: SyncedFolder):
        """Indexar archivos de una carpeta"""
        folder_path = Path(folder.local_path)

        for filepath in folder_path.rglob("*"):
            if filepath.is_file() and not filepath.name.startswith('.'):
                relative_path = filepath.relative_to(folder_path)
                category, subcategory = self.organizer.get_file_category(filepath)
                tags = self.organizer.generate_ai_tags(filepath)
                checksum = self._file_checksum(filepath)

                synced_file = SyncedFile(
                    file_id=hashlib.md5(f"{folder.folder_id}:{relative_path}".encode()).hexdigest()[:16],
                    folder_id=folder.folder_id,
                    relative_path=str(relative_path),
                    filename=filepath.name,
                    size=filepath.stat().st_size,
                    checksum=checksum,
                    category=category,
                    subcategory=subcategory,
                    ai_tags=tags,
                    status="synced",
                    modified_at=datetime.fromtimestamp(filepath.stat().st_mtime).isoformat()
                )

                self.storage.add_file(synced_file)

    def _file_checksum(self, filepath: Path, block_size: int = 65536) -> str:
        """Calcular checksum MD5 de un archivo"""
        hasher = hashlib.md5()
        try:
            with open(filepath, 'rb') as f:
                for block in iter(lambda: f.read(block_size), b''):
                    hasher.update(block)
            return hasher.hexdigest()
        except Exception:
            return ""

    # Organization
    def organize_folder(
        self,
        folder_id: str,
        dry_run: bool = True,
        by_date: bool = True
    ) -> Dict[str, Any]:
        """Organizar una carpeta con IA"""
        folder = self.storage.get_folder(folder_id)
        if not folder:
            return {"error": "Carpeta no encontrada"}

        source_path = Path(folder.local_path)
        dest_path = source_path / "_organized"

        results = self.organizer.organize_folder(
            source_path, dest_path, dry_run=dry_run, by_date=by_date
        )

        if not dry_run:
            # Re-index folder
            self._index_folder(folder)

        return results

    def suggest_organization(self, folder_id: str) -> Dict[str, Any]:
        """Obtener sugerencias de organización para una carpeta"""
        folder = self.storage.get_folder(folder_id)
        if not folder:
            return {"error": "Carpeta no encontrada"}

        suggestions = self.organizer.suggest_organization(Path(folder.local_path))

        return {
            "folder": folder.to_dict(),
            "suggestions": suggestions,
            "total_files": sum(len(files) for files in suggestions.values())
        }

    # Device management
    def register_device(
        self,
        device_id: str,
        name: str,
        device_type: str,
        ip_address: str = ""
    ) -> Dict[str, Any]:
        """Registrar un dispositivo"""
        device = Device(
            device_id=device_id,
            name=name,
            device_type=device_type,
            last_seen=datetime.now().isoformat(),
            ip_address=ip_address,
            is_online=True
        )

        if self.storage.add_device(device):
            return {"success": True, "device": device.to_dict()}

        return {"error": "Error al registrar dispositivo"}

    def list_devices(self) -> List[Dict]:
        """Listar dispositivos registrados"""
        return [d.to_dict() for d in self.storage.get_all_devices()]

    def link_folder_to_device(self, folder_id: str, device_id: str) -> Dict[str, Any]:
        """Vincular carpeta a un dispositivo para sincronización"""
        folder = self.storage.get_folder(folder_id)
        if not folder:
            return {"error": "Carpeta no encontrada"}

        if device_id not in folder.devices:
            folder.devices.append(device_id)
            self.storage.update_folder(folder)

        return {"success": True, "folder": folder.to_dict()}

    # Sync operations
    def sync_now(self, folder_id: str = None) -> Dict[str, Any]:
        """Forzar sincronización"""
        if not self._check_syncthing():
            return {"error": "Syncthing no está corriendo"}

        # Trigger Syncthing rescan
        try:
            # Using syncthing CLI
            if folder_id:
                folder = self.storage.get_folder(folder_id)
                if folder:
                    subprocess.run(
                        ["syncthing", "cli", "operations", "scan", folder.local_path],
                        capture_output=True
                    )
            else:
                subprocess.run(
                    ["syncthing", "cli", "operations", "scan"],
                    capture_output=True
                )

            return {"success": True, "message": "Sincronización iniciada"}
        except Exception as e:
            return {"error": str(e)}

    def start_watcher(self):
        """Iniciar el observador de carpetas"""
        if not self.watcher._running:
            self.watcher.start()
            return {"success": True, "message": "Watcher iniciado"}
        return {"info": "Watcher ya está corriendo"}

    def stop_watcher(self):
        """Detener el observador"""
        if self.watcher._running:
            self.watcher.stop()
            return {"success": True, "message": "Watcher detenido"}
        return {"info": "Watcher no está corriendo"}


# ============================================
# Singleton Instance
# ============================================

_sync_engine: Optional[SyncEngine] = None


def get_sync_engine() -> SyncEngine:
    """Obtener instancia del motor de sync"""
    global _sync_engine
    if _sync_engine is None:
        _sync_engine = SyncEngine()
    return _sync_engine
