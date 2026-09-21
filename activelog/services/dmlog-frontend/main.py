#!/usr/bin/env python3
"""
DMLog.ai Gaming Platform Frontend
=================================

Revolutionary RPG gaming platform with AI-powered campaign management,
cross-domain character enhancement, and collaborative gaming tools.
Integrates with the complete DMLog ecosystem for immersive gaming experiences.

🎮 Gaming Features:
- AI-powered campaign generation and management
- Cross-domain character enhancement (fitness → stats)
- Real-time collaborative gaming sessions
- Advanced dice mechanics and combat systems
- Dynamic encounter generation
- Intelligent NPC behavior and dialogue
- Economy integration with compute capital rewards

🤖 AI Integration:
- Campaign AI that learns from player preferences
- Dynamic story adaptation and branching narratives
- Personalized quests based on player history
- AI-driven NPC personalities and interactions
- Intelligent balancing and difficulty scaling

🌐 Cross-Domain Features:
- Fitness data influences character physical stats
- Business knowledge affects campaign economics
- Marine expertise enhances naval adventures
- Educational background impacts skill learning rates
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
    title="DMLog.ai Gaming Platform",
    description="Revolutionary RPG gaming platform with AI-powered campaigns",
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
async def gaming_homepage(request: Request):
    """DMLog.ai gaming platform home"""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "title": "DMLog.ai - Revolutionary RPG Gaming Platform",
        "description": "AI-powered campaigns, cross-domain character enhancement, collaborative gaming"
    })

@app.get("/dashboard", response_class=HTMLResponse)
async def gaming_dashboard(request: Request):
    """Main gaming dashboard"""
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "title": "Gaming Dashboard - DMLog.ai",
        "dmlog_api": os.getenv("DMLOG_API", "http://localhost:8012"),
        "ai_insights_api": os.getenv("AI_INSIGHTS_API", "http://localhost:8090")
    })

@app.get("/campaign/{campaign_id}", response_class=HTMLResponse)
async def campaign_interface(request: Request, campaign_id: str):
    """Campaign management interface"""
    return templates.TemplateResponse("campaign.html", {
        "request": request,
        "title": f"Campaign Management - {campaign_id}",
        "campaign_id": campaign_id,
        "dmlog_api": os.getenv("DMLOG_API", "http://localhost:8012")
    })

@app.get("/character-builder", response_class=HTMLResponse)
async def character_builder(request: Request):
    """Character creation and management"""
    return templates.TemplateResponse("character-builder.html", {
        "request": request,
        "title": "Character Builder - DMLog.ai",
        "fitness_api": os.getenv("FITNESS_API", "http://localhost:8099"),
        "dmlog_api": os.getenv("DMLOG_API", "http://localhost:8012")
    })

@app.get("/session/{session_id}", response_class=HTMLResponse)
async def gaming_session(request: Request, session_id: str):
    """Live gaming session interface"""
    return templates.TemplateResponse("session.html", {
        "request": request,
        "title": f"Gaming Session - {session_id}",
        "session_id": session_id,
        "dmlog_api": os.getenv("DMLOG_API", "http://localhost:8012")
    })

@app.get("/api/config")
async def get_config():
    """Get frontend configuration"""
    return {
        "dmlog_api": os.getenv("DMLOG_API", "http://localhost:8012"),
        "ai_insights_api": os.getenv("AI_INSIGHTS_API", "http://localhost:8090"),
        "fitness_api": os.getenv("FITNESS_API", "http://localhost:8099"),
        "features": {
            "ai_campaigns": True,
            "cross_domain_enhancement": True,
            "collaborative_gaming": True,
            "compute_rewards": True,
            "advanced_combat": True,
            "dynamic_encounters": True
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "DMLog.ai Gaming Platform Frontend",
        "version": "1.0.0"
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8600))
    
    print("🎮 DMLog.ai Gaming Platform Starting")
    print("🎯 Revolutionary RPG gaming with AI campaigns")
    print("🤖 Cross-domain character enhancement enabled")
    print("⚔️ Advanced combat and encounter systems")
    print("🌐 Collaborative gaming sessions ready")
    print(f"🎲 Running on http://0.0.0.0:{port}")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False
    )