#!/bin/sh
# Frontend health check script

set -e

# Check if the application is responding
if curl -f http://localhost:3000/api/health 2>/dev/null; then
    echo "Frontend health check passed"
    exit 0
else
    echo "Frontend health check failed"
    exit 1
fi