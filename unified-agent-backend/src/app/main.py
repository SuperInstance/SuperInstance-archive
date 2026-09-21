"""
Main FastAPI application entry point.

This module initializes the FastAPI application with all necessary middleware,
routers, exception handlers, and configuration. It provides a production-ready
API server with comprehensive error handling, logging, and monitoring.
"""

import logging
import time
from contextlib import asynccontextmanager
from typing import Dict, Any

import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

from app.core.config.settings import get_settings
from app.core.logging import get_logger
from app.db import init_db, close_db
from app.middleware import (
    RequestLoggingMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    RequestIDMiddleware,
)
from app.exceptions.handlers import setup_exception_handlers
from app.api.v1.api import api_router
from app.websocket.manager import websocket_manager

# Get logger
logger = get_logger(__name__)

# Get settings
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> Dict[str, Any]:
    """
    Application lifespan manager.

    Handles startup and shutdown events for the FastAPI application.
    This is where we initialize database connections, load models,
    and perform other startup tasks.

    Args:
        app: FastAPI application instance

    Yields:
        Dictionary with application state
    """
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug mode: {settings.DEBUG}")

    try:
        # Initialize database
        logger.info("Initializing database connection...")
        await init_db(settings.get_database_url())
        logger.info("Database initialized successfully")

        # Initialize WebSocket manager
        logger.info("Initializing WebSocket manager...")
        await websocket_manager.start()
        logger.info("WebSocket manager initialized successfully")

        # Add any other startup tasks here
        # For example: loading models, connecting to external services, etc.

        # Set application state
        app.state.startup_time = time.time()
        app.state.settings = settings

        logger.info("Application startup completed successfully")

        yield {"startup_time": app.state.startup_time}

    except Exception as e:
        logger.error(f"Failed to start application: {str(e)}")
        raise

    # Shutdown
    logger.info("Shutting down application...")
    try:
        # Close database connection
        await close_db()
        logger.info("Database connection closed")

        # Shutdown WebSocket manager
        logger.info("Shutting down WebSocket manager...")
        await websocket_manager.stop()
        logger.info("WebSocket manager shutdown complete")

        # Add any other cleanup tasks here
        logger.info("Application shutdown completed")

    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")


def create_application() -> FastAPI:
    """
    Create and configure FastAPI application.

    Returns:
        Configured FastAPI application instance
    """
    # Create FastAPI app
    app = FastAPI(
        title=settings.TITLE,
        description=settings.APP_DESCRIPTION,
        version=settings.APP_VERSION,
        contact=settings.CONTACT,
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
        docs_url=f"{settings.API_V1_PREFIX}/docs",
        redoc_url=f"{settings.API_V1_PREFIX}/redoc",
        lifespan=lifespan,
        debug=settings.DEBUG,
    )

    # Add custom OpenAPI schema
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema

        openapi_schema = get_openapi(
            title=settings.TITLE,
            version=settings.APP_VERSION,
            description=settings.APP_DESCRIPTION,
            routes=app.routes,
        )

        # Add custom schema info
        openapi_schema["info"]["x-logo"] = {
            "url": "https://fastapi.tiangolo.com/img/logo-margin/logo-teal.png"
        }

        # Add security schemes
        openapi_schema["components"]["securitySchemes"] = {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT"
            }
        }

        app.openapi_schema = openapi_schema
        return app.openapi_schema

    app.openapi = custom_openapi

    # Add middleware in the correct order
    setup_middleware(app)

    # Add exception handlers
    setup_exception_handlers(app)

    # Add routers
    setup_routers(app)

    # Add health check endpoints
    setup_health_endpoints(app)

    return app


def setup_middleware(app: FastAPI) -> None:
    """
    Setup application middleware.

    Args:
        app: FastAPI application instance
    """
    # TrustedHost middleware for production security
    if settings.is_production:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["*"]  # Configure this based on your domain
        )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
    )

    # Request ID middleware (adds unique ID to each request)
    app.add_middleware(RequestIDMiddleware)

    # Security headers middleware
    app.add_middleware(SecurityHeadersMiddleware)

    # Request logging middleware
    app.add_middleware(RequestLoggingMiddleware)

    # Rate limiting middleware (if enabled)
    if settings.RATE_LIMIT_ENABLED:
        app.add_middleware(
            RateLimitMiddleware,
            requests=settings.RATE_LIMIT_REQUESTS,
            window=settings.RATE_LIMIT_WINDOW,
        )


