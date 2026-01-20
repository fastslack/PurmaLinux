#!/bin/bash
#
# PurmaLinux - Setup AI Models
# Descarga y configura los modelos de IA recomendados
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║              PurmaLinux - AI Models Setup                    ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Ensure Ollama is running
if ! pgrep -x "ollama" > /dev/null; then
    log_info "Iniciando Ollama..."
    ollama serve &
    sleep 3
fi

# ============================================
# Download recommended models
# ============================================

echo ""
echo "Modelos disponibles:"
echo ""
echo "  1) llama3.2:3b      - Rápido, bueno para tareas simples (2GB)"
echo "  2) llama3.1:8b      - Equilibrado, recomendado (4.7GB)"
echo "  3) qwen2.5:7b       - Muy bueno para código (4.4GB)"
echo "  4) deepseek-coder:6.7b - Especializado en código (3.8GB)"
echo "  5) mistral:7b       - General purpose (4.1GB)"
echo "  6) codellama:7b     - Código (3.8GB)"
echo ""
echo "  a) Todos los recomendados (llama3.1:8b + qwen2.5:7b)"
echo "  s) Skip - no descargar ahora"
echo ""

read -p "Selecciona modelo(s) [1-6, a, s]: " choice

case $choice in
    1)
        log_info "Descargando llama3.2:3b..."
        ollama pull llama3.2:3b
        ;;
    2)
        log_info "Descargando llama3.1:8b..."
        ollama pull llama3.1:8b
        ;;
    3)
        log_info "Descargando qwen2.5:7b..."
        ollama pull qwen2.5:7b
        ;;
    4)
        log_info "Descargando deepseek-coder:6.7b..."
        ollama pull deepseek-coder:6.7b
        ;;
    5)
        log_info "Descargando mistral:7b..."
        ollama pull mistral:7b
        ;;
    6)
        log_info "Descargando codellama:7b..."
        ollama pull codellama:7b
        ;;
    a|A)
        log_info "Descargando modelos recomendados..."
        ollama pull llama3.1:8b
        ollama pull qwen2.5:7b
        ;;
    s|S)
        log_info "Saltando descarga de modelos"
        ;;
    *)
        log_info "Opción no válida, saltando..."
        ;;
esac

# ============================================
# Create Purma model (customized)
# ============================================

log_info "Creando modelo Purma personalizado..."

# Create Modelfile for Purma
cat > /tmp/Modelfile.purma << 'EOF'
FROM llama3.1:8b

PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER num_ctx 8192

SYSTEM """
Eres Purma, un asistente de IA integrado en PurmaLinux.

Tu función principal es ayudar al usuario con tareas en su sistema:
- Puedes crear, leer, editar y eliminar archivos en el directorio del usuario
- Puedes ejecutar comandos de terminal de forma segura
- Puedes ayudar con programación, scripts, y automatización
- Puedes buscar información y responder preguntas

REGLAS DE SEGURIDAD:
- SOLO puedes operar dentro del directorio home del usuario (~/)
- NUNCA ejecutes comandos destructivos sin confirmación
- NUNCA accedas a archivos del sistema fuera de ~/
- NUNCA reveles información sensible del sistema

Sé conciso, útil y proactivo. Cuando el usuario pida hacer algo, hazlo directamente
si es seguro, o pide confirmación si tiene riesgos.

Responde en el idioma del usuario.
"""
EOF

# Check if base model exists before creating custom model
if ollama list | grep -q "llama3.1:8b"; then
    ollama create purma -f /tmp/Modelfile.purma
    log_success "Modelo 'purma' creado"
else
    log_info "Modelo base no encontrado. Ejecuta 'ollama pull llama3.1:8b' primero"
    log_info "Luego ejecuta: ollama create purma -f $SCRIPT_DIR/../prompts/Modelfile.purma"
fi

rm -f /tmp/Modelfile.purma

echo ""
log_success "Setup de modelos completado"
echo ""
echo "Para usar el modelo Purma: ollama run purma"
echo ""
