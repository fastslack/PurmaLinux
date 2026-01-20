#!/bin/bash
# Get list of installed models
result=$(curl -s http://localhost:11435/models/list 2>/dev/null)
if [ $? -eq 0 ]; then
    echo "$result" | jq -c '.models // []'
else
    echo "[]"
fi
