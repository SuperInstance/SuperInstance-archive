#!/bin/bash

# Bot Orchestrator Startup Script
# Starts the intelligent bot orchestration system on port 8450

# Set environment variables
export ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY:-"your-api-key-here"}
export BOT_ORCHESTRATOR_HOST=${BOT_ORCHESTRATOR_HOST:-"0.0.0.0"}
export BOT_ORCHESTRATOR_PORT=${BOT_ORCHESTRATOR_PORT:-8450}
export BOT_ORCHESTRATOR_LOG_LEVEL=${BOT_ORCHESTRATOR_LOG_LEVEL:-"info"}

# Create logs directory if it doesn't exist
mkdir -p /home/activeloguser/activelog/logs

# Change to service directory
cd /home/activeloguser/activelog/services/bot-orchestrator

echo "Starting Bot Orchestration System..."
echo "Host: $BOT_ORCHESTRATOR_HOST"
echo "Port: $BOT_ORCHESTRATOR_PORT"
echo "Log Level: $BOT_ORCHESTRATOR_LOG_LEVEL"
echo ""
echo "Make sure to set your ANTHROPIC_API_KEY environment variable!"
echo ""

# Start the server
python main.py --host $BOT_ORCHESTRATOR_HOST --port $BOT_ORCHESTRATOR_PORT --log-level $BOT_ORCHESTRATOR_LOG_LEVEL