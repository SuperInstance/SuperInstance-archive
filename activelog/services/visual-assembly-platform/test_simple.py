#!/usr/bin/env python3
"""
Minimal test server to isolate the FastAPI issue
"""

from fastapi import FastAPI
import uvicorn
import socket
import os

app = FastAPI(title="Test SuperInstance Visual Assembly Platform")

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "SuperInstance Visual Assembly Platform",
        "version": "2.0.0",
        "message": "Basic test working"
    }

@app.get("/")
async def root():
    return {"message": "Visual Assembly Platform Test Server"}

if __name__ == "__main__":
    def find_free_port(start_port=8300):
        for port in range(start_port, start_port + 100):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(("0.0.0.0", port))
                    return port
            except OSError:
                continue
        return None
    
    port = find_free_port()
    print(f"🧪 Testing Visual Assembly Platform on http://0.0.0.0:{port}")
    
    uvicorn.run(
        "test_simple:app",
        host="0.0.0.0", 
        port=port,
        reload=False,
        access_log=True
    )