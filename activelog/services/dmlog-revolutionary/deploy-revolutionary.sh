#!/bin/bash

# DMLog Revolutionary Deployment Script
# Deploy the D&D Beyond killer platform

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICES=("character-engine" "campaign-master" "ai-content-generator")
PORTS=(8600 8601 8602)
LOG_FILE="${SCRIPT_DIR}/logs/deployment.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Logging function
log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    mkdir -p "$(dirname "$LOG_FILE")"
    echo "[$timestamp] [$level] $message" >> "$LOG_FILE"
    
    case "$level" in
        "ERROR")   echo -e "${RED}[$level]${NC} $message" >&2 ;;
        "SUCCESS") echo -e "${GREEN}[$level]${NC} $message" ;;
        "WARN")    echo -e "${YELLOW}[$level]${NC} $message" ;;
        "INFO")    echo -e "${BLUE}[$level]${NC} $message" ;;
        *)         echo -e "${CYAN}[$level]${NC} $message" ;;
    esac
}

# Print banner
print_banner() {
    echo -e "${PURPLE}"
    cat << 'EOF'
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║               🐉 DMLog Revolutionary Deployment             ║  
║                                                              ║
║              The D&D Beyond Killer Platform                 ║
║                                                              ║
║   ⚔️  Universal Rule Systems     🤖 AI-Powered Content     ║
║   🎲 Physics-Based 3D Dice       🗺️  Holographic Maps      ║
║   🏰 Real-time Collaboration     ⛓️  Blockchain Assets      ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
}

# Check dependencies
check_dependencies() {
    log "INFO" "Checking system dependencies..."
    
    local missing_deps=()
    
    # Check Python 3.11+
    if ! command -v python3 &> /dev/null; then
        missing_deps+=("python3")
    else
        python_version=$(python3 --version | cut -d' ' -f2)
        if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 11) else 1)" 2>/dev/null; then
            log "WARN" "Python 3.11+ recommended, found: $python_version"
        fi
    fi
    
    # Check Node.js
    if ! command -v node &> /dev/null; then
        missing_deps+=("node")
    fi
    
    # Check PostgreSQL
    if ! command -v psql &> /dev/null; then
        log "WARN" "PostgreSQL client not found - database connection may fail"
    fi
    
    # Check Redis
    if ! command -v redis-cli &> /dev/null; then
        log "WARN" "Redis client not found - caching may be disabled"
    fi
    
    # Check Docker (optional)
    if command -v docker &> /dev/null; then
        log "INFO" "Docker found - container deployment available"
    fi
    
    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        log "ERROR" "Missing dependencies: ${missing_deps[*]}"
        log "INFO" "Please install missing dependencies and try again"
        exit 1
    fi
    
    log "SUCCESS" "All required dependencies found"
}

# Setup Python environment
setup_python_env() {
    log "INFO" "Setting up Python environment..."
    
    # Create virtual environment
    if [[ ! -d "${SCRIPT_DIR}/venv" ]]; then
        python3 -m venv "${SCRIPT_DIR}/venv"
        log "INFO" "Created Python virtual environment"
    fi
    
    # Activate virtual environment
    source "${SCRIPT_DIR}/venv/bin/activate"
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install requirements
    if [[ -f "${SCRIPT_DIR}/requirements.txt" ]]; then
        pip install -r "${SCRIPT_DIR}/requirements.txt"
        log "SUCCESS" "Installed Python dependencies"
    else
        log "INFO" "No requirements.txt found, installing core dependencies"
        pip install fastapi uvicorn sqlalchemy psycopg2-binary redis aioredis numpy openai python-multipart websockets
    fi
}

# Setup database
setup_database() {
    log "INFO" "Setting up database..."
    
    # Check PostgreSQL connection
    if psql -h localhost -U postgres -d postgres -c '\q' 2>/dev/null; then
        log "INFO" "PostgreSQL connection successful"
        
        # Create database if not exists
        createdb dmlog_revolutionary 2>/dev/null || log "INFO" "Database already exists"
        
        log "SUCCESS" "Database setup complete"
    else
        log "WARN" "PostgreSQL connection failed - using SQLite fallback"
        # Services will automatically use SQLite if PostgreSQL unavailable
    fi
    
    # Check Redis connection
    if redis-cli ping &>/dev/null; then
        log "SUCCESS" "Redis connection successful"
    else
        log "WARN" "Redis connection failed - real-time features may be limited"
    fi
}

