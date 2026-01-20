#!/usr/bin/env python3
"""
PurmaLinux - Purma Spaces
Sistema de escritorios contextuales 100% configurables y persistentes.
"""

import os
import json
import subprocess
import asyncio
import signal
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
from dataclasses import dataclass, field, asdict
from enum import Enum
import yaml

# ============================================
# Configuration
# ============================================

HOME = Path.home()
CONFIG_DIR = HOME / ".config" / "purma"
SPACES_DIR = CONFIG_DIR / "spaces"
STATE_FILE = CONFIG_DIR / "spaces_state.json"
SESSIONS_DIR = CONFIG_DIR / "space_sessions"

# Ensure directories exist
SPACES_DIR.mkdir(parents=True, exist_ok=True)
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

# ============================================
# Data Models
# ============================================

class AppAction(Enum):
    OPEN = "open"
    CLOSE = "close"
    FOCUS = "focus"

@dataclass
class AppConfig:
    """Configuration for an app in a space"""
    command: str                          # Command to launch
    name: str = ""                        # Display name
    class_name: str = ""                  # WM_CLASS for window matching
    workspace: int = 1                    # Which workspace/desktop
    delay: float = 0.0                    # Delay before launching (seconds)
    position: Optional[Dict[str, int]] = None  # {x, y, width, height}
    floating: bool = False
    focused: bool = False
    env: Dict[str, str] = field(default_factory=dict)  # Environment variables

    def to_dict(self):
        return {k: v for k, v in asdict(self).items() if v}

@dataclass
class SpaceConfig:
    """Full space configuration"""
    id: str
    name: str
    description: str = ""
    icon: str = ""

    # Visual
    wallpaper: str = ""
    theme: str = ""
    color_scheme: str = ""

    # Apps
    apps_open: List[AppConfig] = field(default_factory=list)
    apps_close: List[str] = field(default_factory=list)  # Process names to close
    apps_block: List[str] = field(default_factory=list)  # Apps to prevent from opening

    # Commands
    on_activate: List[str] = field(default_factory=list)   # Commands on space activation
    on_deactivate: List[str] = field(default_factory=list) # Commands on leaving space

    # Environment
    env_vars: Dict[str, str] = field(default_factory=dict)

    # Window Management
    workspaces: int = 4                   # Number of workspaces in this space
    gaps: int = 10                        # Window gaps

    # Behavior
    auto_restore: bool = True             # Restore window positions
    save_state: bool = True               # Save state when leaving

    # Metadata
    created_at: str = ""
    last_used: str = ""
    use_count: int = 0

@dataclass
class SpaceState:
    """Runtime state of a space (for persistence)"""
    space_id: str
    windows: List[Dict[str, Any]] = field(default_factory=list)
    focused_window: str = ""
    active_workspace: int = 1
    timestamp: str = ""

@dataclass
class GlobalState:
    """Global spaces state"""
    active_space: str = ""
    last_space: str = ""
    auto_restore_on_boot: bool = True
    default_space: str = "default"

# ============================================
# Space Manager
# ============================================

