#!/usr/bin/env python3
"""
PersonalLog.ai Backend Service - Simplified Version
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import uvicorn
from datetime import datetime

app = FastAPI(title="PersonalLog.ai Backend", version="2.0.0")

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
        "service": "personallog-backend",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/")
async def root():
    return {
        "service": "PersonalLog.ai Backend",
        "status": "operational",
        "version": "2.0.0"
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8100))
    uvicorn.run(app, host="0.0.0.0", port=port)