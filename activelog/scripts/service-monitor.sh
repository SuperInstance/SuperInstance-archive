#!/bin/bash
# SuperInstance.AI Service Monitor
# Real-time monitoring for all domains

echo "🔍 SuperInstance.AI Service Monitor"
echo "===================================="

# Service configuration
declare -A SERVICES=(
    ["auth"]="8001"
    ["api-gateway"]="8088"
    ["ai-insights"]="8090"
    ["personallog-backend"]="8100"
    ["fishinglog-backend"]="8200"
    ["dmlog-backend"]="8300"
    ["businesslog-backend"]="8400"
)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Check service function
check_service() {
    local name=$1
    local port=$2
    
    if curl -s -f http://localhost:$port/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ $name (port $port)${NC}"
        return 0
    else
        echo -e "${RED}❌ $name (port $port) - Not responding${NC}"
        return 1
    fi
}

# Monitor function
monitor_services() {
    local failed_count=0
    
    echo "Checking service health..."
    echo "=========================="
    
    for service in "${!SERVICES[@]}"; do
        if ! check_service "$service" "${SERVICES[$service]}"; then
            ((failed_count++))
        fi
    done
    
    echo ""
    echo "Summary:"
    echo "========="
    local total=${#SERVICES[@]}
    local healthy=$((total - failed_count))
    echo -e "${GREEN}Healthy: $healthy/$total${NC}"
    
    if [ $failed_count -gt 0 ]; then
        echo -e "${RED}Failed: $failed_count/$total${NC}"
        echo -e "${YELLOW}Run 'make start-activelog' to start missing services${NC}"
    fi
    
    return $failed_count
}

# Continuous monitoring function
watch_services() {
    local interval=${1:-30}
    
    echo "Starting continuous monitoring (interval: ${interval}s)"
    echo "Press Ctrl+C to stop"
    echo ""
    
    while true; do
        clear
        echo "$(date)"
        monitor_services
        sleep $interval
    done
}

# Auto-restart function
auto_restart() {
    echo "Auto-restart mode enabled"
    
    monitor_services
    local failed=$?
    
    if [ $failed -gt 0 ]; then
        echo "Restarting failed services..."
        make start-activelog
        sleep 10
        echo "Verifying restart..."
        monitor_services
    fi
}

# Show help
show_help() {
    echo "Usage: $0 [command] [options]"
    echo ""
    echo "Commands:"
    echo "  check          Check service health once"
    echo "  watch [N]      Continuous monitoring (default: 30s interval)"
    echo "  restart        Check and auto-restart failed services"
    echo "  help           Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 check"
    echo "  $0 watch 10"
    echo "  $0 restart"
}

# Main execution
case ${1:-check} in
    "check")
        monitor_services
        ;;
    "watch")
        watch_services $2
        ;;
    "restart")
        auto_restart
        ;;
    "help"|"-h"|"--help")
        show_help
        ;;
    *)
        echo "Unknown command: $1"
        show_help
        exit 1
        ;;
esac