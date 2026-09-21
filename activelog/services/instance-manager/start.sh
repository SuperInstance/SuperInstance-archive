#!/bin/bash

# ActiveLog Instance Manager Startup Script

# Set script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Set environment
export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"
export ENVIRONMENT="${ENVIRONMENT:-development}"

# Logging
LOG_DIR="/home/activeloguser/activelog/logs"
LOG_FILE="$LOG_DIR/instance-manager.log"
PID_FILE="/home/activeloguser/activelog/pids/instance-manager.pid"

# Ensure directories exist
mkdir -p "$LOG_DIR"
mkdir -p "/home/activeloguser/activelog/pids"
mkdir -p "/home/activeloguser/activelog/data/instance-manager"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[Instance Manager]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[Instance Manager]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[Instance Manager]${NC} $1"
}

print_error() {
    echo -e "${RED}[Instance Manager]${NC} $1"
}

# Function to check if service is running
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

# Function to start the service
start_service() {
    if is_running; then
        print_warning "Instance Manager is already running (PID: $(cat $PID_FILE))"
        return 1
    fi

    print_status "Starting Instance Manager service..."

    # Check Python dependencies
    if ! python3 -c "import boto3, flask" 2>/dev/null; then
        print_error "Missing required Python dependencies"
        print_status "Installing dependencies..."
        pip3 install -r requirements.txt || {
            print_error "Failed to install dependencies"
            return 1
        }
    fi

    # Check AWS credentials
    if [ -z "$AWS_ACCESS_KEY_ID" ] || [ -z "$AWS_SECRET_ACCESS_KEY" ]; then
        print_warning "AWS credentials not found in environment"
        print_status "Attempting to use IAM role or default profile..."
    fi

    # Start the service
    nohup python3 main.py > "$LOG_FILE" 2>&1 &
    local pid=$!
    echo "$pid" > "$PID_FILE"

    # Give it a moment to start
    sleep 3

    # Check if it's running
    if is_running; then
        print_success "Instance Manager started successfully (PID: $pid)"
        print_status "Service available at: http://localhost:8330"
        print_status "Health check: http://localhost:8330/health"
        print_status "Log file: $LOG_FILE"
        return 0
    else
        print_error "Failed to start Instance Manager"
        print_status "Check log file for details: $LOG_FILE"
        return 1
    fi
}

# Function to stop the service
stop_service() {
    if ! is_running; then
        print_warning "Instance Manager is not running"
        return 1
    fi

    local pid=$(cat "$PID_FILE")
    print_status "Stopping Instance Manager (PID: $pid)..."

    # Send SIGTERM
    kill "$pid" 2>/dev/null || {
        print_error "Failed to stop service"
        return 1
    }

    # Wait for graceful shutdown
    local count=0
    while ps -p "$pid" > /dev/null 2>&1 && [ $count -lt 30 ]; do
        sleep 1
        ((count++))
    done

    # Force kill if still running
    if ps -p "$pid" > /dev/null 2>&1; then
        print_warning "Forcing shutdown..."
        kill -9 "$pid" 2>/dev/null
        sleep 2
    fi

    rm -f "$PID_FILE"
    print_success "Instance Manager stopped"
    return 0
}

# Function to restart the service
restart_service() {
    print_status "Restarting Instance Manager..."
    stop_service
    sleep 2
    start_service
}

# Function to show service status
status_service() {
    if is_running; then
        local pid=$(cat "$PID_FILE")
        print_success "Instance Manager is running (PID: $pid)"
        
        # Check if port is listening
        if netstat -tuln 2>/dev/null | grep -q ":8330 "; then
            print_success "Service is listening on port 8330"
        else
            print_warning "Service is running but not listening on port 8330"
        fi
        
        # Show memory usage
        local memory_usage=$(ps -p "$pid" -o pid,ppid,pcpu,pmem,rss,vsz,time,comm --no-headers 2>/dev/null)
        if [ -n "$memory_usage" ]; then
            print_status "Process info: $memory_usage"
        fi
        
        return 0
    else
        print_error "Instance Manager is not running"
        return 1
    fi
}

# Function to show logs
show_logs() {
    local lines=${1:-50}
    if [ -f "$LOG_FILE" ]; then
        print_status "Showing last $lines lines from log file:"
        echo "----------------------------------------"
        tail -n "$lines" "$LOG_FILE"
    else
        print_error "Log file not found: $LOG_FILE"
    fi
}

