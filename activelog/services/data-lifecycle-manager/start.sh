#!/bin/bash

# Data Lifecycle Manager Startup Script
# =====================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SERVICE_NAME="Data Lifecycle Manager"
PYTHON_CMD="python3"
MAIN_FILE="main.py"
PID_FILE="data_lifecycle_manager.pid"
LOG_FILE="startup.log"
VENV_DIR="venv"

echo -e "${BLUE}Starting ${SERVICE_NAME}...${NC}"

# Function to log messages
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Function to check if service is already running
is_running() {
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0
        else
            rm -f "$PID_FILE"
            return 1
        fi
    fi
    return 1
}

# Function to create virtual environment
create_venv() {
    if [ ! -d "$VENV_DIR" ]; then
        echo -e "${YELLOW}Creating virtual environment...${NC}"
        $PYTHON_CMD -m venv "$VENV_DIR"
        log_message "Created virtual environment"
    fi
}

# Function to activate virtual environment
activate_venv() {
    if [ -f "$VENV_DIR/bin/activate" ]; then
        source "$VENV_DIR/bin/activate"
        log_message "Activated virtual environment"
        echo -e "${GREEN}Virtual environment activated${NC}"
    else
        echo -e "${RED}Virtual environment not found, creating...${NC}"
        create_venv
        source "$VENV_DIR/bin/activate"
    fi
}

# Function to install dependencies
install_dependencies() {
    echo -e "${YELLOW}Installing dependencies...${NC}"
    
    # Upgrade pip first
    pip install --upgrade pip
    
    # Install requirements
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
        log_message "Installed Python dependencies"
    else
        echo -e "${RED}requirements.txt not found!${NC}"
        exit 1
    fi
}

# Function to check system requirements
check_requirements() {
    echo -e "${YELLOW}Checking system requirements...${NC}"
    
    # Check Python version
    if ! command -v $PYTHON_CMD &> /dev/null; then
        echo -e "${RED}Python 3 not found!${NC}"
        exit 1
    fi
    
    local python_version=$($PYTHON_CMD --version 2>&1 | cut -d' ' -f2)
    echo -e "${GREEN}Python version: $python_version${NC}"
    
    # Check available memory
    local available_memory=$(free -m | awk 'NR==2{printf "%.0f", $7}')
    if [ "$available_memory" -lt 1024 ]; then
        echo -e "${YELLOW}Warning: Low available memory (${available_memory}MB). Service may run slowly.${NC}"
    fi
    
    # Check disk space
    local available_disk=$(df -h . | awk 'NR==2{print $4}' | sed 's/[^0-9]*//g')
    if [ "$available_disk" -lt 5000 ]; then  # 5GB
        echo -e "${YELLOW}Warning: Low disk space. Data lifecycle manager needs sufficient space to operate.${NC}"
    fi
    
    log_message "System requirements check completed"
}

# Function to setup directory structure
setup_directories() {
    echo -e "${YELLOW}Setting up directory structure...${NC}"
    
    # Create necessary directories
    mkdir -p logs
    mkdir -p models
    mkdir -p backups
    mkdir -p cache
    mkdir -p data
    
    # Set permissions
    chmod 755 logs models backups cache data
    
    log_message "Directory structure setup completed"
}

# Function to initialize databases
initialize_databases() {
    echo -e "${YELLOW}Initializing databases...${NC}"
    
    # The databases will be automatically created when the service starts
    # But we can do some pre-checks here
    
    if [ ! -w "." ]; then
        echo -e "${RED}Error: Cannot write to current directory. Check permissions.${NC}"
        exit 1
    fi
    
    log_message "Database initialization prepared"
}

# Function to validate configuration
validate_config() {
    echo -e "${YELLOW}Validating configuration...${NC}"
    
    if [ ! -f "config.json" ]; then
        echo -e "${RED}Error: config.json not found!${NC}"
        exit 1
    fi
    
    # Check if config.json is valid JSON
    if ! $PYTHON_CMD -c "import json; json.load(open('config.json'))" 2>/dev/null; then
        echo -e "${RED}Error: config.json is not valid JSON!${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}Configuration validated${NC}"
    log_message "Configuration validation completed"
}

# Function to start the service
start_service() {
    echo -e "${YELLOW}Starting ${SERVICE_NAME} service...${NC}"
    
    # Set environment variables
    export PYTHONPATH="${SCRIPT_DIR}:${PYTHONPATH}"
    export PYTHONUNBUFFERED=1
    
    # Start the main service
    nohup $PYTHON_CMD "$MAIN_FILE" > "logs/service.log" 2>&1 &
    local pid=$!
    
    # Save PID
    echo "$pid" > "$PID_FILE"
    
    # Wait a moment to check if service started successfully
    sleep 3
    
    if ps -p "$pid" > /dev/null 2>&1; then
        echo -e "${GREEN}${SERVICE_NAME} started successfully (PID: $pid)${NC}"
        log_message "Service started successfully with PID: $pid"
        
        # Display service information
        echo -e "${BLUE}Service Information:${NC}"
        echo -e "  PID: $pid"
        echo -e "  Log file: logs/service.log"
        echo -e "  Web interface: http://localhost:8490"
        echo -e "  Dashboard: http://localhost:8490/dashboard"
        
        return 0
    else
        echo -e "${RED}Failed to start ${SERVICE_NAME}${NC}"
        rm -f "$PID_FILE"
        log_message "Failed to start service"
        return 1
    fi
}