class SpaceManager:
    def __init__(self):
        self.spaces: Dict[str, SpaceConfig] = {}
        self.global_state = GlobalState()
        self.load_all()

    # ============================================
    # Persistence
    # ============================================

    def load_all(self):
        """Load all spaces and global state"""
        self._load_global_state()
        self._load_spaces()
        self._ensure_default_space()

    def _load_global_state(self):
        """Load global state from file"""
        if STATE_FILE.exists():
            try:
                data = json.loads(STATE_FILE.read_text())
                self.global_state = GlobalState(**data)
            except Exception as e:
                print(f"Error loading global state: {e}")

    def _save_global_state(self):
        """Save global state to file"""
        STATE_FILE.write_text(json.dumps(asdict(self.global_state), indent=2))

    def _load_spaces(self):
        """Load all space configurations"""
        self.spaces = {}

        # Load from JSON files
        for file in SPACES_DIR.glob("*.json"):
            try:
                data = json.loads(file.read_text())
                space = self._dict_to_space(data)
                self.spaces[space.id] = space
            except Exception as e:
                print(f"Error loading space {file}: {e}")

        # Load from YAML files
        for file in SPACES_DIR.glob("*.yaml"):
            try:
                data = yaml.safe_load(file.read_text())
                space = self._dict_to_space(data)
                self.spaces[space.id] = space
            except Exception as e:
                print(f"Error loading space {file}: {e}")

    def _dict_to_space(self, data: Dict) -> SpaceConfig:
        """Convert dict to SpaceConfig"""
        apps_open = []
        for app in data.get("apps_open", []):
            if isinstance(app, str):
                apps_open.append(AppConfig(command=app))
            else:
                apps_open.append(AppConfig(**app))

        return SpaceConfig(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            icon=data.get("icon", ""),
            wallpaper=data.get("wallpaper", ""),
            theme=data.get("theme", ""),
            color_scheme=data.get("color_scheme", ""),
            apps_open=apps_open,
            apps_close=data.get("apps_close", []),
            apps_block=data.get("apps_block", []),
            on_activate=data.get("on_activate", []),
            on_deactivate=data.get("on_deactivate", []),
            env_vars=data.get("env_vars", {}),
            workspaces=data.get("workspaces", 4),
            gaps=data.get("gaps", 10),
            auto_restore=data.get("auto_restore", True),
            save_state=data.get("save_state", True),
            created_at=data.get("created_at", ""),
            last_used=data.get("last_used", ""),
            use_count=data.get("use_count", 0),
        )

    def _space_to_dict(self, space: SpaceConfig) -> Dict:
        """Convert SpaceConfig to dict for saving"""
        return {
            "id": space.id,
            "name": space.name,
            "description": space.description,
            "icon": space.icon,
            "wallpaper": space.wallpaper,
            "theme": space.theme,
            "color_scheme": space.color_scheme,
            "apps_open": [app.to_dict() for app in space.apps_open],
            "apps_close": space.apps_close,
            "apps_block": space.apps_block,
            "on_activate": space.on_activate,
            "on_deactivate": space.on_deactivate,
            "env_vars": space.env_vars,
            "workspaces": space.workspaces,
            "gaps": space.gaps,
            "auto_restore": space.auto_restore,
            "save_state": space.save_state,
            "created_at": space.created_at,
            "last_used": space.last_used,
            "use_count": space.use_count,
        }

    def save_space(self, space: SpaceConfig):
        """Save a space configuration"""
        file_path = SPACES_DIR / f"{space.id}.json"
        file_path.write_text(json.dumps(self._space_to_dict(space), indent=2))
        self.spaces[space.id] = space

    def _ensure_default_space(self):
        """Create default space if none exist"""
        if not self.spaces:
            default = SpaceConfig(
                id="default",
                name="Default",
                description="Espacio de trabajo por defecto",
                icon="",
                created_at=datetime.now().isoformat(),
            )
            self.save_space(default)

    # ============================================
    # CRUD Operations
    # ============================================

    def create_space(
        self,
        name: str,
        description: str = "",
        icon: str = "",
        template: str = None
    ) -> SpaceConfig:
        """Create a new space"""
        # Generate ID from name
        space_id = name.lower().replace(" ", "_")

        # Check if exists
        if space_id in self.spaces:
            raise ValueError(f"Space '{space_id}' already exists")

        # Use template if provided
        if template and template in self.spaces:
            base = self.spaces[template]
            space = SpaceConfig(
                id=space_id,
                name=name,
                description=description or base.description,
                icon=icon or base.icon,
                wallpaper=base.wallpaper,
                theme=base.theme,
                apps_open=base.apps_open.copy(),
                apps_close=base.apps_close.copy(),
                on_activate=base.on_activate.copy(),
                on_deactivate=base.on_deactivate.copy(),
                env_vars=base.env_vars.copy(),
                workspaces=base.workspaces,
                gaps=base.gaps,
                created_at=datetime.now().isoformat(),
            )
        else:
            space = SpaceConfig(
                id=space_id,
                name=name,
                description=description,
                icon=icon or "",
                created_at=datetime.now().isoformat(),
            )

        self.save_space(space)
        return space

    def get_space(self, space_id: str) -> Optional[SpaceConfig]:
        """Get a space by ID"""
        return self.spaces.get(space_id)

    def list_spaces(self) -> List[Dict]:
        """List all spaces"""
        return [
            {
                "id": s.id,
                "name": s.name,
                "description": s.description,
                "icon": s.icon,
                "apps_count": len(s.apps_open),
                "last_used": s.last_used,
                "use_count": s.use_count,
                "is_active": s.id == self.global_state.active_space,
            }
            for s in self.spaces.values()
        ]

    def update_space(self, space_id: str, updates: Dict) -> SpaceConfig:
        """Update a space configuration"""
        if space_id not in self.spaces:
            raise ValueError(f"Space '{space_id}' not found")

        space = self.spaces[space_id]

        # Update fields
        for key, value in updates.items():
            if hasattr(space, key) and key not in ["id", "created_at"]:
                if key == "apps_open" and isinstance(value, list):
                    apps = []
                    for app in value:
                        if isinstance(app, str):
                            apps.append(AppConfig(command=app))
                        elif isinstance(app, dict):
                            apps.append(AppConfig(**app))
                        else:
                            apps.append(app)
                    setattr(space, key, apps)
                else:
                    setattr(space, key, value)

        self.save_space(space)
        return space

    def delete_space(self, space_id: str):
        """Delete a space"""
        if space_id == "default":
            raise ValueError("Cannot delete default space")

        if space_id not in self.spaces:
            raise ValueError(f"Space '{space_id}' not found")

        # Remove file
        file_path = SPACES_DIR / f"{space_id}.json"
        if file_path.exists():
            file_path.unlink()

        file_path = SPACES_DIR / f"{space_id}.yaml"
        if file_path.exists():
            file_path.unlink()

        # Remove session
        session_file = SESSIONS_DIR / f"{space_id}.json"
        if session_file.exists():
            session_file.unlink()

        del self.spaces[space_id]

        # Update active space if needed
        if self.global_state.active_space == space_id:
            self.global_state.active_space = "default"
            self._save_global_state()

    # ============================================
    # Window Management (Hyprland/i3/Openbox)
    # ============================================

    async def get_current_windows(self) -> List[Dict]:
        """Get list of current windows with their properties"""
        windows = []

        # Try Hyprland first
        try:
            result = await asyncio.create_subprocess_exec(
                "hyprctl", "clients", "-j",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await result.communicate()
            if result.returncode == 0:
                clients = json.loads(stdout.decode())
                for client in clients:
                    windows.append({
                        "class": client.get("class", ""),
                        "title": client.get("title", ""),
                        "pid": client.get("pid", 0),
                        "workspace": client.get("workspace", {}).get("id", 1),
                        "position": {"x": client.get("at", [0, 0])[0], "y": client.get("at", [0, 0])[1]},
                        "size": {"width": client.get("size", [0, 0])[0], "height": client.get("size", [0, 0])[1]},
                        "floating": client.get("floating", False),
                        "focused": client.get("focusHistoryID", -1) == 0,
                    })
                return windows
        except:
            pass

        # Try wmctrl (works with most WMs)
        try:
            result = await asyncio.create_subprocess_exec(
                "wmctrl", "-l", "-p", "-G",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await result.communicate()
            if result.returncode == 0:
                for line in stdout.decode().strip().split("\n"):
                    if line:
                        parts = line.split(None, 8)
                        if len(parts) >= 8:
                            windows.append({
                                "id": parts[0],
                                "workspace": int(parts[1]) + 1,
                                "pid": int(parts[2]),
                                "position": {"x": int(parts[3]), "y": int(parts[4])},
                                "size": {"width": int(parts[5]), "height": int(parts[6])},
                                "class": parts[7] if len(parts) > 7 else "",
                                "title": parts[8] if len(parts) > 8 else "",
                            })
                return windows
        except:
            pass

        return windows

    async def save_space_state(self, space_id: str):
        """Save current window state for a space"""
        windows = await self.get_current_windows()

        state = SpaceState(
            space_id=space_id,
            windows=windows,
            active_workspace=1,  # TODO: detect active workspace
            timestamp=datetime.now().isoformat(),
        )

        session_file = SESSIONS_DIR / f"{space_id}.json"
        session_file.write_text(json.dumps(asdict(state), indent=2))

    def load_space_state(self, space_id: str) -> Optional[SpaceState]:
        """Load saved state for a space"""
        session_file = SESSIONS_DIR / f"{space_id}.json"
        if session_file.exists():
            try:
                data = json.loads(session_file.read_text())
                return SpaceState(**data)
            except:
                pass
        return None

    # ============================================
    # Space Activation
    # ============================================

    async def activate_space(self, space_id: str, save_current: bool = True) -> Dict:
        """Activate a space"""
        if space_id not in self.spaces:
            return {"success": False, "error": f"Space '{space_id}' not found"}

        space = self.spaces[space_id]
        current_space_id = self.global_state.active_space

        results = {
            "success": True,
            "space": space_id,
            "previous": current_space_id,
            "actions": [],
        }

        # 1. Save current space state if configured
        if save_current and current_space_id and current_space_id in self.spaces:
            current_space = self.spaces[current_space_id]
            if current_space.save_state:
                await self.save_space_state(current_space_id)
                results["actions"].append(f"Saved state for {current_space_id}")

            # Run deactivation commands
            for cmd in current_space.on_deactivate:
                try:
                    await self._run_command(cmd)
                    results["actions"].append(f"Ran deactivate: {cmd}")
                except Exception as e:
                    results["actions"].append(f"Error in deactivate: {e}")

        # 2. Close blocked/unwanted apps
        for app_name in space.apps_close:
            try:
                await self._close_app(app_name)
                results["actions"].append(f"Closed {app_name}")
            except:
                pass

        # 3. Set environment variables
        for key, value in space.env_vars.items():
            os.environ[key] = value
            results["actions"].append(f"Set env {key}")

        # 4. Set wallpaper
        if space.wallpaper:
            await self._set_wallpaper(space.wallpaper)
            results["actions"].append(f"Set wallpaper")

        # 5. Apply theme/gaps
        if space.gaps:
            await self._set_gaps(space.gaps)

        # 6. Run activation commands
        for cmd in space.on_activate:
            try:
                await self._run_command(cmd)
                results["actions"].append(f"Ran activate: {cmd}")
            except Exception as e:
                results["actions"].append(f"Error in activate: {e}")

        # 7. Restore window state or open apps
        saved_state = self.load_space_state(space_id) if space.auto_restore else None

        if saved_state and saved_state.windows:
            # Restore saved windows
            for window in saved_state.windows:
                await self._restore_window(window)
            results["actions"].append(f"Restored {len(saved_state.windows)} windows")
        else:
            # Open configured apps
            for app in space.apps_open:
                try:
                    if app.delay > 0:
                        await asyncio.sleep(app.delay)
                    await self._open_app(app)
                    results["actions"].append(f"Opened {app.command}")
                except Exception as e:
                    results["actions"].append(f"Error opening {app.command}: {e}")

        # 8. Update state
        self.global_state.last_space = current_space_id
        self.global_state.active_space = space_id
        self._save_global_state()

        # Update space metadata
        space.last_used = datetime.now().isoformat()
        space.use_count += 1
        self.save_space(space)

        return results

    async def _run_command(self, command: str):
        """Run a shell command"""
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(HOME),
        )
        await asyncio.wait_for(proc.communicate(), timeout=30)

    async def _close_app(self, app_name: str):
        """Close an application by name"""
        # Try graceful close first
        await self._run_command(f"pkill -TERM -f '{app_name}' || true")
        await asyncio.sleep(0.5)
        # Force kill if still running
        await self._run_command(f"pkill -KILL -f '{app_name}' || true")

    async def _open_app(self, app: AppConfig):
        """Open an application"""
        env = {**os.environ, **app.env}

        # Build command with workspace if supported
        cmd = app.command

        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
            start_new_session=True,
            env=env,
        )

        # Don't wait for the process
        return proc.pid

    async def _set_wallpaper(self, path: str):
        """Set desktop wallpaper"""
        expanded = Path(path).expanduser()
        if not expanded.exists():
            return

        # Try different wallpaper setters
        setters = [
            f"swww img '{expanded}' --transition-type fade",
            f"swaybg -i '{expanded}' -m fill &",
            f"feh --bg-fill '{expanded}'",
            f"nitrogen --set-zoom-fill '{expanded}'",
        ]

        for setter in setters:
            try:
                await self._run_command(setter)
                return
            except:
                continue

    async def _set_gaps(self, gaps: int):
        """Set window gaps"""
        # Hyprland
        try:
            await self._run_command(f"hyprctl keyword general:gaps_in {gaps}")
            await self._run_command(f"hyprctl keyword general:gaps_out {gaps}")
            return
        except:
            pass

        # i3-gaps
        try:
            await self._run_command(f"i3-msg 'gaps inner all set {gaps}'")
            await self._run_command(f"i3-msg 'gaps outer all set {gaps}'")
        except:
            pass

    async def _restore_window(self, window: Dict):
        """Restore a window to its saved position"""
        # This is WM-specific, basic implementation
        class_name = window.get("class", "")
        if not class_name:
            return

        pos = window.get("position", {})
        size = window.get("size", {})

        # Try wmctrl
        try:
            if pos and size:
                await self._run_command(
                    f"wmctrl -r '{class_name}' -e 0,{pos.get('x', 0)},{pos.get('y', 0)},"
                    f"{size.get('width', 800)},{size.get('height', 600)}"
                )
        except:
            pass

    # ============================================
    # Convenience Methods
    # ============================================

    def get_active_space(self) -> Optional[SpaceConfig]:
        """Get the currently active space"""
        if self.global_state.active_space:
            return self.spaces.get(self.global_state.active_space)
        return None

    async def quick_switch(self, direction: str = "next") -> Dict:
        """Switch to next/previous space"""
        space_ids = list(self.spaces.keys())
        if not space_ids:
            return {"success": False, "error": "No spaces available"}

        current_idx = 0
        if self.global_state.active_space in space_ids:
            current_idx = space_ids.index(self.global_state.active_space)

        if direction == "next":
            new_idx = (current_idx + 1) % len(space_ids)
        elif direction == "prev":
            new_idx = (current_idx - 1) % len(space_ids)
        else:
            return {"success": False, "error": f"Invalid direction: {direction}"}

        return await self.activate_space(space_ids[new_idx])

    async def restore_on_boot(self) -> Dict:
        """Restore last active space on boot"""
        if not self.global_state.auto_restore_on_boot:
            return {"success": False, "message": "Auto-restore disabled"}

        space_id = self.global_state.active_space or self.global_state.default_space
        if space_id and space_id in self.spaces:
            return await self.activate_space(space_id, save_current=False)

        return {"success": False, "message": "No space to restore"}


