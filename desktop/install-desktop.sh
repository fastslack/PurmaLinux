#!/bin/bash
#
# PurmaLinux Desktop - Installation Script
# Instala y configura la versión Desktop con Openbox + AGS
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
echo "║               PurmaLinux Desktop Installer                   ║"
echo "║                   Openbox + AGS Edition                      ║"
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
# Install Desktop packages
# ============================================
log_info "Instalando paquetes de Desktop..."

PACKAGES=$(grep -v '^#' "$PROJECT_ROOT/base/packages/desktop.txt" | grep -v '^$' | tr '\n' ' ')
sudo apt install -y $PACKAGES

log_success "Paquetes instalados"

# ============================================
# Install AGS
# ============================================
log_info "Instalando AGS..."

if ! command -v ags &> /dev/null; then
    # Install AGS from source
    sudo apt install -y \
        meson \
        gjs \
        libgtk-3-dev \
        libgtk-layer-shell-dev \
        libpulse-dev \
        libdbusmenu-gtk3-dev \
        gobject-introspection \
        libgirepository1.0-dev \
        libsoup-3.0-dev \
        gir1.2-soup-3.0 \
        gir1.2-nm-1.0

    cd /tmp
    git clone --depth 1 https://github.com/Aylur/ags.git
    cd ags
    meson setup build
    sudo meson install -C build

    cd "$PROJECT_ROOT"
    rm -rf /tmp/ags

    log_success "AGS instalado"
else
    log_warn "AGS ya está instalado"
fi

# ============================================
# Install picom (latest)
# ============================================
log_info "Instalando picom..."

if ! command -v picom &> /dev/null; then
    sudo apt install -y picom
    log_success "Picom instalado"
else
    log_warn "Picom ya está instalado"
fi

# ============================================
# Copy configurations
# ============================================
log_info "Copiando configuraciones..."

# Openbox
mkdir -p ~/.config/openbox
cp "$SCRIPT_DIR/openbox/rc.xml" ~/.config/openbox/
cp "$SCRIPT_DIR/openbox/menu.xml" ~/.config/openbox/
cp "$SCRIPT_DIR/openbox/autostart" ~/.config/openbox/
chmod +x ~/.config/openbox/autostart

# AGS
mkdir -p ~/.config/ags
cp "$SCRIPT_DIR/ags/config.js" ~/.config/ags/
cp "$SCRIPT_DIR/ags/style.css" ~/.config/ags/

# Picom
mkdir -p ~/.config/picom
cp "$SCRIPT_DIR/picom/picom.conf" ~/.config/picom/

# Rofi
mkdir -p ~/.config/rofi
cp "$SCRIPT_DIR/rofi/config.rasi" ~/.config/rofi/
cp "$SCRIPT_DIR/rofi/purma.rasi" ~/.local/share/rofi/themes/ 2>/dev/null || \
    mkdir -p ~/.local/share/rofi/themes && cp "$SCRIPT_DIR/rofi/purma.rasi" ~/.local/share/rofi/themes/

log_success "Configuraciones copiadas"

# ============================================
# Create session file
# ============================================
log_info "Creando sesión de Openbox..."

sudo tee /usr/share/xsessions/purma-desktop.desktop > /dev/null << 'EOF'
[Desktop Entry]
Name=PurmaLinux Desktop
Comment=PurmaLinux with Openbox and AGS
Exec=openbox-session
TryExec=openbox
Type=Application
DesktopNames=Openbox
EOF

log_success "Sesión creada"

# ============================================
# Install AI chat UI (Desktop widget)
# ============================================
log_info "Configurando Purma Chat UI..."

# Create simple chat launcher script
mkdir -p ~/.local/bin

cat > ~/.local/bin/purma-chat << 'EOF'
#!/bin/bash
# PurmaLinux - AI Chat Launcher
# Opens Purma AI chat in a floating terminal

kitty \
  --name purma-chat \
  --title "Purma AI" \
  -o initial_window_width=400 \
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

# Create a simple gradient wallpaper using ImageMagick if available
if command -v convert &> /dev/null; then
    convert -size 1920x1080 \
        gradient:'#1a1b26'-'#24283b' \
        -blur 0x20 \
        ~/Pictures/Wallpapers/purma-default.png 2>/dev/null || true
fi

# Configure nitrogen
mkdir -p ~/.config/nitrogen
cat > ~/.config/nitrogen/nitrogen.cfg << 'EOF'
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
dirs=/home/$USER/Pictures/Wallpapers;
EOF

cat > ~/.config/nitrogen/bg-saved.cfg << 'EOF'
[xin_-1]
file=/home/$USER/Pictures/Wallpapers/purma-default.png
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
# PurmaLinux - Kitty Configuration

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
cursor_blink_interval 0.5

# Window
window_padding_width 12
background_opacity 0.95
dynamic_background_opacity yes

# Bell
enable_audio_bell no
visual_bell_duration 0.1

# Tab bar
tab_bar_style powerline
tab_powerline_style slanted

# URL
url_color #7aa2f7
url_style curly

# Scrollback
scrollback_lines 10000

# Keybindings
map ctrl+shift+c copy_to_clipboard
map ctrl+shift+v paste_from_clipboard
map ctrl+shift+t new_tab
map ctrl+shift+w close_tab
map ctrl+plus change_font_size all +1.0
map ctrl+minus change_font_size all -1.0
map ctrl+0 change_font_size all 0
EOF

log_success "Kitty configurado"

# ============================================
# Final
# ============================================
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                                                              ║"
echo "║           PurmaLinux Desktop instalado                       ║"
echo "║                                                              ║"
echo "║  - Cierra sesión y selecciona 'PurmaLinux Desktop'           ║"
echo "║  - Super+D: Launcher                                         ║"
echo "║  - Super+Return: Terminal                                    ║"
echo "║  - Super+A: Purma AI Chat                                    ║"
echo "║                                                              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