# Start services
start_services() {
    log "INFO" "Starting DMLog Revolutionary services..."
    
    # Activate Python environment
    source "${SCRIPT_DIR}/venv/bin/activate" 2>/dev/null || true
    
    # Start each service
    for i in "${!SERVICES[@]}"; do
        local service="${SERVICES[$i]}"
        local port="${PORTS[$i]}"
        local service_file="${SCRIPT_DIR}/${service}.py"
        local pid_file="/tmp/dmlog-${service}.pid"
        
        if [[ -f "$service_file" ]]; then
            log "INFO" "Starting $service on port $port..."
            
            # Stop existing instance
            if [[ -f "$pid_file" ]]; then
                local old_pid=$(cat "$pid_file")
                if kill -0 "$old_pid" 2>/dev/null; then
                    kill "$old_pid"
                    sleep 2
                fi
                rm -f "$pid_file"
            fi
            
            # Start service in background
            nohup python3 "$service_file" > "${SCRIPT_DIR}/logs/${service}.log" 2>&1 &
            local service_pid=$!
            echo "$service_pid" > "$pid_file"
            
            # Wait for service to start
            sleep 3
            
            # Check if service is running
            if kill -0 "$service_pid" 2>/dev/null; then
                log "SUCCESS" "$service started successfully (PID: $service_pid)"
                
                # Check if port is responding
                if curl -s "http://localhost:$port/health" >/dev/null 2>&1; then
                    log "SUCCESS" "$service health check passed on port $port"
                else
                    log "WARN" "$service may not be responding on port $port"
                fi
            else
                log "ERROR" "$service failed to start"
            fi
        else
            log "WARN" "$service_file not found - skipping $service"
        fi
    done
}

# Setup frontend
setup_frontend() {
    log "INFO" "Setting up frontend..."
    
    local frontend_dir="${SCRIPT_DIR}/frontend"
    
    if [[ -d "$frontend_dir" ]]; then
        cd "$frontend_dir"
        
        # Install dependencies
        if [[ -f "package.json" ]]; then
            npm install
            log "SUCCESS" "Frontend dependencies installed"
            
            # Build for production
            npm run build 2>/dev/null || log "WARN" "Frontend build failed - using development mode"
            
            # Start development server
            PORT=3000 nohup npm start > "${SCRIPT_DIR}/logs/frontend.log" 2>&1 &
            echo $! > /tmp/dmlog-frontend.pid
            
            log "SUCCESS" "Frontend started on http://localhost:3000"
        else
            log "WARN" "No package.json found in frontend directory"
        fi
        
        cd "$SCRIPT_DIR"
    else
        log "WARN" "Frontend directory not found - API-only deployment"
    fi
}

# Health check all services
health_check() {
    log "INFO" "Performing health checks..."
    
    local all_healthy=true
    
    # Check backend services
    for i in "${!SERVICES[@]}"; do
        local service="${SERVICES[$i]}"
        local port="${PORTS[$i]}"
        
        if curl -s "http://localhost:$port/health" >/dev/null 2>&1; then
            log "SUCCESS" "$service is healthy on port $port"
        else
            log "ERROR" "$service health check failed on port $port"
            all_healthy=false
        fi
    done
    
    # Check frontend
    if curl -s "http://localhost:3000" >/dev/null 2>&1; then
        log "SUCCESS" "Frontend is healthy on port 3000"
    else
        log "WARN" "Frontend may not be available on port 3000"
    fi
    
    if $all_healthy; then
        log "SUCCESS" "All services are healthy!"
        return 0
    else
        log "ERROR" "Some services failed health checks"
        return 1
    fi
}

# Print service URLs
print_service_urls() {
    echo ""
    echo -e "${GREEN}🎉 DMLog Revolutionary is now running!${NC}"
    echo ""
    echo -e "${CYAN}Service URLs:${NC}"
    echo -e "  🌐 Frontend:           ${BLUE}http://localhost:3000${NC}"
    echo -e "  👤 Character Engine:   ${BLUE}http://localhost:8600/docs${NC}"
    echo -e "  🏰 Campaign Master:    ${BLUE}http://localhost:8601/docs${NC}"
    echo -e "  🤖 AI Content Gen:     ${BLUE}http://localhost:8602/docs${NC}"
    echo ""
    echo -e "${CYAN}Health Checks:${NC}"
    for i in "${!SERVICES[@]}"; do
        local service="${SERVICES[$i]}"
        local port="${PORTS[$i]}"
        echo -e "  📊 ${service}: ${BLUE}http://localhost:$port/health${NC}"
    done
    echo ""
    echo -e "${YELLOW}Logs:${NC}"
    echo -e "  📋 Deployment: ${SCRIPT_DIR}/logs/deployment.log"
    echo -e "  📋 Services:    ${SCRIPT_DIR}/logs/"
    echo ""
    echo -e "${PURPLE}🐉 Welcome to the future of tabletop gaming!${NC}"
    echo -e "${PURPLE}   D&D Beyond has been officially dethroned.${NC}"
    echo ""
}

