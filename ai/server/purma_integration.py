"""
PurmaLinux - Sistema de Integración Unificado
==============================================
Author: Matías Aguirre
Company: Matware

Bus de eventos central que conecta todos los módulos Purma
permitiendo comunicación inteligente entre componentes.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Callable, Any, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import defaultdict
import sqlite3
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("purma.integration")


# ============================================
# Event Types - Taxonomía de Eventos
# ============================================

class EventCategory(Enum):
    """Categorías principales de eventos"""
    SYSTEM = "system"           # Eventos del sistema operativo
    USER = "user"               # Acciones del usuario
    AI = "ai"                   # Eventos de módulos AI
    NOTIFICATION = "notification"  # Notificaciones
    COMMAND = "command"         # Comandos ejecutados
    DATA = "data"               # Cambios de datos


class EventType(Enum):
    """Tipos específicos de eventos"""
    # System Events
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"
    SYSTEM_RESOURCE_ALERT = "system.resource_alert"

    # User Events
    USER_APP_FOCUSED = "user.app_focused"
    USER_APP_LAUNCHED = "user.app_launched"
    USER_APP_CLOSED = "user.app_closed"
    USER_COMMAND_EXECUTED = "user.command_executed"
    USER_FILE_ACCESSED = "user.file_accessed"
    USER_CLIPBOARD_CHANGED = "user.clipboard_changed"
    USER_IDLE = "user.idle"
    USER_ACTIVE = "user.active"

    # AI Module Events
    AI_CHAT_MESSAGE = "ai.chat.message"
    AI_CHAT_RESPONSE = "ai.chat.response"
    AI_CORTEX_PREDICTION = "ai.cortex.prediction"
    AI_CORTEX_PATTERN_LEARNED = "ai.cortex.pattern_learned"
    AI_MEMORY_INDEXED = "ai.memory.indexed"
    AI_MEMORY_SEARCH = "ai.memory.search"
    AI_GHOST_SUGGESTION = "ai.ghost.suggestion"
    AI_GHOST_PATTERN_DETECTED = "ai.ghost.pattern_detected"
    AI_AGENT_TASK_STARTED = "ai.agent.task_started"
    AI_AGENT_TASK_COMPLETED = "ai.agent.task_completed"

    # Module Specific Events
    LENS_CAPTURE = "lens.capture"
    LENS_OCR_COMPLETE = "lens.ocr_complete"
    VAULT_UNLOCKED = "vault.unlocked"
    VAULT_LOCKED = "vault.locked"
    VAULT_SECRET_ACCESSED = "vault.secret_accessed"
    SCRIBE_RECORDING_STARTED = "scribe.recording_started"
    SCRIBE_TRANSCRIPTION_COMPLETE = "scribe.transcription_complete"
    SCRIBE_TTS_COMPLETE = "scribe.tts_complete"
    SPACES_CHANGED = "spaces.changed"
    FLOW_WORKFLOW_STARTED = "flow.workflow_started"
    FLOW_WORKFLOW_COMPLETED = "flow.workflow_completed"
    PULSE_ALERT = "pulse.alert"
    BRIDGE_COMMAND = "bridge.command"

    # Cross-Module Events
    CONTEXT_CHANGED = "context.changed"
    SUGGESTION_GENERATED = "suggestion.generated"
    ACTION_REQUIRED = "action.required"


# ============================================
# Event Structure
# ============================================

@dataclass
class PurmaEvent:
    """Estructura unificada de evento"""
    event_type: str
    source: str                              # Módulo que genera el evento
    data: Dict[str, Any]                     # Datos del evento
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    event_id: str = field(default_factory=lambda: f"evt_{datetime.now().timestamp()}")
    priority: int = 5                        # 1-10, 10 más alta
    requires_response: bool = False          # Si espera respuesta
    correlation_id: Optional[str] = None     # Para rastrear cadenas de eventos
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'PurmaEvent':
        return cls(**data)


# ============================================
# Event Bus - Sistema Central de Mensajería
# ============================================

class PurmaEventBus:
    """
    Bus de eventos central para PurmaLinux.
    Implementa pub/sub con soporte para:
    - Suscripciones por tipo de evento
    - Suscripciones por patrón (wildcards)
    - Priorización de eventos
    - Persistencia de eventos
    - Replay de eventos históricos
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._pattern_subscribers: List[tuple] = []  # (pattern, callback)
        self._event_queue: asyncio.Queue = None
        self._running = False
        self._event_history: List[PurmaEvent] = []
        self._max_history = 1000

        # Persistencia
        self._db_path = Path.home() / ".purma" / "integration" / "events.db"
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

        # Módulos registrados
        self._modules: Dict[str, 'PurmaModule'] = {}

        self._initialized = True
        logger.info("PurmaEventBus inicializado")

    def _init_db(self):
        """Inicializa la base de datos de eventos"""
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                event_id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                source TEXT NOT NULL,
                data TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                priority INTEGER DEFAULT 5,
                correlation_id TEXT,
                tags TEXT
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_event_type ON events(event_type)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp ON events(timestamp)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_source ON events(source)
        """)
        conn.commit()
        conn.close()

    def subscribe(self, event_type: str, callback: Callable[[PurmaEvent], Any]):
        """
        Suscribirse a un tipo de evento específico.

        Args:
            event_type: Tipo de evento (puede usar wildcards como "ai.*")
            callback: Función a llamar cuando ocurra el evento
        """
        if "*" in event_type:
            pattern = event_type.replace(".", r"\.").replace("*", ".*")
            self._pattern_subscribers.append((pattern, callback))
            logger.debug(f"Suscripción por patrón: {event_type}")
        else:
            self._subscribers[event_type].append(callback)
            logger.debug(f"Suscripción: {event_type}")

    def unsubscribe(self, event_type: str, callback: Callable):
        """Desuscribirse de un evento"""
        if "*" in event_type:
            pattern = event_type.replace(".", r"\.").replace("*", ".*")
            self._pattern_subscribers = [
                (p, c) for p, c in self._pattern_subscribers
                if not (p == pattern and c == callback)
            ]
        elif callback in self._subscribers[event_type]:
            self._subscribers[event_type].remove(callback)

    async def publish(self, event: PurmaEvent, persist: bool = True):
        """
        Publicar un evento en el bus.

        Args:
            event: Evento a publicar
            persist: Si debe guardarse en la base de datos
        """
        logger.info(f"Evento publicado: {event.event_type} desde {event.source}")

        # Guardar en historial
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)

        # Persistir si es necesario
        if persist:
            self._persist_event(event)

        # Notificar suscriptores directos
        for callback in self._subscribers.get(event.event_type, []):
            try:
                result = callback(event)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error(f"Error en callback para {event.event_type}: {e}")

        # Notificar suscriptores por patrón
        import re
        for pattern, callback in self._pattern_subscribers:
            if re.match(pattern, event.event_type):
                try:
                    result = callback(event)
                    if asyncio.iscoroutine(result):
                        await result
                except Exception as e:
                    logger.error(f"Error en pattern callback: {e}")

    def publish_sync(self, event: PurmaEvent, persist: bool = True):
        """Publicar evento de forma síncrona"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self.publish(event, persist))
            else:
                loop.run_until_complete(self.publish(event, persist))
        except RuntimeError:
            # No hay loop, crear uno nuevo
            asyncio.run(self.publish(event, persist))

    def _persist_event(self, event: PurmaEvent):
        """Guardar evento en la base de datos"""
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO events
            (event_id, event_type, source, data, timestamp, priority, correlation_id, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event.event_id,
            event.event_type,
            event.source,
            json.dumps(event.data),
            event.timestamp,
            event.priority,
            event.correlation_id,
            json.dumps(event.tags)
        ))
        conn.commit()
        conn.close()

    def query_events(
        self,
        event_type: str = None,
        source: str = None,
        since: str = None,
        limit: int = 100
    ) -> List[PurmaEvent]:
        """Consultar eventos históricos"""
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()

        query = "SELECT * FROM events WHERE 1=1"
        params = []

        if event_type:
            if "*" in event_type:
                query += " AND event_type LIKE ?"
                params.append(event_type.replace("*", "%"))
            else:
                query += " AND event_type = ?"
                params.append(event_type)

        if source:
            query += " AND source = ?"
            params.append(source)

        if since:
            query += " AND timestamp >= ?"
            params.append(since)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        events = []
        for row in rows:
            events.append(PurmaEvent(
                event_id=row[0],
                event_type=row[1],
                source=row[2],
                data=json.loads(row[3]),
                timestamp=row[4],
                priority=row[5],
                correlation_id=row[6],
                tags=json.loads(row[7]) if row[7] else []
            ))

        return events

    def register_module(self, module: 'PurmaModule'):
        """Registrar un módulo en el sistema"""
        self._modules[module.name] = module
        logger.info(f"Módulo registrado: {module.name}")

    def get_module(self, name: str) -> Optional['PurmaModule']:
        """Obtener un módulo registrado"""
        return self._modules.get(name)

    def get_all_modules(self) -> Dict[str, 'PurmaModule']:
        """Obtener todos los módulos registrados"""
        return self._modules.copy()


