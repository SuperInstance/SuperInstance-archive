#!/bin/bash
echo "💼 Starting demo-business-api business API..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install -r requirements.txt
if [ -f .env ]; then
    export $(cat .env | xargs)
fi
echo "🎯 Starting demo-business-api on port $PORT"
echo "📊 Dashboard: http://localhost:$PORT"
echo "📖 API docs: http://localhost:$PORT/docs"
python main.py &
SERVICE_PID=$!
sleep 3
curl -f http://localhost:$PORT/health && echo "✅ Service is healthy"
echo "🎉 demo-business-api is running! PID: $SERVICE_PID"
wait $SERVICE_PID
