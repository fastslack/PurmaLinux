#!/bin/bash
# PurmaLinux - Install Spaces Persistence Services
# Run this script to enable automatic space save/restore

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
USER_SERVICES_DIR="${HOME}/.config/systemd/user"

echo "Installing Purma Spaces persistence services..."

# Create user services directory
mkdir -p "$USER_SERVICES_DIR"

# Install the scripts
echo "Installing purma scripts..."
sudo install -m 755 "${SCRIPT_DIR}/purma-spaces" /usr/local/bin/purma-spaces
sudo install -m 755 "${SCRIPT_DIR}/purma-spaces-ctl" /usr/local/bin/purma-spaces-ctl
sudo install -m 755 "${SCRIPT_DIR}/purma-flow-ctl" /usr/local/bin/purma-flow-ctl
sudo install -m 755 "${SCRIPT_DIR}/purma-bridge" /usr/local/bin/purma-bridge
sudo install -m 755 "${SCRIPT_DIR}/purma-pulse-ctl" /usr/local/bin/purma-pulse-ctl

# Install user services
echo "Installing systemd user services..."
cp "${SCRIPT_DIR}/purma-spaces-restore.service" "$USER_SERVICES_DIR/"
cp "${SCRIPT_DIR}/purma-spaces-save.service" "$USER_SERVICES_DIR/"

# Reload systemd
echo "Reloading systemd..."
systemctl --user daemon-reload

# Enable services
echo "Enabling services..."
systemctl --user enable purma-spaces-restore.service
systemctl --user enable purma-spaces-save.service

echo ""
echo "Installation complete!"
echo ""
echo "Services installed:"
echo "  - purma-spaces-restore.service (runs on login)"
echo "  - purma-spaces-save.service (runs on shutdown)"
echo ""
echo "Commands:"
echo "  purma-spaces save       # Save current state"
echo "  purma-spaces restore    # Restore last state"
echo "  purma-spaces-ctl toggle # Toggle Spaces popup"
echo "  purma-spaces-ctl menu   # Rofi space selector"
echo "  purma-spaces-ctl next   # Next space"
echo "  purma-spaces-ctl prev   # Previous space"
echo "  purma-flow-ctl toggle   # Toggle Flow popup"
echo "  purma-flow-ctl record   # Toggle recording"
echo "  purma-bridge            # AI-augmented terminal"
echo "  purma-pulse-ctl status  # System health status"
echo "  purma-pulse-ctl metrics # Detailed metrics"
echo "  purma-pulse-ctl insights# AI insights"
echo "  purma-pulse-ctl cleanup # Clean disk space"
echo ""
echo "Keyboard shortcuts (Openbox):"
echo "  Super+S         Toggle Spaces popup"
echo "  Super+Shift+S   Rofi space selector"
echo "  Super+]         Next space"
echo "  Super+[         Previous space"
echo "  Ctrl+Super+1-4  Quick spaces (work/code/focus/gaming)"
echo "  Super+G         Toggle Flow popup"
echo "  Super+Shift+G   Toggle recording"
echo "  Super+B         Toggle Bridge popup"
echo "  Super+Shift+B   Open Bridge terminal"
echo "  Super+P         Toggle Pulse popup"
echo "  Super+Shift+P   Open htop"
echo ""
echo "Keyboard shortcuts (i3):"
echo "  Super+O         Toggle Spaces popup"
echo "  Super+Shift+O   Rofi space selector"
echo "  Super+]         Next space"
echo "  Super+[         Previous space"
echo "  Super+Ctrl+F1-4 Quick spaces (work/code/focus/gaming)"
echo "  Super+G         Toggle Flow popup"
echo "  Super+Shift+G   Toggle recording"
echo "  Super+B         Toggle Bridge popup"
echo "  Super+Shift+B   Open Bridge terminal"
echo "  Super+P         Toggle Pulse popup"
echo "  Super+Shift+P   Open htop"
echo ""
echo "To check service status:"
echo "  systemctl --user status purma-spaces-restore"
echo "  systemctl --user status purma-spaces-save"
