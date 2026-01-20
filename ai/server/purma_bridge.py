"""
PurmaLinux Bridge - AI-Augmented Terminal
"A terminal that understands what you want to do, not just what you type"

Features:
- Natural language to command translation
- Semantic autocomplete
- Inline error explanations with solutions
- Semantic history search
- Sandbox mode for dangerous commands
- Smart confirmation for destructive operations
"""

import asyncio
import hashlib
import json
import os
import re
import shlex
import subprocess
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import sqlite3


# ============================================
# Configuration
# ============================================

BRIDGE_CONFIG_DIR = Path.home() / ".config" / "purma" / "bridge"
BRIDGE_HISTORY_DB = BRIDGE_CONFIG_DIR / "history.db"
BRIDGE_CONFIG_FILE = BRIDGE_CONFIG_DIR / "config.json"

BRIDGE_CONFIG_DIR.mkdir(parents=True, exist_ok=True)


# ============================================
# Enums
# ============================================

class CommandRisk(str, Enum):
    """Risk level of a command"""
    SAFE = "safe"              # Read-only, no side effects
    LOW = "low"                # Minor changes, easily reversible
    MEDIUM = "medium"          # Significant changes, reversible with effort
    HIGH = "high"              # Destructive, hard to reverse
    CRITICAL = "critical"      # System-wide, potentially catastrophic


class CommandCategory(str, Enum):
    """Category of command"""
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    FILE_DELETE = "file_delete"
    PROCESS = "process"
    NETWORK = "network"
    SYSTEM = "system"
    PACKAGE = "package"
    GIT = "git"
    DOCKER = "docker"
    DATABASE = "database"
    OTHER = "other"


# ============================================
# Data Models
# ============================================

@dataclass
class CommandAnalysis:
    """Analysis of a command"""
    command: str
    risk: CommandRisk = CommandRisk.SAFE
    category: CommandCategory = CommandCategory.OTHER
    description: str = ""
    effects: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    requires_confirmation: bool = False
    sandbox_available: bool = False
    suggested_alternatives: List[str] = field(default_factory=list)
    affected_paths: List[str] = field(default_factory=list)


@dataclass
class CommandSuggestion:
    """A suggested command"""
    command: str
    description: str
    confidence: float = 0.0
    source: str = "ai"  # ai, history, alias


@dataclass
class ErrorExplanation:
    """Explanation of an error"""
    error_type: str
    error_message: str
    explanation: str
    cause: str
    solutions: List[Dict[str, str]] = field(default_factory=list)  # {description, command}
    docs_url: Optional[str] = None


@dataclass
class HistoryEntry:
    """A command history entry"""
    id: int = 0
    command: str = ""
    intent: str = ""  # Natural language description
    output: str = ""
    exit_code: int = 0
    working_dir: str = ""
    timestamp: float = 0
    duration: float = 0
    tags: List[str] = field(default_factory=list)
    embedding: Optional[List[float]] = None  # For semantic search


@dataclass
class BridgeConfig:
    """Bridge configuration"""
    confirm_high_risk: bool = True
    confirm_critical: bool = True
    show_command_preview: bool = True
    enable_sandbox: bool = True
    max_history: int = 10000
    ai_model: str = "purma"
    remote_ai: Optional[str] = None
    remote_api_key: Optional[str] = None


# ============================================
# Dangerous Patterns
# ============================================

