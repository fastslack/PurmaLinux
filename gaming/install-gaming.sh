#!/bin/bash
#
# PurmaLinux - Gaming Stack Installation
# Instala todo lo necesario para gaming en Linux
#
# Uso: bash install-gaming.sh
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

   ██████╗  █████╗ ███╗   ███╗██╗███╗   ██╗ ██████╗
  ██╔════╝ ██╔══██╗████╗ ████║██║████╗  ██║██╔════╝
  ██║  ███╗███████║██╔████╔██║██║██╔██╗ ██║██║  ███╗
  ██║   ██║██╔══██║██║╚██╔╝██║██║██║╚██╗██║██║   ██║
  ╚██████╔╝██║  ██║██║ ╚═╝ ██║██║██║ ╚████║╚██████╔╝
   ╚═════╝ ╚═╝  ╚═╝╚═╝     ╚═╝╚═╝╚═╝  ╚═══╝ ╚═════╝
BANNER
echo -e "${NC}"
echo ""

# ═══════════════════════════════════════════════════════════════════
# DETECT GPU
# ═══════════════════════════════════════════════════════════════════
log "Detectando GPU..."

GPU_VENDOR="unknown"
if lspci | grep -i nvidia > /dev/null 2>&1; then
    GPU_VENDOR="nvidia"
    success "GPU NVIDIA detectada"
elif lspci | grep -i "amd\|radeon" > /dev/null 2>&1; then
    GPU_VENDOR="amd"
    success "GPU AMD detectada"
elif lspci | grep -i intel > /dev/null 2>&1; then
    GPU_VENDOR="intel"
    success "GPU Intel detectada"
else
    warn "No se pudo detectar la GPU"
fi

# ═══════════════════════════════════════════════════════════════════
# ENABLE 32-BIT
# ═══════════════════════════════════════════════════════════════════
log "Habilitando arquitectura i386 (32-bit)..."

sudo dpkg --add-architecture i386
sudo apt update

success "Arquitectura i386 habilitada"

# ═══════════════════════════════════════════════════════════════════
# GPU DRIVERS
# ═══════════════════════════════════════════════════════════════════
log "Instalando drivers de GPU..."

case $GPU_VENDOR in
    nvidia)
        log "Instalando drivers NVIDIA..."
        # Añadir PPA de drivers si no existe
        sudo add-apt-repository -y ppa:graphics-drivers/ppa 2>/dev/null || true
        sudo apt update

        # Instalar driver recomendado
        sudo apt install -y \
            nvidia-driver-535 \
            nvidia-settings \
            nvidia-prime \
            libvulkan1 \
            libvulkan1:i386 \
            nvidia-vulkan-icd \
            libnvidia-gl-535:i386 2>/dev/null || {
            warn "No se pudieron instalar drivers NVIDIA específicos"
            sudo apt install -y nvidia-driver
        }
        ;;

    amd)
        log "Instalando drivers AMD (Mesa)..."
        sudo apt install -y \
            mesa-vulkan-drivers \
            mesa-vulkan-drivers:i386 \
            libvulkan1 \
            libvulkan1:i386 \
            vulkan-tools \
            libgl1-mesa-dri:i386 \
            mesa-utils \
            radeontop
        ;;

    intel)
        log "Instalando drivers Intel..."
        sudo apt install -y \
            mesa-vulkan-drivers \
            mesa-vulkan-drivers:i386 \
            intel-media-va-driver \
            libvulkan1 \
            libvulkan1:i386 \
            vulkan-tools \
            libgl1-mesa-dri:i386
        ;;

    *)
        log "Instalando drivers genéricos..."
        sudo apt install -y \
            mesa-vulkan-drivers \
            libvulkan1 \
            vulkan-tools
        ;;
esac

success "Drivers de GPU instalados"

# ═══════════════════════════════════════════════════════════════════
# 32-BIT LIBRARIES
# ═══════════════════════════════════════════════════════════════════
log "Instalando bibliotecas 32-bit..."

