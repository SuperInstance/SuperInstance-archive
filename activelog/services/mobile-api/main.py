#!/usr/bin/env python3
"""
ActiveLog Mobile API Service

High-performance mobile-optimized API server with:
- Protocol Buffers for binary communication
- Offline-first sync protocol
- Push notification support
- Image optimization
- Battery-efficient sync strategies
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from services.mobile_api.core.config import settings
from services.mobile_api.core.database import get_database
from services.mobile_api.core.logging_config import setup_logging
from services.mobile_api.core.exceptions import MobileAPIException, mobile_exception_handler
from services.mobile_api.api.auth import router as auth_router
from services.mobile_api.api.sync import router as sync_router
from services.mobile_api.api.files import router as files_router
from services.mobile_api.api.push import router as push_router
from services.mobile_api.api.media import router as media_router
from services.mobile_api.api.protobuf_endpoints import router as protobuf_router
from services.mobile_api.services.push_notifications import PushNotificationService
from services.mobile_api.services.sync_manager import SyncManager
from services.mobile_api.services.image_optimizer import ImageOptimizer
from services.mobile_api.services.battery_manager import BatteryManager
from services.mobile_api.middleware.compression import CompressionMiddleware
from services.mobile_api.middleware.mobile_optimization import MobileOptimizationMiddleware
from services.mobile_api.middleware.protocol_buffer import ProtocolBufferMiddleware

# Setup logging
logger = setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting Mobile API Service...")
    
    # Initialize services
    try:
        # Database connection
        database = get_database()
        await database.connect()
        app.state.database = database
        
        # Initialize core services
        app.state.push_service = PushNotificationService()
        app.state.sync_manager = SyncManager()
        app.state.image_optimizer = ImageOptimizer()
        app.state.battery_manager = BatteryManager()
        
        # Start background services
        await app.state.push_service.initialize()
        await app.state.sync_manager.initialize()
        
        logger.info(f"Mobile API Service started on port {settings.PORT}")
        
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Mobile API Service...")
    
    try:
        # Cleanup services
        if hasattr(app.state, 'push_service'):
            await app.state.push_service.cleanup()
        
        if hasattr(app.state, 'sync_manager'):
            await app.state.sync_manager.cleanup()
        
        if hasattr(app.state, 'database'):
            await app.state.database.disconnect()
            
        logger.info("Mobile API Service shutdown complete")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")

# Create FastAPI app
app = FastAPI(
    title="ActiveLog Mobile API",
    description="Mobile-optimized API for ActiveLog with offline-first sync and Protocol Buffers support",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None
)

# Add middleware (order matters!)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Sync-Token", "X-Battery-Hint", "X-Compression-Ratio"]
)

# Mobile optimization middleware
app.add_middleware(MobileOptimizationMiddleware)

# Protocol Buffer middleware
app.add_middleware(ProtocolBufferMiddleware)

# Compression middleware
app.add_middleware(CompressionMiddleware)

# Gzip for remaining content
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Exception handlers
app.add_exception_handler(MobileAPIException, mobile_exception_handler)

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """General exception handler with mobile-specific error format"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "An internal error occurred",
            "retry_after": 30,  # Mobile-specific: suggest retry delay
            "battery_impact": "low"  # Battery impact hint
        }
    )

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint optimized for mobile"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "services": {
            "database": "healthy",
            "push_notifications": "healthy",
            "sync_manager": "healthy",
            "image_optimizer": "healthy"
        },
        "mobile_optimizations": {
            "compression_enabled": True,
            "protobuf_enabled": True,
            "battery_optimization": True,
            "offline_sync": True
        }
    }

# Root endpoint with API information
@app.get("/")
async def root():
    """API root with mobile-specific information"""
    return {
        "service": "ActiveLog Mobile API",
        "version": "1.0.0",
        "features": [
            "Protocol Buffers binary communication",
            "Offline-first sync",
            "Push notifications",
            "Image optimization",
            "Battery-efficient operations",
            "Bandwidth optimization"
        ],
        "endpoints": {
            "auth": "/api/v1/auth/*",
            "sync": "/api/v1/sync/*",
            "files": "/api/v1/files/*",
            "push": "/api/v1/push/*",
            "media": "/api/v1/media/*",
            "protobuf": "/api/v1/pb/*"
        },
        "protocols": {
            "http": "Supported with JSON",
            "protobuf": "Supported for binary data",
            "websocket": "Supported for real-time sync"
        }
    }

