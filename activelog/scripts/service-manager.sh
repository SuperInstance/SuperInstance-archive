#!/bin/bash

# ActiveLog Service Manager
# Centralized service management with resource optimization

set -e

SERVICES_DIR="/home/activeloguser/activelog/services"
PID_DIR="/home/activeloguser/activelog/pids"
LOGS_DIR="/home/activeloguser/activelog/logs"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Ensure directories exist
mkdir -p "$PID_DIR" "$LOGS_DIR"

usage() {
    echo "ActiveLog Service Manager"
    echo ""
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  start [service|all]     Start services"
    echo "  stop [service|all]      Stop services"
    echo "  restart [service|all]   Restart services"
    echo "  status                  Show service status"
    echo "  list                    List available services"
    echo "  logs [service]          Show service logs"
    echo "  health                  Run health checks"
    echo "  cleanup                 Clean stale PIDs"
    echo ""
    echo "Examples:"
    echo "  $0 start auth           # Start auth service"
    echo "  $0 start all            # Start all services"
    echo "  $0 status               # Show all service status"
    echo "  $0 logs api-gateway     # Show API gateway logs"
}

# Essential services (core functionality)
ESSENTIAL_SERVICES=(
    "api-gateway"
    "auth" 
    "metadata"
    "file-sync"
    "frontend"
)

# Optional services (can be started on demand)
OPTIONAL_SERVICES=(
    "analytics"
    "business-incubator"
    "dream-mode-v2"
    "enterprise-custom"
    "gaming-platform"
    "integration-hub"
    "invoice-engine"
    "marketplace-v2"
    "revenue-distribution"
    "tycoon-games"
)

get_service_port() {
    local service="$1"
    case "$service" in
        "api-gateway") echo "8000" ;;
        "auth") echo "8001" ;;
        "metadata") echo "8002" ;;
        "file-sync") echo "8003" ;;
        "frontend") echo "3000" ;;
        *) echo "$((8000 + RANDOM % 1000))" ;;
    esac
}

