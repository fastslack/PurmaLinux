# PurmaLinux - Sistema de Integración Unificado

> **Autor:** Matías Aguirre | **Empresa:** Matware

## Arquitectura de Comunicación

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           PurmaLinux AI System                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        PurmaEventBus                                  │   │
│  │  (Sistema Central de Mensajería Pub/Sub)                             │   │
│  │                                                                       │   │
│  │  • Suscripciones por tipo de evento                                  │   │
│  │  • Suscripciones por patrón (wildcards: "ai.*")                     │   │
│  │  • Persistencia de eventos en SQLite                                 │   │
│  │  • Priorización de eventos (1-10)                                    │   │
│  │  • Correlación de eventos relacionados                               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              ▲                                              │
│                              │                                              │
│              ┌───────────────┼───────────────┐                             │
│              │               │               │                             │
│              ▼               ▼               ▼                             │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐                  │
│  │ PurmaContext  │  │ Intelligence  │  │   Workflow    │                  │
│  │   (Estado)    │  │    Router     │  │ Orchestrator  │                  │
│  └───────────────┘  └───────────────┘  └───────────────┘                  │
│                                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                           MÓDULOS                                            │
│                                                                              │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ │
│  │  Chat   │ │  Lens   │ │  Vault  │ │ Scribe  │ │  Pulse  │ │ Bridge  │ │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ │
│       │          │          │          │          │          │          │
│  ┌────┴────┐ ┌────┴────┐ ┌────┴────┐ ┌────┴────┐ ┌────┴────┐ ┌────┴────┐ │
│  │ Spaces  │ │  Flow   │ │ Cortex  │ │ Memory  │ │  Ghost  │ │ Agents  │ │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘ │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Componentes del Sistema

### 1. PurmaEventBus (Bus de Eventos)

El corazón del sistema de comunicación. Implementa el patrón Publish/Subscribe.

```python
from purma_integration import event_bus, PurmaEvent, EventType

# Publicar un evento
await event_bus.publish(PurmaEvent(
    event_type=EventType.USER_APP_FOCUSED.value,
    source="window_manager",
    data={"app": "Firefox", "window_id": "0x12345"}
))

# Suscribirse a eventos
def on_app_change(event):
    print(f"App cambiada a: {event.data['app']}")

event_bus.subscribe("user.app_focused", on_app_change)

# Suscribirse con wildcards
event_bus.subscribe("ai.*", handle_all_ai_events)
```

### 2. PurmaContext (Contexto Global)

Mantiene el estado actual del sistema.

```python
from purma_integration import context

# Obtener contexto actual
current_app = context.get("current_app")
recent_files = context.get("recent_files")

# Contexto completo
full_ctx = context.get_full_context()

# Resumen para AI
summary = context.get_context_summary()
# Output:
# App actual: Firefox
# Espacio: work
# Estado: active
# Apps recientes: Firefox, VSCode, Kitty
# Vault: desbloqueado
```

### 3. IntelligenceRouter (Enrutador Inteligente)

Decide qué módulo debe manejar una consulta.

```python
from purma_integration import router

# Enrutar una consulta
module, confidence = router.route("buscar mi contraseña de github")
# module = "vault", confidence = 0.7

# Smart query (enruta y ejecuta)
result = await router.smart_query("captura la pantalla y extrae el texto")
# Automáticamente llama a Lens y ejecuta OCR
```

### 4. WorkflowOrchestrator (Orquestador de Flujos)

Coordina flujos complejos entre módulos.

```python
from purma_integration import orchestrator

# Ejecutar workflow predefinido
result = await orchestrator.execute("morning_routine")
result = await orchestrator.execute("focus_mode", {"duration": 25})
result = await orchestrator.execute("research_task", {"topic": "RAG systems"})
```

---

## Taxonomía de Eventos

### Categorías

| Categoría | Descripción |
|-----------|-------------|
| `system.*` | Eventos del sistema operativo |
| `user.*` | Acciones del usuario |
| `ai.*` | Eventos de módulos AI |
| `notification.*` | Notificaciones |
| `command.*` | Comandos ejecutados |
| `data.*` | Cambios de datos |

### Eventos por Módulo

