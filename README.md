<p align="center">
  <img src="assets/logo.svg" alt="PurmaLinux" width="600">
</p>

<p align="center">
  <strong>Where Local AI meets the Andes</strong>
  <br>
  <sub>Powered by Ollama & Local LLMs - Your data stays with you</sub>
</p>

<br>

```
                                        ⋆  ˚    ✦    ˚  ⋆
                    ⋆   ✧                   ✦              ✧   ⋆
              ✦              ⋆                     ⋆              ✦
                        ▲                 ▲
          ⋆     ▲      ╱ ╲    ▲         ╱░╲         ▲     ⋆
               ╱ ╲    ╱   ╲  ╱ ╲   ▲   ╱░░░╲   ▲   ╱ ╲
          ▲   ╱   ╲  ╱  ░  ╲╱   ╲ ╱ ╲ ╱░░░░░╲ ╱ ╲ ╱   ╲   ▲
         ╱ ╲ ╱  ░  ╲╱░░░░░░░╲ ░ ╳   ╳░░░░░░░░╳   ╳ ░░░ ╲ ╱ ╲
        ╱   ╳░░░░░░░░░░░░░░░░╲░╱ ╲ ╱░░░░░░░░░░╲ ╱ ╲░░░░░╳   ╲
       ╱░░░╱░░░░░░░░░░░░░░░░░░╳   ╳░░░░░░░░░░░░╳   ╳░░░░░╲░░░╲
    ▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔
         P   U   R   M   A   L   I   N   U   X       🧠  A I
```

<p align="center">
  <a href="#installation"><img src="https://img.shields.io/badge/Platform-Linux-00d4ff?style=for-the-badge&logo=linux&logoColor=white" alt="Platform"></a>
  <a href="#installation"><img src="https://img.shields.io/badge/Ollama-Local%20AI-ff6b6b?style=for-the-badge&logo=ollama&logoColor=white" alt="Ollama"></a>
  <a href="#installation"><img src="https://img.shields.io/badge/Python-3.11+-a855f7?style=for-the-badge&logo=python&logoColor=white" alt="Python"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-22c55e?style=for-the-badge" alt="License"></a>
</p>

<p align="center">
  <a href="#philosophy">Philosophy</a> •
  <a href="#modules">Modules</a> •
  <a href="#installation">Installation</a> •
  <a href="#usage">Usage</a> •
  <a href="#api">API</a> •
  <a href="#roadmap">Roadmap</a>
</p>

---

<br>

## 🌄 Philosophy

> *"Purma"* - Inspired by the majestic peaks of the Argentine Andes, where the air is clear and vision reaches far.

**PurmaLinux** is not just another Linux distribution with AI tools bolted on. It's an operating system where artificial intelligence is woven into the very fabric of the user experience.

### 🏠 Why Local AI?

```
┌─────────────────────────────────────────────────────────────────┐
│  🔒 PRIVACY      Your data never leaves your machine           │
│  ⚡ SPEED        No network latency, instant responses         │
│  💰 COST         No API fees, unlimited usage                  │
│  🌐 OFFLINE      Works without internet connection             │
│  🎛️ CONTROL      Choose and customize your models              │
└─────────────────────────────────────────────────────────────────┘
```

PurmaLinux uses **Ollama** as its AI runtime, supporting models like LLaMA, Mistral, CodeLlama, and more.

### 📦 Starter Packs

Choose a pack based on your hardware:

| Pack | RAM | Models | Use Case |
|------|-----|--------|----------|
| **Minimal** | 4GB | llama3.2:1b, nomic-embed | Basic chat, low resources |
| **Standard** | 8GB | llama3.2, codellama, nomic-embed | Most users |
| **Developer** | 16GB | llama3.2, deepseek-coder, codegemma | Full coding setup |
| **Creative** | 16GB | mistral, llava-llama3, moondream | Image analysis |
| **Power User** | 32GB+ | mixtral, deepseek-coder, llava | Everything |

```bash
# Check recommendation for your system
purma models recommend

# Install a pack
purma models pack standard
```

<table>
<tr>
<td width="50%">

### 🔗 Unified Communication
All modules communicate through a central **EventBus**, enabling seamless data flow and intelligent coordination.

### 🧠 Shared Context
The AI understands your complete system state, making decisions based on full awareness.

</td>
<td width="50%">

### ⚡ Intelligent Workflows
Multiple modules coordinate automatically to accomplish complex tasks without manual intervention.

### 🔮 Anticipation
The system learns your patterns and anticipates your needs before you express them.

</td>
</tr>
</table>

<br>

---

<br>

