#!/bin/bash

echo "Starting ActiveLog Beta Services..."

# Kill any existing services
pkill -f "python3.*main.py" 2>/dev/null

# Create pids directory if it doesn't exist
mkdir -p ~/activelog/pids

# Function to start a service if it exists
start_service() {
    local service_name=$1
    local service_path=$2
    local port=$3
    
    if [ -d "$service_path" ] && [ -f "$service_path/main.py" ]; then
        echo "Starting $service_name on port $port..."
        cd "$service_path"
        python3 main.py &
        echo $! > ~/activelog/pids/${service_name}.pid
        sleep 1
    else
        echo "Skipping $service_name (not found at $service_path)"
    fi
}

# Start existing core services
start_service "auth" "~/activelog/services/auth" "8002"
start_service "file-sync" "~/activelog/services/file-sync" "8000"
start_service "ai-orchestrator" "~/activelog/services/ai-orchestrator" "8001"
start_service "api-gateway" "~/activelog/services/api-gateway" "8088"
start_service "metadata" "~/activelog/services/metadata" "8003"

# Start any services that exist
for service_dir in ~/activelog/services/*/; do
    if [ -f "$service_dir/main.py" ]; then
        service_name=$(basename "$service_dir")
        # Check if not already started
        if [ ! -f "~/activelog/pids/${service_name}.pid" ]; then
            echo "Found additional service: $service_name"
            cd "$service_dir"
            # Try to find port in main.py
            port=$(grep -oP 'port\s*=\s*\K\d+' main.py | head -1)
            if [ ! -z "$port" ]; then
                echo "Starting $service_name on port $port"
                python3 main.py &
                echo $! > ~/activelog/pids/${service_name}.pid
                sleep 1
            fi
        fi
    fi
done

echo ""
echo "Services started. Checking status..."
sleep 3

# Count running services
running=$(ps aux | grep python3 | grep main.py | grep -v grep | wc -l)
echo "Services running: $running"

echo ""
echo "Beta services are ready!"
echo "Access points:"
echo "  API Gateway: http://localhost:8088"
echo "  Frontend: http://localhost:3000"
echo "  File Sync: http://localhost:8000/docs"
echo "  AI Orchestrator: http://localhost:8001/docs"
