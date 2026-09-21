#!/bin/bash

# SuperInstance Smart Task System Startup Script

set -e

echo "🧠 Starting SuperInstance Smart Task System..."
echo "=============================================="

# Check required environment variables
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "❌ Error: ANTHROPIC_API_KEY environment variable is required"
    echo "Set it with: export ANTHROPIC_API_KEY='your-api-key'"
    exit 1
fi

# Set default values
BOT_ORCHESTRATOR_URL=${BOT_ORCHESTRATOR_URL:-"http://localhost:8450"}
REDIS_URL=${REDIS_URL:-"redis://localhost:6379"}
SMART_TASK_PORT=${SMART_TASK_PORT:-8470}

echo "🔧 Configuration:"
echo "  - Smart Task API Port: $SMART_TASK_PORT"
echo "  - Bot Orchestrator URL: $BOT_ORCHESTRATOR_URL"
echo "  - Redis URL: $REDIS_URL"
echo ""

# Create logs directory
mkdir -p /home/activeloguser/activelog/logs

# Install Python dependencies if needed
if [ ! -d "venv" ]; then
    echo "📦 Setting up Python virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

echo "🧪 Testing task intelligence system..."
echo ""

# Quick test of the system
python -c "
from task_intelligence import TaskIntelligenceClassifier, SmartTaskQueue

print('🔬 Testing Task Classification:')
classifier = TaskIntelligenceClassifier()

test_tasks = [
    ('Fix typo in README.md', 'LOW'),
    ('Implement JWT authentication API', 'HIGH'), 
    ('Design scalable microservices architecture', 'CRITICAL')
]

for desc, priority in test_tasks:
    analysis = classifier.analyze_task(desc, priority=priority)
    print(f'  📋 \"{desc[:30]}...\"')
    print(f'     🤖 Model: {analysis.recommended_model.value.upper()}')
    print(f'     💰 Cost: \${analysis.estimated_cost:.4f}')
    print(f'     🎯 Confidence: {analysis.confidence:.0%}')
    print()

print('✅ Task intelligence system working correctly!')
"

echo ""
echo "🚀 Starting Smart Task API Server..."
echo "   - API Base URL: http://localhost:$SMART_TASK_PORT"
echo "   - Submit tasks: POST /tasks/submit"
echo "   - Task analysis: POST /tasks/analyze"  
echo "   - Performance: GET /performance/report"
echo "   - Queue status: GET /queue/status"
echo ""

echo "💡 Smart Model Selection:"
echo "   - Haiku: Simple tasks (90%+ cost savings)"
echo "   - Sonnet: Standard development (balanced)"
echo "   - Opus: Complex reasoning (premium quality)"
echo ""

echo "📊 Integration Points:"
echo "   - Auto-monitors: /home/activeloguser/activelog/micro_updates.log"
echo "   - Task files: /home/activeloguser/activelog/task_assignments_optimized.txt"
echo "   - API submission: curl -X POST http://localhost:$SMART_TASK_PORT/tasks/submit"
echo ""

echo "🔄 Press Ctrl+C to stop"
echo ""

# Start the smart task API
python task_api.py \
    --host 0.0.0.0 \
    --port $SMART_TASK_PORT \
    --log-level info