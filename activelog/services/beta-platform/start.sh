#!/bin/bash

# Start the ActiveLog Beta Platform on port 8323
echo "Starting ActiveLog Beta Platform..."

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
mkdir -p static/screenshots static/uploads

# Set environment variables
export DATABASE_URL="postgresql+asyncpg://postgres:password@localhost:5432/activelog_beta"
export REDIS_URL="redis://localhost:6379/0"
export PORT=8323

# Start the server
echo "Starting server on port 8323..."
python -m uvicorn src.main:app --host 0.0.0.0 --port 8323 --reload