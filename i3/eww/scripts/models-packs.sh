#!/bin/bash
# Get starter packs
result=$(curl -s http://localhost:11435/models/packs 2>/dev/null)
if [ $? -eq 0 ]; then
    echo "$result" | jq -c '.packs // {}'
else
    echo "{}"
fi
