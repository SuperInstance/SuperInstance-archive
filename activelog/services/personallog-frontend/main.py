#!/usr/bin/env python3
"""
PersonalLog.ai Frontend Service
===============================

Beautiful, modern web frontend for the PersonalLog.ai journaling platform.
Features local-first architecture with real-time sync, AI-powered insights,
and a premium writing experience.

🎨 Modern Design Elements:
- Clean, minimalist interface focused on writing
- Dark/light mode support with automatic switching
- Responsive design for all devices
- Smooth animations and transitions
- Accessibility-first approach

📱 Key Features:
- Rich text editor with markdown support
- Real-time AI writing suggestions
- Mood tracking with beautiful visualizations
- Tag-based organization
- Search with intelligent filtering
- Local-first with cloud sync
- Offline support with service worker
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import uvicorn
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="PersonalLog.ai Frontend",
    description="Beautiful, modern journaling experience with AI-powered insights",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup templates and static files
templates_dir = Path(__file__).parent / "templates"
static_dir = Path(__file__).parent / "static"

templates_dir.mkdir(exist_ok=True)
static_dir.mkdir(exist_ok=True)

templates = Jinja2Templates(directory=str(templates_dir))

# Mount static files
if static_dir.exists() and any(static_dir.iterdir()):
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

@app.get("/", response_class=HTMLResponse)
async def homepage(request: Request):
    """PersonalLog.ai main application"""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "title": "PersonalLog.ai - AI-Powered Personal Journaling",
        "description": "Transform your thoughts into insights with our beautiful, AI-enhanced journaling platform"
    })

@app.get("/app", response_class=HTMLResponse) 
async def main_app(request: Request):
    """Main journaling application interface"""
    return templates.TemplateResponse("app.html", {
        "request": request,
        "title": "Your Personal Journal - PersonalLog.ai",
        "backend_url": os.getenv("BACKEND_URL", "http://localhost:8100")
    })

@app.get("/app/accessible", response_class=HTMLResponse)
async def accessible_app(request: Request):
    """Accessibility-enhanced journaling application"""
    return templates.TemplateResponse("app-accessible.html", {
        "request": request,
        "title": "Your Personal Journal - PersonalLog.ai (Accessible Mode)",
        "backend_url": os.getenv("BACKEND_URL", "http://localhost:8100")
    })

@app.get("/api/config")
async def get_config():
    """Get frontend configuration"""
    return {
        "backend_url": os.getenv("BACKEND_URL", "http://localhost:8100"),
        "ai_insights_enabled": os.getenv("AI_INSIGHTS", "true").lower() == "true",
        "offline_mode": os.getenv("OFFLINE_MODE", "true").lower() == "true",
        "theme": os.getenv("DEFAULT_THEME", "auto"),
        "features": {
            "rich_editor": True,
            "ai_suggestions": True,
            "mood_tracking": True,
            "cloud_sync": True,
            "offline_support": True,
            "search": True,
            "tags": True,
            "analytics": True
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "PersonalLog.ai Frontend",
        "version": "1.0.0"
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 3000))
    
    print("🎨 PersonalLog.ai Frontend Starting")
    print("📝 Beautiful AI-powered journaling experience")
    print("💫 Local-first with cloud sync")
    print("🤖 Real-time AI writing insights")
    print(f"🌐 Running on http://0.0.0.0:{port}")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False
    )