sudo apt install -y \
    libc6-i386 \
    lib32z1 \
    lib32gcc-s1 \
    lib32stdc++6 \
    libgl1:i386 \
    libglx0:i386 \
    libglu1-mesa:i386

success "Bibliotecas 32-bit instaladas"

# ═══════════════════════════════════════════════════════════════════
# WINE
# ═══════════════════════════════════════════════════════════════════
log "Instalando Wine..."

# Añadir repositorio de WineHQ
sudo mkdir -pm755 /etc/apt/keyrings
sudo wget -O /etc/apt/keyrings/winehq-archive.key https://dl.winehq.org/wine-builds/winehq.key 2>/dev/null || true
sudo wget -NP /etc/apt/sources.list.d/ https://dl.winehq.org/wine-builds/ubuntu/dists/$(lsb_release -cs)/winehq-$(lsb_release -cs).sources 2>/dev/null || true

sudo apt update
sudo apt install -y --install-recommends winehq-staging || sudo apt install -y wine wine64 wine32

# Winetricks
sudo apt install -y winetricks

success "Wine instalado"

# ═══════════════════════════════════════════════════════════════════
# STEAM
# ═══════════════════════════════════════════════════════════════════
log "Instalando Steam..."

# Aceptar licencia de Steam automáticamente
echo "steam steam/question select I AGREE" | sudo debconf-set-selections
echo "steam steam/license note" | sudo debconf-set-selections

sudo apt install -y steam steam-devices

success "Steam instalado"

# ═══════════════════════════════════════════════════════════════════
# LUTRIS
# ═══════════════════════════════════════════════════════════════════
log "Instalando Lutris..."

# Añadir PPA de Lutris
sudo add-apt-repository -y ppa:lutris-team/lutris 2>/dev/null || true
sudo apt update
sudo apt install -y lutris

success "Lutris instalado"

# ═══════════════════════════════════════════════════════════════════
# HEROIC GAMES LAUNCHER
# ═══════════════════════════════════════════════════════════════════
log "Instalando Heroic Games Launcher..."

