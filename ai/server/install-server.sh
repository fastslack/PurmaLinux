#!/bin/bash
#
# PurmaLinux - Install AI Server
# Instala el servidor de IA como servicio del usuario
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║              Purma AI Server - Installation                  ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# ============================================
# Create directories
# ============================================
log_info "Creando directorios..."

PURMA_DIR="$HOME/.local/share/purma"
mkdir -p "$PURMA_DIR/server"
mkdir -p "$HOME/.config/systemd/user"

# ============================================
# Copy server files
# ============================================
log_info "Copiando archivos del servidor..."

cp "$SCRIPT_DIR/purma_server.py" "$PURMA_DIR/server/"
cp "$SCRIPT_DIR/requirements.txt" "$PURMA_DIR/server/"

log_success "Archivos copiados"

# ============================================
# Create virtual environment
# ============================================
log_info "Creando entorno virtual Python..."

if [[ ! -d "$PURMA_DIR/venv" ]]; then
    python3 -m venv "$PURMA_DIR/venv"
fi

log_success "Entorno virtual creado"

# ============================================
# Install dependencies
# ============================================
log_info "Instalando dependencias..."

"$PURMA_DIR/venv/bin/pip" install --upgrade pip
"$PURMA_DIR/venv/bin/pip" install -r "$PURMA_DIR/server/requirements.txt"

log_success "Dependencias instaladas"

# ============================================
# Install systemd service
# ============================================
log_info "Instalando servicio systemd..."

cp "$SCRIPT_DIR/systemd/purma-server.service" "$HOME/.config/systemd/user/"

# Reload systemd
systemctl --user daemon-reload

log_success "Servicio instalado"

# ============================================
# Create control script
# ============================================
log_info "Creando script de control..."

cat > "$HOME/.local/bin/purma-server" << 'EOF'
#!/bin/bash
# Purma AI Server Control Script

case "$1" in
    start)
        systemctl --user start purma-server
        echo "Purma Server started"
        ;;
    stop)
        systemctl --user stop purma-server
        echo "Purma Server stopped"
        ;;
    restart)
        systemctl --user restart purma-server
        echo "Purma Server restarted"
        ;;
    status)
        systemctl --user status purma-server
        ;;
    logs)
        journalctl --user -u purma-server -f
        ;;
    enable)
        systemctl --user enable purma-server
        echo "Purma Server enabled at startup"
        ;;
    disable)
        systemctl --user disable purma-server
        echo "Purma Server disabled at startup"
        ;;
    *)
        echo "Purma AI Server Control"
        echo ""
        echo "Usage: purma-server {start|stop|restart|status|logs|enable|disable}"
        echo ""
        echo "Commands:"
        echo "  start    - Start the server"
        echo "  stop     - Stop the server"
        echo "  restart  - Restart the server"
        echo "  status   - Show server status"
        echo "  logs     - Follow server logs"
        echo "  enable   - Enable autostart"
        echo "  disable  - Disable autostart"
        ;;
esac
EOF

chmod +x "$HOME/.local/bin/purma-server"

log_success "Script de control creado"

# ============================================
# Enable and start service
# ============================================
log_info "Habilitando servicio..."

# Enable lingering for user services to start at boot
loginctl enable-linger "$USER" 2>/dev/null || true

# Enable service
systemctl --user enable purma-server

# Start service
systemctl --user start purma-server

log_success "Servicio habilitado e iniciado"

# ============================================
# Verify
# ============================================
echo ""
log_info "Verificando servidor..."
sleep 2

if systemctl --user is-active --quiet purma-server; then
    log_success "Servidor corriendo correctamente"

    # Test endpoint
    if command -v curl &> /dev/null; then
        response=$(curl -s http://127.0.0.1:11435/status 2>/dev/null || echo "error")
        if [[ "$response" != "error" ]]; then
            log_success "API respondiendo en http://127.0.0.1:11435"
        fi
    fi
else
    log_warn "El servidor no está corriendo. Revisa: purma-server logs"
fi

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                                                              ║"
echo "║              Purma AI Server instalado                       ║"
echo "║                                                              ║"
echo "║  API:      http://127.0.0.1:11435                           ║"
echo "║  Docs:     http://127.0.0.1:11435/docs                      ║"
echo "║                                                              ║"
echo "║  Control:  purma-server {start|stop|status|logs}            ║"
echo "║                                                              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
