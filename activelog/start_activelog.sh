#!/bin/bash

echo "🚀 Starting ActiveLog.ai System..."

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to check if port is in use
check_port() {
    netstat -tuln | grep -q ":$1 "
    return $?
}

# Start Docker services
echo -e "${BLUE}Starting Docker services...${NC}"
docker compose up -d
sleep 5

# Kill any existing services on our ports
for port in 8000 8001 8002 8003 8080 3000; do
    if check_port $port; then
        echo "Killing process on port $port"
        fuser -k $port/tcp 2>/dev/null
    fi
done

sleep 2

# Start all services in background
echo -e "${BLUE}Starting File Sync Service (port 8000)...${NC}"
cd ~/activelog/services/file-sync
nohup uvicorn main:app --host 0.0.0.0 --port 8000 > ~/activelog/logs/file-sync.log 2>&1 &
echo $! > ~/activelog/pids/file-sync.pid

echo -e "${BLUE}Starting AI Orchestrator (port 8001)...${NC}"
cd ~/activelog/services/ai-orchestrator
nohup uvicorn main:app --host 0.0.0.0 --port 8001 > ~/activelog/logs/ai-orchestrator.log 2>&1 &
echo $! > ~/activelog/pids/ai-orchestrator.pid

echo -e "${BLUE}Starting API Gateway (port 8080)...${NC}"
cd ~/activelog/services/api-gateway
nohup uvicorn main:app --host 0.0.0.0 --port 8088 > ~/activelog/logs/api-gateway.log 2>&1 &
echo $! > ~/activelog/pids/api-gateway.pid

echo -e "${BLUE}Starting Frontend (port 3000)...${NC}"
cd ~/activelog/frontend
nohup python3 -m http.server 3000 > ~/activelog/logs/frontend.log 2>&1 &
echo $! > ~/activelog/pids/frontend.pid

# Wait for services to start
echo -e "${BLUE}Waiting for services to initialize...${NC}"
sleep 5

# Check health
echo -e "${GREEN}Checking service health...${NC}"
for port in 8000 8001 8080; do
    if curl -s http://localhost:$port/health > /dev/null; then
        echo -e "${GREEN}✓ Service on port $port is healthy${NC}"
    else
        echo -e "✗ Service on port $port failed to start"
    fi
done

echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}ActiveLog.ai is running!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "📊 Dashboard:        http://localhost:3000"
echo "📁 File Sync API:    http://localhost:8000/docs"
echo "🤖 AI Orchestrator:  http://localhost:8001/docs"
echo "🌐 API Gateway:      http://localhost:8088/docs"
echo "💾 MinIO Console:    http://localhost:9001"
echo ""
echo "To view logs: tail -f ~/activelog/logs/*.log"
echo "To stop all: ~/activelog/stop_activelog.sh"
