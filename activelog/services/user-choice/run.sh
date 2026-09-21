#!/bin/bash
echo "Starting Choice Economics Service on port 8335..."
cd "$(dirname "$0")"
python -m uvicorn main:app --host 0.0.0.0 --port 8335 --reload