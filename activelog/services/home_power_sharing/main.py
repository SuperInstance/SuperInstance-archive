"""
Home Power Sharing Service
Distributed computing power sharing and resource allocation system

Generated on 2025-08-25 by activeloguser
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import os
from datetime import datetime
from typing import Dict, Any

from models import HealthResponse, ServiceInfoResponse
from database import get_database, init_database
from config import settings

# Setup logging
logging.basicConfig(level=getattr(logging, settings.log_level))
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Home Power Sharing",
    description="Distributed computing power sharing and resource allocation system",
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
    logger.info("Starting Home Power Sharing service...")
    await init_database()
    logger.info("Home Power Sharing service started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down Home Power Sharing service...")


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        service="home_power_sharing",
        timestamp=datetime.utcnow(),
        version="1.0.0"
    )


@app.get("/info", response_model=ServiceInfoResponse)
async def service_info():
    """Service information endpoint."""
    return ServiceInfoResponse(
        service_name="home_power_sharing",
        version="1.0.0",
        description="Distributed computing power sharing and resource allocation system",
        port=8440,
        environment=settings.environment,
        generated_date="2025-08-25"
    )


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Home Power Sharing API", "docs": "/docs"}


# Power Sharing API Routes
@app.post("/api/v1/nodes/register")
async def register_node(node_data: dict, db = Depends(get_database)):
    """Register a computing node for power sharing."""
    node = {
        "id": node_data.get("node_id"),
        "hostname": node_data.get("hostname"),
        "cpu_cores": node_data.get("cpu_cores", 4),
        "memory_gb": node_data.get("memory_gb", 8),
        "gpu_available": node_data.get("gpu_available", False),
        "power_capacity": node_data.get("power_capacity", 100),
        "current_load": 0,
        "status": "active",
        "registered_at": datetime.utcnow()
    }
    return {"message": "Node registered", "node_id": node["id"], "status": "active"}


@app.get("/api/v1/nodes")
async def list_nodes(db = Depends(get_database)):
    """List all available computing nodes."""
    nodes = [
        {"id": "node_1", "hostname": "home-pc-1", "cpu_cores": 8, "memory_gb": 16, "current_load": 25, "status": "active"},
        {"id": "node_2", "hostname": "home-laptop-1", "cpu_cores": 4, "memory_gb": 8, "current_load": 60, "status": "active"}
    ]
    return {"nodes": nodes, "total": len(nodes)}


@app.post("/api/v1/jobs/submit")
async def submit_job(job_data: dict, db = Depends(get_database)):
    """Submit a computing job to the power sharing network."""
    job = {
        "job_id": job_data.get("job_id", f"job_{datetime.utcnow().timestamp()}"),
        "task_type": job_data.get("task_type"),
        "cpu_required": job_data.get("cpu_required", 1),
        "memory_required": job_data.get("memory_required", 1),
        "estimated_duration": job_data.get("estimated_duration", 300),
        "priority": job_data.get("priority", "medium"),
        "status": "queued",
        "submitted_at": datetime.utcnow()
    }
    return {"message": "Job submitted", "job_id": job["job_id"], "status": "queued"}


@app.get("/api/v1/jobs/{job_id}")
async def get_job_status(job_id: str, db = Depends(get_database)):
    """Get the status of a specific job."""
    return {
        "job_id": job_id,
        "status": "running",
        "assigned_node": "node_1",
        "progress": 45,
        "estimated_completion": "2025-08-25T15:30:00Z"
    }


@app.get("/api/v1/network/stats")
async def network_statistics(db = Depends(get_database)):
    """Get network-wide power sharing statistics."""
    return {
        "total_nodes": 12,
        "active_nodes": 8,
        "total_jobs_completed": 1245,
        "jobs_in_queue": 3,
        "jobs_running": 5,
        "total_power_shared_kwh": 45.7,
        "average_efficiency": 87.3
    }


@app.post("/api/v1/nodes/{node_id}/update")
async def update_node_status(node_id: str, update_data: dict, db = Depends(get_database)):
    """Update node status and resource availability."""
    return {
        "node_id": node_id,
        "status": "updated",
        "current_load": update_data.get("current_load"),
        "available_resources": update_data.get("available_resources")
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8440)
