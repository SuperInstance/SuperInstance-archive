#!/usr/bin/env python3
"""
DMLog.ai Backend Service - Simplified Version
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import uvicorn
from datetime import datetime

app = FastAPI(title="DMLog.ai Backend", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "dmlog-backend",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/")
async def root():
    return {
        "service": "DMLog.ai Backend", 
        "status": "operational",
        "version": "2.0.0"
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8300))
    uvicorn.run(app, host="0.0.0.0", port=port)