#!/bin/bash
# Stop the overnight improvement system

echo "🛑 Stopping Overnight Improvement System..."

# Check if PID file exists
PID_FILE="/home/activeloguser/activelog/SYSTEM/overnight.pid"

if [ -f "$PID_FILE" ]; then
    OVERNIGHT_PID=$(cat "$PID_FILE")
    
    if ps -p $OVERNIGHT_PID > /dev/null 2>&1; then
        echo "🔍 Found running process: $OVERNIGHT_PID"
        kill $OVERNIGHT_PID
        
        # Wait a bit for graceful shutdown
        sleep 5
        
        # Force kill if still running
        if ps -p $OVERNIGHT_PID > /dev/null 2>&1; then
            echo "⚡ Force killing process: $OVERNIGHT_PID"
            kill -9 $OVERNIGHT_PID
        fi
        
        echo "✅ Overnight improvement system stopped"
    else
        echo "⚠️  Process $OVERNIGHT_PID not found (may have already finished)"
    fi
    
    # Remove PID file
    rm "$PID_FILE"
else
    echo "⚠️  No PID file found - system may not be running"
fi

# Kill any remaining related processes
pkill -f "overnight_improvement"
pkill -f "claude_api_synthesizer"

echo "🧹 Cleanup complete"
echo "📊 Check final results in: /home/activeloguser/activelog/SYSTEM/OVERNIGHT_IMPROVEMENTS/"
echo "📝 Check logs in: /home/activeloguser/activelog/SYSTEM/LOGS/"