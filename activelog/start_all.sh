#!/bin/bash

echo "Starting complete ActiveLog system..."

# Function to check if service is running
check_service() {
    local pid_file=$1
    local service_name=$2
    if [ -f "$pid_file" ] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
        echo "$service_name already running (PID: $(cat "$pid_file"))"
        return 0
    else
        return 1
    fi
}

# Function to start service with health check
start_service_with_health_check() {
    local service_dir=$1
    local service_name=$2
    local pid_file=$3
    local port=$4
    local max_attempts=${5:-30}
    
    if ! check_service "$pid_file" "$service_name"; then
        echo "Starting $service_name..."
        cd "$service_dir" || exit 1
        python3 main.py &
        echo $! > "$pid_file"
        
        # Wait for service to be ready
        local attempt=0
        while [ $attempt -lt $max_attempts ]; do
            if curl -s "http://localhost:$port/health" >/dev/null 2>&1; then
                echo "$service_name started successfully on port $port"
                break
            fi
            sleep 1
            attempt=$((attempt + 1))
        done
        
        if [ $attempt -eq $max_attempts ]; then
            echo "Warning: $service_name may not have started properly"
        fi
    fi
}

# Create pids directory if it doesn't exist
mkdir -p ~/activelog/pids

# Start core services first (parallel startup)
echo "Starting core services..."
start_service_with_health_check "~/activelog/services/file-sync" "File-Sync" "~/activelog/pids/file-sync.pid" "8000" &
start_service_with_health_check "~/activelog/services/ai-orchestrator" "AI-Orchestrator" "~/activelog/pids/ai-orchestrator.pid" "8001" &
start_service_with_health_check "~/activelog/services/auth" "Auth" "~/activelog/pids/auth.pid" "8002" &
start_service_with_health_check "~/activelog/services/api-gateway" "API-Gateway" "~/activelog/pids/api-gateway.pid" "8088" &

# Wait for core services
wait

# Start secondary services
echo "Starting secondary services..."
start_service_with_health_check "~/activelog/services/auto-scheduler" "Auto-Scheduler" "~/activelog/pids/auto-scheduler.pid" "8500"

# Start frontend (optimized)
if ! check_service "~/activelog/pids/frontend.pid" "Frontend"; then
    echo "Starting Frontend..."
    cd ~/activelog/frontend || exit 1
    NODE_OPTIONS="--max-old-space-size=2048" npm start &
    echo $! > ~/activelog/pids/frontend.pid
    echo "Frontend started on port 3000"
fi

# Show status
echo ""
echo "=== SYSTEM READY ==="
running_services=$(ps aux | grep python3 | grep main.py | grep -v grep | wc -l)
echo "Services running: $running_services"

# Health check summary
echo ""
echo "Health Check Summary:"
for service in file-sync:8000 ai-orchestrator:8001 auth:8002 api-gateway:8088 frontend:3000; do
    name=$(echo $service | cut -d: -f1)
    port=$(echo $service | cut -d: -f2)
    if curl -s "http://localhost:$port/health" >/dev/null 2>&1 || curl -s "http://localhost:$port/" >/dev/null 2>&1; then
        echo "✓ $name (port $port) - Healthy"
    else
        echo "✗ $name (port $port) - Not responding"
    fi
done

echo ""
echo "System is ready for beta testing!"
echo "Main interface: http://localhost:3000"
echo "API Gateway: http://localhost:8088"
