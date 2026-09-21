#!/bin/bash
# Instance Orchestrator Startup Script
# Configures and starts the auto-scaling service

set -euo pipefail

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_DIR="$SCRIPT_DIR"
LOG_FILE="/var/log/instance-orchestrator.log"
PID_FILE="/var/run/instance-orchestrator.pid"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case "$level" in
        "ERROR")   echo -e "${RED}[$level]${NC} $message" >&2 ;;
        "SUCCESS") echo -e "${GREEN}[$level]${NC} $message" ;;
        "WARN")    echo -e "${YELLOW}[$level]${NC} $message" ;;
        "INFO")    echo -e "${BLUE}[$level]${NC} $message" ;;
        *)         echo -e "[$level] $message" ;;
    esac
    
    # Also log to file
    echo "[$timestamp] [$level] $message" >> "$LOG_FILE"
}

# Function to check if service is running
is_running() {
    if [[ -f "$PID_FILE" ]]; then
        local pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            return 0
        else
            rm -f "$PID_FILE"
            return 1
        fi
    fi
    return 1
}

# Function to stop the service
stop_service() {
    if is_running; then
        local pid=$(cat "$PID_FILE")
        log "INFO" "Stopping Instance Orchestrator (PID: $pid)..."
        
        kill "$pid"
        
        # Wait for graceful shutdown
        local count=0
        while kill -0 "$pid" 2>/dev/null && [[ $count -lt 30 ]]; do
            sleep 1
            count=$((count + 1))
        done
        
        if kill -0 "$pid" 2>/dev/null; then
            log "WARN" "Graceful shutdown failed, forcing termination..."
            kill -9 "$pid"
        fi
        
        rm -f "$PID_FILE"
        log "SUCCESS" "Instance Orchestrator stopped"
    else
        log "INFO" "Instance Orchestrator is not running"
    fi
}

# Function to start the service
start_service() {
    if is_running; then
        log "WARN" "Instance Orchestrator is already running"
        return 0
    fi
    
    log "INFO" "Starting Instance Orchestrator..."
    
    # Create log directory
    sudo mkdir -p "$(dirname "$LOG_FILE")"
    sudo chown "$USER:$USER" "$(dirname "$LOG_FILE")"
    
    # Check prerequisites
    log "INFO" "Checking prerequisites..."
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        log "ERROR" "Python3 is not installed"
        return 1
    fi
    
    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        log "ERROR" "AWS CLI is not installed"
        return 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        log "ERROR" "AWS credentials are not configured"
        return 1
    fi
    
    # Install Python dependencies
    log "INFO" "Installing Python dependencies..."
    cd "$SERVICE_DIR"
    pip3 install -r requirements.txt --user
    
    # Set environment variables
    export AWS_DEFAULT_REGION=${AWS_REGION:-us-west-2}
    export PYTHONPATH="$SERVICE_DIR:$PYTHONPATH"
    
    # Start the service
    log "INFO" "Launching Instance Orchestrator service..."
    cd "$SERVICE_DIR"
    
    nohup python3 main.py > "$LOG_FILE" 2>&1 &
    local pid=$!
    
    echo "$pid" > "$PID_FILE"
    
    # Wait a moment to check if it started successfully
    sleep 3
    
    if kill -0 "$pid" 2>/dev/null; then
        log "SUCCESS" "Instance Orchestrator started successfully (PID: $pid)"
        log "INFO" "Dashboard available at: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):8500"
        log "INFO" "Log file: $LOG_FILE"
        return 0
    else
        rm -f "$PID_FILE"
        log "ERROR" "Instance Orchestrator failed to start"
        return 1
    fi
}

# Function to restart the service
restart_service() {
    stop_service
    sleep 2
    start_service
}