# ============================================
# Base Module - Clase Base para Módulos
# ============================================

class PurmaModule:
    """
    Clase base para todos los módulos de PurmaLinux.
    Proporciona integración automática con el EventBus.
    """

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.bus = PurmaEventBus()
        self._subscriptions: List[tuple] = []

        # Registrar en el bus
        self.bus.register_module(self)

    def emit(
        self,
        event_type: str,
        data: Dict[str, Any],
        priority: int = 5,
        requires_response: bool = False,
        correlation_id: str = None,
        tags: List[str] = None
    ):
        """Emitir un evento desde este módulo"""
        event = PurmaEvent(
            event_type=event_type,
            source=self.name,
            data=data,
            priority=priority,
            requires_response=requires_response,
            correlation_id=correlation_id,
            tags=tags or []
        )
        self.bus.publish_sync(event)
        return event

    async def emit_async(
        self,
        event_type: str,
        data: Dict[str, Any],
        **kwargs
    ):
        """Emitir un evento de forma asíncrona"""
        event = PurmaEvent(
            event_type=event_type,
            source=self.name,
            data=data,
            **kwargs
        )
        await self.bus.publish(event)
        return event

    def on(self, event_type: str, callback: Callable):
        """Suscribirse a un tipo de evento"""
        self.bus.subscribe(event_type, callback)
        self._subscriptions.append((event_type, callback))

    def off(self, event_type: str, callback: Callable):
        """Desuscribirse de un evento"""
        self.bus.unsubscribe(event_type, callback)
        self._subscriptions = [
            (e, c) for e, c in self._subscriptions
            if not (e == event_type and c == callback)
        ]

    def get_status(self) -> Dict[str, Any]:
        """Obtener estado del módulo (override en subclases)"""
        return {
            "name": self.name,
            "description": self.description,
            "active": True
        }

    def shutdown(self):
        """Limpiar suscripciones al cerrar"""
        for event_type, callback in self._subscriptions:
            self.bus.unsubscribe(event_type, callback)
        self._subscriptions.clear()