## 🏔️ Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│    ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐    │
│    │   Chat   │     │   Lens   │     │  Vault   │     │  Scribe  │    │
│    │    💬    │     │    👁️    │     │    🔐    │     │    🎤    │    │
│    └────┬─────┘     └────┬─────┘     └────┬─────┘     └────┬─────┘    │
│         │                │                │                │          │
│         └────────────────┴────────┬───────┴────────────────┘          │
│                                   │                                    │
│                    ┌──────────────┴──────────────┐                    │
│                    │       🚌 EventBus 🚌        │                    │
│                    │    Central Message System    │                    │
│                    └──────────────┬──────────────┘                    │
│                                   │                                    │
│         ┌────────────────┬───────┴────────┬────────────────┐          │
│         │                │                │                │          │
│    ┌────┴─────┐    ┌────┴─────┐    ┌────┴─────┐    ┌────┴─────┐     │
│    │  Cortex  │    │  Memory  │    │  Ghost   │    │  Agents  │     │
│    │    🧬    │    │    📚    │    │    👻    │    │    🤖    │     │
│    └──────────┘    └──────────┘    └──────────┘    └──────────┘     │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

<br>

---

<br>

## 📦 Modules

<details open>
<summary><h3>🎯 Core AI</h3></summary>

| Module | Icon | Description |
|:-------|:----:|:------------|
| **Purma Chat** | 💬 | Conversational interface powered by local AI models |
| **Purma Lens** | 👁️ | Vision AI for image analysis, OCR, and screenshots |
| **Purma Vault** | 🔐 | Secure secrets management with AES-256 encryption |
| **Purma Scribe** | 🎤 | Audio transcription and voice dictation |
| **Purma Brain** | 🧠 | Desktop widget with instant AI access |

</details>

<details open>
<summary><h3>⚡ Intelligence Layer</h3></summary>

| Module | Icon | Description |
|:-------|:----:|:------------|
| **Purma Cortex** | 🧬 | Predictive engine that learns your usage patterns |
| **Purma Memory** | 📚 | Personal knowledge base with semantic search |
| **Purma Ghost** | 👻 | Proactive assistant that suggests actions |
| **Purma Agents** | 🤖 | Multi-agent system for complex tasks |
| **Purma Spaces** | 🌐 | Context-aware work environments |
| **Purma Pulse** | 💓 | System health and wellness monitoring |
| **Purma Models** | 🤖 | Easy download and management of local AI models |

</details>

<details open>
<summary><h3>🔄 Sync & Organization</h3></summary>

| Module | Icon | Description |
|:-------|:----:|:------------|
| **Purma Sync** | 📱 | Mobile device synchronization hub |
| **AI Organizer** | 📁 | Intelligent automatic file organization |
| **File Managers** | 🗂️ | Deep integration with Thunar & Yazi |

</details>

<br>

---

<br>

## 🚀 Installation

### Prerequisites

```
┌────────────────────────────────────────┐
│  ✓ Python 3.11+                        │
│  ✓ Ollama (local AI runtime)           │
│  ✓ Arch Linux (recommended)            │
│  ✓ 8GB RAM minimum (16GB recommended)  │
│  ○ CUDA GPU (optional, faster inference│
└────────────────────────────────────────┘
```

### Quick Start

```bash
# Clone the repository
git clone https://github.com/matware-lab/PurmaLinux.git
cd PurmaLinux

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install Ollama and pull a model
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.2

# Launch the server
python ai/server/purma_server.py
```

### CLI Installation

```bash
# Make CLI executable
chmod +x bin/purma

# Create system-wide symlink
sudo ln -s $(pwd)/bin/purma /usr/local/bin/purma

# Verify installation
purma status
```

<br>

---

<br>

## 💻 Usage

<table>
<tr>
<td width="50%">

### 💬 Chat with AI
```bash
# Interactive mode
purma chat

# Direct query
purma chat "Explain this code"
```

### 📁 File Organization
```bash
# Preview changes
purma organize preview ~/Downloads

# Execute organization
purma organize run ~/Downloads

# Enable auto-organize
purma organize enable ~/Downloads --mode smart
```

</td>
<td width="50%">

### 🔄 Synchronization
```bash
# Add sync folder
purma sync add ~/Documents --name "Docs"

# List synced folders
purma sync list

# View devices
purma sync devices
```

### 🔐 Secrets Vault
```bash
# Check status
purma vault status

# Generate password
purma vault generate --length 32

# Retrieve secret
purma vault get github_token
```

</td>
</tr>
</table>

### 🤖 Model Management

```bash
# List installed models
purma models list

# See available models
purma models available

# Install a model
purma models install llama3.2

# Install a starter pack
purma models packs              # See available packs
purma models pack standard      # Install standard pack

# Get recommendation for your system
purma models recommend
```

### ⚡ Advanced Commands

```bash
# Predictive suggestions
purma cortex predict

# Search knowledge base
purma memory search "nginx configuration"

# Run specialized agents
purma agents list
purma agents run code_reviewer

# Server management
purma server start
purma server logs
```

<br>

---

<br>

## 🗂️ File Manager Integration

<table>
<tr>
<td width="50%" align="center">

### 🖱️ Thunar (GUI)

Right-click context menu:

```
📁 Organize with AI
🔄 Enable Auto-organization
📱 Sync Folder
🔍 Analyze with AI
📝 Extract Text (OCR)
👁️ Code Review
💡 Explain File
📋 Summarize Document
```

</td>
<td width="50%" align="center">

### ⌨️ Yazi (Terminal)

AI keybindings (`A` prefix):

