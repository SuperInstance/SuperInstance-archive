#!/bin/bash

# Building Bots Network - Code Generation Service Startup Script
# This script starts the code generation service with proper configuration
# and Building Bots Network integration.

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Service configuration
SERVICE_NAME="Code Generation Service"
SERVICE_DIR="/home/activeloguser/activelog/services/code-generation-service"
PYTHON_VERSION="3.8"
DEFAULT_PORT="8000"
DEFAULT_HOST="0.0.0.0"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                Building Bots Network                           ║${NC}"
echo -e "${BLUE}║              Code Generation Service                           ║${NC}"
echo -e "${BLUE}║                                                                ║${NC}"
echo -e "${BLUE}║    Comprehensive AI-powered code generation platform          ║${NC}"
echo -e "${BLUE}║         with ML intelligence and quality assurance            ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Function to print status messages
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the correct directory
if [ ! -f "main.py" ]; then
    print_error "main.py not found. Please run this script from the service directory."
    exit 1
fi

# Check Python version
print_status "Checking Python version..."
PYTHON_CMD="python3"
if ! command -v python3 &> /dev/null; then
    if command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        print_error "Python not found. Please install Python ${PYTHON_VERSION} or higher."
        exit 1
    fi
fi

PYTHON_VER=$($PYTHON_CMD -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
print_status "Python version: ${PYTHON_VER}"

# Check required packages
print_status "Checking required packages..."
MISSING_PACKAGES=()

# Check for required Python packages
required_packages=("fastapi" "uvicorn" "anthropic" "openai" "sklearn" "numpy" "requests")
for package in "${required_packages[@]}"; do
    if ! $PYTHON_CMD -c "import ${package}" 2>/dev/null; then
        MISSING_PACKAGES+=($package)
    fi
done

if [ ${#MISSING_PACKAGES[@]} -gt 0 ]; then
    print_warning "Missing packages detected. Installing dependencies..."
    $PYTHON_CMD -m pip install -r requirements.txt
    
    # Verify installation
    for package in "${MISSING_PACKAGES[@]}"; do
        if ! $PYTHON_CMD -c "import ${package}" 2>/dev/null; then
            print_error "Failed to install ${package}. Please install manually."
            exit 1
        fi
    done
    print_status "All dependencies installed successfully."
else
    print_status "All required packages are installed."
fi

# Environment variable setup
print_status "Checking environment configuration..."

# Set default environment variables if not present
export HOST="${HOST:-$DEFAULT_HOST}"
export PORT="${PORT:-$DEFAULT_PORT}"
export LOG_LEVEL="${LOG_LEVEL:-INFO}"
export BBN_QUALITY_LEVEL="${BBN_QUALITY_LEVEL:-production}"
export BBN_HUB_ENDPOINT="${BBN_HUB_ENDPOINT:-http://localhost:8080}"

# Check API keys
if [ -z "$ANTHROPIC_API_KEY" ] && [ -z "$OPENAI_API_KEY" ]; then
    print_warning "No API keys found for external AI providers."
    print_warning "Set ANTHROPIC_API_KEY and/or OPENAI_API_KEY for full functionality."
    print_warning "Service will run with local models only."
fi

if [ -n "$ANTHROPIC_API_KEY" ]; then
    print_status "Anthropic (Claude) API key configured."
fi

if [ -n "$OPENAI_API_KEY" ]; then
    print_status "OpenAI API key configured."
fi

# Database setup
print_status "Setting up database..."
DB_PATH="${DB_PATH:-code_generation.db}"
if [ ! -f "$DB_PATH" ]; then
    print_status "Database file not found. Will be created on first run."
fi

# Create logs directory
LOGS_DIR="logs"
if [ ! -d "$LOGS_DIR" ]; then
    mkdir -p "$LOGS_DIR"
    print_status "Created logs directory: $LOGS_DIR"
fi

# Check port availability
print_status "Checking port availability..."
if command -v nc &> /dev/null; then
    if nc -z localhost $PORT 2>/dev/null; then
        print_error "Port $PORT is already in use. Please set a different PORT environment variable."
        exit 1
    fi
else
    print_warning "netcat not available. Cannot check port availability."
fi

# Building Bots Network integration check
print_status "Checking Building Bots Network integration..."
if command -v curl &> /dev/null; then
    if curl -s --connect-timeout 2 "$BBN_HUB_ENDPOINT/health" > /dev/null 2>&1; then
        print_status "Building Bots Network hub is accessible at $BBN_HUB_ENDPOINT"
    else
        print_warning "Building Bots Network hub is not accessible. Service will run in standalone mode."
    fi
else
    print_warning "curl not available. Cannot check Building Bots Network hub connectivity."
fi

# Parse command line arguments
DEVELOPMENT_MODE=false
RUN_TESTS=false
BACKGROUND_MODE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --dev|--development)
            DEVELOPMENT_MODE=true
            shift
            ;;
        --test|--tests)
            RUN_TESTS=true
            shift
            ;;
        --background|--daemon)
            BACKGROUND_MODE=true
            shift
            ;;
        --port)
            export PORT="$2"
            shift 2
            ;;
        --host)
            export HOST="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --dev, --development     Run in development mode with auto-reload"
            echo "  --test, --tests         Run tests before starting service"
            echo "  --background, --daemon   Run service in background"
            echo "  --port PORT             Set service port (default: $DEFAULT_PORT)"
            echo "  --host HOST             Set service host (default: $DEFAULT_HOST)"
            echo "  --help, -h              Show this help message"
            echo ""
            echo "Environment Variables:"
            echo "  ANTHROPIC_API_KEY       Claude API key"
            echo "  OPENAI_API_KEY          OpenAI API key"
            echo "  BBN_HUB_ENDPOINT        Building Bots Network hub endpoint"
            echo "  BBN_QUALITY_LEVEL       Quality level (development/testing/production)"
            echo "  LOG_LEVEL               Logging level (DEBUG/INFO/WARNING/ERROR)"
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Run tests if requested
if [ "$RUN_TESTS" = true ]; then
    print_status "Running tests..."
    if command -v pytest &> /dev/null; then
        $PYTHON_CMD -m pytest test_service.py -v --tb=short
        if [ $? -ne 0 ]; then
            print_error "Tests failed. Aborting service start."
            exit 1
        fi
        print_status "All tests passed!"
    else
        print_warning "pytest not found. Skipping tests. Install pytest to run tests."
    fi
