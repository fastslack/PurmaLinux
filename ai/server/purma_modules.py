"""
PurmaLinux - Module Adapters
=============================
Author: Matías Aguirre
Company: Matware

Adaptadores que conectan cada módulo existente con el sistema de integración.
Cada adaptador envuelve un módulo y lo hace reactivo a través del EventBus.
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from pathlib import Path

from purma_integration import (
    PurmaModule, PurmaEvent, EventType,
    get_event_bus, get_context
)

logger = logging.getLogger("purma.modules")


# ============================================
# Chat Module Adapter
# ============================================

class ChatModule(PurmaModule):
    """Adaptador para el módulo de chat principal"""

    def __init__(self):
        super().__init__(
            name="chat",
            description="Chat AI principal con Ollama"
        )

        # Suscribirse a eventos relevantes
        self.on(EventType.USER_COMMAND_EXECUTED.value, self._on_command)
        self.on(EventType.CONTEXT_CHANGED.value, self._on_context_change)

    def _on_command(self, event: PurmaEvent):
        """Procesar comandos que podrían necesitar respuesta AI"""
        cmd = event.data.get("command", "")
        if cmd.startswith("purma ") or cmd.startswith("ai "):
            # Podría activar una respuesta del chat
            pass

    def _on_context_change(self, event: PurmaEvent):
        """Ajustar comportamiento según contexto"""
        pass

    async def process_query(self, query: str, context: Dict = None) -> Dict:
        """Procesar una consulta de chat"""
        # Emitir evento de mensaje
        self.emit(
            event_type=EventType.AI_CHAT_MESSAGE.value,
            data={"query": query, "context": context}
        )

        # Aquí iría la lógica real del chat
        # Por ahora retornamos placeholder
        response = {"response": f"Chat procesando: {query}"}

        # Emitir evento de respuesta
        self.emit(
            event_type=EventType.AI_CHAT_RESPONSE.value,
            data=response
        )

        return response


# ============================================
# Lens Module Adapter
# ============================================

class LensModule(PurmaModule):
    """Adaptador para Purma Lens (screenshots + OCR)"""

    def __init__(self):
        super().__init__(
            name="lens",
            description="Captura de pantalla con OCR y análisis visual"
        )

        self._lens_engine = None

    def _get_engine(self):
        if self._lens_engine is None:
            try:
                from purma_lens import get_lens_engine
                self._lens_engine = get_lens_engine()
            except ImportError:
                logger.warning("purma_lens no disponible")
        return self._lens_engine

    async def capture(self, mode: str = "screen") -> Dict:
        """Capturar pantalla"""
        engine = self._get_engine()
        if not engine:
            return {"error": "Lens no disponible"}

        result = await engine.capture(mode)

        # Emitir evento
        self.emit(
            event_type=EventType.LENS_CAPTURE.value,
            data={"mode": mode, "result": result}
        )

        return result

    async def ocr(self, image_path: str) -> Dict:
        """Extraer texto de imagen"""
        engine = self._get_engine()
        if not engine:
            return {"error": "Lens no disponible"}

        result = await engine.ocr(image_path)

        # Emitir evento
        self.emit(
            event_type=EventType.LENS_OCR_COMPLETE.value,
            data={"path": image_path, "text": result.get("text", "")}
        )

        return result

    async def process_query(self, query: str, context: Dict = None) -> Dict:
        """Procesar consulta de Lens"""
        if "captura" in query.lower() or "screenshot" in query.lower():
            return await self.capture()
        elif "ocr" in query.lower() or "texto" in query.lower():
            path = context.get("image_path") if context else None
            if path:
                return await self.ocr(path)
        return {"info": "Usa 'capturar' o 'ocr' con una imagen"}


# ============================================
# Vault Module Adapter
# ============================================

class VaultModule(PurmaModule):
    """Adaptador para Purma Vault (password manager)"""

    def __init__(self):
        super().__init__(
            name="vault",
            description="Gestor de contraseñas cifrado"
        )

        self._vault_engine = None

    def _get_engine(self):
        if self._vault_engine is None:
            try:
                from purma_vault import get_vault_engine
                self._vault_engine = get_vault_engine()
            except ImportError:
                logger.warning("purma_vault no disponible")
        return self._vault_engine

    def unlock(self, master_password: str) -> Dict:
        """Desbloquear vault"""
        engine = self._get_engine()
        if not engine:
            return {"error": "Vault no disponible"}

        result = engine.unlock(master_password)

        if result.get("success"):
            self.emit(
                event_type=EventType.VAULT_UNLOCKED.value,
                data={"timestamp": result.get("timestamp")}
            )

        return result

    def lock(self) -> Dict:
        """Bloquear vault"""
        engine = self._get_engine()
        if not engine:
            return {"error": "Vault no disponible"}

        result = engine.lock()

        self.emit(
            event_type=EventType.VAULT_LOCKED.value,
            data={}
        )

        return result

    def get_secret(self, secret_id: str) -> Dict:
        """Obtener secreto (emite evento de auditoría)"""
        engine = self._get_engine()
        if not engine:
            return {"error": "Vault no disponible"}

        result = engine.get_secret(secret_id)

        # Evento de auditoría
        self.emit(
            event_type=EventType.VAULT_SECRET_ACCESSED.value,
            data={"secret_id": secret_id},
            tags=["security", "audit"]
        )

        return result

    async def process_query(self, query: str, context: Dict = None) -> Dict:
        """Procesar consulta de Vault"""
        engine = self._get_engine()
        if not engine:
            return {"error": "Vault no disponible"}

        # Búsqueda AI
        return engine.ai_search(query)


# ============================================
# Scribe Module Adapter
# ============================================

class ScribeModule(PurmaModule):
    """Adaptador para Purma Scribe (voz)"""

    def __init__(self):
        super().__init__(
            name="scribe",
            description="Asistente de voz con STT y TTS"
        )

        self._scribe_engine = None

    def _get_engine(self):
        if self._scribe_engine is None:
            try:
                from purma_scribe import get_scribe_engine
                self._scribe_engine = get_scribe_engine()
            except ImportError:
                logger.warning("purma_scribe no disponible")
        return self._scribe_engine

    async def quick_record(self, duration: int = 5) -> Dict:
        """Grabar y transcribir rápidamente"""
        engine = self._get_engine()
        if not engine:
            return {"error": "Scribe no disponible"}

        # Emitir inicio de grabación
        self.emit(
            event_type=EventType.SCRIBE_RECORDING_STARTED.value,
            data={"duration": duration}
        )

        result = await engine.quick_record(duration)

        # Emitir transcripción completada
        self.emit(
            event_type=EventType.SCRIBE_TRANSCRIPTION_COMPLETE.value,
            data={
                "transcription": result.get("transcription", ""),
                "duration": duration
            }
        )

        return result

    async def speak(self, text: str) -> Dict:
        """Text to speech"""
        engine = self._get_engine()
        if not engine:
            return {"error": "Scribe no disponible"}

        result = await engine.speak(text)

        self.emit(
            event_type=EventType.SCRIBE_TTS_COMPLETE.value,
            data={"text": text}
        )

        return result

    async def process_query(self, query: str, context: Dict = None) -> Dict:
        """Procesar consulta de Scribe"""
        if "grabar" in query.lower() or "escucha" in query.lower():
            return await self.quick_record()
        elif "habla" in query.lower() or "di " in query.lower():
            text = query.replace("habla", "").replace("di ", "").strip()
            return await self.speak(text)
        return {"info": "Usa 'grabar' o 'habla [texto]'"}


# ============================================
# Cortex Module Adapter
# ============================================

class CortexModule(PurmaModule):
    """Adaptador para Purma Cortex (predicción)"""

    def __init__(self):
        super().__init__(
            name="cortex",
            description="Motor predictivo AI"
        )

        self._cortex_engine = None

        # Suscribirse a eventos de apps para aprender
        self.on(EventType.USER_APP_FOCUSED.value, self._on_app_focused)
        self.on(EventType.USER_APP_LAUNCHED.value, self._on_app_launched)

    def _get_engine(self):
        if self._cortex_engine is None:
            try:
                from purma_cortex import get_cortex_engine
                self._cortex_engine = get_cortex_engine()
            except ImportError:
                logger.warning("purma_cortex no disponible")
        return self._cortex_engine

    def _on_app_focused(self, event: PurmaEvent):
        """Aprender de cambios de app"""
        engine = self._get_engine()
        if engine and engine.is_learning:
            app = event.data.get("app")
            if app:
                engine.tracker.track_app(app)

    def _on_app_launched(self, event: PurmaEvent):
        """Aprender de lanzamientos de app"""
        engine = self._get_engine()
        if engine and engine.is_learning:
            app = event.data.get("app")
            if app:
                engine.tracker.track_app(app)

    def predict(self, current_app: str = None) -> Dict:
        """Obtener predicciones"""
        engine = self._get_engine()
        if not engine:
            return {"error": "Cortex no disponible"}

        result = engine.predict(current_app)

        # Emitir predicción
        self.emit(
            event_type=EventType.AI_CORTEX_PREDICTION.value,
            data=result
        )

        return result

    def start_learning(self) -> Dict:
        """Iniciar aprendizaje"""
        engine = self._get_engine()
        if not engine:
            return {"error": "Cortex no disponible"}
        return engine.start_learning()

    def stop_learning(self) -> Dict:
        """Detener aprendizaje"""
        engine = self._get_engine()
        if not engine:
            return {"error": "Cortex no disponible"}
        return engine.stop_learning()

    def prepare_for_context(self, context_name: str) -> Dict:
        """Pre-cargar apps para un contexto"""
        engine = self._get_engine()
        if not engine:
            return {"error": "Cortex no disponible"}

        # Obtener predicciones y preparar
        predictions = engine.predict()
        return {"context": context_name, "predictions": predictions}

    async def process_query(self, query: str, context: Dict = None) -> Dict:
        """Procesar consulta de Cortex"""
        if "predecir" in query.lower() or "siguiente" in query.lower():
            return self.predict()
        elif "aprender" in query.lower() or "iniciar" in query.lower():
            return self.start_learning()
        return self.predict()


# ============================================
# Memory Module Adapter
# ============================================

class MemoryModule(PurmaModule):
    """Adaptador para Purma Memory (RAG)"""

    def __init__(self):
        super().__init__(
            name="memory",
            description="Sistema RAG de búsqueda semántica"
        )

        self._memory_engine = None

        # Escuchar archivos accedidos para indexar
        self.on(EventType.USER_FILE_ACCESSED.value, self._on_file_accessed)

    def _get_engine(self):
        if self._memory_engine is None:
            try:
                from purma_memory import get_memory_engine
                self._memory_engine = get_memory_engine()
            except ImportError:
                logger.warning("purma_memory no disponible")
        return self._memory_engine

    def _on_file_accessed(self, event: PurmaEvent):
        """Indexar archivos accedidos automáticamente"""
        engine = self._get_engine()
        if engine:
            path = event.data.get("path")
            if path:
                # Indexar en background
                asyncio.create_task(engine.index_file(path))

    async def search(self, query: str, mode: str = "hybrid") -> Dict:
        """Buscar en memoria"""
        engine = self._get_engine()
        if not engine:
            return {"error": "Memory no disponible"}

        result = await engine.search(query, mode)

        # Emitir evento de búsqueda
        self.emit(
            event_type=EventType.AI_MEMORY_SEARCH.value,
            data={"query": query, "results_count": len(result.get("results", []))}
        )

        return result

    async def ask(self, question: str) -> Dict:
        """Preguntar con RAG"""
        engine = self._get_engine()
        if not engine:
            return {"error": "Memory no disponible"}
        return await engine.ask(question)

    async def index_content(self, content: str, metadata: Dict = None) -> Dict:
        """Indexar contenido directamente"""
        engine = self._get_engine()
        if not engine:
            return {"error": "Memory no disponible"}

        # Crear archivo temporal e indexar
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(content)
            temp_path = f.name

        result = await engine.index_file(temp_path, metadata=metadata)

        self.emit(
            event_type=EventType.AI_MEMORY_INDEXED.value,
            data={"content_length": len(content), "metadata": metadata}
        )

        return result

    async def process_query(self, query: str, context: Dict = None) -> Dict:
        """Procesar consulta de Memory"""
        return await self.ask(query)


# ============================================
# Ghost Module Adapter
# ============================================

class GhostModule(PurmaModule):
    """Adaptador para Purma Ghost (observador)"""

    def __init__(self):
        super().__init__(
            name="ghost",
            description="AI sombra que sugiere automatizaciones"
        )

        self._ghost_engine = None

        # Escuchar comandos para observar
        self.on(EventType.USER_COMMAND_EXECUTED.value, self._on_command)
        self.on(EventType.USER_CLIPBOARD_CHANGED.value, self._on_clipboard)

    def _get_engine(self):
        if self._ghost_engine is None:
            try:
                from purma_ghost import get_ghost_engine
                self._ghost_engine = get_ghost_engine()
            except ImportError:
                logger.warning("purma_ghost no disponible")
        return self._ghost_engine

    def _on_command(self, event: PurmaEvent):
        """Observar comandos ejecutados"""
        engine = self._get_engine()
        if engine and engine.is_observing:
            cmd = event.data.get("command")
            if cmd:
                engine.observer.observe_command(cmd)

    def _on_clipboard(self, event: PurmaEvent):
        """Observar cambios de clipboard"""
        engine = self._get_engine()
        if engine and engine.is_observing:
            content = event.data.get("content")
            if content:
                engine.observer.observe_clipboard(content)

    def get_suggestions(self, limit: int = 10) -> list:
        """Obtener sugerencias pendientes"""
        engine = self._get_engine()
        if not engine:
            return []

        suggestions = engine.get_suggestions(limit)

        # Emitir evento si hay nuevas sugerencias
        if suggestions:
            self.emit(
                event_type=EventType.AI_GHOST_SUGGESTION.value,
                data={"count": len(suggestions)}
            )

        return suggestions

    def start(self) -> Dict:
        """Iniciar observación"""
        engine = self._get_engine()
        if not engine:
            return {"error": "Ghost no disponible"}
        return engine.start()

    def stop(self) -> Dict:
        """Detener observación"""
        engine = self._get_engine()
        if not engine:
            return {"error": "Ghost no disponible"}
        return engine.stop()

    async def process_query(self, query: str, context: Dict = None) -> Dict:
        """Procesar consulta de Ghost"""
        suggestions = self.get_suggestions()
        return {"suggestions": suggestions}


# ============================================
# Agents Module Adapter
# ============================================

class AgentsModule(PurmaModule):
    """Adaptador para Purma Multi-Agent"""

    def __init__(self):
        super().__init__(
            name="agents",
            description="Sistema de agentes AI especializados"
        )

        self._agent_engine = None

    def _get_engine(self):
        if self._agent_engine is None:
            try:
                from purma_agents import get_agent_engine
                self._agent_engine = get_agent_engine()
            except ImportError:
                logger.warning("purma_agents no disponible")
        return self._agent_engine

    async def run(self, task: Dict) -> Dict:
        """Ejecutar tarea multi-agente"""
        engine = self._get_engine()
        if not engine:
            return {"error": "Agents no disponible"}

        description = task.get("description", "")
        context = task.get("context", {})

        # Emitir inicio
        self.emit(
            event_type=EventType.AI_AGENT_TASK_STARTED.value,
            data={"description": description}
        )

        result = await engine.run(description, context)

        # Emitir completado
        self.emit(
            event_type=EventType.AI_AGENT_TASK_COMPLETED.value,
            data={"description": description, "success": "error" not in result}
        )

        return result

    def get_agents(self) -> list:
        """Obtener lista de agentes"""
        engine = self._get_engine()
        if not engine:
            return []
        return engine.get_agents()

    async def process_query(self, query: str, context: Dict = None) -> Dict:
        """Procesar consulta para agents"""
        return await self.run({
            "description": query,
            "context": context or {}
        })


# ============================================
# Spaces Module Adapter
# ============================================

class SpacesModule(PurmaModule):
    """Adaptador para Purma Spaces"""

    def __init__(self):
        super().__init__(
            name="spaces",
            description="Gestión de espacios de trabajo contextuales"
        )

        self._current_space = "default"
        self._spaces = {
            "default": {"apps": [], "icon": "🏠"},
            "work": {"apps": ["slack", "teams", "outlook"], "icon": "💼"},
            "code": {"apps": ["vscode", "terminal", "browser"], "icon": "💻"},
            "focus": {"apps": ["minimal", "music"], "icon": "🎯"},
            "gaming": {"apps": ["steam", "discord"], "icon": "🎮"},
        }

    def activate_space(self, space_name: str) -> Dict:
        """Activar un espacio"""
        if space_name not in self._spaces:
            return {"error": f"Espacio '{space_name}' no existe"}

        old_space = self._current_space
        self._current_space = space_name

        # Emitir evento
        self.emit(
            event_type=EventType.SPACES_CHANGED.value,
            data={
                "previous": old_space,
                "current": space_name,
                "apps": self._spaces[space_name]["apps"]
            }
        )

        # Actualizar contexto global
        context = get_context()
        context.set("current_space", space_name)

        return {
            "success": True,
            "space": space_name,
            "apps": self._spaces[space_name]["apps"]
        }

    def get_current_space(self) -> Dict:
        """Obtener espacio actual"""
        return {
            "name": self._current_space,
            **self._spaces[self._current_space]
        }

    def list_spaces(self) -> Dict:
        """Listar espacios disponibles"""
        return {
            "current": self._current_space,
            "spaces": self._spaces
        }

    async def process_query(self, query: str, context: Dict = None) -> Dict:
        """Procesar consulta de Spaces"""
        query_lower = query.lower()

        for space_name in self._spaces:
            if space_name in query_lower:
                return self.activate_space(space_name)

        return self.list_spaces()


# ============================================
# Pulse Module Adapter
# ============================================

class PulseModule(PurmaModule):
    """Adaptador para Purma Pulse (monitor)"""

    def __init__(self):
        super().__init__(
            name="pulse",
            description="Monitor de sistema con análisis AI"
        )

    def get_status(self) -> Dict:
        """Obtener estado del sistema"""
        try:
            import psutil

            status = {
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "memory": {
                    "total": psutil.virtual_memory().total,
                    "available": psutil.virtual_memory().available,
                    "percent": psutil.virtual_memory().percent
                },
                "disk": {
                    "total": psutil.disk_usage('/').total,
                    "free": psutil.disk_usage('/').free,
                    "percent": psutil.disk_usage('/').percent
                }
            }

            # Alertar si hay problemas
            if status["cpu_percent"] > 90:
                self.emit(
                    event_type=EventType.PULSE_ALERT.value,
                    data={"type": "cpu", "value": status["cpu_percent"]},
                    priority=8
                )

            if status["memory"]["percent"] > 90:
                self.emit(
                    event_type=EventType.PULSE_ALERT.value,
                    data={"type": "memory", "value": status["memory"]["percent"]},
                    priority=8
                )

            return status

        except ImportError:
            return {"error": "psutil no disponible"}

    async def process_query(self, query: str, context: Dict = None) -> Dict:
        """Procesar consulta de Pulse"""
        return self.get_status()


# ============================================
# Module Registration
# ============================================

def register_all_modules():
    """Registrar todos los módulos en el EventBus"""
    modules = [
        ChatModule(),
        LensModule(),
        VaultModule(),
        ScribeModule(),
        CortexModule(),
        MemoryModule(),
        GhostModule(),
        AgentsModule(),
        SpacesModule(),
        PulseModule(),
    ]

    logger.info(f"Registrados {len(modules)} módulos en el EventBus")

    return {m.name: m for m in modules}


# Instancias singleton
_modules = None


def get_modules() -> Dict[str, PurmaModule]:
    """Obtener todos los módulos registrados"""
    global _modules
    if _modules is None:
        _modules = register_all_modules()
    return _modules


def get_module(name: str) -> Optional[PurmaModule]:
    """Obtener un módulo por nombre"""
    return get_modules().get(name)