# Mobile-specific metrics endpoint
@app.get("/metrics/mobile")
async def mobile_metrics(request: Request):
    """Mobile-specific metrics for monitoring and optimization"""
    battery_manager = request.app.state.battery_manager
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "active_connections": battery_manager.get_active_connections(),
        "battery_efficiency": {
            "avg_request_time": battery_manager.get_avg_request_time(),
            "battery_impact_score": battery_manager.get_battery_impact_score(),
            "sync_efficiency": battery_manager.get_sync_efficiency()
        },
        "bandwidth_optimization": {
            "compression_ratio": battery_manager.get_compression_ratio(),
            "data_saved_mb": battery_manager.get_data_saved(),
            "protobuf_usage_percent": battery_manager.get_protobuf_usage()
        },
        "sync_status": {
            "pending_syncs": await request.app.state.sync_manager.get_pending_sync_count(),
            "failed_syncs": await request.app.state.sync_manager.get_failed_sync_count(),
            "last_sync": await request.app.state.sync_manager.get_last_sync_time()
        }
    }

# Include API routers
app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(sync_router, prefix="/api/v1/sync", tags=["Synchronization"])
app.include_router(files_router, prefix="/api/v1/files", tags=["Files"])
app.include_router(push_router, prefix="/api/v1/push", tags=["Push Notifications"])
app.include_router(media_router, prefix="/api/v1/media", tags=["Media"])
app.include_router(protobuf_router, prefix="/api/v1/pb", tags=["Protocol Buffers"])

# Background tasks
@app.on_event("startup")
async def startup_tasks():
    """Background tasks to run on startup"""
    # Start periodic cleanup tasks
    asyncio.create_task(periodic_cleanup())
    asyncio.create_task(sync_health_check())
    asyncio.create_task(battery_optimization_task())

async def periodic_cleanup():
    """Periodic cleanup of temporary files and expired sessions"""
    while True:
        try:
            logger.info("Running periodic cleanup...")
            
            # Cleanup expired sync tokens
            sync_manager = app.state.sync_manager
            await sync_manager.cleanup_expired_tokens()
            
            # Cleanup temporary files
            image_optimizer = app.state.image_optimizer
            await image_optimizer.cleanup_temp_files()
            
            # Cleanup push notification cache
            push_service = app.state.push_service
            await push_service.cleanup_expired_notifications()
            
            logger.info("Periodic cleanup completed")
            
        except Exception as e:
            logger.error(f"Error in periodic cleanup: {e}")
        
        # Run cleanup every 30 minutes
        await asyncio.sleep(1800)

async def sync_health_check():
    """Monitor sync service health and performance"""
    while True:
        try:
            sync_manager = app.state.sync_manager
            health = await sync_manager.health_check()
            
            if not health["healthy"]:
                logger.warning(f"Sync service health check failed: {health}")
                
                # Attempt to restart sync service if needed
                if health["critical"]:
                    logger.info("Attempting to restart sync service...")
                    await sync_manager.restart()
            
        except Exception as e:
            logger.error(f"Error in sync health check: {e}")
        
        # Check every 5 minutes
        await asyncio.sleep(300)

async def battery_optimization_task():
    """Monitor and optimize battery usage patterns"""
    while True:
        try:
            battery_manager = app.state.battery_manager
            
            # Analyze battery usage patterns
            analysis = await battery_manager.analyze_usage_patterns()
            
            if analysis["optimization_needed"]:
                logger.info(f"Applying battery optimizations: {analysis['recommendations']}")
                await battery_manager.apply_optimizations(analysis["recommendations"])
            
        except Exception as e:
            logger.error(f"Error in battery optimization task: {e}")
        
        # Run optimization analysis every 15 minutes
        await asyncio.sleep(900)

if __name__ == "__main__":
    # Development server
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info" if settings.DEBUG else "warning",
        access_log=settings.DEBUG,
        server_header=False,
        date_header=False
    )