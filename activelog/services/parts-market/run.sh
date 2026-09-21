#!/bin/bash
echo "Starting Parts Marketplace Service on port 8339..."
cd "$(dirname "$0")"
python -m uvicorn main:app --host 0.0.0.0 --port 8339 --reload