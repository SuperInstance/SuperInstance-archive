#!/bin/bash

echo "🚀 Setting up all ActiveLog services..."

# Create all service directories
mkdir -p ~/activelog/services/{file-sync,ai-orchestrator,api-gateway,metadata,auth}

# File Sync Service
echo "📁 Creating File Sync Service..."
cat > ~/activelog/services/file-sync/main.py << 'EOSERVICE'
[FULL SERVICE CODE HERE]
EOSERVICE

# AI Orchestrator
echo "🤖 Creating AI Orchestrator..."
cat > ~/activelog/services/ai-orchestrator/main.py << 'EOSERVICE'
[FULL SERVICE CODE HERE]
EOSERVICE

# API Gateway
echo "🌐 Creating API Gateway..."
cat > ~/activelog/services/api-gateway/main.py << 'EOSERVICE'
[FULL SERVICE CODE HERE]
EOSERVICE

# Create a supervisor script to run all services
cat > ~/activelog/start_all.sh << 'EOSTART'
#!/bin/bash
tmux new-session -d -s activelog
tmux send-keys -t activelog:0 "cd ~/activelog/services/file-sync && uvicorn main:app --host 0.0.0.0 --port 8000" C-m
tmux new-window -t activelog:1
tmux send-keys -t activelog:1 "cd ~/activelog/services/ai-orchestrator && uvicorn main:app --host 0.0.0.0 --port 8001" C-m
tmux new-window -t activelog:2
tmux send-keys -t activelog:2 "cd ~/activelog/services/api-gateway && uvicorn main:app --host 0.0.0.0 --port 8080" C-m
echo "All services started! Use 'tmux attach -t activelog' to view"
EOSTART

chmod +x ~/activelog/start_all.sh
echo "✅ Setup complete! Run: ~/activelog/start_all.sh"
