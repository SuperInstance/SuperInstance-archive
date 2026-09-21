#!/bin/bash
# SuperInstance Service Manager
# Cost-optimized development: Start/stop services on-demand

set -e

SERVICES_DIR="/home/activeloguser/activelog/services"
FRONTEND_DIR="/home/activeloguser/activelog/frontend-activelog"
LOG_FILE="/home/activeloguser/activelog/service-manager.log"
PID_FILE="/home/activeloguser/activelog/service-pids.txt"

# Service definitions with ports and descriptions
declare -A SERVICES=(
    ["auth-service"]="8001:JWT authentication service"
    ["api-gateway"]="8088:API routing and load balancing"
    ["user-management"]="8092:User profiles and preferences"
    ["ai-insights"]="8090:AI-powered insights (OpenAI + Ollama)"
    ["workout-sessions"]="8093:Exercise tracking and analysis"
    ["nutrition-tracking"]="8094:Nutrition logging with AI patterns"
    ["personallog-ai"]="8095:Productivity optimization AI"
    ["fishinglog-ai"]="8096:Fishing intelligence and predictions"
    ["dmlog-ai"]="8097:D&D campaign management AI"
    ["businesslog-ai"]="8098:Business analytics and intelligence"
    ["fitness-data-api"]="8099:Comprehensive fitness data endpoints"
    ["frontend-activelog"]="3001:Vue.js mobile-first frontend"
)

# Development profiles - common service combinations
declare -A DEV_PROFILES=(
    ["api-development"]="auth-service api-gateway user-management"
    ["ai-development"]="ai-insights user-management auth-service"
    ["frontend-development"]="frontend-activelog auth-service api-gateway user-management"
    ["full-fitness"]="auth-service api-gateway user-management ai-insights workout-sessions nutrition-tracking fitness-data-api frontend-activelog"
    ["minimal"]="auth-service api-gateway user-management"
    ["ai-research"]="ai-insights personallog-ai fishinglog-ai dmlog-ai businesslog-ai"
)

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

check_port() {
    local port=$1
    netstat -tuln 2>/dev/null | grep -q ":$port " || ss -tuln 2>/dev/null | grep -q ":$port "
}

start_service() {
    local service=$1
    local service_info=${SERVICES[$service]}
    
    if [[ -z "$service_info" ]]; then
        log "❌ Unknown service: $service"
        return 1
    fi
    
    local port=$(echo "$service_info" | cut -d: -f1)
    local description=$(echo "$service_info" | cut -d: -f2-)
    
    # Check if already running
    if check_port "$port"; then
        log "✅ $service already running on port $port"
        return 0
    fi
    
    log "🚀 Starting $service on port $port: $description"
    
    # Start service based on type
    if [[ "$service" == "frontend-activelog" ]]; then
        cd "$FRONTEND_DIR"
        npm run dev --silent > "/tmp/${service}.log" 2>&1 &
        local pid=$!
    else
        cd "$SERVICES_DIR/$service"
        if [[ -f "main.py" ]]; then
            python3 main.py > "/tmp/${service}.log" 2>&1 &
            local pid=$!
        elif [[ -f "app.py" ]]; then
            python3 app.py > "/tmp/${service}.log" 2>&1 &
            local pid=$!
        else
            log "❌ No main.py or app.py found in $SERVICES_DIR/$service"
            return 1
        fi
    fi
    
    # Store PID for later management
    echo "$service:$pid:$port" >> "$PID_FILE"
    
    # Wait a moment and check if service started successfully
    sleep 3
    if check_port "$port"; then
        log "✅ $service started successfully (PID: $pid)"
        return 0
    else
        log "❌ $service failed to start on port $port"
        # Clean up PID file
        grep -v "^$service:" "$PID_FILE" > "$PID_FILE.tmp" && mv "$PID_FILE.tmp" "$PID_FILE"
        return 1
    fi
}

stop_service() {
    local service=$1
    local service_info=${SERVICES[$service]}
    
    if [[ -z "$service_info" ]]; then
        log "❌ Unknown service: $service"
        return 1
    fi
    
    local port=$(echo "$service_info" | cut -d: -f1)
    
    # Find and kill process
    if [[ -f "$PID_FILE" ]]; then
        local pid=$(grep "^$service:" "$PID_FILE" | cut -d: -f2)
        if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
            log "🛑 Stopping $service (PID: $pid)"
            kill "$pid" 2>/dev/null || kill -9 "$pid" 2>/dev/null
            # Remove from PID file
            grep -v "^$service:" "$PID_FILE" > "$PID_FILE.tmp" && mv "$PID_FILE.tmp" "$PID_FILE"
        fi
    fi
    
    # Also try to kill by port
    local process_pid=$(lsof -ti :$port 2>/dev/null || true)
    if [[ -n "$process_pid" ]]; then
        log "🛑 Stopping process on port $port (PID: $process_pid)"
        kill "$process_pid" 2>/dev/null || kill -9 "$process_pid" 2>/dev/null
    fi
    
    # Verify stopped
    sleep 2
    if ! check_port "$port"; then
        log "✅ $service stopped successfully"
        return 0
    else
        log "⚠️  $service may still be running on port $port"
        return 1
    fi
}

