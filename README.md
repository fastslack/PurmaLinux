# PurmaLinux

**AI-First Linux Distribution** - An operating system that integrates artificial intelligence into every aspect of the user experience.

![PurmaLinux](https://img.shields.io/badge/PurmaLinux-AI%20First-00d4ff?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.11+-blue?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

> **Author:** Matías Aguirre
> **Company:** [Matware](https://matware.nl)
> **Project:** PurmaLinux

## Philosophy

PurmaLinux is not just a Linux distribution with AI tools added on. It's an operating system where artificial intelligence is integrated from the core, enabling:

- **Unified communication** between all modules via EventBus
- **Shared context** that allows AI to understand the complete system state
- **Intelligent workflows** that automatically coordinate multiple modules
- **Anticipation** of user needs based on usage patterns

## Architecture

```
+------------------+     +------------------+     +------------------+
|   Purma Chat     |     |   Purma Lens     |     |   Purma Vault    |
|   (Interface)    |     |   (Vision AI)    |     |   (Secrets)      |
+--------+---------+     +--------+---------+     +--------+---------+
         |                        |                        |
         +------------------------+------------------------+
                                  |
                    +-------------+-------------+
                    |      PurmaEventBus        |
                    |     (Event System)        |
                    +-------------+-------------+
                                  |
         +------------------------+------------------------+
         |                        |                        |
+--------+---------+     +--------+---------+     +--------+---------+
|  Purma Cortex    |     |  Purma Memory    |     |   Purma Ghost    |
|  (Prediction)    |     |  (Knowledge)     |     |  (Proactive)     |
+------------------+     +------------------+     +------------------+
```

## Modules

### Core AI

| Module | Description |
|--------|-------------|
| **Purma Chat** | Conversational interface with Claude AI |
| **Purma Lens** | Vision AI for image analysis, OCR, screenshots |
| **Purma Vault** | Secure secrets management with AES-256 encryption |
| **Purma Scribe** | Audio transcription and dictation |
| **Purma Brain** | Desktop widget with quick access |

### Intelligence Layer

| Module | Description |
|--------|-------------|
| **Purma Cortex** | Predictive engine that learns usage patterns |
| **Purma Memory** | Indexed personal knowledge base |
| **Purma Ghost** | Proactive assistant that suggests actions |
| **Purma Agents** | Multi-agent system for complex tasks |
| **Purma Spaces** | Specialized work contexts |
| **Purma Pulse** | System and wellness monitoring |

### Sync & Organization

| Module | Description |
|--------|-------------|
| **Purma Sync** | Synchronization with mobile devices |
| **AI Organizer** | Intelligent file organization |
| **File Managers** | Integration with Thunar and Yazi |

## Installation

### Requirements

- Python 3.11+
- Arch Linux (recommended base)
- 8GB RAM minimum
- CUDA compatible GPU (optional, for acceleration)

### Quick Install

```bash
# Clone repository
git clone https://github.com/user/PurmaLinux.git
cd PurmaLinux

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure API key
export ANTHROPIC_API_KEY="your-api-key"

# Start server
python ai/server/purma_server.py
```

### CLI

```bash
# Install CLI globally
chmod +x bin/purma
sudo ln -s $(pwd)/bin/purma /usr/local/bin/purma

# Verify installation
purma status
```

## Usage

### Chat with AI

```bash
# Interactive chat
purma chat

# Direct command
purma chat "Explain this code"
```

### Synchronization

```bash
# Add folder to sync
purma sync add ~/Documents --name "My Documents"

# List synced folders
purma sync list

# View connected devices
purma sync devices
```

### File Organization

```bash
# Preview organization
purma organize preview ~/Downloads

# Execute organization
purma organize run ~/Downloads

# Enable auto-organization
purma organize enable ~/Downloads --mode smart
```

### Vault (Secrets)

```bash
# Vault status
purma vault status

# Generate password
purma vault generate --length 32

# Get secret
purma vault get github_token
```

### Other Commands

```bash
# Predictive system
purma cortex predict

# Knowledge base
purma memory search "nginx configuration"

# Specialized agents
purma agents list
purma agents run code_reviewer

# Server
purma server start
purma server logs
```

## File Manager Integration

### Thunar (GUI)

Custom Actions are installed at:
`~/.config/Thunar/uca.xml`

Available actions via right-click:
- Organize with AI
- Enable Auto-organization
- Sync Folder
- Analyze with AI
- Extract Text (OCR)
- Code Review
- Explain File
- Summarize Document

### Yazi (Terminal)

Keybindings with `A` prefix (AI):
- `A o` - Preview organization
- `A O` - Execute organization
- `A s` - Add to sync
- `A i` - Analyze file
- `A r` - Code review
- `A e` - Explain file
- `A t` - Extract text OCR
- `A ?` - AI help

## REST API

The server exposes a REST API at `http://localhost:11435`:

```bash
# Chat
POST /chat
{"message": "Hello", "context": {}}

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

PurmaLinux acts as a central hub. The mobile app (Android/iOS) connects via:

1. **Code pairing**: The hub generates a 6-digit code
2. **QR pairing**: Scan QR from the app
3. **Sync**: Selected folders sync automatically

```bash
# Generate pairing code
curl http://localhost:11435/mobile/pairing/generate

# Or via CLI
purma sync pair
```

## Configuration

The configuration file is located at `~/.purma/config.json`:

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

## Project Structure

```
PurmaLinux/
├── ai/
│   └── server/
│       ├── purma_server.py      # Main FastAPI server
│       ├── purma_sync.py        # Sync engine
│       ├── purma_integration.py # Integration system
│       ├── purma_modules.py     # Module adapters
│       └── purma_mobile_api.py  # Mobile API
├── base/
│   ├── packages.txt             # System packages
│   └── configs/                 # Base configurations
├── bin/
│   └── purma                    # Unified CLI
├── desktop/
│   ├── thunar/
│   │   └── uca.xml              # Custom Actions
│   └── yazi/
│       ├── yazi.toml            # Configuration
│       ├── keymap.toml          # Keybindings
│       └── theme.toml           # Aurora theme
├── docs/
│   └── INTEGRATION.md           # Integration documentation
├── CLAUDE.md                    # AI documentation
└── README.md
```

## Aurora Theme

PurmaLinux uses the "Aurora" theme with the following palette:

| Color | Hex | Usage |
|-------|-----|-------|
| Cyan | `#00d4ff` | Primary, accents |
| Purple | `#a855f7` | Secondary |
| Green | `#22c55e` | Success, confirmation |
| Orange | `#f59e0b` | Warnings |
| Red | `#ef4444` | Errors |
| Dark | `#0d1117` | Background |
| Gray | `#8b949e` | Secondary text |

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/new-feature`)
3. Commit your changes (`git commit -m 'Add new feature'`)
4. Push to branch (`git push origin feature/new-feature`)
5. Open a Pull Request

## Roadmap

- [ ] Native mobile app (Flutter)
- [ ] Purma Anticipate (needs prediction)
- [ ] Purma Timeline (visual history)
- [ ] Purma Focus Shield (distraction protection)
- [ ] Purma Habits (habit tracking)
- [ ] Purma Dream (overnight organization)
- [ ] Multi-language support
- [ ] Third-party plugins

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

**PurmaLinux** - *Where artificial intelligence meets Linux*