fi

# Set development mode configuration
if [ "$DEVELOPMENT_MODE" = true ]; then
    print_status "Starting in development mode..."
    export LOG_LEVEL="DEBUG"
    export BBN_QUALITY_LEVEL="development"
    RELOAD_FLAG="--reload"
else
    RELOAD_FLAG=""
fi

# Display startup information
print_status "=== Service Configuration ==="
print_status "Host: $HOST"
print_status "Port: $PORT"
print_status "Log Level: $LOG_LEVEL"
print_status "Quality Level: $BBN_QUALITY_LEVEL"
print_status "Database: $DB_PATH"
print_status "Building Bots Network Hub: $BBN_HUB_ENDPOINT"
print_status "Development Mode: $DEVELOPMENT_MODE"
echo ""

print_status "Starting Building Bots Network Code Generation Service..."

# Create startup command
STARTUP_CMD="$PYTHON_CMD -m uvicorn main:app --host $HOST --port $PORT --log-level $(echo $LOG_LEVEL | tr '[:upper:]' '[:lower:]') $RELOAD_FLAG"

# Add process management for background mode
if [ "$BACKGROUND_MODE" = true ]; then
    PID_FILE="$SERVICE_DIR/service.pid"
    LOG_FILE="$LOGS_DIR/service.log"
    
    print_status "Starting service in background mode..."
    print_status "Logs: $LOG_FILE"
    print_status "PID file: $PID_FILE"
    
    # Check if service is already running
    if [ -f "$PID_FILE" ]; then
        OLD_PID=$(cat "$PID_FILE")
        if kill -0 "$OLD_PID" 2>/dev/null; then
            print_error "Service is already running with PID $OLD_PID"
            exit 1
        else
            print_warning "Removing stale PID file"
            rm -f "$PID_FILE"
        fi
    fi
    
    # Start in background
    nohup $STARTUP_CMD > "$LOG_FILE" 2>&1 &
    SERVICE_PID=$!
    echo $SERVICE_PID > "$PID_FILE"
    
    # Wait a moment and check if service started successfully
    sleep 3
    if kill -0 "$SERVICE_PID" 2>/dev/null; then
        print_status "Service started successfully with PID $SERVICE_PID"
        print_status "Service URL: http://$HOST:$PORT"
        print_status "Health check: http://$HOST:$PORT/health"
        print_status "API documentation: http://$HOST:$PORT/docs"
        echo ""
        print_status "Use 'kill $SERVICE_PID' to stop the service"
        print_status "Or run: kill \$(cat $PID_FILE)"
    else
        print_error "Service failed to start. Check logs: $LOG_FILE"
        rm -f "$PID_FILE"
        exit 1
    fi
else
    # Run in foreground
    print_status "Service URL: http://$HOST:$PORT"
    print_status "Health check: http://$HOST:$PORT/health"
    print_status "API documentation: http://$HOST:$PORT/docs"
    echo ""
    print_status "Press Ctrl+C to stop the service"
    echo ""
    
    # Trap Ctrl+C for graceful shutdown
    trap 'print_status "Shutting down service..."; exit 0' INT TERM
    
    # Start the service
    exec $STARTUP_CMD
fi