#!/usr/bin/env python3
"""
Enhanced FastAPI Service Base Class
Provides optimized startup, database pooling, caching, and monitoring for all ActiveLog services
"""

import asyncio
import os
import sys
import time
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional, List
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
import uvicorn

# Add shared modules to path
sys.path.append('/home/activeloguser/activelog/shared')

from database.connection_pool import init_db_connections, close_db_connections, db_health_check, db_stats
from cache.cache_manager import init_cache, cache_health, cache_metrics, close_cache

logger = logging.getLogger(__name__)

class PerformanceMiddleware:
    """Middleware for performance monitoring and optimization"""
    
    def __init__(self, app: FastAPI):
        self.app = app
        
    async def __call__(self, request: Request, call_next):
        start_time = time.time()
        
        # Add request ID for tracing
        request_id = f"{int(time.time())}-{id(request)}"
        request.state.request_id = request_id
        
        try:
            response = await call_next(request)
            
            # Add performance headers
            process_time = time.time() - start_time
            response.headers["X-Process-Time"] = str(process_time)
            response.headers["X-Request-ID"] = request_id
            
            # Log slow requests
            if process_time > 1.0:  # Log requests taking > 1 second
                logger.warning(f"Slow request {request_id}: {request.method} {request.url.path} took {process_time:.2f}s")
            
            return response
            
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(f"Request {request_id} failed after {process_time:.2f}s: {e}")
            
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "request_id": request_id,
                    "process_time": process_time
                }
            )

