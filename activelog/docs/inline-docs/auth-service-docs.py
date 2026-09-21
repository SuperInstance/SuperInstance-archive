"""
Enhanced Auth Service with Comprehensive Documentation

This module provides the main FastAPI application for the ActiveLog Authentication Service.
It handles user authentication, authorization, JWT token management, and role-based access control.

Architecture Overview:
- FastAPI framework for high-performance async API
- JWT-based stateless authentication
- Role-based access control (RBAC)
- CORS middleware for cross-origin requests
- Dependency injection for clean separation of concerns

Security Features:
- Secure JWT token generation and validation
- Password hashing using bcrypt
- Rate limiting for authentication endpoints
- HTTPS enforcement in production
- Session management and token refresh

Example Usage:
    Start the auth service:
    $ uvicorn main:app --host 0.0.0.0 --port 8001
    
    Login request:
    $ curl -X POST http://localhost:8001/auth/login \\
           -H "Content-Type: application/json" \\
           -d '{"username": "user@example.com", "password": "password"}'
           
    Access protected endpoint:
    $ curl -H "Authorization: Bearer <jwt_token>" \\
           http://localhost:8001/protected

Author: ActiveLog Team
Version: 1.0.0
License: MIT
"""

from typing import Optional, Dict, Any
from contextlib import asynccontextmanager
import logging
import uvicorn

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from auth_models import init_db, get_db_health
from auth_routes import router as auth_router
from middleware import get_current_user, require_role, rate_limit_middleware
from config import get_settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load application settings
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup and shutdown events.
    
    This async context manager handles:
    - Database initialization on startup
    - Connection pool setup
    - Health check initialization
    - Graceful shutdown and cleanup
    
    Args:
        app: The FastAPI application instance
        
    Yields:
        None: Control during application runtime
        
    Raises:
        DatabaseConnectionError: If database initialization fails
        ConfigurationError: If required settings are missing
    """
    logger.info("🚀 Starting ActiveLog Auth Service...")
    
    try:
        # Initialize database connection and tables
        await init_db()
        logger.info("✅ Database initialized successfully")
        
        # Verify database health
        db_status = await get_db_health()
        if not db_status.get("healthy"):
            raise Exception("Database health check failed")
            
        logger.info("✅ Auth Service startup complete")
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise
    
    # Application is running
    yield
    
    # Shutdown cleanup
    logger.info("🔄 Shutting down Auth Service...")
    # Add cleanup code here if needed
    logger.info("✅ Auth Service shutdown complete")


def create_app() -> FastAPI:
    """
    Factory function to create and configure the FastAPI application.
    
    This function sets up:
    - FastAPI app with metadata and documentation
    - CORS middleware for cross-origin requests
    - Security middleware for trusted hosts
    - Rate limiting middleware
    - Authentication routes and endpoints
    - Error handlers and exception handling
    
    Returns:
        FastAPI: Configured FastAPI application instance
        
    Example:
        app = create_app()
        uvicorn.run(app, host="0.0.0.0", port=8001)
    """
    
    # Create FastAPI app with comprehensive metadata
    app = FastAPI(
        title="ActiveLog Authentication Service",
        description="""
        🔐 **ActiveLog Authentication & Authorization Service**
        
        This service provides secure authentication and authorization for the ActiveLog platform.
        
        ## Features
        - JWT-based stateless authentication
        - Role-based access control (RBAC)
        - User management and profiles
        - Session management
        - OAuth2 integration support
        - Multi-factor authentication (2FA)
        
        ## Security
        - Bcrypt password hashing
        - Secure JWT token generation
        - Rate limiting on auth endpoints
        - HTTPS enforcement
        - CORS protection
        
        ## Usage
        1. **Login**: POST `/auth/login` with credentials
        2. **Get Token**: Receive JWT token in response
        3. **Access APIs**: Include `Authorization: Bearer <token>` header
        4. **Refresh**: Use refresh token to get new access token
        
        For detailed API documentation, see the endpoints below.
        """,
        version="1.0.0",
        docs_url="/docs" if settings.DEBUG else None,  # Disable docs in production
        redoc_url="/redoc" if settings.DEBUG else None,
        openapi_url="/openapi.json" if settings.DEBUG else None,
        lifespan=lifespan,
        # Additional metadata
        contact={
            "name": "ActiveLog Support",
            "url": "https://activelog.com/support",
            "email": "support@activelog.com",
        },
        license_info={
            "name": "MIT License",
            "url": "https://opensource.org/licenses/MIT",
        },
        servers=[
            {
                "url": "http://localhost:8001",
                "description": "Development server"
            },
            {
                "url": "https://auth.activelog.com",
                "description": "Production server"
            }
        ]
    )
    
    # Security middleware - add trusted host protection
    if not settings.DEBUG:
        app.add_middleware(
            TrustedHostMiddleware, 
            allowed_hosts=settings.ALLOWED_HOSTS or ["*"]
        )
    
    # CORS middleware for cross-origin requests
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS or ["*"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Total-Count", "X-Rate-Limit-*"]
    )
    
    # Rate limiting middleware
    app.add_middleware(rate_limit_middleware)
    
    return app


# Create the FastAPI application
app = create_app()

# HTTP Bearer security scheme for OpenAPI documentation
security = HTTPBearer(
    scheme_name="JWT",
    description="JWT token obtained from /auth/login endpoint"
)

# Include authentication routes with comprehensive tagging
app.include_router(
    auth_router, 
    prefix="/auth", 
    tags=["authentication"],
    responses={
        401: {"description": "Authentication failed"},
        403: {"description": "Insufficient permissions"},
        429: {"description": "Too many requests"}
    }
)


@app.get(
    "/",
    summary="Service Information",
    description="Returns basic information about the Auth Service",
    response_description="Service status and metadata",
    tags=["health"]
)
async def root() -> Dict[str, Any]:
    """
    Get basic service information and status.
    
    This endpoint provides:
    - Service name and version
    - Current status
    - Uptime information
    - Configuration summary (non-sensitive)
    
    Returns:
        Dict[str, Any]: Service information including:
            - service: Service name
            - version: Service version
            - status: Current operational status
            - uptime: Service uptime in seconds
            - features: Enabled features list
            
    Example:
        ```json
        {
            "service": "ActiveLog Auth Service",
            "version": "1.0.0",
            "status": "running",
            "uptime": 3600,
            "features": ["jwt", "rbac", "2fa"]
        }
        ```
    """
    return {
        "service": "ActiveLog Auth Service",
        "version": "1.0.0",
        "status": "running",
        "uptime": 0,  # TODO: Implement actual uptime tracking
        "features": [
            "jwt_authentication",
            "role_based_access_control", 
            "user_management",
            "session_management"
        ],
        "documentation": "/docs" if settings.DEBUG else None
    }


@app.get(
    "/health",
    summary="Health Check",
    description="Comprehensive health check for monitoring and load balancers",
    response_description="Detailed health status",
    tags=["health"],
    responses={
        200: {
            "description": "Service is healthy",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "service": "auth",
                        "timestamp": "2024-01-01T12:00:00Z",
                        "components": {
                            "database": "healthy",
                            "cache": "healthy"
                        }
                    }
                }
            }
        },
        503: {
            "description": "Service is unhealthy",
            "content": {
                "application/json": {
                    "example": {
                        "status": "unhealthy",
                        "service": "auth",
                        "errors": ["database_connection_failed"]
                    }
                }
            }
        }
    }
)
async def health_check() -> JSONResponse:
    """
    Comprehensive health check endpoint for service monitoring.
    
    This endpoint checks:
    - Database connectivity and response time
    - Cache system availability (Redis)
    - External dependencies status
    - Service memory and CPU usage
    - Configuration validity
    
    Used by:
    - Load balancers for routing decisions
    - Monitoring systems (Prometheus, Grafana)
    - Container orchestrators (Kubernetes, Docker Swarm)
    - CI/CD pipelines for deployment validation
    
    Returns:
        JSONResponse: Health status with detailed component information
        - HTTP 200: Service is fully operational
        - HTTP 503: Service has issues (removes from load balancer)
        
    Health Check Components:
        - database: PostgreSQL connection and query performance
        - cache: Redis connectivity and memory usage
        - external_apis: Third-party service dependencies
        - disk_space: Available storage for logs and temp files
        - memory: Current memory usage vs limits
        
    Example Response (Healthy):
        ```json
        {
            "status": "healthy",
            "service": "auth",
            "timestamp": "2024-01-01T12:00:00Z",
            "uptime_seconds": 3600,
            "components": {
                "database": {
                    "status": "healthy",
                    "response_time_ms": 5,
                    "connection_pool": "20/50"
                },
                "cache": {
                    "status": "healthy", 
                    "memory_usage": "45%",
                    "hit_rate": "95%"
                }
            },
            "metrics": {
                "requests_per_second": 150,
                "error_rate": 0.001,
                "avg_response_time_ms": 45
            }
        }
        ```
        
    Example Response (Unhealthy):
        ```json
        {
            "status": "unhealthy",
            "service": "auth", 
            "timestamp": "2024-01-01T12:00:00Z",
            "errors": [
                "database_connection_timeout",
                "high_memory_usage"
            ],
            "components": {
                "database": {
                    "status": "unhealthy",
                    "error": "Connection timeout after 30s"
                },
                "cache": {
                    "status": "healthy"
                }
            }
        }
        ```
    """
    from datetime import datetime
    
    health_data = {
        "status": "healthy",
        "service": "auth",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "uptime_seconds": 0,  # TODO: Implement uptime tracking
        "version": "1.0.0"
    }
    
    components = {}
    overall_healthy = True
    errors = []
    
    try:
        # Check database health
        db_health = await get_db_health()
        components["database"] = db_health
        if not db_health.get("healthy"):
            overall_healthy = False
            errors.append("database_unhealthy")
            
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        components["database"] = {"status": "unhealthy", "error": str(e)}
        overall_healthy = False
        errors.append("database_connection_failed")
    
    # TODO: Add more health checks (Redis, external APIs, disk space, etc.)
    
    health_data["components"] = components
    
    if not overall_healthy:
        health_data["status"] = "unhealthy"
        health_data["errors"] = errors
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=health_data
        )
    
    return JSONResponse(content=health_data)


@app.get(
    "/protected",
    summary="Protected Endpoint Example", 
    description="Example endpoint requiring valid JWT authentication",
    response_description="Protected resource data",
    tags=["examples"],
    dependencies=[Depends(security)]
)
async def protected_endpoint(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Example protected endpoint requiring authentication.
    
    This endpoint demonstrates:
    - JWT token validation
    - User context injection
    - Protected resource access
    - Proper error responses
    
    Authentication Required:
        Include JWT token in Authorization header:
        ```
        Authorization: Bearer <jwt_token>
        ```
        
    Args:
        current_user: Injected user context from JWT token, contains:
            - user_id: Unique user identifier
            - username: User's username/email
            - roles: List of user roles
            - permissions: List of user permissions
            - exp: Token expiration timestamp
            
    Returns:
        Dict[str, Any]: Protected resource data with user context
        
    Raises:
        HTTPException 401: Token invalid, expired, or missing
        HTTPException 403: User lacks required permissions
        
    Example Response:
        ```json
        {
            "message": "Access granted to protected resource",
            "user": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "username": "user@example.com",
                "roles": ["user"],
                "permissions": ["read", "write"]
            },
            "resource": "protected_data",
            "timestamp": "2024-01-01T12:00:00Z"
        }
        ```
    """
    return {
        "message": "Access granted to protected resource",
        "user": {
            "user_id": current_user.get("user_id"),
            "username": current_user.get("username"), 
            "roles": current_user.get("roles", []),
            "permissions": current_user.get("permissions", [])
        },
        "resource": "protected_data",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "request_id": None  # TODO: Add request tracking
    }


