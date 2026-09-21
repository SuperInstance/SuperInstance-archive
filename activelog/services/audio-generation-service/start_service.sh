#!/bin/bash
# Comprehensive Audio Generation Service - Building Bots Network
# Startup script with dependency checks and service initialization

set -e

# Service configuration
SERVICE_NAME="Comprehensive Audio Generation Service"
SERVICE_PORT=8485
SERVICE_DIR="/home/activeloguser/activelog/services/audio-generation-service"
LOG_FILE="$SERVICE_DIR/audio_service.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Building Bots Network banner
print_banner() {
    echo -e "${PURPLE}"
    echo "████████████████████████████████████████████████████████████"
    echo "█                                                          █"
    echo "█    🏗️  BUILDING BOTS NETWORK - AUDIO GENERATION SERVICE  █"
    echo "█                                                          █"
    echo "█    Mission: Excellence in Audio Construction             █"
    echo "█    Network: Interconnected Intelligent Systems          █"
    echo "█                                                          █"
    echo "████████████████████████████████████████████████████████████"
    echo -e "${NC}"
    echo ""
}

# Progress indicator
show_progress() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

show_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

show_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

show_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check Python dependencies
check_python_deps() {
    show_progress "Checking Python dependencies..."
    
    local required_packages=(
        "fastapi" "uvicorn" "aiohttp" "pydantic" 
        "librosa" "soundfile" "scipy" "numpy"
    )
    
    local missing_packages=()
    
    for package in "${required_packages[@]}"; do
        if ! python3 -c "import $package" 2>/dev/null; then
            missing_packages+=("$package")
        fi
    done
    
    if [ ${#missing_packages[@]} -eq 0 ]; then
        show_success "All Python dependencies satisfied"
        return 0
    else
        show_warning "Missing Python packages: ${missing_packages[*]}"
        show_progress "Installing missing packages..."
        pip install -r "$SERVICE_DIR/requirements.txt"
        show_success "Python dependencies installed"
        return 0
    fi
}

# Check system dependencies
check_system_deps() {
    show_progress "Checking system dependencies..."
    
    local missing_deps=()
    
    # Check TTS engines
    if ! command_exists festival; then
        missing_deps+=("festival")
    fi
    
    if ! command_exists espeak; then
        missing_deps+=("espeak")
    fi
    
    if ! command_exists ffmpeg; then
        missing_deps+=("ffmpeg")
    fi
    
    if [ ${#missing_deps[@]} -eq 0 ]; then
        show_success "All system dependencies available"
    else
        show_warning "Missing system packages: ${missing_deps[*]}"
        echo ""
        echo "To install missing dependencies on Ubuntu/Debian:"
        echo "sudo apt-get update"
        echo "sudo apt-get install ${missing_deps[*]}"
        echo ""
        echo "For other systems, please install these packages manually."
        echo ""
    fi
}

# Check port availability
check_port() {
    show_progress "Checking port $SERVICE_PORT availability..."
    
    if lsof -Pi :$SERVICE_PORT -sTCP:LISTEN -t >/dev/null; then
        show_error "Port $SERVICE_PORT is already in use!"
        echo "Please stop the service using that port or change SERVICE_PORT"
        return 1
    else
        show_success "Port $SERVICE_PORT is available"
        return 0
    fi
}

# Create necessary directories
setup_directories() {
    show_progress "Setting up directories..."
    
    mkdir -p "/tmp/audio_generation"
    mkdir -p "/tmp/audio_cache"
    mkdir -p "$(dirname "$LOG_FILE")"
    
    show_success "Directories created"
}

# Check hub integration
check_hub_integration() {
    show_progress "Checking building bots network connectivity..."
    
    # Check if generative hub is running
    if curl -s "http://localhost:8500" >/dev/null 2>&1; then
        show_success "Generative hub detected - network integration active"
        export HUB_INTEGRATION_ENABLED=true
    else
        show_warning "Generative hub not detected - running in standalone mode"
        export HUB_INTEGRATION_ENABLED=false
    fi
    
    # Check if OpenAI service is running
    if curl -s "http://localhost:8475" >/dev/null 2>&1; then
        show_success "OpenAI integration service detected"
        export OPENAI_INTEGRATION_AVAILABLE=true
    else
        show_warning "OpenAI integration service not detected - using local models only"
        export OPENAI_INTEGRATION_AVAILABLE=false
    fi
}

# Display service information
show_service_info() {
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}                    SERVICE INFORMATION                     ${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${BLUE}Service:${NC} $SERVICE_NAME"
    echo -e "${BLUE}Version:${NC} 3.0.0"
    echo -e "${BLUE}Port:${NC} $SERVICE_PORT"
    echo -e "${BLUE}URL:${NC} http://localhost:$SERVICE_PORT"
    echo -e "${BLUE}Documentation:${NC} http://localhost:$SERVICE_PORT (see README.md)"
    echo ""
    echo -e "${PURPLE}🏗️  Building Bots Network Status:${NC}"
    echo -e "${BLUE}Mission:${NC} Excellence in Audio Construction"
    echo -e "${BLUE}Network Integration:${NC} ${HUB_INTEGRATION_ENABLED:-false}"
    echo -e "${BLUE}Service Discovery:${NC} Enabled"
    echo -e "${BLUE}Cross-Service Optimization:${NC} Active"
    echo ""
    echo -e "${GREEN}🎵 Audio Capabilities:${NC}"
    echo "  • Multi-model Text-to-Speech (OpenAI, Piper, Festival, eSpeak)"
    echo "  • Voice Cloning and Personalization"
    echo "  • Procedural Music Generation (12+ styles)"
    echo "  • Advanced Audio Editing and Enhancement"
    echo "  • Real-time Transcription (Whisper)"
    echo "  • ML-Powered Optimization and Learning"
    echo "  • 19+ Language Support"
    echo "  • Batch Processing and API Integration"
    echo ""
    echo -e "${YELLOW}📋 Available Endpoints:${NC}"
    echo "  • POST /generate/speech - Text-to-speech generation"
    echo "  • POST /generate/batch - Batch audio generation"
    echo "  • POST /clone/voice - Voice cloning from reference"
    echo "  • POST /generate/music - Procedural music creation"
    echo "  • POST /edit - Audio editing and enhancement"
    echo "  • POST /transcribe - Audio-to-text transcription"
    echo "  • GET /voices - Available voices catalog"
    echo "  • GET /languages - Supported languages"
    echo "  • GET /models - TTS models information"
    echo "  • GET /analytics/system - Service analytics"
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
    echo ""
}

# Start the service
start_service() {
    show_progress "Starting $SERVICE_NAME..."
    
    cd "$SERVICE_DIR"
    
    # Set environment variables
    export PORT=$SERVICE_PORT
    export PYTHONPATH="$SERVICE_DIR:$PYTHONPATH"
    
    # Start the service with proper logging
    show_success "🚀 Service starting on port $SERVICE_PORT"
    echo ""
    echo -e "${GREEN}Building Bots Network - Audio Construction Excellence Engaged!${NC}"
    echo -e "${BLUE}Press Ctrl+C to stop the service${NC}"
    echo ""
    
    # Run the service
    if [ "$1" = "--background" ]; then
        nohup python3 main.py > "$LOG_FILE" 2>&1 &
        local pid=$!
        echo $pid > "$SERVICE_DIR/service.pid"
        show_success "Service started in background with PID $pid"
        echo "Monitor logs: tail -f $LOG_FILE"
        echo "Stop service: kill $pid or run: ./stop_service.sh"
    else
        python3 main.py 2>&1 | tee -a "$LOG_FILE"
    fi
}

# Stop the service (if running in background)
stop_service() {
    if [ -f "$SERVICE_DIR/service.pid" ]; then
        local pid=$(cat "$SERVICE_DIR/service.pid")
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid"
            rm -f "$SERVICE_DIR/service.pid"
            show_success "Service stopped (PID $pid)"
        else
            show_warning "Service PID file found but process not running"
            rm -f "$SERVICE_DIR/service.pid"
        fi
    else
        show_warning "No service PID file found"
    fi
}

# Service status
service_status() {
    if [ -f "$SERVICE_DIR/service.pid" ]; then
        local pid=$(cat "$SERVICE_DIR/service.pid")
        if kill -0 "$pid" 2>/dev/null; then
            show_success "Service is running (PID $pid)"
            echo "Service URL: http://localhost:$SERVICE_PORT"
            echo "Logs: tail -f $LOG_FILE"
            return 0
        else
            show_warning "Service PID file exists but process not running"
            return 1
        fi
    else
        show_warning "Service is not running"
        return 1
    fi
}

# Main execution
main() {
    print_banner
    
    case "${1:-start}" in
        "start")
            check_python_deps
            check_system_deps
            check_port || exit 1
            setup_directories
            check_hub_integration
            show_service_info
            start_service
            ;;
        "start-bg"|"background")
            check_python_deps
            check_system_deps
            check_port || exit 1
            setup_directories
            check_hub_integration
            show_service_info
            start_service --background
            ;;
        "stop")
            stop_service
            ;;
        "status")
            service_status
            ;;
        "restart")
            stop_service
            sleep 2
            check_port || exit 1
            start_service --background
            ;;
        "check")
            show_progress "Running system checks..."
            check_python_deps
            check_system_deps
            check_hub_integration
            show_success "System check completed"
            ;;
        "info")
            check_hub_integration
            show_service_info
            ;;
        *)
            echo "Usage: $0 {start|start-bg|stop|status|restart|check|info}"
            echo ""
            echo "Commands:"
            echo "  start     - Start service interactively"
            echo "  start-bg  - Start service in background"
            echo "  stop      - Stop background service"
            echo "  status    - Check service status"
            echo "  restart   - Restart background service"
            echo "  check     - Run system dependency checks"
            echo "  info      - Show service information"
            echo ""
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"