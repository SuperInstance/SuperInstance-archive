"""
Health check endpoints.

This module provides health check endpoints for monitoring the application
status, database connectivity, and system metrics.
"""

import time
from typing import Dict, Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.dependencies import get_database_session, get_settings_dependency
from app.exceptions.models import HealthCheckResponse, DetailedHealthCheckResponse
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/", response_model=HealthCheckResponse, summary="Basic health check")
async def health_check(
    request: Request,
    db: AsyncSession = Depends(get_database_session),
    settings = Depends(get_settings_dependency)
) -> HealthCheckResponse:
    """
    Basic health check endpoint.

    Returns basic health information about the application.
    """
    startup_time = getattr(request.app.state, 'startup_time', time.time())
    uptime = time.time() - startup_time

    # Perform basic health checks
    checks = {}

    # Database health check
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        checks["database"] = "unhealthy"

    # API health check (always healthy if we can respond)
    checks["api"] = "healthy"

    # Determine overall status
    overall_status = "healthy"
    if any(check != "healthy" for check in checks.values()):
        overall_status = "unhealthy"

    return HealthCheckResponse(
        status=overall_status,
        timestamp=time.time(),
        uptime_seconds=round(uptime, 2),
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        checks=checks
    )


@router.get("/detailed", response_model=DetailedHealthCheckResponse, summary="Detailed health check")
async def detailed_health_check(
    request: Request,
    db: AsyncSession = Depends(get_database_session),
    settings = Depends(get_settings_dependency)
) -> DetailedHealthCheckResponse:
    """
    Detailed health check endpoint.

    Returns detailed health information including system metrics.
    """
    import psutil

    startup_time = getattr(request.app.state, 'startup_time', time.time())
    uptime = time.time() - startup_time

    # System metrics
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')

    # Detailed health checks
    checks = {}

    # Database health check with timing
    try:
        start_time = time.time()
        await db.execute(text("SELECT 1"))
        db_response_time = (time.time() - start_time) * 1000
        checks["database"] = {
            "status": "healthy",
            "response_time_ms": round(db_response_time, 2),
        }
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        checks["database"] = {
            "status": "unhealthy",
            "error": str(e),
        }

    # API health check
    checks["api"] = {
        "status": "healthy",
        "response_time_ms": 1.0,
    }

    # Memory health check
    memory_status = "healthy" if memory.percent < 80 else "degraded"
    if memory.percent > 95:
        memory_status = "unhealthy"
    checks["memory"] = {
        "status": memory_status,
        "usage_percent": memory.percent,
        "available_gb": round(memory.available / (1024**3), 2),
    }

    # CPU health check
    cpu_status = "healthy" if cpu_percent < 80 else "degraded"
    if cpu_percent > 95:
        cpu_status = "unhealthy"
    checks["cpu"] = {
        "status": cpu_status,
        "usage_percent": cpu_percent,
    }

    # Disk health check
    disk_percent = (disk.used / disk.total) * 100
    disk_status = "healthy" if disk_percent < 80 else "degraded"
    if disk_percent > 95:
        disk_status = "unhealthy"
    checks["disk"] = {
        "status": disk_status,
        "usage_percent": round(disk_percent, 2),
        "free_gb": round(disk.free / (1024**3), 2),
    }

    # Determine overall status
    statuses = [check["status"] if isinstance(check, dict) else check for check in checks.values()]
    if any(status == "unhealthy" for status in statuses):
        overall_status = "unhealthy"
    elif any(status == "degraded" for status in statuses):
        overall_status = "degraded"
    else:
        overall_status = "healthy"

    return DetailedHealthCheckResponse(
        status=overall_status,
        timestamp=time.time(),
        uptime_seconds=round(uptime, 2),
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        checks=checks,
        system={
            "cpu_percent": cpu_percent,
            "memory": {
                "total": memory.total,
                "available": memory.available,
                "percent": memory.percent,
                "used": memory.used,
                "free": memory.free,
            },
            "disk": {
                "total": disk.total,
                "free": disk.free,
                "used": disk.used,
                "percent": round(disk_percent, 2),
            }
        }
    )


@router.get("/ready", summary="Readiness check")
async def readiness_check(
    request: Request,
    db: AsyncSession = Depends(get_database_session)
) -> Dict[str, Any]:
    """
    Readiness check endpoint.

    Used by Kubernetes and other orchestration systems to determine
    if the application is ready to serve traffic.
    """
    checks = {}

    # Database connectivity check
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "ready"
    except Exception as e:
        logger.error(f"Database readiness check failed: {str(e)}")
        checks["database"] = "not_ready"

    # API readiness check (always ready if we can respond)
    checks["api"] = "ready"

    # Determine overall readiness
    overall_ready = all(check == "ready" for check in checks.values())

    return {
        "status": "ready" if overall_ready else "not_ready",
        "timestamp": time.time(),
        "checks": checks
    }


@router.get("/live", summary="Liveness check")
async def liveness_check(request: Request) -> Dict[str, Any]:
    """
    Liveness check endpoint.

    Used by Kubernetes and other orchestration systems to determine
    if the application is still alive.
    """
    startup_time = getattr(request.app.state, 'startup_time', time.time())
    uptime = time.time() - startup_time

    return {
        "status": "alive",
        "timestamp": time.time(),
        "uptime_seconds": round(uptime, 2)
    }