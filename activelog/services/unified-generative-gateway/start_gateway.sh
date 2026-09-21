#!/bin/bash
# Building Bots Network Unified Generative Gateway Startup Script

set -e

# Configuration
GATEWAY_DIR="/home/activeloguser/activelog/services/unified-generative-gateway"
GATEWAY_PORT=8600
DASHBOARD_PORT=8601
ORCHESTRATOR_ENABLED=true

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

echo -e "${PURPLE}🏗️  Building Bots Network Unified Generative Gateway${NC}"
echo -e "${PURPLE}════════════════════════════════════════════════${NC}"
echo ""

# Function to check if port is in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

# Function to start service
start_service() {
    local name=$1
    local script=$2
    local port=$3
    local description=$4
    
    echo -e "${BLUE}🚀 Starting $name...${NC}"
    
    if check_port $port; then
        echo -e "${YELLOW}⚠️  Port $port already in use for $name${NC}"
        echo -e "${GREEN}✅ $name appears to already be running${NC}"
        return 0
    fi
    
    cd "$GATEWAY_DIR"
    
    # Start service in background
    nohup python3 "$script" > "${name}.log" 2>&1 &
    local pid=$!
    echo $pid > "${name}.pid"
    
    echo -e "${GREEN}📝 $name started with PID $pid${NC}"
    echo -e "${GREEN}📄 Logs: $GATEWAY_DIR/${name}.log${NC}"
    
    # Wait a moment for service to initialize
    sleep 3
    
    # Check if service is responding
    if check_port $port; then
        echo -e "${GREEN}✅ $name is responding on port $port${NC}"
        return 0
    else
        echo -e "${RED}❌ $name failed to start properly${NC}"
        return 1
    fi
}

# Function to check system requirements
check_requirements() {
    echo -e "${BLUE}🔍 Checking system requirements...${NC}"
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}❌ Python 3 is not installed${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ Python 3 found: $(python3 --version)${NC}"
    
    # Check required Python packages
    local required_packages=("fastapi" "uvicorn" "aiohttp" "sqlite3" "psutil")
    for package in "${required_packages[@]}"; do
        if python3 -c "import $package" 2>/dev/null; then
            echo -e "${GREEN}✅ Python package '$package' found${NC}"
        else
            echo -e "${YELLOW}⚠️  Python package '$package' not found, attempting to install...${NC}"
            pip3 install "$package" || echo -e "${RED}❌ Failed to install $package${NC}"
        fi
    done
    
    # Check available memory
    local available_memory=$(free -m | awk 'NR==2{printf "%.0f", $7}')
    if [ "$available_memory" -lt 512 ]; then
        echo -e "${YELLOW}⚠️  Low available memory: ${available_memory}MB${NC}"
    else
        echo -e "${GREEN}✅ Available memory: ${available_memory}MB${NC}"
    fi
    
    echo ""
}

# Function to create directories
setup_directories() {
    echo -e "${BLUE}📁 Setting up directories...${NC}"
    
    mkdir -p "$GATEWAY_DIR/logs"
    mkdir -p "$GATEWAY_DIR/data"
    mkdir -p "$GATEWAY_DIR/tmp"
    
    echo -e "${GREEN}✅ Directories created${NC}"
    echo ""
}

# Function to start orchestrator
start_orchestrator() {
    if [ "$ORCHESTRATOR_ENABLED" = true ]; then
        echo -e "${PURPLE}🎯 Starting Building Bots Network Orchestrator...${NC}"
        
        cd "$GATEWAY_DIR"
        nohup python3 orchestrator.py > orchestrator.log 2>&1 &
        local pid=$!
        echo $pid > orchestrator.pid
        
        echo -e "${GREEN}📝 Orchestrator started with PID $pid${NC}"
        echo -e "${GREEN}📄 Logs: $GATEWAY_DIR/orchestrator.log${NC}"
        
        sleep 5  # Give orchestrator time to start services
        echo ""
    fi
}

