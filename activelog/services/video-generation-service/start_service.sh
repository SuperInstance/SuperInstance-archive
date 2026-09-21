#!/bin/bash

# Comprehensive Video Generation Service Startup Script
# Building Bots Network - Excellence in Video Construction

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Service configuration
SERVICE_NAME="Video Generation Service"
SERVICE_DIR="/home/activeloguser/activelog/services/video-generation-service"
SERVICE_PORT=${PORT:-8481}
HUB_URL=${HUB_URL:-"http://localhost:8500"}
LOG_LEVEL=${LOG_LEVEL:-"info"}

echo -e "${BLUE}🎬 Starting ${SERVICE_NAME} - Building Bots Network${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"

# Check if we're in the correct directory
if [ ! -f "main.py" ]; then
    echo -e "${RED}❌ Error: main.py not found. Please run from service directory.${NC}"
    echo -e "${YELLOW}Expected directory: ${SERVICE_DIR}${NC}"
    exit 1
fi

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if a port is available
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 1  # Port is in use
    else
        return 0  # Port is available
    fi
}

# Function to wait for service to be ready
wait_for_service() {
    local port=$1
    local max_attempts=30
    local attempt=0
    
    echo -e "${YELLOW}⏳ Waiting for service to be ready...${NC}"
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -s http://localhost:$port/ >/dev/null 2>&1; then
            echo -e "${GREEN}✅ Service is ready!${NC}"
            return 0
        fi
        
        attempt=$((attempt + 1))
        echo -n "."
        sleep 1
    done
    
    echo -e "\n${RED}❌ Service failed to start within $max_attempts seconds${NC}"
    return 1
}

# Check system requirements
echo -e "${YELLOW}🔍 Checking system requirements...${NC}"

# Check Python
if ! command_exists python3; then
    echo -e "${RED}❌ Python 3 is required but not installed${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo -e "${GREEN}✅ Python ${PYTHON_VERSION} found${NC}"

# Check pip
if ! command_exists pip3; then
    echo -e "${RED}❌ pip3 is required but not installed${NC}"
    exit 1
fi

# Check FFmpeg (required for video processing)
if ! command_exists ffmpeg; then
    echo -e "${YELLOW}⚠️  FFmpeg not found. Video processing may be limited.${NC}"
    echo -e "${YELLOW}   Install with: sudo apt-get install ffmpeg${NC}"
fi

# Check if port is available
if ! check_port $SERVICE_PORT; then
    echo -e "${RED}❌ Port $SERVICE_PORT is already in use${NC}"
    echo -e "${YELLOW}   Use 'PORT=<other_port> ./start_service.sh' to use a different port${NC}"
    exit 1
fi

# Install/update dependencies
echo -e "${YELLOW}📦 Installing dependencies...${NC}"

if [ -f "requirements.txt" ]; then
    pip3 install -r requirements.txt --upgrade --quiet
    echo -e "${GREEN}✅ Dependencies installed${NC}"
else
    echo -e "${YELLOW}⚠️  requirements.txt not found, skipping dependency installation${NC}"
fi

# Create necessary directories
echo -e "${YELLOW}📁 Creating necessary directories...${NC}"
mkdir -p /tmp/video_editing
mkdir -p logs
echo -e "${GREEN}✅ Directories created${NC}"

# Check database initialization
if [ ! -f "video_generation.db" ]; then
    echo -e "${YELLOW}🗄️  Database not found, will be created on first run${NC}"
fi

# Set environment variables
export PORT=$SERVICE_PORT
export HUB_URL=$HUB_URL
export PYTHONPATH="${PYTHONPATH}:${SERVICE_DIR}"

echo -e "${PURPLE}🔧 Configuration:${NC}"
echo -e "   Service Port: ${GREEN}$SERVICE_PORT${NC}"
echo -e "   Hub URL: ${GREEN}$HUB_URL${NC}"
echo -e "   Log Level: ${GREEN}$LOG_LEVEL${NC}"
echo -e "   Working Directory: ${GREEN}$(pwd)${NC}"

# Function to handle cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}🛑 Shutting down service...${NC}"
    if [ ! -z "$SERVICE_PID" ]; then
        kill $SERVICE_PID 2>/dev/null || true
    fi
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Start the service
echo -e "${BLUE}🚀 Starting ${SERVICE_NAME}...${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"

# Start service in background if --daemon flag is provided
if [ "$1" = "--daemon" ] || [ "$1" = "-d" ]; then
    echo -e "${YELLOW}🌙 Starting in daemon mode...${NC}"
    nohup python3 main.py > logs/service.log 2>&1 &
    SERVICE_PID=$!
    echo $SERVICE_PID > logs/service.pid
    
    # Wait for service to be ready
    if wait_for_service $SERVICE_PORT; then
        echo -e "${GREEN}✅ ${SERVICE_NAME} started successfully (PID: $SERVICE_PID)${NC}"
        echo -e "${GREEN}📊 Service URL: http://localhost:$SERVICE_PORT${NC}"
        echo -e "${GREEN}📚 API Documentation: http://localhost:$SERVICE_PORT/docs${NC}"
        echo -e "${YELLOW}📋 Logs: tail -f logs/service.log${NC}"
        echo -e "${YELLOW}🛑 Stop service: ./stop_service.sh${NC}"
    else
        echo -e "${RED}❌ Failed to start service${NC}"
        exit 1
    fi
else
    # Start service in foreground
    echo -e "${GREEN}🌟 Starting ${SERVICE_NAME} in foreground mode...${NC}"
    echo -e "${GREEN}   Press Ctrl+C to stop the service${NC}"
    echo -e "${GREEN}   Service URL: http://localhost:$SERVICE_PORT${NC}"
    echo -e "${GREEN}   API Documentation: http://localhost:$SERVICE_PORT/docs${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
    
    python3 main.py
fi