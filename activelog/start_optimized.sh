#!/bin/bash
# Device-Optimized ActiveLog Startup Script
# Generated for: desktop (medium performance)

echo "🚀 Starting ActiveLog for desktop device..."
echo "Device specs: 12 cores, 15.2GB RAM"

# Set environment variables based on device
export ACTIVELOG_DEVICE_TYPE="desktop"
export ACTIVELOG_PERFORMANCE_TIER="medium"
export ACTIVELOG_MAX_MEMORY="9326"

# Platform-specific optimizations

# Linux optimizations
export OMP_NUM_THREADS=$(($(nproc) / 2))
ulimit -n 4096  # Increase file descriptor limit

# Start core services in parallel (high/medium performance devices)
start_services_parallel() {
    echo "Starting core services in parallel..."
    
    cd services/auth && python3 main.py &
    AUTH_PID=$!
    
    cd ../../services/api-gateway && python3 main.py &
    GATEWAY_PID=$!
    
    cd ../../services/file-sync && python3 main.py &
    FILESYNC_PID=$!
    
    # Wait for core services
    wait $AUTH_PID $GATEWAY_PID $FILESYNC_PID
    
    # Start secondary services
    cd ../../services/ai-orchestrator && python3 main.py &
    cd ../../services/metadata && python3 main.py &
}

# Health check function
check_service_health() {
    local service_name=$1
    local port=$2
    local max_attempts=10
    
    for i in $(seq 1 $max_attempts); do
        if curl -s http://localhost:$port/health >/dev/null 2>&1; then
            echo "✅ $service_name is healthy"
            return 0
        fi
        sleep 1
    done
    
    echo "❌ $service_name failed to start properly"
    return 1
}

# Main startup logic
main() {
    # Create necessary directories
    mkdir -p pids logs cache
    
    # Apply device-specific system optimizations
    if [ "medium" = "high" ]; then
        start_services_parallel
    else
        start_services_sequential  
    fi
    
    # Health checks
    sleep 5
    check_service_health "Auth" 8002
    check_service_health "API Gateway" 8088
    check_service_health "File Sync" 8000
    
    echo ""
    echo "🎉 ActiveLog started successfully on desktop device!"
    echo "Performance tier: medium"
    echo "Main interface: http://localhost:8088"
    echo "Memory usage optimized for 15.2GB RAM"
}

# Run main function
main "$@"
