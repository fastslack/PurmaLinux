#!/bin/bash
# Get list of available models
result=$(curl -s http://localhost:11435/models/recommended 2>/dev/null)
if [ $? -eq 0 ]; then
    echo "$result" | jq -c '.models // []'
else
    echo "[]"
fi
