#!/usr/bin/env python3
"""
PurmaLinux - AI Assistant Server v3.0
=====================================
Author: Matías Aguirre
Company: Matware

Servidor completo de asistente de IA con:
- Sistema de agentes personalizables con modelos AI locales (Ollama)
- Comandos rápidos (/organize, /search, /cleanup, etc.)
- Gestión de archivos y sistema
"""

import os
import sys
import json
import asyncio
import subprocess
import re
import mimetypes
import shutil
import yaml
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from collections import defaultdict

import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx

# ============================================
# Configuration
# ============================================

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
DEFAULT_MODEL = os.getenv("PURMA_MODEL", "purma")
SERVER_HOST = os.getenv("PURMA_SERVER_HOST", "127.0.0.1")
SERVER_PORT = int(os.getenv("PURMA_SERVER_PORT", "11435"))

HOME = Path.home()
WORK_DIR = HOME / "AI"
CONFIG_DIR = HOME / ".config" / "purma"
AGENTS_DIR = CONFIG_DIR / "agents"
COMMANDS_DIR = CONFIG_DIR / "commands"
MAX_OUTPUT_LENGTH = 15000

# File categories for organization
FILE_CATEGORIES = {
    "images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp", ".ico", ".tiff", ".raw"],
    "documents": [".pdf", ".doc", ".docx", ".odt", ".txt", ".rtf", ".xls", ".xlsx", ".ppt", ".pptx", ".csv"],
    "code": [".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".scss", ".json", ".yaml", ".yml",
             ".sh", ".bash", ".go", ".rs", ".c", ".cpp", ".h", ".java", ".rb", ".php", ".sql", ".md"],
    "videos": [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v"],
    "audio": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a"],
    "archives": [".zip", ".tar", ".gz", ".rar", ".7z", ".bz2", ".xz"],
    "data": [".db", ".sqlite", ".json", ".xml", ".csv", ".parquet"],
}

# Create directories
WORK_DIR.mkdir(exist_ok=True)
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
AGENTS_DIR.mkdir(exist_ok=True)
COMMANDS_DIR.mkdir(exist_ok=True)

# ============================================
# FastAPI App
# ============================================

app = FastAPI(
    title="Purma AI Assistant",
    description="Asistente completo de IA para PurmaLinux con agentes y comandos",
    version="3.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# Models
# ============================================

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Message]] = []
    model: Optional[str] = None
    context_path: Optional[str] = None
    agent: Optional[str] = None  # Agent to use

class ChatResponse(BaseModel):
    response: str
    actions: List[Dict[str, Any]] = []
    model: str
    agent: Optional[str] = None
    timestamp: str

class AgentConfig(BaseModel):
    name: str
    description: str
    icon: str = "󰚩"
    mode: str = "primary"  # primary, subagent
    model: Optional[str] = None
    prompt: str
    tools: Dict[str, bool] = {}
    temperature: float = 0.7
    max_steps: int = 10

class CommandConfig(BaseModel):
    name: str
    description: str
    icon: str = ""
    prompt: str
    args: List[Dict[str, Any]] = []
    agent: Optional[str] = None

# ============================================
# Security
# ============================================

def is_path_safe(path: str) -> bool:
    """Check if path is within user's home directory"""
    try:
        resolved = Path(path).expanduser().resolve()
        return str(resolved).startswith(str(HOME))
    except:
        return False

def sanitize_command(command: str) -> Tuple[bool, str]:
    """Check if command is safe to execute"""
    blocked = [
        r'\bsudo\b', r'\bsu\b', r'\brm\s+-rf\s+/', r'\bdd\b.*of=',
        r'\bmkfs\b', r'\bfdisk\b', r'>\s*/etc/', r'>\s*/usr/',
        r'\bsystemctl\b', r'\breboot\b', r'\bshutdown\b',
        r':(){ :|:& };:', r'\bcurl\b.*\|\s*(ba)?sh',
    ]
    for pattern in blocked:
        if re.search(pattern, command, re.IGNORECASE):
            return False, "Comando bloqueado por seguridad"
    return True, "OK"

# ============================================
# Agents System
# ============================================

# Built-in agents
BUILTIN_AGENTS = {
    "purma": {
        "name": "purma",
        "description": "Asistente general de PurmaLinux con acceso completo",
        "icon": "󰚩",
        "mode": "primary",
        "model": None,
        "temperature": 0.7,
        "max_steps": 10,
        "tools": {"*": True},
        "prompt": """Eres Purma, el asistente de IA integrado en PurmaLinux.

## Tu Rol
Eres el asistente personal del usuario. Puedes ayudarle con CUALQUIER tarea relacionada con sus archivos y su sistema.

## Capacidades
- Gestión de archivos (listar, buscar, organizar, mover, copiar, eliminar)
- Lectura y escritura de archivos
- Ejecución de comandos
- Información del sistema

## Categorías de Archivos
- images: fotos, imágenes
- documents: PDFs, documentos
- code: archivos de programación
- videos, audio, archives, data

## Formato de Acciones
Para ejecutar una herramienta:
```tool:nombre
{"param": "valor"}
```

## Reglas
- Opera dentro de ~/ del usuario
- No uses sudo ni comandos destructivos
- Para eliminar, pide confirmación
- Responde en español
"""
    },
    "organizer": {
        "name": "organizer",
        "description": "Especialista en organización de archivos",
        "icon": "",
        "mode": "subagent",
        "model": None,
        "temperature": 0.3,
        "max_steps": 5,
        "tools": {"list": True, "search": True, "organize": True, "move": True, "mkdir": True},
        "prompt": """Eres un agente especializado en ORGANIZAR archivos.

## Tu Única Misión
Organizar archivos de manera eficiente y lógica.

## Estrategias de Organización
1. **Por categoría**: images/, documents/, code/, videos/, audio/, archives/
2. **Por fecha**: 2024/01-Enero/, 2024/02-Febrero/
3. **Por extensión**: pdf/, jpg/, py/
4. **Por proyecto**: crear carpetas temáticas

## Flujo de Trabajo
1. Primero usa `list` para ver qué hay
2. Analiza los archivos y propón un plan
3. SIEMPRE muestra preview con dry_run=true primero
4. Solo ejecuta si el usuario confirma

## Formato
```tool:organize
{"path": "~/Downloads", "by": "category", "dry_run": true}
```

## Reglas
- NUNCA organices sin mostrar preview primero
- Pregunta si hay dudas sobre la estructura
- Mantén nombres de archivo originales
"""
    },
    "searcher": {
        "name": "searcher",
        "description": "Especialista en búsqueda de archivos",
        "icon": "",
        "mode": "subagent",
        "model": None,
        "temperature": 0.3,
        "max_steps": 5,
        "tools": {"list": True, "search": True, "info": True, "read": True},
        "prompt": """Eres un agente especializado en BUSCAR archivos.

## Tu Única Misión
Encontrar archivos de manera rápida y precisa.

## Estrategias de Búsqueda
1. **Por nombre**: buscar texto en nombres de archivo
2. **Por contenido**: buscar dentro de archivos de texto
3. **Por categoría**: filtrar por tipo (images, documents, code...)
4. **Por fecha**: archivos recientes o de un período

## Herramientas
```tool:search
{"query": "texto", "path": "~", "category": "images", "search_content": false}
```

```tool:list
{"path": "~/Downloads", "category": "documents", "recursive": true}
```

## Consejos
- Empieza con búsquedas amplias y refina
- Usa categorías para filtrar resultados
- Para buscar "foto del perro" → query="perro", category="images"
- Muestra resultados de forma clara y organizada
"""
    },
    "coder": {
        "name": "coder",
        "description": "Asistente de programación",
        "icon": "",
        "mode": "subagent",
        "model": None,
        "temperature": 0.5,
        "max_steps": 10,
        "tools": {"read": True, "write": True, "execute": True, "search": True, "list": True},
        "prompt": """Eres un agente especializado en PROGRAMACIÓN.

## Tu Misión
Ayudar con tareas de desarrollo: crear scripts, editar código, ejecutar programas.

## Capacidades
- Leer y analizar código existente
- Crear nuevos scripts y programas
- Ejecutar comandos de desarrollo
- Buscar en código fuente

## Lenguajes Principales
Python, JavaScript, Bash, y cualquier otro que el usuario necesite.

## Flujo de Trabajo
1. Entiende qué quiere el usuario
2. Si hay código existente, léelo primero
3. Escribe código limpio y comentado
4. Ofrece ejecutar para probar

## Formato para Crear Archivos
```tool:write
{"path": "~/AI/script.py", "content": "#!/usr/bin/env python3\\n..."}
```

## Reglas
- Código limpio y legible
- Añade comentarios explicativos
- Maneja errores apropiadamente
- Pregunta antes de sobrescribir archivos existentes
"""
    },
    "cleaner": {
        "name": "cleaner",
        "description": "Limpieza y mantenimiento del sistema",
        "icon": "",
        "mode": "subagent",
        "model": None,
        "temperature": 0.2,
        "max_steps": 8,
        "tools": {"list": True, "search": True, "delete": True, "info": True, "system": True},
        "prompt": """Eres un agente especializado en LIMPIEZA del sistema.

## Tu Misión
Ayudar a liberar espacio y mantener el sistema ordenado.

## Áreas de Limpieza
1. **Archivos temporales**: ~/.cache, /tmp (dentro de home)
2. **Duplicados**: encontrar archivos duplicados
3. **Archivos grandes**: identificar qué ocupa más espacio
4. **Descargas antiguas**: archivos viejos en Downloads

## Flujo de Trabajo
1. Analiza el espacio con `system`
2. Lista archivos candidatos a eliminar
3. Muestra qué se va a borrar y cuánto espacio se libera
4. SIEMPRE pide confirmación antes de eliminar

## Formato
```tool:delete
{"path": "archivo", "confirm": false}
```

## REGLAS CRÍTICAS
- NUNCA elimines sin confirmación explícita
- Muestra tamaño de cada archivo
- Advierte sobre archivos importantes
- No toques configuraciones del sistema
"""
    }
}

# Runtime agents storage
loaded_agents: Dict[str, Dict] = {}

def load_agent_from_file(file_path: Path) -> Optional[Dict]:
    """Load agent from markdown or yaml file"""
    try:
        content = file_path.read_text()

        # Parse frontmatter (YAML between ---)
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter = yaml.safe_load(parts[1])
                prompt = parts[2].strip()

                return {
                    "name": file_path.stem,
                    "description": frontmatter.get("description", "Custom agent"),
                    "icon": frontmatter.get("icon", ""),
                    "mode": frontmatter.get("mode", "subagent"),
                    "model": frontmatter.get("model"),
                    "temperature": frontmatter.get("temperature", 0.7),
                    "max_steps": frontmatter.get("max_steps", 10),
                    "tools": frontmatter.get("tools", {"*": True}),
                    "prompt": prompt
                }

        # JSON file
        if file_path.suffix == ".json":
            return json.loads(content)

    except Exception as e:
        print(f"Error loading agent {file_path}: {e}")
    return None

def load_all_agents():
    """Load all agents (builtin + custom)"""
    global loaded_agents
    loaded_agents = BUILTIN_AGENTS.copy()

    # Load custom agents from config directory
    for file_path in AGENTS_DIR.glob("*.md"):
        agent = load_agent_from_file(file_path)
        if agent:
            loaded_agents[agent["name"]] = agent

    for file_path in AGENTS_DIR.glob("*.json"):
        agent = load_agent_from_file(file_path)
        if agent:
            loaded_agents[agent["name"]] = agent

def get_agent(name: str) -> Optional[Dict]:
    """Get agent by name"""
    if not loaded_agents:
        load_all_agents()
    return loaded_agents.get(name)

def get_all_agents() -> List[Dict]:
    """Get all available agents"""
    if not loaded_agents:
        load_all_agents()
    return list(loaded_agents.values())

# ============================================
# Quick Commands System
# ============================================