# Function to show service status
show_status() {
    if is_running; then
        local pid=$(cat "$PID_FILE")
        log "SUCCESS" "Instance Orchestrator is running (PID: $pid)"
        
        # Show resource usage
        if command -v ps &> /dev/null; then
            local cpu_mem=$(ps -p "$pid" -o %cpu,%mem --no-headers 2>/dev/null || echo "N/A N/A")
            log "INFO" "Resource usage: CPU: $(echo $cpu_mem | awk '{print $1}')%, Memory: $(echo $cpu_mem | awk '{print $2}')%"
        fi
        
        # Check if dashboard is responding
        local public_ip=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo "unknown")
        if curl -s "http://localhost:8500/health" > /dev/null 2>&1; then
            log "SUCCESS" "Dashboard is responding: http://$public_ip:8500"
        else
            log "WARN" "Dashboard is not responding"
        fi
        
        return 0
    else
        log "INFO" "Instance Orchestrator is not running"
        return 1
    fi
}

# Function to show logs
show_logs() {
    if [[ -f "$LOG_FILE" ]]; then
        tail -f "$LOG_FILE"
    else
        log "WARN" "Log file not found: $LOG_FILE"
    fi
}

# Function to run health check
health_check() {
    log "INFO" "Running health check..."
    
    if ! is_running; then
        log "ERROR" "Service is not running"
        return 1
    fi
    
    # Check dashboard endpoint
    if curl -s "http://localhost:8500/health" > /dev/null 2>&1; then
        log "SUCCESS" "Dashboard health check passed"
    else
        log "ERROR" "Dashboard health check failed"
        return 1
    fi
    
    # Check AWS connectivity
    if aws sts get-caller-identity > /dev/null 2>&1; then
        log "SUCCESS" "AWS connectivity check passed"
    else
        log "ERROR" "AWS connectivity check failed"
        return 1
    fi
    
    log "SUCCESS" "All health checks passed"
    return 0
}

# Function to install as system service
install_service() {
    log "INFO" "Installing Instance Orchestrator as system service..."
    
    # Create systemd service file
    sudo tee /etc/systemd/system/instance-orchestrator.service > /dev/null << EOF
[Unit]
Description=ActiveLog Instance Orchestrator
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=$SERVICE_DIR
Environment=PATH=/usr/local/bin:/usr/bin:/bin:/usr/local/sbin:/usr/sbin
Environment=AWS_DEFAULT_REGION=us-west-2
ExecStart=/usr/bin/python3 $SERVICE_DIR/main.py
ExecStop=/bin/kill -TERM \$MAINPID
Restart=always
RestartSec=10
StandardOutput=file:$LOG_FILE
StandardError=file:$LOG_FILE

[Install]
WantedBy=multi-user.target
EOF
    
    # Reload systemd and enable service
    sudo systemctl daemon-reload
    sudo systemctl enable instance-orchestrator.service
    
    log "SUCCESS" "Instance Orchestrator installed as system service"
    log "INFO" "Use 'sudo systemctl start instance-orchestrator' to start the service"
    log "INFO" "Use 'sudo systemctl status instance-orchestrator' to check status"
}

# Main script logic
case "${1:-start}" in
    "start")
        start_service
        ;;
    "stop")
        stop_service
        ;;
    "restart")
        restart_service
        ;;
    "status")
        show_status
        ;;
    "logs")
        show_logs
        ;;
    "health")
        health_check
        ;;
    "install")
        install_service
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs|health|install}"
        echo ""
        echo "Commands:"
        echo "  start     - Start the Instance Orchestrator service"
        echo "  stop      - Stop the Instance Orchestrator service"
        echo "  restart   - Restart the Instance Orchestrator service"
        echo "  status    - Show service status and resource usage"
        echo "  logs      - Show real-time logs"
        echo "  health    - Run health checks"
        echo "  install   - Install as system service"
        echo ""
        echo "Examples:"
        echo "  $0 start                    # Start the service"
        echo "  $0 status                   # Check if running"
        echo "  $0 logs                     # Monitor logs"
        echo "  sudo $0 install            # Install as system service"
        exit 1
        ;;
esac