"""
PurmaLinux - GameHub Module
Centro unificado de gaming con AI

Integra: Steam, Lutris, Heroic, Bottles, juegos nativos
Características: ProtonDB integration, GameMode, optimizaciones AI
"""

import os
import json
import asyncio
import subprocess
import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
import aiohttp
import aiofiles
import re

# ═══════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════

class GameSource(Enum):
    STEAM = "steam"
    LUTRIS = "lutris"
    HEROIC = "heroic"
    BOTTLES = "bottles"
    NATIVE = "native"
    CUSTOM = "custom"

class ProtonRating(Enum):
    PLATINUM = "platinum"  # Funciona perfecto
    GOLD = "gold"          # Funciona con ajustes menores
    SILVER = "silver"      # Funciona con ajustes
    BRONZE = "bronze"      # Funciona pero con problemas
    BORKED = "borked"      # No funciona
    PENDING = "pending"    # Sin datos
    NATIVE = "native"      # Juego nativo Linux

@dataclass
class Game:
    id: str
    name: str
    source: GameSource
    app_id: Optional[str] = None  # Steam App ID
    install_path: Optional[str] = None
    executable: Optional[str] = None
    icon: Optional[str] = None
    banner: Optional[str] = None
    proton_rating: ProtonRating = ProtonRating.PENDING
    last_played: Optional[datetime] = None
    playtime_minutes: int = 0
    is_installed: bool = True
    is_favorite: bool = False
    launch_options: Optional[str] = None
    proton_version: Optional[str] = None
    notes: Optional[str] = None

@dataclass
class GameSession:
    game_id: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    fps_avg: Optional[float] = None
    fps_min: Optional[float] = None
    fps_max: Optional[float] = None

# ═══════════════════════════════════════════════════════════════════
# STORAGE
# ═══════════════════════════════════════════════════════════════════