# Function to display status
show_status() {
    echo -e "${PURPLE}📊 Building Bots Network Status${NC}"
    echo -e "${PURPLE}═════════════════════════════${NC}"
    
    # Gateway Status
    if check_port $GATEWAY_PORT; then
        echo -e "${GREEN}✅ Unified Generative Gateway - Running on port $GATEWAY_PORT${NC}"
        if [ -f "${GATEWAY_DIR}/main.pid" ]; then
            local pid=$(cat "${GATEWAY_DIR}/main.pid")
            echo -e "   PID: $pid"
        fi
    else
        echo -e "${RED}❌ Unified Generative Gateway - Not running${NC}"
    fi
    
    # Dashboard Status
    if check_port $DASHBOARD_PORT; then
        echo -e "${GREEN}✅ Dashboard - Running on port $DASHBOARD_PORT${NC}"
        echo -e "   URL: http://localhost:$DASHBOARD_PORT"
        if [ -f "${GATEWAY_DIR}/dashboard.pid" ]; then
            local pid=$(cat "${GATEWAY_DIR}/dashboard.pid")
            echo -e "   PID: $pid"
        fi
    else
        echo -e "${RED}❌ Dashboard - Not running${NC}"
    fi
    
    # Orchestrator Status
    if [ -f "${GATEWAY_DIR}/orchestrator.pid" ]; then
        local pid=$(cat "${GATEWAY_DIR}/orchestrator.pid")
        if ps -p $pid > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Orchestrator - Running (PID: $pid)${NC}"
        else
            echo -e "${RED}❌ Orchestrator - Process not found${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  Orchestrator - Status unknown${NC}"
    fi
    
    echo ""
    echo -e "${BLUE}🔗 Access URLs:${NC}"
    echo -e "   Gateway API: http://localhost:$GATEWAY_PORT"
    echo -e "   Dashboard:   http://localhost:$DASHBOARD_PORT"
    echo -e "   Health:      http://localhost:$GATEWAY_PORT/health"
    echo -e "   Network:     http://localhost:$GATEWAY_PORT/network-status"
    echo ""
}

# Main execution
main() {
    echo -e "${BLUE}🏁 Starting Building Bots Network initialization...${NC}"
    echo ""
    
    # Check requirements
    check_requirements
    
    # Setup directories
    setup_directories
    
    # Start orchestrator (which will start other services)
    start_orchestrator
    
    # Start main gateway
    if ! start_service "Gateway" "main.py" $GATEWAY_PORT "Unified Generative Gateway"; then
        echo -e "${RED}❌ Failed to start main gateway${NC}"
        exit 1
    fi
    echo ""
    
    # Start dashboard
    if ! start_service "Dashboard" "dashboard.py" $DASHBOARD_PORT "Real-time Dashboard"; then
        echo -e "${YELLOW}⚠️  Dashboard failed to start, continuing without it${NC}"
    fi
    echo ""
    
    # Show final status
    show_status
    
    echo -e "${GREEN}🎉 Building Bots Network startup complete!${NC}"
    echo -e "${GREEN}🏗️  The network is now coordinating construction excellence${NC}"
    echo ""
    echo -e "${BLUE}💡 Next steps:${NC}"
    echo -e "   1. Visit the dashboard: http://localhost:$DASHBOARD_PORT"
    echo -e "   2. Test the API: curl http://localhost:$GATEWAY_PORT/health"
    echo -e "   3. Start a construction project via API"
    echo ""
    echo -e "${YELLOW}📝 Logs are available in:${NC}"
    echo -e "   - Gateway: $GATEWAY_DIR/Gateway.log"
    echo -e "   - Dashboard: $GATEWAY_DIR/Dashboard.log" 
    echo -e "   - Orchestrator: $GATEWAY_DIR/orchestrator.log"
    echo ""
    echo -e "${PURPLE}🛠️  Building Bots Network is ready for construction!${NC}"
}

# Handle command line arguments
case "${1:-start}" in
    "start")
        main
        ;;
    "status")
        show_status
        ;;
    "stop")
        echo -e "${YELLOW}🛑 Stopping Building Bots Network...${NC}"
        # Stop services (implementation for stop functionality)
        if [ -f "${GATEWAY_DIR}/main.pid" ]; then
            kill $(cat "${GATEWAY_DIR}/main.pid") 2>/dev/null || true
            rm -f "${GATEWAY_DIR}/main.pid"
        fi
        if [ -f "${GATEWAY_DIR}/dashboard.pid" ]; then
            kill $(cat "${GATEWAY_DIR}/dashboard.pid") 2>/dev/null || true
            rm -f "${GATEWAY_DIR}/dashboard.pid"
        fi
        if [ -f "${GATEWAY_DIR}/orchestrator.pid" ]; then
            kill $(cat "${GATEWAY_DIR}/orchestrator.pid") 2>/dev/null || true
            rm -f "${GATEWAY_DIR}/orchestrator.pid"
        fi
        echo -e "${GREEN}✅ Building Bots Network stopped${NC}"
        ;;
    "restart")
        $0 stop
        sleep 3
        $0 start
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status}"
        echo ""
        echo "Commands:"
        echo "  start   - Start the Building Bots Network"
        echo "  stop    - Stop all services"
        echo "  restart - Restart all services"
        echo "  status  - Show current status"
        exit 1
        ;;
esac