```
A o  →  Preview organization
A O  →  Execute organization
A s  →  Add to sync
A i  →  Analyze file
A r  →  Code review
A e  →  Explain file
A t  →  Extract text (OCR)
A ?  →  AI help
```

</td>
</tr>
</table>

<br>

---

<br>

## 🌐 API

The server exposes a REST API at `http://localhost:11435`

```
┌─────────────────────────────────────────────────────────────┐
│  ENDPOINT                  │  METHOD  │  DESCRIPTION        │
├─────────────────────────────────────────────────────────────┤
│  /chat                     │  POST    │  Send message to AI │
│  /sync/folders             │  GET     │  List sync folders  │
│  /sync/folder              │  POST    │  Add sync folder    │
│  /mobile/pairing/generate  │  POST    │  Get pairing code   │
│  /mobile/sync/folders      │  GET     │  Mobile folder list │
│  /integration/workflow     │  POST    │  Run workflow       │
│  /integration/context      │  GET     │  Get system context │
└─────────────────────────────────────────────────────────────┘
```

### 📱 Mobile Pairing

```bash
# Generate 6-digit pairing code
curl http://localhost:11435/mobile/pairing/generate

# Or via CLI
purma sync pair
```

<br>

---

<br>

## 🎨 Aurora Theme

<table>
<tr>
<td align="center"><img src="https://via.placeholder.com/60/00d4ff/00d4ff" alt="Cyan"><br><code>#00d4ff</code><br>Primary</td>
<td align="center"><img src="https://via.placeholder.com/60/a855f7/a855f7" alt="Purple"><br><code>#a855f7</code><br>Secondary</td>
<td align="center"><img src="https://via.placeholder.com/60/22c55e/22c55e" alt="Green"><br><code>#22c55e</code><br>Success</td>
<td align="center"><img src="https://via.placeholder.com/60/f59e0b/f59e0b" alt="Orange"><br><code>#f59e0b</code><br>Warning</td>
<td align="center"><img src="https://via.placeholder.com/60/ef4444/ef4444" alt="Red"><br><code>#ef4444</code><br>Error</td>
<td align="center"><img src="https://via.placeholder.com/60/0d1117/0d1117" alt="Dark"><br><code>#0d1117</code><br>Background</td>
</tr>
</table>

<br>

---

<br>

## 📂 Project Structure

```
PurmaLinux/
│
├── 🤖 ai/
│   └── server/
│       ├── purma_server.py       # Main FastAPI server
│       ├── purma_models.py       # AI model management
│       ├── purma_sync.py         # Synchronization engine
│       ├── purma_integration.py  # EventBus & orchestration
│       ├── purma_modules.py      # Module adapters
│       └── purma_mobile_api.py   # Mobile REST API
│
├── 📦 base/
│   ├── packages.txt              # System packages
│   └── configs/                  # Base configurations
│
├── 🔧 bin/
│   └── purma                     # Unified CLI tool
│
├── 🖥️ desktop/
│   ├── thunar/
│   │   └── uca.xml               # Custom Actions
│   └── yazi/
│       ├── yazi.toml             # Configuration
│       ├── keymap.toml           # AI keybindings
│       └── theme.toml            # Aurora theme
│
├── 📚 docs/
│   └── INTEGRATION.md            # Integration guide
│
├── 🎨 assets/
│   └── logo.svg                  # Project logo
│
└── 📋 README.md
```

<br>

---

<br>

## 🗺️ Roadmap

<table>
<tr><td>📱</td><td><strong>Native Mobile App</strong></td><td>Flutter-based companion app</td></tr>
<tr><td>🔮</td><td><strong>Purma Anticipate</strong></td><td>Predictive needs engine</td></tr>
<tr><td>📅</td><td><strong>Purma Timeline</strong></td><td>Visual activity history</td></tr>
<tr><td>🛡️</td><td><strong>Purma Focus Shield</strong></td><td>Intelligent distraction blocking</td></tr>
<tr><td>📊</td><td><strong>Purma Habits</strong></td><td>Behavioral pattern tracking</td></tr>
<tr><td>🌙</td><td><strong>Purma Dream</strong></td><td>Overnight organization & maintenance</td></tr>
<tr><td>🌍</td><td><strong>Multi-language</strong></td><td>Internationalization support</td></tr>
<tr><td>🔌</td><td><strong>Plugin System</strong></td><td>Third-party extensions</td></tr>
</table>

<br>

---

<br>

## 🤝 Contributing

```
1. Fork the repository
2. Create feature branch    →  git checkout -b feature/amazing-feature
3. Commit your changes      →  git commit -m 'Add amazing feature'
4. Push to branch           →  git push origin feature/amazing-feature
5. Open a Pull Request
```

<br>

---

<br>

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

<br>

---

<p align="center">
  <br>
  <img src="https://img.shields.io/badge/Powered%20by-🏠%20Local%20AI-00d4ff?style=for-the-badge" alt="Powered by Local AI">
  <br><br>
  <strong>PurmaLinux</strong> — <em>Where local AI meets the mountains</em>
  <br>
  <sub>Your data. Your hardware. Your AI.</sub>
  <br><br>
  ⭐ Star this repo if you find it useful!
</p>
