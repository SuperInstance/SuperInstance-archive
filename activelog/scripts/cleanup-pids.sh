#!/bin/bash

# ActiveLog PID Cleanup Script
# Safely stops services and cleans up stale PID files

echo "🧹 ActiveLog PID Cleanup Starting..."

PID_DIR="/home/activeloguser/activelog/pids"

if [ ! -d "$PID_DIR" ]; then
    echo "❌ PID directory not found: $PID_DIR"
    exit 1
fi

# Count of services to clean
TOTAL_PIDS=$(find "$PID_DIR" -name "*.pid" | wc -l)
echo "📊 Found $TOTAL_PIDS PID files to process"

CLEANED=0
RUNNING=0
STALE=0

# Process each PID file
for pid_file in "$PID_DIR"/*.pid; do
    if [ ! -f "$pid_file" ]; then
        continue
    fi
    
    service_name=$(basename "$pid_file" .pid)
    
    if [ -s "$pid_file" ]; then
        pid=$(cat "$pid_file")
        
        # Check if process is actually running
        if kill -0 "$pid" 2>/dev/null; then
            echo "✅ $service_name (PID: $pid) - Running"
            ((RUNNING++))
        else
            echo "🗑️  $service_name (PID: $pid) - Stale, cleaning up"
            rm -f "$pid_file"
            ((STALE++))
            ((CLEANED++))
        fi
    else
        echo "🗑️  $service_name - Empty PID file, cleaning up" 
        rm -f "$pid_file"
        ((CLEANED++))
    fi
done

echo ""
echo "📈 Cleanup Summary:"
echo "   - Running services: $RUNNING"
echo "   - Cleaned stale PIDs: $STALE" 
echo "   - Total files processed: $TOTAL_PIDS"
echo ""

if [ $CLEANED -gt 0 ]; then
    echo "✨ Cleanup completed successfully!"
else
    echo "✅ No cleanup needed - all services are healthy"
fi