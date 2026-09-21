#!/bin/bash

# Quick Analysis Portal - Service Stop Script
# This script stops the Quick Analysis Portal service

PID_FILE="quick-analysis.pid"
SERVICE_NAME="Quick Analysis Portal"
PORT=8420

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

echo "🛑 Stopping $SERVICE_NAME..."

# Stop service using PID file
if [ -f "$PID_FILE" ]; then
    PID=$(cat $PID_FILE)
    
    if ps -p $PID > /dev/null 2>&1; then
        print_status "Stopping service (PID: $PID)..."
        kill $PID
        
        # Wait for graceful shutdown
        sleep 3
        
        # Check if still running
        if ps -p $PID > /dev/null 2>&1; then
            print_warning "Service still running, forcing shutdown..."
            kill -9 $PID
            sleep 1
        fi
        
        if ! ps -p $PID > /dev/null 2>&1; then
            print_status "Service stopped successfully"
        else
            print_error "Failed to stop service"
        fi
    else
        print_warning "Process not found (PID: $PID)"
    fi
    
    rm -f $PID_FILE
else
    print_warning "PID file not found"
fi

# Kill any remaining processes on our port
PORT_PID=$(lsof -ti:$PORT 2>/dev/null || true)
if [ -n "$PORT_PID" ]; then
    print_warning "Killing process using port $PORT (PID: $PORT_PID)..."
    kill $PORT_PID 2>/dev/null || true
    sleep 1
    
    # Check if port is now free
    if ! lsof -i:$PORT > /dev/null 2>&1; then
        print_status "Port $PORT is now available"
    else
        print_warning "Port $PORT may still be in use"
    fi
fi

# Kill any Python processes that might be running our app
pkill -f "python.*app.py" 2>/dev/null || true
pkill -f "python.*main.py" 2>/dev/null || true
pkill -f "python.*simple_main.py" 2>/dev/null || true

print_status "$SERVICE_NAME stopped"