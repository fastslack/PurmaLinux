# PurmaLinux

**AI-First Linux Distribution** - Un sistema operativo que integra inteligencia artificial en cada aspecto de la experiencia de usuario.

![PurmaLinux](https://img.shields.io/badge/PurmaLinux-AI%20First-00d4ff?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.11+-blue?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

> **Autor:** Matías Aguirre
> **Empresa:** [Matware](https://matware.nl)
> **Proyecto:** PurmaLinux

## Filosofia

PurmaLinux no es solo una distribucion Linux con herramientas AI agregadas. Es un sistema operativo donde la inteligencia artificial esta integrada desde el nucleo, permitiendo:

- **Comunicacion unificada** entre todos los modulos via EventBus
- **Contexto compartido** que permite a la AI entender el estado completo del sistema
- **Workflows inteligentes** que coordinan multiples modulos automaticamente
- **Anticipacion** de necesidades del usuario basada en patrones de uso

## Arquitectura

```
+------------------+     +------------------+     +------------------+
|   Purma Chat     |     |   Purma Lens     |     |   Purma Vault    |
|   (Interfaz)     |     |   (Vision AI)    |     |   (Secretos)     |
+--------+---------+     +--------+---------+     +--------+---------+
         |                        |                        |
         +------------------------+------------------------+
                                  |
                    +-------------+-------------+
                    |      PurmaEventBus        |
                    |   (Sistema de Eventos)    |
                    +-------------+-------------+
                                  |
         +------------------------+------------------------+
         |                        |                        |
+--------+---------+     +--------+---------+     +--------+---------+
|  Purma Cortex    |     |  Purma Memory    |     |   Purma Ghost    |
|  (Prediccion)    |     |  (Conocimiento)  |     |  (Proactividad)  |
+------------------+     +------------------+     +------------------+
```

## Modulos

### Core AI

| Modulo | Descripcion |
|--------|-------------|
| **Purma Chat** | Interfaz conversacional con Claude AI |
| **Purma Lens** | Vision AI para analisis de imagenes, OCR, screenshots |
| **Purma Vault** | Gestion segura de secretos con cifrado AES-256 |
| **Purma Scribe** | Transcripcion de audio y dictado |
| **Purma Brain** | Widget de escritorio con acceso rapido |

### Intelligence Layer

| Modulo | Descripcion |
|--------|-------------|
| **Purma Cortex** | Motor predictivo que aprende patrones de uso |
| **Purma Memory** | Base de conocimiento personal indexada |
| **Purma Ghost** | Asistente proactivo que sugiere acciones |
| **Purma Agents** | Sistema multi-agente para tareas complejas |
| **Purma Spaces** | Contextos de trabajo especializados |
| **Purma Pulse** | Monitoreo de sistema y bienestar |

### Sync & Organization

| Modulo | Descripcion |
|--------|-------------|
| **Purma Sync** | Sincronizacion con dispositivos moviles |
| **AI Organizer** | Organizacion inteligente de archivos |
| **File Managers** | Integracion con Thunar y Yazi |

## Instalacion

### Requisitos

- Python 3.11+
- Arch Linux (base recomendada)
- 8GB RAM minimo
- GPU compatible con CUDA (opcional, para aceleracion)

### Instalacion Rapida

```bash
# Clonar repositorio
git clone https://github.com/tu-usuario/PurmaLinux.git
cd PurmaLinux

# Crear entorno virtual
python -m venv .venv
source .venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar API key
export ANTHROPIC_API_KEY="tu-api-key"

# Iniciar servidor
python ai/server/purma_server.py
```

### CLI

```bash
# Instalar CLI globalmente
chmod +x bin/purma
sudo ln -s $(pwd)/bin/purma /usr/local/bin/purma

# Verificar instalacion
purma status
```

## Uso

### Chat con AI

```bash
# Chat interactivo
purma chat

# Comando directo
purma chat "Explica este codigo"
```

### Sincronizacion

```bash
# Agregar carpeta a sync
purma sync add ~/Documents --name "Mis Documentos"

# Listar carpetas sincronizadas
purma sync list

# Ver dispositivos conectados
purma sync devices
```

### Organizacion de Archivos

```bash
# Vista previa de organizacion
purma organize preview ~/Downloads

# Ejecutar organizacion
purma organize run ~/Downloads

# Habilitar auto-organizacion
purma organize enable ~/Downloads --mode smart
```

### Vault (Secretos)

```bash
# Estado del vault
purma vault status

# Generar password
purma vault generate --length 32

# Obtener secreto
purma vault get github_token
```

### Otros Comandos

```bash
# Sistema predictivo
purma cortex predict

# Base de conocimiento
purma memory search "configuracion nginx"

# Agentes especializados
purma agents list
purma agents run code_reviewer

# Servidor
purma server start
purma server logs
```

## Integracion con File Managers

### Thunar (GUI)

Las Custom Actions se instalan en:
`~/.config/Thunar/uca.xml`

Acciones disponibles via click derecho:
- Organizar con IA
- Habilitar Auto-organizacion
- Sincronizar Carpeta
- Analizar con IA
- Extraer Texto (OCR)
- Code Review
- Explicar Archivo
- Resumir Documento

### Yazi (Terminal)

Keybindings con prefijo `A` (AI):
- `A o` - Preview organizacion
- `A O` - Ejecutar organizacion
- `A s` - Agregar a sync
- `A i` - Analizar archivo
- `A r` - Code review
- `A e` - Explicar archivo
- `A t` - Extraer texto OCR
- `A ?` - Ayuda AI

## API REST

El servidor expone una API REST en `http://localhost:11435`:

```bash
# Chat
POST /chat
{"message": "Hola", "context": {}}

# Sync
GET /sync/folders
POST /sync/folder

# Mobile
POST /mobile/pairing/generate
GET /mobile/sync/folders

# Integration
POST /integration/workflow
GET /integration/context
```

## Mobile App

PurmaLinux actua como hub central. La app movil (Android/iOS) se conecta via:

1. **Emparejamiento por codigo**: El hub genera un codigo de 6 digitos
2. **Emparejamiento por QR**: Escanear QR desde la app
3. **Sincronizacion**: Las carpetas seleccionadas se sincronizan automaticamente

```bash
# Generar codigo de emparejamiento
curl http://localhost:11435/mobile/pairing/generate

# O via CLI
purma sync pair
```

## Configuracion

El archivo de configuracion se encuentra en `~/.purma/config.json`:

```json
{
  "api_key": "sk-...",
  "model": "claude-sonnet-4-20250514",
  "theme": "aurora",
  "sync": {
    "auto_organize": true,
    "organize_mode": "smart"
  },
  "ghost": {
    "enabled": true,
    "proactivity_level": "balanced"
  }
}
```

## Estructura del Proyecto

```
PurmaLinux/
├── ai/
│   └── server/
│       ├── purma_server.py      # Servidor principal FastAPI
│       ├── purma_sync.py        # Motor de sincronizacion
│       ├── purma_integration.py # Sistema de integracion
│       ├── purma_modules.py     # Adaptadores de modulos
│       └── purma_mobile_api.py  # API movil
├── base/
│   ├── packages.txt             # Paquetes del sistema
│   └── configs/                 # Configuraciones base
├── bin/
│   └── purma                    # CLI unificado
├── desktop/
│   ├── thunar/
│   │   └── uca.xml              # Custom Actions
│   └── yazi/
│       ├── yazi.toml            # Configuracion
│       ├── keymap.toml          # Keybindings
│       └── theme.toml           # Tema Aurora
├── docs/
│   └── INTEGRATION.md           # Documentacion de integracion
├── CLAUDE.md                    # Documentacion para AI
└── README.md
```

## Tema Aurora

PurmaLinux usa el tema "Aurora" con la siguiente paleta:

| Color | Hex | Uso |
|-------|-----|-----|
| Cyan | `#00d4ff` | Primario, acentos |
| Purple | `#a855f7` | Secundario |
| Green | `#22c55e` | Exito, confirmacion |
| Orange | `#f59e0b` | Advertencias |
| Red | `#ef4444` | Errores |
| Dark | `#0d1117` | Fondo |
| Gray | `#8b949e` | Texto secundario |

## Contribuir

1. Fork el repositorio
2. Crea una rama para tu feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit tus cambios (`git commit -m 'Agrega nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Abre un Pull Request

## Roadmap

- [ ] App movil nativa (Flutter)
- [ ] Purma Anticipate (prediccion de necesidades)
- [ ] Purma Timeline (historial visual)
- [ ] Purma Focus Shield (proteccion de distracciones)
- [ ] Purma Habits (seguimiento de habitos)
- [ ] Purma Dream (organizacion nocturna)
- [ ] Soporte multi-idioma
- [ ] Plugins de terceros

## Licencia

Este proyecto esta bajo la Licencia MIT. Ver el archivo [LICENSE](LICENSE) para mas detalles.

## Creditos

- **Claude AI** by Anthropic - Motor de inteligencia artificial
- **FastAPI** - Framework web
- **Yazi** - Terminal file manager
- **Thunar** - GUI file manager

---

**PurmaLinux** - *Donde la inteligencia artificial se encuentra con Linux*
