#!/bin/bash

echo "🛑 Stopping ActiveLog.ai System..."

# Stop services using PID files
for service in file-sync ai-orchestrator api-gateway frontend; do
    if [ -f ~/activelog/pids/$service.pid ]; then
        PID=$(cat ~/activelog/pids/$service.pid)
        if ps -p $PID > /dev/null; then
            echo "Stopping $service (PID: $PID)"
            kill $PID
        fi
        rm ~/activelog/pids/$service.pid
    fi
done

# Stop Docker services
echo "Stopping Docker services..."
cd ~/activelog
docker compose down

# Kill any remaining processes on our ports
for port in 8000 8001 8002 8003 8080 3000; do
    fuser -k $port/tcp 2>/dev/null
done

echo "✓ All services stopped"
