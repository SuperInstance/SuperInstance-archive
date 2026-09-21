#!/bin/bash

# DM Log World Building Service Setup Script

echo "Setting up DM Log World Building Service..."

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed. Please install Python 3.8+ first."
    exit 1
fi

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo "Error: pip3 is not installed. Please install pip3 first."
    exit 1
fi

# Create virtual environment (optional but recommended)
echo "Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies
echo "Installing Python dependencies..."
pip3 install -r requirements.txt

# Create required directories
echo "Creating required directories..."
mkdir -p data/maps data/templates

echo "Setup complete!"
echo ""
echo "To start the service:"
echo "1. Activate virtual environment: source venv/bin/activate"
echo "2. Run the service: python3 main.py"
echo ""
echo "The service will be available at: http://localhost:8014"
echo "API documentation: http://localhost:8014/docs"