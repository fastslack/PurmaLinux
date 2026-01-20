#!/bin/bash
#
# PurmaLinux - macOS Development Setup
# Configura el entorno para desarrollar el backend AI localmente en macOS
#
# Uso: ./dev/macos-dev-setup.sh
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log() { echo -e "${BLUE}[•]${NC} $1"; }
success() { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[✗]${NC} $1"; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo ""
echo -e "${CYAN}PurmaLinux - macOS Development Setup${NC}"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Check macOS
if [[ "$(uname)" != "Darwin" ]]; then
    error "Este script es solo para macOS"
fi

# Check Homebrew
if ! command -v brew &> /dev/null; then
    log "Instalando Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi
success "Homebrew disponible"

# ═══════════════════════════════════════════════════════════════════
# Instalar dependencias
# ═══════════════════════════════════════════════════════════════════
echo ""
log "Instalando dependencias con Homebrew..."

# Ollama
if ! command -v ollama &> /dev/null; then
    brew install ollama
    success "Ollama instalado"
else
    success "Ollama ya instalado"
fi

# Python (si no está)
if ! command -v python3 &> /dev/null; then
    brew install python@3.12
fi
success "Python3 disponible"

# Tesseract para OCR
if ! command -v tesseract &> /dev/null; then
    brew install tesseract tesseract-lang
    success "Tesseract instalado"
else
    success "Tesseract ya instalado"
fi

# ffmpeg para audio
if ! command -v ffmpeg &> /dev/null; then
    brew install ffmpeg
    success "ffmpeg instalado"
else
    success "ffmpeg ya instalado"
fi

# ═══════════════════════════════════════════════════════════════════
# Configurar Python venv
# ═══════════════════════════════════════════════════════════════════
echo ""
log "Configurando entorno virtual Python..."

cd "$PROJECT_DIR"

if [[ ! -d "venv" ]]; then
    python3 -m venv venv
    success "Entorno virtual creado"
else
    success "Entorno virtual ya existe"
fi

source venv/bin/activate

log "Instalando dependencias Python..."
pip install --upgrade pip -q

# Instalar desde requirements.txt si existe
if [[ -f "ai/server/requirements.txt" ]]; then
    pip install -r ai/server/requirements.txt -q
else
    pip install -q \
        fastapi \
        "uvicorn[standard]" \
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
fi

success "Dependencias Python instaladas"

# ═══════════════════════════════════════════════════════════════════
# Crear directorios de datos
# ═══════════════════════════════════════════════════════════════════
echo ""
log "Creando directorios de datos..."

mkdir -p ~/.purma/{cortex,memory,ghost,vault,scribe,sync,lens}
success "Directorios creados en ~/.purma/"

# ═══════════════════════════════════════════════════════════════════
# Configurar Ollama
# ═══════════════════════════════════════════════════════════════════
echo ""
log "Configurando Ollama..."

# Iniciar Ollama si no está corriendo
if ! pgrep -x "ollama" > /dev/null; then
    log "Iniciando Ollama en background..."
    ollama serve &>/dev/null &
    sleep 3
fi

# Verificar si hay modelos
MODELS=$(ollama list 2>/dev/null | tail -n +2)
if [[ -z "$MODELS" ]]; then
    log "Descargando modelo llama3.2 (puede tardar varios minutos)..."
    ollama pull llama3.2
    success "Modelo llama3.2 descargado"
else
    success "Modelos disponibles:"
    echo "$MODELS" | sed 's/^/    /'
fi

# ═══════════════════════════════════════════════════════════════════
# Crear scripts de desarrollo
# ═══════════════════════════════════════════════════════════════════
echo ""
log "Creando scripts de desarrollo..."

# Script principal de desarrollo
cat > "$PROJECT_DIR/dev/run-server.sh" << 'SCRIPT'
#!/bin/bash
cd "$(dirname "$0")/.."
source venv/bin/activate

# Asegurar que Ollama está corriendo
if ! pgrep -x "ollama" > /dev/null; then
    echo "Iniciando Ollama..."
    ollama serve &>/dev/null &
    sleep 2
fi

echo "Iniciando Purma Server en http://localhost:11435"
echo "Presiona Ctrl+C para detener"
echo ""

python ai/server/purma_server.py
SCRIPT
chmod +x "$PROJECT_DIR/dev/run-server.sh"

# Script para probar endpoints
cat > "$PROJECT_DIR/dev/test-api.sh" << 'SCRIPT'
#!/bin/bash

BASE_URL="http://localhost:11435"

echo "Testing Purma API..."
echo ""

echo "1. Status:"
curl -s "$BASE_URL/status" | python3 -m json.tool 2>/dev/null || echo "  Server no disponible"
echo ""

echo "2. Chat (test):"
curl -s -X POST "$BASE_URL/chat" \
    -H "Content-Type: application/json" \
    -d '{"message": "hola, di solo OK"}' | python3 -m json.tool 2>/dev/null || echo "  Error en chat"
echo ""

echo "3. System Info:"
curl -s "$BASE_URL/system/status" | python3 -m json.tool 2>/dev/null || echo "  Endpoint no disponible"
SCRIPT
chmod +x "$PROJECT_DIR/dev/test-api.sh"

success "Scripts creados"

# ═══════════════════════════════════════════════════════════════════
# Resumen final
# ═══════════════════════════════════════════════════════════════════
echo ""
echo "════════════════════════════════════════════════════════════════"
echo ""
echo -e "${GREEN}¡Entorno de desarrollo macOS configurado!${NC}"
echo ""
echo "Comandos disponibles:"
echo ""
echo -e "  ${CYAN}./dev/run-server.sh${NC}    → Iniciar servidor Purma (puerto 11435)"
echo -e "  ${CYAN}./dev/test-api.sh${NC}      → Probar endpoints de la API"
echo ""
echo "Activar entorno manualmente:"
echo ""
echo -e "  ${YELLOW}cd $PROJECT_DIR${NC}"
echo -e "  ${YELLOW}source venv/bin/activate${NC}"
echo -e "  ${YELLOW}python ai/server/purma_server.py${NC}"
echo ""
echo "URLs útiles:"
echo ""
echo "  API:     http://localhost:11435"
echo "  Docs:    http://localhost:11435/docs  (Swagger UI)"
echo "  Ollama:  http://localhost:11434"
echo ""
echo "════════════════════════════════════════════════════════════════"