DANGEROUS_PATTERNS = {
    # Critical - System destruction
    CommandRisk.CRITICAL: [
        r"rm\s+(-rf?|--recursive)\s+(/|/\*|~|\$HOME)",
        r"rm\s+-rf?\s+/",
        r"dd\s+.*of=/dev/[sh]d[a-z]",
        r"mkfs\.",
        r":(){ :|:& };:",  # Fork bomb
        r">\s*/dev/[sh]d[a-z]",
        r"chmod\s+-R\s+777\s+/",
        r"chown\s+-R\s+.*\s+/",
    ],
    # High - Destructive operations
    CommandRisk.HIGH: [
        r"rm\s+(-rf?|--recursive)",
        r"rm\s+-r",
        r"git\s+push\s+.*--force",
        r"git\s+reset\s+--hard",
        r"docker\s+system\s+prune\s+-a",
        r"docker\s+rm\s+-f",
        r"drop\s+database",
        r"drop\s+table",
        r"truncate\s+table",
        r"shutdown",
        r"reboot",
        r"init\s+[0-6]",
        r"systemctl\s+(stop|disable|mask)\s+",
        r"kill\s+-9",
        r"pkill\s+-9",
        r">\s+[^|]",  # Overwrite file
    ],
    # Medium - Significant changes
    CommandRisk.MEDIUM: [
        r"mv\s+",
        r"cp\s+-r",
        r"chmod\s+",
        r"chown\s+",
        r"git\s+checkout\s+--",
        r"git\s+stash\s+drop",
        r"docker\s+stop",
        r"npm\s+uninstall",
        r"pip\s+uninstall",
        r"apt\s+remove",
        r"apt\s+purge",
    ],
    # Low - Minor changes
    CommandRisk.LOW: [
        r"git\s+add",
        r"git\s+commit",
        r"git\s+push(?!\s+.*--force)",
        r"npm\s+install",
        r"pip\s+install",
        r"mkdir",
        r"touch",
        r"echo\s+.*>>",  # Append
    ],
}

# Read-only commands (safe)
SAFE_COMMANDS = [
    "ls", "ll", "la", "dir", "cat", "less", "more", "head", "tail",
    "grep", "find", "locate", "which", "whereis", "type", "file",
    "pwd", "cd", "echo", "printf", "date", "cal", "uptime",
    "whoami", "id", "groups", "hostname", "uname",
    "ps", "top", "htop", "free", "df", "du",
    "ip", "ifconfig", "netstat", "ss", "ping", "traceroute", "dig", "nslookup",
    "git status", "git log", "git diff", "git show", "git branch",
    "docker ps", "docker images", "docker logs",
    "man", "help", "info", "--help", "-h", "--version", "-v",
]


# ============================================
# Bridge Engine
# ============================================

