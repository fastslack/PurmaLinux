#!/bin/bash
# Get number of installed models
result=$(curl -s http://localhost:11435/models/status 2>/dev/null)
if [ $? -eq 0 ]; then
    echo "$result" | jq -r '.installed_count // 0'
else
    echo "0"
fi