# Function to show service status
show_status() {
    if is_running; then
        local pid=$(cat "$PID_FILE")
        echo -e "${GREEN}${SERVICE_NAME} is running (PID: $pid)${NC}"
        
        # Show resource usage
        if command -v ps &> /dev/null; then
            local cpu_usage=$(ps -p "$pid" -o %cpu --no-headers 2>/dev/null | tr -d ' ')
            local mem_usage=$(ps -p "$pid" -o %mem --no-headers 2>/dev/null | tr -d ' ')
            echo -e "  CPU Usage: ${cpu_usage}%"
            echo -e "  Memory Usage: ${mem_usage}%"
        fi
        
        # Show recent log entries
        echo -e "${BLUE}Recent log entries:${NC}"
        if [ -f "logs/service.log" ]; then
            tail -5 "logs/service.log"
        fi
    else
        echo -e "${RED}${SERVICE_NAME} is not running${NC}"
    fi
}

# Function to perform health check
health_check() {
    echo -e "${YELLOW}Performing health check...${NC}"
    
    if ! is_running; then
        echo -e "${RED}Service is not running${NC}"
        return 1
    fi
    
    # Try to connect to the web interface
    local health_url="http://localhost:8490/health"
    if command -v curl &> /dev/null; then
        if curl -f -s "$health_url" > /dev/null; then
            echo -e "${GREEN}Health check passed - service is responding${NC}"
            return 0
        else
            echo -e "${YELLOW}Health check warning - service may be starting up${NC}"
            return 1
        fi
    else
        echo -e "${YELLOW}curl not available, skipping HTTP health check${NC}"
        # Just check if process is running
        echo -e "${GREEN}Process health check passed${NC}"
        return 0
    fi
}

# Main execution
main() {
    case "${1:-start}" in
        start)
            if is_running; then
                echo -e "${YELLOW}${SERVICE_NAME} is already running${NC}"
                show_status
                exit 0
            fi
            
            log_message "Starting ${SERVICE_NAME}"
            check_requirements
            create_venv
            activate_venv
            install_dependencies
            setup_directories
            initialize_databases
            validate_config
            
            if start_service; then
                echo -e "${GREEN}Startup completed successfully!${NC}"
                
                # Wait for service to fully initialize
                echo -e "${YELLOW}Waiting for service to initialize...${NC}"
                sleep 5
                
                # Perform health check
                health_check
            else
                echo -e "${RED}Startup failed!${NC}"
                exit 1
            fi
            ;;
        stop)
            if is_running; then
                local pid=$(cat "$PID_FILE")
                echo -e "${YELLOW}Stopping ${SERVICE_NAME} (PID: $pid)...${NC}"
                kill "$pid"
                
                # Wait for graceful shutdown
                local count=0
                while [ $count -lt 30 ] && ps -p "$pid" > /dev/null 2>&1; do
                    sleep 1
                    count=$((count + 1))
                done
                
                if ps -p "$pid" > /dev/null 2>&1; then
                    echo -e "${YELLOW}Forcing shutdown...${NC}"
                    kill -9 "$pid"
                fi
                
                rm -f "$PID_FILE"
                echo -e "${GREEN}${SERVICE_NAME} stopped${NC}"
                log_message "Service stopped"
            else
                echo -e "${YELLOW}${SERVICE_NAME} is not running${NC}"
            fi
            ;;
        restart)
            $0 stop
            sleep 2
            $0 start
            ;;
        status)
            show_status
            ;;
        health)
            health_check
            ;;
        logs)
            if [ -f "logs/service.log" ]; then
                tail -f "logs/service.log"
            else
                echo -e "${RED}Log file not found${NC}"
                exit 1
            fi
            ;;
        clean)
            echo -e "${YELLOW}Cleaning up temporary files...${NC}"
            rm -rf cache/*
            rm -rf logs/*.log.*
            rm -f *.pyc
            find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
            echo -e "${GREEN}Cleanup completed${NC}"
            ;;
        *)
            echo "Usage: $0 {start|stop|restart|status|health|logs|clean}"
            echo ""
            echo "Commands:"
            echo "  start   - Start the Data Lifecycle Manager service"
            echo "  stop    - Stop the service"
            echo "  restart - Restart the service"
            echo "  status  - Show service status and resource usage"
            echo "  health  - Perform health check"
            echo "  logs    - Follow service logs"
            echo "  clean   - Clean up temporary files"
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"