#!/bin/bash
#
# PurmaLinux - VM Post-Installation Script
# Para usar después de instalar Ubuntu Server 24.04 ARM64 en UTM
#
# Uso:
#   curl -fsSL https://raw.githubusercontent.com/tu-usuario/PurmaLinux/main/dev/vm-post-install.sh | bash
#   # O si ya tienes el repo:
#   ./dev/vm-post-install.sh
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

log() { echo -e "${BLUE}[$(date '+%H:%M:%S')]${NC} $1"; }
success() { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[✗]${NC} $1"; exit 1; }

clear
echo ""
echo -e "${MAGENTA}"
cat << 'EOF'
    ____                             __    _
   / __ \__  _________ ___  ____ _  / /   (_)___  __  ___  __
  / /_/ / / / / ___/ __ `__ \/ __ `/ / /   / / __ \/ / / / |/_/
 / ____/ /_/ / /  / / / / / / /_/ / / /___/ / / / / /_/ />  <
/_/    \__,_/_/  /_/ /_/ /_/\__,_/ /_____/_/_/ /_/\__,_/_/|_|

EOF
echo -e "${NC}"
echo -e "${CYAN}         VM Development Environment Setup${NC}"
echo -e "${CYAN}              Ubuntu Server ARM64${NC}"
echo ""
echo "════════════════════════════════════════════════════════════════"
echo ""

# Check if running as root
if [[ $EUID -eq 0 ]]; then
    error "No ejecutar como root. Usa tu usuario normal."
fi

# Check Ubuntu
if ! grep -q "Ubuntu" /etc/os-release 2>/dev/null; then
    error "Este script requiere Ubuntu"
fi

ARCH=$(uname -m)
log "Arquitectura detectada: ${CYAN}$ARCH${NC}"

if [[ "$ARCH" != "aarch64" && "$ARCH" != "arm64" ]]; then
    warn "No es ARM64. El script continuará pero puede haber diferencias."
fi

# ═══════════════════════════════════════════════════════════════════
# FASE 1: Sistema base
# ═══════════════════════════════════════════════════════════════════
echo ""
log "${YELLOW}[1/6]${NC} Actualizando sistema..."
sudo apt update && sudo apt upgrade -y

log "Instalando herramientas esenciales..."
sudo apt install -y \
    git \
    curl \
    wget \
    unzip \
    build-essential \
    pkg-config \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release

success "Sistema base actualizado"

# ═══════════════════════════════════════════════════════════════════
# FASE 2: Entorno gráfico mínimo
# ═══════════════════════════════════════════════════════════════════
echo ""
log "${YELLOW}[2/6]${NC} Instalando entorno gráfico..."

sudo apt install -y \
    xorg \
    xserver-xorg \
    xinit \
    lightdm \
    lightdm-gtk-greeter \
    dbus-x11

# Window managers
sudo apt install -y \
    openbox \
    obconf \
    i3-wm \
    i3status \
    i3lock

# Utilidades gráficas
sudo apt install -y \
    picom \
    rofi \
    dunst \
    feh \
    polybar \
    lxappearance \
    pcmanfm \
    thunar \
    kitty \
    xdg-utils \
    xclip \
    maim \
    slop

success "Entorno gráfico instalado"

# ═══════════════════════════════════════════════════════════════════
# FASE 3: AGS (Aylur's GTK Shell)
# ═══════════════════════════════════════════════════════════════════
echo ""
log "${YELLOW}[3/6]${NC} Instalando AGS y dependencias GTK..."

# Dependencias para AGS
sudo apt install -y \
    gjs \
    libgtk-3-dev \
    libgtk-layer-shell-dev \
    libpulse-dev \
    libnm-dev \
    libsoup-3.0-dev \
    libjson-glib-dev \
    libgirepository1.0-dev \
    gobject-introspection \
    gir1.2-gtk-3.0 \
    gir1.2-gtklayershell-0.1 \
    gir1.2-nm-1.0 \
    gir1.2-soup-3.0 \
    typescript \
    npm

# Instalar AGS
if ! command -v ags &> /dev/null; then
    log "Instalando AGS desde fuente..."
    cd /tmp
    git clone --depth 1 https://github.com/Aylur/ags.git
    cd ags
    npm install
    sudo npm link
    cd ~
    success "AGS instalado"
else
    success "AGS ya está instalado"
fi

# ═══════════════════════════════════════════════════════════════════
# FASE 4: Python y dependencias AI
# ═══════════════════════════════════════════════════════════════════
echo ""
log "${YELLOW}[4/6]${NC} Configurando Python y stack AI..."

sudo apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    python3-gi \
    python3-gi-cairo \
    python3-dbus

# Dependencias para Whisper/Audio
sudo apt install -y \
    ffmpeg \
    portaudio19-dev \
    libsndfile1-dev \
    espeak-ng

# Dependencias para OCR
sudo apt install -y \
    tesseract-ocr \
    tesseract-ocr-spa \
    tesseract-ocr-eng \
    libtesseract-dev

success "Python y dependencias instaladas"

# ═══════════════════════════════════════════════════════════════════
# FASE 5: Ollama
# ═══════════════════════════════════════════════════════════════════
echo ""
log "${YELLOW}[5/6]${NC} Instalando Ollama..."

if ! command -v ollama &> /dev/null; then
    curl -fsSL https://ollama.com/install.sh | sh
    success "Ollama instalado"
else
    success "Ollama ya está instalado"
fi

# Iniciar servicio Ollama
sudo systemctl enable ollama
sudo systemctl start ollama

# Esperar a que Ollama esté listo
log "Esperando a que Ollama inicie..."
sleep 5

# Descargar modelo base
log "Descargando modelo llama3.2 (puede tardar varios minutos)..."
ollama pull llama3.2 || warn "No se pudo descargar llama3.2, descargar manualmente después"

success "Ollama configurado"

# ═══════════════════════════════════════════════════════════════════
# FASE 6: Clonar/Configurar PurmaLinux
# ═══════════════════════════════════════════════════════════════════
echo ""
log "${YELLOW}[6/6]${NC} Configurando PurmaLinux..."

PURMA_DIR="$HOME/PurmaLinux"

# Si el script se ejecuta desde el repo, usar ese directorio
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$SCRIPT_DIR/../install.sh" ]]; then
    PURMA_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
    log "Usando directorio existente: $PURMA_DIR"
else
    # Clonar si no existe
    if [[ ! -d "$PURMA_DIR" ]]; then
        log "Clonando repositorio PurmaLinux..."
        # Cambiar por tu URL de repo
        git clone https://github.com/tu-usuario/PurmaLinux.git "$PURMA_DIR" || {
            warn "No se pudo clonar. Creando directorio vacío..."
            mkdir -p "$PURMA_DIR"
        }
    fi
