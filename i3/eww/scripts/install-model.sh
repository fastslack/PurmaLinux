#!/bin/bash
# Install a model
MODEL_ID="$1"

if [ -z "$MODEL_ID" ]; then
    echo "Usage: install-model.sh <model_id>"
    exit 1
fi

# Update eww state to show installing
eww update installing="$MODEL_ID"

# Send notification
notify-send "PurmaLinux" "Installing $MODEL_ID..." -i dialog-information

# Install model
result=$(curl -s -X POST "http://localhost:11435/models/install/$MODEL_ID" 2>/dev/null)
success=$(echo "$result" | jq -r '.success // false')

if [ "$success" = "true" ]; then
    notify-send "PurmaLinux" "$MODEL_ID installed successfully!" -i emblem-ok-symbolic
else
    message=$(echo "$result" | jq -r '.message // "Installation failed"')
    notify-send "PurmaLinux" "$message" -i dialog-error
fi

# Reset installing state
eww update installing=""
