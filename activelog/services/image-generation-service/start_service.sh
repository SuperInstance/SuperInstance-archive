#!/bin/bash

# Comprehensive Image Generation Service Startup Script
# Starts the image generation service with proper environment setup

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Service configuration
SERVICE_NAME="comprehensive-image-generation"
SERVICE_PORT="${PORT:-8480}"
SERVICE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="${SERVICE_DIR}/service.log"
PID_FILE="${SERVICE_DIR}/service.pid"

echo -e "${BLUE}🎨 Starting Comprehensive Image Generation Service${NC}"
echo -e "${BLUE}=================================================${NC}"

# Function to print status messages
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if service is already running
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p $PID > /dev/null 2>&1; then
        print_warning "Service is already running with PID $PID"
        echo "To stop the service, run: kill $PID"
        exit 1
    else
        print_warning "Stale PID file found. Cleaning up..."
        rm -f "$PID_FILE"
    fi
fi

# Check Python version
print_status "Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1)
echo "  $PYTHON_VERSION"

if ! python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)"; then
    print_error "Python 3.8+ is required"
    exit 1
fi

# Check if virtual environment exists
if [ -d "${SERVICE_DIR}/venv" ]; then
    print_status "Activating virtual environment..."
    source "${SERVICE_DIR}/venv/bin/activate"
else
    print_warning "No virtual environment found. Creating one..."
    python3 -m venv "${SERVICE_DIR}/venv"
    source "${SERVICE_DIR}/venv/bin/activate"
    print_status "Virtual environment created and activated"
fi

# Install/update dependencies
print_status "Checking dependencies..."
if [ -f "${SERVICE_DIR}/requirements.txt" ]; then
    echo "Installing/updating packages from requirements.txt..."
    pip install --quiet --upgrade pip
    pip install --quiet -r "${SERVICE_DIR}/requirements.txt"
    print_status "Dependencies installed"
else
    print_warning "requirements.txt not found. Installing basic dependencies..."
    pip install --quiet fastapi uvicorn aiohttp pillow numpy
fi

# Create necessary directories
print_status "Setting up directories..."
mkdir -p "${SERVICE_DIR}/logs"
mkdir -p "${SERVICE_DIR}/data"
mkdir -p "${SERVICE_DIR}/temp"
mkdir -p "/tmp/generated_images"

# Set up environment variables
export IMG_GEN_SERVICE_PORT="$SERVICE_PORT"
export IMG_GEN_DATABASE_PATH="${SERVICE_DIR}/image_generation.db"
export IMG_GEN_LOG_LEVEL="INFO"

# Check external service connectivity
print_status "Checking external service connectivity..."

check_service() {
    local service_name=$1
    local service_url=$2
    local timeout=5
    
    if curl -s --max-time $timeout "$service_url" > /dev/null 2>&1; then
        print_status "$service_name is accessible at $service_url"
        return 0
    else
        print_warning "$service_name not accessible at $service_url"
        return 1
    fi
}

# Check OpenAI Integration Service
OPENAI_SERVICE="http://localhost:8475"
check_service "OpenAI Integration Service" "$OPENAI_SERVICE"

# Check Generative Tools Hub
HUB_SERVICE="http://localhost:8500" 
check_service "Generative Tools Hub" "$HUB_SERVICE"

# Check Local AI Service
LOCAL_AI="http://localhost:8471"
check_service "Local AI Service" "$LOCAL_AI"

# Initialize database if needed
print_status "Initializing database..."
python3 -c "
import sys
sys.path.append('$SERVICE_DIR')
from main import ComprehensiveImageGenerationService
service = ComprehensiveImageGenerationService()
print('Database initialized successfully')
" 2>/dev/null || print_warning "Database initialization had warnings"

# Start the service
print_status "Starting service on port $SERVICE_PORT..."

# Run in background and capture PID
nohup python3 "${SERVICE_DIR}/main.py" > "$LOG_FILE" 2>&1 &
SERVICE_PID=$!

# Save PID to file
echo $SERVICE_PID > "$PID_FILE"

# Wait a moment and check if service started successfully
sleep 3
if ps -p $SERVICE_PID > /dev/null 2>&1; then
    print_status "Service started successfully!"
    echo "  PID: $SERVICE_PID"
    echo "  Port: $SERVICE_PORT"
    echo "  Log file: $LOG_FILE"
    echo "  URL: http://localhost:$SERVICE_PORT"
    
    # Test service endpoint
    echo ""
    echo "Testing service endpoint..."
    sleep 2
    if curl -s "http://localhost:$SERVICE_PORT/" > /dev/null 2>&1; then
        print_status "Service is responding to requests"
        
        # Show service capabilities
        echo ""
        echo "Service Capabilities:"
        curl -s "http://localhost:$SERVICE_PORT/" | python3 -m json.tool | head -20
        
    else
        print_warning "Service started but not responding yet (may still be initializing)"
    fi
    
    echo ""
    echo -e "${BLUE}🚀 Service is now running!${NC}"
    echo ""
    echo "Useful commands:"
    echo "  View logs: tail -f $LOG_FILE"
    echo "  Stop service: kill $SERVICE_PID"
    echo "  Service status: curl http://localhost:$SERVICE_PORT/"
    echo "  Generate image: curl -X POST http://localhost:$SERVICE_PORT/generate"
    echo ""
    echo "Documentation and examples available at:"
    echo "  http://localhost:$SERVICE_PORT/docs (FastAPI auto-docs)"
    
else
    print_error "Failed to start service"
    if [ -f "$LOG_FILE" ]; then
        echo "Last few lines of log file:"
        tail -10 "$LOG_FILE"
    fi
    rm -f "$PID_FILE"
    exit 1
fi