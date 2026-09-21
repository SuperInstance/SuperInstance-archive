#!/bin/bash

# Start the ActiveLog Pricing Engine on port 8326
echo "Starting ActiveLog Pricing Engine..."

# Check if virtual environment exists, create if not
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install requirements
echo "Installing requirements..."
pip install -r requirements.txt

# Create directories
mkdir -p static/uploads static/reports

# Set environment variables
export DATABASE_URL="postgresql+asyncpg://postgres:password@localhost:5432/activelog_pricing"
export REDIS_URL="redis://localhost:6379/2"
export PORT=8326

# Start the server
echo "Starting Pricing Engine on port 8326..."
python -m uvicorn src.main:app --host 0.0.0.0 --port 8326 --reload