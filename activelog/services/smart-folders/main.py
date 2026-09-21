"""
ActiveLog Smart Folders Service

Intelligent folder management with dynamic content organization:
- Dynamic folders based on rules and conditions
- AI-suggested folder structures and organization
- Virtual folders without moving physical files
- Folder templates for common use cases
- Inheritance rules for nested hierarchies
- Folder sharing with granular permissions
"""

import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

# Add src to path for imports
sys.path.append(str(Path(__file__).parent / "src"))

from core.config import settings
from core.database import init_db, get_db
from core.smart_folder_manager import SmartFolderManager
from api.routes import router as api_router
from middleware.auth import AuthMiddleware
from middleware.rate_limit import RateLimitMiddleware
from utils.logger import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Global smart folder manager
smart_folder_manager = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    global smart_folder_manager
    
    # Startup
    logger.info("Starting ActiveLog Smart Folders Service...")
    
    # Initialize database
    await init_db()
    
    # Initialize smart folder manager
    smart_folder_manager = SmartFolderManager()
    await smart_folder_manager.initialize()
    
    # Start background tasks
    asyncio.create_task(smart_folder_manager.start_background_tasks())
    
    logger.info(f"Smart Folders Service started on port {settings.PORT}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Smart Folders Service...")
    if smart_folder_manager:
        await smart_folder_manager.cleanup()

# Create FastAPI app
app = FastAPI(
    title="ActiveLog Smart Folders Service",
    description="Intelligent folder management with dynamic content organization",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8088"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(AuthMiddleware)
app.add_middleware(RateLimitMiddleware)

# Include API routes
app.include_router(api_router, prefix="/api/v1")

@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": "ActiveLog Smart Folders Service",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "features": [
            "Dynamic Folder Rules",
            "AI-Suggested Organization", 
            "Virtual Folders",
            "Folder Templates",
            "Inheritance Rules",
            "Permission Management"
        ]
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check smart folder manager
        if not smart_folder_manager:
            raise Exception("Smart folder manager not initialized")
        
        # Check database connectivity
        db = await get_db()
        await db.database.fetch_one("SELECT 1")
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "smart_folder_manager": "active",
            "active_folders": len(smart_folder_manager.active_folders) if smart_folder_manager else 0
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )

@app.get("/metrics")
async def get_metrics():
    """Service metrics endpoint"""
    if not smart_folder_manager:
        raise HTTPException(status_code=503, detail="Smart folder manager not available")
    
    return await smart_folder_manager.get_metrics()

@app.get("/folders/suggestions/{user_id}")
async def get_folder_suggestions(user_id: str):
    """Get AI-generated folder structure suggestions"""
    if not smart_folder_manager:
        raise HTTPException(status_code=503, detail="Smart folder manager not available")
    
    suggestions = await smart_folder_manager.get_folder_suggestions(user_id)
    return {"suggestions": suggestions}

@app.post("/folders/apply-template")
async def apply_folder_template(request: dict):
    """Apply a folder template to user's organization"""
    if not smart_folder_manager:
        raise HTTPException(status_code=503, detail="Smart folder manager not available")
    
    user_id = request.get("user_id")
    template_id = request.get("template_id")
    
    if not user_id or not template_id:
        raise HTTPException(status_code=400, detail="user_id and template_id required")
    
    result = await smart_folder_manager.apply_template(user_id, template_id)
    return result

@app.post("/folders/refresh/{folder_id}")
async def refresh_smart_folder(folder_id: str, background_tasks: BackgroundTasks):
    """Manually refresh a smart folder's content"""
    if not smart_folder_manager:
        raise HTTPException(status_code=503, detail="Smart folder manager not available")
    
    # Add refresh task to background
    background_tasks.add_task(smart_folder_manager.refresh_folder, folder_id)
    
    return {"message": "Folder refresh initiated", "folder_id": folder_id}

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Global HTTP exception handler"""
    logger.warning(f"HTTP {exc.status_code}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "timestamp": datetime.utcnow().isoformat(),
            "path": str(request.url)
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "timestamp": datetime.utcnow().isoformat(),
            "path": str(request.url)
        }
    )

def get_smart_folder_manager():
    """Dependency to get smart folder manager"""
    global smart_folder_manager
    if not smart_folder_manager:
        raise HTTPException(status_code=503, detail="Smart folder manager not available")
    return smart_folder_manager

if __name__ == "__main__":
    # Development server
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info" if not settings.DEBUG else "debug",
        workers=1 if settings.DEBUG else settings.WORKERS
    )