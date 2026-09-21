#!/bin/bash

# Quick Analysis Portal - Service Startup Script
# This script starts the Quick Analysis Portal service

set -e

# Configuration
SERVICE_NAME="Quick Analysis Portal"
APP_FILE="app.py"
SIMPLE_APP_FILE="simple_main.py"
PORT=8420
LOG_DIR="logs"
DATA_DIR="data"
PID_FILE="quick-analysis.pid"

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

print_header() {
    echo "=================================================="
    echo "  🚀 $SERVICE_NAME Startup"
    echo "=================================================="
    echo
}

# Function to check if port is available
check_port() {
    if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 1  # Port is in use
    else
        return 0  # Port is available
    fi
}

# Function to stop existing service
stop_existing_service() {
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat $PID_FILE)
        if ps -p $pid > /dev/null 2>&1; then
            print_warning "Stopping existing service (PID: $pid)..."
            kill $pid
            sleep 2
            
            # Force kill if still running
            if ps -p $pid > /dev/null 2>&1; then
                kill -9 $pid
                sleep 1
            fi
        fi
        rm -f $PID_FILE
    fi
    
    # Kill any process using our port
    local port_pid=$(lsof -ti:$PORT 2>/dev/null || true)
    if [ -n "$port_pid" ]; then
        print_warning "Killing process using port $PORT (PID: $port_pid)..."
        kill $port_pid 2>/dev/null || true
        sleep 1
    fi
}

# Function to create directories
setup_directories() {
    print_status "Setting up directories..."
    
    # Create necessary directories
    mkdir -p $LOG_DIR
    mkdir -p $DATA_DIR
    mkdir -p static
    mkdir -p templates
    
    # Set permissions
    chmod 755 $LOG_DIR $DATA_DIR static templates
}

# Function to check dependencies
check_dependencies() {
    print_status "Checking dependencies..."
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed"
        exit 1
    fi
    
    # Check required Python packages
    local missing_packages=()
    
    if ! python3 -c "import flask" &> /dev/null; then
        missing_packages+=("flask")
    fi
    
    if ! python3 -c "import flask_cors" &> /dev/null; then
        missing_packages+=("flask-cors")
    fi
    
    if ! python3 -c "import flask_limiter" &> /dev/null; then
        missing_packages+=("flask-limiter")
    fi
    
    if [ ${#missing_packages[@]} -ne 0 ]; then
        print_warning "Installing missing Python packages..."
        pip3 install ${missing_packages[@]}
        
        if [ $? -eq 0 ]; then
            print_status "Dependencies installed successfully"
        else
            print_error "Failed to install dependencies"
            exit 1
        fi
    fi
}

# Function to initialize database
init_database() {
    print_status "Initializing database..."
    
    python3 -c "
import sqlite3
import os
from pathlib import Path

# Ensure data directory exists
Path('$DATA_DIR').mkdir(exist_ok=True)

# Create database and tables
conn = sqlite3.connect('$DATA_DIR/quick_analysis.db')
cursor = conn.cursor()

# Create users table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT UNIQUE NOT NULL,
        tier TEXT DEFAULT 'free',
        api_key TEXT UNIQUE,
        daily_searches INTEGER DEFAULT 0,
        last_search_date TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')

# Create search_history table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS search_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        symbol TEXT NOT NULL,
        search_type TEXT DEFAULT 'basic',
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (session_id) REFERENCES users (session_id)
    )
''')

# Create indexes for better performance
cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_session_id ON users (session_id)')
cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_api_key ON users (api_key)')
cursor.execute('CREATE INDEX IF NOT EXISTS idx_search_history_session_id ON search_history (session_id)')
cursor.execute('CREATE INDEX IF NOT EXISTS idx_search_history_timestamp ON search_history (timestamp)')

conn.commit()
conn.close()
print('Database initialized successfully')
"
    
    if [ $? -eq 0 ]; then
        print_status "Database initialized successfully"
    else
        print_error "Failed to initialize database"
        exit 1
    fi
}

# Function to determine which app file to use
select_app_file() {
    if [ -f "$APP_FILE" ]; then
        # Test if the main app file works
        python3 -c "import $APP_FILE" &> /dev/null
        if [ $? -eq 0 ]; then
            echo "$APP_FILE"
            return
        else
            print_warning "Main app file has issues, trying simple version..."
        fi
    fi
    
    if [ -f "$SIMPLE_APP_FILE" ]; then
        echo "$SIMPLE_APP_FILE"
        return
    fi
    
    print_error "No valid app file found"
    exit 1
}

# Function to start the service
start_service() {
    local app_file=$(select_app_file)
    print_status "Starting $SERVICE_NAME using $app_file..."
    
    # Start the service in background
    nohup python3 $app_file > $LOG_DIR/service.log 2>&1 &
    local pid=$!
    
    # Save PID
    echo $pid > $PID_FILE
    
    # Wait a moment and check if service started successfully
    sleep 3
    
    if ps -p $pid > /dev/null 2>&1; then
        print_status "$SERVICE_NAME started successfully (PID: $pid)"
        
        # Test if service is responding
        print_status "Testing service health..."
        sleep 2
        
        if curl -s http://localhost:$PORT/health > /dev/null 2>&1; then
            print_status "Service is responding to health checks"
        else
            print_warning "Service started but health check failed"
        fi
    else
        print_error "Failed to start $SERVICE_NAME"
        rm -f $PID_FILE
        echo "Check logs at $LOG_DIR/service.log for details"
        exit 1
    fi
}

# Function to display service information
show_service_info() {
    echo
    print_status "$SERVICE_NAME is now running!"
    echo
    echo "📋 Service Information:"
    echo "========================"
    echo "Status:      Running"
    echo "PID:         $(cat $PID_FILE 2>/dev/null || echo 'Unknown')"
    echo "Port:        $PORT"
    echo "URL:         http://localhost:$PORT"
    echo "Health:      http://localhost:$PORT/health"
    echo "API Docs:    http://localhost:$PORT/api/docs"
    echo "Logs:        $LOG_DIR/service.log"
    echo
    echo "🔧 Useful Commands:"
    echo "==================="
    echo "Stop Service:    ./stop_service.sh"
    echo "View Logs:       tail -f $LOG_DIR/service.log"
    echo "Health Check:    curl http://localhost:$PORT/health"
    echo "Monitor:         python3 monitoring.py --mode monitor"
    echo
    echo "🎯 Access Points:"
    echo "=================="
    echo "• Main Portal:     http://localhost:$PORT"
    echo "• Mobile Widget:   http://localhost:$PORT/mobile-widget"
    echo "• Browser Ext:     http://localhost:$PORT/extension"
    echo "• PWA Install:     Click 'Install PWA' button"
    echo "• API Access:      POST to /api/quick-analysis"
    echo
    print_status "Ready for financial analysis! 🎉"
}

# Main execution
main() {
    print_header
    
    # Stop any existing service
    stop_existing_service
    
    # Setup
    setup_directories
    check_dependencies
    init_database
    
    # Start service
    start_service
    
    # Show information
    show_service_info
}

# Handle Ctrl+C
trap 'echo -e "\n${YELLOW}Startup interrupted by user${NC}"; exit 1' INT

# Run main function
main

exit 0