#!/bin/bash

# Auto-Scheduler Service Stop Script

set -e

# Configuration
SERVICE_NAME="auto-scheduler"
PID_FILE="../../pids/auto-scheduler.pid"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

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

# Check if PID file exists
if [ ! -f "$PID_FILE" ]; then
    warn "PID file not found. Service may not be running."
    exit 0
fi

# Read PID
PID=$(cat "$PID_FILE")

# Check if process is running
if ! ps -p "$PID" > /dev/null 2>&1; then
    warn "Process with PID $PID is not running"
    rm -f "$PID_FILE"
    exit 0
fi

log "Stopping Auto-Scheduler Service (PID: $PID)..."

# Try graceful shutdown first (SIGTERM)
kill -TERM "$PID" 2>/dev/null || true

# Wait for graceful shutdown
WAIT_TIME=10
for i in $(seq 1 $WAIT_TIME); do
    if ! ps -p "$PID" > /dev/null 2>&1; then
        log "Service stopped gracefully"
        rm -f "$PID_FILE"
        exit 0
    fi
    sleep 1
done

# Force kill if graceful shutdown failed
warn "Graceful shutdown failed, forcing termination..."
kill -KILL "$PID" 2>/dev/null || true

# Wait a bit more
sleep 2

# Check if process is truly gone
if ps -p "$PID" > /dev/null 2>&1; then
    error "Failed to stop service with PID $PID"
    exit 1
else
    log "Service forcefully stopped"
    rm -f "$PID_FILE"
fi

log "Auto-Scheduler Service stopped successfully"