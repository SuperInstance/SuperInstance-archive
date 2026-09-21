#!/bin/bash
echo "Starting AI Receptionist Service on port 8341..."
cd "$(dirname "$0")"
python -m uvicorn main:app --host 0.0.0.0 --port 8341 --reload