#!/usr/bin/env bash
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  PurmaLinux Power Menu Script                                                ║
# ║  Aurora Theme                                                                ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

# Options with icons
LOCK="  Lock"
LOGOUT="󰍃  Logout"
SUSPEND="󰤄  Suspend"
REBOOT="  Reboot"
SHUTDOWN="󰐥  Shutdown"

# Show menu
if [ -z "$@" ]; then
    echo -e "$LOCK\n$LOGOUT\n$SUSPEND\n$REBOOT\n$SHUTDOWN"
else
    case "$1" in
        *Lock)
            i3lock-color -c 0a0e14 \
                --ring-color=00d4ff \
                --keyhl-color=a855f7 \
                --bshl-color=ef4444 \
                --insidever-color=0a0e14 \
                --ringver-color=22c55e \
                --insidewrong-color=0a0e14 \
                --ringwrong-color=ef4444 \
                --line-color=00000000 \
                --separator-color=00000000 \
                --verif-color=f0f6fc \
                --wrong-color=ef4444 \
                --time-color=00d4ff \
                --date-color=8b949e \
                --layout-color=8b949e \
                --greeter-color=c9d1d9 \
                --ind-pos="w/2:h/2" \
                --time-pos="w/2:h/2-80" \
                --date-pos="w/2:h/2+80" \
                --greeter-pos="w/2:h-80" \
                --clock --indicator \
                --time-str="%H:%M" \
                --date-str="%A, %B %d" \
                --greeter-text="PurmaLinux"
            ;;
        *Logout)
            i3-msg exit
            ;;
        *Suspend)
            systemctl suspend
            ;;
        *Reboot)
            systemctl reboot
            ;;
        *Shutdown)
            systemctl poweroff
            ;;
    esac
fi
