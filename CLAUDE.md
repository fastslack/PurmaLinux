# PurmaLinux - AI-First Linux Distribution

<project>
  <name>PurmaLinux</name>
  <author>Matías Aguirre</author>
  <company>Matware</company>
  <description>Distribución Linux AI-First con integración profunda de inteligencia artificial en cada aspecto del sistema operativo</description>
  <philosophy>AI como ciudadano de primera clase, no como add-on</philosophy>
  <target>Usuarios avanzados, desarrolladores, entusiastas de AI</target>
</project>

<architecture>
  <backend>
    <server>
      <path>ai/server/purma_server.py</path>
      <framework>FastAPI</framework>
      <port>11435</port>
      <features>
        <feature>Chat AI con Ollama</feature>
        <feature>Comandos builtin con prefijo /</feature>
        <feature>WebSocket para streaming</feature>
        <feature>Integración con todos los módulos Purma</feature>
      </features>
    </server>
    <model>
      <name>purma</name>
      <base>Ollama (llama3.2 o similar)</base>
      <personality>Asistente técnico de PurmaLinux</personality>
    </model>
  </backend>

  <frontend>
    <framework>AGS (Aylur's GTK Shell)</framework>
    <language>JavaScript/GJS</language>
    <styling>GTK CSS</styling>
    <path>desktop/ags/</path>
  </frontend>

  <window_managers>
    <wm name="i3-gaps">
      <config_path>i3/config/config</config_path>
      <bar>Polybar</bar>
      <launcher>Rofi</launcher>
      <compositor>Picom</compositor>
      <notifications>Dunst</notifications>
      <terminal>Kitty</terminal>
    </wm>
    <wm name="Openbox">
      <config_path>desktop/openbox/rc.xml</config_path>
      <bar>AGS</bar>
      <launcher>Rofi</launcher>
      <compositor>Picom</compositor>
      <autostart>desktop/openbox/autostart</autostart>
    </wm>
  </window_managers>
</architecture>

<theme name="Aurora">
  <colors>
    <backgrounds>
      <color name="void" hex="#0a0e14" usage="Fondo más oscuro"/>
      <color name="space" hex="#0d1117" usage="Fondo principal"/>
      <color name="nebula" hex="#161b22" usage="Fondo elevado"/>
      <color name="cosmic" hex="#21262d" usage="Bordes, separadores"/>
      <color name="stardust" hex="#30363d" usage="Bordes activos"/>
    </backgrounds>
    <text>
      <color name="moonlight" hex="#8b949e" usage="Texto secundario"/>
      <color name="starlight" hex="#c9d1d9" usage="Texto normal"/>
      <color name="plasma" hex="#f0f6fc" usage="Texto destacado"/>
    </text>
    <accents>
      <color name="cyan" hex="#00d4ff" usage="Acento principal, focus"/>
      <color name="purple" hex="#a855f7" usage="Acento secundario, AI"/>
      <color name="pink" hex="#ec4899" usage="Acento terciario"/>
      <color name="green" hex="#22c55e" usage="Éxito, Scribe"/>
      <color name="yellow" hex="#f59e0b" usage="Advertencia, Vault"/>
      <color name="red" hex="#ef4444" usage="Error, urgente"/>
    </accents>
  </colors>
  <design>
    <gaps inner="12px" outer="8px"/>
    <borders width="3px" radius="12px"/>
    <font family="JetBrains Mono" size="10"/>
    <shadows blur="32px" opacity="0.5"/>
  </design>
</theme>

<modules>
  <module name="Purma Chat">
    <shortcut>Super+A</shortcut>
    <shortcut_alt>Super+Shift+A (terminal)</shortcut_alt>
    <description>Conversación con AI, comandos del sistema</description>
    <backend>ai/server/purma_server.py</backend>
    <widget>desktop/ags/widgets/chat/Chat.js</widget>
    <style>desktop/ags/widgets/chat/style.css</style>
    <api_endpoints>
      <endpoint method="POST" path="/chat">/chat - Enviar mensaje</endpoint>
      <endpoint method="GET" path="/chat/history">/chat/history - Historial</endpoint>
      <endpoint method="WS" path="/ws">/ws - WebSocket streaming</endpoint>
    </api_endpoints>
  </module>

  <module name="Purma Spaces">
    <shortcut>Super+O</shortcut>
    <shortcut_alt>Super+Shift+O (menú)</shortcut_alt>
    <shortcut_nav>Super+] / Super+[ (next/prev)</shortcut_nav>
    <shortcut_quick>Ctrl+Super+1-4 (espacios rápidos)</shortcut_quick>
    <description>Gestión de contextos de trabajo con perfiles AI</description>
    <widget>desktop/ags/widgets/spaces/Spaces.js</widget>
    <style>desktop/ags/widgets/spaces/style.css</style>
    <spaces>
      <space name="work" icon="💼" apps="slack,teams,outlook"/>
      <space name="code" icon="💻" apps="vscode,terminal,browser"/>
      <space name="focus" icon="🎯" apps="minimal,music"/>
      <space name="gaming" icon="🎮" apps="steam,discord"/>
    </spaces>
  </module>

  <module name="Purma Flow">
    <shortcut>Super+F</shortcut>
    <shortcut_alt>Super+Shift+F (grabar)</shortcut_alt>
    <description>Automatización de workflows, grabación de macros</description>
    <widget>desktop/ags/widgets/flow/Flow.js</widget>
    <style>desktop/ags/widgets/flow/style.css</style>
    <features>
      <feature>Grabar secuencias de acciones</feature>
      <feature>Ejecutar workflows guardados</feature>
      <feature>AI sugiere automatizaciones</feature>
    </features>
  </module>

  <module name="Purma Bridge">
    <shortcut>Super+B</shortcut>
    <shortcut_alt>Super+Shift+B (terminal)</shortcut_alt>
    <description>Terminal AI-enhanced con sugerencias de comandos</description>
    <widget>desktop/ags/widgets/bridge/Bridge.js</widget>
    <style>desktop/ags/widgets/bridge/style.css</style>
    <features>
      <feature>Autocompletado inteligente</feature>
      <feature>Explicación de comandos</feature>
      <feature>Corrección de errores</feature>
    </features>
  </module>

  <module name="Purma Pulse">
    <shortcut>Super+P</shortcut>
    <shortcut_alt>Super+Shift+P (btop)</shortcut_alt>
    <description>Monitor de sistema con análisis AI</description>
    <widget>desktop/ags/widgets/pulse/Pulse.js</widget>
    <style>desktop/ags/widgets/pulse/style.css</style>
    <api_endpoints>
      <endpoint method="GET" path="/system/status">/system/status - Estado del sistema</endpoint>
      <endpoint method="GET" path="/system/processes">/system/processes - Procesos</endpoint>
      <endpoint method="POST" path="/system/analyze">/system/analyze - Análisis AI</endpoint>
    </api_endpoints>
    <metrics>
      <metric>CPU, RAM, Disco, Red</metric>
      <metric>Procesos por consumo</metric>
      <metric>Predicciones de rendimiento</metric>
    </metrics>
  </module>

  <module name="Purma Lens">
    <shortcut>Super+Y</shortcut>
    <shortcut_alt>Super+Shift+Y (región)</shortcut_alt>
    <shortcut_print>Print (pantalla), Shift+Print (región), Super+Print (ventana)</shortcut_print>
    <description>Captura de pantalla con OCR y análisis visual AI</description>
    <backend>ai/server/purma_lens.py</backend>
    <widget>desktop/ags/widgets/lens/Lens.js</widget>
    <style>desktop/ags/widgets/lens/style.css</style>
    <api_endpoints>
      <endpoint method="POST" path="/lens/capture">/lens/capture - Capturar</endpoint>
      <endpoint method="POST" path="/lens/ocr">/lens/ocr - Extraer texto</endpoint>
      <endpoint method="POST" path="/lens/analyze">/lens/analyze - Analizar imagen</endpoint>
      <endpoint method="GET" path="/lens/history">/lens/history - Historial</endpoint>
    </api_endpoints>
    <features>
      <feature>OCR con Tesseract</feature>
      <feature>Análisis visual con LLaVA</feature>
      <feature>Historial de capturas</feature>
      <feature>Copiar texto extraído</feature>
    </features>
  </module>

  <module name="Purma Vault">
    <shortcut>Super+V</shortcut>
    <shortcut_alt>Super+Shift+V (CLI)</shortcut_alt>
    <description>Password manager con cifrado y búsqueda AI</description>
    <backend>ai/server/purma_vault.py</backend>
    <widget>desktop/ags/widgets/vault/Vault.js</widget>
    <style>desktop/ags/widgets/vault/style.css</style>
    <accent_color>#f59e0b (yellow)</accent_color>
    <api_endpoints>
      <endpoint method="GET" path="/vault/status">/vault/status - Estado</endpoint>
      <endpoint method="POST" path="/vault/init">/vault/init - Inicializar</endpoint>
      <endpoint method="POST" path="/vault/unlock">/vault/unlock - Desbloquear</endpoint>
      <endpoint method="POST" path="/vault/lock">/vault/lock - Bloquear</endpoint>
      <endpoint method="GET" path="/vault/secrets">/vault/secrets - Listar</endpoint>
      <endpoint method="POST" path="/vault/secrets">/vault/secrets - Agregar</endpoint>
      <endpoint method="GET" path="/vault/secrets/{id}">/vault/secrets/{id} - Obtener</endpoint>
      <endpoint method="GET" path="/vault/search">/vault/search?q= - Buscar</endpoint>
      <endpoint method="GET" path="/vault/generate">/vault/generate - Generar password</endpoint>
      <endpoint method="POST" path="/vault/query">/vault/query - Búsqueda AI</endpoint>
    </api_endpoints>
    <encryption>
      <algorithm>PBKDF2-HMAC-SHA256</algorithm>
      <iterations>480000</iterations>
      <cipher>Fernet (AES-128-CBC)</cipher>
      <storage>SQLite cifrado</storage>
    </encryption>
    <chat_commands>
      <command>/vault - Estado del vault</command>
      <command>/password {query} - Buscar con AI</command>
      <command>/generate {length} - Generar password</command>
      <command>/addpass {name} - Agregar secreto</command>
    </chat_commands>
  </module>

  <module name="Purma Scribe">
    <shortcut>Super+C</shortcut>
    <shortcut_alt>Super+Shift+X (quick 5s)</shortcut_alt>
    <description>Asistente de voz con transcripción y TTS</description>
    <backend>ai/server/purma_scribe.py</backend>
    <widget>desktop/ags/widgets/scribe/Scribe.js</widget>
    <style>desktop/ags/widgets/scribe/style.css</style>
    <accent_color>#22c55e (green)</accent_color>
    <api_endpoints>
      <endpoint method="GET" path="/scribe/status">/scribe/status - Estado</endpoint>
      <endpoint method="POST" path="/scribe/record/start">/scribe/record/start - Iniciar grabación</endpoint>
      <endpoint method="POST" path="/scribe/record/stop">/scribe/record/stop - Detener grabación</endpoint>
      <endpoint method="POST" path="/scribe/transcribe/{id}">/scribe/transcribe/{id} - Transcribir</endpoint>
      <endpoint method="POST" path="/scribe/quick">/scribe/quick?duration= - Grabación rápida</endpoint>
      <endpoint method="POST" path="/scribe/speak">/scribe/speak - Text-to-Speech</endpoint>
      <endpoint method="GET" path="/scribe/voices">/scribe/voices - Listar voces</endpoint>
      <endpoint method="GET" path="/scribe/history">/scribe/history - Historial</endpoint>
    </api_endpoints>
    <stt_engines>
      <engine priority="1">faster-whisper</engine>
      <engine priority="2">whisper</engine>
      <engine priority="3">vosk</engine>
    </stt_engines>
    <tts_engines>
      <engine priority="1">piper</engine>
      <engine priority="2">espeak-ng</engine>
      <engine priority="3">espeak</engine>
      <engine priority="4">festival</engine>
      <engine priority="5">say (macOS)</engine>
    </tts_engines>
    <chat_commands>
      <command>/scribe - Estado</command>
      <command>/record {seconds} - Grabar</command>
      <command>/transcribe {file} - Transcribir archivo</command>
      <command>/speak {text} - TTS</command>
      <command>/dictate - Modo dictado</command>
    </chat_commands>
  </module>

  <module name="Purma Brain">
    <shortcut>Super+I</shortcut>
    <description>Panel de control unificado para sistemas AI avanzados</description>
    <widget>desktop/ags/widgets/brain/Brain.js</widget>
    <style>desktop/ags/widgets/brain/style.css</style>
    <accent_color>linear-gradient(#a855f7 → #00d4ff)</accent_color>
    <views>
      <view name="Overview">Panel de estado de todos los subsistemas AI</view>
      <view name="Cortex">Control del motor predictivo</view>
      <view name="Memory">Búsqueda semántica RAG</view>
      <view name="Ghost">Sugerencias de automatización</view>
      <view name="Agents">Sistema multi-agente</view>
    </views>
    <features>
      <feature>Vista unificada de estado AI</feature>
      <feature>Toggle rápido de subsistemas</feature>
      <feature>Tabs para cada módulo AI</feature>
    </features>
  </module>

  <module name="Purma Cortex">
    <shortcut>Via Brain (Super+I)</shortcut>
    <description>Motor predictivo AI que aprende patrones de uso</description>
    <backend>ai/server/purma_cortex.py</backend>
    <accent_color>#a855f7 (purple)</accent_color>
    <api_endpoints>
      <endpoint method="GET" path="/cortex/status">/cortex/status - Estado del motor</endpoint>
      <endpoint method="POST" path="/cortex/start">/cortex/start - Iniciar aprendizaje</endpoint>
      <endpoint method="POST" path="/cortex/stop">/cortex/stop - Detener aprendizaje</endpoint>
      <endpoint method="GET" path="/cortex/predict">/cortex/predict - Obtener predicciones</endpoint>
      <endpoint method="GET" path="/cortex/schedule">/cortex/schedule - Calendario predictivo</endpoint>
      <endpoint method="GET" path="/cortex/patterns">/cortex/patterns - Patrones aprendidos</endpoint>
      <endpoint method="GET" path="/cortex/insights">/cortex/insights - Insights de uso</endpoint>
      <endpoint method="POST" path="/cortex/prepare">/cortex/prepare - Pre-cargar apps</endpoint>
    </api_endpoints>
    <storage>SQLite (~/.purma/cortex/cortex.db)</storage>
    <components>
      <component name="CortexStorage">Persistencia de patrones en SQLite</component>
      <component name="ActivityTracker">Observador de actividad (ventanas, apps)</component>
      <component name="PredictionEngine">Motor de predicciones basado en patrones</component>
    </components>
    <patterns_tracked>
      <pattern>Secuencias de aplicaciones</pattern>
      <pattern>Patrones por hora del día</pattern>
      <pattern>Co-ocurrencias de apps</pattern>
      <pattern>Duración de uso por app</pattern>
    </patterns_tracked>
    <chat_commands>
      <command>/cortex - Estado del motor</command>
      <command>/predict - Obtener predicciones</command>
      <command>/schedule - Ver calendario predictivo</command>
      <command>/patterns - Ver patrones aprendidos</command>
      <command>/learn - Toggle aprendizaje</command>
    </chat_commands>
  </module>

  <module name="Purma Memory">
    <shortcut>Via Brain (Super+I)</shortcut>
    <description>Sistema RAG local para búsqueda semántica de archivos</description>
    <backend>ai/server/purma_memory.py</backend>
    <accent_color>#00d4ff (cyan)</accent_color>
    <api_endpoints>
      <endpoint method="GET" path="/memory/status">/memory/status - Estado</endpoint>
      <endpoint method="POST" path="/memory/index/file">/memory/index/file - Indexar archivo</endpoint>
      <endpoint method="POST" path="/memory/index/directory">/memory/index/directory - Indexar directorio</endpoint>
      <endpoint method="GET" path="/memory/search">/memory/search?q= - Buscar</endpoint>
      <endpoint method="POST" path="/memory/ask">/memory/ask - Pregunta RAG</endpoint>
      <endpoint method="GET" path="/memory/document/{id}">/memory/document/{id} - Ver documento</endpoint>
      <endpoint method="POST" path="/memory/watch">/memory/watch - Observar directorio</endpoint>
    </api_endpoints>
    <storage>SQLite + FTS5 (~/.purma/memory/memory.db)</storage>
    <components>
      <component name="VectorStore">Almacén de vectores con FTS5</component>
      <component name="EmbeddingGenerator">Generador de embeddings (Ollama/fallback)</component>
      <component name="DocumentProcessor">Procesador de documentos (txt, md, pdf, code)</component>
    </components>
    <search_modes>
      <mode name="semantic">Búsqueda por similitud de embeddings</mode>
      <mode name="keyword">Búsqueda por palabras clave (FTS5)</mode>
      <mode name="hybrid">Combinación de ambos métodos</mode>
    </search_modes>
    <supported_files>
      <type>.txt, .md, .rst</type>
      <type>.py, .js, .ts, .go, .rs, .c, .cpp, .java</type>
      <type>.json, .yaml, .toml, .xml</type>
      <type>.sh, .bash, .zsh</type>
    </supported_files>
    <chat_commands>
      <command>/memory - Estado del sistema</command>
      <command>/remember {path} - Indexar archivo/directorio</command>
      <command>/ask-memory {question} - Preguntar con RAG</command>
      <command>/index - Indexar directorio actual</command>
    </chat_commands>
  </module>

  <module name="Purma Ghost">
    <shortcut>Via Brain (Super+I)</shortcut>
    <description>AI sombra que observa y sugiere automatizaciones</description>
    <backend>ai/server/purma_ghost.py</backend>
    <accent_color>#22c55e (green)</accent_color>
    <api_endpoints>
      <endpoint method="GET" path="/ghost/status">/ghost/status - Estado</endpoint>
      <endpoint method="POST" path="/ghost/start">/ghost/start - Iniciar observación</endpoint>
      <endpoint method="POST" path="/ghost/stop">/ghost/stop - Detener observación</endpoint>
      <endpoint method="GET" path="/ghost/analyze">/ghost/analyze - Analizar patrones</endpoint>
      <endpoint method="GET" path="/ghost/suggestions">/ghost/suggestions - Obtener sugerencias</endpoint>
      <endpoint method="POST" path="/ghost/suggestions/{id}/respond">/ghost/suggestions/{id}/respond - Responder</endpoint>
      <endpoint method="POST" path="/ghost/apply/{id}">/ghost/apply/{id} - Aplicar sugerencia</endpoint>
      <endpoint method="GET" path="/ghost/insights">/ghost/insights - Insights</endpoint>
    </api_endpoints>
    <storage>SQLite (~/.purma/ghost/ghost.db)</storage>
    <components>
      <component name="GhostStorage">Persistencia de observaciones</component>
      <component name="ActionObserver">Observador de acciones (shell, clipboard, files)</component>
      <component name="PatternDetector">Detector de patrones repetitivos</component>
      <component name="SuggestionGenerator">Generador de sugerencias de automatización</component>
    </components>
    <observation_sources>
      <source>Shell history (~/.bash_history, ~/.zsh_history)</source>
      <source>Clipboard changes</source>
      <source>File system events (inotify)</source>
    </observation_sources>
    <suggestion_types>
      <type name="alias">Crear alias para comandos frecuentes</type>
      <type name="script">Crear script para secuencias repetitivas</type>
      <type name="automation">Automatizar tarea detectada</type>
      <type name="optimization">Optimizar comando existente</type>
    </suggestion_types>
    <chat_commands>
      <command>/ghost - Estado de Ghost</command>
      <command>/observe - Toggle observación</command>
      <command>/suggestions - Ver sugerencias</command>
      <command>/insights - Ver insights</command>
    </chat_commands>
  </module>

  <module name="Purma Multi-Agent">
    <shortcut>Via Brain (Super+I)</shortcut>
    <description>Sistema de agentes AI especializados coordinados</description>
    <backend>ai/server/purma_agents.py</backend>
    <accent_color>#f59e0b (yellow/orange)</accent_color>
    <api_endpoints>
      <endpoint method="GET" path="/agents/status">/agents/status - Estado</endpoint>
      <endpoint method="GET" path="/agents/list">/agents/list - Listar agentes</endpoint>
      <endpoint method="POST" path="/agents/run">/agents/run - Ejecutar tarea</endpoint>
      <endpoint method="POST" path="/agents/{name}/ask">/agents/{name}/ask - Preguntar a agente</endpoint>
    </api_endpoints>
    <agents>
      <agent name="researcher" icon="🔍" capabilities="web search, documentation lookup, information gathering"/>
      <agent name="analyzer" icon="📊" capabilities="data analysis, pattern recognition, insights generation"/>
      <agent name="executor" icon="⚡" capabilities="command execution, file operations, system tasks"/>
      <agent name="coder" icon="💻" capabilities="code generation, refactoring, debugging"/>
      <agent name="reviewer" icon="✅" capabilities="code review, quality analysis, suggestions"/>
    </agents>
    <components>
      <component name="BaseAgent">Clase base para todos los agentes</component>
      <component name="OrchestratorAgent">Coordinador que delega tareas</component>
      <component name="MultiAgentEngine">Motor principal del sistema</component>
    </components>
    <orchestration>
      <step>Orquestador analiza la tarea</step>
      <step>Selecciona agentes relevantes</step>
      <step>Delega subtareas a cada agente</step>
      <step>Combina resultados</step>
      <step>Retorna respuesta unificada</step>
    </orchestration>
    <chat_commands>
      <command>/agents - Listar agentes disponibles</command>
      <command>/task {description} - Ejecutar tarea multi-agente</command>
      <command>/ask-agent {name} {question} - Preguntar a agente específico</command>
    </chat_commands>
  </module>

  <module name="Purma GameHub">
    <shortcut>Super+G</shortcut>
    <description>Centro unificado de gaming con escaneo de bibliotecas, ProtonDB y GameMode</description>
    <backend>ai/server/purma_gamehub.py</backend>
    <widget>desktop/ags/widgets/gamehub/GameHub.js</widget>
    <style>desktop/ags/widgets/gamehub/style.css</style>
    <accent_color>#8b5cf6 (gaming purple)</accent_color>
    <api_endpoints>
      <endpoint method="GET" path="/gamehub/status">/gamehub/status - Estado del sistema</endpoint>
      <endpoint method="GET" path="/gamehub/games">/gamehub/games - Listar juegos</endpoint>
      <endpoint method="POST" path="/gamehub/scan">/gamehub/scan - Escanear bibliotecas</endpoint>
      <endpoint method="POST" path="/gamehub/launch/{id}">/gamehub/launch/{id} - Lanzar juego</endpoint>
      <endpoint method="GET" path="/gamehub/protondb/{appid}">/gamehub/protondb/{appid} - Rating ProtonDB</endpoint>
      <endpoint method="GET" path="/gamehub/gamemode">/gamehub/gamemode - Estado de GameMode</endpoint>
      <endpoint method="POST" path="/gamehub/favorites/{id}">/gamehub/favorites/{id} - Toggle favorito</endpoint>
    </api_endpoints>
    <storage>SQLite (~/.purma/gamehub/gamehub.db)</storage>
    <sources>
      <source name="Steam">Biblioteca de Steam</source>
      <source name="Lutris">Juegos de Lutris</source>
      <source name="Heroic">Epic Games y GOG</source>
      <source name="Native">Juegos nativos Linux (OpenRA, etc.)</source>
    </sources>
    <features>
      <feature>Escaneo automático de bibliotecas de juegos</feature>
      <feature>Integración con ProtonDB para compatibilidad</feature>
      <feature>Activación automática de GameMode</feature>
      <feature>Overlay con MangoHud</feature>
      <feature>Gestión de favoritos</feature>
      <feature>Búsqueda y filtrado</feature>
    </features>
    <included_games>
      <game>OpenRA (C&C, Red Alert, Dune 2000)</game>
    </included_games>
    <chat_commands>
      <command>/games - Listar juegos instalados</command>
      <command>/play {name} - Lanzar juego</command>
      <command>/gamemode - Estado de GameMode</command>
      <command>/protondb {appid} - Consultar ProtonDB</command>
    </chat_commands>
  </module>
</modules>

<file_structure>
  <directory name="ai">
    <directory name="server">
      <file>purma_server.py</file>
      <file>purma_lens.py</file>
      <file>purma_vault.py</file>
      <file>purma_scribe.py</file>
      <file>purma_cortex.py</file>
      <file>purma_memory.py</file>
      <file>purma_ghost.py</file>
      <file>purma_agents.py</file>
      <file>purma_gamehub.py</file>
      <file>purma_integration.py</file>
      <file>purma_modules.py</file>
      <file>purma_sync.py</file>
      <file>purma_mobile_api.py</file>
    </directory>
    <directory name="models">
      <file>Modelfile</file>
    </directory>
  </directory>

  <directory name="bin">
    <file>purma</file>
  </directory>

  <directory name="docs">
    <file>INTEGRATION.md</file>
  </directory>

  <directory name="desktop">
    <directory name="thunar">
      <file>uca.xml</file>
    </directory>
    <directory name="yazi">
      <file>yazi.toml</file>
      <file>keymap.toml</file>
      <file>theme.toml</file>
    </directory>

  <directory name="desktop">
    <directory name="ags">
      <file>config.js</file>
      <file>style.css</file>
      <directory name="widgets">
        <directory name="chat">
          <file>Chat.js</file>
          <file>style.css</file>
        </directory>
        <directory name="spaces">
          <file>Spaces.js</file>
          <file>style.css</file>
        </directory>
        <directory name="flow">
          <file>Flow.js</file>
          <file>style.css</file>
        </directory>
        <directory name="bridge">
          <file>Bridge.js</file>
          <file>style.css</file>
        </directory>
        <directory name="pulse">
          <file>Pulse.js</file>
          <file>style.css</file>
        </directory>
        <directory name="lens">
          <file>Lens.js</file>
          <file>style.css</file>
        </directory>
        <directory name="vault">
          <file>Vault.js</file>
          <file>style.css</file>
        </directory>
        <directory name="scribe">
          <file>Scribe.js</file>
          <file>style.css</file>
        </directory>
        <directory name="brain">
          <file>Brain.js</file>
          <file>style.css</file>
        </directory>
        <directory name="gamehub">
          <file>GameHub.js</file>
          <file>style.css</file>
        </directory>
      </directory>
    </directory>
    <directory name="gaming">
      <file>install-gaming.sh</file>
    </directory>
    <directory name="openbox">
      <file>rc.xml</file>
      <file>autostart</file>
      <directory name="themes">
        <directory name="Aurora-PurmaLinux">
          <file>themerc</file>
        </directory>
      </directory>
    </directory>
  </directory>

  <directory name="i3">
    <directory name="config">
      <file>config</file>
      <file>autostart.sh</file>
    </directory>
    <directory name="polybar">
      <file>config.ini</file>
    </directory>
    <directory name="rofi">
      <file>aurora.rasi</file>
      <file>aurora-power.rasi</file>
      <directory name="scripts">
        <file>power-menu.sh</file>
      </directory>
    </directory>
    <directory name="dunst">
      <file>dunstrc</file>
    </directory>
    <directory name="picom">
      <file>picom.conf</file>
    </directory>
    <directory name="kitty">
      <file>kitty.conf</file>
    </directory>
    <directory name="gtk-3.0">
      <file>settings.ini</file>
    </directory>
  </directory>
</file_structure>

<keybindings>
  <category name="Purma AI Suite">
    <binding keys="Super+A" action="Purma Chat"/>
    <binding keys="Super+Shift+A" action="Chat en terminal"/>
    <binding keys="Super+O" action="Purma Spaces"/>
    <binding keys="Super+Shift+O" action="Spaces menú"/>
    <binding keys="Super+F" action="Purma Flow"/>
    <binding keys="Super+Shift+F" action="Flow grabar"/>
    <binding keys="Super+B" action="Purma Bridge"/>
    <binding keys="Super+Shift+B" action="Bridge terminal"/>
    <binding keys="Super+P" action="Purma Pulse"/>
    <binding keys="Super+Shift+P" action="btop"/>
    <binding keys="Super+Y" action="Purma Lens"/>
    <binding keys="Super+Shift+Y" action="Captura región"/>
    <binding keys="Super+V" action="Purma Vault"/>
    <binding keys="Super+Shift+V" action="Vault CLI"/>
    <binding keys="Super+C" action="Purma Scribe"/>
    <binding keys="Super+Shift+X" action="Quick record 5s"/>
    <binding keys="Super+I" action="Purma Brain (AI Control Panel)"/>
    <binding keys="Super+G" action="Purma GameHub"/>
  </category>

  <category name="Screenshots">
    <binding keys="Print" action="Captura pantalla completa"/>
    <binding keys="Shift+Print" action="Captura región"/>
    <binding keys="Super+Print" action="Captura ventana"/>
    <binding keys="Ctrl+Print" action="Abrir Lens"/>
  </category>

  <category name="Window Management">
    <binding keys="Super+Return" action="Terminal"/>
    <binding keys="Super+Q" action="Cerrar ventana"/>
    <binding keys="Super+D" action="Launcher (Rofi)"/>
    <binding keys="Super+Space" action="Toggle float"/>
    <binding keys="Super+M" action="Fullscreen"/>
    <binding keys="Super+H/J/K/L" action="Focus vim-style"/>
    <binding keys="Super+1-0" action="Workspace"/>
    <binding keys="Super+Z" action="Modo resize"/>
    <binding keys="Super+G" action="Modo gaps"/>
  </category>

  <category name="Quick Spaces">
    <binding keys="Ctrl+Super+1" action="Space: Work"/>
    <binding keys="Ctrl+Super+2" action="Space: Code"/>
    <binding keys="Ctrl+Super+3" action="Space: Focus"/>
    <binding keys="Ctrl+Super+4" action="Space: Gaming"/>
  </category>
</keybindings>

<builtin_commands>
  <command name="/help" description="Mostrar ayuda"/>
  <command name="/clear" description="Limpiar historial"/>
  <command name="/system" description="Info del sistema"/>
  <command name="/apps" description="Aplicaciones instaladas"/>
  <command name="/search {query}" description="Buscar archivos"/>
  <command name="/run {cmd}" description="Ejecutar comando"/>
  <command name="/install {pkg}" description="Instalar paquete"/>
  <command name="/update" description="Actualizar sistema"/>
  <command name="/config {app}" description="Configurar app"/>
  <command name="/theme {name}" description="Cambiar tema"/>
  <command name="/spaces" description="Gestionar espacios"/>
  <command name="/flow" description="Workflows"/>
  <command name="/pulse" description="Estado del sistema"/>
  <command name="/lens" description="Captura y OCR"/>
  <command name="/vault" description="Password manager"/>
  <command name="/password {query}" description="Buscar password"/>
  <command name="/generate {length}" description="Generar password"/>
  <command name="/addpass {name}" description="Agregar password"/>
  <command name="/scribe" description="Asistente de voz"/>
  <command name="/record {seconds}" description="Grabar audio"/>
  <command name="/transcribe {file}" description="Transcribir archivo"/>
  <command name="/speak {text}" description="Text-to-speech"/>
  <command name="/dictate" description="Modo dictado"/>

  <!-- Cortex Commands -->
  <command name="/cortex" description="Estado del motor predictivo"/>
  <command name="/predict" description="Obtener predicciones de apps"/>
  <command name="/schedule" description="Ver calendario predictivo"/>
  <command name="/patterns" description="Ver patrones aprendidos"/>
  <command name="/learn" description="Toggle modo aprendizaje"/>

  <!-- Memory Commands -->
  <command name="/memory" description="Estado del sistema RAG"/>
  <command name="/remember {path}" description="Indexar archivo o directorio"/>
  <command name="/ask-memory {question}" description="Preguntar con contexto RAG"/>
  <command name="/index" description="Indexar directorio actual"/>

  <!-- Ghost Commands -->
  <command name="/ghost" description="Estado del observador Ghost"/>
  <command name="/observe" description="Toggle modo observación"/>
  <command name="/suggestions" description="Ver sugerencias de automatización"/>
  <command name="/insights" description="Ver insights de Ghost"/>

  <!-- Multi-Agent Commands -->
  <command name="/agents" description="Listar agentes disponibles"/>
  <command name="/task {description}" description="Ejecutar tarea multi-agente"/>
  <command name="/ask-agent {name} {question}" description="Preguntar a agente específico"/>

  <!-- Integration Commands -->
  <command name="/status" description="Estado completo del sistema Purma"/>
  <command name="/context" description="Ver contexto actual del sistema"/>
  <command name="/workflow {name} {params}" description="Ejecutar workflow integrado"/>
  <command name="/smart {query}" description="Consulta inteligente auto-enrutada"/>
  <command name="/events {limit}" description="Ver eventos recientes del sistema"/>
  <command name="/modules" description="Ver módulos registrados"/>
  <command name="/morning" description="Ejecutar rutina matutina"/>
  <command name="/research {topic}" description="Iniciar investigación"/>
  <command name="/review {file}" description="Code review de archivo"/>

  <!-- GameHub Commands -->
  <command name="/games" description="Listar juegos instalados"/>
  <command name="/play {name}" description="Lanzar juego"/>
  <command name="/gamemode" description="Estado de GameMode"/>
  <command name="/protondb {appid}" description="Consultar compatibilidad ProtonDB"/>
  <command name="/scan-games" description="Escanear bibliotecas de juegos"/>
</builtin_commands>

<dependencies>
  <system>
    <package>i3-gaps</package>
    <package>openbox</package>
    <package>polybar</package>
    <package>rofi</package>
    <package>picom</package>
    <package>dunst</package>
    <package>kitty</package>
    <package>ags</package>
    <package>wl-clipboard</package>
    <package>grim</package>
    <package>slurp</package>
    <package>brightnessctl</package>
    <package>playerctl</package>
    <package>pactl</package>
    <package>i3lock-color</package>
  </system>

  <python>
    <package>fastapi</package>
    <package>uvicorn</package>
    <package>httpx</package>
    <package>websockets</package>
    <package>pillow</package>
    <package>pytesseract</package>
    <package>cryptography</package>
    <package>pyaudio</package>
    <package>faster-whisper</package>
    <package>pyttsx3</package>
    <package>psutil</package>
    <package>aiosqlite</package>
    <package>aiofiles</package>
    <package>watchdog</package>
    <package>numpy</package>
  </python>

  <ai>
    <package>ollama</package>
    <package>llama3.2 (o similar)</package>
    <package>llava (para vision)</package>
    <package>whisper (para STT)</package>
    <package>piper (para TTS)</package>
  </ai>
</dependencies>

<api_base_url>http://localhost:11435</api_base_url>

<coding_patterns>
  <pattern name="AGS Widget Structure">
    <description>Cada widget AGS sigue esta estructura:</description>
    <code><![CDATA[
// State management
const widgetState = Variable({
  visible: false,
  // ... estado específico
});

// API Functions
async function fetchData() { ... }

// UI Components
function Header() { return Widget.Box({...}); }
function Content() { return Widget.Box({...}); }

// Main Window
export function WidgetWindow() {
  return Widget.Window({
    name: "purma-widget",
    visible: widgetState.bind().as(s => s.visible),
    child: Widget.Box({ children: [Header(), Content()] }),
  });
}

// Bar Button
export function WidgetButton() {
  return Widget.Button({
    on_clicked: () => toggleWidget(),
  });
}

// Toggle
export function toggleWidget() {
  widgetState.value = { ...widgetState.value, visible: !widgetState.value.visible };
}
    ]]></code>
  </pattern>

  <pattern name="API Endpoint Structure">
    <description>Endpoints FastAPI siguen este patrón:</description>
    <code><![CDATA[
@app.get("/module/status")
async def get_status():
    return {"status": "ok", "data": engine.get_status()}

@app.post("/module/action")
async def perform_action(request: ActionRequest):
    result = await engine.action(request.param)
    return {"success": True, "result": result}
    ]]></code>
  </pattern>

  <pattern name="CSS Color Variables">
    <description>Usar colores del tema Aurora consistentemente:</description>
    <code><![CDATA[
.widget-popup {
  background: #0d1117;  /* space */
  border: 1px solid #30363d;  /* stardust */
}

.widget-header {
  background: #161b22;  /* nebula */
}

.accent-btn {
  background: #00d4ff;  /* cyan - acento principal */
}

.success { color: #22c55e; }  /* green */
.warning { color: #f59e0b; }  /* yellow */
.error { color: #ef4444; }    /* red */
    ]]></code>
  </pattern>
</coding_patterns>

<future_modules>
  <module name="Purma Canvas" priority="high">
    <description>Generación de imágenes con Stable Diffusion</description>
  </module>
  <module name="Purma Guard" priority="high">
    <description>Monitor de seguridad y firewall inteligente</description>
  </module>
  <module name="Purma Notes" priority="medium">
    <description>Notas con búsqueda semántica AI</description>
  </module>
  <module name="Purma Clips" priority="medium">
    <description>Clipboard manager con historial AI</description>
  </module>
  <module name="Purma Search" priority="medium">
    <description>Búsqueda universal semántica</description>
  </module>
  <module name="Purma Mail" priority="low">
    <description>Cliente email con AI compose</description>
  </module>
  <module name="Purma Code" priority="high">
    <description>Copilot local con Ollama</description>
  </module>
  <module name="Purma Translate" priority="medium">
    <description>Traducción en tiempo real</description>
  </module>
  <module name="Purma Reader" priority="low">
    <description>Lector PDF con summarization</description>
  </module>
</future_modules>

<module name="Purma Sync">
  <description>Sistema de sincronización con móviles y organización AI automática</description>
  <backend>ai/server/purma_sync.py</backend>
  <mobile_api>ai/server/purma_mobile_api.py</mobile_api>
  <cli>bin/purma sync</cli>
  <storage>~/.purma/sync/sync.db</storage>

  <features>
    <feature>Hub central Linux para sincronización</feature>
    <feature>API REST para apps Android/iOS</feature>
    <feature>Emparejamiento por código QR/6 dígitos</feature>
    <feature>Organización automática por IA</feature>
    <feature>Categorización inteligente de archivos</feature>
    <feature>Sincronización incremental (solo cambios)</feature>
    <feature>Integración con Syncthing</feature>
  </features>

  <organize_modes>
    <mode name="disabled">Sin organización automática</mode>
    <mode name="manual">Organizar con comando explícito</mode>
    <mode name="auto">Organizar automáticamente nuevos archivos</mode>
    <mode name="smart">AI decide basándose en contenido</mode>
  </organize_modes>

  <file_categories>
    <category name="documents" icon="📄" extensions=".pdf,.doc,.docx,.txt,.md"/>
    <category name="images" icon="🖼️" extensions=".jpg,.png,.gif,.svg"/>
    <category name="videos" icon="🎬" extensions=".mp4,.mkv,.avi,.mov"/>
    <category name="audio" icon="🎵" extensions=".mp3,.flac,.wav,.ogg"/>
    <category name="code" icon="💻" extensions=".py,.js,.ts,.go,.rs"/>
    <category name="archives" icon="📦" extensions=".zip,.tar,.gz,.rar"/>
    <category name="data" icon="🗃️" extensions=".db,.sqlite,.json,.csv"/>
  </file_categories>

  <api_endpoints>
    <!-- Sync -->
    <endpoint method="GET" path="/sync/status">Estado del sistema sync</endpoint>
    <endpoint method="GET" path="/sync/folders">Listar carpetas sincronizadas</endpoint>
    <endpoint method="POST" path="/sync/folders">Añadir carpeta</endpoint>
    <endpoint method="DELETE" path="/sync/folders/{id}">Remover carpeta</endpoint>
    <endpoint method="POST" path="/sync/folders/{id}/organize">Organizar carpeta</endpoint>
    <endpoint method="GET" path="/sync/devices">Listar dispositivos</endpoint>
    <endpoint method="POST" path="/sync/now">Forzar sincronización</endpoint>

    <!-- Mobile API -->
    <endpoint method="POST" path="/mobile/pairing/generate">Generar código emparejamiento</endpoint>
    <endpoint method="POST" path="/mobile/pairing/complete">Completar emparejamiento</endpoint>
    <endpoint method="GET" path="/mobile/pairing/qr">Datos para QR code</endpoint>
    <endpoint method="GET" path="/mobile/sync/folders">Carpetas (autenticado)</endpoint>
    <endpoint method="GET" path="/mobile/sync/changes">Cambios incrementales</endpoint>
    <endpoint method="GET" path="/mobile/files/{folder}/{path}">Descargar archivo</endpoint>
    <endpoint method="POST" path="/mobile/files/{folder}">Subir archivo</endpoint>
  </api_endpoints>

  <cli_commands>
    <command>purma sync status - Estado de sincronización</command>
    <command>purma sync add --path ~/Docs - Añadir carpeta</command>
    <command>purma sync list - Listar carpetas</command>
    <command>purma sync remove --id X - Remover carpeta</command>
    <command>purma sync devices - Ver dispositivos</command>
    <command>purma sync now - Sincronizar ahora</command>
    <command>purma organize preview --path ~/Downloads - Vista previa</command>
    <command>purma organize run --id X --confirm - Ejecutar organización</command>
    <command>purma organize enable --id X --mode auto - Habilitar auto</command>
  </cli_commands>
</module>

<module name="Purma CLI">
  <description>Comando unificado para controlar todo PurmaLinux</description>
  <path>bin/purma</path>
  <executable>purma</executable>

  <subcommands>
    <subcommand name="status">Estado completo del sistema</subcommand>
    <subcommand name="chat">Chat interactivo con AI</subcommand>
    <subcommand name="sync">Gestión de sincronización</subcommand>
    <subcommand name="organize">Organización de archivos</subcommand>
    <subcommand name="vault">Gestor de contraseñas</subcommand>
    <subcommand name="cortex">Motor predictivo</subcommand>
    <subcommand name="memory">Búsqueda semántica</subcommand>
    <subcommand name="ghost">Sugerencias de automatización</subcommand>
    <subcommand name="agents">Sistema multi-agente</subcommand>
    <subcommand name="server">Control del servidor</subcommand>
    <subcommand name="config">Configuración</subcommand>
  </subcommands>

  <examples>
    <example>purma status</example>
    <example>purma chat "hola purma"</example>
    <example>purma sync add --path ~/Documents --organize auto</example>
    <example>purma organize preview --path ~/Downloads</example>
    <example>purma vault unlock</example>
    <example>purma cortex predict</example>
    <example>purma memory search "informe"</example>
    <example>purma agents run "analiza este código"</example>
  </examples>
</module>

<file_managers>
  <manager name="Thunar">
    <type>GUI</type>
    <config>desktop/thunar/uca.xml</config>
    <description>File manager gráfico con acciones AI personalizadas</description>
    <ai_actions>
      <action>Organizar con IA (preview/execute)</action>
      <action>Habilitar auto-organización</action>
      <action>Sincronizar con móvil</action>
      <action>Analizar con IA</action>
      <action>OCR (extraer texto)</action>
      <action>Indexar en Memory</action>
      <action>Code Review</action>
      <action>Explicar Código</action>
      <action>Resumir Documento</action>
    </ai_actions>
  </manager>

  <manager name="Yazi">
    <type>Terminal</type>
    <config>desktop/yazi/</config>
    <files>yazi.toml, keymap.toml, theme.toml</files>
    <description>File manager de terminal ultra-rápido con tema Aurora</description>
    <ai_keybindings prefix="A">
      <key>A o - Preview organización</key>
      <key>A O - Ejecutar organización</key>
      <key>A a - Auto-organización</key>
      <key>A i - Analizar archivo</key>
      <key>A s - Resumir</key>
      <key>A e - Explicar código</key>
      <key>A r - Code review</key>
      <key>A S - Añadir a sync</key>
      <key>A m - Indexar en Memory</key>
      <key>A t - OCR</key>
      <key>A c - Abrir chat</key>
      <key>A p - Predicciones</key>
      <key>A g - Ghost suggestions</key>
    </ai_keybindings>
  </manager>
</file_managers>

<integration_system>
  <description>Sistema de comunicación unificado que conecta todos los módulos Purma</description>
  <documentation>docs/INTEGRATION.md</documentation>

  <components>
    <component name="PurmaEventBus">
      <description>Bus de eventos pub/sub central</description>
      <file>ai/server/purma_integration.py</file>
      <features>
        <feature>Suscripciones por tipo de evento</feature>
        <feature>Suscripciones por patrón (wildcards: "ai.*")</feature>
        <feature>Persistencia de eventos en SQLite</feature>
        <feature>Priorización de eventos (1-10)</feature>
        <feature>Correlación de eventos relacionados</feature>
      </features>
    </component>

    <component name="PurmaContext">
      <description>Gestor de contexto global del sistema</description>
      <context_keys>
        <key>current_app</key>
        <key>current_workspace</key>
        <key>current_space</key>
        <key>user_state</key>
        <key>recent_apps</key>
        <key>recent_files</key>
        <key>recent_commands</key>
        <key>clipboard_content</key>
        <key>ai_suggestions</key>
        <key>vault_unlocked</key>
        <key>recording_active</key>
      </context_keys>
    </component>

    <component name="PurmaIntelligenceRouter">
      <description>Enrutador inteligente que decide qué módulo maneja cada consulta</description>
      <routing_keywords>
        <route keyword="password,contraseña,secret" module="vault"/>
        <route keyword="captura,screenshot,ocr" module="lens"/>
        <route keyword="grabar,transcribir,voz" module="scribe"/>
        <route keyword="sistema,cpu,memoria" module="pulse"/>
        <route keyword="predecir,patrón,aprender" module="cortex"/>
        <route keyword="buscar archivo,recordar" module="memory"/>
        <route keyword="sugerencia,automatización" module="ghost"/>
        <route keyword="agente,investigar,analizar" module="agents"/>
      </routing_keywords>
    </component>

    <component name="PurmaWorkflowOrchestrator">
      <description>Orquestador de flujos de trabajo entre módulos</description>
      <workflows>
        <workflow name="morning_routine">Rutina matutina: predicciones + notas + estado</workflow>
        <workflow name="focus_mode">Modo concentración: cambia espacio + DND + prepara apps</workflow>
        <workflow name="research_task">Investigación: agents + memory indexing</workflow>
        <workflow name="code_review">Code review: coder + reviewer agents</workflow>
        <workflow name="capture_and_analyze">Captura: lens + OCR + memory indexing</workflow>
        <workflow name="voice_command">Voz: scribe + router + ejecución</workflow>
      </workflows>
    </component>

    <component name="PurmaModule">
      <description>Clase base para todos los módulos integrados</description>
      <file>ai/server/purma_modules.py</file>
      <methods>
        <method>emit(event_type, data) - Emitir evento</method>
        <method>on(event_type, callback) - Suscribirse a evento</method>
        <method>process_query(query, context) - Procesar consulta</method>
        <method>get_status() - Obtener estado</method>
      </methods>
    </component>
  </components>

  <event_categories>
    <category name="system.*">Eventos del sistema operativo</category>
    <category name="user.*">Acciones del usuario</category>
    <category name="ai.*">Eventos de módulos AI</category>
    <category name="lens.*">Eventos de captura</category>
    <category name="vault.*">Eventos de vault</category>
    <category name="scribe.*">Eventos de voz</category>
    <category name="spaces.*">Eventos de espacios</category>
    <category name="flow.*">Eventos de workflows</category>
    <category name="pulse.*">Alertas de sistema</category>
  </event_categories>

  <api_endpoints>
    <endpoint method="GET" path="/integration/status">Estado del sistema de integración</endpoint>
    <endpoint method="GET" path="/integration/events">Consultar eventos recientes</endpoint>
    <endpoint method="POST" path="/integration/events">Publicar evento</endpoint>
    <endpoint method="GET" path="/integration/context">Obtener contexto actual</endpoint>
    <endpoint method="POST" path="/integration/route">Enrutar consulta a módulo</endpoint>
    <endpoint method="POST" path="/integration/smart-query">Enrutar y ejecutar consulta</endpoint>
    <endpoint method="POST" path="/integration/workflow/{name}">Ejecutar workflow</endpoint>
    <endpoint method="GET" path="/integration/modules">Listar módulos registrados</endpoint>
  </api_endpoints>

  <chat_commands>
    <command>/status - Estado completo del sistema</command>
    <command>/context - Ver contexto actual</command>
    <command>/workflow {name} - Ejecutar workflow</command>
    <command>/smart {query} - Consulta inteligente auto-enrutada</command>
    <command>/events {limit} - Ver eventos recientes</command>
    <command>/modules - Ver módulos registrados</command>
    <command>/morning - Ejecutar rutina matutina</command>
    <command>/research {topic} - Investigar tema</command>
    <command>/review {file} - Code review de archivo</command>
  </chat_commands>

  <data_flow>
    <step n="1">Usuario interactúa (app, comando, archivo, voz)</step>
    <step n="2">Módulo detecta y emite evento al EventBus</step>
    <step n="3">EventBus persiste y notifica suscriptores</step>
    <step n="4">PurmaContext actualiza estado global</step>
    <step n="5">Módulos suscritos reaccionan (Cortex aprende, Ghost observa, Memory indexa)</step>
    <step n="6">Si hay consulta, Router determina módulo destino</step>
    <step n="7">Orquestador coordina si es workflow multi-módulo</step>
    <step n="8">Respuesta regresa al usuario con contexto enriquecido</step>
  </data_flow>
</integration_system>

<notes>
  <note>El servidor AI debe estar corriendo en puerto 11435</note>
  <note>Ollama debe tener el modelo 'purma' disponible</note>
  <note>AGS maneja todos los widgets del desktop</note>
  <note>Los shortcuts de i3 y Openbox deben mantenerse sincronizados</note>
  <note>Cada módulo tiene su propio color de acento dentro del tema Aurora</note>
  <note>Los widgets usan Variable() para state management reactivo</note>
  <note>Las APIs retornan JSON consistente con {success, data/error}</note>
  <note>Brain es el panel de control unificado para Cortex, Memory, Ghost y Agents</note>
  <note>Cortex aprende patrones de uso y predice las siguientes aplicaciones</note>
  <note>Memory usa RAG local con FTS5 para búsqueda semántica de archivos</note>
  <note>Ghost observa silenciosamente y sugiere automatizaciones sin interrumpir</note>
  <note>Multi-Agent coordina 5 agentes especializados para tareas complejas</note>
  <note>Los módulos avanzados usan SQLite para persistencia local (~/.purma/)</note>
</notes>