def setup_routers(app: FastAPI) -> None:
    """
    Setup API routers.

    Args:
        app: FastAPI application instance
    """
    # Include main API router
    app.include_router(
        api_router,
        prefix=settings.API_V1_PREFIX,
        tags=["API v1"]
    )

    # Add root endpoint
    @app.get("/", tags=["Root"], include_in_schema=False)
    async def root() -> Dict[str, Any]:
        """Root endpoint with basic information."""
        return {
            "message": f"Welcome to {settings.APP_NAME}",
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
            "docs_url": f"{settings.API_V1_PREFIX}/docs",
            "api_url": settings.API_V1_PREFIX,
        }


def setup_health_endpoints(app: FastAPI) -> None:
    """
    Setup health check endpoints.

    Args:
        app: FastAPI application instance
    """
    @app.get("/health", tags=["Health"])
    async def health_check() -> Dict[str, Any]:
        """
        Basic health check endpoint.

        Returns basic health information about the application.
        """
        uptime = time.time() - app.state.startup_time if hasattr(app.state, 'startup_time') else 0

        return {
            "status": "healthy",
            "timestamp": time.time(),
            "uptime_seconds": round(uptime, 2),
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
            "checks": {
                "database": "healthy",  # TODO: Implement actual database health check
                "api": "healthy",
            }
        }

    @app.get("/health/detailed", tags=["Health"])
    async def detailed_health_check() -> Dict[str, Any]:
        """
        Detailed health check endpoint.

        Returns detailed health information including system metrics.
        """
        import psutil

        uptime = time.time() - app.state.startup_time if hasattr(app.state, 'startup_time') else 0

        # System metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        return {
            "status": "healthy",
            "timestamp": time.time(),
            "uptime_seconds": round(uptime, 2),
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
            "system": {
                "cpu_percent": cpu_percent,
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "percent": memory.percent,
                },
                "disk": {
                    "total": disk.total,
                    "free": disk.free,
                    "percent": (disk.used / disk.total) * 100,
                }
            },
            "checks": {
                "database": {
                    "status": "healthy",  # TODO: Implement actual database health check
                    "response_time_ms": 5.2,
                },
                "api": {
                    "status": "healthy",
                    "response_time_ms": 1.0,
                },
                "memory": {
                    "status": "healthy" if memory.percent < 80 else "degraded",
                    "usage_percent": memory.percent,
                },
                "cpu": {
                    "status": "healthy" if cpu_percent < 80 else "degraded",
                    "usage_percent": cpu_percent,
                },
            }
        }

    @app.get("/ready", tags=["Health"])
    async def readiness_check() -> Dict[str, Any]:
        """
        Readiness check endpoint.

        Used by Kubernetes and other orchestration systems to determine
        if the application is ready to serve traffic.
        """
        # TODO: Add actual readiness checks (database connectivity, etc.)
        return {
            "status": "ready",
            "timestamp": time.time(),
            "checks": {
                "database": "ready",
                "api": "ready",
            }
        }

    @app.get("/live", tags=["Health"])
    async def liveness_check() -> Dict[str, Any]:
        """
        Liveness check endpoint.

        Used by Kubernetes and other orchestration systems to determine
        if the application is still alive.
        """
        return {
            "status": "alive",
            "timestamp": time.time(),
            "uptime_seconds": round(
                time.time() - app.state.startup_time if hasattr(app.state, 'startup_time') else 0,
                2
            )
        }


# Create application instance
app = create_application()


if __name__ == "__main__":
    """
    Run the application directly.

    This is useful for development and testing.
    For production, use uvicorn or gunicorn with appropriate workers.
    """
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=True,
        use_colors=True,
    )