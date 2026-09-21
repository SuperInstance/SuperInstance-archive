"""
ActiveLog Data Export Service

Comprehensive data export service providing multiple export formats:
- PDF documents with preserved metadata
- ZIP and tar.gz archives
- Static website generation
- Photo books and albums
- GDPR-compliant data exports
- Bulk export with progress tracking
- Cloud provider integration
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
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

# Add src to path for imports
sys.path.append(str(Path(__file__).parent / "src"))

from core.config import settings, ExportSettings
from core.database import init_db, get_db
from core.export_manager import ExportManager
from api.routes import router as api_router
from middleware.auth import AuthMiddleware
from middleware.rate_limit import RateLimitMiddleware
from utils.logger import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Global export manager
export_manager = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    global export_manager
    
    # Startup
    logger.info("Starting ActiveLog Data Export Service...")
    
    # Initialize database
    await init_db()
    
    # Initialize export manager
    export_manager = ExportManager()
    await export_manager.initialize()
    
    # Create output directories
    os.makedirs(settings.EXPORT_OUTPUT_DIR, exist_ok=True)
    os.makedirs(settings.EXPORT_TEMP_DIR, exist_ok=True)
    
    logger.info(f"Data Export Service started on port {settings.PORT}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Data Export Service...")
    if export_manager:
        await export_manager.cleanup()

# Create FastAPI app
app = FastAPI(
    title="ActiveLog Data Export Service",
    description="Comprehensive data export service with multiple format support",
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

# Mount static files for templates and generated content
app.mount("/static", StaticFiles(directory="templates"), name="static")
app.mount("/exports", StaticFiles(directory=settings.EXPORT_OUTPUT_DIR), name="exports")

# Include API routes
app.include_router(api_router, prefix="/api/v1")

@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": "ActiveLog Data Export Service",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "features": [
            "PDF Export",
            "Archive Creation (ZIP, tar.gz)",
            "Static Website Generation", 
            "Photo Books/Albums",
            "GDPR Data Export",
            "Bulk Export with Progress",
            "Cloud Provider Integration"
        ]
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check export manager
        if not export_manager:
            raise Exception("Export manager not initialized")
        
        # Check directories
        if not os.path.exists(settings.EXPORT_OUTPUT_DIR):
            raise Exception("Output directory not accessible")
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "export_manager": "active",
            "active_exports": len(export_manager.active_exports) if export_manager else 0
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
    if not export_manager:
        raise HTTPException(status_code=503, detail="Export manager not available")
    
    return await export_manager.get_metrics()

@app.get("/exports/progress/{export_id}")
async def get_export_progress(export_id: str):
    """Get progress of a specific export job"""
    if not export_manager:
        raise HTTPException(status_code=503, detail="Export manager not available")
    
    progress = await export_manager.get_export_progress(export_id)
    if not progress:
        raise HTTPException(status_code=404, detail="Export job not found")
    
    return progress

@app.delete("/exports/{export_id}")
async def cancel_export(export_id: str):
    """Cancel a running export job"""
    if not export_manager:
        raise HTTPException(status_code=503, detail="Export manager not available")
    
    success = await export_manager.cancel_export(export_id)
    if not success:
        raise HTTPException(status_code=404, detail="Export job not found")
    
    return {"message": "Export cancelled successfully"}

@app.get("/exports/{export_id}/download")
async def download_export(export_id: str):
    """Download completed export file"""
    if not export_manager:
        raise HTTPException(status_code=503, detail="Export manager not available")
    
    file_path = await export_manager.get_export_file_path(export_id)
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Export file not found")
    
    # Determine filename and media type
    filename = os.path.basename(file_path)
    
    return FileResponse(
        path=file_path,
        filename=filename,
        headers={"X-Export-ID": export_id}
    )

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

def get_export_manager():
    """Dependency to get export manager"""
    global export_manager
    if not export_manager:
        raise HTTPException(status_code=503, detail="Export manager not available")
    return export_manager

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