class BridgeEngine:
    """Main Bridge engine for AI-augmented terminal"""

    def __init__(self):
        self.config = self._load_config()
        self._init_database()

    def _load_config(self) -> BridgeConfig:
        """Load configuration"""
        if BRIDGE_CONFIG_FILE.exists():
            try:
                with open(BRIDGE_CONFIG_FILE) as f:
                    data = json.load(f)
                    return BridgeConfig(**data)
            except Exception:
                pass
        return BridgeConfig()

    def _save_config(self):
        """Save configuration"""
        with open(BRIDGE_CONFIG_FILE, 'w') as f:
            json.dump(asdict(self.config), f, indent=2)

    def _init_database(self):
        """Initialize SQLite database for history"""
        conn = sqlite3.connect(str(BRIDGE_HISTORY_DB))
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                command TEXT NOT NULL,
                intent TEXT,
                output TEXT,
                exit_code INTEGER,
                working_dir TEXT,
                timestamp REAL,
                duration REAL,
                tags TEXT,
                command_hash TEXT
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp ON history(timestamp DESC)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_intent ON history(intent)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_hash ON history(command_hash)
        """)

        conn.commit()
        conn.close()

    # ============================================
    # Command Analysis
    # ============================================

    def analyze_command(self, command: str) -> CommandAnalysis:
        """Analyze a command for risk and effects"""
        command = command.strip()
        analysis = CommandAnalysis(command=command)

        # Check for empty or comment
        if not command or command.startswith("#"):
            analysis.risk = CommandRisk.SAFE
            analysis.description = "Empty or comment"
            return analysis

        # Get base command
        parts = shlex.split(command) if command else []
        base_cmd = parts[0] if parts else ""

        # Check if it's a safe read-only command
        if any(command.startswith(safe) for safe in SAFE_COMMANDS):
            analysis.risk = CommandRisk.SAFE
            analysis.category = self._categorize_command(base_cmd)
            analysis.description = f"Read-only {analysis.category} command"
            return analysis

        # Check dangerous patterns
        for risk_level, patterns in DANGEROUS_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, command, re.IGNORECASE):
                    analysis.risk = risk_level
                    analysis.requires_confirmation = risk_level in [
                        CommandRisk.HIGH, CommandRisk.CRITICAL
                    ]
                    break
            if analysis.risk != CommandRisk.SAFE:
                break

        # Categorize
        analysis.category = self._categorize_command(base_cmd)

        # Analyze effects
        analysis.effects = self._analyze_effects(command, parts)
        analysis.warnings = self._generate_warnings(command, analysis.risk)
        analysis.affected_paths = self._extract_paths(parts)

        # Check if sandbox is available
        analysis.sandbox_available = self._can_sandbox(command)

        # Generate description
        analysis.description = self._describe_command(command, analysis)

        return analysis

    def _categorize_command(self, base_cmd: str) -> CommandCategory:
        """Categorize a command"""
        categories = {
            CommandCategory.FILE_READ: ["cat", "less", "more", "head", "tail", "grep", "find", "ls", "tree"],
            CommandCategory.FILE_WRITE: ["touch", "mkdir", "cp", "mv", "echo", "tee", "nano", "vim"],
            CommandCategory.FILE_DELETE: ["rm", "rmdir", "unlink"],
            CommandCategory.PROCESS: ["ps", "top", "htop", "kill", "pkill", "bg", "fg", "jobs"],
            CommandCategory.NETWORK: ["ping", "curl", "wget", "ssh", "scp", "netstat", "ss", "ip"],
            CommandCategory.SYSTEM: ["systemctl", "service", "shutdown", "reboot", "mount", "umount"],
            CommandCategory.PACKAGE: ["apt", "apt-get", "dpkg", "snap", "npm", "pip", "cargo", "yay"],
            CommandCategory.GIT: ["git"],
            CommandCategory.DOCKER: ["docker", "docker-compose", "podman"],
            CommandCategory.DATABASE: ["mysql", "psql", "mongo", "redis-cli", "sqlite3"],
        }

        for category, commands in categories.items():
            if base_cmd in commands:
                return category

        return CommandCategory.OTHER

    def _analyze_effects(self, command: str, parts: List[str]) -> List[str]:
        """Analyze what a command will do"""
        effects = []

        if not parts:
            return effects

        base = parts[0]

        if base == "rm":
            if "-r" in parts or "-rf" in parts or "--recursive" in parts:
                effects.append("Eliminara directorios recursivamente")
            if "-f" in parts or "--force" in parts:
                effects.append("No pedira confirmacion")
            paths = [p for p in parts[1:] if not p.startswith("-")]
            if paths:
                effects.append(f"Afectara: {', '.join(paths)}")

        elif base == "mv":
            if len(parts) >= 3:
                effects.append(f"Movera {parts[-2]} a {parts[-1]}")

        elif base == "cp":
            if "-r" in parts:
                effects.append("Copiara directorios recursivamente")

        elif base == "chmod":
            effects.append("Cambiara permisos de archivos")

        elif base == "chown":
            effects.append("Cambiara propietario de archivos")

        elif base in ["git", "docker"]:
            subcommand = parts[1] if len(parts) > 1 else ""
            if base == "git":
                if subcommand == "push" and "--force" in parts:
                    effects.append("Forzara push, puede perder commits remotos")
                elif subcommand == "reset" and "--hard" in parts:
                    effects.append("Perdera cambios no commiteados")
            elif base == "docker":
                if subcommand == "rm" and "-f" in parts:
                    effects.append("Forzara eliminacion de contenedores")

        return effects

    def _generate_warnings(self, command: str, risk: CommandRisk) -> List[str]:
        """Generate warnings for a command"""
        warnings = []

        if risk == CommandRisk.CRITICAL:
            warnings.append("⛔ PELIGRO: Este comando puede destruir tu sistema")
        elif risk == CommandRisk.HIGH:
            warnings.append("⚠️ ADVERTENCIA: Este comando puede causar perdida de datos")
        elif risk == CommandRisk.MEDIUM:
            warnings.append("📝 NOTA: Este comando realizara cambios significativos")

        # Specific warnings
        if "sudo" in command:
            warnings.append("🔐 Requiere privilegios de administrador")

        if re.search(r"rm.*\*", command):
            warnings.append("🎯 Usas wildcard (*) - verifica que afecte solo lo deseado")

        if "|" in command and ("rm" in command or ">" in command):
            warnings.append("⚡ Comando con pipe - verifica el flujo completo")

        return warnings

    def _extract_paths(self, parts: List[str]) -> List[str]:
        """Extract file paths from command parts"""
        paths = []
        for part in parts:
            if part.startswith("-"):
                continue
            if "/" in part or part.startswith("~") or part.startswith("."):
                expanded = os.path.expanduser(part)
                paths.append(expanded)
        return paths

    def _can_sandbox(self, command: str) -> bool:
        """Check if command can be run in sandbox mode"""
        # Commands that support dry-run or similar
        sandboxable = [
            ("rm", "-i"),          # Interactive mode
            ("cp", "-i"),
            ("mv", "-i"),
            ("rsync", "--dry-run"),
            ("apt", "--dry-run"),
            ("pip", "--dry-run"),
            ("npm", "--dry-run"),
            ("git", "--dry-run"),
        ]

        parts = shlex.split(command) if command else []
        if not parts:
            return False

        for cmd, flag in sandboxable:
            if parts[0] == cmd:
                return True

        return False

    def _describe_command(self, command: str, analysis: CommandAnalysis) -> str:
        """Generate human-readable description"""
        parts = shlex.split(command) if command else []
        if not parts:
            return "Comando vacio"

        base = parts[0]
        descriptions = {
            "ls": "Listar archivos",
            "cd": "Cambiar directorio",
            "cat": "Mostrar contenido de archivo",
            "rm": "Eliminar archivos",
            "cp": "Copiar archivos",
            "mv": "Mover/renombrar archivos",
            "mkdir": "Crear directorio",
            "touch": "Crear archivo vacio",
            "chmod": "Cambiar permisos",
            "chown": "Cambiar propietario",
            "grep": "Buscar texto en archivos",
            "find": "Buscar archivos",
            "git": "Control de versiones Git",
            "docker": "Gestion de contenedores",
            "npm": "Gestor de paquetes Node.js",
            "pip": "Gestor de paquetes Python",
        }

        return descriptions.get(base, f"Ejecutar {base}")

    # ============================================
    # Natural Language Translation
    # ============================================

    async def translate_to_command(self, natural_language: str,
                                    context: Dict = None) -> List[CommandSuggestion]:
        """Translate natural language to shell command"""

        prompt = f"""Translate this natural language request to a Linux shell command.

