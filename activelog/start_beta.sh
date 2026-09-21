#!/bin/bash

echo "Starting ActiveLog Beta Services..."

# Kill any existing services
pkill -f "python.*main.py" 2>/dev/null

# Start core services
echo "Starting Authentication Service..."
cd ~/activelog/services/auth && python main.py &
echo $! > ~/activelog/pids/auth.pid
sleep 2

echo "Starting File Sync Service..."
cd ~/activelog/services/file-sync && python main.py &
echo $! > ~/activelog/pids/file-sync.pid
sleep 2

echo "Starting AI Orchestrator..."
cd ~/activelog/services/ai-orchestrator && python main.py &
echo $! > ~/activelog/pids/ai-orchestrator.pid
sleep 2

echo "Starting API Gateway..."
cd ~/activelog/services/api-gateway && python main.py &
echo $! > ~/activelog/pids/api-gateway.pid
sleep 2

echo "Starting Metadata Service..."
cd ~/activelog/services/metadata && python main.py &
echo $! > ~/activelog/pids/metadata.pid
sleep 2

# Start app-specific services
echo "Starting PersonalLog services..."
cd ~/activelog/services/personallog-core && python main.py &
echo $! > ~/activelog/pids/personallog.pid

echo "Starting BusinessLog services..."
cd ~/activelog/services/businesslog-core && python main.py &
echo $! > ~/activelog/pids/businesslog.pid

echo "Starting FishingLog services..."
cd ~/activelog/services/fishinglog-nav && python main.py &
echo $! > ~/activelog/pids/fishinglog.pid

echo "Starting DMLog services..."
cd ~/activelog/services/dmlog-core && python main.py &
echo $! > ~/activelog/pids/dmlog.pid

echo "Starting Payment System..."
cd ~/activelog/services/payment-gateway && python main.py &
echo $! > ~/activelog/pids/payment.pid

echo "Starting Compute Capital System..."
cd ~/activelog/services/compute-capital && python main.py &
echo $! > ~/activelog/pids/compute-capital.pid

echo ""
echo "Core services started. Checking status..."
sleep 5

# Check all services
ps aux | grep python | grep main.py | wc -l
echo "Services running: $(ps aux | grep python | grep main.py | wc -l)"

echo ""
echo "Beta services are ready!"
echo "Access points:"
echo "  API Gateway: http://localhost:8088"
echo "  Frontend: http://localhost:3000"
echo "  Auth Service: http://localhost:8002"
echo ""