BUILTIN_COMMANDS = {
    "organize": {
        "name": "organize",
        "description": "Organiza archivos en un directorio",
        "icon": "",
        "args": [
            {"name": "path", "description": "Directorio a organizar", "default": "~/Downloads"},
            {"name": "by", "description": "Criterio: category, date, extension", "default": "category"}
        ],
        "agent": "organizer",
        "prompt": "Organiza los archivos en {path} por {by}. Primero muestra una preview de lo que vas a hacer."
    },
    "search": {
        "name": "search",
        "description": "Busca archivos",
        "icon": "",
        "args": [
            {"name": "query", "description": "Qué buscar", "required": True},
            {"name": "path", "description": "Dónde buscar", "default": "~"},
            {"name": "type", "description": "Tipo: images, documents, code, all", "default": "all"}
        ],
        "agent": "searcher",
        "prompt": "Busca archivos que contengan '{query}' en {path}. Tipo: {type}."
    },
    "cleanup": {
        "name": "cleanup",
        "description": "Analiza y limpia archivos innecesarios",
        "icon": "",
        "args": [
            {"name": "path", "description": "Directorio a analizar", "default": "~"}
        ],
        "agent": "cleaner",
        "prompt": "Analiza {path} y sugiere archivos que se pueden eliminar para liberar espacio. NO elimines nada sin mi confirmación."
    },
    "recent": {
        "name": "recent",
        "description": "Muestra archivos recientes",
        "icon": "",
        "args": [
            {"name": "count", "description": "Cantidad de archivos", "default": "10"},
            {"name": "type", "description": "Tipo de archivo", "default": "all"}
        ],
        "agent": "purma",
        "prompt": "Lista los últimos {count} archivos modificados. Tipo: {type}."
    },
    "script": {
        "name": "script",
        "description": "Crea un script",
        "icon": "",
        "args": [
            {"name": "description", "description": "Qué debe hacer el script", "required": True},
            {"name": "lang", "description": "Lenguaje: python, bash, js", "default": "python"}
        ],
        "agent": "coder",
        "prompt": "Crea un script en {lang} que haga lo siguiente: {description}"
    },
    "disk": {
        "name": "disk",
        "description": "Información del disco",
        "icon": "",
        "args": [],
        "agent": "purma",
        "prompt": "Muéstrame información detallada del uso de disco y memoria del sistema."
    },
    "help": {
        "name": "help",
        "description": "Muestra ayuda de comandos",
        "icon": "",
        "args": [],
        "agent": None,
        "prompt": None
    },
    # ===== Spaces Commands =====
    "space": {
        "name": "space",
        "description": "Activa un espacio de trabajo",
        "icon": "",
        "args": [
            {"name": "name", "description": "Nombre del espacio", "required": True}
        ],
        "agent": None,
        "prompt": "__SPACE_ACTIVATE__:{name}"
    },
    "spaces": {
        "name": "spaces",
        "description": "Lista todos los espacios de trabajo",
        "icon": "",
        "args": [],
        "agent": None,
        "prompt": "__SPACES_LIST__"
    },
    "space-new": {
        "name": "space-new",
        "description": "Crea un nuevo espacio de trabajo",
        "icon": "",
        "args": [
            {"name": "name", "description": "Nombre del espacio", "required": True},
            {"name": "template", "description": "Template: work, code, design, gaming, focus, media", "default": ""}
        ],
        "agent": None,
        "prompt": "__SPACE_CREATE__:{name}:{template}"
    },
    "work": {
        "name": "work",
        "description": "Activa el modo trabajo",
        "icon": "",
        "args": [],
        "agent": None,
        "prompt": "__SPACE_ACTIVATE__:work"
    },
    "code": {
        "name": "code",
        "description": "Activa el modo programación",
        "icon": "",
        "args": [],
        "agent": None,
        "prompt": "__SPACE_ACTIVATE__:coding"
    },
    "focus": {
        "name": "focus",
        "description": "Activa el modo concentración",
        "icon": "",
        "args": [],
        "agent": None,
        "prompt": "__SPACE_ACTIVATE__:focus"
    },
    "gaming": {
        "name": "gaming",
        "description": "Activa el modo gaming",
        "icon": "",
        "args": [],
        "agent": None,
        "prompt": "__SPACE_ACTIVATE__:gaming"
    },
    # ===== Flow Commands =====
    "flow": {
        "name": "flow",
        "description": "Ejecuta un flow de automatizacion",
        "icon": "⚡",
        "args": [
            {"name": "name", "description": "Nombre del flow", "required": True}
        ],
        "agent": None,
        "prompt": "__FLOW_RUN__:{name}"
    },
    "flows": {
        "name": "flows",
        "description": "Lista todos los flows",
        "icon": "⚡",
        "args": [],
        "agent": None,
        "prompt": "__FLOWS_LIST__"
    },
    "record": {
        "name": "record",
        "description": "Inicia/detiene grabacion de acciones",
        "icon": "",
        "args": [
            {"name": "name", "description": "Nombre de la grabacion", "default": ""}
        ],
        "agent": None,
        "prompt": "__FLOW_RECORD_TOGGLE__:{name}"
    },
    "automate": {
        "name": "automate",
        "description": "Crea un flow con IA a partir de una descripcion",
        "icon": "",
        "args": [
            {"name": "description", "description": "Que quieres automatizar", "required": True}
        ],
        "agent": None,
        "prompt": "__FLOW_CREATE_AI__:{description}"
    },
    # ===== Bridge Commands =====
    "run": {
        "name": "run",
        "description": "Traduce lenguaje natural a comando y lo ejecuta",
        "icon": "⚡",
        "args": [
            {"name": "query", "description": "Que quieres hacer", "required": True}
        ],
        "agent": None,
        "prompt": "__BRIDGE_RUN__:{query}"
    },
    "explain": {
        "name": "explain",
        "description": "Explica un error de terminal",
        "icon": "",
        "args": [
            {"name": "error", "description": "El mensaje de error", "required": True}
        ],
        "agent": None,
        "prompt": "__BRIDGE_EXPLAIN__:{error}"
    },
    "cmd": {
        "name": "cmd",
        "description": "Genera un comando sin ejecutarlo",
        "icon": "",
        "args": [
            {"name": "query", "description": "Que comando necesitas", "required": True}
        ],
        "agent": None,
        "prompt": "__BRIDGE_TRANSLATE__:{query}"
    },
    # ===== Pulse Commands =====
    "pulse": {
        "name": "pulse",
        "description": "Muestra el estado del sistema",
        "icon": "",
        "args": [],
        "agent": None,
        "prompt": "__PULSE_STATUS__"
    },
    "health": {
        "name": "health",
        "description": "Muestra la salud del sistema",
        "icon": "",
        "args": [],
        "agent": None,
        "prompt": "__PULSE_HEALTH__"
    },
    "metrics": {
        "name": "metrics",
        "description": "Muestra metricas detalladas",
        "icon": "",
        "args": [],
        "agent": None,
        "prompt": "__PULSE_METRICS__"
    },
    "insights": {
        "name": "insights",
        "description": "Obtiene insights de IA sobre el sistema",
        "icon": "",
        "args": [],
        "agent": None,
        "prompt": "__PULSE_INSIGHTS__"
    },
    "cleanup": {
        "name": "cleanup",
        "description": "Limpia espacio en disco",
        "icon": "",
        "args": [],
        "agent": None,
        "prompt": "__PULSE_CLEANUP__"
    },
    # ===== Lens Commands =====
    "lens": {
        "name": "lens",
        "description": "Captura y analiza la pantalla",
        "icon": "",
        "args": [],
        "agent": None,
        "prompt": "__LENS_CAPTURE__"
    },
    "screenshot": {
        "name": "screenshot",
        "description": "Captura pantalla completa",
        "icon": "",
        "args": [],
        "agent": None,
        "prompt": "__LENS_FULLSCREEN__"
    },
    "ocr": {
        "name": "ocr",
        "description": "Extrae texto de la pantalla",
        "icon": "",
        "args": [],
        "agent": None,
        "prompt": "__LENS_OCR__"
    },
    "see": {
        "name": "see",
        "description": "Pregunta sobre lo que ves en pantalla",
        "icon": "",
        "args": [
            {"name": "question", "description": "Pregunta sobre la pantalla", "required": True}
        ],
        "agent": None,
        "prompt": "__LENS_ASK__:{question}"
    },
    # ===== Vault Commands =====
    "vault": {
        "name": "vault",
        "description": "Accede al gestor de contraseñas",
        "icon": "",
        "args": [],
        "agent": None,
        "prompt": "__VAULT_STATUS__"
    },
    "password": {
        "name": "password",
        "description": "Busca una contraseña",
        "icon": "",
        "args": [
            {"name": "query", "description": "Servicio o nombre", "required": True}
        ],
        "agent": None,
        "prompt": "__VAULT_QUERY__:{query}"
    },
    "generate": {
        "name": "generate",
        "description": "Genera una contraseña segura",
        "icon": "",
        "args": [
            {"name": "length", "description": "Longitud", "default": "20"}
        ],
        "agent": None,
        "prompt": "__VAULT_GENERATE__:{length}"
    },
    "addpass": {
        "name": "addpass",
        "description": "Agrega una nueva contraseña",
        "icon": "",
        "args": [
            {"name": "name", "description": "Nombre del servicio", "required": True}
        ],
        "agent": None,
        "prompt": "__VAULT_ADD__:{name}"
    },
    # ===== Scribe Commands =====
    "scribe": {
        "name": "scribe",
        "description": "Inicia la grabación de voz",
        "icon": "",
        "args": [],
        "agent": None,
        "prompt": "__SCRIBE_STATUS__"
    },
    "record": {
        "name": "record",
        "description": "Graba y transcribe audio",
        "icon": "󰑊",
        "args": [
            {"name": "seconds", "description": "Segundos a grabar", "default": "5"}
        ],
        "agent": None,
        "prompt": "__SCRIBE_RECORD__:{seconds}"
    },
    "transcribe": {
        "name": "transcribe",
        "description": "Transcribe un archivo de audio",
        "icon": "",
        "args": [
            {"name": "file", "description": "Archivo de audio", "required": True}
        ],
        "agent": None,
        "prompt": "__SCRIBE_TRANSCRIBE__:{file}"
    },
    "speak": {
        "name": "speak",
        "description": "Convierte texto a voz",
        "icon": "",
        "args": [
            {"name": "text", "description": "Texto a hablar", "required": True}
        ],
        "agent": None,
        "prompt": "__SCRIBE_SPEAK__:{text}"
    },
    "dictate": {
        "name": "dictate",
        "description": "Modo dictado continuo",
        "icon": "",
        "args": [],
        "agent": None,
        "prompt": "__SCRIBE_DICTATE__"
    },
    # ===== Cortex Commands (Predictive AI) =====
    "cortex": {
        "name": "cortex",
        "description": "Estado de Purma Cortex (AI predictivo)",
        "icon": "🧠",
        "args": [],
        "agent": None,
        "prompt": "__CORTEX_STATUS__"
    },
    "predict": {
        "name": "predict",
        "description": "Predice tu próxima acción",
        "icon": "🔮",
        "args": [],
        "agent": None,
        "prompt": "__CORTEX_PREDICT__"
    },
    "schedule": {
        "name": "schedule",
        "description": "Muestra tu horario predicho",
        "icon": "📅",
        "args": [],
        "agent": None,
        "prompt": "__CORTEX_SCHEDULE__"
    },
    "patterns": {
        "name": "patterns",
        "description": "Muestra patrones aprendidos",
        "icon": "📊",
        "args": [],
        "agent": None,
        "prompt": "__CORTEX_PATTERNS__"
    },
    "learn": {
        "name": "learn",
        "description": "Activa/desactiva el aprendizaje",
        "icon": "📚",
        "args": [
            {"name": "state", "description": "on/off", "default": "on"}
        ],
        "agent": None,
        "prompt": "__CORTEX_LEARN__:{state}"
    },
    # ===== Memory Commands (RAG) =====
    "memory": {
        "name": "memory",
        "description": "Estado de Purma Memory (búsqueda semántica)",
        "icon": "🧠",
        "args": [],
        "agent": None,
        "prompt": "__MEMORY_STATUS__"
    },
    "remember": {
        "name": "remember",
        "description": "Busca en tu memoria (archivos indexados)",
        "icon": "💭",
        "args": [
            {"name": "query", "description": "Qué buscar", "required": True}
        ],
        "agent": None,
        "prompt": "__MEMORY_SEARCH__:{query}"
    },
    "ask-memory": {
        "name": "ask-memory",
        "description": "Pregunta sobre tus archivos (RAG)",
        "icon": "❓",
        "args": [
            {"name": "question", "description": "Tu pregunta", "required": True}
        ],
        "agent": None,
        "prompt": "__MEMORY_ASK__:{question}"
    },
    "index": {
        "name": "index",
        "description": "Indexa archivos para búsqueda",
        "icon": "📑",
        "args": [
            {"name": "path", "description": "Directorio a indexar", "default": "~"}
        ],
        "agent": None,
        "prompt": "__MEMORY_INDEX__:{path}"
    },
    # ===== Ghost Commands (Shadow AI) =====
    "ghost": {
        "name": "ghost",
        "description": "Estado de Purma Ghost (observador AI)",
        "icon": "👻",
        "args": [],
        "agent": None,
        "prompt": "__GHOST_STATUS__"
    },
    "observe": {
        "name": "observe",
        "description": "Activa/desactiva el observador Ghost",
        "icon": "👁️",
        "args": [
            {"name": "state", "description": "on/off", "default": "on"}
        ],
        "agent": None,
        "prompt": "__GHOST_OBSERVE__:{state}"
    },
    "suggestions": {
        "name": "suggestions",
        "description": "Ver sugerencias de automatización",
        "icon": "💡",
        "args": [],
        "agent": None,
        "prompt": "__GHOST_SUGGESTIONS__"
    },
    "insights": {
        "name": "insights",
        "description": "Ver insights de Ghost",
        "icon": "🔍",
        "args": [],
        "agent": None,
        "prompt": "__GHOST_INSIGHTS__"
    },
    # ===== Multi-Agent Commands =====
    "agents": {
        "name": "agents",
        "description": "Lista de agentes AI disponibles",
        "icon": "🤖",
        "args": [],
        "agent": None,
        "prompt": "__AGENTS_LIST__"
    },
    "task": {
        "name": "task",
        "description": "Ejecuta una tarea con múltiples agentes",
        "icon": "⚙️",
        "args": [
            {"name": "description", "description": "Descripción de la tarea", "required": True}
        ],
        "agent": None,
        "prompt": "__AGENTS_TASK__:{description}"
    },
    "ask-agent": {
        "name": "ask-agent",
        "description": "Pregunta a un agente específico",
        "icon": "🎯",
        "args": [
            {"name": "agent", "description": "Nombre del agente: researcher, analyzer, executor, coder, reviewer", "required": True},
            {"name": "question", "description": "Tu pregunta", "required": True}
        ],
        "agent": None,
        "prompt": "__AGENTS_ASK__:{agent}:{question}"
    },
    # ===== Integration Commands =====
    "status": {
        "name": "status",
        "description": "Estado completo del sistema Purma",
        "icon": "📊",
        "args": [],
        "agent": None,
        "prompt": "__INTEGRATION_STATUS__"
    },
    "context": {
        "name": "context",
        "description": "Ver contexto actual del sistema",
        "icon": "🧠",
        "args": [],
        "agent": None,
        "prompt": "__INTEGRATION_CONTEXT__"
    },
    "workflow": {
        "name": "workflow",
        "description": "Ejecutar un workflow integrado",
        "icon": "🔄",
        "args": [
            {"name": "name", "description": "Nombre: morning_routine, focus_mode, research_task, code_review, voice_command", "required": True},
            {"name": "params", "description": "Parámetros JSON opcionales", "default": "{}"}
        ],
        "agent": None,
        "prompt": "__INTEGRATION_WORKFLOW__:{name}:{params}"
    },
    "smart": {
        "name": "smart",
        "description": "Consulta inteligente - el sistema elige el módulo correcto",
        "icon": "✨",
        "args": [
            {"name": "query", "description": "Tu consulta en lenguaje natural", "required": True}
        ],
        "agent": None,
        "prompt": "__INTEGRATION_SMART__:{query}"
    },
    "events": {
        "name": "events",
        "description": "Ver eventos recientes del sistema",
        "icon": "📜",
        "args": [
            {"name": "limit", "description": "Cantidad de eventos", "default": "20"}
        ],
        "agent": None,
        "prompt": "__INTEGRATION_EVENTS__:{limit}"
    },
    "modules": {
        "name": "modules",
        "description": "Ver módulos registrados en el sistema",
        "icon": "🧩",
        "args": [],
        "agent": None,
        "prompt": "__INTEGRATION_MODULES__"
    },
    "morning": {
        "name": "morning",
        "description": "Ejecutar rutina matutina (predicciones, notas, estado)",
        "icon": "🌅",
        "args": [],
        "agent": None,
        "prompt": "__INTEGRATION_WORKFLOW__:morning_routine:{}"
    },
    "research": {
        "name": "research",
        "description": "Iniciar investigación sobre un tema",
        "icon": "🔬",
        "args": [
            {"name": "topic", "description": "Tema a investigar", "required": True}
        ],
        "agent": None,
        "prompt": "__INTEGRATION_WORKFLOW__:research_task:{\"topic\":\"{topic}\"}"
    },
    "review": {
        "name": "review",
        "description": "Hacer code review de un archivo",
        "icon": "👀",
        "args": [
            {"name": "file", "description": "Archivo a revisar", "required": True}
        ],
        "agent": None,
        "prompt": "__INTEGRATION_WORKFLOW__:code_review:{\"file\":\"{file}\"}"
    }
}

loaded_commands: Dict[str, Dict] = {}

def load_command_from_file(file_path: Path) -> Optional[Dict]:
    """Load command from file"""
    try:
        content = file_path.read_text()

        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter = yaml.safe_load(parts[1])
                prompt = parts[2].strip()

                return {
                    "name": file_path.stem,
                    "description": frontmatter.get("description", "Custom command"),
                    "icon": frontmatter.get("icon", ""),
                    "args": frontmatter.get("args", []),
                    "agent": frontmatter.get("agent"),
                    "prompt": prompt
                }

        if file_path.suffix == ".json":
            return json.loads(content)

    except Exception as e:
        print(f"Error loading command {file_path}: {e}")
    return None

def load_all_commands():
    """Load all commands"""
    global loaded_commands
    loaded_commands = BUILTIN_COMMANDS.copy()

    for file_path in COMMANDS_DIR.glob("*.md"):
        cmd = load_command_from_file(file_path)
        if cmd:
            loaded_commands[cmd["name"]] = cmd

    for file_path in COMMANDS_DIR.glob("*.json"):
        cmd = load_command_from_file(file_path)
        if cmd:
            loaded_commands[cmd["name"]] = cmd

def get_command(name: str) -> Optional[Dict]:
    """Get command by name"""
    if not loaded_commands:
        load_all_commands()
    return loaded_commands.get(name)

def get_all_commands() -> List[Dict]:
    """Get all commands"""
    if not loaded_commands:
        load_all_commands()
    return list(loaded_commands.values())

def parse_command_input(text: str) -> Tuple[Optional[str], Dict[str, str]]:
    """Parse /command arg1 arg2 or /command key=value"""
    if not text.startswith("/"):
        return None, {}

    parts = text[1:].split(maxsplit=1)
    cmd_name = parts[0].lower()
    args_str = parts[1] if len(parts) > 1 else ""

    # Parse arguments
    args = {}
    if args_str:
        # Try key=value format
        kv_pattern = r'(\w+)=(?:"([^"]*)"|(\S+))'
        matches = re.findall(kv_pattern, args_str)
        if matches:
            for key, quoted, unquoted in matches:
                args[key] = quoted or unquoted
        else:
            # Positional argument
            args["_positional"] = args_str

    return cmd_name, args

def execute_command(cmd_name: str, args: Dict[str, str]) -> Tuple[str, Optional[str]]:
    """Execute a command and return (prompt, agent_name)"""
    cmd = get_command(cmd_name)
    if not cmd:
        return f"Comando /{cmd_name} no encontrado. Usa /help para ver comandos disponibles.", None

    # Special case: help
    if cmd_name == "help":
        commands = get_all_commands()
        help_text = "## Comandos Disponibles\n\n"
        for c in commands:
            args_str = " ".join([f"[{a['name']}]" for a in c.get("args", [])])
            help_text += f"**/{c['name']}** {args_str}\n  {c['description']}\n\n"
        return help_text, None

    # Build prompt from template
    prompt = cmd["prompt"]

    # Fill in arguments with defaults
    for arg_def in cmd.get("args", []):
        arg_name = arg_def["name"]
        value = args.get(arg_name) or args.get("_positional") or arg_def.get("default", "")
        prompt = prompt.replace(f"{{{arg_name}}}", str(value))

    return prompt, cmd.get("agent")

# ============================================
# File Tools
# ============================================