# Function to follow logs
follow_logs() {
    if [ -f "$LOG_FILE" ]; then
        print_status "Following log file (Ctrl+C to exit):"
        echo "----------------------------------------"
        tail -f "$LOG_FILE"
    else
        print_error "Log file not found: $LOG_FILE"
    fi
}

# Function to check health
health_check() {
    print_status "Performing health check..."
    
    if ! is_running; then
        print_error "Service is not running"
        return 1
    fi
    
    # HTTP health check
    local response=$(curl -s -w "%{http_code}" -o /tmp/health_response http://localhost:8330/health 2>/dev/null)
    
    if [ "$response" = "200" ]; then
        print_success "Health check passed"
        cat /tmp/health_response 2>/dev/null | python3 -m json.tool 2>/dev/null || cat /tmp/health_response
        rm -f /tmp/health_response
        return 0
    else
        print_error "Health check failed (HTTP $response)"
        return 1
    fi
}

# Function to run diagnostics
run_diagnostics() {
    print_status "Running diagnostics..."
    echo "========================================"
    
    # System info
    print_status "System Information:"
    echo "OS: $(uname -s) $(uname -r)"
    echo "Python: $(python3 --version 2>&1)"
    echo "PID File: $PID_FILE"
    echo "Log File: $LOG_FILE"
    echo "Working Directory: $PWD"
    echo ""
    
    # Service status
    print_status "Service Status:"
    status_service
    echo ""
    
    # Port check
    print_status "Network Status:"
    if netstat -tuln 2>/dev/null | grep -q ":8330 "; then
        print_success "Port 8330 is listening"
    else
        print_warning "Port 8330 is not listening"
    fi
    echo ""
    
    # AWS credentials
    print_status "AWS Configuration:"
    if [ -n "$AWS_ACCESS_KEY_ID" ]; then
        print_success "AWS_ACCESS_KEY_ID is set"
    else
        print_warning "AWS_ACCESS_KEY_ID is not set"
    fi
    
    if aws sts get-caller-identity >/dev/null 2>&1; then
        print_success "AWS credentials are valid"
        aws sts get-caller-identity 2>/dev/null | head -3
    else
        print_warning "AWS credentials test failed"
    fi
    echo ""
    
    # Dependencies check
    print_status "Dependencies Check:"
    python3 -c "
import sys
modules = ['boto3', 'flask', 'pytz', 'croniter', 'numpy']
for module in modules:
    try:
        __import__(module)
        print(f'✓ {module}')
    except ImportError:
        print(f'✗ {module} (missing)')
" 2>/dev/null
    
    echo ""
    print_status "Recent log entries:"
    show_logs 10
}

# Function to install dependencies
install_deps() {
    print_status "Installing Python dependencies..."
    pip3 install -r requirements.txt || {
        print_error "Failed to install dependencies"
        return 1
    }
    print_success "Dependencies installed successfully"
}

# Function to show help
show_help() {
    echo "ActiveLog Instance Manager Control Script"
    echo "Usage: $0 {start|stop|restart|status|logs|follow-logs|health|diagnostics|install-deps|help}"
    echo ""
    echo "Commands:"
    echo "  start        Start the Instance Manager service"
    echo "  stop         Stop the Instance Manager service"
    echo "  restart      Restart the Instance Manager service"
    echo "  status       Show service status"
    echo "  logs [N]     Show last N lines from log file (default: 50)"
    echo "  follow-logs  Follow log file in real-time"
    echo "  health       Perform health check"
    echo "  diagnostics  Run comprehensive diagnostics"
    echo "  install-deps Install Python dependencies"
    echo "  help         Show this help message"
    echo ""
    echo "Environment Variables:"
    echo "  ENVIRONMENT              Set environment (development|staging|production)"
    echo "  AWS_ACCESS_KEY_ID        AWS access key"
    echo "  AWS_SECRET_ACCESS_KEY    AWS secret key"
    echo "  AWS_DEFAULT_REGION       AWS region (default: us-west-2)"
    echo "  INSTANCE_MANAGER_PORT    Service port (default: 8330)"
    echo ""
}

# Main script logic
case "${1:-}" in
    start)
        start_service
        ;;
    stop)
        stop_service
        ;;
    restart)
        restart_service
        ;;
    status)
        status_service
        ;;
    logs)
        show_logs "${2:-50}"
        ;;
    follow-logs)
        follow_logs
        ;;
    health)
        health_check
        ;;
    diagnostics)
        run_diagnostics
        ;;
    install-deps)
        install_deps
        ;;
    help|--help|-h)
        show_help
        ;;
    "")
        print_error "No command specified"
        show_help
        exit 1
        ;;
    *)
        print_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac

exit $?