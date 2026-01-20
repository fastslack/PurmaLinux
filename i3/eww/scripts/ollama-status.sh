#!/bin/bash
# Check if Ollama is running
curl -s http://localhost:11434/api/tags > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "true"
else
    echo "false"
fi
