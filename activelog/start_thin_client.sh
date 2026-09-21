#!/bin/bash
# ActiveLog Thin Client Startup Script
# Optimized for high devices

echo "🌐 Starting ActiveLog Thin Client Mode..."
echo "Device tier: high"
echo "Offload threshold: 30%"

# Set environment variables
export ACTIVELOG_MODE="thin_client"
export CLOUD_OFFLOAD_ENABLED="true"
export DEVICE_TIER="high"

# Start only essential services locally
echo "Starting essential local services..."
cd services/auth && python3 main.py &
AUTH_PID=$!

cd ../../services/api-gateway && python3 main.py &
GATEWAY_PID=$!

# Start cloud offloader
echo "Starting cloud compute offloader..."
python3 cloud_compute_offloader.py &
OFFLOADER_PID=$!

# Start lightweight frontend
echo "Starting optimized frontend..."
cd frontend && npm run build:thin && npm run serve:thin &
FRONTEND_PID=$!

echo "Essential services started:"
echo "- Auth Service (PID: $AUTH_PID)"  
echo "- API Gateway (PID: $GATEWAY_PID)"
echo "- Cloud Offloader (PID: $OFFLOADER_PID)"
echo "- Thin Frontend (PID: $FRONTEND_PID)"

echo ""
echo "🎉 ActiveLog Thin Client ready!"
echo "Local interface: http://localhost:3000"
echo "Cloud compute: Enabled"
echo "Estimated cost: $0.01-0.10/hour depending on usage"