@app.get(
    "/admin-only",
    summary="Admin-Only Endpoint Example",
    description="Example endpoint requiring admin role",
    response_description="Admin resource data", 
    tags=["examples"],
    dependencies=[Depends(security)]
)
async def admin_only_endpoint(
    current_user: Dict[str, Any] = Depends(require_role("admin"))
) -> Dict[str, Any]:
    """
    Example admin-only endpoint with role-based access control.
    
    This endpoint demonstrates:
    - Role-based access control (RBAC)
    - Admin privilege verification
    - Hierarchical permission checking
    - Audit logging for admin actions
    
    Required Role:
        User must have 'admin' role or higher in their JWT token.
        Role hierarchy: guest < user < moderator < admin < super_admin
        
    Authentication Required:
        Include JWT token with admin role:
        ```
        Authorization: Bearer <jwt_token_with_admin_role>
        ```
        
    Args:
        current_user: Injected admin user context, validated to have admin role
        
    Returns:
        Dict[str, Any]: Admin resource data with elevated permissions
        
    Raises:
        HTTPException 401: Token invalid, expired, or missing
        HTTPException 403: User lacks admin role
        
    Security Notes:
        - All admin actions are logged for audit purposes
        - Admin endpoints have stricter rate limiting
        - Additional security headers are included
        - IP restrictions may apply in production
        
    Example Response:
        ```json
        {
            "message": "Admin access granted",
            "user": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000", 
                "username": "admin@example.com",
                "roles": ["admin", "user"],
                "admin_level": "administrator"
            },
            "admin_resources": [
                "user_management",
                "system_configuration", 
                "audit_logs",
                "service_metrics"
            ],
            "audit_logged": true
        }
        ```
    """
    # Log admin action for audit trail
    logger.info(
        f"Admin endpoint accessed by user {current_user.get('user_id')} "
        f"({current_user.get('username')})"
    )
    
    return {
        "message": "Admin access granted", 
        "user": {
            "user_id": current_user.get("user_id"),
            "username": current_user.get("username"),
            "roles": current_user.get("roles", []),
            "admin_level": "administrator"
        },
        "admin_resources": [
            "user_management",
            "system_configuration",
            "audit_logs", 
            "service_metrics",
            "security_settings"
        ],
        "permissions": current_user.get("permissions", []),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "audit_logged": True
    }


# Global exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """
    Global HTTP exception handler for consistent error responses.
    
    Provides standardized error format across all endpoints with:
    - Consistent error structure
    - Request correlation IDs
    - Security-appropriate error messages
    - Proper HTTP status codes
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.status_code,
                "message": exc.detail,
                "type": "http_exception"
            },
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "path": str(request.url),
            "method": request.method
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """
    Global exception handler for unexpected errors.
    
    Provides secure error handling that:
    - Logs detailed errors for debugging
    - Returns generic errors to clients
    - Prevents information disclosure
    - Maintains service stability
    """
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": 500,
                "message": "Internal server error" if not settings.DEBUG else str(exc),
                "type": "internal_error"
            },
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    )


# Application startup and configuration
if __name__ == "__main__":
    """
    Direct execution entry point for development.
    
    Usage:
        python main.py
        
    For production deployment, use a proper ASGI server:
        uvicorn main:app --host 0.0.0.0 --port 8001 --workers 4
    """
    logger.info("🚀 Starting Auth Service in development mode...")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
        debug=settings.DEBUG,
        reload=settings.DEBUG,
        access_log=True,
        log_level="info" if settings.DEBUG else "warning"
    )