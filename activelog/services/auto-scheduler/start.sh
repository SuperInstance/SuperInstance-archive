#!/bin/bash

# Auto-Scheduler Service Startup Script

set -e

# Configuration
SERVICE_NAME="auto-scheduler"
SERVICE_PORT=8500
PID_FILE="../../pids/auto-scheduler.pid"
LOG_FILE="logs/startup.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Create necessary directories
mkdir -p logs pids data backups config

# Function to print colored output
log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

# Check if service is already running
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        error "Auto-Scheduler is already running (PID: $PID)"
        exit 1
    else
        warn "Stale PID file found, removing..."
        rm -f "$PID_FILE"
    fi
fi

# Check Python dependencies
log "Checking Python dependencies..."
if ! python3 -c "import fastapi, uvicorn, pydantic" 2>/dev/null; then
    error "Missing required Python dependencies. Please install: pip3 install -r requirements.txt"
    exit 1
fi

# Check port availability
if lsof -i :$SERVICE_PORT >/dev/null 2>&1; then
    error "Port $SERVICE_PORT is already in use"
    exit 1
fi

# Start the service
log "Starting Auto-Scheduler Service on port $SERVICE_PORT..."

# Set environment variables
export PYTHONPATH="$(pwd)/src:$PYTHONPATH"
export AUTO_SCHEDULER_CONFIG="$(pwd)/config/config.yaml"

# Start the service in background
nohup python3 main.py > "$LOG_FILE" 2>&1 &
SERVICE_PID=$!

# Save PID
echo $SERVICE_PID > "$PID_FILE"

# Wait a moment and check if service started successfully
sleep 3
if ps -p "$SERVICE_PID" > /dev/null 2>&1; then
    log "Auto-Scheduler Service started successfully (PID: $SERVICE_PID)"
    
    # Check if service is responding
    if curl -f http://localhost:$SERVICE_PORT/health > /dev/null 2>&1; then
        log "Health check passed - service is responding"
        log "Service URL: http://localhost:$SERVICE_PORT"
        log "API Documentation: http://localhost:$SERVICE_PORT/docs"
    else
        warn "Service started but not yet responding to health checks"
        log "Check logs: tail -f $LOG_FILE"
    fi
else
    error "Failed to start Auto-Scheduler Service"
    rm -f "$PID_FILE"
    exit 1
fi

log "Auto-Scheduler Service startup complete!"