#!/bin/bash

# Video Generation Service Stop Script
# Building Bots Network - Excellence in Video Construction

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SERVICE_NAME="Video Generation Service"
PID_FILE="logs/service.pid"
SERVICE_PORT=${PORT:-8481}

echo -e "${BLUE}🛑 Stopping ${SERVICE_NAME}${NC}"
echo -e "${BLUE}═══════════════════════════════════${NC}"

# Function to check if service is running
is_service_running() {
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            return 0  # Service is running
        fi
    fi
    return 1  # Service is not running
}

# Function to stop service by PID
stop_by_pid() {
    local pid=$(cat "$PID_FILE")
    echo -e "${YELLOW}🔄 Stopping service (PID: $pid)...${NC}"
    
    # Try graceful shutdown first
    if kill -TERM "$pid" 2>/dev/null; then
        echo -e "${YELLOW}⏳ Waiting for graceful shutdown...${NC}"
        
        # Wait up to 10 seconds for graceful shutdown
        local count=0
        while [ $count -lt 10 ]; do
            if ! kill -0 "$pid" 2>/dev/null; then
                echo -e "${GREEN}✅ Service stopped gracefully${NC}"
                rm -f "$PID_FILE"
                return 0
            fi
            sleep 1
            count=$((count + 1))
            echo -n "."
        done
        
        # Force kill if graceful shutdown failed
        echo -e "\n${YELLOW}⚠️  Graceful shutdown timeout, forcing stop...${NC}"
        if kill -KILL "$pid" 2>/dev/null; then
            echo -e "${GREEN}✅ Service force stopped${NC}"
        else
            echo -e "${RED}❌ Failed to stop service${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  Process not found, cleaning up PID file${NC}"
    fi
    
    rm -f "$PID_FILE"
}

# Function to stop service by port
stop_by_port() {
    echo -e "${YELLOW}🔍 Looking for service on port $SERVICE_PORT...${NC}"
    
    local pid=$(lsof -ti:$SERVICE_PORT 2>/dev/null || true)
    if [ ! -z "$pid" ]; then
        echo -e "${YELLOW}🔄 Found service on port $SERVICE_PORT (PID: $pid)${NC}"
        if kill -TERM "$pid" 2>/dev/null; then
            echo -e "${GREEN}✅ Service stopped${NC}"
            return 0
        else
            echo -e "${RED}❌ Failed to stop service${NC}"
            return 1
        fi
    else
        echo -e "${YELLOW}ℹ️  No service found on port $SERVICE_PORT${NC}"
        return 1
    fi
}

# Main stop logic
if is_service_running; then
    stop_by_pid
elif stop_by_port; then
    echo -e "${GREEN}✅ Service stopped by port${NC}"
else
    echo -e "${YELLOW}ℹ️  Service is not running${NC}"
    
    # Clean up any stale PID file
    if [ -f "$PID_FILE" ]; then
        rm -f "$PID_FILE"
        echo -e "${YELLOW}🧹 Cleaned up stale PID file${NC}"
    fi
fi

# Additional cleanup
echo -e "${YELLOW}🧹 Performing cleanup...${NC}"

# Kill any remaining python processes for this service
pkill -f "video-generation-service" 2>/dev/null || true
pkill -f "main.py.*8481" 2>/dev/null || true

# Clean up temporary files
rm -rf /tmp/video_editing/* 2>/dev/null || true
rm -rf /tmp/*video* 2>/dev/null || true
rm -rf /tmp/*merge* 2>/dev/null || true
rm -rf /tmp/*compress* 2>/dev/null || true
rm -rf /tmp/*convert* 2>/dev/null || true
rm -rf /tmp/*analyze* 2>/dev/null || true

echo -e "${GREEN}✅ Cleanup completed${NC}"
echo -e "${GREEN}🏁 ${SERVICE_NAME} stopped successfully${NC}"

# Show final status
if lsof -Pi :$SERVICE_PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${RED}⚠️  Warning: Something is still running on port $SERVICE_PORT${NC}"
else
    echo -e "${GREEN}✅ Port $SERVICE_PORT is now available${NC}"
fi