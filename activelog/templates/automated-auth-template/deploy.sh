#!/bin/bash
# Auto-generated deployment script for automated-auth-template

PORT=${1:-8000}

echo "🚀 Deploying automated-auth-template on port $PORT"

# Install dependencies
pip install -r requirements.txt

# Start service
python main.py --port=$PORT