#### Sistema
```
system.startup           - Sistema iniciado
system.shutdown          - Sistema apagándose
system.resource_alert    - Alerta de recursos
```

#### Usuario
```
user.app_focused         - Aplicación enfocada
user.app_launched        - Aplicación lanzada
user.app_closed          - Aplicación cerrada
user.command_executed    - Comando ejecutado
user.file_accessed       - Archivo accedido
user.clipboard_changed   - Clipboard modificado
user.idle                - Usuario inactivo
user.active              - Usuario activo
```

#### Chat
```
ai.chat.message          - Mensaje enviado
ai.chat.response         - Respuesta recibida
```

#### Cortex
```
ai.cortex.prediction     - Predicción generada
ai.cortex.pattern_learned - Patrón aprendido
```

#### Memory
```
ai.memory.indexed        - Documento indexado
ai.memory.search         - Búsqueda realizada
```

#### Ghost
```
ai.ghost.suggestion      - Sugerencia generada
ai.ghost.pattern_detected - Patrón detectado
```

#### Agents
```
ai.agent.task_started    - Tarea iniciada
ai.agent.task_completed  - Tarea completada
```

#### Lens
```
lens.capture             - Captura realizada
lens.ocr_complete        - OCR completado
```

#### Vault
```
vault.unlocked           - Vault desbloqueado
vault.locked             - Vault bloqueado
vault.secret_accessed    - Secreto accedido
```

#### Scribe
```
scribe.recording_started - Grabación iniciada
scribe.transcription_complete - Transcripción completada
scribe.tts_complete      - TTS completado
```

#### Spaces
```
spaces.changed           - Espacio cambiado
```

#### Flow
```
flow.workflow_started    - Workflow iniciado
flow.workflow_completed  - Workflow completado
```

#### Pulse
```
pulse.alert              - Alerta de sistema
```

#### Bridge
```
bridge.command           - Comando de terminal
```

---

## Estructura de Evento

```python
@dataclass
class PurmaEvent:
    event_type: str          # Tipo de evento (ej: "user.app_focused")
    source: str              # Módulo origen (ej: "cortex")
    data: Dict[str, Any]     # Datos del evento
    timestamp: str           # ISO timestamp
    event_id: str            # ID único
    priority: int            # 1-10 (10 = más alta)
    requires_response: bool  # Si espera respuesta
    correlation_id: str      # Para rastrear cadenas
    tags: List[str]          # Etiquetas adicionales
```

---

## Integración de Módulos

### Crear un Módulo Integrado

```python
from purma_integration import PurmaModule, EventType

class MiModulo(PurmaModule):
    def __init__(self):
        super().__init__(
            name="mi_modulo",
            description="Mi módulo personalizado"
        )

        # Suscribirse a eventos
        self.on("user.app_focused", self._on_app_change)
        self.on("ai.*", self._on_ai_event)

    def _on_app_change(self, event):
        # Reaccionar al cambio de app
        app = event.data.get("app")
        self.emit(
            event_type="mi_modulo.processed",
            data={"app": app, "action": "processed"}
        )

    async def _on_ai_event(self, event):
        # Manejar eventos AI
        pass

    async def process_query(self, query: str, context: dict) -> dict:
        # Procesar consulta (usado por router)
        return {"response": f"Procesado: {query}"}
```

### Emitir Eventos desde Cualquier Lugar

```python
from purma_integration import emit_event_sync, emit_event

# Síncrono
emit_event_sync(
    event_type="custom.event",
    source="mi_script",
    data={"key": "value"}
)

# Asíncrono
await emit_event(
    event_type="custom.event",
    source="mi_script",
    data={"key": "value"},
    priority=8,
    tags=["important"]
)
```

---

## Flujos de Trabajo Predefinidos

### 1. Morning Routine
```python
await orchestrator.execute("morning_routine")
```
1. Cortex predice apps necesarias
2. Memory busca notas recientes
3. Pulse muestra estado del sistema

### 2. Focus Mode
```python
await orchestrator.execute("focus_mode", {"duration": 25})
```
1. Cambia a espacio "focus"
2. Activa modo no molestar
3. Prepara apps de trabajo

### 3. Research Task
```python
await orchestrator.execute("research_task", {"topic": "machine learning"})
```
1. Agents (researcher) investiga el tema
2. Agents (analyzer) procesa resultados
3. Memory indexa la información

