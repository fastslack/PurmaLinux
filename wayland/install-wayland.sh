#!/bin/bash
#
# PurmaLinux - Wayland Installation Script
# Instala Hyprland o Sway como alternativa a X11
#
# Uso:
#   bash install-wayland.sh [hyprland|sway|both]
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

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# ═══════════════════════════════════════════════════════════════════
# BANNER
# ═══════════════════════════════════════════════════════════════════
echo ""
echo -e "${MAGENTA}"
cat << 'BANNER'
    ____                             __    _
   / __ \__  _________ ___  ____ _  / /   (_)___  __  ___  __
  / /_/ / / / / ___/ __ `__ \/ __ `/ / /   / / __ \/ / / / |/_/
 / ____/ /_/ / /  / / / / / / /_/ / / /___/ / / / / /_/ />  <
/_/    \__,_/_/  /_/ /_/ /_/\__,_/ /_____/_/_/ /_/\__,_/_/|_|

        ██╗    ██╗ █████╗ ██╗   ██╗██╗      █████╗ ███╗   ██╗██████╗
        ██║    ██║██╔══██╗╚██╗ ██╔╝██║     ██╔══██╗████╗  ██║██╔══██╗
        ██║ █╗ ██║███████║ ╚████╔╝ ██║     ███████║██╔██╗ ██║██║  ██║
        ██║███╗██║██╔══██║  ╚██╔╝  ██║     ██╔══██║██║╚██╗██║██║  ██║
        ╚███╔███╔╝██║  ██║   ██║   ███████╗██║  ██║██║ ╚████║██████╔╝
         ╚══╝╚══╝ ╚═╝  ╚═╝   ╚═╝   ╚══════╝╚═╝  ╚═╝╚═╝  ╚═══╝╚═════╝
BANNER
echo -e "${NC}"
echo ""

# ═══════════════════════════════════════════════════════════════════
# MENU
# ═══════════════════════════════════════════════════════════════════
WM_CHOICE="${1:-}"

if [[ -z "$WM_CHOICE" ]]; then
    echo -e "${YELLOW}Selecciona el compositor Wayland:${NC}"
    echo ""
    echo "  1) ${CYAN}Hyprland${NC} - Moderno, animaciones fluidas, muy configurable"
    echo "     Recomendado para hardware moderno y buena experiencia visual"
    echo ""
    echo "  2) ${CYAN}Sway${NC} - Compatible con i3, estable, eficiente"
    echo "     Recomendado si vienes de i3 o prefieres estabilidad"
    echo ""
    echo "  3) ${CYAN}Ambos${NC} - Instalar Hyprland y Sway"
    echo "     Podrás elegir en el login manager"
    echo ""
    echo "  q) Cancelar"
    echo ""
    read -p "Opción [1/2/3/q]: " choice

    case $choice in
        1) WM_CHOICE="hyprland" ;;
        2) WM_CHOICE="sway" ;;
        3) WM_CHOICE="both" ;;
        q|Q) echo "Cancelado."; exit 0 ;;
        *) error "Opción no válida" ;;
    esac
fi

# ═══════════════════════════════════════════════════════════════════
# WAYLAND BASE
# ═══════════════════════════════════════════════════════════════════
log "Instalando paquetes base de Wayland..."

sudo apt update
sudo apt install -y \
    wayland-protocols \
    libwayland-dev \
    xwayland \
    wl-clipboard \
    grim \
    slurp \
    wf-recorder \
    mako-notifier \
    wofi \
    swayidle \
    swaylock \
    swaybg \
    wlsunset \
    wlr-randr

success "Paquetes Wayland base instalados"

# ═══════════════════════════════════════════════════════════════════
# WAYBAR
# ═══════════════════════════════════════════════════════════════════
log "Instalando Waybar..."

if ! command -v waybar &> /dev/null; then
    sudo apt install -y waybar || {
        log "Compilando Waybar desde source..."
        sudo apt install -y \
            libgtk-3-dev \
            libgtkmm-3.0-dev \
            libdbusmenu-gtk3-dev \
            gobject-introspection \
            libgirepository1.0-dev \
            libpulse-dev \
            libnl-3-dev \
            libnl-genl-3-dev \
            libfmt-dev \
            libspdlog-dev \
            libmpdclient-dev \
            libxkbregistry-dev \
            libjsoncpp-dev \
            libsigc++-2.0-dev \
            libdate-dev

        cd /tmp
        git clone https://github.com/Alexays/Waybar.git
        cd Waybar
        meson build
        ninja -C build
        sudo ninja -C build install
        cd ~
        rm -rf /tmp/Waybar
    }
fi

success "Waybar instalado"