fi

# Crear entorno virtual Python
log "Creando entorno virtual Python..."
cd "$PURMA_DIR"
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias Python
if [[ -f "ai/server/requirements.txt" ]]; then
    pip install --upgrade pip
    pip install -r ai/server/requirements.txt
    success "Dependencias Python instaladas"
else
    log "Instalando dependencias Python manualmente..."
    pip install --upgrade pip
    pip install \
        fastapi \
        uvicorn[standard] \
        httpx \
        websockets \
        pillow \
        pytesseract \
        cryptography \
        psutil \
        aiosqlite \
        aiofiles \
        watchdog \
        numpy \
        python-multipart
    success "Dependencias Python instaladas"
fi

# Crear directorios de datos
mkdir -p ~/.purma/{cortex,memory,ghost,vault,scribe,sync,lens}
mkdir -p ~/.local/bin

# Copiar binarios a PATH
if [[ -d "$PURMA_DIR/bin" ]]; then
    cp -r "$PURMA_DIR/bin/"* ~/.local/bin/ 2>/dev/null || true
    chmod +x ~/.local/bin/* 2>/dev/null || true
fi

# Añadir a PATH si no está
if ! grep -q '.local/bin' ~/.bashrc; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
fi

success "PurmaLinux configurado"

# ═══════════════════════════════════════════════════════════════════
# CONFIGURACIÓN FINAL
# ═══════════════════════════════════════════════════════════════════
echo ""
echo "════════════════════════════════════════════════════════════════"
echo ""

# Crear script de inicio rápido
cat > ~/.local/bin/purma-dev << 'DEVSCRIPT'
#!/bin/bash
# Script de desarrollo rápido para PurmaLinux

PURMA_DIR="$HOME/PurmaLinux"
cd "$PURMA_DIR"
source venv/bin/activate

case "$1" in
    server)
        echo "Iniciando servidor Purma..."
        python ai/server/purma_server.py
        ;;
    chat)
        echo "Iniciando chat CLI..."
        python ai/chat/purma-chat-cli.py
        ;;
    test)
        echo "Probando conexión con Ollama..."
        curl -s http://localhost:11434/api/tags | python3 -m json.tool
        ;;
    logs)
        journalctl -u ollama -f
        ;;
    *)
        echo "Uso: purma-dev {server|chat|test|logs}"
        echo ""
        echo "  server  - Iniciar servidor FastAPI (puerto 11435)"
        echo "  chat    - Iniciar chat CLI"
        echo "  test    - Probar conexión con Ollama"
        echo "  logs    - Ver logs de Ollama"
        ;;
esac
DEVSCRIPT
chmod +x ~/.local/bin/purma-dev

# Crear servicio systemd para desarrollo
mkdir -p ~/.config/systemd/user
cat > ~/.config/systemd/user/purma-server.service << 'SYSTEMD'
[Unit]
Description=PurmaLinux AI Server (Development)
After=network.target ollama.service

[Service]
Type=simple
WorkingDirectory=%h/PurmaLinux
Environment="PATH=%h/PurmaLinux/venv/bin:%h/.local/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=%h/PurmaLinux/venv/bin/python ai/server/purma_server.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
SYSTEMD

systemctl --user daemon-reload

echo -e "${GREEN}"
cat << 'EOF'
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║         ¡Entorno de desarrollo configurado!                      ║
║                                                                  ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  Comandos disponibles:                                           ║
║                                                                  ║
║    purma-dev server   → Iniciar servidor AI (puerto 11435)       ║
║    purma-dev chat     → Chat CLI con Purma                       ║
║    purma-dev test     → Verificar Ollama                         ║
║    purma-dev logs     → Ver logs de Ollama                       ║
║                                                                  ║
║  Para iniciar entorno gráfico:                                   ║
║                                                                  ║
║    sudo systemctl start lightdm                                  ║
║                                                                  ║
║  Directorio del proyecto: ~/PurmaLinux                           ║
║                                                                  ║
║  Siguiente paso:                                                 ║
║    cd ~/PurmaLinux && ./install.sh                               ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

echo ""
log "Recargando shell..."
exec bash