# Descargar último release
HEROIC_URL=$(curl -s https://api.github.com/repos/Heroic-Games-Launcher/HeroicGamesLauncher/releases/latest | grep "browser_download_url.*amd64.deb" | cut -d '"' -f 4 | head -1)

if [[ -n "$HEROIC_URL" ]]; then
    wget -O /tmp/heroic.deb "$HEROIC_URL"
    sudo apt install -y /tmp/heroic.deb
    rm /tmp/heroic.deb
    success "Heroic instalado"
else
    warn "No se pudo descargar Heroic, instalar manualmente desde https://heroicgameslauncher.com"
fi

# ═══════════════════════════════════════════════════════════════════
# GAMEMODE
# ═══════════════════════════════════════════════════════════════════
log "Instalando GameMode..."

sudo apt install -y gamemode

# Configurar gamemode
mkdir -p ~/.config/gamemode
cat > ~/.config/gamemode/gamemode.ini << 'GAMEMODE'
[general]
; Renice spawned processes to this value
renice = 10

[gpu]
; Apply GPU optimizations
apply_gpu_optimisations = accept-responsibility
; GPU power mode (nvidia only: adaptive, prefer_maximum_performance)
gpu_device = 0
nv_powermizer_mode = 1

[cpu]
; Set CPU governor to performance
desiredgov = performance

[custom]
; Script to run when gamemode starts
start = notify-send "GameMode" "Gaming optimizations enabled"
; Script to run when gamemode ends
end = notify-send "GameMode" "Gaming optimizations disabled"
GAMEMODE

success "GameMode instalado y configurado"

# ═══════════════════════════════════════════════════════════════════
# MANGOHUD
# ═══════════════════════════════════════════════════════════════════
log "Instalando MangoHud..."

sudo apt install -y mangohud

# Instalar GOverlay para configurar MangoHud
sudo apt install -y goverlay 2>/dev/null || {
    # Si no está en repos, compilar
    warn "GOverlay no disponible en repos, instalando desde Flatpak..."
    flatpak install -y flathub io.github.benjamimgois.goverlay 2>/dev/null || true
}

# Configurar MangoHud
mkdir -p ~/.config/MangoHud
cat > ~/.config/MangoHud/MangoHud.conf << 'MANGOHUD'
# PurmaLinux MangoHud Configuration

# Position
position = top-left
round_corners = 8

# Toggle key
toggle_hud = Shift_R+F12

# Display
fps
frametime
cpu_stats
cpu_temp
gpu_stats
gpu_temp
ram
vram

# Appearance
font_size = 20
background_alpha = 0.5
font_scale = 1.0

# Colors (Aurora theme)
gpu_color = 00d4ff
cpu_color = a855f7
frametime_color = 22c55e
background_color = 0d1117
text_color = c9d1d9

# FPS limit indicator
fps_limit = 0
fps_limit_method = late

# Logging
output_folder = ~/.purma/gamehub/logs
log_duration = 30
MANGOHUD

success "MangoHud instalado y configurado"

# ═══════════════════════════════════════════════════════════════════
# PROTON-GE
# ═══════════════════════════════════════════════════════════════════
log "Instalando ProtonUp-Qt para gestionar versiones de Proton..."

# Instalar desde Flatpak (más fácil)
flatpak install -y flathub net.davidotek.pupgui2 2>/dev/null || {
    warn "No se pudo instalar ProtonUp-Qt"
}

success "ProtonUp-Qt instalado"

# ═══════════════════════════════════════════════════════════════════
# GAME CONTROLLERS
# ═══════════════════════════════════════════════════════════════════
log "Instalando soporte para controladores..."

sudo apt install -y \
    joystick \
    jstest-gtk \
    xboxdrv 2>/dev/null || true

# Instalar AntiMicroX para mapeo de controles
sudo apt install -y antimicrox 2>/dev/null || {
    flatpak install -y flathub io.github.antimicrox.antimicrox 2>/dev/null || true
}

# Reglas udev para controladores
sudo tee /etc/udev/rules.d/99-steam-controller.rules > /dev/null << 'UDEV'
# Steam Controller
SUBSYSTEM=="usb", ATTRS{idVendor}=="28de", MODE="0666"
KERNEL=="uinput", MODE="0660", GROUP="input", OPTIONS+="static_node=uinput"
# Xbox controllers
SUBSYSTEM=="usb", ATTR{idVendor}=="045e", ATTR{idProduct}=="028e", MODE="0666"
SUBSYSTEM=="usb", ATTR{idVendor}=="045e", ATTR{idProduct}=="0719", MODE="0666"
# PS4/PS5 controllers
SUBSYSTEM=="usb", ATTR{idVendor}=="054c", ATTR{idProduct}=="05c4", MODE="0666"
SUBSYSTEM=="usb", ATTR{idVendor}=="054c", ATTR{idProduct}=="09cc", MODE="0666"
SUBSYSTEM=="usb", ATTR{idVendor}=="054c", ATTR{idProduct}=="0ce6", MODE="0666"
UDEV

sudo udevadm control --reload-rules

success "Soporte para controladores instalado"

# ═══════════════════════════════════════════════════════════════════
# DISCORD (Optional)
# ═══════════════════════════════════════════════════════════════════
read -p "¿Instalar Discord? [y/N]: " install_discord
if [[ "$install_discord" =~ ^[Yy]$ ]]; then
    log "Instalando Discord..."
    wget -O /tmp/discord.deb "https://discord.com/api/download?platform=linux&format=deb"
    sudo apt install -y /tmp/discord.deb
    rm /tmp/discord.deb
    success "Discord instalado"
fi

# ═══════════════════════════════════════════════════════════════════
# OPENRA (Native Linux RTS Games)
# ═══════════════════════════════════════════════════════════════════
log "Instalando OpenRA (Command & Conquer, Red Alert, Dune 2000)..."

# Añadir PPA oficial de OpenRA
sudo add-apt-repository -y ppa:openra/release 2>/dev/null || true
sudo apt update
sudo apt install -y openra

success "OpenRA instalado"

# ═══════════════════════════════════════════════════════════════════
# CORECTRL (AMD GPU Control)
# ═══════════════════════════════════════════════════════════════════
if [[ "$GPU_VENDOR" == "amd" ]]; then
    log "Instalando CoreCtrl para control de GPU AMD..."

    sudo add-apt-repository -y ppa:ernstp/mesarc 2>/dev/null || true
    sudo apt update
    sudo apt install -y corectrl

    # Permitir CoreCtrl sin password
    sudo tee /etc/polkit-1/rules.d/90-corectrl.rules > /dev/null << 'POLKIT'
polkit.addRule(function(action, subject) {
    if ((action.id == "org.corectrl.helper.init" ||
         action.id == "org.corectrl.helperkiller.init") &&
        subject.local == true &&
        subject.active == true &&
        subject.isInGroup("sudo")) {
            return polkit.Result.YES;
    }
});
POLKIT

    success "CoreCtrl instalado"
fi

# ═══════════════════════════════════════════════════════════════════
# CREATE GAMEHUB DATA DIRECTORY
# ═══════════════════════════════════════════════════════════════════
mkdir -p ~/.purma/gamehub/{logs,cache,screenshots}

# ═══════════════════════════════════════════════════════════════════
# ADD GAMING KEYBINDING
# ═══════════════════════════════════════════════════════════════════
log "Creando script de toggle para GameHub..."

mkdir -p ~/.local/bin
cat > ~/.local/bin/purma-gamehub-toggle << 'SCRIPT'
#!/bin/bash
# Toggle Purma GameHub widget
# Usa DBus o AGS command para toggle

# Si AGS está corriendo, usar su método
if pgrep -x ags > /dev/null; then
    ags -r "toggleGameHub()"
else
    # Fallback: abrir lutris o steam
    if command -v lutris &> /dev/null; then
        lutris
    elif command -v steam &> /dev/null; then
        steam
    fi
fi
SCRIPT
chmod +x ~/.local/bin/purma-gamehub-toggle

# ═══════════════════════════════════════════════════════════════════
# RESUMEN
# ═══════════════════════════════════════════════════════════════════
echo ""
echo -e "${GREEN}"
cat << 'EOF'
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║         ¡Gaming Stack instalado correctamente!                   ║
║                                                                  ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  Instalado:                                                      ║
║    ✓ Steam                                                       ║
║    ✓ Lutris                                                      ║
║    ✓ Heroic Games Launcher                                       ║
║    ✓ Wine/Proton                                                 ║
║    ✓ GameMode (optimización automática)                          ║
║    ✓ MangoHud (overlay de rendimiento)                           ║
║    ✓ ProtonUp-Qt (gestión de Proton)                             ║
║    ✓ OpenRA (C&C, Red Alert, Dune 2000)                          ║
║    ✓ Controladores (Xbox, PS4/PS5, Steam)                        ║
║                                                                  ║
║  Comandos útiles:                                                ║
║    gamemoderun ./juego     → Ejecutar con GameMode               ║
║    mangohud ./juego        → Ejecutar con overlay                ║
║    gamemoderun mangohud %command%  → Launch option Steam         ║
║                                                                  ║
║  Configuración:                                                  ║
║    MangoHud: ~/.config/MangoHud/MangoHud.conf                    ║
║    GameMode: ~/.config/gamemode/gamemode.ini                     ║
║                                                                  ║
║  Atajos:                                                         ║
║    Super+G      → Purma GameHub                                  ║
║    Shift+F12    → Toggle MangoHud overlay                        ║
║                                                                  ║
║  Próximo paso:                                                   ║
║    Reiniciar sesión para aplicar cambios de grupos               ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

echo ""
warn "Es recomendable reiniciar para que todos los cambios surtan efecto"
read -p "¿Reiniciar ahora? [y/N]: " reboot_choice
if [[ "$reboot_choice" =~ ^[Yy]$ ]]; then
    sudo reboot
fi