class GameHubStorage:
    """Almacenamiento SQLite para GameHub"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.expanduser("~/.purma/gamehub/gamehub.db")

        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS games (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    source TEXT NOT NULL,
                    app_id TEXT,
                    install_path TEXT,
                    executable TEXT,
                    icon TEXT,
                    banner TEXT,
                    proton_rating TEXT DEFAULT 'pending',
                    last_played TEXT,
                    playtime_minutes INTEGER DEFAULT 0,
                    is_installed INTEGER DEFAULT 1,
                    is_favorite INTEGER DEFAULT 0,
                    launch_options TEXT,
                    proton_version TEXT,
                    notes TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    game_id TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    fps_avg REAL,
                    fps_min REAL,
                    fps_max REAL,
                    FOREIGN KEY (game_id) REFERENCES games(id)
                );

                CREATE TABLE IF NOT EXISTS protondb_cache (
                    app_id TEXT PRIMARY KEY,
                    rating TEXT,
                    confidence TEXT,
                    score REAL,
                    best_proton TEXT,
                    tweaks TEXT,
                    fetched_at TEXT
                );

                CREATE TABLE IF NOT EXISTS optimizations (
                    game_id TEXT PRIMARY KEY,
                    env_vars TEXT,
                    launch_args TEXT,
                    proton_version TEXT,
                    gamemode INTEGER DEFAULT 1,
                    mangohud INTEGER DEFAULT 0,
                    fsr INTEGER DEFAULT 0,
                    notes TEXT,
                    FOREIGN KEY (game_id) REFERENCES games(id)
                );

                CREATE INDEX IF NOT EXISTS idx_games_source ON games(source);
                CREATE INDEX IF NOT EXISTS idx_games_last_played ON games(last_played);
                CREATE INDEX IF NOT EXISTS idx_sessions_game ON sessions(game_id);
            """)

    def save_game(self, game: Game):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO games
                (id, name, source, app_id, install_path, executable, icon, banner,
                 proton_rating, last_played, playtime_minutes, is_installed,
                 is_favorite, launch_options, proton_version, notes, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                game.id, game.name, game.source.value, game.app_id,
                game.install_path, game.executable, game.icon, game.banner,
                game.proton_rating.value,
                game.last_played.isoformat() if game.last_played else None,
                game.playtime_minutes, int(game.is_installed), int(game.is_favorite),
                game.launch_options, game.proton_version, game.notes,
                datetime.now().isoformat()
            ))

    def get_game(self, game_id: str) -> Optional[Game]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM games WHERE id = ?", (game_id,)
            ).fetchone()

            if row:
                return self._row_to_game(row)
        return None

    def get_all_games(self, source: Optional[GameSource] = None) -> List[Game]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            if source:
                rows = conn.execute(
                    "SELECT * FROM games WHERE source = ? ORDER BY last_played DESC",
                    (source.value,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM games ORDER BY last_played DESC NULLS LAST"
                ).fetchall()

            return [self._row_to_game(row) for row in rows]

    def get_recent_games(self, limit: int = 10) -> List[Game]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT * FROM games
                WHERE last_played IS NOT NULL
                ORDER BY last_played DESC
                LIMIT ?
            """, (limit,)).fetchall()

            return [self._row_to_game(row) for row in rows]

    def get_favorites(self) -> List[Game]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM games WHERE is_favorite = 1 ORDER BY name"
            ).fetchall()

            return [self._row_to_game(row) for row in rows]

    def _row_to_game(self, row) -> Game:
        return Game(
            id=row['id'],
            name=row['name'],
            source=GameSource(row['source']),
            app_id=row['app_id'],
            install_path=row['install_path'],
            executable=row['executable'],
            icon=row['icon'],
            banner=row['banner'],
            proton_rating=ProtonRating(row['proton_rating']),
            last_played=datetime.fromisoformat(row['last_played']) if row['last_played'] else None,
            playtime_minutes=row['playtime_minutes'],
            is_installed=bool(row['is_installed']),
            is_favorite=bool(row['is_favorite']),
            launch_options=row['launch_options'],
            proton_version=row['proton_version'],
            notes=row['notes']
        )

    def cache_protondb(self, app_id: str, data: dict):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO protondb_cache
                (app_id, rating, confidence, score, best_proton, tweaks, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                app_id, data.get('rating'), data.get('confidence'),
                data.get('score'), data.get('best_proton'),
                json.dumps(data.get('tweaks', [])),
                datetime.now().isoformat()
            ))

    def get_protondb_cache(self, app_id: str) -> Optional[dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM protondb_cache WHERE app_id = ?", (app_id,)
            ).fetchone()

            if row:
                return dict(row)
        return None

# ═══════════════════════════════════════════════════════════════════
# GAME SCANNERS
# ═══════════════════════════════════════════════════════════════════

class SteamScanner:
    """Escanea juegos instalados de Steam"""

    STEAM_PATHS = [
        "~/.steam/steam",
        "~/.local/share/Steam",
        "~/.steam/debian-installation"
    ]

    def __init__(self):
        self.steam_path = self._find_steam_path()

    def _find_steam_path(self) -> Optional[Path]:
        for path in self.STEAM_PATHS:
            expanded = Path(os.path.expanduser(path))
            if expanded.exists():
                return expanded
        return None

    def scan(self) -> List[Game]:
        games = []

        if not self.steam_path:
            return games

        # Buscar libraryfolders.vdf para encontrar todas las bibliotecas
        library_file = self.steam_path / "steamapps" / "libraryfolders.vdf"
        library_paths = [self.steam_path / "steamapps"]

        if library_file.exists():
            try:
                content = library_file.read_text()
                # Parsear VDF simple para encontrar paths adicionales
                paths = re.findall(r'"path"\s+"([^"]+)"', content)
                for p in paths:
                    lib_path = Path(p) / "steamapps"
                    if lib_path.exists():
                        library_paths.append(lib_path)
            except Exception:
                pass

        # Escanear cada biblioteca
        for lib_path in library_paths:
            games.extend(self._scan_library(lib_path))

        return games

    def _scan_library(self, library_path: Path) -> List[Game]:
        games = []

        for manifest in library_path.glob("appmanifest_*.acf"):
            try:
                game = self._parse_manifest(manifest, library_path)
                if game:
                    games.append(game)
            except Exception:
                continue

        return games

    def _parse_manifest(self, manifest_path: Path, library_path: Path) -> Optional[Game]:
        content = manifest_path.read_text()

        # Parsear campos básicos del ACF
        app_id = re.search(r'"appid"\s+"(\d+)"', content)
        name = re.search(r'"name"\s+"([^"]+)"', content)
        install_dir = re.search(r'"installdir"\s+"([^"]+)"', content)

        if not all([app_id, name]):
            return None

        app_id = app_id.group(1)
        game_name = name.group(1)

        # Ignorar herramientas de Steam (Proton, etc.)
        if any(x in game_name.lower() for x in ['proton', 'steamworks', 'redistributable']):
            return None

        install_path = None
        if install_dir:
            install_path = str(library_path / "common" / install_dir.group(1))

        # Buscar icono
        icon_path = self.steam_path / "appcache" / "librarycache" / f"{app_id}_icon.jpg"
        banner_path = self.steam_path / "appcache" / "librarycache" / f"{app_id}_header.jpg"

        return Game(
            id=f"steam_{app_id}",
            name=game_name,
            source=GameSource.STEAM,
            app_id=app_id,
            install_path=install_path,
            icon=str(icon_path) if icon_path.exists() else None,
            banner=str(banner_path) if banner_path.exists() else None,
            is_installed=True
        )


class LutrisScanner:
    """Escanea juegos de Lutris"""

    LUTRIS_DB_PATH = "~/.local/share/lutris/pga.db"

    def scan(self) -> List[Game]:
        games = []
        db_path = os.path.expanduser(self.LUTRIS_DB_PATH)

        if not os.path.exists(db_path):
            return games

        try:
            with sqlite3.connect(db_path) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute("""
                    SELECT id, name, slug, runner, directory, installed,
                           lastplayed, playtime
                    FROM games
                    WHERE installed = 1
                """).fetchall()

                for row in rows:
                    # Buscar icono
                    icon_path = os.path.expanduser(
                        f"~/.local/share/lutris/coverart/{row['slug']}.jpg"
                    )
                    banner_path = os.path.expanduser(
                        f"~/.local/share/lutris/banners/{row['slug']}.jpg"
                    )

                    games.append(Game(
                        id=f"lutris_{row['slug']}",
                        name=row['name'],
                        source=GameSource.LUTRIS,
                        install_path=row['directory'],
                        icon=icon_path if os.path.exists(icon_path) else None,
                        banner=banner_path if os.path.exists(banner_path) else None,
                        last_played=datetime.fromtimestamp(row['lastplayed']) if row['lastplayed'] else None,
                        playtime_minutes=int(row['playtime'] * 60) if row['playtime'] else 0,
                        is_installed=bool(row['installed'])
                    ))
        except Exception:
            pass

        return games


class HeroicScanner:
    """Escanea juegos de Heroic Games Launcher (Epic/GOG)"""

    HEROIC_CONFIG = "~/.config/heroic"

    def scan(self) -> List[Game]:
        games = []
        config_path = os.path.expanduser(self.HEROIC_CONFIG)

        if not os.path.exists(config_path):
            return games

        # Escanear Epic Games
        games.extend(self._scan_epic(config_path))

        # Escanear GOG
        games.extend(self._scan_gog(config_path))

        return games

    def _scan_epic(self, config_path: str) -> List[Game]:
        games = []
        library_file = os.path.join(config_path, "store_cache", "legendary_library.json")

        if os.path.exists(library_file):
            try:
                with open(library_file) as f:
                    data = json.load(f)

                for app_name, info in data.get('library', {}).items():
                    if info.get('is_installed'):
                        games.append(Game(
                            id=f"heroic_epic_{app_name}",
                            name=info.get('title', app_name),
                            source=GameSource.HEROIC,
                            app_id=app_name,
                            install_path=info.get('install_path'),
                            is_installed=True
                        ))
            except Exception:
                pass

        return games

    def _scan_gog(self, config_path: str) -> List[Game]:
        games = []
        library_file = os.path.join(config_path, "store_cache", "gog_library.json")

        if os.path.exists(library_file):
            try:
                with open(library_file) as f:
                    data = json.load(f)

                for game_info in data.get('games', []):
                    if game_info.get('is_installed'):
                        games.append(Game(
                            id=f"heroic_gog_{game_info.get('app_name')}",
                            name=game_info.get('title'),
                            source=GameSource.HEROIC,
                            app_id=game_info.get('app_name'),
                            install_path=game_info.get('install_path'),
                            is_installed=True
                        ))
            except Exception:
                pass

        return games


class NativeScanner:
    """Escanea juegos nativos de Linux (.desktop files)"""

    DESKTOP_PATHS = [
        "~/.local/share/applications",
        "/usr/share/applications"
    ]

    GAME_CATEGORIES = ['Game', 'ActionGame', 'AdventureGame', 'ArcadeGame',
                       'BoardGame', 'BlocksGame', 'CardGame', 'KidsGame',
                       'LogicGame', 'RolePlaying', 'Shooter', 'Simulation',
                       'SportsGame', 'StrategyGame']

    def scan(self) -> List[Game]:
        games = []
        seen = set()

        for path in self.DESKTOP_PATHS:
            expanded = os.path.expanduser(path)
            if not os.path.exists(expanded):
                continue

            for desktop_file in Path(expanded).glob("*.desktop"):
                try:
                    game = self._parse_desktop(desktop_file)
                    if game and game.id not in seen:
                        games.append(game)
                        seen.add(game.id)
                except Exception:
                    continue

        return games

    def _parse_desktop(self, desktop_path: Path) -> Optional[Game]:
        content = desktop_path.read_text()

        # Verificar si es un juego
        categories_match = re.search(r'^Categories=(.+)$', content, re.MULTILINE)
        if not categories_match:
            return None

        categories = categories_match.group(1).split(';')
        if not any(cat in self.GAME_CATEGORIES for cat in categories):
            return None

        # Parsear campos
        name_match = re.search(r'^Name=(.+)$', content, re.MULTILINE)
        exec_match = re.search(r'^Exec=(.+)$', content, re.MULTILINE)
        icon_match = re.search(r'^Icon=(.+)$', content, re.MULTILINE)

        if not name_match:
            return None

        name = name_match.group(1)

        # Ignorar Steam/Lutris launchers
        if any(x in name.lower() for x in ['steam', 'lutris', 'heroic', 'bottles']):
            return None

        return Game(
            id=f"native_{desktop_path.stem}",
            name=name,
            source=GameSource.NATIVE,
            executable=exec_match.group(1) if exec_match else None,
            icon=icon_match.group(1) if icon_match else None,
            proton_rating=ProtonRating.NATIVE,
            is_installed=True
        )

# ═══════════════════════════════════════════════════════════════════
# PROTONDB INTEGRATION
# ═══════════════════════════════════════════════════════════════════

class ProtonDBClient:
    """Cliente para consultar ProtonDB"""

    API_URL = "https://www.protondb.com/api/v1/reports/summaries"

    def __init__(self, storage: GameHubStorage):
        self.storage = storage

    async def get_rating(self, app_id: str) -> dict:
        # Verificar caché primero
        cached = self.storage.get_protondb_cache(app_id)
        if cached:
            # Caché válido por 7 días
            fetched = datetime.fromisoformat(cached['fetched_at'])
            if (datetime.now() - fetched).days < 7:
                return cached

        # Consultar API
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.API_URL}/{app_id}.json"
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()

                        result = {
                            'rating': data.get('tier', 'pending'),
                            'confidence': data.get('confidence', 'low'),
                            'score': data.get('score', 0),
                            'best_proton': data.get('bestReportedTier'),
                            'tweaks': []
                        }

                        self.storage.cache_protondb(app_id, result)
                        return result
        except Exception:
            pass

        return {'rating': 'pending', 'confidence': 'none'}

    def rating_to_enum(self, rating: str) -> ProtonRating:
        mapping = {
            'platinum': ProtonRating.PLATINUM,
            'gold': ProtonRating.GOLD,
            'silver': ProtonRating.SILVER,
            'bronze': ProtonRating.BRONZE,
            'borked': ProtonRating.BORKED,
            'pending': ProtonRating.PENDING
        }
        return mapping.get(rating.lower(), ProtonRating.PENDING)

# ═══════════════════════════════════════════════════════════════════
# GAME LAUNCHER
# ═══════════════════════════════════════════════════════════════════

class GameLauncher:
    """Lanza juegos con optimizaciones"""

    def __init__(self, storage: GameHubStorage):
        self.storage = storage
        self.current_session: Optional[GameSession] = None

    async def launch(self, game: Game, use_gamemode: bool = True,
                     use_mangohud: bool = False) -> bool:
        """Lanza un juego con las optimizaciones configuradas"""

        # Construir comando según la fuente
        if game.source == GameSource.STEAM:
            return await self._launch_steam(game, use_gamemode, use_mangohud)
        elif game.source == GameSource.LUTRIS:
            return await self._launch_lutris(game)
        elif game.source == GameSource.HEROIC:
            return await self._launch_heroic(game)
        elif game.source == GameSource.NATIVE:
            return await self._launch_native(game, use_gamemode, use_mangohud)

        return False

    async def _launch_steam(self, game: Game, gamemode: bool, mangohud: bool) -> bool:
        """Lanza juego de Steam"""
        if not game.app_id:
            return False

        # Construir launch options
        options = []
        if gamemode:
            options.append("gamemoderun")
        if mangohud:
            options.append("mangohud")

        # Usar steam:// protocol
        cmd = ["steam", f"steam://rungameid/{game.app_id}"]

        # Si hay opciones, configurarlas via launch options de Steam
        # Por ahora, lanzamos directamente
        try:
            subprocess.Popen(cmd, start_new_session=True)

            # Registrar sesión
            self.current_session = GameSession(
                game_id=game.id,
                started_at=datetime.now()
            )

            # Actualizar last_played
            game.last_played = datetime.now()
            self.storage.save_game(game)

            return True
        except Exception:
            return False

    async def _launch_lutris(self, game: Game) -> bool:
        """Lanza juego de Lutris"""
        game_slug = game.id.replace("lutris_", "")

        try:
            subprocess.Popen(
                ["lutris", f"lutris:rungame/{game_slug}"],
                start_new_session=True
            )

            game.last_played = datetime.now()
            self.storage.save_game(game)
            return True
        except Exception:
            return False

    async def _launch_heroic(self, game: Game) -> bool:
        """Lanza juego de Heroic"""
        try:
            # Heroic usa xdg-open con su protocol
            subprocess.Popen(
                ["heroic", "--no-gui", f"launch {game.app_id}"],
                start_new_session=True
            )

            game.last_played = datetime.now()
            self.storage.save_game(game)
            return True
        except Exception:
            return False

    async def _launch_native(self, game: Game, gamemode: bool, mangohud: bool) -> bool:
        """Lanza juego nativo"""
        if not game.executable:
            return False

        cmd = []
        if gamemode:
            cmd.append("gamemoderun")
        if mangohud:
            cmd.append("mangohud")

        # Parsear el ejecutable (puede tener %u, %f, etc.)
        exe = re.sub(r'%[a-zA-Z]', '', game.executable).strip()
        cmd.extend(exe.split())

        try:
            subprocess.Popen(cmd, start_new_session=True)

            game.last_played = datetime.now()
            self.storage.save_game(game)
            return True
        except Exception:
            return False

# ═══════════════════════════════════════════════════════════════════
# GAMEMODE MANAGER
# ═══════════════════════════════════════════════════════════════════

class GameModeManager:
    """Gestiona el modo gaming del sistema"""

    @staticmethod
    def is_available() -> bool:
        """Verifica si gamemode está instalado"""
        return os.path.exists("/usr/bin/gamemoderun") or \
               os.path.exists("/usr/local/bin/gamemoderun")

    @staticmethod
    def is_active() -> bool:
        """Verifica si gamemode está activo"""
        try:
            result = subprocess.run(
                ["gamemoded", "-s"],
                capture_output=True,
                text=True
            )
            return "active" in result.stdout.lower()
        except Exception:
            return False

    @staticmethod
    async def get_status() -> dict:
        """Obtiene estado completo de gamemode"""
        return {
            'available': GameModeManager.is_available(),
            'active': GameModeManager.is_active(),
            'clients': GameModeManager._get_clients()
        }

    @staticmethod
    def _get_clients() -> int:
        """Cuenta clientes activos de gamemode"""
        try:
            result = subprocess.run(
                ["gamemoded", "-s"],
                capture_output=True,
                text=True
            )
            # Parsear número de clientes
            match = re.search(r'(\d+)\s+client', result.stdout)
            return int(match.group(1)) if match else 0
        except Exception:
            return 0

# ═══════════════════════════════════════════════════════════════════
# MAIN ENGINE
# ═══════════════════════════════════════════════════════════════════

class GameHubEngine:
    """Motor principal de GameHub"""

    def __init__(self):
        self.storage = GameHubStorage()
        self.protondb = ProtonDBClient(self.storage)
        self.launcher = GameLauncher(self.storage)

        self.scanners = {
            GameSource.STEAM: SteamScanner(),
            GameSource.LUTRIS: LutrisScanner(),
            GameSource.HEROIC: HeroicScanner(),
            GameSource.NATIVE: NativeScanner()
        }

    async def scan_all(self) -> Dict[str, int]:
        """Escanea todas las fuentes de juegos"""
        counts = {}

        for source, scanner in self.scanners.items():
            try:
                games = scanner.scan()
                for game in games:
                    self.storage.save_game(game)
                counts[source.value] = len(games)
            except Exception as e:
                counts[source.value] = 0

        return counts

    async def get_all_games(self, source: Optional[str] = None) -> List[dict]:
        """Obtiene todos los juegos"""
        game_source = GameSource(source) if source else None
        games = self.storage.get_all_games(game_source)
        return [self._game_to_dict(g) for g in games]

    async def get_recent_games(self, limit: int = 10) -> List[dict]:
        """Obtiene juegos recientes"""
        games = self.storage.get_recent_games(limit)
        return [self._game_to_dict(g) for g in games]

    async def get_favorites(self) -> List[dict]:
        """Obtiene juegos favoritos"""
        games = self.storage.get_favorites()
        return [self._game_to_dict(g) for g in games]

    async def get_game(self, game_id: str) -> Optional[dict]:
        """Obtiene un juego por ID"""
        game = self.storage.get_game(game_id)
        if game:
            return self._game_to_dict(game)
        return None

    async def launch_game(self, game_id: str, gamemode: bool = True,
                          mangohud: bool = False) -> dict:
        """Lanza un juego"""
        game = self.storage.get_game(game_id)
        if not game:
            return {'success': False, 'error': 'Game not found'}

        success = await self.launcher.launch(game, gamemode, mangohud)
        return {
            'success': success,
            'game': self._game_to_dict(game)
        }

    async def toggle_favorite(self, game_id: str) -> dict:
        """Toggle favorito de un juego"""
        game = self.storage.get_game(game_id)
        if not game:
            return {'success': False, 'error': 'Game not found'}

        game.is_favorite = not game.is_favorite
        self.storage.save_game(game)

        return {
            'success': True,
            'is_favorite': game.is_favorite
        }

    async def get_proton_info(self, game_id: str) -> dict:
        """Obtiene información de ProtonDB para un juego"""
        game = self.storage.get_game(game_id)
        if not game or not game.app_id:
            return {'error': 'Game not found or no app_id'}

        info = await self.protondb.get_rating(game.app_id)

        # Actualizar rating del juego
        game.proton_rating = self.protondb.rating_to_enum(info.get('rating', 'pending'))
        self.storage.save_game(game)

        return info

    async def get_status(self) -> dict:
        """Estado general de GameHub"""
        all_games = self.storage.get_all_games()

        by_source = {}
        for game in all_games:
            source = game.source.value
            by_source[source] = by_source.get(source, 0) + 1

        return {
            'total_games': len(all_games),
            'by_source': by_source,
            'gamemode': await GameModeManager.get_status(),
            'sources_available': {
                'steam': self.scanners[GameSource.STEAM].steam_path is not None,
                'lutris': os.path.exists(os.path.expanduser("~/.local/share/lutris")),
                'heroic': os.path.exists(os.path.expanduser("~/.config/heroic")),
                'native': True
            }
        }

    async def search(self, query: str) -> List[dict]:
        """Busca juegos por nombre"""
        all_games = self.storage.get_all_games()
        query_lower = query.lower()

        matches = [
            self._game_to_dict(g) for g in all_games
            if query_lower in g.name.lower()
        ]

        return matches

    def _game_to_dict(self, game: Game) -> dict:
        return {
            'id': game.id,
            'name': game.name,
            'source': game.source.value,
            'app_id': game.app_id,
            'install_path': game.install_path,
            'icon': game.icon,
            'banner': game.banner,
            'proton_rating': game.proton_rating.value,
            'last_played': game.last_played.isoformat() if game.last_played else None,
            'playtime_hours': round(game.playtime_minutes / 60, 1),
            'is_installed': game.is_installed,
            'is_favorite': game.is_favorite,
            'launch_options': game.launch_options,
            'proton_version': game.proton_version
        }

# ═══════════════════════════════════════════════════════════════════
# FASTAPI ROUTES
# ═══════════════════════════════════════════════════════════════════

def register_gamehub_routes(app):
    """Registra las rutas de GameHub en la aplicación FastAPI"""
    from fastapi import APIRouter, HTTPException
    from pydantic import BaseModel

    router = APIRouter(prefix="/gamehub", tags=["GameHub"])
    engine = GameHubEngine()

    class LaunchRequest(BaseModel):
        game_id: str
        gamemode: bool = True
        mangohud: bool = False

    @router.get("/status")
    async def get_status():
        """Estado de GameHub"""
        return await engine.get_status()

    @router.post("/scan")
    async def scan_games():
        """Escanea todas las fuentes de juegos"""
        counts = await engine.scan_all()
        return {'success': True, 'scanned': counts}

    @router.get("/games")
    async def get_games(source: Optional[str] = None):
        """Lista todos los juegos"""
        games = await engine.get_all_games(source)
        return {'games': games, 'count': len(games)}

    @router.get("/games/recent")
    async def get_recent(limit: int = 10):
        """Juegos recientes"""
        games = await engine.get_recent_games(limit)
        return {'games': games}

    @router.get("/games/favorites")
    async def get_favorites():
        """Juegos favoritos"""
        games = await engine.get_favorites()
        return {'games': games}

    @router.get("/games/{game_id}")
    async def get_game(game_id: str):
        """Obtiene un juego específico"""
        game = await engine.get_game(game_id)
        if not game:
            raise HTTPException(status_code=404, detail="Game not found")
        return game

    @router.post("/games/{game_id}/launch")
    async def launch_game(game_id: str, gamemode: bool = True, mangohud: bool = False):
        """Lanza un juego"""
        result = await engine.launch_game(game_id, gamemode, mangohud)
        if not result['success']:
            raise HTTPException(status_code=400, detail=result.get('error'))
        return result

    @router.post("/games/{game_id}/favorite")
    async def toggle_favorite(game_id: str):
        """Toggle favorito"""
        result = await engine.toggle_favorite(game_id)
        if not result['success']:
            raise HTTPException(status_code=404, detail=result.get('error'))
        return result

    @router.get("/games/{game_id}/protondb")
    async def get_protondb(game_id: str):
        """Información de ProtonDB"""
        return await engine.get_proton_info(game_id)

    @router.get("/search")
    async def search_games(q: str):
        """Busca juegos"""
        games = await engine.search(q)
        return {'games': games, 'count': len(games)}

    @router.get("/gamemode")
    async def get_gamemode_status():
        """Estado de GameMode"""
        return await GameModeManager.get_status()

    app.include_router(router)


# Para testing
if __name__ == "__main__":
    import asyncio

    async def test():
        engine = GameHubEngine()

        print("Scanning games...")
        counts = await engine.scan_all()
        print(f"Found: {counts}")

        print("\nRecent games:")
        recent = await engine.get_recent_games(5)
        for game in recent:
            print(f"  - {game['name']} ({game['source']})")

        print("\nStatus:")
        status = await engine.get_status()
        print(json.dumps(status, indent=2))

    asyncio.run(test())
