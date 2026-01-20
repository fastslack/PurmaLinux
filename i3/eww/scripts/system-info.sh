#!/bin/bash
# Get system info for recommendations
result=$(curl -s http://localhost:11435/models/system-info 2>/dev/null)
if [ $? -eq 0 ]; then
    echo "$result" | jq -c '.'
else
    echo '{"ram_total_gb": 0, "recommended_pack": "minimal"}'
fi