Request: "{natural_language}"

Context:
- Current directory: {context.get('cwd', os.getcwd()) if context else os.getcwd()}
- Shell: {context.get('shell', 'bash') if context else 'bash'}

Rules:
1. Return ONLY the command, no explanations
2. Use common, portable commands when possible
3. Prefer safe options (e.g., -i for interactive)
4. If multiple commands needed, chain with && or ;

Respond in JSON format:
{{
    "commands": [
        {{"command": "the command", "description": "what it does", "confidence": 0.9}}
    ]
}}"""

        result = await self._call_ai(prompt)

        suggestions = []
        for cmd_data in result.get("commands", []):
            suggestions.append(CommandSuggestion(
                command=cmd_data.get("command", ""),
                description=cmd_data.get("description", ""),
                confidence=cmd_data.get("confidence", 0.5),
                source="ai"
            ))

        # Also check history for similar intents
        history_matches = self.search_history_semantic(natural_language, limit=3)
        for entry in history_matches:
            suggestions.append(CommandSuggestion(
                command=entry.command,
                description=entry.intent or "From history",
                confidence=0.7,
                source="history"
            ))

        return suggestions

    # ============================================
    # Error Explanation
    # ============================================

    async def explain_error(self, command: str, error_output: str,
                            exit_code: int) -> ErrorExplanation:
        """Explain an error and suggest solutions"""

        prompt = f"""Analyze this shell command error and provide solutions.

Command: {command}
Exit code: {exit_code}
Error output:
{error_output[:1500]}

Provide:
1. Type of error
2. Clear explanation of what went wrong
3. Likely cause
4. 2-4 specific solutions with commands

