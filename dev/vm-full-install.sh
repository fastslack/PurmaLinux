#!/bin/bash
#
# PurmaLinux - Full VM Installation Script
# Configura TODO desde Ubuntu Server limpio
#
# Uso desde la VM:
#   # Opción 1: Si tienes el repo copiado
#   bash ~/PurmaLinux/dev/vm-full-install.sh
#
#   # Opción 2: Descargar y ejecutar (cambiar URL por tu repo)
#   curl -fsSL https://raw.githubusercontent.com/tu-usuario/PurmaLinux/main/dev/vm-full-install.sh | bash
#

set -e

# ═══════════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════════════
PURMA_DIR="${PURMA_DIR:-$HOME/PurmaLinux}"
INSTALL_VERSION="${1:-both}"  # desktop, i3, both

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

# Logging
log() { echo -e "${BLUE}[$(date '+%H:%M:%S')]${NC} $1"; }
success() { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[✗]${NC} $1"; exit 1; }
phase() { echo -e "\n${MAGENTA}════════════════════════════════════════════════════════════════${NC}"; echo -e "${CYAN}$1${NC}"; echo -e "${MAGENTA}════════════════════════════════════════════════════════════════${NC}\n"; }

# ═══════════════════════════════════════════════════════════════════
# BANNER
# ═══════════════════════════════════════════════════════════════════
clear
echo ""
echo -e "${MAGENTA}"
cat << 'BANNER'
    ____                             __    _
   / __ \__  _________ ___  ____ _  / /   (_)___  __  ___  __
  / /_/ / / / / ___/ __ `__ \/ __ `/ / /   / / __ \/ / / / |/_/
 / ____/ /_/ / /  / / / / / / /_/ / / /___/ / / / / /_/ />  <
/_/    \__,_/_/  /_/ /_/ /_/\__,_/ /_____/_/_/ /_/\__,_/_/|_|

         ███████╗██╗   ██╗██╗     ██╗
         ██╔════╝██║   ██║██║     ██║
         █████╗  ██║   ██║██║     ██║
         ██╔══╝  ██║   ██║██║     ██║
         ██║     ╚██████╔╝███████╗███████╗
         ╚═╝      ╚═════╝ ╚══════╝╚══════╝

            I N S T A L L A T I O N
BANNER
echo -e "${NC}"
echo -e "${CYAN}           AI-First Linux Distribution${NC}"
echo -e "${CYAN}              Ubuntu Server ARM64${NC}"
echo ""

# ═══════════════════════════════════════════════════════════════════
# VALIDACIONES
# ═══════════════════════════════════════════════════════════════════
if [[ $EUID -eq 0 ]]; then
    error "No ejecutar como root. Usa: bash $0"
fi

if ! grep -qE "Ubuntu|Debian" /etc/os-release 2>/dev/null; then
    error "Este script requiere Ubuntu o Debian"
fi

ARCH=$(uname -m)
log "Sistema: $(lsb_release -ds 2>/dev/null || cat /etc/os-release | grep PRETTY_NAME | cut -d'"' -f2)"
log "Arquitectura: ${CYAN}$ARCH${NC}"
log "Usuario: ${CYAN}$USER${NC}"
log "Directorio PurmaLinux: ${CYAN}$PURMA_DIR${NC}"

if [[ ! -d "$PURMA_DIR" ]]; then
    warn "Directorio $PURMA_DIR no existe. Se creará."
fi

echo ""
echo -e "${YELLOW}Este script instalará:${NC}"
echo "  - Entorno gráfico completo (Openbox + i3)"
echo "  - AGS (Aylur's GTK Shell)"
echo "  - Polybar"
echo "  - Zsh + Oh My Zsh + Powerlevel10k"
echo "  - Ollama + modelo llama3.2"
echo "  - Stack Python para AI"
echo "  - Todas las configuraciones de PurmaLinux"
echo ""
read -p "¿Continuar? [Y/n]: " confirm
if [[ "$confirm" =~ ^[Nn]$ ]]; then
    echo "Instalación cancelada."
    exit 0
fi

# ═══════════════════════════════════════════════════════════════════
# FASE 1: ACTUALIZACIÓN DEL SISTEMA
# ═══════════════════════════════════════════════════════════════════
phase "[1/9] Actualizando sistema base..."

sudo apt update
sudo apt upgrade -y
sudo apt install -y \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release

success "Sistema actualizado"

# ═══════════════════════════════════════════════════════════════════
# FASE 2: PAQUETES CORE
# ═══════════════════════════════════════════════════════════════════
phase "[2/9] Instalando paquetes core..."

# Build tools
sudo apt install -y \
    build-essential \
    git \
    curl \
    wget \
    unzip \
    cmake \
    pkg-config \
    meson \
    ninja-build

# Xorg y Display
sudo apt install -y \
    xorg \
    xserver-xorg \
    xinit \
    xclip \
    xdotool \
    xsel \
    dbus-x11

# Display Manager
sudo apt install -y \
    lightdm \
    lightdm-gtk-greeter \
    lightdm-gtk-greeter-settings

# Audio (Pipewire)
sudo apt install -y \
    pipewire \
    pipewire-audio \
    pipewire-pulse \
    wireplumber \
    pavucontrol

# Network
sudo apt install -y \
    network-manager \
    network-manager-gnome

# Filesystem
sudo apt install -y \
    thunar \
    thunar-archive-plugin \
    gvfs \
    gvfs-backends \
    udisks2 \
    file-roller

# System utilities
sudo apt install -y \
    htop \
    btop \
    neofetch \
    tree \
    ripgrep \
    fd-find \
    fzf \
    jq

# Terminal
sudo apt install -y \
    kitty \
    tmux

# Fonts
sudo apt install -y \
    fonts-noto \
    fonts-noto-color-emoji \
    fonts-jetbrains-mono \
    fonts-font-awesome

# Themes
sudo apt install -y \
    arc-theme \
    papirus-icon-theme \
    adwaita-icon-theme

# Media
sudo apt install -y \
    imv \
    mpv \
    ffmpeg

# Screenshots
sudo apt install -y \
    maim \
    slop

# Notifications & Theming
sudo apt install -y \
    libnotify-bin \
    lxappearance \
    qt5ct

# Polkit
sudo apt install -y \
    policykit-1 \
    policykit-1-gnome

# Misc
sudo apt install -y \
    feh \
    nitrogen \
    brightnessctl \
    playerctl \
    acpi \
    upower \
    zsh

success "Paquetes core instalados"

# ═══════════════════════════════════════════════════════════════════
# FASE 3: ZSH + OH MY ZSH
# ═══════════════════════════════════════════════════════════════════
phase "[3/9] Instalando Zsh + Oh My Zsh + Powerlevel10k..."

# Instalar Oh My Zsh (sin cambiar shell automáticamente)
if [[ ! -d "$HOME/.oh-my-zsh" ]]; then
    log "Instalando Oh My Zsh..."
    RUNZSH=no CHSH=no sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"
    success "Oh My Zsh instalado"
else
    success "Oh My Zsh ya está instalado"
fi

# Instalar Powerlevel10k
if [[ ! -d "${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}/themes/powerlevel10k" ]]; then
    log "Instalando Powerlevel10k..."
    git clone --depth=1 https://github.com/romkatv/powerlevel10k.git \
        "${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}/themes/powerlevel10k"
    success "Powerlevel10k instalado"
else
    success "Powerlevel10k ya está instalado"
fi

# Instalar plugins populares
ZSH_CUSTOM="${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}"

# zsh-autosuggestions
if [[ ! -d "$ZSH_CUSTOM/plugins/zsh-autosuggestions" ]]; then
    git clone https://github.com/zsh-users/zsh-autosuggestions "$ZSH_CUSTOM/plugins/zsh-autosuggestions"
fi

# zsh-syntax-highlighting
if [[ ! -d "$ZSH_CUSTOM/plugins/zsh-syntax-highlighting" ]]; then
    git clone https://github.com/zsh-users/zsh-syntax-highlighting "$ZSH_CUSTOM/plugins/zsh-syntax-highlighting"
fi

# zsh-completions
if [[ ! -d "$ZSH_CUSTOM/plugins/zsh-completions" ]]; then
    git clone https://github.com/zsh-users/zsh-completions "$ZSH_CUSTOM/plugins/zsh-completions"
fi

# fast-syntax-highlighting (mejor que zsh-syntax-highlighting)
if [[ ! -d "$ZSH_CUSTOM/plugins/fast-syntax-highlighting" ]]; then
    git clone https://github.com/zdharma-continuum/fast-syntax-highlighting "$ZSH_CUSTOM/plugins/fast-syntax-highlighting"
fi

# zsh-autocomplete
if [[ ! -d "$ZSH_CUSTOM/plugins/zsh-autocomplete" ]]; then
    git clone --depth 1 https://github.com/marlonrichert/zsh-autocomplete "$ZSH_CUSTOM/plugins/zsh-autocomplete"
fi

success "Plugins de Zsh instalados"

# Crear configuración .zshrc
log "Configurando .zshrc..."
cat > ~/.zshrc << 'ZSHRC'
# ═══════════════════════════════════════════════════════════════════
# PurmaLinux - Zsh Configuration
# ═══════════════════════════════════════════════════════════════════

# Enable Powerlevel10k instant prompt
if [[ -r "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh" ]]; then
  source "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh"
fi

# Path to Oh My Zsh
export ZSH="$HOME/.oh-my-zsh"

# Theme
ZSH_THEME="powerlevel10k/powerlevel10k"

# Plugins
plugins=(
    git
    sudo
    docker
    docker-compose
    python
    pip
    node
    npm
    command-not-found
    colored-man-pages
    extract
    history
    zsh-autosuggestions
    zsh-completions
    fast-syntax-highlighting
)

# Completions
fpath+=${ZSH_CUSTOM:-${ZSH:-~/.oh-my-zsh}/custom}/plugins/zsh-completions/src

source $ZSH/oh-my-zsh.sh

# ═══════════════════════════════════════════════════════════════════
# USER CONFIGURATION
# ═══════════════════════════════════════════════════════════════════

# Path
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"

# Editor
export EDITOR='nvim'
export VISUAL='nvim'

# PurmaLinux
export PURMA_DIR="$HOME/PurmaLinux"

# Aliases - General
alias ll='ls -alF'
alias la='ls -A'
alias l='ls -CF'
alias cls='clear'
alias ..='cd ..'
alias ...='cd ../..'

# Aliases - PurmaLinux
alias purma='purma-dev'
alias pserver='purma-dev server'
alias pchat='purma-dev chat'
alias ptest='purma-dev test'

# Aliases - Git
alias gs='git status'
alias ga='git add'
alias gc='git commit'
alias gp='git push'
alias gl='git pull'
alias gd='git diff'
alias glog='git log --oneline --graph --decorate'

# Aliases - System
alias update='sudo apt update && sudo apt upgrade -y'
alias install='sudo apt install'
alias remove='sudo apt remove'
alias search='apt search'

# Aliases - Yazi (si está instalado)
if command -v yazi &> /dev/null; then
    alias y='yazi'
fi

# Aliases - Ollama
alias models='ollama list'
alias chat='ollama run llama3.2'

# FZF configuration
if command -v fzf &> /dev/null; then
    export FZF_DEFAULT_OPTS='
        --color=fg:#c9d1d9,bg:#0d1117,hl:#00d4ff
        --color=fg+:#f0f6fc,bg+:#161b22,hl+:#00d4ff
        --color=info:#a855f7,prompt:#00d4ff,pointer:#ec4899
        --color=marker:#22c55e,spinner:#a855f7,header:#8b949e
    '
fi

# Load Powerlevel10k config
[[ ! -f ~/.p10k.zsh ]] || source ~/.p10k.zsh
ZSHRC

# Crear configuración de Powerlevel10k (tema Aurora)
log "Configurando Powerlevel10k con tema Aurora..."
cat > ~/.p10k.zsh << 'P10K'
# Powerlevel10k configuration for PurmaLinux Aurora theme
# Minimal and clean prompt

'builtin' 'local' '-a' 'p10k_config_opts'
[[ ! -o 'aliases'         ]] || p10k_config_opts+=('aliases')
[[ ! -o 'sh_glob'         ]] || p10k_config_opts+=('sh_glob')
[[ ! -o 'no_brace_expand' ]] || p10k_config_opts+=('no_brace_expand')
'builtin' 'setopt' 'no_aliases' 'no_sh_glob' 'brace_expand'

() {
  emulate -L zsh -o extended_glob

  unset -m '(POWERLEVEL9K_*|DEFAULT_USER)~POWERLEVEL9K_GITSTATUS_DIR'

  typeset -g POWERLEVEL9K_LEFT_PROMPT_ELEMENTS=(
    os_icon
    dir
    vcs
    prompt_char
  )

  typeset -g POWERLEVEL9K_RIGHT_PROMPT_ELEMENTS=(
    status
    command_execution_time
    background_jobs
    virtualenv
    node_version
    python_version
  )

  # Basic settings
  typeset -g POWERLEVEL9K_MODE=nerdfont-complete
  typeset -g POWERLEVEL9K_ICON_PADDING=moderate
  typeset -g POWERLEVEL9K_PROMPT_ADD_NEWLINE=true

  # Colors (Aurora theme)
  typeset -g POWERLEVEL9K_BACKGROUND=
  typeset -g POWERLEVEL9K_FOREGROUND=249

  # OS icon
  typeset -g POWERLEVEL9K_OS_ICON_FOREGROUND=cyan
  typeset -g POWERLEVEL9K_OS_ICON_CONTENT_EXPANSION='󰣇'  # Linux icon

  # Directory
  typeset -g POWERLEVEL9K_DIR_FOREGROUND=cyan
  typeset -g POWERLEVEL9K_SHORTEN_STRATEGY=truncate_to_unique
  typeset -g POWERLEVEL9K_SHORTEN_DELIMITER=
  typeset -g POWERLEVEL9K_DIR_SHORTENED_FOREGROUND=103
  typeset -g POWERLEVEL9K_DIR_ANCHOR_FOREGROUND=39
  typeset -g POWERLEVEL9K_DIR_ANCHOR_BOLD=true

  # Git
  typeset -g POWERLEVEL9K_VCS_CLEAN_FOREGROUND=green
  typeset -g POWERLEVEL9K_VCS_MODIFIED_FOREGROUND=yellow
  typeset -g POWERLEVEL9K_VCS_UNTRACKED_FOREGROUND=magenta
  typeset -g POWERLEVEL9K_VCS_CONFLICTED_FOREGROUND=red
  typeset -g POWERLEVEL9K_VCS_LOADING_FOREGROUND=grey

  # Prompt char
  typeset -g POWERLEVEL9K_PROMPT_CHAR_OK_{VIINS,VICMD,VIVIS,VIOWR}_FOREGROUND=cyan
  typeset -g POWERLEVEL9K_PROMPT_CHAR_ERROR_{VIINS,VICMD,VIVIS,VIOWR}_FOREGROUND=red
  typeset -g POWERLEVEL9K_PROMPT_CHAR_{OK,ERROR}_VIINS_CONTENT_EXPANSION='❯'
  typeset -g POWERLEVEL9K_PROMPT_CHAR_{OK,ERROR}_VICMD_CONTENT_EXPANSION='❮'
  typeset -g POWERLEVEL9K_PROMPT_CHAR_{OK,ERROR}_VIVIS_CONTENT_EXPANSION='V'
  typeset -g POWERLEVEL9K_PROMPT_CHAR_OVERWRITE_STATE=true
  typeset -g POWERLEVEL9K_PROMPT_CHAR_{OK,ERROR}_VIOWR_CONTENT_EXPANSION='▶'

  # Status
  typeset -g POWERLEVEL9K_STATUS_EXTENDED_STATES=true
  typeset -g POWERLEVEL9K_STATUS_OK=false
  typeset -g POWERLEVEL9K_STATUS_OK_FOREGROUND=green
  typeset -g POWERLEVEL9K_STATUS_ERROR_FOREGROUND=red

  # Command execution time
  typeset -g POWERLEVEL9K_COMMAND_EXECUTION_TIME_THRESHOLD=3
  typeset -g POWERLEVEL9K_COMMAND_EXECUTION_TIME_PRECISION=0
  typeset -g POWERLEVEL9K_COMMAND_EXECUTION_TIME_FOREGROUND=yellow
  typeset -g POWERLEVEL9K_COMMAND_EXECUTION_TIME_FORMAT='d h m s'

  # Background jobs
  typeset -g POWERLEVEL9K_BACKGROUND_JOBS_VERBOSE=false
  typeset -g POWERLEVEL9K_BACKGROUND_JOBS_FOREGROUND=cyan

  # Python virtualenv
  typeset -g POWERLEVEL9K_VIRTUALENV_FOREGROUND=green
  typeset -g POWERLEVEL9K_VIRTUALENV_SHOW_PYTHON_VERSION=false
  typeset -g POWERLEVEL9K_VIRTUALENV_{LEFT,RIGHT}_DELIMITER=

  # Node version
  typeset -g POWERLEVEL9K_NODE_VERSION_FOREGROUND=green
  typeset -g POWERLEVEL9K_NODE_VERSION_PROJECT_ONLY=true

  # Python version
  typeset -g POWERLEVEL9K_PYTHON_VERSION_FOREGROUND=blue
  typeset -g POWERLEVEL9K_PYTHON_VERSION_PROJECT_ONLY=true

  # Transient prompt
  typeset -g POWERLEVEL9K_TRANSIENT_PROMPT=off

  # Instant prompt
  typeset -g POWERLEVEL9K_INSTANT_PROMPT=quiet

  # Hot reload
  typeset -g POWERLEVEL9K_DISABLE_HOT_RELOAD=true

  (( ${#p10k_config_opts} )) && setopt ${p10k_config_opts[@]}
  'builtin' 'unset' 'p10k_config_opts'
}
P10K

# Cambiar shell por defecto a zsh
log "Cambiando shell por defecto a zsh..."
sudo chsh -s $(which zsh) $USER

success "Zsh + Oh My Zsh + Powerlevel10k configurado"

# ═══════════════════════════════════════════════════════════════════
# FASE 4: WINDOW MANAGERS Y COMPOSITOR
# ═══════════════════════════════════════════════════════════════════
phase "[4/9] Instalando window managers..."

# Openbox
sudo apt install -y \
    openbox \
    obconf \
    obmenu

# i3
sudo apt install -y \
    i3-wm \
    i3lock \
    i3status

# Compositor
sudo apt install -y picom

# Rofi
sudo apt install -y rofi

# Dunst (notificaciones para i3)
sudo apt install -y dunst

success "Window managers instalados"

# ═══════════════════════════════════════════════════════════════════
# FASE 5: POLYBAR
# ═══════════════════════════════════════════════════════════════════
phase "[5/9] Instalando Polybar..."

if ! command -v polybar &> /dev/null; then
    # Dependencias de Polybar
    sudo apt install -y \
        libasound2-dev \
        libcurl4-openssl-dev \
        libiw-dev \
        libmpdclient-dev \
        libpulse-dev \
        libnl-genl-3-dev \
        libcairo2-dev \
        libxcb1-dev \
        libxcb-util0-dev \
        libxcb-randr0-dev \
        libxcb-composite0-dev \
        libxcb-image0-dev \
        libxcb-ewmh-dev \
        libxcb-icccm4-dev \
        libxcb-xkb-dev \
        libxcb-xrm-dev \
        libxcb-cursor-dev \
        python3-xcbgen \
        xcb-proto \
        libjsoncpp-dev \
        libuv1-dev

    log "Compilando Polybar desde source..."
    cd /tmp
    git clone --recursive https://github.com/polybar/polybar.git
    cd polybar
    mkdir build && cd build
    cmake ..
    make -j$(nproc)
    sudo make install
    cd ~
    rm -rf /tmp/polybar
    success "Polybar compilado e instalado"
else
    success "Polybar ya está instalado"
fi

# ═══════════════════════════════════════════════════════════════════
# FASE 6: AGS (Aylur's GTK Shell)
# ═══════════════════════════════════════════════════════════════════
phase "[6/9] Instalando AGS..."

# Dependencias de AGS
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
    gir1.2-nm-1.0 \
    gir1.2-soup-3.0 \
    typescript

# GIR para layer-shell puede no existir en todos los repos
sudo apt install -y gir1.2-gtklayershell-0.1 2>/dev/null || warn "gir1.2-gtklayershell-0.1 no disponible, AGS puede tener funcionalidad limitada"

# Node.js y npm
if ! command -v node &> /dev/null; then
    log "Instalando Node.js..."
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt install -y nodejs
fi

# Instalar AGS
if ! command -v ags &> /dev/null; then
    log "Instalando AGS desde source..."
    cd /tmp
    git clone --depth 1 https://github.com/Aylur/ags.git
    cd ags
    npm install
    sudo npm link
    cd ~
    rm -rf /tmp/ags
    success "AGS instalado"
else
    success "AGS ya está instalado"
fi

# ═══════════════════════════════════════════════════════════════════
# FASE 7: PYTHON Y STACK AI
# ═══════════════════════════════════════════════════════════════════
phase "[7/9] Configurando Python y stack AI..."

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
    portaudio19-dev \
    libsndfile1-dev \
    espeak-ng \
    espeak-ng-espeak

# Dependencias para OCR
sudo apt install -y \
    tesseract-ocr \
    tesseract-ocr-spa \
    tesseract-ocr-eng \
    libtesseract-dev

# Yazi (file manager terminal moderno)
if ! command -v yazi &> /dev/null; then
    log "Instalando Yazi..."
    # Instalar Rust si no existe
    if ! command -v cargo &> /dev/null; then
        curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
        source "$HOME/.cargo/env"
    fi
    cargo install --locked yazi-fm yazi-cli 2>/dev/null || warn "No se pudo instalar Yazi"
fi

success "Python y dependencias AI instaladas"

# ═══════════════════════════════════════════════════════════════════
# FASE 8: OLLAMA
# ═══════════════════════════════════════════════════════════════════
phase "[8/9] Instalando Ollama..."

if ! command -v ollama &> /dev/null; then
    curl -fsSL https://ollama.com/install.sh | sh
    success "Ollama instalado"
else
    success "Ollama ya está instalado"
fi

# Habilitar y arrancar servicio
sudo systemctl enable ollama
sudo systemctl start ollama

# Esperar a que Ollama esté listo
log "Esperando a que Ollama inicie..."
sleep 5

# Verificar que Ollama responde
for i in {1..10}; do
    if curl -s http://localhost:11434/api/tags &>/dev/null; then
        break
    fi
    sleep 2
done

# Descargar modelo
log "Descargando modelo llama3.2 (esto puede tardar varios minutos)..."
ollama pull llama3.2 || warn "No se pudo descargar llama3.2. Ejecutar manualmente: ollama pull llama3.2"

success "Ollama configurado"

# ═══════════════════════════════════════════════════════════════════
# FASE 9: CONFIGURAR PURMALINUX
# ═══════════════════════════════════════════════════════════════════
phase "[9/9] Configurando PurmaLinux..."

# Detectar si el script está dentro del repo
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd)"
if [[ -f "$SCRIPT_DIR/../install.sh" ]]; then
    PURMA_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
    log "Usando repositorio existente: $PURMA_DIR"
fi

cd "$PURMA_DIR" 2>/dev/null || cd ~

# Crear directorios necesarios
mkdir -p ~/.config/{openbox,i3,polybar,rofi,dunst,kitty,picom,ags,gtk-3.0,yazi,thunar}
mkdir -p ~/.local/bin
mkdir -p ~/.purma/{cortex,memory,ghost,vault,scribe,sync,lens,logs}
mkdir -p ~/.local/share/applications

# Copiar configuraciones si existen
if [[ -d "$PURMA_DIR" && -f "$PURMA_DIR/install.sh" ]]; then
    log "Copiando configuraciones de PurmaLinux..."

    # i3
    [[ -f "$PURMA_DIR/i3/config/config" ]] && cp "$PURMA_DIR/i3/config/config" ~/.config/i3/config
    [[ -f "$PURMA_DIR/i3/config/autostart.sh" ]] && cp "$PURMA_DIR/i3/config/autostart.sh" ~/.config/i3/ && chmod +x ~/.config/i3/autostart.sh

    # Polybar
    [[ -f "$PURMA_DIR/i3/polybar/config.ini" ]] && cp "$PURMA_DIR/i3/polybar/config.ini" ~/.config/polybar/

    # Rofi
    [[ -d "$PURMA_DIR/i3/rofi" ]] && cp -r "$PURMA_DIR/i3/rofi/"* ~/.config/rofi/ 2>/dev/null || true
    [[ -d "$PURMA_DIR/desktop/rofi" ]] && cp -r "$PURMA_DIR/desktop/rofi/"* ~/.config/rofi/ 2>/dev/null || true

    # Dunst
    [[ -f "$PURMA_DIR/i3/dunst/dunstrc" ]] && cp "$PURMA_DIR/i3/dunst/dunstrc" ~/.config/dunst/

    # Picom
    [[ -f "$PURMA_DIR/i3/picom/picom.conf" ]] && cp "$PURMA_DIR/i3/picom/picom.conf" ~/.config/picom/
    [[ -f "$PURMA_DIR/desktop/picom/picom.conf" ]] && cp "$PURMA_DIR/desktop/picom/picom.conf" ~/.config/picom/

    # Kitty
    [[ -f "$PURMA_DIR/i3/kitty/kitty.conf" ]] && cp "$PURMA_DIR/i3/kitty/kitty.conf" ~/.config/kitty/
    [[ -f "$PURMA_DIR/desktop/kitty/kitty.conf" ]] && cp "$PURMA_DIR/desktop/kitty/kitty.conf" ~/.config/kitty/

    # GTK
    [[ -f "$PURMA_DIR/i3/gtk-3.0/settings.ini" ]] && cp "$PURMA_DIR/i3/gtk-3.0/settings.ini" ~/.config/gtk-3.0/

    # Openbox
    [[ -f "$PURMA_DIR/desktop/openbox/rc.xml" ]] && cp "$PURMA_DIR/desktop/openbox/rc.xml" ~/.config/openbox/
    [[ -f "$PURMA_DIR/desktop/openbox/autostart" ]] && cp "$PURMA_DIR/desktop/openbox/autostart" ~/.config/openbox/ && chmod +x ~/.config/openbox/autostart
    [[ -f "$PURMA_DIR/desktop/openbox/menu.xml" ]] && cp "$PURMA_DIR/desktop/openbox/menu.xml" ~/.config/openbox/

    # Openbox theme
    if [[ -d "$PURMA_DIR/desktop/openbox/themes/Aurora-PurmaLinux" ]]; then
        mkdir -p ~/.themes/Aurora-PurmaLinux/openbox-3
        cp -r "$PURMA_DIR/desktop/openbox/themes/Aurora-PurmaLinux/"* ~/.themes/Aurora-PurmaLinux/openbox-3/
    fi

    # AGS
    [[ -f "$PURMA_DIR/desktop/ags/config.js" ]] && cp "$PURMA_DIR/desktop/ags/config.js" ~/.config/ags/
    [[ -f "$PURMA_DIR/desktop/ags/style.css" ]] && cp "$PURMA_DIR/desktop/ags/style.css" ~/.config/ags/
    [[ -d "$PURMA_DIR/desktop/ags/widgets" ]] && cp -r "$PURMA_DIR/desktop/ags/widgets" ~/.config/ags/

    # Yazi
    [[ -d "$PURMA_DIR/desktop/yazi" ]] && cp -r "$PURMA_DIR/desktop/yazi/"* ~/.config/yazi/ 2>/dev/null || true

    # Thunar custom actions
    [[ -f "$PURMA_DIR/desktop/thunar/uca.xml" ]] && cp "$PURMA_DIR/desktop/thunar/uca.xml" ~/.config/Thunar/

    # Binarios/scripts
    [[ -d "$PURMA_DIR/bin" ]] && cp -r "$PURMA_DIR/bin/"* ~/.local/bin/ 2>/dev/null || true
    [[ -d "$PURMA_DIR/shared/bin" ]] && cp -r "$PURMA_DIR/shared/bin/"* ~/.local/bin/ 2>/dev/null || true
    chmod +x ~/.local/bin/* 2>/dev/null || true

    success "Configuraciones copiadas"

    # Crear entorno virtual Python
    log "Configurando entorno Python..."
    cd "$PURMA_DIR"
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip -q

    if [[ -f "ai/server/requirements.txt" ]]; then
        pip install -r ai/server/requirements.txt -q
    fi

    # Instalar dependencias adicionales para todos los módulos
    pip install -q \
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

    success "Entorno Python configurado"
else
    warn "Repositorio PurmaLinux no encontrado en $PURMA_DIR"
    warn "Copiar el repositorio manualmente y ejecutar ./install.sh"
fi

# ═══════════════════════════════════════════════════════════════════
# CREAR ARCHIVOS DE SESIÓN X
# ═══════════════════════════════════════════════════════════════════
log "Configurando sesiones de escritorio..."

# Sesión Openbox para LightDM
sudo tee /usr/share/xsessions/purmalinux-openbox.desktop > /dev/null << 'EOF'
[Desktop Entry]
Name=PurmaLinux (Openbox)
Comment=PurmaLinux Desktop with Openbox and AGS
Exec=openbox-session
Type=Application
EOF

# Sesión i3 para LightDM
sudo tee /usr/share/xsessions/purmalinux-i3.desktop > /dev/null << 'EOF'
[Desktop Entry]
Name=PurmaLinux (i3)
Comment=PurmaLinux with i3 tiling window manager
Exec=i3
Type=Application
EOF

success "Sesiones de escritorio creadas"

# ═══════════════════════════════════════════════════════════════════
# CREAR SCRIPTS DE UTILIDAD
# ═══════════════════════════════════════════════════════════════════
log "Creando scripts de utilidad..."

# Script purma-dev
cat > ~/.local/bin/purma-dev << 'SCRIPT'
#!/bin/bash
PURMA_DIR="$HOME/PurmaLinux"
cd "$PURMA_DIR" 2>/dev/null || { echo "PurmaLinux no encontrado en $PURMA_DIR"; exit 1; }
source venv/bin/activate 2>/dev/null || { echo "Entorno virtual no encontrado"; exit 1; }

case "$1" in
    server|s)
        echo "Iniciando Purma Server en http://localhost:11435..."
        python ai/server/purma_server.py
        ;;
    chat|c)
        if [[ -f "ai/chat/purma-chat-cli.py" ]]; then
            python ai/chat/purma-chat-cli.py
        else
            echo "Chat CLI no encontrado"
        fi
        ;;
    test|t)
        echo "Probando conexión..."
        echo -n "Ollama: "
        curl -s http://localhost:11434/api/tags &>/dev/null && echo "OK" || echo "FAIL"
        echo -n "Purma Server: "
        curl -s http://localhost:11435/status &>/dev/null && echo "OK" || echo "FAIL (iniciar con: purma-dev server)"
        ;;
    logs|l)
        journalctl -u ollama -f
        ;;
    models|m)
        ollama list
        ;;
    pull)
        shift
        ollama pull "$@"
        ;;
    *)
        echo "PurmaLinux Development Tool"
        echo ""
        echo "Uso: purma-dev <comando>"
        echo ""
        echo "Comandos:"
        echo "  server, s    Iniciar servidor AI (puerto 11435)"
        echo "  chat, c      Abrir chat CLI"
        echo "  test, t      Probar conexiones"
        echo "  logs, l      Ver logs de Ollama"
        echo "  models, m    Listar modelos instalados"
        echo "  pull <name>  Descargar modelo de Ollama"
        ;;
esac
SCRIPT
chmod +x ~/.local/bin/purma-dev

# Script para iniciar Purma Server como servicio
mkdir -p ~/.config/systemd/user
cat > ~/.config/systemd/user/purma-server.service << 'SYSTEMD'
[Unit]
Description=PurmaLinux AI Server
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

# Añadir ~/.local/bin al PATH
if ! grep -q 'local/bin' ~/.bashrc; then
    echo '' >> ~/.bashrc
    echo '# PurmaLinux' >> ~/.bashrc
    echo 'export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"' >> ~/.bashrc
fi

success "Scripts de utilidad creados"

# ═══════════════════════════════════════════════════════════════════
# CONFIGURAR LIGHTDM
# ═══════════════════════════════════════════════════════════════════
log "Configurando LightDM..."

sudo systemctl enable lightdm

# Configurar greeter
sudo tee /etc/lightdm/lightdm-gtk-greeter.conf > /dev/null << 'EOF'
[greeter]
theme-name = Arc-Dark
icon-theme-name = Papirus-Dark
font-name = JetBrains Mono 10
background = #0d1117
user-background = false
EOF

success "LightDM configurado"

# ═══════════════════════════════════════════════════════════════════
# RESUMEN FINAL
# ═══════════════════════════════════════════════════════════════════
echo ""
echo -e "${MAGENTA}════════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${GREEN}"
cat << 'EOF'
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║      ██████╗ ██╗   ██╗██████╗ ███╗   ███╗ █████╗                 ║
║      ██╔══██╗██║   ██║██╔══██╗████╗ ████║██╔══██╗                ║
║      ██████╔╝██║   ██║██████╔╝██╔████╔██║███████║                ║
║      ██╔═══╝ ██║   ██║██╔══██╗██║╚██╔╝██║██╔══██║                ║
║      ██║     ╚██████╔╝██║  ██║██║ ╚═╝ ██║██║  ██║                ║
║      ╚═╝      ╚═════╝ ╚═╝  ╚═╝╚═╝     ╚═╝╚═╝  ╚═╝                ║
║                                                                  ║
║           ¡INSTALACIÓN COMPLETADA!                               ║
║                                                                  ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  Para iniciar el entorno gráfico:                                ║
║                                                                  ║
║    sudo systemctl start lightdm                                  ║
║                                                                  ║
║  O reiniciar el sistema:                                         ║
║                                                                  ║
║    sudo reboot                                                   ║
║                                                                  ║
║  Sesiones disponibles en LightDM:                                ║
║    • PurmaLinux (Openbox) - Desktop con AGS                      ║
║    • PurmaLinux (i3) - Tiling con Polybar                        ║
║                                                                  ║
║  Comandos útiles:                                                ║
║    purma-dev server  → Iniciar servidor AI                       ║
║    purma-dev test    → Verificar servicios                       ║
║    purma-dev chat    → Chat CLI                                  ║
║                                                                  ║
║  Atajos principales (en i3/Openbox):                             ║
║    Super+A           → Purma Chat                                ║
║    Super+Return      → Terminal (Kitty)                          ║
║    Super+D           → Launcher (Rofi)                           ║
║    Super+Q           → Cerrar ventana                            ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

echo ""
read -p "¿Reiniciar ahora para iniciar el entorno gráfico? [Y/n]: " reboot_choice
if [[ ! "$reboot_choice" =~ ^[Nn]$ ]]; then
    sudo reboot
fi
