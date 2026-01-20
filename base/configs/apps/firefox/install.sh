#!/bin/bash
# PurmaLinux - Firefox Installation and Configuration

set -e

echo "Configurando Firefox con tema Aurora..."

# Detectar perfil de Firefox
FIREFOX_PROFILE_DIR="$HOME/.mozilla/firefox"

# Esperar a que Firefox cree el perfil (si es primera instalación)
if [ ! -d "$FIREFOX_PROFILE_DIR" ]; then
    echo "Iniciando Firefox por primera vez para crear perfil..."
    timeout 5 firefox --headless 2>/dev/null || true
    sleep 2
fi

# Encontrar el perfil default
PROFILE=$(find "$FIREFOX_PROFILE_DIR" -maxdepth 1 -type d -name "*.default-release" | head -1)

if [ -z "$PROFILE" ]; then
    PROFILE=$(find "$FIREFOX_PROFILE_DIR" -maxdepth 1 -type d -name "*.default" | head -1)
fi

if [ -z "$PROFILE" ]; then
    echo "⚠️  No se encontró perfil de Firefox. Ejecuta Firefox manualmente primero."
    exit 0
fi

echo "Perfil encontrado: $PROFILE"

# Copiar user.js
cp user.js "$PROFILE/user.js"
echo "✓ Configuración aplicada a $PROFILE/user.js"

# Crear directorio chrome para userChrome.css (futuro)
mkdir -p "$PROFILE/chrome"

echo "✓ Firefox configurado con tema Aurora"
echo "  Reinicia Firefox para aplicar los cambios"
