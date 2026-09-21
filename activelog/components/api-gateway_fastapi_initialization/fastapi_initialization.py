"""
fastapi_initialization component extracted from api-gateway
Reusability Score: 9.5

Production-ready FastAPI initialization component with comprehensive middleware,
authentication, caching, rate limiting, and monitoring capabilities.
"""

from fastapi import FastAPI, Request, HTTPException, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from contextlib import asynccontextmanager
import httpx
import jwt
import time
import json
import uuid
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Set, List, Callable
from collections import defaultdict
import asyncio
import redis.asyncio as redis
import hashlib
from threading import Lock

logger = logging.getLogger(__name__)

class FastAPIInitializationComponent:
    """
    Production-ready FastAPI initialization component with:
    - JWT Authentication & Authorization
    - Role-based Access Control
    - Rate Limiting (Redis + in-memory fallback)  
    - Request Caching with TTL
    - Circuit Breaker Pattern
    - Comprehensive Metrics & Logging
    - CORS Configuration
    - Service-to-Service Authentication
    """
    
    def __init__(self, 
                 service_name: str,
                 service_port: int,
                 jwt_secret_key: str = "your-secret-key-change-in-production",
                 service_to_service_key: str = "service-internal-key-change-in-production",
                 redis_host: str = "localhost",
                 redis_port: int = 6379,
                 enable_cors: bool = True,
                 cors_origins: List[str] = None,
                 rate_limits: Dict[str, Dict[str, int]] = None,
                 cache_ttl: Dict[str, int] = None,
                 circuit_breaker_config: Dict[str, int] = None):
        
        self.service_name = service_name
        self.service_port = service_port
        self.jwt_secret_key = jwt_secret_key
        self.service_to_service_key = service_to_service_key
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.enable_cors = enable_cors
        
        # Default configurations
        self.cors_origins = cors_origins or [f"http://localhost:{service_port}", "http://localhost:3000"]
        
        self.rate_limits = rate_limits or {
            "viewer": {"requests": 100, "window": 3600},
            "user": {"requests": 500, "window": 3600},
            "admin": {"requests": 2000, "window": 3600},
            "service": {"requests": 10000, "window": 3600}
        }
        
        self.cache_ttl = cache_ttl or {
            "default": 300,
            "health": 30,
            "static": 3600,
            "user_profile": 600,
            "search": 180
        }
        
        circuit_config = circuit_breaker_config or {"failure_threshold": 5, "timeout": 60}
        
        # Initialize components
        self.redis_client = None
        self.security = HTTPBearer(auto_error=False)
        self.rate_limiter = RateLimitService(self.rate_limits)
        self.circuit_breaker = CircuitBreaker(**circuit_config)
        self.cache_service = CacheService(self.cache_ttl)
        self.metrics_service = MetricsService()
        self.auth_service = AuthenticationService(
            self.jwt_secret_key, 
            self.service_to_service_key
        )
        
        # Metrics storage
        self.request_metrics = defaultdict(lambda: defaultdict(int))
        self.error_metrics = defaultdict(lambda: defaultdict(int))

    async def init_redis(self):
        """Initialize Redis connection"""
        try:
            self.redis_client = redis.Redis(
                host=self.redis_host, 
                port=self.redis_port, 
                decode_responses=True
            )
            await self.redis_client.ping()
            logger.info("Redis connection established")
            
            # Share Redis client with components
            self.rate_limiter.redis_client = self.redis_client
            self.cache_service.redis_client = self.redis_client
            
        except Exception as e:
            logger.warning(f"Redis not available: {e}. Using in-memory storage.")
            self.redis_client = None

    @asynccontextmanager
    async def lifespan(self, app: FastAPI):
        """Application lifespan manager"""
        # Startup
        await self.init_redis()
        yield
        # Shutdown
        if self.redis_client:
            await self.redis_client.aclose()

    def create_app(self, 
                   title: str = None,
                   description: str = None,
                   version: str = "1.0.0",
                   docs_url: str = "/docs",
                   redoc_url: str = "/redoc") -> FastAPI:
        """Create and configure FastAPI application"""
        
        app = FastAPI(
            title=title or f"{self.service_name} API",
            description=description or f"Secure API for {self.service_name} with authentication and monitoring",
            version=version,
            lifespan=self.lifespan,
            docs_url=docs_url,
            redoc_url=redoc_url
        )

        # Add CORS middleware
        if self.enable_cors:
            app.add_middleware(
                CORSMiddleware,
                allow_origins=self.cors_origins,
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )

        # Add authentication and rate limiting middleware
        app.middleware("http")(self._auth_middleware)

        # Add standard endpoints
        self._add_standard_endpoints(app)

        return app

    async def _auth_middleware(self, request: Request, call_next):
        """Authentication and rate limiting middleware"""
        start_time = time.time()
        
        # Skip middleware for standard endpoints
        skip_paths = ["/", "/health", "/metrics", "/docs", "/redoc", "/openapi.json"]
        if request.url.path in skip_paths:
            response = await call_next(request)
            return response
        
        # Handle authentication for protected paths
        current_user = None
        service_auth_header = request.headers.get("X-Service-Auth")
        is_service_request = (service_auth_header and 
                            self.auth_service.verify_service_token(service_auth_header))
        
        # Get user from JWT token if present
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer ") and not is_service_request:
            token = auth_header.split(" ", 1)[1]
            payload = self.auth_service.verify_jwt_token(token)
            
            if payload:
                user_id = payload.get("sub")
                current_user = {
                    "id": user_id,
                    "username": payload.get("username"),
                    "role": payload.get("role", "user"),
                    "is_active": True
                }
                
                # Rate limiting for authenticated users
                user_role = current_user.get("role", "user")
                if await self.rate_limiter.is_rate_limited(current_user["id"], user_role):
                    duration = time.time() - start_time
                    self.metrics_service.record_request(
                        "api", request.method, request.url.path, 429, duration, current_user.get("id")
                    )
                    return JSONResponse(
                        status_code=429,
                        content={"error": "Rate limit exceeded", "retry_after": 3600}
                    )
        
        # Add user context to request headers
        if current_user:
            request.headers.__dict__["_list"].extend([
                (b"x-user-id", current_user["id"].encode()),
                (b"x-user-role", current_user["role"].encode()),
                (b"x-user-username", current_user.get("username", "").encode())
            ])
        
        # Process request
        response = await call_next(request)
        
        # Record metrics
        duration = time.time() - start_time
        user_id = current_user["id"] if current_user else None
        self.metrics_service.record_request(
            "api", request.method, request.url.path, response.status_code, duration, user_id
        )
        
        # Add response headers
        response.headers["X-Request-ID"] = str(uuid.uuid4())
        response.headers["X-Response-Time"] = f"{duration:.3f}s"
        
        return response

    def _add_standard_endpoints(self, app: FastAPI):
        """Add standard health, metrics, and info endpoints"""
        
        @app.get("/")
        async def root():
            return {
                "service": self.service_name,
                "version": "1.0.0",
                "status": "running",
                "features": [
                    "JWT Authentication",
                    "Rate Limiting", 
                    "Request Caching",
                    "Circuit Breaker",
                    "Metrics Collection"
                ]
            }

        @app.get("/health")
        async def health_check():
            health = {
                "service": self.service_name,
                "status": "healthy", 
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Check Redis
            redis_status = "not_configured"
            if self.redis_client:
                try:
                    await self.redis_client.ping()
                    redis_status = "healthy"
                except:
                    redis_status = "unhealthy"
            
            health["redis"] = redis_status
            return health

        @app.get("/metrics")
        async def get_metrics(current_user: Dict[str, Any] = Depends(self.require_role("admin"))):
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "request_metrics": dict(self.request_metrics),
                "error_metrics": dict(self.error_metrics),
                "rate_limits": self.rate_limits,
                "cache_stats": self.cache_service.cache_stats
            }

    def get_current_user(self) -> Callable:
        """Dependency to get current authenticated user"""
        async def _get_current_user(credentials: HTTPAuthorizationCredentials = Depends(self.security)) -> Optional[Dict[str, Any]]:
            if not credentials:
                return None
            
            token = credentials.credentials
            payload = self.auth_service.verify_jwt_token(token)
            
            if not payload:
                return None
            
            user_id = payload.get("sub")
            if not user_id:
                return None
            
            return {
                "id": user_id,
                "username": payload.get("username"),
                "role": payload.get("role", "user"),
                "is_active": True
            }
        
        return _get_current_user

    def require_role(self, required_role: str) -> Callable:
        """Dependency to require specific role"""
        async def role_checker(current_user: Dict[str, Any] = Depends(self.get_current_user())):
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            role_hierarchy = {"viewer": 1, "user": 2, "admin": 3}
            required_level = role_hierarchy.get(required_role, 0)
            user_level = role_hierarchy.get(current_user.get("role"), 0)
            
            if user_level < required_level:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions. Required role: {required_role}"
                )
            
            return current_user
        
        return role_checker

    def run(self, host: str = "0.0.0.0", port: int = None, **uvicorn_kwargs):
        """Run the FastAPI application"""
        import uvicorn
        
        port = port or self.service_port
        uvicorn.run(
            self.create_app(),
            host=host,
            port=port,
            **uvicorn_kwargs
        )


