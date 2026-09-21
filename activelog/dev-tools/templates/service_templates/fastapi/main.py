"""
{{SERVICE_NAME_TITLE}} Service
{{SERVICE_DESCRIPTION}}

Generated on {{GENERATED_DATE}} by {{AUTHOR}}
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
    title="{{SERVICE_NAME_TITLE}}",
    description="{{SERVICE_DESCRIPTION}}",
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
    logger.info("Starting {{SERVICE_NAME_TITLE}} service...")
    await init_database()
    logger.info("{{SERVICE_NAME_TITLE}} service started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down {{SERVICE_NAME_TITLE}} service...")


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        service="{{SERVICE_NAME_SNAKE}}",
        timestamp=datetime.utcnow(),
        version="1.0.0"
    )


@app.get("/info", response_model=ServiceInfoResponse)
async def service_info():
    """Service information endpoint."""
    return ServiceInfoResponse(
        service_name="{{SERVICE_NAME_SNAKE}}",
        version="1.0.0",
        description="{{SERVICE_DESCRIPTION}}",
        port={{SERVICE_PORT}},
        environment=settings.environment,
        generated_date="{{GENERATED_DATE}}"
    )


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "{{SERVICE_NAME_TITLE}} API", "docs": "/docs"}


# Add your API routes here
@app.get("/api/v1/{{SERVICE_NAME_KEBAB}}")
async def list_items(db = Depends(get_database)):
    """List items endpoint."""
    # Implement your business logic here
    return {"items": [], "total": 0}


@app.post("/api/v1/{{SERVICE_NAME_KEBAB}}")
async def create_item(db = Depends(get_database)):
    """Create item endpoint."""
    # Implement your business logic here
    return {"message": "Item created"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port={{SERVICE_PORT}})
