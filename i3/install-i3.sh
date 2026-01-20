#!/bin/bash
#
# PurmaLinux i3 - Installation Script
# Instala y configura la versión i3 tiling
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                                                              ║"
echo "║                 PurmaLinux i3 Installer                      ║"
echo "║                   Tiling WM Edition                          ║"
echo "║                                                              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# ============================================
# Check prerequisites
# ============================================
if [[ $EUID -eq 0 ]]; then
    log_error "No ejecutes este script como root"
    exit 1
fi

# ============================================
# Install i3 packages
# ============================================
log_info "Instalando paquetes de i3..."

PACKAGES=$(grep -v '^#' "$PROJECT_ROOT/base/packages/i3.txt" | grep -v '^$' | tr '\n' ' ')
sudo apt install -y $PACKAGES

# i3-gaps from PPA or compile if not available
if ! apt-cache show i3-gaps &>/dev/null; then
    log_info "Instalando i3 estándar (i3-gaps no disponible en repos)"
    sudo apt install -y i3-wm
else
    sudo apt install -y i3-gaps
fi

log_success "Paquetes instalados"

# ============================================
# Install Polybar
# ============================================
log_info "Instalando Polybar..."

if ! command -v polybar &> /dev/null; then
    # Try from repos first
    if apt-cache show polybar &>/dev/null; then
        sudo apt install -y polybar
    else
        # Build from source
        sudo apt install -y \
            build-essential cmake cmake-data pkg-config \
            libcairo2-dev libxcb1-dev libxcb-util0-dev \
            libxcb-randr0-dev libxcb-composite0-dev \
            python3-xcbgen xcb-proto libxcb-image0-dev \
            libxcb-ewmh-dev libxcb-icccm4-dev \
            libxcb-xkb-dev libxcb-xrm-dev libxcb-cursor-dev \
            libasound2-dev libpulse-dev \
            libjsoncpp-dev libmpdclient-dev \
            libcurl4-openssl-dev libnl-genl-3-dev

        cd /tmp
        git clone --depth 1 https://github.com/polybar/polybar.git
        cd polybar
        mkdir build && cd build
        cmake ..
        make -j$(nproc)
        sudo make install

        cd "$PROJECT_ROOT"
        rm -rf /tmp/polybar
    fi

    log_success "Polybar instalado"
else
    log_warn "Polybar ya está instalado"
fi

# ============================================
# Install picom
# ============================================
log_info "Instalando picom..."

if ! command -v picom &> /dev/null; then
    sudo apt install -y picom
    log_success "Picom instalado"
else
    log_warn "Picom ya está instalado"
fi

# ============================================
# Install additional tools
# ============================================
log_info "Instalando herramientas adicionales..."

sudo apt install -y \
    dunst \
    numlockx \
    xss-lock \
    autorandr \
    arandr

log_success "Herramientas instaladas"

# ============================================
# Copy configurations
# ============================================
log_info "Copiando configuraciones..."

# i3
mkdir -p ~/.config/i3
cp "$SCRIPT_DIR/config/config" ~/.config/i3/config
cp "$SCRIPT_DIR/config/autostart.sh" ~/.config/i3/
chmod +x ~/.config/i3/autostart.sh

# Polybar
mkdir -p ~/.config/polybar
cp "$SCRIPT_DIR/polybar/config.ini" ~/.config/polybar/

# Picom (shared with desktop)
mkdir -p ~/.config/picom
if [[ -f "$PROJECT_ROOT/desktop/picom/picom.conf" ]]; then
    cp "$PROJECT_ROOT/desktop/picom/picom.conf" ~/.config/picom/
fi

# Dunst
mkdir -p ~/.config/dunst
cp "$SCRIPT_DIR/dunst/dunstrc" ~/.config/dunst/

# Rofi
mkdir -p ~/.config/rofi
mkdir -p ~/.local/share/rofi/themes
cp "$SCRIPT_DIR/rofi/config.rasi" ~/.config/rofi/
cp "$SCRIPT_DIR/rofi/purma-i3.rasi" ~/.local/share/rofi/themes/

log_success "Configuraciones copiadas"

# ============================================
# Create session file
# ============================================
log_info "Creando sesión de i3..."

sudo tee /usr/share/xsessions/purma-i3.desktop > /dev/null << 'EOF'
[Desktop Entry]
Name=PurmaLinux i3
Comment=PurmaLinux with i3 tiling window manager
Exec=i3
TryExec=i3
Type=Application
DesktopNames=i3
Keywords=tiling;wm;windowmanager;window;manager;
EOF

