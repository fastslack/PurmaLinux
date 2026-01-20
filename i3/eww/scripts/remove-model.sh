#!/bin/bash
# Remove a model
MODEL_ID="$1"

if [ -z "$MODEL_ID" ]; then
    echo "Usage: remove-model.sh <model_id>"
    exit 1
fi

# Confirm with user
if command -v rofi &> /dev/null; then
    confirm=$(echo -e "Yes\nNo" | rofi -dmenu -p "Remove $MODEL_ID?")
    if [ "$confirm" != "Yes" ]; then
        exit 0
    fi
fi

# Remove model
result=$(curl -s -X DELETE "http://localhost:11435/models/$MODEL_ID" 2>/dev/null)
success=$(echo "$result" | jq -r '.success // false')

if [ "$success" = "true" ]; then
    notify-send "PurmaLinux" "$MODEL_ID removed" -i user-trash-symbolic
else
    notify-send "PurmaLinux" "Failed to remove $MODEL_ID" -i dialog-error
fi
