#!/bin/bash

echo "=== ActiveLog Service Status Dashboard ==="
echo "Time: $(date)"
echo ""

# Function to check service
check_service() {
    local name=$1
    local port=$2
    local endpoint=${3:-"/health"}
    
    if curl -s -f -o /dev/null "http://localhost:${port}${endpoint}"; then
        echo "✅ $name (port $port): Running"
        # Check for docs
        if curl -s -f -o /dev/null "http://localhost:${port}/docs"; then
            echo "   📚 Docs: http://localhost:${port}/docs"
        fi
    else
        echo "❌ $name (port $port): Not responding"
    fi
}

echo "Core Services:"
check_service "File Sync" 8000
check_service "AI Orchestrator" 8001
check_service "Auth Service" 8002
check_service "Metadata" 8003
check_service "API Gateway" 8088

echo ""
echo "Web Interfaces:"
check_service "Frontend" 3000 "/"
check_service "MinIO Console" 9001 "/"

echo ""
echo "Docker Services:"
docker ps --format "table {{.Names}}\t{{.Status}}" | grep activelog | head -5
