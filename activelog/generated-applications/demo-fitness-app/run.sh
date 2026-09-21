#!/bin/bash
# Deployment script for demo-fitness-app

echo "🏋️ Starting demo-fitness-app fitness application..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "📋 Installing dependencies..."
pip install -r requirements.txt

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | xargs)
fi

# Health check function
health_check() {
    echo "🔍 Checking service health..."
    curl -f http://localhost:$PORT/health || exit 1
    echo "✅ Service is healthy"
}

# Start service
echo "🎯 Starting demo-fitness-app on port $PORT"
echo "📊 Dashboard: http://localhost:$PORT"
echo "📖 API docs: http://localhost:$PORT/docs"
echo "🔐 Demo login: username=demo, password=password"

# Run in background and monitor
python main.py &
SERVICE_PID=$!

# Wait for startup
sleep 3

# Perform health check
health_check

echo "🎉 demo-fitness-app is running successfully!"
echo "PID: $SERVICE_PID"
echo ""
echo "🔗 Quick Links:"
echo "   Health: http://localhost:$PORT/health"
echo "   Docs: http://localhost:$PORT/docs"
echo "   Login: POST http://localhost:$PORT/auth/login"
echo ""
echo "To stop: kill $SERVICE_PID"

# Keep script running
wait $SERVICE_PID
