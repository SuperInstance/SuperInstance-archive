#!/bin/bash

# Start the CCC Economy System on port 8327
echo "Starting CCC Economy System..."

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
mkdir -p static/uploads static/reports static/certificates

# Set environment variables
export DATABASE_URL="postgresql+asyncpg://postgres:password@localhost:5432/activelog_ccc_economy"
export REDIS_URL="redis://localhost:6379/3"
export PORT=8327

# Start the server
echo "Starting CCC Economy System on port 8327..."
python -m uvicorn src.main:app --host 0.0.0.0 --port 8327 --reload