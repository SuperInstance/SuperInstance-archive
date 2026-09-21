#!/bin/bash
# Quick start script for overnight improvement system
# Run this and go to sleep - everything gets better automatically

echo "🌙 Starting Overnight Improvement System..."
echo "💤 You can now sleep while your project improves!"

# Make scripts executable
chmod +x /home/activeloguser/activelog/SYSTEM/CONFIGS/overnight_improvement_system.sh
chmod +x /home/activeloguser/activelog/SYSTEM/SCRIPTS/overnight_improvement.py
chmod +x /home/activeloguser/activelog/SYSTEM/SCRIPTS/claude_api_synthesizer.py

# Create necessary directories
mkdir -p /home/activeloguser/activelog/SYSTEM/LOGS
mkdir -p /home/activeloguser/activelog/SYSTEM/OVERNIGHT_IMPROVEMENTS
mkdir -p /home/activeloguser/activelog/SYSTEM/CLAUDE_SYNTHESES
mkdir -p /home/activeloguser/activelog/SYSTEM/DOCUMENT_IMPROVEMENTS

# Set up environment variables (if needed)
export PYTHONPATH="/home/activeloguser/activelog/SYSTEM/SCRIPTS:$PYTHONPATH"

# Display configuration
echo "📊 Configuration:"
echo "   💾 Storage Limit: 8GB"
echo "   💰 API Budget: \$50"
echo "   🔄 Cycles: 12 (every 40 minutes)"
echo "   ⏰ Duration: ~8 hours"
echo ""

echo "🚀 Starting autonomous improvement..."
echo "📝 Check logs at: /home/activeloguser/activelog/SYSTEM/LOGS/"
echo ""

# Start the overnight improvement system in background
nohup /home/activeloguser/activelog/SYSTEM/CONFIGS/overnight_improvement_system.sh > /home/activeloguser/activelog/SYSTEM/LOGS/overnight_main.log 2>&1 &

# Get the PID
OVERNIGHT_PID=$!

# Save PID for later reference
echo $OVERNIGHT_PID > /home/activeloguser/activelog/SYSTEM/overnight.pid

echo "✅ Overnight improvement system started!"
echo "🆔 Process ID: $OVERNIGHT_PID"
echo "📋 PID saved to: /home/activeloguser/activelog/SYSTEM/overnight.pid"
echo ""
echo "🛑 To stop early: kill $OVERNIGHT_PID"
echo "📊 Monitor progress: tail -f /home/activeloguser/activelog/SYSTEM/LOGS/overnight_main.log"
echo ""
echo "😴 Good night! Your project will be improved by morning."
echo "🌅 Check results in: /home/activeloguser/activelog/SYSTEM/OVERNIGHT_IMPROVEMENTS/"