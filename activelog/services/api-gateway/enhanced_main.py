#!/usr/bin/env python3
"""
Enhanced API Gateway with Advanced Performance Optimizations
Integrates new connection pooling, caching, and monitoring systems
"""

import sys
sys.path.append('/home/activeloguser/activelog/shared')

from fastapi import FastAPI, Request, HTTPException, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from contextlib import asynccontextmanager
import httpx
import jwt
import time
import json
import uuid
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Set, List
from collections import defaultdict
import asyncio
import hashlib

# Import our enhanced components
from base.enhanced_service import EnhancedService, CircuitBreaker, create_service
from database.connection_pool import init_db_connections, close_db_connections, get_redis_pool, db_health_check
from cache.cache_manager import init_cache, cache_get, cache_set, cache_delete, cached, cache_metrics, cache_health, close_cache

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# JWT Configuration
JWT_SECRET_KEY = "your-secret-key-change-in-production"
JWT_ALGORITHM = "HS256"
SERVICE_TO_SERVICE_KEY = "service-internal-key-change-in-production"

# Security
security = HTTPBearer(auto_error=False)

# Enhanced Rate limiting configuration with Redis backing
RATE_LIMITS = {
    "viewer": {"requests": 100, "window": 3600},
    "user": {"requests": 500, "window": 3600},
    "admin": {"requests": 2000, "window": 3600},
    "service": {"requests": 10000, "window": 3600}
}

# Advanced cache configuration
CACHE_TTL = {
    "default": 300,
    "health": 30,
    "static": 3600,
    "user_profile": 600,
    "search": 180,
    "metadata": 1800,
    "analytics": 900
}

# Service definitions with enhanced configuration
SERVICES = {
    "file-sync": {
        "url": "http://localhost:8000",
        "protected_paths": ["/upload", "/delete", "/sync"],
        "admin_only_paths": ["/admin"],
        "service_auth": True,
        "circuit_breaker": {"failure_threshold": 5, "recovery_timeout": 60}
    },
    "ai-orchestrator": {
        "url": "http://localhost:8001",
        "protected_paths": ["/analyze", "/plugins"],
        "admin_only_paths": ["/admin", "/plugins/manage"],
        "service_auth": True,
        "circuit_breaker": {"failure_threshold": 3, "recovery_timeout": 120}
    },
    "auth": {
        "url": "http://localhost:8002",
        "protected_paths": ["/me", "/change-password", "/logout"],
        "admin_only_paths": ["/users"],
        "service_auth": False,
        "circuit_breaker": {"failure_threshold": 10, "recovery_timeout": 30}
    },
    "metadata": {
        "url": "http://localhost:8003",
        "protected_paths": ["/metadata", "/tags", "/embeddings", "/relationships", "/batch"],
        "admin_only_paths": ["/batch"],
        "service_auth": True,
        "circuit_breaker": {"failure_threshold": 5, "recovery_timeout": 90}
    },
    "backup": {
        "url": "http://localhost:8009",
        "protected_paths": ["/backup", "/backups", "/storage-stats"],
        "admin_only_paths": ["/backup", "/backups", "/storage-stats"],
        "service_auth": False,
        "circuit_breaker": {"failure_threshold": 3, "recovery_timeout": 180}
    },
    "auto-scheduler": {
        "url": "http://localhost:8500",
        "protected_paths": ["/tasks", "/bots", "/reports"],
        "admin_only_paths": ["/tasks", "/bots", "/backups", "/config"],
        "service_auth": True,
        "circuit_breaker": {"failure_threshold": 5, "recovery_timeout": 60}
    }
}

