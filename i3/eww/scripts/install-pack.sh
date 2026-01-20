#!/bin/bash
# Install a starter pack
PACK_ID="$1"

if [ -z "$PACK_ID" ]; then
    echo "Usage: install-pack.sh <pack_id>"
    exit 1
fi

# Update eww state
eww update installing="$PACK_ID"

# Send notification
notify-send "PurmaLinux" "Installing $PACK_ID pack... This may take a while." -i dialog-information

# Install pack
result=$(curl -s -X POST "http://localhost:11435/models/pack/$PACK_ID" 2>/dev/null)
success=$(echo "$result" | jq -r '.success // false')

if [ "$success" = "true" ]; then
    notify-send "PurmaLinux" "$PACK_ID pack installed!" -i emblem-ok-symbolic
else
    notify-send "PurmaLinux" "Some models failed to install" -i dialog-warning
fi

# Reset state
eww update installing=""