### 4. Code Review
```python
await orchestrator.execute("code_review", {"file": "/path/to/file.py"})
```
1. Coder analiza el código
2. Reviewer da feedback
3. Se generan sugerencias

### 5. Capture and Analyze
```python
await orchestrator.execute("capture_and_analyze", {"mode": "region"})
```
1. Lens captura pantalla
2. OCR extrae texto
3. Memory indexa contenido

### 6. Voice Command
```python
await orchestrator.execute("voice_command", {"duration": 5})
```
1. Scribe graba audio
2. Transcribe a texto
3. Router determina intención
4. Ejecuta comando apropiado

---

## Comunicación Entre Módulos

### Diagrama de Flujo: Comando de Voz → Acción

```
┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
│  User   │────▶│ Scribe  │────▶│ Router  │────▶│ Target  │
│  Speaks │     │ (STT)   │     │         │     │ Module  │
└─────────┘     └────┬────┘     └────┬────┘     └────┬────┘
                     │               │               │
                     ▼               ▼               ▼
              ┌──────────┐   ┌──────────┐   ┌──────────┐
              │ Event:   │   │ Event:   │   │ Event:   │
              │ scribe.  │   │ context. │   │ [module].│
              │ trans-   │   │ changed  │   │ action   │
              │ cription │   │          │   │          │
              └──────────┘   └──────────┘   └──────────┘
                     │               │               │
                     └───────────────┴───────────────┘
                                     │
                                     ▼
                              ┌──────────┐
                              │ EventBus │
                              │(persists)│
                              └──────────┘
```

### Diagrama de Flujo: Aprendizaje Continuo

```
┌─────────────────────────────────────────────────────────────────┐
│                    Ciclo de Aprendizaje                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌──────────┐                                                  │
│   │  User    │                                                  │
│   │  Action  │                                                  │
│   └────┬─────┘                                                  │
│        │                                                        │
│        ▼                                                        │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐                 │
│   │  Ghost   │───▶│  Cortex  │───▶│  Memory  │                 │
│   │ (Observe)│    │ (Learn)  │    │ (Index)  │                 │
│   └────┬─────┘    └────┬─────┘    └────┬─────┘                 │
│        │               │               │                        │
│        ▼               ▼               ▼                        │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐                 │
│   │Suggestion│    │Prediction│    │ Semantic │                 │
│   │Generated │    │Available │    │ Search   │                 │
│   └────┬─────┘    └────┬─────┘    └────┬─────┘                 │
│        │               │               │                        │
│        └───────────────┴───────────────┘                        │
│                        │                                        │
│                        ▼                                        │
│                 ┌──────────┐                                    │
│                 │  Smarter │                                    │
│                 │  System  │                                    │
│                 └──────────┘                                    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## API de Integración

### Endpoints del EventBus

```
GET  /integration/status           - Estado del sistema
GET  /integration/events           - Eventos recientes
POST /integration/events           - Publicar evento
GET  /integration/events/query     - Consultar eventos
GET  /integration/modules          - Módulos registrados
GET  /integration/context          - Contexto actual
POST /integration/route            - Enrutar consulta
POST /integration/workflow/{name}  - Ejecutar workflow
```

### Ejemplos de Llamadas

```bash
# Estado del sistema
curl http://localhost:11435/integration/status

# Publicar evento
curl -X POST http://localhost:11435/integration/events \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "custom.event",
    "source": "external",
    "data": {"message": "Hello"}
  }'

# Enrutar consulta
curl -X POST http://localhost:11435/integration/route \
  -H "Content-Type: application/json" \
  -d '{"query": "buscar mi contraseña de github"}'

# Ejecutar workflow
curl -X POST http://localhost:11435/integration/workflow/focus_mode \
  -H "Content-Type: application/json" \
  -d '{"duration": 25}'
```

---

## Configuración

### Variables de Entorno

```bash
# Ubicación de datos
PURMA_DATA_DIR=~/.purma

# Nivel de log
PURMA_LOG_LEVEL=INFO

# Puerto del servidor
PURMA_PORT=11435