# ============================================
# Context Manager - Gestor de Contexto Global
# ============================================

class PurmaContext:
    """
    Gestor de contexto global que mantiene el estado
    actual del sistema y del usuario.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.bus = PurmaEventBus()

        # Estado actual
        self._context = {
            "current_app": None,
            "current_workspace": 1,
            "current_space": "default",
            "user_state": "active",  # active, idle, away
            "recent_apps": [],
            "recent_files": [],
            "recent_commands": [],
            "clipboard_content": None,
            "system_load": {},
            "ai_suggestions": [],
            "active_workflows": [],
            "vault_unlocked": False,
            "recording_active": False,
        }

        # Suscribirse a eventos relevantes
        self._setup_listeners()

        self._initialized = True
        logger.info("PurmaContext inicializado")

    def _setup_listeners(self):
        """Configurar listeners para actualizar contexto"""

        # Escuchar cambios de app
        self.bus.subscribe(EventType.USER_APP_FOCUSED.value, self._on_app_focused)
        self.bus.subscribe(EventType.USER_COMMAND_EXECUTED.value, self._on_command)
        self.bus.subscribe(EventType.USER_FILE_ACCESSED.value, self._on_file_accessed)
        self.bus.subscribe(EventType.USER_CLIPBOARD_CHANGED.value, self._on_clipboard)
        self.bus.subscribe(EventType.SPACES_CHANGED.value, self._on_space_changed)
        self.bus.subscribe(EventType.VAULT_UNLOCKED.value, self._on_vault_unlocked)
        self.bus.subscribe(EventType.VAULT_LOCKED.value, self._on_vault_locked)
        self.bus.subscribe(EventType.SCRIBE_RECORDING_STARTED.value, self._on_recording_start)
        self.bus.subscribe(EventType.SCRIBE_TRANSCRIPTION_COMPLETE.value, self._on_recording_stop)
        self.bus.subscribe("ai.*", self._on_ai_event)

    def _on_app_focused(self, event: PurmaEvent):
        app = event.data.get("app")
        if app:
            self._context["current_app"] = app
            recent = self._context["recent_apps"]
            if app in recent:
                recent.remove(app)
            recent.insert(0, app)
            self._context["recent_apps"] = recent[:20]

    def _on_command(self, event: PurmaEvent):
        cmd = event.data.get("command")
        if cmd:
            recent = self._context["recent_commands"]
            recent.insert(0, {"command": cmd, "timestamp": event.timestamp})
            self._context["recent_commands"] = recent[:50]

    def _on_file_accessed(self, event: PurmaEvent):
        path = event.data.get("path")
        if path:
            recent = self._context["recent_files"]
            if path in recent:
                recent.remove(path)
            recent.insert(0, path)
            self._context["recent_files"] = recent[:30]

    def _on_clipboard(self, event: PurmaEvent):
        self._context["clipboard_content"] = event.data.get("content")

    def _on_space_changed(self, event: PurmaEvent):
        self._context["current_space"] = event.data.get("space", "default")

    def _on_vault_unlocked(self, event: PurmaEvent):
        self._context["vault_unlocked"] = True

    def _on_vault_locked(self, event: PurmaEvent):
        self._context["vault_unlocked"] = False

    def _on_recording_start(self, event: PurmaEvent):
        self._context["recording_active"] = True

    def _on_recording_stop(self, event: PurmaEvent):
        self._context["recording_active"] = False

    def _on_ai_event(self, event: PurmaEvent):
        if "suggestion" in event.event_type:
            suggestions = self._context["ai_suggestions"]
            suggestions.insert(0, {
                "source": event.source,
                "data": event.data,
                "timestamp": event.timestamp
            })
            self._context["ai_suggestions"] = suggestions[:20]

    def get(self, key: str, default: Any = None) -> Any:
        """Obtener valor del contexto"""
        return self._context.get(key, default)

    def set(self, key: str, value: Any):
        """Establecer valor en el contexto"""
        old_value = self._context.get(key)
        self._context[key] = value

        # Emitir evento de cambio de contexto
        if old_value != value:
            self.bus.publish_sync(PurmaEvent(
                event_type=EventType.CONTEXT_CHANGED.value,
                source="context",
                data={
                    "key": key,
                    "old_value": old_value,
                    "new_value": value
                }
            ))

    def get_full_context(self) -> Dict[str, Any]:
        """Obtener todo el contexto actual"""
        return self._context.copy()

    def get_context_summary(self) -> str:
        """Obtener resumen del contexto para AI"""
        ctx = self._context
        lines = [
            f"App actual: {ctx['current_app'] or 'ninguna'}",
            f"Espacio: {ctx['current_space']}",
            f"Estado: {ctx['user_state']}",
            f"Apps recientes: {', '.join(ctx['recent_apps'][:5]) or 'ninguna'}",
            f"Vault: {'desbloqueado' if ctx['vault_unlocked'] else 'bloqueado'}",
        ]
        if ctx['ai_suggestions']:
            lines.append(f"Sugerencias pendientes: {len(ctx['ai_suggestions'])}")
        return "\n".join(lines)


# ============================================
# Intelligence Router - Enrutador Inteligente
# ============================================

class PurmaIntelligenceRouter:
    """
    Enrutador inteligente que decide qué módulo debe
    manejar una petición basándose en el contexto.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.bus = PurmaEventBus()
        self.context = PurmaContext()

        # Patrones de routing
        self._routes = {
            # Palabras clave -> módulo destino
            "password": "vault",
            "contraseña": "vault",
            "secret": "vault",
            "credencial": "vault",

            "captura": "lens",
            "screenshot": "lens",
            "ocr": "lens",
            "imagen": "lens",

            "grabar": "scribe",
            "transcribir": "scribe",
            "voz": "scribe",
            "dictar": "scribe",

            "sistema": "pulse",
            "cpu": "pulse",
            "memoria": "pulse",
            "proceso": "pulse",

            "terminal": "bridge",
            "comando": "bridge",
            "ejecutar": "bridge",

            "workflow": "flow",
            "automatizar": "flow",
            "macro": "flow",

            "espacio": "spaces",
            "workspace": "spaces",
            "contexto": "spaces",

            "predecir": "cortex",
            "patrón": "cortex",
            "aprender": "cortex",

            "buscar archivo": "memory",
            "encontrar": "memory",
            "recordar": "memory",
            "rag": "memory",

            "sugerencia": "ghost",
            "automatización": "ghost",
            "optimizar": "ghost",

            "agente": "agents",
            "investigar": "agents",
            "analizar": "agents",
            "código": "agents",
        }

        self._initialized = True

    def route(self, query: str) -> tuple[str, float]:
        """
        Determinar qué módulo debe manejar una consulta.

        Returns:
            tuple: (nombre_modulo, confianza)
        """
        query_lower = query.lower()

        # Buscar coincidencias en rutas
        matches = []
        for keyword, module in self._routes.items():
            if keyword in query_lower:
                matches.append((module, len(keyword) / len(query_lower)))

        if matches:
            # Ordenar por confianza y tomar el mejor
            matches.sort(key=lambda x: x[1], reverse=True)
            return matches[0]

        # Contexto actual puede influir
        ctx = self.context.get_full_context()
        current_app = ctx.get("current_app", "").lower()

        # Si está en terminal, probablemente quiera Bridge
        if "terminal" in current_app or "kitty" in current_app:
            return ("bridge", 0.3)

        # Si está en editor, probablemente quiera code agent
        if any(x in current_app for x in ["code", "vim", "nvim", "emacs"]):
            return ("agents", 0.3)

        # Default: chat general
        return ("chat", 0.1)

    async def smart_query(self, query: str, context: Dict = None) -> Dict[str, Any]:
        """
        Procesar una consulta inteligentemente, delegando
        al módulo apropiado.
        """
        module_name, confidence = self.route(query)
        module = self.bus.get_module(module_name)

        result = {
            "routed_to": module_name,
            "confidence": confidence,
            "context_used": context or self.context.get_full_context()
        }

        if module and hasattr(module, 'process_query'):
            result["response"] = await module.process_query(query, context)
        else:
            result["response"] = f"Consulta dirigida a {module_name} (módulo no disponible)"

        return result


