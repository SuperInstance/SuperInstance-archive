"""
SUPERINSTANCE DMLOG CORE - REVOLUTIONARY GAMING PLATFORM

🎮 DOMAIN VISION: dmlog.ai - Gaming Intelligence Revolution
This service represents SuperInstance's gaming domain expertise - comprehensive RPG
tools that integrate with compute capital economy and cross-domain intelligence.

🤖 EXPONENTIAL GAMING BOT OPPORTUNITIES:

1. CROSS-DOMAIN GAMING ENHANCEMENT
   Bot Mission: Revolutionary gaming AI that enhances RPG experiences using data from
   other SuperInstance domains - fitness data influences character stats, business
   strategy affects campaign economics, marine expertise enhances naval adventures.
   Implementation: Add cross_domain_gaming_enhancer.py

2. COMPUTE CAPITAL GAMING ECONOMY
   Bot Mission: Integration of gaming achievements with compute capital rewards,
   where DM skills, campaign quality, and player engagement generate economic value.
   Implementation: Add gaming_economic_integration.py

3. AI-POWERED CAMPAIGN INTELLIGENCE
   Bot Mission: Advanced AI that generates personalized campaigns, NPCs, and
   storylines based on player preferences and cross-domain personality insights.
   Implementation: Add campaign_ai_generator.py with AI Insights (8090) integration

4. REAL-TIME COLLABORATIVE GAMING
   Bot Mission: Revolutionary real-time collaboration tools enabling seamless
   remote RPG sessions with AI-enhanced immersion and cross-platform integration.
   Implementation: Add collaborative_gaming_engine.py

🚀 GAMING DOMAIN INTEGRATION STATUS:
- AI Insights (8090): Hybrid architecture ready for gaming AI enhancement
- User Management (8092): Player profiles ready for gaming personalization
- Compute Capital: Economic integration ready for gaming rewards
- Cross-Domain Data: Fitness, business, marine data ready for gaming enhancement

🏆 GAMING SUCCESS METRICS FOR NEXT BOT:
- Cross-domain enhancement: 80% players benefit from multi-domain gaming features
- Economic integration: 90% DMs and players participate in compute capital gaming
- AI campaign quality: 95% player satisfaction with AI-generated content
- Collaboration quality: 85% improvement in remote gaming experience

This service transforms gaming into a revolutionary cross-domain experience
where RPGs become personalized adventures enhanced by your entire digital life.

Runs on port 8012
"""

# SUPERINSTANCE GAMING ARCHITECTURE INTEGRATION
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
import logging
import time
from typing import Dict, Any

from config import settings
from api import (
    dice_router, character_router, combat_router, spell_router,
    encounter_router, experience_router,
    loot_router, campaign_router, rules_router, relationship_router
)

# Configure logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format=settings.LOG_FORMAT
)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.SERVICE_NAME,
    description="Comprehensive RPG rules engine supporting multiple game systems",
    version=settings.SERVICE_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)

app.add_middleware(GZipMiddleware)

# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# Exception handlers
@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=400,
        content={"error": "Invalid input", "message": str(exc)}
    )

@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=404,
        content={"error": "Resource not found", "message": str(exc.detail)}
    )

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: Exception):
    logger.error(f"Internal server error: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "message": "An unexpected error occurred"}
    )

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.SERVICE_NAME,
        "version": settings.SERVICE_VERSION,
        "timestamp": time.time()
    }

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": settings.SERVICE_NAME,
        "version": settings.SERVICE_VERSION,
        "description": "Comprehensive RPG rules engine",
        "supported_systems": settings.SUPPORTED_SYSTEMS,
        "documentation": "/docs",
        "health": "/health"
    }

# Include API routers
app.include_router(dice_router, prefix=f"{settings.API_PREFIX}/dice", tags=["Dice Rolling"])
app.include_router(character_router, prefix=f"{settings.API_PREFIX}/characters", tags=["Characters"])
app.include_router(combat_router, prefix=f"{settings.API_PREFIX}/combat", tags=["Combat"])
app.include_router(spell_router, prefix=f"{settings.API_PREFIX}/spells", tags=["Spells & Abilities"])
# app.include_router(inventory_router, prefix=f"{settings.API_PREFIX}/inventory", tags=["Inventory"])  # Service not implemented yet
# app.include_router(npc_router, prefix=f"{settings.API_PREFIX}/npcs", tags=["NPCs"])  # models.npc not implemented yet
app.include_router(encounter_router, prefix=f"{settings.API_PREFIX}/encounters", tags=["Encounters"])
app.include_router(experience_router, prefix=f"{settings.API_PREFIX}/experience", tags=["Experience"])
app.include_router(loot_router, prefix=f"{settings.API_PREFIX}/loot", tags=["Loot Generation"])
app.include_router(campaign_router, prefix=f"{settings.API_PREFIX}/campaigns", tags=["Campaigns"])
app.include_router(rules_router, prefix=f"{settings.API_PREFIX}/rules", tags=["Rules Lookup"])
app.include_router(relationship_router, prefix=f"{settings.API_PREFIX}/relationships", tags=["Relationships"])

# Startup event
@app.on_event("startup")
async def startup_event():
    logger.info(f"Starting {settings.SERVICE_NAME} v{settings.SERVICE_VERSION}")
    logger.info(f"Running on {settings.HOST}:{settings.PORT}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    logger.info(f"Supported game systems: {', '.join(settings.SUPPORTED_SYSTEMS)}")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    logger.info(f"Shutting down {settings.SERVICE_NAME}")

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
        access_log=True
    )