Respond in JSON format:
{{
    "error_type": "type of error",
    "explanation": "clear explanation",
    "cause": "likely cause",
    "solutions": [
        {{"description": "what to do", "command": "command to run"}}
    ],
    "docs_url": "optional documentation URL"
}}"""

        result = await self._call_ai(prompt)

        return ErrorExplanation(
            error_type=result.get("error_type", "Unknown error"),
            error_message=error_output[:500],
            explanation=result.get("explanation", "Error occurred"),
            cause=result.get("cause", "Unknown cause"),
            solutions=result.get("solutions", []),
            docs_url=result.get("docs_url")
        )

    # ============================================
    # Command Suggestions
    # ============================================

    async def get_suggestions(self, partial_input: str,
                               context: Dict = None) -> List[CommandSuggestion]:
        """Get command suggestions based on partial input"""
        suggestions = []

        # If it looks like natural language (contains spaces, no special chars at start)
        if " " in partial_input and not partial_input.startswith(("./", "/", "$")):
            # Might be natural language
            nl_suggestions = await self.translate_to_command(partial_input, context)
            suggestions.extend(nl_suggestions)

        # Get history-based suggestions
        history_matches = self.search_history(partial_input, limit=5)
        for entry in history_matches:
            if entry.command not in [s.command for s in suggestions]:
                suggestions.append(CommandSuggestion(
                    command=entry.command,
                    description=entry.intent or f"Used {self._time_ago(entry.timestamp)}",
                    confidence=0.6,
                    source="history"
                ))

        return suggestions[:10]

    def _time_ago(self, timestamp: float) -> str:
        """Human-readable time ago"""
        diff = time.time() - timestamp
        if diff < 60:
            return "just now"
        elif diff < 3600:
            return f"{int(diff/60)}m ago"
        elif diff < 86400:
            return f"{int(diff/3600)}h ago"
        else:
            return f"{int(diff/86400)}d ago"

    # ============================================
    # Sandbox Mode
    # ============================================

    async def sandbox_preview(self, command: str) -> Dict:
        """Preview what a command would do without executing"""

        analysis = self.analyze_command(command)

        preview = {
            "command": command,
            "analysis": asdict(analysis),
            "would_affect": [],
            "simulated_output": None,
        }

        parts = shlex.split(command) if command else []
        if not parts:
            return preview

        base = parts[0]

        # Simulate effects for common commands
        if base == "rm":
            paths = [p for p in parts[1:] if not p.startswith("-")]
            for path in paths:
                expanded = os.path.expanduser(path)
                if "*" in expanded:
                    # Glob pattern
                    import glob
                    matches = glob.glob(expanded)
                    preview["would_affect"].extend(matches)
                elif os.path.exists(expanded):
                    if os.path.isdir(expanded) and ("-r" in parts or "-rf" in parts):
                        # Count files in directory
                        count = sum(1 for _ in Path(expanded).rglob("*"))
                        preview["would_affect"].append(f"{expanded} ({count} files)")
                    else:
                        preview["would_affect"].append(expanded)

        elif base == "find":
            # Actually run find to show what would be found
            try:
                result = subprocess.run(
                    parts, capture_output=True, text=True, timeout=5
                )
                preview["simulated_output"] = result.stdout[:2000]
                preview["would_affect"] = result.stdout.strip().split("\n")[:20]
            except Exception:
                pass

        elif base == "grep":
            # Show what would match
            try:
                result = subprocess.run(
                    parts, capture_output=True, text=True, timeout=5
                )
                preview["simulated_output"] = result.stdout[:2000]
            except Exception:
                pass

        return preview

    # ============================================
    # History Management
    # ============================================

    def add_to_history(self, command: str, output: str = "", exit_code: int = 0,
                       working_dir: str = "", duration: float = 0,
                       intent: str = "") -> int:
        """Add command to history"""
        conn = sqlite3.connect(str(BRIDGE_HISTORY_DB))
        cursor = conn.cursor()

        command_hash = hashlib.md5(command.encode()).hexdigest()

        cursor.execute("""
            INSERT INTO history (command, intent, output, exit_code, working_dir,
                                timestamp, duration, tags, command_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            command,
            intent,
            output[:5000],  # Limit output size
            exit_code,
            working_dir or os.getcwd(),
            time.time(),
            duration,
            "",
            command_hash
        ))

        entry_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return entry_id

    def search_history(self, query: str, limit: int = 10) -> List[HistoryEntry]:
        """Search history by command text"""
        conn = sqlite3.connect(str(BRIDGE_HISTORY_DB))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, command, intent, output, exit_code, working_dir,
                   timestamp, duration, tags
            FROM history
            WHERE command LIKE ? OR intent LIKE ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (f"%{query}%", f"%{query}%", limit))

        entries = []
        for row in cursor.fetchall():
            entries.append(HistoryEntry(
                id=row[0],
                command=row[1],
                intent=row[2] or "",
                output=row[3] or "",
                exit_code=row[4],
                working_dir=row[5] or "",
                timestamp=row[6],
                duration=row[7],
                tags=row[8].split(",") if row[8] else []
            ))

        conn.close()
        return entries

    def search_history_semantic(self, query: str, limit: int = 5) -> List[HistoryEntry]:
        """Search history by semantic meaning (uses AI)"""
        # For now, do keyword-based search
        # In production, would use embeddings
        return self.search_history(query, limit)

    def get_recent_history(self, limit: int = 50) -> List[HistoryEntry]:
        """Get recent history entries"""
        conn = sqlite3.connect(str(BRIDGE_HISTORY_DB))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, command, intent, output, exit_code, working_dir,
                   timestamp, duration, tags
            FROM history
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))

        entries = []
        for row in cursor.fetchall():
            entries.append(HistoryEntry(
                id=row[0],
                command=row[1],
                intent=row[2] or "",
                output=row[3] or "",
                exit_code=row[4],
                working_dir=row[5] or "",
                timestamp=row[6],
                duration=row[7],
                tags=row[8].split(",") if row[8] else []
            ))

        conn.close()
        return entries

    # ============================================
    # AI Integration
    # ============================================

    async def _call_ai(self, prompt: str) -> Dict:
        """Call AI model"""
        import httpx

        # Try local Ollama first
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": self.config.ai_model,
                        "prompt": prompt,
                        "stream": False,
                        "format": "json",
                    }
                )

                if response.status_code == 200:
                    result = response.json()
                    try:
                        return json.loads(result.get("response", "{}"))
                    except json.JSONDecodeError:
                        return {}

        except Exception as e:
            print(f"Ollama error: {e}")

        # Try remote if configured
        if self.config.remote_ai and self.config.remote_api_key:
            return await self._call_remote_ai(prompt)

        return {}

    async def _call_remote_ai(self, prompt: str) -> Dict:
        """Call remote AI provider"""
        import httpx

        if self.config.remote_ai == "anthropic":
            url = "https://api.anthropic.com/v1/messages"
            headers = {
                "x-api-key": self.config.remote_api_key,
                "content-type": "application/json",
                "anthropic-version": "2023-06-01"
            }
            data = {
                "model": "claude-3-haiku-20240307",
                "max_tokens": 1000,
                "messages": [{"role": "user", "content": prompt}]
            }
        elif self.config.remote_ai == "openai":
            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.config.remote_api_key}",
                "Content-Type": "application/json"
            }
            data = {
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "response_format": {"type": "json_object"}
            }
        else:
            return {}

        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.post(url, headers=headers, json=data)
                if response.status_code == 200:
                    result = response.json()
                    if self.config.remote_ai == "anthropic":
                        text = result["content"][0]["text"]
                    else:
                        text = result["choices"][0]["message"]["content"]
                    return json.loads(text)
        except Exception:
            pass

        return {}


# ============================================
# Global Instance
# ============================================

bridge_engine = BridgeEngine()


# ============================================
# Convenience Functions
# ============================================

def analyze(command: str) -> CommandAnalysis:
    """Analyze a command"""
    return bridge_engine.analyze_command(command)


async def translate(text: str) -> List[CommandSuggestion]:
    """Translate natural language to command"""
    return await bridge_engine.translate_to_command(text)


async def explain(command: str, error: str, exit_code: int) -> ErrorExplanation:
    """Explain an error"""
    return await bridge_engine.explain_error(command, error, exit_code)


def history_add(command: str, **kwargs) -> int:
    """Add to history"""
    return bridge_engine.add_to_history(command, **kwargs)


def history_search(query: str) -> List[HistoryEntry]:
    """Search history"""
    return bridge_engine.search_history(query)
