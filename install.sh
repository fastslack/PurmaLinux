#!/bin/bash
#
# PurmaLinux - Main Installer
# AI-First Linux Distribution
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

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
echo -e "${CYAN}              AI-First Linux Distribution${NC}"
echo -e "${CYAN}                 Based on Ubuntu Server${NC}"
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Check system
if [[ $EUID -eq 0 ]]; then
    echo -e "${RED}Error: No ejecutes este script como root${NC}"
    exit 1
fi

if ! grep -q "Ubuntu" /etc/os-release 2>/dev/null; then
    echo -e "${RED}Error: Este instalador requiere Ubuntu Server${NC}"
    exit 1
fi

# Menu
echo -e "${YELLOW}Selecciona la versión a instalar:${NC}"
echo ""
echo "  1) ${GREEN}Desktop${NC} - Openbox + AGS (barra completa, flotante)"
echo "     Para usuarios que prefieren un escritorio tradicional"
echo "     con ventanas flotantes y una barra muy personalizable."
echo ""
echo "  2) ${GREEN}i3${NC} - i3 tiling + Polybar (minimalista, teclado)"
echo "     Para usuarios que prefieren un entorno tiling,"
echo "     eficiente y controlado completamente por teclado."
echo ""
echo "  3) ${BLUE}Ambas${NC} - Instalar las dos versiones"
echo "     Podrás elegir en el login manager."
echo ""
echo "  q) Salir"
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo ""

read -p "Opción [1/2/3/q]: " choice

case $choice in
    1)
        VERSION="desktop"
        echo ""
        echo -e "${GREEN}Instalando PurmaLinux Desktop...${NC}"
        ;;
    2)
        VERSION="i3"
        echo ""
        echo -e "${GREEN}Instalando PurmaLinux i3...${NC}"
        ;;
    3)
        VERSION="both"
        echo ""
        echo -e "${GREEN}Instalando ambas versiones...${NC}"
        ;;
    q|Q)
        echo "Instalación cancelada."
        exit 0
        ;;
    *)
        echo -e "${RED}Opción no válida${NC}"
        exit 1
        ;;
esac

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Run base installation
echo -e "${BLUE}[1/4]${NC} Instalando sistema base..."
bash "$SCRIPT_DIR/base/scripts/install-base.sh"

# Run AI setup
echo ""
echo -e "${BLUE}[2/4]${NC} Configurando stack de IA..."
bash "$SCRIPT_DIR/ai/runtime/setup-models.sh"

# Install selected version(s)
echo ""
echo -e "${BLUE}[3/4]${NC} Instalando entorno gráfico..."

case $VERSION in
    desktop)
        bash "$SCRIPT_DIR/desktop/install-desktop.sh"
        ;;
    i3)
        bash "$SCRIPT_DIR/i3/install-i3.sh"
        ;;
    both)
        bash "$SCRIPT_DIR/desktop/install-desktop.sh"
        echo ""
        bash "$SCRIPT_DIR/i3/install-i3.sh"
        ;;
esac

# Final setup
echo ""
echo -e "${BLUE}[4/4]${NC} Configuración final..."

# Make scripts executable
chmod +x "$SCRIPT_DIR/base/scripts/"*.sh 2>/dev/null || true
chmod +x "$SCRIPT_DIR/ai/runtime/"*.sh 2>/dev/null || true
chmod +x "$SCRIPT_DIR/desktop/"*.sh 2>/dev/null || true
chmod +x "$SCRIPT_DIR/i3/"*.sh 2>/dev/null || true
chmod +x ~/.local/bin/* 2>/dev/null || true

# Enable services
sudo systemctl enable lightdm 2>/dev/null || true
systemctl --user enable ollama 2>/dev/null || true

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                                              ║${NC}"
echo -e "${GREEN}║           ¡PurmaLinux instalado correctamente!               ║${NC}"
echo -e "${GREEN}║                                                              ║${NC}"
echo -e "${GREEN}╠══════════════════════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║                                                              ║${NC}"
echo -e "${GREEN}║  Reinicia tu sistema y selecciona PurmaLinux en el login.    ║${NC}"
echo -e "${GREEN}║                                                              ║${NC}"
echo -e "${GREEN}║  Para chatear con Purma AI:                                  ║${NC}"
echo -e "${GREEN}║    - Presiona Super+A en cualquier momento                   ║${NC}"
echo -e "${GREEN}║    - O ejecuta: purma-chat                                   ║${NC}"
echo -e "${GREEN}║                                                              ║${NC}"
echo -e "${GREEN}║  Documentación: ~/AI/README.md                               ║${NC}"
echo -e "${GREEN}║                                                              ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

read -p "¿Reiniciar ahora? [y/N]: " reboot_choice
if [[ "$reboot_choice" =~ ^[Yy]$ ]]; then
    sudo reboot
fi