async def list_files(
    path: str = "~",
    recursive: bool = False,
    pattern: str = None,
    category: str = None,
    max_depth: int = 3
) -> Dict[str, Any]:
    """List files with optional filtering"""
    expanded = Path(path).expanduser().resolve()

    if not is_path_safe(str(expanded)):
        return {"success": False, "error": f"Acceso denegado: {path}"}

    if not expanded.exists():
        return {"success": False, "error": f"Ruta no existe: {path}"}

    try:
        items = []

        def should_include(file_path: Path) -> bool:
            if pattern and not re.search(pattern, file_path.name, re.IGNORECASE):
                return False
            if category and category in FILE_CATEGORIES:
                return file_path.suffix.lower() in FILE_CATEGORIES[category]
            return True

        def scan_dir(dir_path: Path, depth: int = 0):
            if depth > max_depth:
                return
            try:
                for item in dir_path.iterdir():
                    if item.name.startswith('.'):
                        continue

                    stat = item.stat()

                    if item.is_file() and should_include(item):
                        items.append({
                            "name": item.name,
                            "path": str(item),
                            "type": "file",
                            "size": stat.st_size,
                            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            "category": get_file_category(item),
                            "extension": item.suffix.lower(),
                        })
                    elif item.is_dir():
                        if not recursive:
                            items.append({
                                "name": item.name,
                                "path": str(item),
                                "type": "dir",
                                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            })
                        else:
                            scan_dir(item, depth + 1)
            except PermissionError:
                pass

        if expanded.is_file():
            stat = expanded.stat()
            items.append({
                "name": expanded.name,
                "path": str(expanded),
                "type": "file",
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "category": get_file_category(expanded),
            })
        else:
            scan_dir(expanded)

        items.sort(key=lambda x: x.get("modified", ""), reverse=True)

        return {
            "success": True,
            "path": str(expanded),
            "count": len(items),
            "items": items[:500]
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_file_category(file_path: Path) -> str:
    """Get category of a file based on extension"""
    ext = file_path.suffix.lower()
    for category, extensions in FILE_CATEGORIES.items():
        if ext in extensions:
            return category
    return "other"


async def search_files(
    query: str,
    path: str = "~",
    search_content: bool = False,
    category: str = None,
    max_results: int = 50
) -> Dict[str, Any]:
    """Search for files by name or content"""
    expanded = Path(path).expanduser().resolve()

    if not is_path_safe(str(expanded)):
        return {"success": False, "error": f"Acceso denegado: {path}"}

    results = []
    query_lower = query.lower()

    try:
        for root, dirs, files in os.walk(expanded):
            dirs[:] = [d for d in dirs if not d.startswith('.')]

            depth = str(root).count(os.sep) - str(expanded).count(os.sep)
            if depth > 5:
                continue

            for file in files:
                if len(results) >= max_results:
                    break

                file_path = Path(root) / file

                if file.startswith('.'):
                    continue

                if category and category != "all" and get_file_category(file_path) != category:
                    continue

                name_match = query_lower in file.lower()
                content_match = False
                content_preview = None

                if search_content and not name_match:
                    if get_file_category(file_path) in ["code", "documents"]:
                        try:
                            content = file_path.read_text(errors='ignore')[:50000]
                            if query_lower in content.lower():
                                content_match = True
                                idx = content.lower().find(query_lower)
                                start = max(0, idx - 50)
                                end = min(len(content), idx + len(query) + 50)
                                content_preview = "..." + content[start:end] + "..."
                        except:
                            pass

                if name_match or content_match:
                    stat = file_path.stat()
                    results.append({
                        "name": file,
                        "path": str(file_path),
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "category": get_file_category(file_path),
                        "match_type": "name" if name_match else "content",
                        "preview": content_preview,
                    })

        return {
            "success": True,
            "query": query,
            "count": len(results),
            "results": results
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def organize_files(
    path: str,
    by: str = "category",
    dry_run: bool = True
) -> Dict[str, Any]:
    """Organize files into folders by category, date, or extension"""
    expanded = Path(path).expanduser().resolve()

    if not is_path_safe(str(expanded)):
        return {"success": False, "error": f"Acceso denegado: {path}"}

    if not expanded.is_dir():
        return {"success": False, "error": "La ruta debe ser un directorio"}

    operations = []

    try:
        for item in expanded.iterdir():
            if item.is_file() and not item.name.startswith('.'):
                if by == "category":
                    category = get_file_category(item)
                    dest_dir = expanded / category.capitalize()
                elif by == "date":
                    mtime = datetime.fromtimestamp(item.stat().st_mtime)
                    dest_dir = expanded / mtime.strftime("%Y") / mtime.strftime("%m-%B")
                elif by == "extension":
                    ext = item.suffix.lower()[1:] if item.suffix else "sin_extension"
                    dest_dir = expanded / ext
                else:
                    continue

                dest_path = dest_dir / item.name

                operations.append({
                    "action": "move",
                    "source": str(item),
                    "destination": str(dest_path),
                    "category": get_file_category(item) if by == "category" else None
                })

        if not dry_run:
            moved = 0
            for op in operations:
                try:
                    dest = Path(op["destination"])
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(op["source"], dest)
                    moved += 1
                except Exception as e:
                    op["error"] = str(e)

            return {
                "success": True,
                "organized": moved,
                "total": len(operations),
                "operations": operations
            }

        grouped = defaultdict(list)
        for op in operations:
            dest_dir = str(Path(op["destination"]).parent)
            grouped[dest_dir].append(Path(op["source"]).name)

        return {
            "success": True,
            "dry_run": True,
            "total_files": len(operations),
            "preview": {k: v for k, v in grouped.items()},
            "message": "Vista previa. Usa dry_run=false para ejecutar."
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def move_file(source: str, destination: str) -> Dict[str, Any]:
    """Move or rename a file"""
    src = Path(source).expanduser().resolve()
    dst = Path(destination).expanduser().resolve()

    if not is_path_safe(str(src)) or not is_path_safe(str(dst)):
        return {"success": False, "error": "Acceso denegado"}

    if not src.exists():
        return {"success": False, "error": f"Archivo no existe: {source}"}

    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        return {"success": True, "message": f"Movido: {src.name} → {dst}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def copy_file(source: str, destination: str) -> Dict[str, Any]:
    """Copy a file or directory"""
    src = Path(source).expanduser().resolve()
    dst = Path(destination).expanduser().resolve()

    if not is_path_safe(str(src)) or not is_path_safe(str(dst)):
        return {"success": False, "error": "Acceso denegado"}

    if not src.exists():
        return {"success": False, "error": f"No existe: {source}"}

    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(str(src), str(dst))
        else:
            shutil.copy2(str(src), str(dst))
        return {"success": True, "message": f"Copiado: {src.name} → {dst}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def delete_file(path: str, confirm: bool = False) -> Dict[str, Any]:
    """Delete a file (requires confirmation)"""
    if not confirm:
        return {
            "success": False,
            "requires_confirmation": True,
            "message": f"¿Confirmar eliminación de {path}?"
        }

    file_path = Path(path).expanduser().resolve()

    if not is_path_safe(str(file_path)):
        return {"success": False, "error": "Acceso denegado"}

    try:
        if file_path.is_dir():
            shutil.rmtree(file_path)
        else:
            file_path.unlink()
        return {"success": True, "message": f"Eliminado: {path}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def read_file(path: str, lines: int = None) -> Dict[str, Any]:
    """Read file content"""
    file_path = Path(path).expanduser().resolve()

    if not is_path_safe(str(file_path)):
        return {"success": False, "error": "Acceso denegado"}

    if not file_path.exists():
        return {"success": False, "error": f"No existe: {path}"}

    try:
        content = file_path.read_text(errors='ignore')
        if lines:
            content = '\n'.join(content.split('\n')[:lines])
        if len(content) > MAX_OUTPUT_LENGTH:
            content = content[:MAX_OUTPUT_LENGTH] + "\n... (truncado)"

        return {
            "success": True,
            "path": str(file_path),
            "content": content,
            "size": file_path.stat().st_size
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def write_file(path: str, content: str, append: bool = False) -> Dict[str, Any]:
    """Write content to file"""
    file_path = Path(path).expanduser().resolve()

    if not is_path_safe(str(file_path)):
        return {"success": False, "error": "Acceso denegado"}

    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        mode = 'a' if append else 'w'
        with open(file_path, mode) as f:
            f.write(content)
        return {"success": True, "message": f"Escrito: {path}", "size": len(content)}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def create_directory(path: str) -> Dict[str, Any]:
    """Create a directory"""
    dir_path = Path(path).expanduser().resolve()

    if not is_path_safe(str(dir_path)):
        return {"success": False, "error": "Acceso denegado"}

    try:
        dir_path.mkdir(parents=True, exist_ok=True)
        return {"success": True, "message": f"Directorio creado: {path}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def get_file_info(path: str) -> Dict[str, Any]:
    """Get detailed file information"""
    file_path = Path(path).expanduser().resolve()

    if not is_path_safe(str(file_path)):
        return {"success": False, "error": "Acceso denegado"}

    if not file_path.exists():
        return {"success": False, "error": f"No existe: {path}"}

    try:
        stat = file_path.stat()
        mime_type, _ = mimetypes.guess_type(str(file_path))

        info = {
            "success": True,
            "name": file_path.name,
            "path": str(file_path),
            "type": "directory" if file_path.is_dir() else "file",
            "size": stat.st_size,
            "size_human": format_size(stat.st_size),
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "accessed": datetime.fromtimestamp(stat.st_atime).isoformat(),
            "mime_type": mime_type,
            "category": get_file_category(file_path),
            "extension": file_path.suffix,
            "permissions": oct(stat.st_mode)[-3:],
        }

        if file_path.is_dir():
            try:
                items = list(file_path.iterdir())
                info["children_count"] = len(items)
                info["files_count"] = sum(1 for i in items if i.is_file())
                info["dirs_count"] = sum(1 for i in items if i.is_dir())
            except:
                pass

        return info
    except Exception as e:
        return {"success": False, "error": str(e)}


def format_size(size: int) -> str:
    """Format file size in human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"


async def execute_command(command: str, cwd: str = None) -> Dict[str, Any]:
    """Execute a shell command safely"""
    is_safe, reason = sanitize_command(command)
    if not is_safe:
        return {"success": False, "error": reason}

    work_dir = cwd if cwd and is_path_safe(cwd) else str(WORK_DIR)

    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=work_dir,
            env={**os.environ, "HOME": str(HOME)},
        )

        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
        except asyncio.TimeoutError:
            proc.kill()
            return {"success": False, "error": "Timeout"}

        output = (stdout.decode() + stderr.decode()).strip()
        if len(output) > MAX_OUTPUT_LENGTH:
            output = output[:MAX_OUTPUT_LENGTH] + "\n... (truncado)"

        return {
            "success": proc.returncode == 0,
            "output": output,
            "return_code": proc.returncode
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def get_system_info() -> Dict[str, Any]:
    """Get system information"""
    try:
        info = {}

        total, used, free = shutil.disk_usage(HOME)
        info["disk"] = {
            "total": format_size(total),
            "used": format_size(used),
            "free": format_size(free),
            "percent": round(used / total * 100, 1)
        }

        try:
            home_size = sum(f.stat().st_size for f in HOME.rglob('*') if f.is_file())
            info["home_size"] = format_size(home_size)
        except:
            info["home_size"] = "N/A"

        try:
            with open('/proc/meminfo') as f:
                meminfo = f.read()
                total_match = re.search(r'MemTotal:\s+(\d+)', meminfo)
                free_match = re.search(r'MemAvailable:\s+(\d+)', meminfo)
                if total_match and free_match:
                    total_kb = int(total_match.group(1))
                    free_kb = int(free_match.group(1))
                    info["memory"] = {
                        "total": format_size(total_kb * 1024),
                        "free": format_size(free_kb * 1024),
                        "percent": round((total_kb - free_kb) / total_kb * 100, 1)
                    }
        except:
            pass

        try:
            with open('/proc/uptime') as f:
                uptime_seconds = float(f.read().split()[0])
                days = int(uptime_seconds // 86400)
                hours = int((uptime_seconds % 86400) // 3600)
                info["uptime"] = f"{days}d {hours}h"
        except:
            pass

        return {"success": True, **info}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================
# Tool Registry
# ============================================

TOOLS = {
    "list": list_files,
    "search": search_files,
    "organize": organize_files,
    "move": move_file,
    "copy": copy_file,
    "delete": delete_file,
    "read": read_file,
    "write": write_file,
    "mkdir": create_directory,
    "info": get_file_info,
    "execute": execute_command,
    "system": get_system_info,
}

# ============================================
# Ollama Integration with Agents
# ============================================

async def check_ollama() -> bool:
    """Check if Ollama is running"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{OLLAMA_HOST}/api/tags", timeout=5)
            return response.status_code == 200
    except:
        return False


async def get_models() -> List[str]:
    """Get available models"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{OLLAMA_HOST}/api/tags", timeout=10)
            data = response.json()
            return [m["name"] for m in data.get("models", [])]
    except:
        return []


def parse_tool_calls(response: str) -> List[Dict[str, Any]]:
    """Parse tool calls from AI response"""
    tools = []
    pattern = r'```tool:(\w+)\n({[\s\S]*?})\n```'

    for match in re.finditer(pattern, response):
        tool_name = match.group(1)
        try:
            params = json.loads(match.group(2))
            tools.append({"tool": tool_name, "params": params})
        except json.JSONDecodeError:
            pass

    return tools


def filter_tools_for_agent(agent: Dict) -> Dict[str, Any]:
    """Get tools available for an agent based on its configuration"""
    agent_tools = agent.get("tools", {"*": True})

    if agent_tools.get("*"):
        return TOOLS

    return {name: func for name, func in TOOLS.items() if agent_tools.get(name)}


async def execute_tools(tool_calls: List[Dict], agent: Dict = None) -> List[Dict[str, Any]]:
    """Execute parsed tool calls"""
    results = []
    available_tools = filter_tools_for_agent(agent) if agent else TOOLS

    for call in tool_calls:
        tool_name = call["tool"]
        params = call["params"]

        if tool_name not in available_tools:
            results.append({
                "tool": tool_name,
                "params": params,
                "success": False,
                "error": f"Tool '{tool_name}' no disponible para este agente",
                "description": f"{tool_name}: no permitido"
            })
            continue

        try:
            result = await available_tools[tool_name](**params)
            results.append({
                "tool": tool_name,
                "params": params,
                "success": result.get("success", False),
                "result": result,
                "description": f"{tool_name}: {json.dumps(params, ensure_ascii=False)[:100]}"
            })
        except Exception as e:
            results.append({
                "tool": tool_name,
                "params": params,
                "success": False,
                "error": str(e),
                "description": f"{tool_name}: error"
            })

    return results


async def chat_with_ollama(
    message: str,
    history: List[Message] = None,
    model: str = None,
    context_path: str = None,
    agent_name: str = None
) -> Tuple[str, List[Dict], str]:
    """Chat with Ollama using specified agent"""

    # Get agent configuration
    agent = get_agent(agent_name or "purma") or BUILTIN_AGENTS["purma"]
    agent_model = agent.get("model") or model or DEFAULT_MODEL

    # Build system prompt
    system_prompt = agent["prompt"]

    # Add tool documentation if agent has tools
    available_tools = filter_tools_for_agent(agent)
    if available_tools:
        tools_doc = "\n\nHerramientas disponibles:\n"
        for name in available_tools.keys():
            tools_doc += f"- {name}\n"
        system_prompt += tools_doc

    messages = [{"role": "system", "content": system_prompt}]

    if context_path:
        messages.append({
            "role": "system",
            "content": f"El usuario está actualmente en: {context_path}"
        })

    if history:
        for msg in history[-10:]:
            messages.append({"role": msg.role, "content": msg.content})

    messages.append({"role": "user", "content": message})

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{OLLAMA_HOST}/api/chat",
                json={
                    "model": agent_model,
                    "messages": messages,
                    "stream": False,
                    "options": {"temperature": agent.get("temperature", 0.7)}
                },
                timeout=120,
            )
            response.raise_for_status()
            ai_response = response.json()["message"]["content"]

        # Parse and execute tools
        tool_calls = parse_tool_calls(ai_response)
        tool_results = []

        if tool_calls:
            tool_results = await execute_tools(tool_calls, agent)

            if tool_results:
                results_text = "\n".join([
                    f"Resultado de {r['tool']}: {json.dumps(r['result'], ensure_ascii=False, indent=2)[:2000]}"
                    for r in tool_results
                ])

                messages.append({"role": "assistant", "content": ai_response})
                messages.append({
                    "role": "user",
                    "content": f"Resultados de las herramientas:\n{results_text}\n\nResume los resultados para el usuario de forma clara y amigable."
                })

                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{OLLAMA_HOST}/api/chat",
                        json={
                            "model": agent_model,
                            "messages": messages,
                            "stream": False,
                            "options": {"temperature": agent.get("temperature", 0.7)}
                        },
                        timeout=60,
                    )
                    response.raise_for_status()
                    ai_response = response.json()["message"]["content"]

        return ai_response, tool_results, agent["name"]

    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Error con Ollama: {e}")


# ============================================
# API Endpoints
# ============================================

@app.get("/")
async def root():
    return {"message": "Purma AI Assistant", "version": "3.0.0"}


@app.get("/status")
async def get_status():
    ollama_ok = await check_ollama()
    models = await get_models() if ollama_ok else []
    return {
        "status": "running",
        "ollama_connected": ollama_ok,
        "models": models,
        "default_model": DEFAULT_MODEL,
        "tools": list(TOOLS.keys()),
        "agents": [a["name"] for a in get_all_agents()],
        "commands": [c["name"] for c in get_all_commands()]
    }


@app.get("/models")
async def list_models():
    models = await get_models()
    return {"models": models, "default": DEFAULT_MODEL}


# ============================================
# Agent Endpoints
# ============================================

@app.get("/agents")
async def list_agents():
    """List all available agents"""
    agents = get_all_agents()
    return {
        "agents": [
            {
                "name": a["name"],
                "description": a["description"],
                "icon": a["icon"],
                "mode": a["mode"],
                "tools": list(filter_tools_for_agent(a).keys())
            }
            for a in agents
        ]
    }


@app.get("/agents/{name}")
async def get_agent_info(name: str):
    """Get agent details"""
    agent = get_agent(name)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{name}' not found")
    return {
        "name": agent["name"],
        "description": agent["description"],
        "icon": agent["icon"],
        "mode": agent["mode"],
        "model": agent.get("model"),
        "temperature": agent.get("temperature", 0.7),
        "tools": list(filter_tools_for_agent(agent).keys())
    }


@app.post("/agents")
async def create_agent(config: AgentConfig):
    """Create a new custom agent"""
    agent_file = AGENTS_DIR / f"{config.name}.md"

    if agent_file.exists():
        raise HTTPException(status_code=400, detail=f"Agent '{config.name}' already exists")

    # Create markdown file with frontmatter
    content = f"""---
description: {config.description}
icon: {config.icon}
mode: {config.mode}
temperature: {config.temperature}
max_steps: {config.max_steps}
tools:
"""
    for tool, enabled in config.tools.items():
        content += f"  {tool}: {str(enabled).lower()}\n"

    content += f"""---
{config.prompt}
"""

    agent_file.write_text(content)
    load_all_agents()  # Reload agents

    return {"success": True, "message": f"Agent '{config.name}' created", "path": str(agent_file)}


@app.delete("/agents/{name}")
async def delete_agent(name: str):
    """Delete a custom agent"""
    if name in BUILTIN_AGENTS:
        raise HTTPException(status_code=400, detail="Cannot delete built-in agents")

    agent_file = AGENTS_DIR / f"{name}.md"
    if not agent_file.exists():
        agent_file = AGENTS_DIR / f"{name}.json"

    if not agent_file.exists():
        raise HTTPException(status_code=404, detail=f"Agent '{name}' not found")

    agent_file.unlink()
    load_all_agents()

    return {"success": True, "message": f"Agent '{name}' deleted"}


# ============================================
# Commands Endpoints
# ============================================

@app.get("/commands")
async def list_commands():
    """List all available commands"""
    commands = get_all_commands()
    return {
        "commands": [
            {
                "name": c["name"],
                "description": c["description"],
                "icon": c["icon"],
                "args": c.get("args", []),
                "agent": c.get("agent")
            }
            for c in commands
        ]
    }


@app.get("/commands/{name}")
async def get_command_info(name: str):
    """Get command details"""
    cmd = get_command(name)
    if not cmd:
        raise HTTPException(status_code=404, detail=f"Command '/{name}' not found")
    return cmd


@app.post("/commands")
async def create_command(config: CommandConfig):
    """Create a new custom command"""
    cmd_file = COMMANDS_DIR / f"{config.name}.md"

    if cmd_file.exists():
        raise HTTPException(status_code=400, detail=f"Command '/{config.name}' already exists")

    content = f"""---
description: {config.description}
icon: {config.icon}
agent: {config.agent or 'purma'}
args:
"""
    for arg in config.args:
        content += f"  - name: {arg.get('name', 'arg')}\n"
        content += f"    description: {arg.get('description', '')}\n"
        if 'default' in arg:
            content += f"    default: {arg['default']}\n"
        if arg.get('required'):
            content += f"    required: true\n"

    content += f"""---
{config.prompt}
"""

    cmd_file.write_text(content)
    load_all_commands()

    return {"success": True, "message": f"Command '/{config.name}' created", "path": str(cmd_file)}


# ============================================
# Chat Endpoint (with commands and agents)
# ============================================

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Chat with Purma AI Assistant"""
    message = request.message.strip()
    agent_name = request.agent

    # Check if message is a command
    if message.startswith("/"):
        cmd_name, args = parse_command_input(message)
        prompt, cmd_agent = execute_command(cmd_name, args)

        # If help command, return directly
        if cmd_name == "help":
            return ChatResponse(
                response=prompt,
                actions=[],
                model="system",
                agent=None,
                timestamp=datetime.now().isoformat()
            )

        # Handle space commands directly
        if prompt.startswith("__SPACE_"):
            space_response = await handle_space_command(prompt)
            return ChatResponse(
                response=space_response["message"],
                actions=space_response.get("actions", []),
                model="system",
                agent=None,
                timestamp=datetime.now().isoformat()
            )

        # Handle flow commands directly
        if prompt.startswith("__FLOW_"):
            flow_response = await handle_flow_command(prompt)
            return ChatResponse(
                response=flow_response["message"],
                actions=flow_response.get("actions", []),
                model="system",
                agent=None,
                timestamp=datetime.now().isoformat()
            )

        # Handle bridge commands directly
        if prompt.startswith("__BRIDGE_"):
            bridge_response = await handle_bridge_command(prompt)
            return ChatResponse(
                response=bridge_response["message"],
                actions=bridge_response.get("actions", []),
                model="system",
                agent=None,
                timestamp=datetime.now().isoformat()
            )

        # Handle pulse commands directly
        if prompt.startswith("__PULSE_"):
            pulse_response = await handle_pulse_command(prompt)
            return ChatResponse(
                response=pulse_response["message"],
                actions=pulse_response.get("actions", []),
                model="system",
                agent=None,
                timestamp=datetime.now().isoformat()
            )

        # Handle lens commands directly
        if prompt.startswith("__LENS_"):
            lens_response = await handle_lens_command(prompt)
            return ChatResponse(
                response=lens_response["message"],
                actions=lens_response.get("actions", []),
                model="system",
                agent=None,
                timestamp=datetime.now().isoformat()
            )

        # Handle vault commands directly
        if prompt.startswith("__VAULT_"):
            vault_response = await handle_vault_command(prompt)
            return ChatResponse(
                response=vault_response["message"],
                actions=vault_response.get("actions", []),
                model="system",
                agent=None,
                timestamp=datetime.now().isoformat()
            )

        # Handle scribe commands directly
        if prompt.startswith("__SCRIBE_"):
            scribe_response = await handle_scribe_command(prompt)
            return ChatResponse(
                response=scribe_response["message"],
                actions=scribe_response.get("actions", []),
                model="system",
                agent=None,
                timestamp=datetime.now().isoformat()
            )

        # Use command's agent if specified
        if cmd_agent:
            agent_name = cmd_agent
        message = prompt

    response_text, actions, used_agent = await chat_with_ollama(
        message,
        request.history,
        request.model,
        request.context_path,
        agent_name
    )

    return ChatResponse(
        response=response_text,
        actions=[{
            "type": a["tool"],
            "description": a["description"],
            "success": a["success"],
            "output": json.dumps(a.get("result", {}), ensure_ascii=False)[:500] if a["success"] else None,
            "error": a.get("error")
        } for a in actions],
        model=request.model or DEFAULT_MODEL,
        agent=used_agent,
        timestamp=datetime.now().isoformat()
    )


@app.post("/tool/{tool_name}")
async def run_tool(tool_name: str, params: Dict[str, Any] = {}):
    """Execute a tool directly"""
    if tool_name not in TOOLS:
        raise HTTPException(status_code=400, detail=f"Tool no existe: {tool_name}")

    result = await TOOLS[tool_name](**params)
    return result


@app.get("/tools")
async def list_tools():
    """List available tools"""
    return {
        "tools": {
            name: {
                "description": func.__doc__,
            }
            for name, func in TOOLS.items()
        }
    }


# Convenience endpoints
@app.get("/ls")
async def ls(path: str = "~", recursive: bool = False, category: str = None):
    return await list_files(path, recursive, category=category)


@app.get("/search")
async def search(q: str, path: str = "~", content: bool = False, category: str = None):
    return await search_files(q, path, content, category)


@app.post("/organize")
async def organize(path: str, by: str = "category", dry_run: bool = True):
    return await organize_files(path, by, dry_run)


@app.get("/info")
async def info(path: str):
    return await get_file_info(path)


@app.get("/system")
async def system():
    return await get_system_info()


@app.post("/reload")
async def reload_config():
    """Reload agents and commands from config files"""
    load_all_agents()
    load_all_commands()
    return {
        "success": True,
        "agents": len(loaded_agents),
        "commands": len(loaded_commands)
    }


# ============================================
# Spaces Endpoints
# ============================================

from purma_spaces import space_manager, SPACE_TEMPLATES, create_template_space


async def handle_space_command(prompt: str) -> Dict[str, Any]:
    """Handle special __SPACE_*__ command prompts"""

    if prompt.startswith("__SPACES_LIST__"):
        # List all spaces
        spaces = space_manager.list_spaces()
        active = space_manager.global_state.active_space

        if not spaces:
            return {
                "message": "📭 **No hay spaces configurados**\n\nUsa `/space-new <nombre>` para crear uno, o `/space-new <nombre> <template>` para usar una plantilla.\n\n**Plantillas disponibles:** work, code, design, gaming, focus, media",
                "actions": []
            }

        lines = ["# 🌌 Purma Spaces\n"]
        for s in spaces:
            icon = s.get("icon", "🔲")
            name = s.get("name", s["id"])
            is_active = "✨ " if s["id"] == active else ""
            desc = s.get("description", "")[:50]
            lines.append(f"{is_active}{icon} **{name}** - {desc}")

        lines.append(f"\n---\n🎯 **Activo:** {active or 'ninguno'}")
        lines.append("\n💡 Usa `/space <nombre>` para cambiar")

        return {"message": "\n".join(lines), "actions": []}

    elif prompt.startswith("__SPACE_ACTIVATE__:"):
        # Activate a space
        space_name = prompt.split(":", 1)[1]

        # Find space by name or id
        space = space_manager.get_space(space_name)
        if not space:
            # Try to find by name
            for s in space_manager.spaces.values():
                if s.name.lower() == space_name.lower():
                    space = s
                    break

        if not space:
            available = [s.name for s in space_manager.spaces.values()]
            return {
                "message": f"❌ **Space '{space_name}' no encontrado**\n\n**Spaces disponibles:** {', '.join(available) if available else 'ninguno'}\n\n💡 Usa `/space-new {space_name}` para crearlo",
                "actions": []
            }

        result = await space_manager.activate_space(space.id)

        if result["success"]:
            actions_taken = []
            if result.get("apps_opened"):
                actions_taken.append(f"▶️ Apps abiertas: {', '.join(result['apps_opened'])}")
            if result.get("apps_closed"):
                actions_taken.append(f"⏹️ Apps cerradas: {', '.join(result['apps_closed'])}")
            if result.get("wallpaper_set"):
                actions_taken.append("🖼️ Wallpaper aplicado")

            actions_str = "\n".join(actions_taken) if actions_taken else "Sin cambios de apps"

            return {
                "message": f"# {space.icon} Space: {space.name}\n\n{space.description}\n\n---\n{actions_str}\n\n✨ **Space activado correctamente**",
                "actions": [{"type": "space_activate", "description": f"Activated space: {space.name}", "success": True}]
            }
        else:
            return {
                "message": f"❌ **Error al activar space**\n\n{result.get('error', 'Error desconocido')}",
                "actions": [{"type": "space_activate", "description": f"Failed to activate: {space_name}", "success": False, "error": result.get("error")}]
            }

    elif prompt.startswith("__SPACE_CREATE__:"):
        # Create a new space
        parts = prompt.split(":", 1)[1].split(":")
        name = parts[0] if parts else "new-space"
        template = parts[1] if len(parts) > 1 and parts[1] else None

        try:
            if template and template in SPACE_TEMPLATES:
                space = create_template_space(space_manager, template)
                # Update name if provided
                if name != SPACE_TEMPLATES[template]["name"]:
                    space_manager.update_space(space.id, {"name": name})
                template_info = f"\n📋 **Plantilla:** {template}"
            else:
                space = space_manager.create_space(name)
                template_info = ""

            return {
                "message": f"# ✨ Space creado: {space.name}\n\n**ID:** `{space.id}`{template_info}\n\n---\n💡 Usa `/space {space.name}` para activarlo\n📝 Edita `~/.config/purma/spaces/{space.id}.yaml` para configurarlo",
                "actions": [{"type": "space_create", "description": f"Created space: {space.name}", "success": True}]
            }
        except ValueError as e:
            return {
                "message": f"❌ **Error al crear space**\n\n{str(e)}",
                "actions": [{"type": "space_create", "description": f"Failed to create: {name}", "success": False, "error": str(e)}]
            }

    elif prompt.startswith("__SPACE_SWITCH__:"):
        # Quick switch
        direction = prompt.split(":", 1)[1] or "next"
        result = await space_manager.quick_switch(direction)

        if result["success"]:
            new_space = space_manager.get_space(result.get("space"))
            return {
                "message": f"# ↔️ Cambio rápido\n\n{new_space.icon if new_space else '🔲'} **{result.get('space', 'unknown')}**\n\n✨ Cambiado correctamente",
                "actions": [{"type": "space_switch", "description": f"Switched to: {result.get('space')}", "success": True}]
            }
        else:
            return {
                "message": f"❌ **Error al cambiar**\n\n{result.get('error', 'Error desconocido')}",
                "actions": []
            }

    # Unknown command
    return {
        "message": "❓ Comando de space no reconocido",
        "actions": []
    }


async def handle_flow_command(prompt: str) -> Dict[str, Any]:
    """Handle special __FLOW_*__ command prompts"""

    if prompt.startswith("__FLOWS_LIST__"):
        # List all flows
        flows = flow_manager.list_flows()
        recording = flow_manager.state.active_recording
        running = flow_manager.state.running_flows

        if not flows:
            return {
                "message": "📭 **No hay flows configurados**\n\nUsa `/record` para grabar acciones o `/automate <descripcion>` para crear con IA.",
                "actions": []
            }

        lines = ["# ⚡ Purma Flows\n"]
        for f in flows:
            icon = f.get("icon", "⚡")
            name = f.get("name", f["id"])
            is_running = "🔄 " if f["id"] in running else ""
            runs = f.get("run_count", 0)
            steps = f.get("steps_count", 0)
            lines.append(f"{is_running}{icon} **{name}** - {steps} pasos ({runs}x ejecutado)")

        if recording:
            lines.append(f"\n---\n🔴 **Grabando:** {recording}")
        lines.append("\n💡 Usa `/flow <nombre>` para ejecutar")

        return {"message": "\n".join(lines), "actions": []}

    elif prompt.startswith("__FLOW_RUN__:"):
        # Run a flow
        flow_name = prompt.split(":", 1)[1]

        # Find flow by name or id
        flow = flow_manager.get_flow(flow_name)
        if not flow:
            for f in flow_manager.flows.values():
                if f.name.lower() == flow_name.lower():
                    flow = f
                    break

        if not flow:
            available = [f.name for f in flow_manager.flows.values()]
            return {
                "message": f"❌ **Flow '{flow_name}' no encontrado**\n\n**Flows disponibles:** {', '.join(available) if available else 'ninguno'}",
                "actions": []
            }

        result = await flow_manager.run_flow(flow.id)

        if result["success"]:
            steps_ok = sum(1 for r in result.get("results", []) if r.get("success"))
            return {
                "message": f"# ⚡ Flow: {flow.name}\n\n✅ **Ejecutado correctamente**\n\n- Pasos: {steps_ok}/{len(result.get('results', []))}\n- Tiempo: {result.get('duration', 0):.2f}s",
                "actions": [{"type": "flow_run", "description": f"Ran flow: {flow.name}", "success": True}]
            }
        else:
            return {
                "message": f"❌ **Error al ejecutar flow**\n\n{result.get('error', 'Error desconocido')}",
                "actions": [{"type": "flow_run", "description": f"Failed: {flow_name}", "success": False}]
            }

    elif prompt.startswith("__FLOW_RECORD_TOGGLE__:"):
        # Toggle recording
        name = prompt.split(":", 1)[1] or ""

        if flow_manager.state.active_recording:
            # Stop recording
            recording = flow_manager.stop_recording()
            if recording:
                return {
                    "message": f"# ⏹️ Grabacion terminada\n\n**{recording.name}**\n- Acciones: {len(recording.actions)}\n\n💡 Usa la API para analizar y crear un flow",
                    "actions": [{"type": "recording_stop", "description": "Stopped recording", "success": True}]
                }
        else:
            # Start recording
            try:
                recording = flow_manager.start_recording(name or "Nueva grabacion")
                return {
                    "message": f"# 🔴 Grabacion iniciada\n\n**{recording.name}**\n\nRealiza las acciones que quieres automatizar.\n\n💡 Usa `/record` de nuevo para detener",
                    "actions": [{"type": "recording_start", "description": "Started recording", "success": True}]
                }
            except ValueError as e:
                return {
                    "message": f"❌ **Error:** {str(e)}",
                    "actions": []
                }

        return {"message": "❓ Error en grabacion", "actions": []}

    elif prompt.startswith("__FLOW_CREATE_AI__:"):
        # Create flow with AI
        description = prompt.split(":", 1)[1]

        result = await flow_analyzer.generate_flow_from_description(description)

        if "error" in result:
            return {
                "message": f"❌ **Error al crear flow**\n\n{result['error']}",
                "actions": []
            }

        # Create flow from result
        steps = [
            FlowStep(
                action_type=ActionType(s.get("action_type", "command")),
                description=s.get("description", ""),
                command=s.get("command", ""),
                template=s.get("command", ""),
            )
            for s in result.get("steps", [])
        ]

        flow = flow_manager.create_flow(
            name=result.get("name", "AI Flow"),
            description=result.get("description", description),
            steps=steps,
        )
        flow.icon = result.get("icon", "🤖")
        flow.variables = result.get("variables", {})
        flow.tags = result.get("tags", ["ai-generated"])
        flow_manager._save_flow(flow)

        return {
            "message": f"# 🤖 Flow creado con IA\n\n**{flow.name}**\n{flow.description}\n\n- Pasos: {len(flow.steps)}\n- Variables: {len(flow.variables)}\n\n💡 Usa `/flow {flow.name}` para ejecutar",
            "actions": [{"type": "flow_create", "description": f"Created: {flow.name}", "success": True}]
        }

    # Unknown command
    return {
        "message": "❓ Comando de flow no reconocido",
        "actions": []
    }


async def handle_bridge_command(prompt: str) -> Dict[str, Any]:
    """Handle special __BRIDGE_*__ command prompts"""

    if prompt.startswith("__BRIDGE_TRANSLATE__:"):
        # Translate natural language to command
        query = prompt.split(":", 1)[1]

        suggestions = await bridge_engine.translate_to_command(query)

        if not suggestions:
            return {
                "message": f"❌ **No pude generar un comando**\n\nIntenta ser mas especifico.",
                "actions": []
            }

        lines = ["# ⚡ Comandos sugeridos\n"]
        for i, sug in enumerate(suggestions[:5], 1):
            conf = int(sug.confidence * 100)
            source = "🤖" if sug.source == "ai" else "📜"
            lines.append(f"**{i}.** `{sug.command}`")
            lines.append(f"   {sug.description} {source} {conf}%\n")

        lines.append("\n💡 Copia y ejecuta el comando que prefieras")

        return {
            "message": "\n".join(lines),
            "actions": [{"type": "bridge_translate", "description": f"Translated: {query}", "success": True}]
        }

    elif prompt.startswith("__BRIDGE_RUN__:"):
        # Translate and run
        query = prompt.split(":", 1)[1]

        suggestions = await bridge_engine.translate_to_command(query)

        if not suggestions:
            return {
                "message": f"❌ **No pude generar un comando**",
                "actions": []
            }

        # Get best suggestion
        best = suggestions[0]

        # Analyze for safety
        analysis = bridge_engine.analyze_command(best.command)

        if analysis.risk.value in ("high", "critical"):
            return {
                "message": f"# ⚠️ Comando de alto riesgo\n\n`{best.command}`\n\n{analysis.description}\n\n**Advertencias:**\n" + "\n".join(f"- {w}" for w in analysis.warnings) + "\n\n❌ Por seguridad, no ejecutare este comando automaticamente.\n💡 Copialo y ejecutalo manualmente si estas seguro.",
                "actions": [{"type": "bridge_blocked", "description": f"High risk: {best.command}", "success": False}]
            }

        # Execute (TODO: actually execute and show output)
        return {
            "message": f"# ⚡ Comando generado\n\n`{best.command}`\n\n{best.description}\n\n💡 Usa la terminal Purma Bridge para ejecucion automatica:\n```\npurma-bridge\n?? {query}\n```",
            "actions": [{"type": "bridge_run", "description": best.command, "success": True}]
        }

    elif prompt.startswith("__BRIDGE_EXPLAIN__:"):
        # Explain an error
        error = prompt.split(":", 1)[1]

        explanation = await bridge_engine.explain_error("", error, 1)

        lines = [f"# 🔍 Explicacion del error\n"]
        lines.append(f"**Tipo:** {explanation.error_type}")
        lines.append(f"\n{explanation.explanation}")
        lines.append(f"\n**Causa probable:** {explanation.cause}")

        if explanation.solutions:
            lines.append("\n## Soluciones:\n")
            for i, sol in enumerate(explanation.solutions, 1):
                lines.append(f"**{i}.** {sol.get('description', '')}")
                if sol.get("command"):
                    lines.append(f"   `{sol['command']}`")

        if explanation.docs_url:
            lines.append(f"\n📖 [Documentacion]({explanation.docs_url})")

        return {
            "message": "\n".join(lines),
            "actions": [{"type": "bridge_explain", "description": "Error explained", "success": True}]
        }

    # Unknown command
    return {
        "message": "❓ Comando de bridge no reconocido",
        "actions": []
    }


async def handle_pulse_command(prompt: str) -> Dict[str, Any]:
    """Handle special __PULSE_*__ command prompts"""

    if prompt == "__PULSE_STATUS__":
        # Get system status
        status = pulse_engine.get_status()
        health = status["health"]
        metrics = status["metrics"]

        # Health emoji
        health_emoji = {
            "excellent": "",
            "good": "",
            "fair": "",
            "poor": "",
            "critical": "",
        }.get(health["level"], "")

        lines = [
            f"# {health_emoji} Sistema: {health['level'].upper()}",
            f"**Puntuacion:** {health['overall']}/100",
            f"\n{health['description']}",
            "\n## Metricas actuales\n",
            f"| Recurso | Uso | Puntuacion |",
            f"|---------|-----|------------|",
            f"| CPU | {metrics['cpu']['percent']:.1f}% | {metrics['cpu']['score']}/100 |",
            f"| Memoria | {metrics['memory']['percent']:.1f}% | {metrics['memory']['score']}/100 |",
            f"| Disco | {metrics['disk']['percent']:.1f}% | {metrics['disk']['score']}/100 |",
        ]

        if metrics.get("battery"):
            bat = metrics["battery"]
            charging = "" if bat["charging"] else ""
            lines.append(f"| Bateria | {bat['percent']:.0f}% {charging} | - |")

        if status["alerts"]:
            lines.append("\n## Alertas activas\n")
            for alert in status["alerts"]:
                icon = {"warning": "", "danger": "", "critical": ""}.get(alert["severity"], "")
                lines.append(f"- {icon} **{alert['title']}**: {alert['message']}")

        return {
            "message": "\n".join(lines),
            "actions": [{"type": "pulse_status", "description": "System status", "success": True}]
        }

    elif prompt == "__PULSE_HEALTH__":
        # Get health details
        status = pulse_engine.get_status()
        health = status["health"]

        health_emoji = {
            "excellent": "",
            "good": "",
            "fair": "",
            "poor": "",
            "critical": "",
        }.get(health["level"], "")

        lines = [
            f"# {health_emoji} Salud del Sistema",
            f"\n**Nivel:** {health['level'].upper()}",
            f"**Puntuacion:** {health['overall']}/100",
            f"\n{health['description']}",
        ]

        # Get insights
        insights = await pulse_engine.get_insights()
        if insights:
            lines.append("\n## Recomendaciones\n")
            for insight in insights[:5]:
                priority_icon = "" * min(insight["priority"], 5)
                lines.append(f"### {insight['title']}")
                lines.append(f"{insight['description']}")
                if insight.get("command"):
                    lines.append(f"\n`{insight['command']}`")
                lines.append("")

        return {
            "message": "\n".join(lines),
            "actions": [{"type": "pulse_health", "description": "Health report", "success": True}]
        }

    elif prompt == "__PULSE_METRICS__":
        # Get detailed metrics
        metrics = pulse_engine.get_detailed_metrics()

        lines = [
            "# Metricas del Sistema\n",
            "## CPU",
            f"- **Uso:** {metrics['cpu']['percent']:.1f}%",
            f"- **Frecuencia:** {metrics['cpu']['frequency']:.0f} MHz",
            f"- **Nucleos:** {metrics['cpu']['cores']}",
            f"- **Carga:** {metrics['cpu']['load_1m']:.2f} / {metrics['cpu']['load_5m']:.2f} / {metrics['cpu']['load_15m']:.2f}",
        ]

        if metrics['cpu']['top_processes']:
            lines.append("\n**Top procesos CPU:**")
            for p in metrics['cpu']['top_processes'][:3]:
                lines.append(f"  - {p['name']}: {p['cpu_percent']:.1f}%")

        lines.extend([
            "\n## Memoria",
            f"- **Uso:** {metrics['memory']['percent']:.1f}%",
            f"- **Usado:** {metrics['memory']['used'] / (1024**3):.1f} GB",
            f"- **Total:** {metrics['memory']['total'] / (1024**3):.1f} GB",
            f"- **Disponible:** {metrics['memory']['available'] / (1024**3):.1f} GB",
            f"- **Swap:** {metrics['memory']['swap_percent']:.1f}%",
        ])

        if metrics['memory']['top_processes']:
            lines.append("\n**Top procesos Memoria:**")
            for p in metrics['memory']['top_processes'][:3]:
                lines.append(f"  - {p['name']}: {p['memory_percent']:.1f}%")

        lines.extend([
            "\n## Disco",
            f"- **Uso:** {metrics['disk']['percent']:.1f}%",
            f"- **Usado:** {metrics['disk']['used'] / (1024**3):.1f} GB",
            f"- **Total:** {metrics['disk']['total'] / (1024**3):.1f} GB",
            f"- **Lectura:** {metrics['disk']['read_rate'] / 1024:.1f} KB/s",
            f"- **Escritura:** {metrics['disk']['write_rate'] / 1024:.1f} KB/s",
        ])

        lines.extend([
            "\n## Red",
            f"- **Descarga:** {metrics['network']['recv_rate'] / 1024:.1f} KB/s",
            f"- **Subida:** {metrics['network']['sent_rate'] / 1024:.1f} KB/s",
            f"- **Conexiones:** {metrics['network']['connections']}",
        ])

        if metrics.get('battery'):
            bat = metrics['battery']
            lines.extend([
                "\n## Bateria",
                f"- **Nivel:** {bat['percent']:.0f}%",
                f"- **Cargando:** {'Si' if bat['charging'] else 'No'}",
            ])
            if bat.get('time_left'):
                lines.append(f"- **Tiempo restante:** {bat['time_left'] // 60} min")

        if metrics.get('temperature'):
            lines.append(f"\n## Temperatura\n- **CPU:** {metrics['temperature']:.0f}C")

        lines.append(f"\n**Procesos activos:** {metrics['process_count']}")

        return {
            "message": "\n".join(lines),
            "actions": [{"type": "pulse_metrics", "description": "Detailed metrics", "success": True}]
        }

    elif prompt == "__PULSE_INSIGHTS__":
        # Get AI insights
        insights = await pulse_engine.get_insights()

        if not insights:
            return {
                "message": " **Todo en orden!**\n\nNo hay recomendaciones en este momento.\nEl sistema esta funcionando bien.",
                "actions": []
            }

        lines = ["#  Insights del Sistema\n"]

        for insight in insights:
            priority_stars = "" * min(insight["priority"], 5)
            category_icon = {
                "performance": "",
                "memory": "",
                "storage": "",
                "battery": "",
                "network": "",
                "prediction": "",
                "health": "",
            }.get(insight["category"], "")

            lines.append(f"## {category_icon} {insight['title']}")
            lines.append(f"**Prioridad:** {priority_stars}")
            lines.append(f"\n{insight['description']}")

            if insight.get("action"):
                lines.append(f"\n**Accion:** {insight['action']}")
            if insight.get("command"):
                lines.append(f"```\n{insight['command']}\n```")

            lines.append("")

        return {
            "message": "\n".join(lines),
            "actions": [{"type": "pulse_insights", "description": "AI insights", "success": True}]
        }

    elif prompt == "__PULSE_CLEANUP__":
        # Run cleanup
        result = pulse_engine.cleanup_disk()

        if result["success"]:
            lines = [
                "#  Limpieza completada\n",
                "**Acciones realizadas:**",
            ]
            for action in result["actions"]:
                lines.append(f"- {action}")

            lines.extend([
                f"\n**Espacio en disco:**",
                f"- Usado: {result['disk_percent']:.1f}%",
                f"- Libre: {result['free_gb']:.1f} GB",
            ])

            return {
                "message": "\n".join(lines),
                "actions": [{"type": "pulse_cleanup", "description": "Cleanup complete", "success": True}]
            }
        else:
            return {
                "message": " Error al realizar la limpieza",
                "actions": []
            }

    # Unknown command
    return {
        "message": "❓ Comando de pulse no reconocido",
        "actions": []
    }


# Import for Lens handler
from purma_lens import lens_engine, CaptureMode

async def handle_lens_command(prompt: str) -> Dict[str, Any]:
    """Handle special __LENS_*__ command prompts"""

    if prompt == "__LENS_CAPTURE__" or prompt == "__LENS_FULLSCREEN__":
        # Capture and analyze full screen
        result = await lens_engine.capture_and_analyze(
            mode=CaptureMode.FULLSCREEN,
            do_ocr=True,
            do_vision=True
        )

        if not result:
            return {
                "message": " **Error al capturar pantalla**\n\nNo se pudo realizar la captura.",
                "actions": []
            }

        lines = ["#  Captura analizada\n"]

        # Analysis
        if result.analysis:
            lines.append(f"**Tipo:** {result.analysis.content_type.value}")
            lines.append(f"\n{result.analysis.description[:500]}")

            if result.analysis.error_detected:
                lines.append("\n **Error detectado en pantalla**")

        # OCR text preview
        if result.ocr and result.ocr.text:
            text_preview = result.ocr.text[:300]
            if len(result.ocr.text) > 300:
                text_preview += "..."
            lines.append(f"\n## Texto extraido ({len(result.ocr.text)} caracteres)\n")
            lines.append(f"```\n{text_preview}\n```")

        # Extracted data
        if result.extracted_data:
            if result.extracted_data.get("urls"):
                lines.append("\n**URLs encontradas:**")
                for url in result.extracted_data["urls"][:3]:
                    lines.append(f"- {url}")
            if result.extracted_data.get("emails"):
                lines.append("\n**Emails encontrados:**")
                for email in result.extracted_data["emails"][:3]:
                    lines.append(f"- {email}")

        # Suggestions
        if result.suggestions:
            lines.append("\n## Acciones sugeridas\n")
            for s in result.suggestions[:5]:
                lines.append(f"- {s.icon} **{s.title}**: {s.description}")

        lines.append(f"\n Captura guardada: `{result.capture.path}`")

        return {
            "message": "\n".join(lines),
            "actions": [{"type": "lens_capture", "description": "Screen captured", "success": True, "path": result.capture.path}]
        }

    elif prompt == "__LENS_OCR__":
        # Quick OCR
        result = await lens_engine.capture_and_analyze(
            mode=CaptureMode.FULLSCREEN,
            do_ocr=True,
            do_vision=False
        )

        if not result or not result.ocr:
            return {
                "message": " **Error al extraer texto**",
                "actions": []
            }

        if not result.ocr.text:
            return {
                "message": " **No se detecto texto**\n\nLa imagen no contiene texto legible.",
                "actions": []
            }

        lines = [
            "#  Texto extraido\n",
            f"**Confianza:** {result.ocr.confidence * 100:.0f}%",
            f"**Lineas:** {len(result.ocr.lines)}",
            f"\n```\n{result.ocr.text[:2000]}\n```",
        ]

        if len(result.ocr.text) > 2000:
            lines.append(f"\n*...texto truncado ({len(result.ocr.text)} caracteres totales)*")

        lines.append("\n Texto copiado al portapapeles")

        # Copy to clipboard
        try:
            import subprocess
            subprocess.run(["wl-copy", result.ocr.text], timeout=5)
        except:
            pass

        return {
            "message": "\n".join(lines),
            "actions": [{"type": "lens_ocr", "description": "Text extracted", "success": True}]
        }

    elif prompt.startswith("__LENS_ASK__:"):
        # Ask about screen
        question = prompt.split(":", 1)[1]

        answer = await lens_engine.ask_about_screen(question)

        return {
            "message": f"#  Respuesta\n\n**Pregunta:** {question}\n\n{answer}",
            "actions": [{"type": "lens_ask", "description": "Screen analyzed", "success": True}]
        }

    # Unknown command
    return {
        "message": "❓ Comando de lens no reconocido",
        "actions": []
    }


# ============================================
# Vault Handler
# ============================================
from purma_vault import get_vault_engine, VaultEngine

vault_engine = get_vault_engine()

async def handle_vault_command(prompt: str) -> Dict[str, Any]:
    """Handle special __VAULT_*__ command prompts"""

    if prompt == "__VAULT_STATUS__":
        # Show vault status
        is_init = vault_engine.is_initialized()
        is_unlocked = vault_engine.is_unlocked

        if not is_init:
            return {
                "message": "# 🔐 Purma Vault\n\n**Estado:** No inicializado\n\nUsa `/vault init` para configurar tu bóveda con una contraseña maestra.",
                "actions": [{"type": "vault_status", "initialized": False, "unlocked": False}]
            }

        if not is_unlocked:
            stats = vault_engine.get_stats()
            return {
                "message": f"# 🔐 Purma Vault\n\n**Estado:** Bloqueado 🔒\n**Secretos:** {stats['total']}\n\nUsa `/vault unlock` para desbloquear.",
                "actions": [{"type": "vault_status", "initialized": True, "unlocked": False, "stats": stats}]
            }

        stats = vault_engine.get_stats()
        categories = vault_engine.get_categories()

        lines = [
            "# 🔓 Purma Vault\n",
            f"**Estado:** Desbloqueado ✓",
            f"**Total de secretos:** {stats['total']}",
            f"**Favoritos:** {stats['favorites']}",
            f"\n**Categorías:** {', '.join(categories) if categories else 'Ninguna'}",
            "\n## Comandos disponibles",
            "- `/password <servicio>` - Buscar contraseña",
            "- `/generate` - Generar contraseña",
            "- `/addpass <nombre>` - Agregar secreto"
        ]

        return {
            "message": "\n".join(lines),
            "actions": [{"type": "vault_status", "initialized": True, "unlocked": True, "stats": stats}]
        }

    elif prompt.startswith("__VAULT_QUERY__:"):
        query = prompt.replace("__VAULT_QUERY__:", "")

        if not vault_engine.is_unlocked:
            return {
                "message": "🔒 **Vault bloqueado**\n\nDebes desbloquear el vault primero.",
                "actions": []
            }

        # Use AI query
        result = await vault_engine.ai_query(query)

        if result["success"]:
            data = result.get("data")
            if isinstance(data, dict) and "password" in data:
                return {
                    "message": f"# 🔑 {data.get('name', query)}\n\n**Usuario:** `{data.get('username', 'N/A')}`\n**Contraseña:** `{data['password']}`\n**URL:** {data.get('url', 'N/A')}\n\n⚠️ *Contraseña copiada al portapapeles*",
                    "actions": [{"type": "vault_get", "success": True, "name": data.get('name')}]
                }
            elif isinstance(data, list):
                lines = [f"# 🔍 Resultados para '{query}'\n"]
                for item in data[:10]:
                    lines.append(f"- **{item['name']}** ({item.get('username', 'N/A')}) - {item.get('category', 'General')}")
                return {
                    "message": "\n".join(lines),
                    "actions": [{"type": "vault_search", "count": len(data)}]
                }

        return {
            "message": f"❌ {result['message']}",
            "actions": []
        }

    elif prompt.startswith("__VAULT_GENERATE__:"):
        length_str = prompt.replace("__VAULT_GENERATE__:", "")
        try:
            length = int(length_str) if length_str.isdigit() else 20
        except:
            length = 20

        result = vault_engine.generate_password(length=length)
        strength = result["strength"]

        return {
            "message": f"# 🎲 Contraseña generada\n\n```\n{result['password']}\n```\n\n**Fortaleza:** {strength['level'].upper()} ({strength['score']}/{strength['max_score']})\n**Longitud:** {length} caracteres\n\n✓ *Copiada al portapapeles*",
            "actions": [{"type": "vault_generate", "strength": strength['level']}]
        }

    elif prompt.startswith("__VAULT_ADD__:"):
        name = prompt.replace("__VAULT_ADD__:", "")

        if not vault_engine.is_unlocked:
            return {
                "message": "🔒 **Vault bloqueado**\n\nDebes desbloquear el vault primero.",
                "actions": []
            }

        return {
            "message": f"# ➕ Agregar secreto\n\nPara agregar '{name}' al vault, usa el widget de Vault o el comando:\n\n```bash\ncurl -X POST http://localhost:11435/vault/add \\\n  -H 'Content-Type: application/json' \\\n  -d '{{\"name\": \"{name}\", \"value\": \"tu-contraseña\"}}'\n```",
            "actions": [{"type": "vault_add_prompt", "name": name}]
        }

    return {
        "message": "❓ Comando de vault no reconocido",
        "actions": []
    }


# ============================================
# Scribe Handler
# ============================================
from purma_scribe import get_scribe_engine, ScribeEngine

scribe_engine = get_scribe_engine()

async def handle_scribe_command(prompt: str) -> Dict[str, Any]:
    """Handle special __SCRIBE_*__ command prompts"""

    if prompt == "__SCRIBE_STATUS__":
        status = scribe_engine.get_status()

        lines = [
            "# 🎙️ Purma Scribe\n",
            f"**Grabación:** {'✓ Disponible' if status['recording_available'] else '✗ No disponible'}",
            f"**Whisper:** {'✓ Disponible' if status['whisper_available'] else '✗ No disponible'}",
            f"**Motor TTS:** {status['tts_engine']}",
            f"**Grabando:** {'Sí 🔴' if status['is_recording'] else 'No'}",
        ]

        if status['audio_devices']:
            lines.append("\n## Dispositivos de audio")
            for dev in status['audio_devices'][:5]:
                lines.append(f"- {dev['name']}")

        lines.extend([
            "\n## Comandos disponibles",
            "- `/record <segundos>` - Grabar y transcribir",
            "- `/transcribe <archivo>` - Transcribir audio",
            "- `/speak <texto>` - Texto a voz",
            "- `/dictate` - Modo dictado"
        ])

        return {
            "message": "\n".join(lines),
            "actions": [{"type": "scribe_status", "status": status}]
        }

    elif prompt.startswith("__SCRIBE_RECORD__:"):
        seconds_str = prompt.replace("__SCRIBE_RECORD__:", "")
        try:
            seconds = int(seconds_str) if seconds_str.isdigit() else 5
        except:
            seconds = 5

        status = scribe_engine.get_status()
        if not status['recording_available']:
            return {
                "message": "❌ **Grabación no disponible**\n\nInstala pyaudio: `pip install pyaudio`",
                "actions": []
            }

        result = await scribe_engine.quick_transcribe(duration_seconds=seconds)

        if result["success"]:
            t = result["transcription"]
            lines = [
                "# 📝 Transcripción\n",
                f"**Duración:** {t['duration_seconds']:.1f}s",
                f"**Idioma:** {t['language']}",
                f"**Palabras:** {t['word_count']}",
                f"\n```\n{t['text']}\n```"
            ]

            if t.get('summary'):
                lines.append(f"\n**Resumen:** {t['summary']}")

            return {
                "message": "\n".join(lines),
                "actions": [{"type": "scribe_transcribe", "id": t['id'], "success": True}]
            }

        return {
            "message": f"❌ **Error:** {result.get('error', 'Unknown error')}",
            "actions": []
        }

    elif prompt.startswith("__SCRIBE_TRANSCRIBE__:"):
        file_path = prompt.replace("__SCRIBE_TRANSCRIBE__:", "")

        result = await scribe_engine.transcribe_file(file_path, summarize=True)

        if result["success"]:
            t = result["transcription"]
            lines = [
                "# 📝 Transcripción\n",
                f"**Archivo:** `{file_path}`",
                f"**Duración:** {t['duration_seconds']:.1f}s",
                f"**Idioma:** {t['language']}",
                f"**Palabras:** {t['word_count']}",
                f"\n```\n{t['text'][:1500]}\n```"
            ]

            if len(t['text']) > 1500:
                lines.append(f"\n*...texto truncado ({len(t['text'])} caracteres)*")

            if t.get('summary'):
                lines.append(f"\n**Resumen:** {t['summary']}")

            return {
                "message": "\n".join(lines),
                "actions": [{"type": "scribe_transcribe", "id": t['id'], "success": True}]
            }

        return {
            "message": f"❌ **Error:** {result.get('error', 'Unknown error')}",
            "actions": []
        }

    elif prompt.startswith("__SCRIBE_SPEAK__:"):
        text = prompt.replace("__SCRIBE_SPEAK__:", "")

        result = scribe_engine.speak(text)

        if result["success"]:
            return {
                "message": f"🔊 **Hablando:**\n\n> {text[:200]}{'...' if len(text) > 200 else ''}",
                "actions": [{"type": "scribe_speak", "success": True}]
            }

        return {
            "message": f"❌ **Error al hablar**\n\nMotor TTS: {scribe_engine.tts.engine}",
            "actions": []
        }

    elif prompt == "__SCRIBE_DICTATE__":
        return {
            "message": "# 🎤 Modo Dictado\n\nEl modo dictado continuo se activa desde el widget de Scribe.\n\nPresiona `Super+Shift+D` para iniciar/detener.",
            "actions": [{"type": "scribe_dictate_prompt"}]
        }

    return {
        "message": "❓ Comando de scribe no reconocido",
        "actions": []
    }


# ============================================
# Vault API Endpoints
# ============================================

class VaultUnlockRequest(BaseModel):
    password: str

class VaultAddRequest(BaseModel):
    name: str
    value: str
    username: Optional[str] = None
    url: Optional[str] = None
    category: str = "General"
    secret_type: str = "password"

@app.get("/vault/status")
async def vault_status():
    """Get vault status"""
    return {
        "initialized": vault_engine.is_initialized(),
        "unlocked": vault_engine.is_unlocked,
        "stats": vault_engine.get_stats() if vault_engine.is_initialized() else None
    }

@app.post("/vault/init")
async def vault_init(request: VaultUnlockRequest):
    """Initialize vault with master password"""
    if vault_engine.is_initialized():
        raise HTTPException(status_code=400, detail="Vault already initialized")
    success = vault_engine.initialize(request.password)
    return {"success": success}

@app.post("/vault/unlock")
async def vault_unlock(request: VaultUnlockRequest):
    """Unlock vault"""
    success = vault_engine.unlock(request.password)
    if not success:
        raise HTTPException(status_code=401, detail="Invalid password")
    return {"success": True}

@app.post("/vault/lock")
async def vault_lock():
    """Lock vault"""
    vault_engine.lock()
    return {"success": True}

@app.get("/vault/secrets")
async def vault_list_secrets():
    """List all secrets (without values)"""
    if not vault_engine.is_unlocked:
        raise HTTPException(status_code=401, detail="Vault is locked")
    return {"secrets": vault_engine.list_all(decrypt=False)}

@app.get("/vault/secrets/{secret_id}")
async def vault_get_secret(secret_id: str):
    """Get a secret by ID"""
    if not vault_engine.is_unlocked:
        raise HTTPException(status_code=401, detail="Vault is locked")
    secret = vault_engine.get_secret(secret_id)
    if not secret:
        raise HTTPException(status_code=404, detail="Secret not found")
    return secret

@app.post("/vault/secrets")
async def vault_add_secret(request: VaultAddRequest):
    """Add a new secret"""
    if not vault_engine.is_unlocked:
        raise HTTPException(status_code=401, detail="Vault is locked")
    secret = vault_engine.add_secret(
        name=request.name,
        value=request.value,
        username=request.username,
        url=request.url,
        category=request.category,
        secret_type=request.secret_type
    )
    return {"success": True, "id": secret.id}

@app.delete("/vault/secrets/{secret_id}")
async def vault_delete_secret(secret_id: str):
    """Delete a secret"""
    if not vault_engine.is_unlocked:
        raise HTTPException(status_code=401, detail="Vault is locked")
    success = vault_engine.delete_secret(secret_id)
    if not success:
        raise HTTPException(status_code=404, detail="Secret not found")
    return {"success": True}

@app.get("/vault/search")
async def vault_search(q: str):
    """Search secrets"""
    if not vault_engine.is_unlocked:
        raise HTTPException(status_code=401, detail="Vault is locked")
    return {"results": vault_engine.search(q)}

@app.get("/vault/generate")
async def vault_generate_password(length: int = 20):
    """Generate a password"""
    return vault_engine.generate_password(length=length)

@app.post("/vault/query")
async def vault_ai_query(query: str):
    """Natural language query"""
    if not vault_engine.is_unlocked:
        raise HTTPException(status_code=401, detail="Vault is locked")
    return await vault_engine.ai_query(query)


# ============================================
# Scribe API Endpoints
# ============================================

@app.get("/scribe/status")
async def scribe_status():
    """Get scribe status"""
    return scribe_engine.get_status()

@app.post("/scribe/record/start")
async def scribe_start_recording(device_index: Optional[int] = None):
    """Start recording"""
    return scribe_engine.start_recording(device_index)

@app.post("/scribe/record/stop")
async def scribe_stop_recording():
    """Stop recording"""
    return scribe_engine.stop_recording()

@app.post("/scribe/transcribe/{recording_id}")
async def scribe_transcribe_recording(
    recording_id: str,
    language: Optional[str] = None,
    summarize: bool = False
):
    """Transcribe a recording"""
    return await scribe_engine.transcribe_recording(recording_id, language, summarize)

@app.post("/scribe/transcribe-file")
async def scribe_transcribe_file(
    file_path: str,
    language: Optional[str] = None,
    summarize: bool = False
):
    """Transcribe an audio file"""
    return await scribe_engine.transcribe_file(file_path, language, summarize)

@app.post("/scribe/quick")
async def scribe_quick_transcribe(
    seconds: int = 5,
    language: Optional[str] = None
):
    """Quick record and transcribe"""
    return await scribe_engine.quick_transcribe(seconds, language)

@app.post("/scribe/speak")
async def scribe_speak(
    text: str,
    voice: Optional[str] = None,
    speed: float = 1.0
):
    """Text to speech"""
    return scribe_engine.speak(text, voice, speed)

@app.get("/scribe/voices")
async def scribe_list_voices():
    """List TTS voices"""
    return {"voices": scribe_engine.list_voices()}

@app.get("/scribe/history")
async def scribe_history(limit: int = 20):
    """Get transcription history"""
    return {"transcriptions": scribe_engine.get_recent_transcriptions(limit)}

@app.get("/scribe/transcription/{transcription_id}")
async def scribe_get_transcription(transcription_id: str):
    """Get a transcription"""
    t = scribe_engine.get_transcription(transcription_id)
    if not t:
        raise HTTPException(status_code=404, detail="Transcription not found")
    return t

@app.delete("/scribe/transcription/{transcription_id}")
async def scribe_delete_transcription(transcription_id: str):
    """Delete a transcription"""
    success = scribe_engine.delete_transcription(transcription_id)
    if not success:
        raise HTTPException(status_code=404, detail="Transcription not found")
    return {"success": True}


@app.get("/spaces")
async def list_spaces():
    """List all spaces"""
    return {
        "spaces": space_manager.list_spaces(),
        "active": space_manager.global_state.active_space,
        "templates": list(SPACE_TEMPLATES.keys()),
    }


@app.get("/spaces/{space_id}")
async def get_space(space_id: str):
    """Get space details"""
    space = space_manager.get_space(space_id)
    if not space:
        raise HTTPException(status_code=404, detail=f"Space '{space_id}' not found")
    return space_manager._space_to_dict(space)


@app.post("/spaces")
async def create_space(
    name: str,
    description: str = "",
    icon: str = "",
    template: str = None
):
    """Create a new space"""
    try:
        if template and template in SPACE_TEMPLATES:
            space = create_template_space(space_manager, template)
            # Rename if different name provided
            if name != SPACE_TEMPLATES[template]["name"]:
                space_manager.update_space(space.id, {"name": name})
        else:
            space = space_manager.create_space(name, description, icon, template)
        return {
            "success": True,
            "space": space_manager._space_to_dict(space)
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.put("/spaces/{space_id}")
async def update_space(space_id: str, updates: Dict[str, Any]):
    """Update a space configuration"""
    try:
        space = space_manager.update_space(space_id, updates)
        return {
            "success": True,
            "space": space_manager._space_to_dict(space)
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.delete("/spaces/{space_id}")
async def delete_space(space_id: str):
    """Delete a space"""
    try:
        space_manager.delete_space(space_id)
        return {"success": True, "message": f"Space '{space_id}' deleted"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/spaces/{space_id}/activate")
async def activate_space(space_id: str, save_current: bool = True):
    """Activate a space"""
    result = await space_manager.activate_space(space_id, save_current)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "Activation failed"))
    return result


@app.post("/spaces/switch")
async def switch_space(direction: str = "next"):
    """Switch to next/previous space"""
    result = await space_manager.quick_switch(direction)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "Switch failed"))
    return result


@app.get("/spaces/active")
async def get_active_space():
    """Get currently active space"""
    space = space_manager.get_active_space()
    if not space:
        return {"active": None}
    return {
        "active": space_manager._space_to_dict(space)
    }


@app.post("/spaces/{space_id}/save-state")
async def save_space_state(space_id: str):
    """Save current window state for a space"""
    if space_id not in space_manager.spaces:
        raise HTTPException(status_code=404, detail=f"Space '{space_id}' not found")
    await space_manager.save_space_state(space_id)
    return {"success": True, "message": f"State saved for '{space_id}'"}


@app.get("/spaces/{space_id}/state")
async def get_space_state(space_id: str):
    """Get saved state for a space"""
    state = space_manager.load_space_state(space_id)
    if not state:
        return {"state": None}
    return {"state": {
        "space_id": state.space_id,
        "windows": state.windows,
        "timestamp": state.timestamp,
    }}


@app.get("/spaces/windows")
async def get_current_windows():
    """Get list of current windows"""
    windows = await space_manager.get_current_windows()
    return {"windows": windows}


@app.get("/spaces/templates")
async def list_templates():
    """List available space templates"""
    return {
        "templates": [
            {
                "id": tid,
                "name": t["name"],
                "description": t.get("description", ""),
                "icon": t.get("icon", ""),
                "apps_count": len(t.get("apps_open", [])),
            }
            for tid, t in SPACE_TEMPLATES.items()
        ]
    }


# ============================================
# Flow Endpoints
# ============================================

from purma_flow import (
    flow_manager, flow_analyzer, trigger_watcher,
    create_flow_from_recording, ActionType, RecordedAction,
    FlowStep, FlowTrigger, TriggerType
)


@app.get("/flows")
async def list_flows():
    """List all flows"""
    return {
        "flows": flow_manager.list_flows(),
        "recording": flow_manager.state.active_recording,
        "running": flow_manager.state.running_flows,
    }


@app.get("/flows/{flow_id}")
async def get_flow(flow_id: str):
    """Get flow details"""
    flow = flow_manager.get_flow(flow_id)
    if not flow:
        raise HTTPException(status_code=404, detail=f"Flow '{flow_id}' not found")
    return flow_manager._flow_to_dict(flow)


@app.post("/flows")
async def create_flow(
    name: str,
    description: str = "",
    from_description: str = None,
):
    """Create a new flow"""
    if from_description:
        # Generate flow from natural language using AI
        result = await flow_analyzer.generate_flow_from_description(from_description)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])

        # Create flow from AI result
        steps = [
            FlowStep(
                action_type=ActionType(s.get("action_type", "command")),
                description=s.get("description", ""),
                command=s.get("command", ""),
                template=s.get("command", ""),
                timeout=s.get("timeout", 30),
            )
            for s in result.get("steps", [])
        ]

        flow = flow_manager.create_flow(
            name=result.get("name", name),
            description=result.get("description", description),
            steps=steps,
        )
        flow.icon = result.get("icon", "⚡")
        flow.variables = result.get("variables", {})
        flow.variable_prompts = result.get("variable_prompts", {})
        flow.tags = result.get("tags", [])
        flow_manager._save_flow(flow)
    else:
        flow = flow_manager.create_flow(name, description)

    return {
        "success": True,
        "flow": flow_manager._flow_to_dict(flow),
    }


@app.put("/flows/{flow_id}")
async def update_flow(flow_id: str, updates: Dict[str, Any]):
    """Update a flow"""
    flow = flow_manager.update_flow(flow_id, updates)
    if not flow:
        raise HTTPException(status_code=404, detail=f"Flow '{flow_id}' not found")
    return {
        "success": True,
        "flow": flow_manager._flow_to_dict(flow),
    }


@app.delete("/flows/{flow_id}")
async def delete_flow(flow_id: str):
    """Delete a flow"""
    if not flow_manager.delete_flow(flow_id):
        raise HTTPException(status_code=404, detail=f"Flow '{flow_id}' not found")
    return {"success": True, "message": f"Flow '{flow_id}' deleted"}


@app.post("/flows/{flow_id}/run")
async def run_flow(
    flow_id: str,
    variables: Dict[str, Any] = None,
    dry_run: bool = False,
):
    """Execute a flow"""
    result = await flow_manager.run_flow(flow_id, variables, dry_run)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "Execution failed"))
    return result


@app.post("/flows/{flow_id}/toggle")
async def toggle_flow(flow_id: str):
    """Enable/disable a flow"""
    flow = flow_manager.get_flow(flow_id)
    if not flow:
        raise HTTPException(status_code=404, detail=f"Flow '{flow_id}' not found")

    flow.enabled = not flow.enabled
    flow_manager._save_flow(flow)

    return {
        "success": True,
        "flow_id": flow_id,
        "enabled": flow.enabled,
    }


@app.post("/flows/{flow_id}/suggestions")
async def get_flow_suggestions(flow_id: str):
    """Get AI suggestions to improve a flow"""
    flow = flow_manager.get_flow(flow_id)
    if not flow:
        raise HTTPException(status_code=404, detail=f"Flow '{flow_id}' not found")

    suggestions = await flow_analyzer.suggest_improvements(flow)
    return {
        "flow_id": flow_id,
        "suggestions": suggestions,
    }


# Recording endpoints
@app.post("/flow/recording/start")
async def start_recording(name: str = ""):
    """Start a new recording session"""
    try:
        recording = flow_manager.start_recording(name)
        return {
            "success": True,
            "recording": {
                "id": recording.id,
                "name": recording.name,
                "started_at": recording.started_at,
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/flow/recording/stop")
async def stop_recording():
    """Stop current recording"""
    recording = flow_manager.stop_recording()
    if not recording:
        raise HTTPException(status_code=400, detail="No active recording")

    return {
        "success": True,
        "recording": {
            "id": recording.id,
            "name": recording.name,
            "actions_count": len(recording.actions),
            "duration": recording.ended_at,
        }
    }


@app.get("/flow/recording/status")
async def recording_status():
    """Get current recording status"""
    if not flow_manager.state.active_recording:
        return {"recording": False}

    recording = flow_manager.recordings.get(flow_manager.state.active_recording)
    return {
        "recording": True,
        "id": recording.id if recording else None,
        "name": recording.name if recording else None,
        "actions_count": len(recording.actions) if recording else 0,
    }


@app.post("/flow/record/action")
async def record_action(action: Dict[str, Any]):
    """Record an action (called by recorder daemon)"""
    if not flow_manager.state.active_recording:
        return {"success": False, "error": "No active recording"}

    try:
        recorded = RecordedAction(
            type=ActionType(action.get("type", "command")),
            data=action.get("data", {}),
            window_title=action.get("window_title", ""),
            working_dir=action.get("working_dir", ""),
            timestamp=action.get("timestamp", 0),
        )
        flow_manager.add_action(recorded)
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/flow/recordings")
async def list_recordings():
    """List all recordings"""
    return {
        "recordings": [
            {
                "id": r.id,
                "name": r.name,
                "started_at": r.started_at,
                "ended_at": r.ended_at,
                "actions_count": len(r.actions),
                "analyzed": r.analyzed,
                "generated_flow_id": r.generated_flow_id,
            }
            for r in flow_manager.recordings.values()
        ]
    }


@app.get("/flow/recordings/{recording_id}")
async def get_recording(recording_id: str):
    """Get recording details"""
    recording = flow_manager.recordings.get(recording_id)
    if not recording:
        raise HTTPException(status_code=404, detail=f"Recording '{recording_id}' not found")
    return flow_manager._recording_to_dict(recording)


@app.post("/flow/recordings/{recording_id}/analyze")
async def analyze_recording(recording_id: str, use_remote: bool = False):
    """Analyze a recording and generate a flow"""
    flow = await create_flow_from_recording(recording_id, use_remote)
    if not flow:
        raise HTTPException(status_code=400, detail="Analysis failed")

    return {
        "success": True,
        "flow": flow_manager._flow_to_dict(flow),
    }


# ============================================
# Bridge Endpoints (AI-Augmented Terminal)
# ============================================

from purma_bridge import bridge_engine, CommandAnalysis, CommandSuggestion, ErrorExplanation
from dataclasses import asdict

# Store last error for explanation
_last_error: Dict[str, Any] = {}


@app.post("/bridge/analyze")
async def bridge_analyze(data: Dict[str, Any]):
    """Analyze a command for safety and effects"""
    command = data.get("command", "")
    analysis = bridge_engine.analyze_command(command)
    return {"analysis": asdict(analysis)}


@app.post("/bridge/translate")
async def bridge_translate(data: Dict[str, Any]):
    """Translate natural language to shell command"""
    text = data.get("text", "")
    context = data.get("context", {})
    suggestions = await bridge_engine.translate_to_command(text, context)
    return {"suggestions": [asdict(s) for s in suggestions]}


@app.post("/bridge/explain")
async def bridge_explain(data: Dict[str, Any]):
    """Explain an error and provide solutions"""
    global _last_error

    command = data.get("command", "")
    error = data.get("error", "")
    exit_code = data.get("exit_code", 1)

    explanation = await bridge_engine.explain_error(command, error, exit_code)

    # Store for later retrieval
    _last_error = {
        "command": command,
        "error": error,
        "exit_code": exit_code,
        "explanation": asdict(explanation),
        "timestamp": time.time(),
    }

    return {"explanation": asdict(explanation)}


@app.get("/bridge/last-error")
async def bridge_last_error():
    """Get explanation for last error"""
    if _last_error and time.time() - _last_error.get("timestamp", 0) < 3600:
        return {"explanation": _last_error.get("explanation")}
    return {"explanation": None}


@app.post("/bridge/suggest")
async def bridge_suggest(data: Dict[str, Any]):
    """Get command suggestions based on partial input"""
    partial = data.get("input", "")
    context = data.get("context", {})
    suggestions = await bridge_engine.get_suggestions(partial, context)
    return {"suggestions": [asdict(s) for s in suggestions]}


@app.post("/bridge/sandbox")
async def bridge_sandbox(data: Dict[str, Any]):
    """Preview what a command would do"""
    command = data.get("command", "")
    preview = await bridge_engine.sandbox_preview(command)
    return {"preview": preview}


@app.post("/bridge/history")
async def bridge_add_history(data: Dict[str, Any]):
    """Add command to history"""
    entry_id = bridge_engine.add_to_history(
        command=data.get("command", ""),
        output=data.get("output", ""),
        exit_code=data.get("exit_code", 0),
        working_dir=data.get("working_dir", ""),
        duration=data.get("duration", 0),
        intent=data.get("intent", ""),
    )
    return {"success": True, "id": entry_id}


@app.post("/bridge/history/search")
async def bridge_search_history(data: Dict[str, Any]):
    """Search command history"""
    query = data.get("query", "")
    limit = data.get("limit", 20)
    entries = bridge_engine.search_history(query, limit)
    return {"entries": [asdict(e) for e in entries]}


@app.get("/bridge/history/recent")
async def bridge_recent_history(limit: int = 50):
    """Get recent history"""
    entries = bridge_engine.get_recent_history(limit)
    return {"entries": [asdict(e) for e in entries]}


# ============================================
# Pulse API Endpoints
# ============================================

from purma_pulse import pulse_engine

@app.get("/pulse/status")
async def pulse_status():
    """Get current system status with health score"""
    return pulse_engine.get_status()


@app.get("/pulse/metrics")
async def pulse_metrics():
    """Get detailed system metrics"""
    return pulse_engine.get_detailed_metrics()


@app.get("/pulse/predictions")
async def pulse_predictions(minutes: int = 30):
    """Get metric predictions"""
    return {"predictions": pulse_engine.get_predictions(minutes)}


@app.get("/pulse/insights")
async def pulse_insights():
    """Get AI-powered insights"""
    insights = await pulse_engine.get_insights()
    return {"insights": insights}


@app.get("/pulse/history")
async def pulse_history(hours: int = 1):
    """Get historical metrics"""
    return {"history": pulse_engine.get_history(hours)}


@app.get("/pulse/alerts")
async def pulse_alerts():
    """Get active alerts"""
    status = pulse_engine.get_status()
    return {"alerts": status["alerts"]}


@app.post("/pulse/alerts/{alert_id}/acknowledge")
async def pulse_acknowledge_alert(alert_id: str):
    """Acknowledge an alert"""
    success = pulse_engine.alert_manager.acknowledge(alert_id)
    return {"success": success}


@app.post("/pulse/alerts/{alert_id}/dismiss")
async def pulse_dismiss_alert(alert_id: str):
    """Dismiss an alert"""
    success = pulse_engine.alert_manager.dismiss(alert_id)
    return {"success": success}


@app.post("/pulse/cleanup")
async def pulse_cleanup():
    """Run disk cleanup"""
    result = pulse_engine.cleanup_disk()
    return result


@app.get("/pulse/refresh")
async def pulse_refresh():
    """Force refresh metrics"""
    metrics, health = pulse_engine.collect_now()
    return pulse_engine.get_status()


# ============================================
# Lens API Endpoints
# ============================================

from purma_lens import lens_engine, CaptureMode, ActionType as LensActionType

@app.post("/lens/capture")
async def lens_capture(
    mode: str = "fullscreen",
    do_ocr: bool = True,
    do_vision: bool = True,
    delay: float = 0
):
    """Capture screen and analyze"""
    capture_mode = CaptureMode(mode)
    result = await lens_engine.capture_and_analyze(
        mode=capture_mode,
        do_ocr=do_ocr,
        do_vision=do_vision,
        delay=delay
    )

    if not result:
        return {"success": False, "error": "Capture failed"}

    return {
        "success": True,
        "capture": {
            "id": result.capture.id,
            "path": result.capture.path,
            "timestamp": result.capture.timestamp,
            "width": result.capture.width,
            "height": result.capture.height,
        },
        "ocr": {
            "text": result.ocr.text if result.ocr else "",
            "confidence": result.ocr.confidence if result.ocr else 0,
            "lines": result.ocr.lines if result.ocr else [],
        } if result.ocr else None,
        "analysis": {
            "description": result.analysis.description if result.analysis else "",
            "content_type": result.analysis.content_type.value if result.analysis else "unknown",
            "error_detected": result.analysis.error_detected if result.analysis else False,
            "code_detected": result.analysis.code_detected if result.analysis else False,
        } if result.analysis else None,
        "suggestions": [
            {
                "action": s.action.value,
                "title": s.title,
                "description": s.description,
                "icon": s.icon,
                "priority": s.priority,
            }
            for s in result.suggestions
        ],
        "extracted_data": result.extracted_data,
    }


@app.post("/lens/capture/region")
async def lens_capture_region(do_ocr: bool = True, do_vision: bool = True):
    """Capture region interactively"""
    result = await lens_engine.capture_and_analyze(
        mode=CaptureMode.REGION,
        do_ocr=do_ocr,
        do_vision=do_vision
    )

    if not result:
        return {"success": False, "error": "Capture failed"}

    return {
        "success": True,
        "capture_id": result.capture.id,
        "path": result.capture.path,
        "text": result.ocr.text if result.ocr else "",
    }


@app.post("/lens/capture/window")
async def lens_capture_window(do_ocr: bool = True, do_vision: bool = True):
    """Capture active window"""
    result = await lens_engine.capture_and_analyze(
        mode=CaptureMode.WINDOW,
        do_ocr=do_ocr,
        do_vision=do_vision
    )

    if not result:
        return {"success": False, "error": "Capture failed"}

    return {
        "success": True,
        "capture_id": result.capture.id,
        "path": result.capture.path,
        "text": result.ocr.text if result.ocr else "",
    }


@app.post("/lens/analyze")
async def lens_analyze_image(data: Dict[str, Any]):
    """Analyze existing image"""
    image_path = data.get("path", "")
    do_ocr = data.get("do_ocr", True)
    do_vision = data.get("do_vision", True)

    if not image_path:
        return {"success": False, "error": "No image path provided"}

    result = await lens_engine.analyze_image(image_path, do_ocr, do_vision)

    if not result:
        return {"success": False, "error": "Analysis failed"}

    return {
        "success": True,
        "ocr": {
            "text": result.ocr.text if result.ocr else "",
            "confidence": result.ocr.confidence if result.ocr else 0,
            "lines": result.ocr.lines if result.ocr else [],
        } if result.ocr else None,
        "analysis": {
            "description": result.analysis.description if result.analysis else "",
            "content_type": result.analysis.content_type.value if result.analysis else "unknown",
        } if result.analysis else None,
        "suggestions": [
            {
                "action": s.action.value,
                "title": s.title,
                "description": s.description,
            }
            for s in result.suggestions
        ],
    }


@app.get("/lens/ocr")
async def lens_quick_ocr(mode: str = "region"):
    """Quick OCR capture"""
    capture_mode = CaptureMode(mode)
    text = await lens_engine.quick_ocr(capture_mode)

    return {
        "success": text is not None,
        "text": text or "",
    }


@app.post("/lens/ask")
async def lens_ask(data: Dict[str, Any]):
    """Ask question about screen"""
    question = data.get("question", "Describe what you see")
    mode = data.get("mode", "fullscreen")

    capture_mode = CaptureMode(mode)
    answer = await lens_engine.ask_about_screen(question, capture_mode)

    return {
        "success": True,
        "answer": answer,
    }


@app.get("/lens/recent")
async def lens_recent(limit: int = 10):
    """Get recent captures"""
    return {
        "captures": lens_engine.get_recent_captures(limit)
    }


@app.post("/lens/execute")
async def lens_execute(data: Dict[str, Any]):
    """Execute a suggestion action"""
    from purma_lens import ContextSuggestion, ActionType as LensActionType

    action = data.get("action", "")
    action_data = data.get("data", "")

    suggestion = ContextSuggestion(
        action=LensActionType(action),
        title="",
        description="",
        data=action_data,
        command=data.get("command"),
    )

    result = lens_engine.execute_suggestion(suggestion)
    return result


@app.post("/lens/cleanup")
async def lens_cleanup(days: int = 7):
    """Clean up old captures"""
    count = lens_engine.cleanup_old_captures(days)
    return {
        "success": True,
        "deleted": count,
    }


# ============================================
# Cortex Endpoints (Predictive AI)
# ============================================

from purma_cortex import get_cortex_engine

cortex_engine = get_cortex_engine()


@app.get("/cortex/status")
async def cortex_status():
    """Get Cortex status"""
    return cortex_engine.get_status()


@app.post("/cortex/start")
async def cortex_start():
    """Start Cortex learning"""
    return cortex_engine.start_learning()


@app.post("/cortex/stop")
async def cortex_stop():
    """Stop Cortex learning"""
    return cortex_engine.stop_learning()


@app.get("/cortex/predict")
async def cortex_predict(current_app: str = None):
    """Get predictions based on current context"""
    return cortex_engine.predict(current_app)


@app.get("/cortex/schedule")
async def cortex_schedule():
    """Get predicted daily schedule"""
    return cortex_engine.get_schedule()


@app.get("/cortex/patterns")
async def cortex_patterns():
    """Get learned patterns"""
    return cortex_engine.get_patterns()


@app.get("/cortex/insights")
async def cortex_insights():
    """Get insights from patterns"""
    return cortex_engine.get_insights()


@app.post("/cortex/prepare")
async def cortex_prepare(data: Dict[str, Any]):
    """Prepare workspace by launching apps"""
    apps = data.get("apps", [])
    return cortex_engine.prepare_workspace(apps)


# ============================================
# Memory Endpoints (RAG)
# ============================================

from purma_memory import get_memory_engine

memory_engine = get_memory_engine()


@app.get("/memory/status")
async def memory_status():
    """Get Memory status"""
    return memory_engine.get_status()


@app.post("/memory/index/file")
async def memory_index_file(data: Dict[str, Any]):
    """Index a single file"""
    path = data.get("path", "")
    embeddings = data.get("embeddings", True)
    doc_id = await memory_engine.index_file(path, embeddings)
    return {"success": doc_id is not None, "id": doc_id}


@app.post("/memory/index/directory")
async def memory_index_directory(data: Dict[str, Any]):
    """Index a directory"""
    path = data.get("path", "")
    recursive = data.get("recursive", True)
    patterns = data.get("patterns")
    result = await memory_engine.index_directory(path, recursive, patterns)
    return result


@app.get("/memory/search")
async def memory_search(q: str, mode: str = "hybrid", limit: int = 10, file_type: str = None):
    """Search the memory"""
    return await memory_engine.search(q, mode, limit, file_type)


@app.post("/memory/ask")
async def memory_ask(data: Dict[str, Any]):
    """Ask a question (RAG)"""
    question = data.get("question", "")
    return await memory_engine.ask(question)


@app.get("/memory/document/{doc_id}")
async def memory_get_document(doc_id: str):
    """Get a document by ID"""
    doc = memory_engine.get_document(doc_id)
    if doc:
        return {"success": True, "document": doc}
    return {"success": False, "error": "Document not found"}


@app.delete("/memory/document/{doc_id}")
async def memory_delete_document(doc_id: str):
    """Delete a document"""
    return memory_engine.delete_document(doc_id)


@app.post("/memory/watch")
async def memory_add_watch(data: Dict[str, Any]):
    """Add a directory to watch"""
    path = data.get("path", "")
    recursive = data.get("recursive", True)
    patterns = data.get("patterns", "*")
    return memory_engine.add_watch(path, recursive, patterns)


@app.get("/memory/history")
async def memory_search_history(limit: int = 20):
    """Get recent searches"""
    return {"searches": memory_engine.get_recent_searches(limit)}


# ============================================
# Ghost Endpoints (Shadow AI)
# ============================================

from purma_ghost import get_ghost_engine

ghost_engine = get_ghost_engine()


@app.get("/ghost/status")
async def ghost_status():
    """Get Ghost status"""
    return ghost_engine.get_status()


@app.post("/ghost/start")
async def ghost_start():
    """Start Ghost observation"""
    return ghost_engine.start()


@app.post("/ghost/stop")
async def ghost_stop():
    """Stop Ghost observation"""
    return ghost_engine.stop()


@app.post("/ghost/analyze")
async def ghost_analyze():
    """Run analysis and generate suggestions"""
    return ghost_engine.analyze()


@app.get("/ghost/suggestions")
async def ghost_suggestions(limit: int = 10):
    """Get pending suggestions"""
    return {"suggestions": ghost_engine.get_suggestions(limit)}


@app.post("/ghost/suggestions/{suggestion_id}/respond")
async def ghost_respond(suggestion_id: str, data: Dict[str, Any]):
    """Respond to a suggestion (accept/reject/dismiss)"""
    response = data.get("response", "dismissed")
    return ghost_engine.respond_to_suggestion(suggestion_id, response)


@app.post("/ghost/suggestions/{suggestion_id}/apply")
async def ghost_apply(suggestion_id: str):
    """Apply an accepted suggestion"""
    return ghost_engine.apply_suggestion(suggestion_id)


@app.get("/ghost/insights")
async def ghost_insights():
    """Get observational insights"""
    return {"insights": ghost_engine.get_insights()}


# ============================================
# Multi-Agent Endpoints
# ============================================

from purma_agents import get_agent_engine

agent_engine = get_agent_engine()


@app.get("/agents/status")
async def agents_status():
    """Get Multi-Agent system status"""
    return agent_engine.get_status()


@app.get("/agents/list")
async def agents_list():
    """Get list of available agents"""
    return {"agents": agent_engine.get_agents()}


@app.post("/agents/run")
async def agents_run(data: Dict[str, Any]):
    """Run a task through the multi-agent system"""
    description = data.get("task", data.get("description", ""))
    context = data.get("context", {})
    return await agent_engine.run(description, context)


@app.post("/agents/{agent_name}/ask")
async def agents_ask(agent_name: str, data: Dict[str, Any]):
    """Ask a specific agent directly"""
    description = data.get("task", data.get("description", ""))
    context = data.get("context", {})
    return await agent_engine.ask_agent(agent_name, description, context)


# ============================================
# Integration System Endpoints
# ============================================

from purma_integration import (
    get_event_bus, get_context, get_router, get_orchestrator,
    PurmaEvent, EventType, emit_event
)

integration_bus = get_event_bus()
integration_context = get_context()
integration_router = get_router()
integration_orchestrator = get_orchestrator()


class EventRequest(BaseModel):
    event_type: str
    source: str
    data: Dict[str, Any]
    priority: int = 5
    tags: List[str] = []


class RouteRequest(BaseModel):
    query: str
    context: Optional[Dict[str, Any]] = None


class WorkflowRequest(BaseModel):
    params: Optional[Dict[str, Any]] = {}


@app.get("/integration/status")
async def integration_status():
    """Get integration system status"""
    return {
        "status": "active",
        "modules_registered": len(integration_bus.get_all_modules()),
        "modules": list(integration_bus.get_all_modules().keys()),
        "context_keys": list(integration_context.get_full_context().keys()),
        "available_workflows": [
            "morning_routine", "focus_mode", "research_task",
            "code_review", "capture_and_analyze", "voice_command"
        ]
    }


@app.get("/integration/events")
async def integration_events(
    event_type: Optional[str] = None,
    source: Optional[str] = None,
    since: Optional[str] = None,
    limit: int = 50
):
    """Query recent events"""
    events = integration_bus.query_events(
        event_type=event_type,
        source=source,
        since=since,
        limit=limit
    )
    return {"events": [e.to_dict() for e in events]}


@app.post("/integration/events")
async def integration_publish_event(request: EventRequest):
    """Publish an event to the bus"""
    event = PurmaEvent(
        event_type=request.event_type,
        source=request.source,
        data=request.data,
        priority=request.priority,
        tags=request.tags
    )
    await integration_bus.publish(event)
    return {"success": True, "event_id": event.event_id}


@app.get("/integration/context")
async def integration_get_context():
    """Get current system context"""
    return {
        "context": integration_context.get_full_context(),
        "summary": integration_context.get_context_summary()
    }


@app.post("/integration/context/{key}")
async def integration_set_context(key: str, data: Dict[str, Any]):
    """Set a context value"""
    value = data.get("value")
    integration_context.set(key, value)
    return {"success": True, "key": key, "value": value}


@app.post("/integration/route")
async def integration_route_query(request: RouteRequest):
    """Route a query to the appropriate module"""
    module, confidence = integration_router.route(request.query)
    return {
        "query": request.query,
        "routed_to": module,
        "confidence": confidence
    }


@app.post("/integration/smart-query")
async def integration_smart_query(request: RouteRequest):
    """Route and execute a query"""
    result = await integration_router.smart_query(
        request.query,
        request.context
    )
    return result


@app.post("/integration/workflow/{workflow_name}")
async def integration_execute_workflow(workflow_name: str, request: WorkflowRequest):
    """Execute a predefined workflow"""
    result = await integration_orchestrator.execute(workflow_name, request.params)
    return {"workflow": workflow_name, "result": result}


@app.get("/integration/modules")
async def integration_list_modules():
    """List all registered modules"""
    modules = integration_bus.get_all_modules()
    return {
        "modules": [
            {
                "name": name,
                "description": mod.description,
                "status": mod.get_status()
            }
            for name, mod in modules.items()
        ]
    }


# ============================================
# Sync Endpoints
# ============================================

from purma_sync import get_sync_engine

sync_engine = get_sync_engine()


class SyncFolderRequest(BaseModel):
    path: str
    name: Optional[str] = None
    organize_mode: str = "disabled"


class OrganizeModeRequest(BaseModel):
    mode: str


class OrganizeRequest(BaseModel):
    dry_run: bool = True
    by_date: bool = True


@app.get("/sync/status")
async def sync_status():
    """Get sync system status"""
    return sync_engine.get_status()


@app.get("/sync/folders")
async def sync_list_folders():
    """List synced folders"""
    return {"folders": sync_engine.list_folders()}


@app.post("/sync/folders")
async def sync_add_folder(request: SyncFolderRequest):
    """Add folder for sync"""
    return sync_engine.add_sync_folder(
        request.path,
        request.name,
        request.organize_mode
    )


@app.delete("/sync/folders/{folder_id}")
async def sync_remove_folder(folder_id: str):
    """Remove folder from sync"""
    return sync_engine.remove_sync_folder(folder_id)


@app.get("/sync/folders/{folder_id}")
async def sync_get_folder(folder_id: str):
    """Get folder details"""
    folder = sync_engine.storage.get_folder(folder_id)
    if folder:
        return folder.to_dict()
    return {"error": "Carpeta no encontrada"}


@app.post("/sync/folders/{folder_id}/organize-mode")
async def sync_set_organize_mode(folder_id: str, request: OrganizeModeRequest):
    """Set folder organize mode"""
    return sync_engine.set_organize_mode(folder_id, request.mode)


@app.get("/sync/folders/{folder_id}/suggest")
async def sync_suggest_organization(folder_id: str):
    """Get organization suggestions for folder"""
    return sync_engine.suggest_organization(folder_id)


@app.post("/sync/folders/{folder_id}/organize")
async def sync_organize_folder(folder_id: str, request: OrganizeRequest):
    """Organize folder with AI"""
    return sync_engine.organize_folder(
        folder_id,
        dry_run=request.dry_run,
        by_date=request.by_date
    )


@app.get("/sync/devices")
async def sync_list_devices():
    """List registered devices"""
    return {"devices": sync_engine.list_devices()}


@app.post("/sync/devices")
async def sync_register_device(data: Dict[str, Any]):
    """Register a device"""
    return sync_engine.register_device(
        data.get("device_id", ""),
        data.get("name", "Unknown"),
        data.get("device_type", "linux"),
        data.get("ip_address", "")
    )


@app.post("/sync/folders/{folder_id}/link/{device_id}")
async def sync_link_folder_device(folder_id: str, device_id: str):
    """Link folder to device"""
    return sync_engine.link_folder_to_device(folder_id, device_id)


@app.post("/sync/now")
async def sync_trigger_sync(data: Dict[str, Any] = None):
    """Trigger immediate sync"""
    folder_id = data.get("folder_id") if data else None
    return sync_engine.sync_now(folder_id)


@app.post("/sync/watcher/start")
async def sync_start_watcher():
    """Start folder watcher"""
    return sync_engine.start_watcher()


@app.post("/sync/watcher/stop")
async def sync_stop_watcher():
    """Stop folder watcher"""
    return sync_engine.stop_watcher()


# Direct organize endpoint (without sync)
@app.post("/organize/preview")
async def organize_preview(data: Dict[str, Any]):
    """Preview organization for any path"""
    from pathlib import Path
    path = data.get("path", "")
    if not path:
        return {"error": "Path requerido"}

    expanded = os.path.expanduser(path)
    folder_path = Path(expanded)

    if not folder_path.exists():
        return {"error": f"No existe: {path}"}

    suggestions = sync_engine.organizer.suggest_organization(folder_path)
    return {
        "path": str(folder_path),
        "suggestions": suggestions,
        "total_files": sum(len(files) for files in suggestions.values())
    }


# ============================================
# Mobile API
# ============================================

from purma_mobile_api import get_mobile_router

app.include_router(get_mobile_router())


# ============================================
# Models API
# ============================================

from purma_models import get_model_manager, RECOMMENDED_MODELS, STARTER_PACKS

@app.get("/models/status")
async def models_status():
    """Estado de Ollama y modelos"""
    manager = get_model_manager()
    status = await manager.check_ollama()
    installed = await manager.get_installed_models() if status["running"] else []
    return {
        **status,
        "installed_count": len(installed),
        "installed": installed
    }

@app.get("/models/list")
async def models_list():
    """Lista modelos instalados"""
    manager = get_model_manager()
    return {"models": await manager.get_installed_models()}

@app.get("/models/available")
async def models_available(category: str = None):
    """Lista modelos disponibles"""
    manager = get_model_manager()
    return {"models": await manager.get_available_models(category)}

@app.get("/models/recommended")
async def models_recommended():
    """Modelos recomendados"""
    manager = get_model_manager()
    return {"models": await manager.get_recommended()}

@app.get("/models/catalog")
async def models_catalog():
    """Catálogo completo de modelos"""
    return {"catalog": RECOMMENDED_MODELS}

@app.get("/models/packs")
async def models_packs():
    """Starter packs disponibles"""
    return {"packs": STARTER_PACKS}

@app.get("/models/system-info")
async def models_system_info():
    """Info del sistema para recomendaciones"""
    manager = get_model_manager()
    return await manager.get_system_info()

@app.post("/models/install/{model_id}")
async def models_install(model_id: str):
    """Instalar un modelo"""
    manager = get_model_manager()
    status = await manager.check_ollama()
    if not status["running"]:
        raise HTTPException(status_code=503, detail="Ollama is not running")
    return await manager.install_model(model_id)

@app.delete("/models/{model_id}")
async def models_delete(model_id: str):
    """Eliminar un modelo"""
    manager = get_model_manager()
    return await manager.uninstall_model(model_id)

@app.post("/models/pack/{pack_id}")
async def models_install_pack(pack_id: str):
    """Instalar un starter pack"""
    manager = get_model_manager()
    status = await manager.check_ollama()
    if not status["running"]:
        raise HTTPException(status_code=503, detail="Ollama is not running")
    return await manager.install_pack(pack_id)

@app.get("/models/search")
async def models_search(q: str):
    """Buscar modelos"""
    manager = get_model_manager()
    return {"results": await manager.search_models(q)}


# ============================================
# Main
# ============================================

def main():
    # Initialize
    load_all_agents()
    load_all_commands()

    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║                  Purma AI Assistant v3.0                     ║
║             Agents • Commands • File Management              ║
║                                                              ║
║  Server:   http://{SERVER_HOST}:{SERVER_PORT}                        ║
║  Ollama:   {OLLAMA_HOST}                             ║
║  Model:    {DEFAULT_MODEL}                                        ║
║                                                              ║
║  Agents:   {len(loaded_agents)} disponibles                                 ║
║  Commands: {len(loaded_commands)} disponibles                                 ║
║  Tools:    {len(TOOLS)} disponibles                                  ║
║                                                              ║
║  Config:   {CONFIG_DIR}                 ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """)

    uvicorn.run(app, host=SERVER_HOST, port=SERVER_PORT, log_level="info")


if __name__ == "__main__":
    main()
