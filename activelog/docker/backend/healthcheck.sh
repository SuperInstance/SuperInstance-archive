#!/bin/sh
# Backend health check script

set -e

# Check if the application is responding
response=$(curl -f -s http://localhost:8080/api/health 2>/dev/null) || exit 1

# Parse JSON response to check status
if echo "$response" | grep -q '"status":"healthy"'; then
    echo "Backend health check passed"
    exit 0
else
    echo "Backend health check failed: $response"
    exit 1
fi