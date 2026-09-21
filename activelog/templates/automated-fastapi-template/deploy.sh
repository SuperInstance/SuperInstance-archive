#!/bin/bash
# Auto-generated deployment script for automated-fastapi-template

PORT=${1:-8000}

echo "🚀 Deploying automated-fastapi-template on port $PORT"

# Install dependencies
pip install -r requirements.txt

# Start service
python main.py --port=$PORT
