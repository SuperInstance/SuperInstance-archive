#!/bin/bash

# Start the SuperInstance Bot Learning System
echo "🧠 Activating SuperInstance Bot ML Learning System..."
echo "===================================================="

# Check for API key
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "❌ Error: ANTHROPIC_API_KEY required for learning system"
    exit 1
fi

# Create necessary directories
mkdir -p journals
mkdir -p training
mkdir -p logs

echo "📁 Created learning system directories:"
echo "  - journals/ (individual bot learning entries)"
echo "  - training/ (synthesized training materials)"
echo "  - logs/ (system activity logs)"

# Log activation
echo "$(date +%H:%M)|learning-system|START|ML-bot-improvement-system-activated" >> /home/activeloguser/activelog/micro_updates.log

echo ""
echo "🚀 Learning System Features:"
echo "  📝 Bots write learning journals after each task"
echo "  🔄 Training bot synthesizes learnings every 15 minutes"
echo "  🧹 Audit bot cleans obsolete materials every hour"
echo "  📈 Continuous improvement through ecosystem-specific ML"
echo ""

echo "✅ Bot Learning System Ready!"
echo "   Bots will now automatically improve through experience"
echo "   Training materials will be continuously optimized"
echo "   System knowledge will compound over time"