log_success "Sesión creada"

# ============================================
# Install AI chat
# ============================================
log_info "Configurando Purma Chat..."

mkdir -p ~/.local/bin

cat > ~/.local/bin/purma-chat << 'EOF'
#!/bin/bash
# PurmaLinux i3 - AI Chat Launcher
# Opens Purma AI chat in a floating terminal

kitty \
  --title "Purma AI" \
  -o initial_window_width=450 \
  -o initial_window_height=800 \
  -o remember_window_size=no \
  -e python3 ~/.local/share/purma/purma-agent.py
EOF

chmod +x ~/.local/bin/purma-chat

# Copy agent
mkdir -p ~/.local/share/purma
cp "$PROJECT_ROOT/ai/agent/purma-agent.py" ~/.local/share/purma/
chmod +x ~/.local/share/purma/purma-agent.py

log_success "Purma Chat configurado"

# ============================================
# Setup wallpaper
# ============================================
log_info "Configurando wallpaper..."

mkdir -p ~/Pictures/Wallpapers

# Simple wallpaper
if command -v convert &> /dev/null; then
    convert -size 1920x1080 \
        gradient:'#1a1b26'-'#24283b' \
        ~/Pictures/Wallpapers/purma-default.png 2>/dev/null || true
fi

# Nitrogen config
mkdir -p ~/.config/nitrogen
cat > ~/.config/nitrogen/nitrogen.cfg << EOF
[geometry]
posx=100
posy=100
sizex=800
sizey=600

[nitrogen]
view=list
recurse=true
sort=alpha
icon_caps=false
dirs=$HOME/Pictures/Wallpapers;
EOF

cat > ~/.config/nitrogen/bg-saved.cfg << EOF
[xin_-1]
file=$HOME/Pictures/Wallpapers/purma-default.png
mode=5
bgcolor=#1a1b26
EOF

log_success "Wallpaper configurado"

# ============================================
# Configure kitty terminal
# ============================================
log_info "Configurando terminal Kitty..."

mkdir -p ~/.config/kitty

cat > ~/.config/kitty/kitty.conf << 'EOF'
# PurmaLinux i3 - Kitty Configuration

# Font
font_family      JetBrains Mono
bold_font        auto
italic_font      auto
bold_italic_font auto
font_size        11.0

# Colors (Tokyo Night)
foreground           #c0caf5
background           #1a1b26
selection_foreground #1a1b26
selection_background #c0caf5

color0  #15161e
color8  #414868
color1  #f7768e
color9  #f7768e
color2  #9ece6a
color10 #9ece6a
color3  #e0af68
color11 #e0af68
color4  #7aa2f7
color12 #7aa2f7
color5  #bb9af7
color13 #bb9af7
color6  #7dcfff
color14 #7dcfff
color7  #a9b1d6
color15 #c0caf5

# Cursor
cursor #c0caf5
cursor_shape beam

# Window
window_padding_width 8
background_opacity 0.92

# No decorations (i3 handles this)
hide_window_decorations yes

# Bell
enable_audio_bell no

# Tab bar
tab_bar_style powerline

# Scrollback
scrollback_lines 10000

# Keybindings
map ctrl+shift+c copy_to_clipboard
map ctrl+shift+v paste_from_clipboard
map ctrl+shift+t new_tab
map ctrl+shift+w close_tab
map ctrl+plus change_font_size all +1.0
map ctrl+minus change_font_size all -1.0
EOF

log_success "Kitty configurado"

# ============================================
# Final
# ============================================
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                                                              ║"
echo "║              PurmaLinux i3 instalado                         ║"
echo "║                                                              ║"
echo "║  - Cierra sesión y selecciona 'PurmaLinux i3'                ║"
echo "║                                                              ║"
echo "║  Atajos principales:                                         ║"
echo "║  - Super+Return: Terminal                                    ║"
echo "║  - Super+D: Launcher                                         ║"
echo "║  - Super+A: Purma AI Chat                                    ║"
echo "║  - Super+Q: Cerrar ventana                                   ║"
echo "║  - Super+1-9: Cambiar workspace                              ║"
echo "║  - Super+Shift+1-9: Mover a workspace                        ║"
echo "║  - Super+H/J/K/L: Navegar ventanas                           ║"
echo "║  - Super+Z: Modo resize                                      ║"
echo "║  - Super+F: Fullscreen                                       ║"
echo "║                                                              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
