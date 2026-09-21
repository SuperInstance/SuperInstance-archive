#!/bin/bash

# Dynamic Bot Language Evolution System Startup Script
# This script starts the core language evolution system for the Building Bots Network

echo "🧠 Starting Dynamic Bot Language Evolution System..."
echo "   Research Platform for Dissertation Bot"
echo "   Building Bots Network Integration"
echo ""

# Set the working directory
cd "$(dirname "$0")"

# Check if Python dependencies are installed
echo "🔍 Checking Python dependencies..."
if ! python3 -c "import flask, numpy, sklearn" 2>/dev/null; then
    echo "📦 Installing Python dependencies..."
    pip3 install -r requirements.txt
else
    echo "✅ Dependencies already installed"
fi

# Create logs directory if it doesn't exist
mkdir -p logs

# Set default port if not specified
if [ -z "$PORT" ]; then
    export PORT=8472
fi

echo ""
echo "🚀 Configuration:"
echo "   Port: $PORT"
echo "   Database: language_evolution.db"
echo "   Logs: language_evolution.log"
echo "   Working Directory: $(pwd)"
echo ""

echo "🎓 Research Features:"
echo "   ✓ Comprehensive logging for academic analysis"
echo "   ✓ Real-time performance metrics"
echo "   ✓ Controlled experiment framework"
echo "   ✓ Cross-domain language evolution"
echo "   ✓ ML-powered optimization"
echo ""

echo "🌐 API Endpoints will be available at:"
echo "   Health Check: http://localhost:$PORT/health"
echo "   Compress: POST http://localhost:$PORT/compress"
echo "   Decompress: POST http://localhost:$PORT/decompress"
echo "   Translate: POST http://localhost:$PORT/translate"
echo "   Analytics: http://localhost:$PORT/analytics"
echo "   Research Metrics: http://localhost:$PORT/research/metrics"
echo ""

# Start the system
echo "🧠 Starting Dynamic Bot Language Evolution System..."
echo "   Press Ctrl+C to stop"
echo "   Logs will be written to language_evolution.log"
echo ""

# Run the main system
python3 main.py

echo ""
echo "🛑 Dynamic Bot Language Evolution System stopped"