# ============================================
# Workflow Orchestrator - Orquestador de Flujos
# ============================================

class PurmaWorkflowOrchestrator:
    """
    Orquestador que coordina flujos de trabajo complejos
    entre múltiples módulos.
    """

    def __init__(self):
        self.bus = PurmaEventBus()
        self.context = PurmaContext()

        # Workflows predefinidos
        self._workflows = {
            "morning_routine": self._workflow_morning,
            "focus_mode": self._workflow_focus,
            "research_task": self._workflow_research,
            "code_review": self._workflow_code_review,
            "capture_and_analyze": self._workflow_capture_analyze,
            "voice_command": self._workflow_voice_command,
        }

    async def execute(self, workflow_name: str, params: Dict = None) -> Dict:
        """Ejecutar un workflow predefinido"""
        if workflow_name not in self._workflows:
            return {"error": f"Workflow '{workflow_name}' no encontrado"}

        # Notificar inicio
        self.bus.publish_sync(PurmaEvent(
            event_type=EventType.FLOW_WORKFLOW_STARTED.value,
            source="orchestrator",
            data={"workflow": workflow_name, "params": params}
        ))

        try:
            result = await self._workflows[workflow_name](params or {})

            # Notificar completado
            self.bus.publish_sync(PurmaEvent(
                event_type=EventType.FLOW_WORKFLOW_COMPLETED.value,
                source="orchestrator",
                data={"workflow": workflow_name, "result": result}
            ))

            return result
        except Exception as e:
            logger.error(f"Error en workflow {workflow_name}: {e}")
            return {"error": str(e)}

    async def _workflow_morning(self, params: Dict) -> Dict:
        """
        Rutina matutina:
        1. Cortex predice apps necesarias
        2. Memory busca notas recientes
        3. Pulse muestra estado del sistema
        """
        results = {}

        # Obtener predicciones de Cortex
        cortex = self.bus.get_module("cortex")
        if cortex:
            results["predictions"] = cortex.predict()

        # Buscar notas de ayer
        memory = self.bus.get_module("memory")
        if memory:
            results["recent_notes"] = await memory.search("modified:yesterday")

        # Estado del sistema
        pulse = self.bus.get_module("pulse")
        if pulse:
            results["system_status"] = pulse.get_status()

        return results

    async def _workflow_focus(self, params: Dict) -> Dict:
        """
        Modo focus:
        1. Cambiar a espacio de focus
        2. Activar DND
        3. Preparar apps de trabajo
        """
        duration = params.get("duration", 25)  # Pomodoro default

        # Cambiar espacio
        spaces = self.bus.get_module("spaces")
        if spaces:
            spaces.activate_space("focus")

        # Cortex prepara apps de focus
        cortex = self.bus.get_module("cortex")
        if cortex:
            cortex.prepare_for_context("focus")

        return {
            "mode": "focus",
            "duration": duration,
            "started": datetime.now().isoformat()
        }

    async def _workflow_research(self, params: Dict) -> Dict:
        """
        Investigación:
        1. Agents investiga el tema
        2. Memory indexa resultados
        3. Ghost observa para futuras automatizaciones
        """
        topic = params.get("topic", "")

        # Iniciar investigación con agents
        agents = self.bus.get_module("agents")
        if agents:
            research_result = await agents.run({
                "description": f"Investigar: {topic}",
                "agents": ["researcher", "analyzer"]
            })
        else:
            research_result = {"error": "Agents no disponible"}

        # Indexar en memory
        memory = self.bus.get_module("memory")
        if memory and "content" in research_result:
            await memory.index_content(
                content=research_result["content"],
                metadata={"type": "research", "topic": topic}
            )

        return research_result

    async def _workflow_code_review(self, params: Dict) -> Dict:
        """
        Code review:
        1. Coder analiza el código
        2. Reviewer da feedback
        3. Se generan sugerencias
        """
        file_path = params.get("file")

        agents = self.bus.get_module("agents")
        if not agents:
            return {"error": "Agents no disponible"}

        # Análisis y review
        result = await agents.run({
            "description": f"Revisar código en {file_path}",
            "agents": ["coder", "reviewer"]
        })

        return result

    async def _workflow_capture_analyze(self, params: Dict) -> Dict:
        """
        Captura y análisis:
        1. Lens captura pantalla
        2. OCR extrae texto
        3. Memory indexa
        4. Agents analiza si necesario
        """
        lens = self.bus.get_module("lens")
        if not lens:
            return {"error": "Lens no disponible"}

        # Capturar
        capture = await lens.capture(params.get("mode", "screen"))

        # OCR
        if capture.get("path"):
            ocr_result = await lens.ocr(capture["path"])

        # Indexar en memory
        memory = self.bus.get_module("memory")
        if memory and ocr_result.get("text"):
            await memory.index_content(
                content=ocr_result["text"],
                metadata={"type": "ocr", "source": capture["path"]}
            )

        return {
            "capture": capture,
            "ocr": ocr_result
        }

    async def _workflow_voice_command(self, params: Dict) -> Dict:
        """
        Comando de voz:
        1. Scribe graba y transcribe
        2. Router determina intención
        3. Se ejecuta el comando apropiado
        """
        duration = params.get("duration", 5)

        scribe = self.bus.get_module("scribe")
        if not scribe:
            return {"error": "Scribe no disponible"}

        # Grabar y transcribir
        recording = await scribe.quick_record(duration)
        if not recording.get("transcription"):
            return {"error": "No se pudo transcribir"}

        # Enrutar comando
        router = PurmaIntelligenceRouter()
        result = await router.smart_query(recording["transcription"])

        return {
            "transcription": recording["transcription"],
            "routed_to": result["routed_to"],
            "response": result["response"]
        }


