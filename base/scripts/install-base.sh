#!/bin/bash
#
# PurmaLinux - Base Installation Script
# Instala los paquetes y configuraciones base comunes a ambas versiones
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check if running as root
if [[ $EUID -eq 0 ]]; then
    log_error "No ejecutes este script como root. Usa tu usuario normal."
    exit 1
fi

# Check Ubuntu
if ! grep -q "Ubuntu" /etc/os-release 2>/dev/null; then
    log_error "Este script requiere Ubuntu Server"
    exit 1
fi

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                                                              ║"
echo "║                     PurmaLinux Installer                     ║"
echo "║                      AI-First Linux OS                       ║"
echo "║                                                              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# ============================================
# Update system
# ============================================
log_info "Actualizando sistema..."
sudo apt update && sudo apt upgrade -y
log_success "Sistema actualizado"

# ============================================
# Install core packages
# ============================================
log_info "Instalando paquetes core..."

PACKAGES_DIR="$PROJECT_ROOT/base/packages"

# Read and install core packages
if [[ -f "$PACKAGES_DIR/core.txt" ]]; then
    # Filter comments and empty lines
    CORE_PACKAGES=$(grep -v '^#' "$PACKAGES_DIR/core.txt" | grep -v '^$' | tr '\n' ' ')
    sudo apt install -y $CORE_PACKAGES
    log_success "Paquetes core instalados"
else
    log_error "No se encontró core.txt"
    exit 1
fi

# ============================================
# Install AI packages
# ============================================
log_info "Instalando dependencias de IA..."

if [[ -f "$PACKAGES_DIR/ai.txt" ]]; then
    AI_PACKAGES=$(grep -v '^#' "$PACKAGES_DIR/ai.txt" | grep -v '^$' | tr '\n' ' ')
    sudo apt install -y $AI_PACKAGES
    log_success "Dependencias de IA instaladas"
fi

# ============================================
# Install Ollama
# ============================================
log_info "Instalando Ollama..."

if ! command -v ollama &> /dev/null; then
    curl -fsSL https://ollama.com/install.sh | sh
    log_success "Ollama instalado"
else
    log_warn "Ollama ya está instalado"
fi

# ============================================
# Setup directories
# ============================================
log_info "Configurando directorios..."

mkdir -p ~/.config
mkdir -p ~/.local/bin
mkdir -p ~/.local/share/purma
mkdir -p ~/AI  # Directorio de trabajo para el agente de IA

log_success "Directorios configurados"

# ============================================
# Copy shared resources
# ============================================
log_info "Copiando recursos compartidos..."

SHARED_DIR="$PROJECT_ROOT/shared"

# Fonts
if [[ -d "$SHARED_DIR/fonts" ]]; then
    mkdir -p ~/.local/share/fonts
    cp -r "$SHARED_DIR/fonts/"* ~/.local/share/fonts/ 2>/dev/null || true
    fc-cache -f
fi

# Scripts to PATH
if [[ -d "$SHARED_DIR/bin" ]]; then
    cp -r "$SHARED_DIR/bin/"* ~/.local/bin/ 2>/dev/null || true
    chmod +x ~/.local/bin/* 2>/dev/null || true
fi

# Add ~/.local/bin to PATH if not already
if ! grep -q 'PATH="$HOME/.local/bin:$PATH"' ~/.bashrc; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
fi

log_success "Recursos compartidos copiados"

# ============================================
# Install systemd services
# ============================================
log_info "Configurando servicios..."

SYSTEMD_DIR="$PROJECT_ROOT/base/systemd"

if [[ -d "$SYSTEMD_DIR" ]]; then
    # User services
    mkdir -p ~/.config/systemd/user
    for service in "$SYSTEMD_DIR/user/"*.service; do
        if [[ -f "$service" ]]; then
            cp "$service" ~/.config/systemd/user/
        fi
    done
    systemctl --user daemon-reload
fi

log_success "Servicios configurados"

# ============================================
# Install Purma AI Server
# ============================================
log_info "Instalando servidor Purma AI..."

AI_SERVER_DIR="$PROJECT_ROOT/ai/server"
PURMA_DIR="$HOME/.local/share/purma"

# Copy server files
mkdir -p "$PURMA_DIR/server"
mkdir -p "$PURMA_DIR/chat"
cp "$AI_SERVER_DIR/purma_server.py" "$PURMA_DIR/server/"
cp "$AI_SERVER_DIR/requirements.txt" "$PURMA_DIR/server/"
cp "$PROJECT_ROOT/ai/chat/purma-chat-cli.py" "$PURMA_DIR/chat/"
cp "$PROJECT_ROOT/ai/agent/purma-agent.py" "$PURMA_DIR/"

# Create virtual environment
if [[ ! -d "$PURMA_DIR/venv" ]]; then
    python3 -m venv "$PURMA_DIR/venv"
fi

# Install server dependencies
"$PURMA_DIR/venv/bin/pip" install --upgrade pip -q
"$PURMA_DIR/venv/bin/pip" install -r "$PURMA_DIR/server/requirements.txt" -q

# Install systemd service for server
mkdir -p ~/.config/systemd/user
cp "$AI_SERVER_DIR/systemd/purma-server.service" ~/.config/systemd/user/

# Create server control script
cat > ~/.local/bin/purma-server << 'SERVERCTL'
#!/bin/bash
case "$1" in
    start)   systemctl --user start purma-server; echo "Purma Server started" ;;
    stop)    systemctl --user stop purma-server; echo "Purma Server stopped" ;;
    restart) systemctl --user restart purma-server; echo "Purma Server restarted" ;;
    status)  systemctl --user status purma-server ;;
    logs)    journalctl --user -u purma-server -f ;;
    enable)  systemctl --user enable purma-server; echo "Enabled" ;;
    disable) systemctl --user disable purma-server; echo "Disabled" ;;
    *)       echo "Usage: purma-server {start|stop|restart|status|logs|enable|disable}" ;;
esac
SERVERCTL
chmod +x ~/.local/bin/purma-server

# Enable and start server
systemctl --user daemon-reload
systemctl --user enable purma-server
loginctl enable-linger "$USER" 2>/dev/null || true

log_success "Servidor Purma AI instalado"

# ============================================
# Configure LightDM
# ============================================
log_info "Configurando LightDM..."

sudo tee /etc/lightdm/lightdm.conf > /dev/null << 'EOF'
[Seat:*]
greeter-session=lightdm-gtk-greeter
user-session=purma
EOF

log_success "LightDM configurado"

# ============================================
# Start services
# ============================================
log_info "Iniciando servicios..."

# Start Ollama if not running
if ! pgrep -x "ollama" > /dev/null; then
    ollama serve &>/dev/null &
    sleep 2
fi

# Start Purma server
systemctl --user start purma-server 2>/dev/null || true

log_success "Servicios iniciados"

# ============================================
# Final message
# ============================================
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                                                              ║"
echo "║              Base instalada correctamente                    ║"
echo "║                                                              ║"
echo "║  Siguiente paso: ejecutar el instalador de la versión       ║"
echo "║                                                              ║"
echo "║    Desktop:  ./desktop/install-desktop.sh                   ║"
echo "║    i3:       ./i3/install-i3.sh                             ║"
echo "║                                                              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