status_all() {
    log "📊 SuperInstance Service Status"
    log "================================"
    
    local running=0
    local total=0
    
    for service in "${!SERVICES[@]}"; do
        local service_info=${SERVICES[$service]}
        local port=$(echo "$service_info" | cut -d: -f1)
        local description=$(echo "$service_info" | cut -d: -f2-)
        
        if check_port "$port"; then
            log "✅ $service (port $port) - RUNNING"
            ((running++))
        else
            log "❌ $service (port $port) - STOPPED"
        fi
        ((total++))
    done
    
    log "================================"
    log "📈 Status: $running/$total services running"
    
    # Show resource usage
    local cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | sed 's/%us,//')
    local mem_usage=$(free | grep Mem | awk '{printf("%.1f%%", $3/$2 * 100.0)}')
    
    log "💻 Resources: CPU ${cpu_usage:-N/A}, Memory $mem_usage"
    
    # Cost calculation
    local daily_cost=1.99
    log "💰 Daily cost: \$${daily_cost} (single t3.large instance)"
}

start_profile() {
    local profile=$1
    local services=${DEV_PROFILES[$profile]}
    
    if [[ -z "$services" ]]; then
        log "❌ Unknown development profile: $profile"
        log "Available profiles: ${!DEV_PROFILES[*]}"
        return 1
    fi
    
    log "🎯 Starting development profile: $profile"
    log "Services: $services"
    
    for service in $services; do
        start_service "$service"
    done
    
    log "🎯 Development profile '$profile' ready!"
}

stop_all() {
    log "🛑 Stopping all SuperInstance services..."
    
    for service in "${!SERVICES[@]}"; do
        stop_service "$service"
    done
    
    # Clean up PID file
    > "$PID_FILE"
    
    log "🛑 All services stopped"
}

optimize_resources() {
    log "⚡ Optimizing resources for cost-effective development..."
    
    # Stop services that haven't been accessed recently
    log "🔍 Analyzing service usage..."
    
    # This is a simple optimization - in practice, you'd track actual usage
    local active_services=()
    for service in "${!SERVICES[@]}"; do
        local port=$(echo "${SERVICES[$service]}" | cut -d: -f1)
        if check_port "$port"; then
            # Check if service has recent activity (simplified)
            local log_file="/tmp/${service}.log"
            if [[ -f "$log_file" ]] && [[ $(find "$log_file" -mmin -30 2>/dev/null) ]]; then
                active_services+=("$service")
                log "✅ $service - Recently active, keeping running"
            else
                log "💤 $service - No recent activity, considering for shutdown"
                # Optionally stop unused services
                # stop_service "$service"
            fi
        fi
    done
    
    log "⚡ Resource optimization complete"
}

show_help() {
    cat << EOF
SuperInstance Service Manager - Cost-Optimized Development

Usage: $0 <command> [options]

Commands:
  start <service>     Start a specific service
  stop <service>      Stop a specific service  
  status              Show status of all services
  profile <name>      Start a development profile
  stop-all            Stop all running services
  optimize            Optimize resource usage
  list                List available services and profiles
  
Development Profiles:
$(for profile in "${!DEV_PROFILES[@]}"; do
    echo "  $profile: ${DEV_PROFILES[$profile]}"
done)

Available Services:
$(for service in "${!SERVICES[@]}"; do
    local service_info=${SERVICES[$service]}
    local port=$(echo "$service_info" | cut -d: -f1)
    local description=$(echo "$service_info" | cut -d: -f2-)
    echo "  $service (port $port): $description"
done)

Examples:
  $0 profile api-development    # Start API development services
  $0 start ai-insights         # Start just the AI insights service
  $0 status                    # Check what's running
  $0 optimize                  # Clean up unused services
  $0 stop-all                  # Stop everything to save resources

Cost Optimization:
- Single AWS t3.large instance: \$1.99/day
- Services start/stop on-demand to save resources
- Use profiles for common development workflows
EOF
}

# Main command handling
case "${1:-help}" in
    "start")
        if [[ -z "$2" ]]; then
            log "❌ Please specify a service name"
            exit 1
        fi
        start_service "$2"
        ;;
    "stop")
        if [[ -z "$2" ]]; then
            log "❌ Please specify a service name"
            exit 1
        fi
        stop_service "$2"
        ;;
    "status")
        status_all
        ;;
    "profile")
        if [[ -z "$2" ]]; then
            log "❌ Please specify a profile name"
            log "Available profiles: ${!DEV_PROFILES[*]}"
            exit 1
        fi
        start_profile "$2"
        ;;
    "stop-all")
        stop_all
        ;;
    "optimize")
        optimize_resources
        ;;
    "list")
        echo "Available Services:"
        for service in "${!SERVICES[@]}"; do
            local service_info=${SERVICES[$service]}
            echo "  $service: $service_info"
        done
        echo ""
        echo "Development Profiles:"
        for profile in "${!DEV_PROFILES[@]}"; do
            echo "  $profile: ${DEV_PROFILES[$profile]}"
        done
        ;;
    "help"|*)
        show_help
        ;;
esac