class EnhancedAPIGateway(EnhancedService):
    """Enhanced API Gateway with advanced performance optimizations"""
    
    def __init__(self):
        super().__init__(
            service_name="Enhanced API Gateway",
            port=8088,
            version="3.0.0",
            description="High-performance API Gateway with advanced caching, connection pooling, and monitoring",
            enable_caching=True,
            enable_compression=True,
            enable_monitoring=True,
            cors_origins=["http://localhost:3000", "http://localhost:8088"],
            redis_url="redis://localhost:6379/0"  # Use DB 0 for gateway
        )
        
        # Performance metrics
        self.request_metrics = defaultdict(lambda: defaultdict(int))
        self.error_metrics = defaultdict(lambda: defaultdict(int))
        
        # Circuit breakers for each service
        self.service_circuit_breakers = {}
        for service_name, config in SERVICES.items():
            cb_config = config.get("circuit_breaker", {"failure_threshold": 5, "recovery_timeout": 60})
            self.service_circuit_breakers[service_name] = self.add_circuit_breaker(
                service_name,
                cb_config["failure_threshold"],
                cb_config["recovery_timeout"]
            )
        
        # Request deduplication
        self.pending_requests = {}
        self.dedup_lock = asyncio.Lock()
        
        # Setup routes
        self._setup_gateway_routes()
    
    async def custom_startup(self):
        """Custom startup logic for API Gateway"""
        logger.info("Initializing Enhanced API Gateway...")
        
        # Test Redis connection for rate limiting
        try:
            redis_client = await get_redis_pool('main')
            await redis_client.ping()
            logger.info("Redis connection for rate limiting established")
        except Exception as e:
            logger.warning(f"Redis not available for rate limiting: {e}")
    
    def _setup_gateway_routes(self):
        """Setup API Gateway specific routes"""
        
        @self.app.get("/")
        async def root():
            """Gateway information endpoint"""
            return {
                "gateway": "Enhanced ActiveLog API Gateway",
                "version": "3.0.0",
                "services": list(SERVICES.keys()),
                "features": [
                    "Advanced Connection Pooling",
                    "Multi-layer Caching",
                    "Circuit Breakers",
                    "Request Deduplication",
                    "JWT Authentication",
                    "Role-based Access Control",
                    "Enhanced Rate Limiting",
                    "Performance Monitoring",
                    "Service Discovery"
                ],
                "performance": {
                    "connection_pooling": "Enabled",
                    "caching": "Multi-layer (Memory + Redis)",
                    "compression": "GZip enabled",
                    "monitoring": "Real-time metrics"
                }
            }
        
        @self.app.get("/enhanced-metrics")
        async def get_enhanced_metrics():
            """Get comprehensive gateway metrics"""
            metrics_data = await self.get_metrics()
            
            # Add gateway-specific metrics
            metrics_data.update({
                "gateway_metrics": {
                    "requests": dict(self.request_metrics),
                    "errors": dict(self.error_metrics),
                    "circuit_breakers": {
                        name: {
                            "state": cb.state,
                            "failure_count": cb.failure_count,
                            "last_failure_time": cb.last_failure_time
                        }
                        for name, cb in self.service_circuit_breakers.items()
                    },
                    "pending_requests": len(self.pending_requests)
                }
            })
            
            return metrics_data
        
        @self.app.get("/services")
        @cached(ttl=300, namespace="gateway")  # Cache for 5 minutes
        async def list_services():
            """List all available services with enhanced status"""
            services_info = {}
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                for name, config in SERVICES.items():
                    service_info = {
                        "name": name,
                        "url": config["url"],
                        "status": "unknown",
                        "endpoints": {
                            "base": config["url"],
                            "health": f"{config['url']}/health",
                            "docs": f"{config['url']}/docs"
                        },
                        "configuration": {
                            "protected_paths": config.get("protected_paths", []),
                            "admin_only_paths": config.get("admin_only_paths", []),
                            "requires_service_auth": config.get("service_auth", False),
                            "circuit_breaker": config.get("circuit_breaker", {})
                        }
                    }
                    
                    # Check service health with circuit breaker
                    cb = self.service_circuit_breakers.get(name)
                    if cb and cb.state == 'OPEN':
                        service_info["status"] = "circuit_breaker_open"
                        service_info["circuit_breaker_state"] = cb.state
                    else:
                        try:
                            headers = {}
                            if config.get("service_auth", False):
                                headers["X-Service-Auth"] = SERVICE_TO_SERVICE_KEY
                            
                            async with cb:
                                resp = await client.get(
                                    f"{config['url']}/health",
                                    headers=headers,
                                    timeout=2.0
                                )
                                service_info["status"] = "healthy" if resp.status_code == 200 else "unhealthy"
                                service_info["health_details"] = resp.json() if resp.text else {"status": "healthy"}
                                
                        except Exception as e:
                            service_info["status"] = "unreachable"
                            service_info["error"] = str(e)
                    
                    services_info[name] = service_info
            
            return {
                "gateway": "Enhanced ActiveLog API Gateway",
                "version": "3.0.0",
                "timestamp": datetime.utcnow().isoformat(),
                "services": services_info
            }
        
        @self.app.middleware("http")
        async def enhanced_gateway_middleware(request: Request, call_next):
            """Enhanced middleware with performance optimizations"""
            start_time = time.time()
            request_id = f"{int(time.time())}-{id(request)}"
            request.state.request_id = request_id
            
            # Skip middleware for gateway endpoints
            if self._is_gateway_endpoint(request.url.path):
                response = await call_next(request)
                self._add_response_headers(response, request_id, time.time() - start_time)
                return response
            
            # Parse service and path
            service, path = self._parse_service_path(request.url.path)
            if not service:
                return JSONResponse(
                    status_code=400,
                    content={"error": "Invalid request path. Expected format: /api/{service}/{path}"}
                )
            
            # Check if service exists
            if service not in SERVICES:
                self._record_metrics(service, request.method, path, 404, time.time() - start_time)
                return JSONResponse(
                    status_code=404,
                    content={"error": f"Service {service} not found"}
                )
            
            # Authentication and authorization
            current_user = await self._authenticate_request(request, service, path)
            if isinstance(current_user, JSONResponse):  # Error response
                return current_user
            
            # Rate limiting
            rate_limit_response = await self._check_rate_limits(current_user, service, start_time, request, path)
            if rate_limit_response:
                return rate_limit_response
            
            # Add user context headers
            self._add_user_headers(request, current_user)
            
            # Process request
            response = await call_next(request)
            
            # Record metrics and add headers
            duration = time.time() - start_time
            user_id = current_user["id"] if isinstance(current_user, dict) and current_user else None
            self._record_metrics(service, request.method, path, response.status_code, duration, user_id)
            self._add_response_headers(response, request_id, duration)
            
            return response
        
        @self.app.api_route("/api/{service}/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
        async def enhanced_proxy(service: str, path: str, request: Request):
            """Enhanced proxy with advanced caching and performance optimizations"""
            
            if service not in SERVICES:
                raise HTTPException(status_code=404, detail=f"Service {service} not found")
            
            # Circuit breaker check
            cb = self.service_circuit_breakers.get(service)
            if cb and cb.state == 'OPEN':
                raise HTTPException(
                    status_code=503,
                    content={
                        "error": f"Service {service} is temporarily unavailable",
                        "circuit_state": cb.state,
                        "retry_after": cb.recovery_timeout
                    }
                )
            
            # Generate cache key
            cache_key = await self._generate_cache_key(request, service, path)
            
            # Check cache for GET requests
            if request.method == "GET":
                cached_response = await cache_get(cache_key, namespace="gateway")
                if cached_response:
                    logger.info(f"Cache hit for {service}/{path}")
                    return JSONResponse(**cached_response)
            
            # Request deduplication for identical concurrent requests
            dedup_key = await self._generate_dedup_key(request, service, path)
            
            async def make_service_request():
                """Make the actual service request"""
                return await self._execute_service_request(service, path, request, cb)
            
            # Execute with deduplication
            async with self.dedup_lock:
                if dedup_key in self.pending_requests:
                    # Wait for existing request
                    logger.info(f"Request deduplication: waiting for {service}/{path}")
                    return await self.pending_requests[dedup_key]
                else:
                    # Create new request
                    task = asyncio.create_task(make_service_request())
                    self.pending_requests[dedup_key] = task
            
            try:
                result = await task
                
                # Cache successful GET responses
                if (request.method == "GET" and 
                    result.status_code == 200 and
                    self._is_cacheable(service, path)):
                    
                    ttl = self._get_cache_ttl(service, path)
                    cache_data = {
                        "status_code": result.status_code,
                        "content": result.body.decode() if hasattr(result, 'body') else {},
                        "headers": dict(result.headers) if hasattr(result, 'headers') else {}
                    }
                    
                    await cache_set(cache_key, cache_data, ttl, namespace="gateway")
                    logger.info(f"Cached response for {service}/{path} (TTL: {ttl}s)")
                
                return result
                
            finally:
                # Clean up deduplication
                async with self.dedup_lock:
                    if dedup_key in self.pending_requests:
                        del self.pending_requests[dedup_key]
        
    def _is_gateway_endpoint(self, path: str) -> bool:
        """Check if path is a gateway-specific endpoint"""
        gateway_paths = [
            "/", "/health", "/metrics", "/enhanced-metrics", "/services", 
            "/docs", "/redoc", "/openapi.json", "/ready"
        ]
        return path in gateway_paths or path.startswith("/docs/")
    
    def _parse_service_path(self, path: str) -> tuple:
        """Parse service and path from URL"""
        path_parts = path.strip("/").split("/", 2)
        if len(path_parts) < 2 or path_parts[0] != "api":
            return None, None
        
        service = path_parts[1]
        service_path = "/" + (path_parts[2] if len(path_parts) > 2 else "")
        return service, service_path
    
    async def _authenticate_request(self, request: Request, service: str, path: str):
        """Enhanced authentication with caching"""
        # Check for service-to-service authentication
        service_auth_header = request.headers.get("X-Service-Auth")
        if service_auth_header and service_auth_header == SERVICE_TO_SERVICE_KEY:
            return {"type": "service", "id": "service"}
        
        # Check if path requires authentication
        if not self._is_protected_path(service, path):
            return None
        
        # Get JWT token
        auth_header = request.headers.get("authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"error": "Authentication required"}
            )
        
        token = auth_header.split(" ", 1)[1]
        
        # Try to get user from cache first
        user_cache_key = f"user:{hashlib.md5(token.encode()).hexdigest()}"
        cached_user = await cache_get(user_cache_key, namespace="auth")
        
        if cached_user:
            current_user = cached_user
        else:
            # Verify token and get user
            try:
                payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
                user_id = payload.get("sub")
                
                if not user_id:
                    return JSONResponse(status_code=401, content={"error": "Invalid token"})
                
                # Get user details (with caching)
                current_user = await self._get_user_details(user_id)
                if not current_user:
                    current_user = {
                        "id": user_id,
                        "username": payload.get("username"),
                        "role": payload.get("role", "user"),
                        "is_active": True
                    }
                
                # Cache user for 10 minutes
                await cache_set(user_cache_key, current_user, 600, namespace="auth")
                
            except jwt.ExpiredSignatureError:
                return JSONResponse(status_code=401, content={"error": "Token expired"})
            except jwt.InvalidTokenError:
                return JSONResponse(status_code=401, content={"error": "Invalid token"})
        
        # Check admin-only paths
        if self._is_admin_only_path(service, path) and current_user.get("role") != "admin":
            return JSONResponse(
                status_code=403,
                content={"error": "Admin access required"}
            )
        
        return current_user
    
    async def _get_user_details(self, user_id: str):
        """Get user details with caching"""
        cache_key = f"user_details:{user_id}"
        cached_details = await cache_get(cache_key, namespace="auth")
        
        if cached_details:
            return cached_details
        
        # Fetch from auth service
        try:
            async with httpx.AsyncClient() as client:
                headers = {"X-Service-Auth": SERVICE_TO_SERVICE_KEY}
                response = await client.get(
                    f"{SERVICES['auth']['url']}/auth/users/{user_id}",
                    headers=headers,
                    timeout=5.0
                )
                if response.status_code == 200:
                    user_details = response.json()
                    # Cache for 5 minutes
                    await cache_set(cache_key, user_details, 300, namespace="auth")
                    return user_details
        except Exception as e:
            logger.error(f"Error fetching user details: {e}")
        
        return None
    
    async def _check_rate_limits(self, current_user, service, start_time, request, path):
        """Enhanced rate limiting with Redis"""
        if isinstance(current_user, dict):
            user_id = current_user["id"]
            user_role = current_user.get("role", "user")
        else:
            user_id = "anonymous"
            user_role = "viewer"
        
        if await self._is_rate_limited(user_id, user_role):
            duration = time.time() - start_time
            self._record_metrics(service, request.method, path, 429, duration, user_id)
            return JSONResponse(
                status_code=429,
                content={"error": "Rate limit exceeded", "retry_after": 3600}
            )
        
        return None
    
    async def _is_rate_limited(self, user_id: str, user_role: str) -> bool:
        """Check rate limits using Redis"""
        limits = RATE_LIMITS.get(user_role, RATE_LIMITS["user"])
        current_time = int(time.time())
        window_start = current_time - limits["window"]
        
        try:
            redis_client = await get_redis_pool('main')
            key = f"rate_limit:{user_id}"
            
            # Remove old entries
            await redis_client.zremrangebyscore(key, 0, window_start)
            
            # Count current requests
            current_count = await redis_client.zcard(key)
            
            if current_count >= limits["requests"]:
                return True
            
            # Add current request
            await redis_client.zadd(key, {str(current_time): current_time})
            await redis_client.expire(key, limits["window"])
            
            return False
            
        except Exception as e:
            logger.error(f"Redis rate limiting error: {e}")
            return False  # Fail open
    
    async def _generate_cache_key(self, request: Request, service: str, path: str) -> str:
        """Generate cache key for request"""
        query_string = str(request.query_params)
        user_id = request.headers.get("x-user-id", "")
        key_data = f"{service}:{request.method}:{path}:{query_string}:{user_id}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    async def _generate_dedup_key(self, request: Request, service: str, path: str) -> str:
        """Generate deduplication key for request"""
        body = await request.body()
        body_hash = hashlib.md5(body).hexdigest() if body else ""
        query_string = str(request.query_params)
        key_data = f"{service}:{request.method}:{path}:{query_string}:{body_hash}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    async def _execute_service_request(self, service: str, path: str, request: Request, circuit_breaker):
        """Execute service request with circuit breaker"""
        service_config = SERVICES[service]
        service_url = service_config["url"]
        
        # Build target URL
        if service == "auth":
            url = f"{service_url}/auth/{path}"
        else:
            url = f"{service_url}/{path}"
        
        # Prepare headers
        headers = {k: v for k, v in request.headers.items() if k.lower() not in ['host', 'content-length']}
        
        if service_config.get("service_auth", False):
            headers["X-Service-Auth"] = SERVICE_TO_SERVICE_KEY
        
        headers["X-Request-ID"] = str(uuid.uuid4())
        headers["X-Gateway-Timestamp"] = datetime.utcnow().isoformat()
        
        body = await request.body()
        
        try:
            async with circuit_breaker:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.request(
                        method=request.method,
                        url=url,
                        content=body if body else None,
                        headers=headers,
                        params=request.query_params
                    )
                    
                    return JSONResponse(
                        status_code=response.status_code,
                        content=response.json() if response.text else {},
                        headers={k: v for k, v in response.headers.items() 
                               if k.lower() not in ['content-length', 'transfer-encoding', 'connection']}
                    )
                    
        except httpx.TimeoutException:
            logger.error(f"Timeout calling service {service} at {url}")
            raise HTTPException(status_code=504, detail=f"Service {service} timeout")
        except httpx.RequestError as e:
            logger.error(f"Error calling service {service}: {e}")
            raise HTTPException(status_code=502, detail=f"Service {service} unavailable")
    
    def _is_protected_path(self, service: str, path: str) -> bool:
        """Check if path requires authentication"""
        service_config = SERVICES.get(service, {})
        protected_paths = service_config.get("protected_paths", [])
        normalized_path = "/" + path.strip("/")
        
        for protected_path in protected_paths:
            if normalized_path.startswith("/" + protected_path.strip("/")):
                return True
        return False
    
    def _is_admin_only_path(self, service: str, path: str) -> bool:
        """Check if path requires admin role"""
        service_config = SERVICES.get(service, {})
        admin_paths = service_config.get("admin_only_paths", [])
        normalized_path = "/" + path.strip("/")
        
        for admin_path in admin_paths:
            if normalized_path.startswith("/" + admin_path.strip("/")):
                return True
        return False
    
    def _is_cacheable(self, service: str, path: str) -> bool:
        """Determine if request should be cached"""
        cacheable_patterns = ["/health", "/docs", "/openapi.json", "/search", "/list", "/profile", "/me"]
        return any(pattern in path for pattern in cacheable_patterns)
    
    def _get_cache_ttl(self, service: str, path: str) -> int:
        """Get TTL for specific path"""
        if "/health" in path:
            return CACHE_TTL["health"]
        elif any(pattern in path for pattern in ["/docs", "/openapi.json"]):
            return CACHE_TTL["static"]
        elif "search" in path:
            return CACHE_TTL["search"]
        elif service == "metadata":
            return CACHE_TTL["metadata"]
        elif "profile" in path or "me" in path:
            return CACHE_TTL["user_profile"]
        else:
            return CACHE_TTL["default"]
    
    def _add_user_headers(self, request: Request, current_user):
        """Add user context headers for downstream services"""
        if isinstance(current_user, dict) and current_user:
            # Add user info as headers
            request.headers.__dict__["_list"].extend([
                (b"x-user-id", str(current_user.get("id", "")).encode()),
                (b"x-user-role", str(current_user.get("role", "")).encode()),
                (b"x-user-username", str(current_user.get("username", "")).encode())
            ])
    
    def _record_metrics(self, service: str, method: str, path: str, status_code: int, duration: float, user_id: str = None):
        """Record request metrics"""
        self.request_metrics[service]["total"] += 1
        self.request_metrics[service][f"method_{method}"] += 1
        self.request_metrics[service][f"status_{status_code}"] += 1
        
        if status_code >= 400:
            self.error_metrics[service]["total"] += 1
            self.error_metrics[service][f"status_{status_code}"] += 1
        
        # Update base service metrics
        self.metrics["requests"] += 1
        if status_code >= 400:
            self.metrics["errors"] += 1
        self.metrics["total_time"] += duration
        
        logger.info(
            f"REQUEST - Service: {service}, Method: {method}, Path: {path}, "
            f"Status: {status_code}, Duration: {duration:.3f}s, User: {user_id or 'anonymous'}"
        )
    
    def _add_response_headers(self, response, request_id: str, duration: float):
        """Add response headers"""
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{duration:.3f}s"
        response.headers["X-Gateway"] = "Enhanced-ActiveLog-Gateway"
        response.headers["X-Gateway-Version"] = "3.0.0"

# Create enhanced gateway instance
gateway = EnhancedAPIGateway()
app = gateway.app

if __name__ == "__main__":
    gateway.run(host="0.0.0.0", port=8088)