#!/bin/sh
# ML Pipeline health check script

set -e

# Check if the API is responding
response=$(curl -f -s http://localhost:8000/health 2>/dev/null) || exit 1

# Check if essential services are available
if echo "$response" | grep -q '"status":"healthy"'; then
    echo "ML Pipeline API health check passed"
    
    # Additional checks for ML-specific components
    # Check if models directory is accessible
    if [ -d "/app/models" ] && [ -w "/app/models" ]; then
        echo "Models directory accessible"
    else
        echo "Warning: Models directory not accessible"
    fi
    
    # Check if registry is accessible
    if [ -d "/app/registry" ] && [ -w "/app/registry" ]; then
        echo "Registry directory accessible"
    else
        echo "Warning: Registry directory not accessible"
    fi
    
    exit 0
else
    echo "ML Pipeline health check failed: $response"
    exit 1
fi