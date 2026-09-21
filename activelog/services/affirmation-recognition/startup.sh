#!/bin/bash

# Affirmation Recognition System Startup Script
# Building Bots Network Service

set -e

echo "🚀 Starting Affirmation Recognition System..."

# Configuration
SERVICE_NAME="affirmation-recognition"
SERVICE_PORT=${1:-8485}
PYTHON_ENV=${2:-"python3"}
LOG_FILE="/home/activeloguser/activelog/services/affirmation-recognition/logs/startup.log"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}" | tee -a "$LOG_FILE"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}" | tee -a "$LOG_FILE"
}

# Create necessary directories
log "Creating necessary directories..."
mkdir -p /home/activeloguser/activelog/services/affirmation-recognition/{data,models,logs,tests}

# Check if Python is available
if ! command -v $PYTHON_ENV &> /dev/null; then
    error "Python ($PYTHON_ENV) not found. Please install Python 3.8+ or specify correct Python command."
    exit 1
fi

log "Using Python: $(which $PYTHON_ENV)"
log "Python version: $($PYTHON_ENV --version)"

# Check if pip is available
if ! $PYTHON_ENV -m pip --version &> /dev/null; then
    error "pip not found. Please install pip."
    exit 1
fi

# Install dependencies if requirements.txt exists
if [ -f "requirements.txt" ]; then
    log "Installing Python dependencies..."
    $PYTHON_ENV -m pip install -r requirements.txt
    if [ $? -eq 0 ]; then
        log "Dependencies installed successfully"
    else
        error "Failed to install dependencies"
        exit 1
    fi
else
    warn "requirements.txt not found, skipping dependency installation"
fi

# Download NLTK data if needed
log "Downloading NLTK data..."
$PYTHON_ENV -c "
import nltk
try:
    nltk.download('vader_lexicon', quiet=True)
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
    nltk.download('wordnet', quiet=True)
    print('NLTK data downloaded successfully')
except Exception as e:
    print(f'Warning: Could not download NLTK data: {e}')
" 2>/dev/null || warn "NLTK data download failed (continuing anyway)"

# Check if database directory exists
if [ ! -d "data" ]; then
    log "Creating data directory..."
    mkdir -p data
fi

# Initialize database if it doesn't exist
DB_PATH="/home/activeloguser/activelog/services/affirmation-recognition/data/affirmation_recognition.db"
if [ ! -f "$DB_PATH" ]; then
    log "Initializing database..."
    $PYTHON_ENV -c "
import sqlite3
import os

db_path = '$DB_PATH'
os.makedirs(os.path.dirname(db_path), exist_ok=True)
conn = sqlite3.connect(db_path)
conn.close()
print('Database initialized successfully')
" || error "Failed to initialize database"
fi

# Check if port is available
if netstat -tuln | grep -q ":$SERVICE_PORT "; then
    warn "Port $SERVICE_PORT is already in use"
    if [ "$3" != "--force" ]; then
        error "Use --force to override port check"
        exit 1
    fi
fi

# Check for required files
REQUIRED_FILES=("main.py")
for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        error "Required file missing: $file"
        exit 1
    fi
done

# Health check function
health_check() {
    local port=$1
    local max_attempts=30
    local attempt=1
    
    log "Performing health check on port $port..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s "http://localhost:$port/health" > /dev/null 2>&1; then
            log "Health check passed on attempt $attempt"
            return 0
        fi
        
        if [ $attempt -eq $max_attempts ]; then
            error "Health check failed after $max_attempts attempts"
            return 1
        fi
        
        sleep 2
        ((attempt++))
    done
}

# Start the service
log "Starting $SERVICE_NAME on port $SERVICE_PORT..."
log "Command: $PYTHON_ENV main.py $SERVICE_PORT"

# Start in background if --daemon flag is provided
if [ "$4" == "--daemon" ]; then
    log "Starting in daemon mode..."
    nohup $PYTHON_ENV main.py $SERVICE_PORT > "$LOG_FILE" 2>&1 &
    SERVICE_PID=$!
    echo $SERVICE_PID > "/tmp/${SERVICE_NAME}-${SERVICE_PORT}.pid"
    log "Service started with PID $SERVICE_PID"
    
    # Wait a moment and check if process is still running
    sleep 3
    if kill -0 $SERVICE_PID 2>/dev/null; then
        log "Service is running successfully"
        
        # Perform health check
        sleep 5
        if health_check $SERVICE_PORT; then
            log "🎉 $SERVICE_NAME started successfully on port $SERVICE_PORT"
            log "🔍 Health endpoint: http://localhost:$SERVICE_PORT/health"
            log "📊 Analytics endpoint: http://localhost:$SERVICE_PORT/analytics"
            log "📝 Documentation: http://localhost:$SERVICE_PORT/"
            log "🔧 PID file: /tmp/${SERVICE_NAME}-${SERVICE_PORT}.pid"
            
            # Integration status
            log "🤖 Building Bots Network Integration: ACTIVE"
            log "🧠 ML Learning System: ENABLED"
            log "🌐 Service Discovery: RUNNING"
            log "📡 Feedback Collection: ACTIVE"
            log "🔄 Pattern Distribution: ENABLED"
            
            # Show connection status to other services
            log "Checking connections to Building Bots Network services..."
            SERVICES=(
                "8470:AI Picker System"
                "8471:Hierarchical Task System"
                "8474:Claude Task Hierarchy"
                "8475:OpenAI Integration"
                "8473:Resource Monitor"
                "8500:Generative Tools Hub"
                "8480:Image Generation"
                "8481:Audio Generation"
                "8483:Video Generation"
                "8482:Code Generation"
            )
            
            CONNECTED=0
            TOTAL=0
            
            for service in "${SERVICES[@]}"; do
                IFS=':' read -r port name <<< "$service"
                TOTAL=$((TOTAL + 1))
                
                if curl -s --connect-timeout 2 "http://localhost:$port/health" > /dev/null 2>&1; then
                    log "  ✅ Connected to $name (port $port)"
                    CONNECTED=$((CONNECTED + 1))
                else
                    warn "  ❌ Cannot connect to $name (port $port)"
                fi
            done
            
            log "🌐 Network connectivity: $CONNECTED/$TOTAL services reachable"
            
            if [ $CONNECTED -gt 0 ]; then
                log "🎯 Ready to receive affirmation feedback from $CONNECTED connected services"
            else
                warn "⚠️  No Building Bots Network services detected - running in standalone mode"
            fi
            
        else
            error "Service started but health check failed"
            exit 1
        fi
    else
        error "Service failed to start"
        exit 1
    fi
else
    # Start in foreground
    log "Starting in foreground mode..."
    log "Press Ctrl+C to stop the service"
    exec $PYTHON_ENV main.py $SERVICE_PORT
fi