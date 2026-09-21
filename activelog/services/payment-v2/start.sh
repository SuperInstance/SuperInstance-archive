#!/bin/bash

# Start the ActiveLog Payment System v2 on port 8325
echo "Starting ActiveLog Payment System v2..."

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
mkdir -p static/uploads static/invoices

# Set environment variables
export DATABASE_URL="postgresql+asyncpg://postgres:password@localhost:5432/activelog_payment_v2"
export REDIS_URL="redis://localhost:6379/1"
export PORT=8325

# Start the server
echo "Starting Payment System v2 on port 8325..."
python -m uvicorn src.main:app --host 0.0.0.0 --port 8325 --reload