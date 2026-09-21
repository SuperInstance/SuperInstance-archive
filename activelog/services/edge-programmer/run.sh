#!/bin/bash
echo "Starting Edge Device Programmer Service on port 8338..."
cd "$(dirname "$0")"
python -m uvicorn main:app --host 0.0.0.0 --port 8338 --reload