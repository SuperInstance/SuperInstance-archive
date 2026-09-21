"""
ActiveLog Collaboration Service

Real-time collaboration platform with:
- Real-time collaborative annotations
- Comments and discussions on files  
- Version control for documents
- Shared workspaces
- Activity feeds and timelines
- Team permissions management
- Guest access with expiry
"""

import asyncio
import logging
import logging.config
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

# Add src to path for imports
sys.path.append(str(Path(__file__).parent / "src"))

from core.config import settings, LOGGING_CONFIG
from core.database import init_db, close_db, db_manager

# Setup logging
logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    
    # Startup
    logger.info("Starting ActiveLog Collaboration Service...")
    
    # Create logs directory
    Path("logs").mkdir(exist_ok=True)
    
    # Create storage directory
    Path(settings.STORAGE_PATH).mkdir(parents=True, exist_ok=True)
    
    # Initialize database
    await init_db()
    
    logger.info(f"Collaboration Service started on port {settings.PORT}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Collaboration Service...")
    await close_db()

# Create FastAPI app
app = FastAPI(
    title="ActiveLog Collaboration Service",
    description="Real-time collaboration platform with annotations, comments, version control, and team workspaces",
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

# Static files for collaboration UI
if Path("static").exists():
    app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": "ActiveLog Collaboration Service",
        "version": "1.0.0",
        "description": "Real-time collaboration platform",
        "features": [
            "Real-time collaborative annotations",
            "Comments and discussions on files",
            "Version control for documents", 
            "Shared workspaces",
            "Activity feeds and timelines",
            "Team permissions management",
            "Guest access with expiry"
        ],
        "docs_url": "/docs",
        "health_url": "/health"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        health_status = {
            "status": "healthy",
            "timestamp": asyncio.get_event_loop().time(),
            "version": "1.0.0",
            "components": {}
        }
        
        # Check database
        try:
            await db_manager.database.execute("SELECT 1")
            health_status["components"]["database"] = "healthy"
        except Exception as e:
            health_status["components"]["database"] = f"unhealthy: {str(e)}"
            health_status["status"] = "degraded"
        
        # Check storage
        try:
            storage_path = Path(settings.STORAGE_PATH)
            if storage_path.exists() and storage_path.is_dir():
                health_status["components"]["storage"] = "healthy"
            else:
                health_status["components"]["storage"] = "storage path not accessible"
                health_status["status"] = "degraded"
        except Exception as e:
            health_status["components"]["storage"] = f"unhealthy: {str(e)}"
            health_status["status"] = "degraded"
        
        return health_status
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": asyncio.get_event_loop().time()
        }

@app.get("/metrics")
async def metrics():
    """Prometheus-style metrics endpoint"""
    try:
        # Basic metrics from database
        metrics_data = {
            "workspaces_total": 0,
            "documents_total": 0,
            "annotations_total": 0,
            "comments_total": 0,
            "active_guest_sessions": 0,
            "storage_usage_bytes": 0
        }
        
        try:
            # Get workspace count
            from core.database import workspaces
            workspace_query = f"SELECT COUNT(*) FROM {workspaces.name}"
            result = await db_manager.database.fetch_one(workspace_query)
            metrics_data["workspaces_total"] = result[0] if result else 0
            
            # Get document count
            from core.database import documents
            doc_query = f"SELECT COUNT(*) FROM {documents.name}"
            result = await db_manager.database.fetch_one(doc_query)
            metrics_data["documents_total"] = result[0] if result else 0
            
            # Get annotation count
            from core.database import annotations
            ann_query = f"SELECT COUNT(*) FROM {annotations.name}"
            result = await db_manager.database.fetch_one(ann_query)
            metrics_data["annotations_total"] = result[0] if result else 0
            
            # Get comment count
            from core.database import comments
            comment_query = f"SELECT COUNT(*) FROM {comments.name}"
            result = await db_manager.database.fetch_one(comment_query)
            metrics_data["comments_total"] = result[0] if result else 0
            
            # Get active guest sessions
            from core.database import guest_sessions
            from sqlalchemy import func
            guest_query = f"SELECT COUNT(*) FROM {guest_sessions.name} WHERE is_active = true"
            result = await db_manager.database.fetch_one(guest_query)
            metrics_data["active_guest_sessions"] = result[0] if result else 0
            
        except Exception as e:
            logger.warning(f"Failed to collect database metrics: {e}")
        
        # Get storage usage
        try:
            storage_path = Path(settings.STORAGE_PATH)
            if storage_path.exists():
                total_size = sum(f.stat().st_size for f in storage_path.rglob('*') if f.is_file())
                metrics_data["storage_usage_bytes"] = total_size
        except Exception as e:
            logger.warning(f"Failed to calculate storage usage: {e}")
        
        return metrics_data
        
    except Exception as e:
        logger.error(f"Metrics collection failed: {e}")
        raise HTTPException(status_code=500, detail="Metrics unavailable")

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception on {request.url}: {exc}", exc_info=True)
    
    if settings.DEBUG:
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "detail": str(exc),
                "type": type(exc).__name__
            }
        )
    else:
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"}
        )

# Development endpoints (only in debug mode)
if settings.DEBUG:
    @app.post("/dev/reset-db")
    async def reset_database():
        """Reset database (development only)"""
        try:
            await db_manager.drop_tables()
            await db_manager.create_tables()
            return {"message": "Database reset successfully"}
        except Exception as e:
            logger.error(f"Database reset failed: {e}")
            raise HTTPException(status_code=500, detail="Database reset failed")

def main():
    """Main entry point"""
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        workers=1,  # Use 1 worker for proper lifespan management
        log_level="debug" if settings.DEBUG else "info",
        access_log=True
    )

if __name__ == "__main__":
    main()