# Stop all services
stop_services() {
    log "INFO" "Stopping all DMLog Revolutionary services..."
    
    # Stop backend services
    for service in "${SERVICES[@]}"; do
        local pid_file="/tmp/dmlog-${service}.pid"
        if [[ -f "$pid_file" ]]; then
            local pid=$(cat "$pid_file")
            if kill -0 "$pid" 2>/dev/null; then
                kill "$pid"
                log "INFO" "Stopped $service (PID: $pid)"
            fi
            rm -f "$pid_file"
        fi
    done
    
    # Stop frontend
    local frontend_pid_file="/tmp/dmlog-frontend.pid"
    if [[ -f "$frontend_pid_file" ]]; then
        local pid=$(cat "$frontend_pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid"
            log "INFO" "Stopped frontend (PID: $pid)"
        fi
        rm -f "$frontend_pid_file"
    fi
    
    log "SUCCESS" "All services stopped"
}

# Status check
status_check() {
    log "INFO" "Checking service status..."
    
    echo -e "\n${CYAN}Service Status:${NC}"
    
    # Check backend services
    for i in "${!SERVICES[@]}"; do
        local service="${SERVICES[$i]}"
        local port="${PORTS[$i]}"
        local pid_file="/tmp/dmlog-${service}.pid"
        
        if [[ -f "$pid_file" ]]; then
            local pid=$(cat "$pid_file")
            if kill -0 "$pid" 2>/dev/null; then
                if curl -s "http://localhost:$port/health" >/dev/null 2>&1; then
                    echo -e "  ✅ $service (PID: $pid, Port: $port) - ${GREEN}Healthy${NC}"
                else
                    echo -e "  ⚠️  $service (PID: $pid, Port: $port) - ${YELLOW}Running but unhealthy${NC}"
                fi
            else
                echo -e "  ❌ $service - ${RED}Stopped${NC}"
            fi
        else
            echo -e "  ❌ $service - ${RED}Not started${NC}"
        fi
    done
    
    # Check frontend
    local frontend_pid_file="/tmp/dmlog-frontend.pid"
    if [[ -f "$frontend_pid_file" ]]; then
        local pid=$(cat "$frontend_pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            if curl -s "http://localhost:3000" >/dev/null 2>&1; then
                echo -e "  ✅ Frontend (PID: $pid, Port: 3000) - ${GREEN}Healthy${NC}"
            else
                echo -e "  ⚠️  Frontend (PID: $pid, Port: 3000) - ${YELLOW}Running but unhealthy${NC}"
            fi
        else
            echo -e "  ❌ Frontend - ${RED}Stopped${NC}"
        fi
    else
        echo -e "  ❌ Frontend - ${RED}Not started${NC}"
    fi
    
    echo ""
}

# Main execution
main() {
    case "${1:-start}" in
        "start")
            print_banner
            check_dependencies
            setup_python_env
            setup_database
            start_services
            setup_frontend
            sleep 5  # Wait for all services to fully start
            if health_check; then
                print_service_urls
            else
                log "ERROR" "Deployment completed with errors - check logs for details"
                exit 1
            fi
            ;;
        "stop")
            stop_services
            ;;
        "restart")
            stop_services
            sleep 2
            main start
            ;;
        "status")
            status_check
            ;;
        "health")
            health_check
            ;;
        "logs")
            echo "Recent deployment logs:"
            tail -n 20 "$LOG_FILE" 2>/dev/null || echo "No logs found"
            ;;
        "clean")
            log "INFO" "Cleaning up deployment files..."
            stop_services
            rm -rf "${SCRIPT_DIR}/venv"
            rm -rf "${SCRIPT_DIR}/logs"
            rm -f /tmp/dmlog-*.pid
            log "SUCCESS" "Cleanup complete"
            ;;
        *)
            echo "Usage: $0 {start|stop|restart|status|health|logs|clean}"
            echo ""
            echo "Commands:"
            echo "  start    - Deploy and start all services"
            echo "  stop     - Stop all services"
            echo "  restart  - Restart all services"
            echo "  status   - Show service status"
            echo "  health   - Run health checks"
            echo "  logs     - Show recent logs"
            echo "  clean    - Clean up all deployment files"
            exit 1
            ;;
    esac
}

# Script entry point
main "$@"