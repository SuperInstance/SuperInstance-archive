#!/bin/bash

echo "📊 ActiveLog.ai System Status"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check Docker services
echo "Docker Services:"
docker compose ps --format "table {{.Name}}\t{{.Status}}"

echo ""
echo "Application Services:"

# Check each service
services=("file-sync:8000" "ai-orchestrator:8001" "api-gateway:8080" "frontend:3000")

for service_port in "${services[@]}"; do
    IFS=':' read -r service port <<< "$service_port"
    if netstat -tuln | grep -q ":$port "; then
        echo "✓ $service (port $port) - Running"
    else
        echo "✗ $service (port $port) - Stopped"
    fi
done

echo ""
echo "API Health Check:"
curl -s http://localhost:8080/health | python3 -m json.tool