class AuthenticationService:
    """JWT and service authentication"""
    
    def __init__(self, jwt_secret: str, service_key: str, algorithm: str = "HS256"):
        self.jwt_secret = jwt_secret
        self.service_key = service_key
        self.algorithm = algorithm
    
    def verify_jwt_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token and return payload"""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"JWT validation error: {e}")
            return None
    
    def verify_service_token(self, token: str) -> bool:
        """Verify service-to-service authentication token"""
        return token == self.service_key


class CacheService:
    """Request caching with Redis and in-memory fallback"""
    
    def __init__(self, cache_ttl: Dict[str, int]):
        self.cache_ttl = cache_ttl
        self.in_memory_cache = {}
        self.cache_stats = {"hits": 0, "misses": 0, "sets": 0}
        self.redis_client = None
    
    def _generate_cache_key(self, method: str, path: str, query_params: str = "", user_id: str = None) -> str:
        """Generate cache key for request"""
        key_data = f"{method}:{path}:{query_params}"
        if user_id:
            key_data += f":user:{user_id}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    async def get_cached_response(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached response"""
        if self.redis_client:
            try:
                cached = await self.redis_client.get(f"cache:{cache_key}")
                if cached:
                    self.cache_stats["hits"] += 1
                    return json.loads(cached)
            except Exception as e:
                logger.warning(f"Redis cache get error: {e}")
        
        # Fallback to in-memory cache
        if cache_key in self.in_memory_cache:
            cached_data, expires_at = self.in_memory_cache[cache_key]
            if time.time() < expires_at:
                self.cache_stats["hits"] += 1
                return cached_data
            else:
                del self.in_memory_cache[cache_key]
        
        self.cache_stats["misses"] += 1
        return None
    
    async def set_cached_response(self, cache_key: str, response_data: Dict[str, Any], ttl: int):
        """Cache response"""
        cache_data = {
            "status_code": response_data["status_code"],
            "content": response_data["content"],
            "headers": response_data.get("headers", {}),
            "cached_at": datetime.utcnow().isoformat()
        }
        
        if self.redis_client:
            try:
                await self.redis_client.setex(
                    f"cache:{cache_key}",
                    ttl,
                    json.dumps(cache_data, default=str)
                )
                self.cache_stats["sets"] += 1
                return
            except Exception as e:
                logger.warning(f"Redis cache set error: {e}")
        
        # Fallback to in-memory cache
        expires_at = time.time() + ttl
        self.in_memory_cache[cache_key] = (cache_data, expires_at)
        self.cache_stats["sets"] += 1