# ═══════════════════════════════════════════════════════════════════
# HYPRLAND
# ═══════════════════════════════════════════════════════════════════
install_hyprland() {
    log "Instalando Hyprland..."

    # Dependencias
    sudo apt install -y \
        meson \
        ninja-build \
        cmake \
        libxcb-util-dev \
        libxcb-ewmh-dev \
        libxcb-icccm4-dev \
        libxcb-render-util0-dev \
        libxcb-res0-dev \
        libcairo2-dev \
        libpango1.0-dev \
        libgbm-dev \
        libdrm-dev \
        libxkbcommon-dev \
        libegl1-mesa-dev \
        libgles2-mesa-dev \
        libpixman-1-dev \
        libseat-dev \
        libinput-dev \
        libxcb-composite0-dev \
        libxcb-damage0-dev \
        libxcb-xfixes0-dev \
        libxcb-xinput-dev \
        hwdata \
        libdisplay-info-dev 2>/dev/null || true

    # Intentar instalar desde repos primero
    if sudo apt install -y hyprland 2>/dev/null; then
        success "Hyprland instalado desde repositorio"
    else
        warn "Hyprland no disponible en repos, compilando desde source..."
        warn "Esto puede tardar bastante..."

        cd /tmp

        # Compilar hyprland
        git clone --recursive https://github.com/hyprwm/Hyprland
        cd Hyprland
        make all
        sudo make install
        cd ~
        rm -rf /tmp/Hyprland

        success "Hyprland compilado e instalado"
    fi

    # Crear sesión
    sudo tee /usr/share/wayland-sessions/purmalinux-hyprland.desktop > /dev/null << 'EOF'
[Desktop Entry]
Name=PurmaLinux (Hyprland)
Comment=PurmaLinux with Hyprland compositor
Exec=Hyprland
Type=Application
EOF

    success "Hyprland configurado"
}

# ═══════════════════════════════════════════════════════════════════
# SWAY
# ═══════════════════════════════════════════════════════════════════
install_sway() {
    log "Instalando Sway..."

    sudo apt install -y sway

    # Crear sesión
    sudo tee /usr/share/wayland-sessions/purmalinux-sway.desktop > /dev/null << 'EOF'
[Desktop Entry]
Name=PurmaLinux (Sway)
Comment=PurmaLinux with Sway compositor
Exec=sway
Type=Application
EOF

    success "Sway instalado y configurado"
}

# ═══════════════════════════════════════════════════════════════════
# INSTALAR SEGÚN ELECCIÓN
# ═══════════════════════════════════════════════════════════════════
case $WM_CHOICE in
    hyprland)
        install_hyprland
        ;;
    sway)
        install_sway
        ;;
    both)
        install_hyprland
        install_sway
        ;;
esac

# ═══════════════════════════════════════════════════════════════════
# COPIAR CONFIGURACIONES
# ═══════════════════════════════════════════════════════════════════
log "Copiando configuraciones..."

mkdir -p ~/.config/{hyprland,sway,waybar,mako,wofi}

# Waybar
[[ -f "$SCRIPT_DIR/waybar/config" ]] && cp "$SCRIPT_DIR/waybar/config" ~/.config/waybar/
[[ -f "$SCRIPT_DIR/waybar/style.css" ]] && cp "$SCRIPT_DIR/waybar/style.css" ~/.config/waybar/

# Mako
[[ -f "$SCRIPT_DIR/mako/config" ]] && cp "$SCRIPT_DIR/mako/config" ~/.config/mako/

# Wofi
[[ -f "$SCRIPT_DIR/wofi/config" ]] && cp "$SCRIPT_DIR/wofi/config" ~/.config/wofi/
[[ -f "$SCRIPT_DIR/wofi/style.css" ]] && cp "$SCRIPT_DIR/wofi/style.css" ~/.config/wofi/

# Hyprland
if [[ "$WM_CHOICE" == "hyprland" || "$WM_CHOICE" == "both" ]]; then
    [[ -f "$SCRIPT_DIR/hyprland/hyprland.conf" ]] && cp "$SCRIPT_DIR/hyprland/hyprland.conf" ~/.config/hypr/
fi

# Sway
if [[ "$WM_CHOICE" == "sway" || "$WM_CHOICE" == "both" ]]; then
    [[ -f "$SCRIPT_DIR/sway/config" ]] && cp "$SCRIPT_DIR/sway/config" ~/.config/sway/
fi

success "Configuraciones copiadas"

# ═══════════════════════════════════════════════════════════════════
# RESUMEN
# ═══════════════════════════════════════════════════════════════════
echo ""
echo -e "${GREEN}"
cat << 'EOF'
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║         ¡Wayland instalado correctamente!                        ║
║                                                                  ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  Sesiones disponibles en LightDM/GDM:                            ║
║                                                                  ║
║    • PurmaLinux (Hyprland) - Compositor moderno                  ║
║    • PurmaLinux (Sway) - Compatible con i3                       ║
║    • PurmaLinux (Openbox) - X11 tradicional                      ║
║    • PurmaLinux (i3) - X11 tiling                                ║
║                                                                  ║
║  Configura el wallpaper:                                         ║
║    cp /path/to/wallpaper.png ~/.config/wallpaper.png             ║
║                                                                  ║
║  Reinicia y selecciona la sesión Wayland en el login.            ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"
