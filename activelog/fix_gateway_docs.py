# Quick script to check and fix API Gateway docs

import sys
import os

gateway_path = os.path.expanduser("~/activelog/services/api-gateway/main.py")

# Read the current gateway code
with open(gateway_path, 'r') as f:
    content = f.read()

# Check if it has FastAPI
if 'FastAPI' in content:
    print("FastAPI detected in API Gateway")
    if '/docs' not in content:
        print("Docs endpoint not found, but FastAPI auto-generates it")
        print("The issue might be with the route configuration")
    else:
        print("Docs endpoint should be available")
else:
    print("API Gateway might not be using FastAPI")

# Show what framework is being used
if 'flask' in content.lower():
    print("Using Flask framework")
elif 'fastapi' in content.lower():
    print("Using FastAPI framework")
elif 'aiohttp' in content.lower():
    print("Using aiohttp framework")
