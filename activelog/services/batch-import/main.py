"""
ActiveLog Batch Import Service
Monitors import folder and processes files in batches
"""

import asyncio
import logging
from pathlib import Path
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from core.config import settings
from core.logging_config import setup_logging
from services.import_monitor import ImportMonitor
from services.batch_processor import BatchProcessor
from services.report_service import ReportService
from api.routes import router
from api.websocket import websocket_router

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="ActiveLog Batch Import Service",
    description="Automated file import and processing service",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(router, prefix="/api/v1")
app.include_router(websocket_router)

# Global services
import_monitor = None
batch_processor = None
report_service = None

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    global import_monitor, batch_processor, report_service
    
    logger.info("Starting ActiveLog Batch Import Service")
    
    # Create necessary directories
    Path(settings.IMPORT_QUEUE_PATH).mkdir(parents=True, exist_ok=True)
    Path(settings.PROCESSING_PATH).mkdir(parents=True, exist_ok=True)
    Path(settings.COMPLETED_PATH).mkdir(parents=True, exist_ok=True)
    Path(settings.FAILED_PATH).mkdir(parents=True, exist_ok=True)
    Path(settings.REPORTS_PATH).mkdir(parents=True, exist_ok=True)
    
    # Initialize services
    report_service = ReportService()
    batch_processor = BatchProcessor(report_service=report_service)
    import_monitor = ImportMonitor(
        import_path=settings.IMPORT_QUEUE_PATH,
        batch_processor=batch_processor,
        check_interval=settings.MONITOR_INTERVAL
    )
    
    # Start monitoring
    asyncio.create_task(import_monitor.start_monitoring())
    
    logger.info(f"Batch Import Service started on port {settings.PORT}")
    logger.info(f"Monitoring directory: {settings.IMPORT_QUEUE_PATH}")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global import_monitor
    
    logger.info("Shutting down ActiveLog Batch Import Service")
    
    if import_monitor:
        await import_monitor.stop_monitoring()

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "ActiveLog Batch Import Service",
        "version": "1.0.0",
        "status": "running",
        "import_queue": settings.IMPORT_QUEUE_PATH,
        "monitor_interval": settings.MONITOR_INTERVAL
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check if import directory exists and is accessible
        import_path = Path(settings.IMPORT_QUEUE_PATH)
        if not import_path.exists():
            raise HTTPException(status_code=503, detail="Import queue directory not accessible")
        
        # Check if services are running
        monitor_status = import_monitor.is_running() if import_monitor else False
        
        return {
            "status": "healthy",
            "services": {
                "import_monitor": monitor_status,
                "batch_processor": batch_processor is not None,
                "report_service": report_service is not None
            },
            "directories": {
                "import_queue": str(import_path),
                "accessible": import_path.exists()
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=str(e))

@app.get("/stats")
async def get_stats():
    """Get service statistics"""
    try:
        stats = {}
        
        if import_monitor:
            stats["monitor"] = import_monitor.get_stats()
        
        if batch_processor:
            stats["processor"] = batch_processor.get_stats()
        
        if report_service:
            stats["reports"] = report_service.get_stats()
        
        return stats
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Dependency injection
def get_batch_processor() -> BatchProcessor:
    """Get batch processor instance"""
    if not batch_processor:
        raise HTTPException(status_code=503, detail="Batch processor not initialized")
    return batch_processor

def get_report_service() -> ReportService:
    """Get report service instance"""
    if not report_service:
        raise HTTPException(status_code=503, detail="Report service not initialized")
    return report_service

def get_import_monitor() -> ImportMonitor:
    """Get import monitor instance"""
    if not import_monitor:
        raise HTTPException(status_code=503, detail="Import monitor not initialized")
    return import_monitor

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )