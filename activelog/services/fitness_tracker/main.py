"""
Fitness Tracker Service
Fitness Tracker Service

Generated on 2025-08-27 by activeloguser
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import os
from datetime import datetime
from typing import Dict, Any

from .models import HealthResponse, ServiceInfoResponse
from .database import get_database, init_database
from .config import settings

# Setup logging
logging.basicConfig(level=getattr(logging, settings.log_level))
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Fitness Tracker",
    description="Fitness Tracker Service",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8088"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize service on startup."""
    logger.info("Starting Fitness Tracker service...")
    await init_database()
    logger.info("Fitness Tracker service started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down Fitness Tracker service...")


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        service="fitness_tracker",
        timestamp=datetime.utcnow(),
        version="1.0.0"
    )


@app.get("/info", response_model=ServiceInfoResponse)
async def service_info():
    """Service information endpoint."""
    return ServiceInfoResponse(
        service_name="fitness_tracker",
        version="1.0.0",
        description="Fitness Tracker Service",
        port=8500,
        environment=settings.environment,
        generated_date="2025-08-27"
    )


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Fitness Tracker API", "docs": "/docs"}


# Add your API routes here
@app.get("/api/v1/fitness-tracker")
async def list_items(db = Depends(get_database)):
    """List items endpoint."""
    # Implement your business logic here
    return {"items": [], "total": 0}


@app.post("/api/v1/fitness-tracker")
async def create_item(db = Depends(get_database)):
    """Create item endpoint."""
    # Implement your business logic here
    return {"message": "Item created"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8500)