class CircuitBreaker:
    """Circuit breaker for external service calls"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60, expected_exception=Exception):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
    
    async def __aenter__(self):
        if self.state == 'OPEN':
            if self.last_failure_time and time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = 'HALF_OPEN'
            else:
                raise HTTPException(status_code=503, detail="Circuit breaker is OPEN")
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            # Success
            if self.state == 'HALF_OPEN':
                self.state = 'CLOSED'
                self.failure_count = 0
        elif issubclass(exc_type, self.expected_exception):
            # Expected failure
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = 'OPEN'
        
        return False  # Don't suppress exceptions

class EnhancedService:
    """Enhanced service base class with performance optimizations"""
    
    def __init__(
        self,
        service_name: str,
        port: int,
        version: str = "1.0.0",
        description: str = "",
        enable_caching: bool = True,
        enable_compression: bool = True,
        enable_monitoring: bool = True,
        cors_origins: List[str] = None,
        redis_url: str = None
    ):
        self.service_name = service_name
        self.port = port
        self.version = version
        self.description = description
        self.enable_caching = enable_caching
        self.enable_compression = enable_compression
        self.enable_monitoring = enable_monitoring
        self.redis_url = redis_url or f"redis://localhost:6379/{self._get_redis_db()}"
        
        # Performance metrics
        self.metrics = {
            'requests': 0,
            'errors': 0,
            'total_time': 0.0,
            'startup_time': 0.0
        }
        
        # Circuit breakers for external services
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        
        # Create FastAPI app with lifespan management
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            # Startup
            startup_start = time.time()
            await self.startup()
            self.metrics['startup_time'] = time.time() - startup_start
            logger.info(f"{service_name} started in {self.metrics['startup_time']:.2f}s")
            
            yield
            
            # Shutdown
            await self.shutdown()
            logger.info(f"{service_name} shut down gracefully")
        
        self.app = FastAPI(
            title=service_name,
            description=description,
            version=version,
            lifespan=lifespan
        )
        
        # Add middleware
        self._setup_middleware(cors_origins or ["*"])
        
        # Add default routes
        self._setup_default_routes()
    
    def _get_redis_db(self) -> int:
        """Get Redis database number based on service port"""
        # Use port-based DB selection to avoid conflicts
        return (self.port - 8000) % 16  # Redis has 16 databases by default
    
    def _setup_middleware(self, cors_origins: List[str]):
        """Setup middleware stack"""
        
        # CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Compression
        if self.enable_compression:
            self.app.add_middleware(GZipMiddleware, minimum_size=1000)
        
        # Performance monitoring
        if self.enable_monitoring:
            self.app.middleware("http")(PerformanceMiddleware(self.app))
    
    def _setup_default_routes(self):
        """Setup default service routes"""
        
        @self.app.get("/health")
        async def health_check():
            """Comprehensive health check"""
            start_time = time.time()
            
            health_status = {
                "service": self.service_name,
                "version": self.version,
                "status": "healthy",
                "timestamp": time.time(),
                "uptime": time.time() - self.metrics.get('startup_complete', time.time()),
                "checks": {}
            }
            
            try:
                # Database health check
                db_health = await db_health_check()
                health_status["checks"]["database"] = {
                    "status": "healthy" if all(db_health.values()) else "unhealthy",
                    "details": db_health
                }
            except Exception as e:
                health_status["checks"]["database"] = {
                    "status": "error",
                    "error": str(e)
                }
            
            # Cache health check
            if self.enable_caching:
                try:
                    cache_health_status = await cache_health()
                    health_status["checks"]["cache"] = {
                        "status": "healthy" if all(cache_health_status.values()) else "unhealthy",
                        "details": cache_health_status
                    }
                except Exception as e:
                    health_status["checks"]["cache"] = {
                        "status": "error",
                        "error": str(e)
                    }
            
            # Determine overall status
            check_statuses = [check["status"] for check in health_status["checks"].values()]
            if "error" in check_statuses or "unhealthy" in check_statuses:
                health_status["status"] = "unhealthy"
            
            health_status["response_time"] = time.time() - start_time
            
            status_code = 200 if health_status["status"] == "healthy" else 503
            return JSONResponse(content=health_status, status_code=status_code)
        
        @self.app.get("/metrics")
        async def get_metrics():
            """Get service performance metrics"""
            metrics_data = {
                "service": self.service_name,
                "version": self.version,
                "metrics": self.metrics.copy(),
                "timestamp": time.time()
            }
            
            # Add database metrics
            try:
                metrics_data["database"] = await db_stats()
            except Exception as e:
                metrics_data["database"] = {"error": str(e)}
            
            # Add cache metrics
            if self.enable_caching:
                try:
                    metrics_data["cache"] = await cache_metrics()
                except Exception as e:
                    metrics_data["cache"] = {"error": str(e)}
            
            # Add circuit breaker status
            metrics_data["circuit_breakers"] = {
                name: {
                    "state": cb.state,
                    "failure_count": cb.failure_count,
                    "last_failure": cb.last_failure_time
                }
                for name, cb in self.circuit_breakers.items()
            }
            
            return metrics_data
        
        @self.app.get("/ready")
        async def readiness_check():
            """Kubernetes-style readiness check"""
            # Simple check that service is ready to serve traffic
            return {"status": "ready", "service": self.service_name, "timestamp": time.time()}
        
        @self.app.get("/")
        async def root():
            """Root endpoint with service information"""
            return {
                "service": self.service_name,
                "version": self.version,
                "description": self.description,
                "docs": f"http://localhost:{self.port}/docs",
                "health": f"http://localhost:{self.port}/health",
                "metrics": f"http://localhost:{self.port}/metrics"
            }
    
    async def startup(self):
        """Service startup initialization"""
        logger.info(f"Starting {self.service_name} v{self.version}")
        
        try:
            # Initialize database connections
            logger.info("Initializing database connections...")
            await init_db_connections()
            
            # Initialize cache if enabled
            if self.enable_caching:
                logger.info("Initializing cache...")
                await init_cache(self.redis_url)
            
            # Custom startup logic
            await self.custom_startup()
            
            self.metrics['startup_complete'] = time.time()
            logger.info(f"{self.service_name} startup completed")
            
        except Exception as e:
            logger.error(f"Startup failed: {e}")
            raise
    
    async def shutdown(self):
        """Service shutdown cleanup"""
        logger.info(f"Shutting down {self.service_name}")
        
        try:
            # Custom shutdown logic
            await self.custom_shutdown()
            
            # Close cache connections
            if self.enable_caching:
                await close_cache()
            
            # Close database connections
            await close_db_connections()
            
        except Exception as e:
            logger.error(f"Shutdown error: {e}")
    
    async def custom_startup(self):
        """Override this method for custom startup logic"""
        pass
    
    async def custom_shutdown(self):
        """Override this method for custom shutdown logic"""
        pass
    
    def add_circuit_breaker(self, name: str, failure_threshold: int = 5, recovery_timeout: int = 60):
        """Add a circuit breaker for external service calls"""
        self.circuit_breakers[name] = CircuitBreaker(failure_threshold, recovery_timeout)
        return self.circuit_breakers[name]
    
    def get_circuit_breaker(self, name: str) -> CircuitBreaker:
        """Get a circuit breaker by name"""
        if name not in self.circuit_breakers:
            self.circuit_breakers[name] = CircuitBreaker()
        return self.circuit_breakers[name]
    
    def run(self, host: str = "0.0.0.0", **kwargs):
        """Run the service with optimized settings"""
        
        # Default optimized uvicorn settings
        default_kwargs = {
            "host": host,
            "port": self.port,
            "log_level": "info",
            "access_log": False,  # Reduce I/O overhead
            "server_header": False,
            "date_header": False,
            "loop": "uvloop",  # Use uvloop for better performance
            "http": "httptools",  # Use httptools for better HTTP parsing
            "ws_max_size": 16 * 1024 * 1024,  # 16MB WebSocket message size
            "ws_ping_interval": 20,
            "ws_ping_timeout": 10,
            "timeout_keep_alive": 75,
            "limit_concurrency": 1000,
            "limit_max_requests": 10000,
        }
        
        # Override with user-provided kwargs
        default_kwargs.update(kwargs)
        
        logger.info(f"Starting {self.service_name} on {host}:{self.port}")
        
        try:
            uvicorn.run(self.app, **default_kwargs)
        except KeyboardInterrupt:
            logger.info("Service stopped by user")
        except Exception as e:
            logger.error(f"Service crashed: {e}")
            raise

# Utility functions for easy service creation
def create_service(
    name: str,
    port: int,
    version: str = "1.0.0",
    description: str = "",
    **kwargs
) -> EnhancedService:
    """Create an enhanced service instance"""
    return EnhancedService(name, port, version, description, **kwargs)

def quick_service(name: str, port: int) -> EnhancedService:
    """Create a service with minimal configuration"""
    return EnhancedService(
        service_name=name,
        port=port,
        description=f"{name} service for ActiveLog platform"
    )