# ============================================
# Built-in Space Templates
# ============================================

SPACE_TEMPLATES = {
    "work": {
        "name": "Work",
        "description": "Entorno de trabajo profesional",
        "icon": "",
        "apps_open": [
            {"command": "firefox", "workspace": 1},
            {"command": "code", "workspace": 2, "delay": 1},
            {"command": "slack", "workspace": 3, "delay": 2},
            {"command": "kitty", "workspace": 2, "delay": 0.5},
        ],
        "apps_close": ["steam", "discord", "spotify"],
        "on_activate": [
            "notify-send 'Purma Spaces' 'Modo trabajo activado'",
        ],
        "workspaces": 4,
        "gaps": 8,
    },
    "code": {
        "name": "Coding",
        "description": "Entorno de desarrollo",
        "icon": "",
        "apps_open": [
            {"command": "code", "workspace": 1},
            {"command": "kitty", "workspace": 1, "delay": 0.5},
            {"command": "firefox --new-window https://devdocs.io", "workspace": 2, "delay": 1},
        ],
        "apps_close": ["slack", "teams", "zoom"],
        "env_vars": {
            "EDITOR": "code",
            "VISUAL": "code",
        },
        "workspaces": 3,
        "gaps": 4,
    },
    "design": {
        "name": "Design",
        "description": "Entorno de diseño creativo",
        "icon": "",
        "apps_open": [
            {"command": "figma-linux", "workspace": 1},
            {"command": "gimp", "workspace": 2, "delay": 1},
            {"command": "firefox --new-window https://coolors.co", "workspace": 3, "delay": 1},
        ],
        "apps_close": ["code", "slack"],
        "workspaces": 4,
        "gaps": 12,
    },
    "gaming": {
        "name": "Gaming",
        "description": "Modo gaming - máximo rendimiento",
        "icon": "",
        "apps_open": [
            {"command": "steam", "workspace": 1},
            {"command": "discord", "workspace": 2, "delay": 1},
        ],
        "apps_close": ["slack", "teams", "code"],
        "on_activate": [
            "notify-send 'Purma Spaces' 'Modo gaming activado'",
        ],
        "workspaces": 2,
        "gaps": 0,
    },
    "focus": {
        "name": "Focus",
        "description": "Modo concentración - sin distracciones",
        "icon": "",
        "apps_open": [],
        "apps_close": ["slack", "discord", "telegram", "teams", "zoom"],
        "apps_block": ["slack", "discord", "telegram"],
        "on_activate": [
            "notify-send 'Purma Spaces' 'Modo focus activado - Distracciones bloqueadas'",
        ],
        "workspaces": 2,
        "gaps": 20,
    },
    "media": {
        "name": "Media",
        "description": "Entretenimiento y multimedia",
        "icon": "",
        "apps_open": [
            {"command": "spotify", "workspace": 1},
            {"command": "firefox --new-window https://youtube.com", "workspace": 2, "delay": 1},
        ],
        "workspaces": 2,
        "gaps": 0,
    },
}


def create_template_space(manager: SpaceManager, template_name: str) -> SpaceConfig:
    """Create a space from a built-in template"""
    if template_name not in SPACE_TEMPLATES:
        raise ValueError(f"Template '{template_name}' not found")

    template = SPACE_TEMPLATES[template_name]

    space = manager.create_space(
        name=template["name"],
        description=template.get("description", ""),
        icon=template.get("icon", ""),
    )

    # Apply template settings
    manager.update_space(space.id, template)

    return manager.get_space(space.id)


# Global instance
space_manager = SpaceManager()