class RateLimitService:
    """Rate limiting with Redis and in-memory fallback"""
    
    def __init__(self, rate_limits: Dict[str, Dict[str, int]]):
        self.rate_limits = rate_limits
        self.in_memory_store = defaultdict(lambda: defaultdict(list))
        self.redis_client = None
    
    async def is_rate_limited(self, user_id: str, user_role: str) -> bool:
        """Check if user is rate limited"""
        limits = self.rate_limits.get(user_role, self.rate_limits["user"])
        current_time = int(time.time())
        window_start = current_time - limits["window"]
        
        if self.redis_client:
            return await self._check_redis_rate_limit(user_id, limits, current_time, window_start)
        else:
            return await self._check_memory_rate_limit(user_id, limits, current_time, window_start)
    
    async def _check_redis_rate_limit(self, user_id: str, limits: Dict, current_time: int, window_start: int) -> bool:
        """Redis-based rate limiting"""
        key = f"rate_limit:{user_id}"
        try:
            await self.redis_client.zremrangebyscore(key, 0, window_start)
            current_count = await self.redis_client.zcard(key)
            
            if current_count >= limits["requests"]:
                return True
            
            await self.redis_client.zadd(key, {str(current_time): current_time})
            await self.redis_client.expire(key, limits["window"])
            return False
        except Exception as e:
            logger.error(f"Redis rate limiting error: {e}")
            return False
    
    async def _check_memory_rate_limit(self, user_id: str, limits: Dict, current_time: int, window_start: int) -> bool:
        """In-memory rate limiting (fallback)"""
        user_requests = self.in_memory_store[user_id]["requests"]
        user_requests[:] = [req_time for req_time in user_requests if req_time > window_start]
        
        if len(user_requests) >= limits["requests"]:
            return True
        
        user_requests.append(current_time)
        return False


class CircuitBreaker:
    """Circuit breaker pattern for service resilience"""
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = defaultdict(int)
        self.last_failure_time = defaultdict(float)
        self.state = defaultdict(str)  # "closed", "open", "half-open"
    
    def can_execute(self, service: str) -> bool:
        """Check if request can be executed"""
        current_time = time.time()
        
        if self.state[service] == "open":
            if current_time - self.last_failure_time[service] >= self.timeout:
                self.state[service] = "half-open"
                return True
            return False
        
        return True
    
    def record_success(self, service: str):
        """Record successful request"""
        self.failure_count[service] = 0
        if self.state[service] == "half-open":
            self.state[service] = "closed"
    
    def record_failure(self, service: str):
        """Record failed request"""
        self.failure_count[service] += 1
        self.last_failure_time[service] = time.time()
        
        if self.failure_count[service] >= self.failure_threshold:
            self.state[service] = "open"
            logger.warning(f"Circuit breaker opened for service {service}")


class MetricsService:
    """Request metrics and monitoring"""
    
    @staticmethod
    def record_request(service: str, method: str, path: str, status_code: int, duration: float, user_id: str = None):
        """Record request metrics"""
        logger.info(
            f"REQUEST - Service: {service}, Method: {method}, Path: {path}, "
            f"Status: {status_code}, Duration: {duration:.3f}s, User: {user_id or 'anonymous'}"
        )


# Convenience function for quick setup
def create_fastapi_app(service_name: str, 
                      service_port: int,
                      **kwargs) -> FastAPI:
    """Create a FastAPI app with all production features enabled"""
    component = FastAPIInitializationComponent(service_name, service_port, **kwargs)
    return component.create_app()
