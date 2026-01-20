#!/usr/bin/env bash
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                                                                              ║
# ║                   PurmaLinux i3 Autostart Script                             ║
# ║                         Aurora Theme                                          ║
# ║                                                                              ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

# Kill any existing processes
killall -q picom polybar dunst

# Wait for processes to shut down
while pgrep -x picom >/dev/null; do sleep 0.1; done
while pgrep -x polybar >/dev/null; do sleep 0.1; done

# ═══════════════════════════════════════════════════════════════════════════════
#  Desktop Environment Setup
# ═══════════════════════════════════════════════════════════════════════════════

# Set wallpaper (Aurora-themed gradient or image)
if command -v feh &> /dev/null; then
    # Use solid color if no wallpaper exists
    feh --bg-fill ~/.config/wallpaper.jpg 2>/dev/null || \
    feh --bg-fill /usr/share/backgrounds/purmalinux-aurora.png 2>/dev/null || \
    hsetroot -solid "#0a0e14"
elif command -v nitrogen &> /dev/null; then
    nitrogen --restore &
elif command -v hsetroot &> /dev/null; then
    hsetroot -solid "#0a0e14"
fi

# ═══════════════════════════════════════════════════════════════════════════════
#  Compositor (Picom) - Blur, Shadows, Transparency
# ═══════════════════════════════════════════════════════════════════════════════
picom --config ~/.config/picom/picom.conf -b &

# ═══════════════════════════════════════════════════════════════════════════════
#  Polybar - Status Bar
# ═══════════════════════════════════════════════════════════════════════════════
# Launch Polybar on each monitor
if type "xrandr" &> /dev/null; then
    for m in $(xrandr --query | grep " connected" | cut -d" " -f1); do
        MONITOR=$m polybar --reload aurora 2>&1 | tee -a /tmp/polybar-$m.log &
    done
else
    polybar --reload aurora 2>&1 | tee -a /tmp/polybar.log &
fi
disown

# ═══════════════════════════════════════════════════════════════════════════════
#  Notifications (Dunst)
# ═══════════════════════════════════════════════════════════════════════════════
dunst &

# ═══════════════════════════════════════════════════════════════════════════════
#  System Services
# ═══════════════════════════════════════════════════════════════════════════════

# PolicyKit authentication agent
/usr/lib/polkit-gnome/polkit-gnome-authentication-agent-1 &>/dev/null &
/usr/lib/policykit-1-gnome/polkit-gnome-authentication-agent-1 &>/dev/null &

# Network Manager applet
nm-applet &

# Bluetooth applet (if available)
command -v blueman-applet &> /dev/null && blueman-applet &

# Clipboard manager
command -v clipit &> /dev/null && clipit &
command -v parcellite &> /dev/null && parcellite &

# Screen locker daemon
command -v xss-lock &> /dev/null && xss-lock -- i3lock-color -c 0a0e14 &

# ═══════════════════════════════════════════════════════════════════════════════
#  Input Settings
# ═══════════════════════════════════════════════════════════════════════════════

# Keyboard repeat rate
xset r rate 300 50 2>/dev/null

# Disable screen blanking (optional)
# xset s off
# xset -dpms
# xset s noblank

# Set numlock on (if numlockx is available)
command -v numlockx &> /dev/null && numlockx on

# ═══════════════════════════════════════════════════════════════════════════════
#  Cursor Theme
# ═══════════════════════════════════════════════════════════════════════════════
xsetroot -cursor_name left_ptr 2>/dev/null

# ═══════════════════════════════════════════════════════════════════════════════
#  PurmaLinux AI Services
# ═══════════════════════════════════════════════════════════════════════════════

# Start Ollama if not running
if ! pgrep -x "ollama" > /dev/null; then
    ollama serve &>/dev/null &
fi

# Start Purma AI server (if not already running)
if ! pgrep -f "purma_server.py" > /dev/null; then
    (cd ~/PurmaLinux/ai/server && python purma_server.py &>/dev/null &)
fi

# AGS (Aylur's GTK Shell) for Purma widgets
command -v ags &> /dev/null && ags &

# EWW (ElKowars Wacky Widgets) for Purma Models widget
if command -v eww &> /dev/null; then
    eww daemon &
    # Optional: Open models bar button
    # eww open models-bar &
fi

# ═══════════════════════════════════════════════════════════════════════════════
#  XDG Autostart
# ═══════════════════════════════════════════════════════════════════════════════
command -v dex &> /dev/null && dex -a -s ~/.config/autostart/ 2>/dev/null &

# ═══════════════════════════════════════════════════════════════════════════════
#  Startup Notification
# ═══════════════════════════════════════════════════════════════════════════════
sleep 2
notify-send -u normal -i face-robot "PurmaLinux Aurora" "Desktop environment loaded\nPress Super+A for Purma AI"

echo "[$(date)] PurmaLinux i3 Aurora theme loaded successfully"