# Modelo de Ollama
PURMA_MODEL=purma
```

### Estructura de Directorios

```
~/.purma/
├── integration/
│   └── events.db        # Historial de eventos
├── cortex/
│   └── cortex.db        # Patrones aprendidos
├── memory/
│   └── memory.db        # Índice de documentos
├── ghost/
│   └── ghost.db         # Observaciones y sugerencias
├── vault/
│   └── vault.db         # Secretos cifrados
├── scribe/
│   └── recordings/      # Grabaciones de audio
└── lens/
    └── captures/        # Capturas de pantalla
```

---

## Mejores Prácticas

### 1. Emitir Eventos Descriptivos

```python
# Bien
self.emit(
    event_type="vault.secret_accessed",
    data={
        "secret_id": "github_token",
        "access_type": "copy",
        "requester": "user"
    },
    tags=["security", "audit"]
)

# Mal
self.emit(
    event_type="action",
    data={"id": 123}
)
```

### 2. Usar Correlation IDs

```python
# Para rastrear flujos relacionados
correlation_id = f"flow_{datetime.now().timestamp()}"

self.emit(
    event_type="flow.step_1",
    data={"action": "start"},
    correlation_id=correlation_id
)

# ... más pasos ...

self.emit(
    event_type="flow.step_n",
    data={"action": "complete"},
    correlation_id=correlation_id
)
```

### 3. Priorizar Correctamente

```python
# Prioridades:
# 1-3: Baja (logs, métricas)
# 4-6: Normal (eventos regulares)
# 7-8: Alta (acciones de usuario)
# 9-10: Crítica (alertas, seguridad)

self.emit(
    event_type="pulse.critical_alert",
    data={"cpu": 95},
    priority=10
)
```

### 4. Suscribirse Específicamente

```python
# Bien: específico
self.on("user.app_focused", self._handle_app)

# Aceptable: patrón cuando necesario
self.on("ai.cortex.*", self._handle_cortex)

# Evitar: demasiado amplio
self.on("*", self._handle_all)  # No recomendado
```

---

## Debugging

### Ver Eventos en Tiempo Real

```python
from purma_integration import event_bus

def debug_handler(event):
    print(f"[{event.timestamp}] {event.event_type}: {event.data}")

event_bus.subscribe("*", debug_handler)
```

### Consultar Historial

```python
# Últimos 10 eventos de Cortex
events = event_bus.query_events(
    event_type="ai.cortex.*",
    limit=10
)

# Eventos de última hora
from datetime import datetime, timedelta
since = (datetime.now() - timedelta(hours=1)).isoformat()
events = event_bus.query_events(since=since)
```

### Logs

```bash
# Ver logs del sistema
tail -f ~/.purma/logs/integration.log

# Filtrar por módulo
grep "cortex" ~/.purma/logs/integration.log
```

---

## Extendiendo el Sistema

### Agregar Nuevo Tipo de Evento

1. Agregar al enum `EventType`:
```python
class EventType(Enum):
    # ... existentes ...
    MI_NUEVO_EVENTO = "mi_modulo.nuevo_evento"
```

2. Documentar en esta guía

3. Implementar handlers necesarios

### Agregar Nuevo Workflow

```python
class PurmaWorkflowOrchestrator:
    def __init__(self):
        # ... existente ...
        self._workflows["mi_workflow"] = self._workflow_mi_workflow

    async def _workflow_mi_workflow(self, params: Dict) -> Dict:
        # Implementación
        pass
```

### Agregar Nueva Ruta al Router

```python
class PurmaIntelligenceRouter:
    def __init__(self):
        # ... existente ...
        self._routes["mi_keyword"] = "mi_modulo"
```

---

## Resumen

El sistema de integración de PurmaLinux permite:

1. **Comunicación desacoplada**: Los módulos no necesitan conocerse entre sí
2. **Reactividad**: Eventos permiten respuestas automáticas
3. **Persistencia**: Historial de eventos para análisis
4. **Inteligencia**: Router y orquestador coordinan automáticamente
5. **Extensibilidad**: Fácil agregar nuevos módulos y workflows
6. **Contexto compartido**: Estado global accesible por todos

La arquitectura sigue el principio de **"AI-First"**: cada interacción genera datos que alimentan el aprendizaje continuo del sistema, haciendo que PurmaLinux sea más inteligente con el uso.
