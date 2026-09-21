#!/bin/sh
# Video pipeline health check script

set -e

# Check if the main API is responding
if curl -f http://localhost:8004/health 2>/dev/null; then
    echo "Video pipeline API health check passed"
    
    # Check if metrics endpoint is available
    if curl -f http://localhost:9090/metrics 2>/dev/null >/dev/null; then
        echo "Metrics endpoint accessible"
    else
        echo "Warning: Metrics endpoint not accessible"
    fi
    
    exit 0
else
    echo "Video pipeline API health check failed"
    exit 1
fi