start_service() {
    local service="$1"
    local service_dir="$SERVICES_DIR/$service"
    local pid_file="$PID_DIR/$service.pid"
    local log_file="$LOGS_DIR/$service.log"
    
    if [ ! -d "$service_dir" ]; then
        echo -e "${RED}❌ Service directory not found: $service_dir${NC}"
        return 1
    fi
    
    # Check if already running
    if [ -f "$pid_file" ] && [ -s "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            echo -e "${YELLOW}⚠️  $service already running (PID: $pid)${NC}"
            return 0
        fi
    fi
    
    echo -e "${BLUE}🚀 Starting $service...${NC}"
    
    # Determine service type and start accordingly
    cd "$service_dir"
    
    local port=$(get_service_port "$service")
    
    if [ -f "main.py" ]; then
        # Python service
        nohup python3 main.py > "$log_file" 2>&1 &
        local pid=$!
        echo "$pid" > "$pid_file"
        echo -e "${GREEN}✅ $service started (PID: $pid, Python)${NC}"
    elif [ -f "package.json" ]; then
        # Node.js service
        PORT="$port" nohup npm start > "$log_file" 2>&1 &
        local pid=$!
        echo "$pid" > "$pid_file"
        echo -e "${GREEN}✅ $service started (PID: $pid, Node.js, Port: $port)${NC}"
    elif [ -f "server.js" ]; then
        # Direct Node.js
        PORT="$port" nohup node server.js > "$log_file" 2>&1 &
        local pid=$!
        echo "$pid" > "$pid_file"
        echo -e "${GREEN}✅ $service started (PID: $pid, Node.js, Port: $port)${NC}"
    else
        echo -e "${RED}❌ Unknown service type for $service${NC}"
        return 1
    fi
    
    # Brief health check
    sleep 2
    if ! kill -0 "$pid" 2>/dev/null; then
        echo -e "${RED}❌ $service failed to start${NC}"
        rm -f "$pid_file"
        return 1
    fi
}

stop_service() {
    local service="$1"
    local pid_file="$PID_DIR/$service.pid"
    
    if [ ! -f "$pid_file" ] || [ ! -s "$pid_file" ]; then
        echo -e "${YELLOW}⚠️  $service not running (no PID file)${NC}"
        return 0
    fi
    
    local pid=$(cat "$pid_file")
    
    if kill -0 "$pid" 2>/dev/null; then
        echo -e "${BLUE}🛑 Stopping $service (PID: $pid)...${NC}"
        kill "$pid"
        sleep 2
        
        # Force kill if still running
        if kill -0 "$pid" 2>/dev/null; then
            echo -e "${YELLOW}💀 Force killing $service...${NC}"
            kill -9 "$pid"
        fi
        
        rm -f "$pid_file"
        echo -e "${GREEN}✅ $service stopped${NC}"
    else
        echo -e "${YELLOW}⚠️  $service PID $pid not found, cleaning up${NC}"
        rm -f "$pid_file"
    fi
}

show_status() {
    echo -e "${BLUE}📊 ActiveLog Service Status${NC}"
    echo ""
    
    local running=0
    local stopped=0
    
    # Check infrastructure
    echo -e "${BLUE}🐳 Infrastructure:${NC}"
    docker ps --format "table {{.Names}}\t{{.Status}}" | grep activelog- || echo "   No infrastructure services running"
    echo ""
    
    # Check application services
    echo -e "${BLUE}🔍 Application Services:${NC}"
    
    for service_dir in "$SERVICES_DIR"/*/; do
        if [ ! -d "$service_dir" ]; then continue; fi
        
        service=$(basename "$service_dir")
        pid_file="$PID_DIR/$service.pid"
        
        if [ -f "$pid_file" ] && [ -s "$pid_file" ]; then
            pid=$(cat "$pid_file")
            if kill -0 "$pid" 2>/dev/null; then
                echo -e "   ${GREEN}✅ $service (PID: $pid)${NC}"
                ((running++))
            else
                echo -e "   ${RED}❌ $service (stale PID)${NC}"
                ((stopped++))
            fi
        else
            echo -e "   ${YELLOW}⚪ $service (stopped)${NC}"
            ((stopped++))
        fi
    done
    
    echo ""
    echo -e "${BLUE}Summary: ${GREEN}$running running${NC}, ${RED}$stopped stopped${NC}"
}

case "${1:-}" in
    "start")
        if [ "${2:-}" = "all" ]; then
            echo -e "${BLUE}🚀 Starting essential services...${NC}"
            for service in "${ESSENTIAL_SERVICES[@]}"; do
                start_service "$service" || true
            done
        elif [ "${2:-}" = "essential" ]; then
            echo -e "${BLUE}🚀 Starting essential services only...${NC}"
            for service in "${ESSENTIAL_SERVICES[@]}"; do
                start_service "$service" || true
            done
        elif [ -n "${2:-}" ]; then
            start_service "$2"
        else
            echo "Usage: $0 start [service|all|essential]"
            exit 1
        fi
        ;;
    "stop")
        if [ "${2:-}" = "all" ]; then
            echo -e "${BLUE}🛑 Stopping all services...${NC}"
            for pid_file in "$PID_DIR"/*.pid; do
                if [ -f "$pid_file" ]; then
                    service=$(basename "$pid_file" .pid)
                    stop_service "$service" || true
                fi
            done
        elif [ -n "${2:-}" ]; then
            stop_service "$2"
        else
            echo "Usage: $0 stop [service|all]"
            exit 1
        fi
        ;;
    "restart")
        if [ -n "${2:-}" ]; then
            stop_service "$2"
            sleep 1
            start_service "$2"
        else
            echo "Usage: $0 restart [service]"
            exit 1
        fi
        ;;
    "status")
        show_status
        ;;
    "list")
        echo -e "${BLUE}📋 Available Services:${NC}"
        echo ""
        echo -e "${GREEN}Essential Services:${NC}"
        for service in "${ESSENTIAL_SERVICES[@]}"; do
            echo "   - $service"
        done
        echo ""
        echo -e "${YELLOW}Optional Services:${NC}"
        for service in "${OPTIONAL_SERVICES[@]}"; do
            echo "   - $service"
        done
        ;;
    "logs")
        if [ -n "${2:-}" ]; then
            log_file="$LOGS_DIR/$2.log"
            if [ -f "$log_file" ]; then
                tail -f "$log_file"
            else
                echo -e "${RED}❌ Log file not found: $log_file${NC}"
                exit 1
            fi
        else
            echo "Usage: $0 logs [service]"
            exit 1
        fi
        ;;
    "health")
        ./scripts/service-health-check.sh
        ;;
    "cleanup")
        ./scripts/cleanup-pids.sh
        ;;
    "help"|"-h"|"--help")
        usage
        ;;
    *)
        usage
        exit 1
        ;;
esac