# ============================================
# API Integration - Funciones de Integración
# ============================================

def get_event_bus() -> PurmaEventBus:
    """Obtener instancia del event bus"""
    return PurmaEventBus()

def get_context() -> PurmaContext:
    """Obtener instancia del contexto"""
    return PurmaContext()

def get_router() -> PurmaIntelligenceRouter:
    """Obtener instancia del router"""
    return PurmaIntelligenceRouter()

def get_orchestrator() -> PurmaWorkflowOrchestrator:
    """Obtener instancia del orquestador"""
    return PurmaWorkflowOrchestrator()


# ============================================
# Integration Helpers
# ============================================

async def emit_event(
    event_type: str,
    source: str,
    data: Dict[str, Any],
    **kwargs
):
    """Helper para emitir eventos rápidamente"""
    bus = get_event_bus()
    event = PurmaEvent(
        event_type=event_type,
        source=source,
        data=data,
        **kwargs
    )
    await bus.publish(event)

def emit_event_sync(
    event_type: str,
    source: str,
    data: Dict[str, Any],
    **kwargs
):
    """Helper síncrono para emitir eventos"""
    bus = get_event_bus()
    event = PurmaEvent(
        event_type=event_type,
        source=source,
        data=data,
        **kwargs
    )
    bus.publish_sync(event)


# ============================================
# Singleton instances
# ============================================

event_bus = PurmaEventBus()
context = PurmaContext()
router = PurmaIntelligenceRouter()
orchestrator = PurmaWorkflowOrchestrator()
