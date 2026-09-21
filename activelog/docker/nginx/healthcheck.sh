#!/bin/sh
# Nginx health check script

set -e

# Check if nginx is responding
if curl -f http://localhost:80/health 2>/dev/null; then
    echo "Nginx health check passed"
    exit 0
else
    echo "Nginx health check failed"
    exit 1
fi