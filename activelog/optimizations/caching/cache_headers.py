"""
Caching headers implementation for ActiveLog endpoints.
Implements intelligent caching strategies for different content types and endpoints.
"""
import time
import hashlib
from typing import Dict, List, Any, Optional, Union, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
from fastapi import FastAPI, Request, Response, Depends
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)


class CacheStrategy(Enum):
    """Different caching strategies."""
    NO_CACHE = "no-cache"
    PRIVATE = "private"
    PUBLIC = "public"
    IMMUTABLE = "immutable"
    MUST_REVALIDATE = "must-revalidate"
    PROXY_REVALIDATE = "proxy-revalidate"


@dataclass
class CacheConfig:
    """Cache configuration for endpoints."""
    max_age: int = 0  # seconds
    s_maxage: Optional[int] = None  # shared cache max age
    strategy: CacheStrategy = CacheStrategy.PRIVATE
    must_revalidate: bool = False
    proxy_revalidate: bool = False
    no_transform: bool = False
    stale_while_revalidate: int = 0
    stale_if_error: int = 0
    vary_headers: List[str] = None
    etag_enabled: bool = True
    last_modified_enabled: bool = True
    
    def __post_init__(self):
        if self.vary_headers is None:
            self.vary_headers = []


class EndpointCacheManager:
    """Manages caching configurations for different endpoints."""
    
    def __init__(self):
        self.cache_configs: Dict[str, CacheConfig] = {}
        self.etag_cache: Dict[str, str] = {}
        self._setup_default_configs()
    
    def _setup_default_configs(self):
        """Setup default cache configurations for common endpoint patterns."""
        
        # Static assets - long cache with immutable flag
        self.cache_configs["/static/*"] = CacheConfig(
            max_age=31536000,  # 1 year
            strategy=CacheStrategy.PUBLIC,
            vary_headers=["Accept-Encoding"],
            etag_enabled=True
        )
        
        # API health check - short cache
        self.cache_configs["/health"] = CacheConfig(
            max_age=30,
            strategy=CacheStrategy.PUBLIC,
            etag_enabled=False,
            last_modified_enabled=False
        )
        
        # User profile - private cache, medium duration
        self.cache_configs["/api/v1/users/me"] = CacheConfig(
            max_age=300,  # 5 minutes
            strategy=CacheStrategy.PRIVATE,
            must_revalidate=True,
            vary_headers=["Authorization"]
        )
        
        # File listings - short cache with revalidation
        self.cache_configs["/api/v1/files"] = CacheConfig(
            max_age=300,  # 5 minutes
            strategy=CacheStrategy.PRIVATE,
            must_revalidate=True,
            stale_while_revalidate=60,
            vary_headers=["Authorization", "Accept"]
        )
        
        # File metadata - medium cache
        self.cache_configs["/api/v1/files/*"] = CacheConfig(
            max_age=1800,  # 30 minutes
            strategy=CacheStrategy.PRIVATE,
            vary_headers=["Authorization"]
        )
        
        # Search results - short cache
        self.cache_configs["/api/v1/files/search"] = CacheConfig(
            max_age=180,  # 3 minutes
            strategy=CacheStrategy.PRIVATE,
            stale_while_revalidate=60,
            vary_headers=["Authorization"]
        )
        
        # Public file shares - medium cache
        self.cache_configs["/api/v1/files/*/public"] = CacheConfig(
            max_age=3600,  # 1 hour
            strategy=CacheStrategy.PUBLIC,
            vary_headers=["Accept-Encoding"]
        )
        
        # File downloads - conditional caching
        self.cache_configs["/api/v1/files/*/download"] = CacheConfig(
            max_age=86400,  # 24 hours
            strategy=CacheStrategy.PRIVATE,
            etag_enabled=True,
            last_modified_enabled=True,
            vary_headers=["Authorization", "Range"]
        )
        
        # User avatars - long cache
        self.cache_configs["/api/v1/users/*/avatar"] = CacheConfig(
            max_age=604800,  # 7 days
            strategy=CacheStrategy.PUBLIC,
            vary_headers=["Accept-Encoding"]
        )
        
        # Analytics data - short cache
        self.cache_configs["/api/v1/analytics/*"] = CacheConfig(
            max_age=300,  # 5 minutes
            strategy=CacheStrategy.PRIVATE,
            must_revalidate=True,
            vary_headers=["Authorization"]
        )
        
        # Admin endpoints - no cache
        self.cache_configs["/api/v1/admin/*"] = CacheConfig(
            max_age=0,
            strategy=CacheStrategy.NO_CACHE,
            must_revalidate=True,
            etag_enabled=False
        )
        
        # Authentication endpoints - no cache
        self.cache_configs["/api/v1/auth/*"] = CacheConfig(
            max_age=0,
            strategy=CacheStrategy.NO_CACHE,
            must_revalidate=True,
            etag_enabled=False,
            last_modified_enabled=False
        )
        
        # Default for all other endpoints
        self.cache_configs["*"] = CacheConfig(
            max_age=0,
            strategy=CacheStrategy.NO_CACHE,
            must_revalidate=True
        )
    
    def get_cache_config(self, path: str, method: str = "GET") -> CacheConfig:
        """Get cache configuration for a specific path and method."""
        # Only cache GET and HEAD requests by default
        if method not in ["GET", "HEAD"]:
            return CacheConfig(
                max_age=0,
                strategy=CacheStrategy.NO_CACHE,
                must_revalidate=True,
                etag_enabled=False
            )
        
        # Find matching configuration
        for pattern, config in self.cache_configs.items():
            if self._path_matches_pattern(path, pattern):
                return config
        
        # Return default configuration
        return self.cache_configs["*"]
    
    def _path_matches_pattern(self, path: str, pattern: str) -> bool:
        """Check if path matches cache pattern."""
        if pattern == "*":
            return True
        
        if pattern.endswith("*"):
            prefix = pattern[:-1]
            return path.startswith(prefix)
        
        return path == pattern
    
    def set_cache_config(self, pattern: str, config: CacheConfig):
        """Set cache configuration for a pattern."""
        self.cache_configs[pattern] = config
    
    def generate_etag(self, content: Union[str, bytes], additional_data: str = "") -> str:
        """Generate ETag for content."""
        if isinstance(content, str):
            content = content.encode('utf-8')
        
        # Include additional data like user_id for private content
        etag_data = content + additional_data.encode('utf-8')
        
        # Generate hash
        etag_hash = hashlib.md5(etag_data).hexdigest()
        return f'"{etag_hash}"'
    
    def check_conditional_headers(
        self,
        request: Request,
        etag: Optional[str] = None,
        last_modified: Optional[datetime] = None
    ) -> Optional[Response]:
        """Check conditional headers and return 304 if not modified."""
        
        # Check If-None-Match (ETag)
        if etag and "if-none-match" in request.headers:
            if_none_match = request.headers["if-none-match"]
            # Handle both quoted and unquoted ETags
            if etag == if_none_match or etag.strip('"') == if_none_match.strip('"'):
                return Response(status_code=304)
        
        # Check If-Modified-Since
        if last_modified and "if-modified-since" in request.headers:
            try:
                if_modified_since = datetime.strptime(
                    request.headers["if-modified-since"],
                    "%a, %d %b %Y %H:%M:%S %Z"
                )
                
                # Compare timestamps (ignore microseconds)
                if last_modified.replace(microsecond=0) <= if_modified_since:
                    return Response(status_code=304)
            except ValueError:
                # Invalid date format, ignore
                pass
        
        return None


class CacheMiddleware:
    """Middleware to automatically add cache headers to responses."""
    
    def __init__(self, cache_manager: EndpointCacheManager = None):
        self.cache_manager = cache_manager or EndpointCacheManager()
    
    async def __call__(self, request: Request, call_next: Callable):
        """Process request and add cache headers to response."""
        # Get cache configuration
        cache_config = self.cache_manager.get_cache_config(
            request.url.path,
            request.method
        )
        
        # Check conditional headers for cacheable requests
        if cache_config.max_age > 0:
            # For GET requests, we might want to check conditional headers
            # This would need to be implemented per endpoint with specific ETag/Last-Modified logic
            pass
        
        # Call the next middleware/endpoint
        response = await call_next(request)
        
        # Add cache headers
        self._add_cache_headers(response, cache_config, request)
        
        return response
    
    def _add_cache_headers(
        self,
        response: Response,
        cache_config: CacheConfig,
        request: Request
    ):
        """Add appropriate cache headers to response."""
        
        # Don't add cache headers if already present
        if "cache-control" in response.headers:
            return
        
        # Build Cache-Control header
        cache_parts = []
        
        # Add strategy
        if cache_config.strategy == CacheStrategy.NO_CACHE:
            cache_parts.append("no-cache")
            cache_parts.append("no-store")
        elif cache_config.strategy == CacheStrategy.PRIVATE:
            cache_parts.append("private")
        elif cache_config.strategy == CacheStrategy.PUBLIC:
            cache_parts.append("public")
        
        # Add max-age
        cache_parts.append(f"max-age={cache_config.max_age}")
        
        # Add s-maxage for shared caches
        if cache_config.s_maxage is not None:
            cache_parts.append(f"s-maxage={cache_config.s_maxage}")
        
        # Add revalidation directives
        if cache_config.must_revalidate:
            cache_parts.append("must-revalidate")
        
        if cache_config.proxy_revalidate:
            cache_parts.append("proxy-revalidate")
        
        # Add transform directive
        if cache_config.no_transform:
            cache_parts.append("no-transform")
        
        # Add stale-while-revalidate
        if cache_config.stale_while_revalidate > 0:
            cache_parts.append(f"stale-while-revalidate={cache_config.stale_while_revalidate}")
        
        # Add stale-if-error
        if cache_config.stale_if_error > 0:
            cache_parts.append(f"stale-if-error={cache_config.stale_if_error}")
        
        # Set Cache-Control header
        response.headers["cache-control"] = ", ".join(cache_parts)
        
        # Add Vary headers
        if cache_config.vary_headers:
            existing_vary = response.headers.get("vary", "")
            vary_headers = cache_config.vary_headers.copy()
            
            if existing_vary:
                existing_headers = [h.strip() for h in existing_vary.split(",")]
                vary_headers.extend(h for h in existing_headers if h not in vary_headers)
            
            response.headers["vary"] = ", ".join(vary_headers)
        
        # Add Expires header for compatibility
        if cache_config.max_age > 0 and cache_config.strategy != CacheStrategy.NO_CACHE:
            expires = datetime.utcnow() + timedelta(seconds=cache_config.max_age)
            response.headers["expires"] = expires.strftime("%a, %d %b %Y %H:%M:%S GMT")


class SmartCacheDecorator:
    """Decorator for adding smart caching to specific endpoints."""
    
    def __init__(self, cache_manager: EndpointCacheManager = None):
        self.cache_manager = cache_manager or EndpointCacheManager()
    
    def cached(
        self,
        max_age: int = 300,
        strategy: CacheStrategy = CacheStrategy.PRIVATE,
        vary: List[str] = None,
        etag_func: Callable = None,
        last_modified_func: Callable = None,
        cache_key_func: Callable = None
    ):
        """Decorator for caching endpoint responses."""
        
        def decorator(func: Callable):
            async def wrapper(*args, **kwargs):
                # Extract request from args/kwargs
                request = None
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break
                
                if not request:
                    # Fallback to original function if no request found
                    return await func(*args, **kwargs)
                
                # Generate cache key
                cache_key = None
                if cache_key_func:
                    cache_key = cache_key_func(request, *args, **kwargs)
                else:
                    cache_key = f"{request.url.path}?{request.url.query}"
                
                # Check conditional headers
                etag = None
                last_modified = None
                
                # Generate ETag if function provided
                if etag_func:
                    etag = etag_func(request, *args, **kwargs)
                
                # Generate Last-Modified if function provided
                if last_modified_func:
                    last_modified = last_modified_func(request, *args, **kwargs)
                
                # Check if we can return 304 Not Modified
                not_modified_response = self.cache_manager.check_conditional_headers(
                    request, etag, last_modified
                )
                if not_modified_response:
                    return not_modified_response
                
                # Call original function
                response = await func(*args, **kwargs)
                
                # Add cache headers if it's a Response object
                if isinstance(response, Response):
                    cache_config = CacheConfig(
                        max_age=max_age,
                        strategy=strategy,
                        vary_headers=vary or []
                    )
                    
                    middleware = CacheMiddleware(self.cache_manager)
                    middleware._add_cache_headers(response, cache_config, request)
                    
                    # Add ETag and Last-Modified headers
                    if etag:
                        response.headers["etag"] = etag
                    
                    if last_modified:
                        response.headers["last-modified"] = last_modified.strftime(
                            "%a, %d %b %Y %H:%M:%S GMT"
                        )
                
                return response
            
            return wrapper
        return decorator


class ContentTypeSpecificCaching:
    """Specialized caching for different content types."""
    
    @staticmethod
    def get_image_cache_config() -> CacheConfig:
        """Cache configuration for images."""
        return CacheConfig(
            max_age=2592000,  # 30 days
            strategy=CacheStrategy.PUBLIC,
            vary_headers=["Accept-Encoding"],
            etag_enabled=True
        )
    
    @staticmethod
    def get_api_data_cache_config() -> CacheConfig:
        """Cache configuration for API data."""
        return CacheConfig(
            max_age=300,  # 5 minutes
            strategy=CacheStrategy.PRIVATE,
            must_revalidate=True,
            stale_while_revalidate=60,
            vary_headers=["Authorization", "Accept"]
        )
    
    @staticmethod
    def get_user_content_cache_config() -> CacheConfig:
        """Cache configuration for user-specific content."""
        return CacheConfig(
            max_age=600,  # 10 minutes
            strategy=CacheStrategy.PRIVATE,
            must_revalidate=True,
            vary_headers=["Authorization"]
        )
    
    @staticmethod
    def get_static_asset_cache_config() -> CacheConfig:
        """Cache configuration for static assets with versioning."""
        return CacheConfig(
            max_age=31536000,  # 1 year
            strategy=CacheStrategy.PUBLIC,
            vary_headers=["Accept-Encoding"],
            etag_enabled=True
        )


# Usage examples and utility functions
def create_etag_for_data(data: Any, user_id: str = None) -> str:
    """Create ETag for JSON data with optional user context."""
    import json
    
    json_str = json.dumps(data, sort_keys=True, default=str)
    additional_data = user_id or ""
    
    cache_manager = EndpointCacheManager()
    return cache_manager.generate_etag(json_str, additional_data)


def create_cached_json_response(
    data: Any,
    cache_config: CacheConfig,
    etag: str = None,
    last_modified: datetime = None
) -> JSONResponse:
    """Create a JSON response with cache headers."""
    
    response = JSONResponse(content=data)
    
    # Add cache headers
    middleware = CacheMiddleware()
    cache_parts = []
    
    if cache_config.strategy == CacheStrategy.NO_CACHE:
        cache_parts.extend(["no-cache", "no-store"])
    elif cache_config.strategy == CacheStrategy.PRIVATE:
        cache_parts.append("private")
    elif cache_config.strategy == CacheStrategy.PUBLIC:
        cache_parts.append("public")
    
    cache_parts.append(f"max-age={cache_config.max_age}")
    
    if cache_config.must_revalidate:
        cache_parts.append("must-revalidate")
    
    response.headers["cache-control"] = ", ".join(cache_parts)
    
    if cache_config.vary_headers:
        response.headers["vary"] = ", ".join(cache_config.vary_headers)
    
    if etag:
        response.headers["etag"] = etag
    
    if last_modified:
        response.headers["last-modified"] = last_modified.strftime(
            "%a, %d %b %Y %H:%M:%S GMT"
        )
    
    return response


def setup_caching_middleware(app: FastAPI, cache_manager: EndpointCacheManager = None):
    """Setup caching middleware for FastAPI application."""
    
    if cache_manager is None:
        cache_manager = EndpointCacheManager()
    
    middleware = CacheMiddleware(cache_manager)
    
    @app.middleware("http")
    async def add_cache_headers(request: Request, call_next):
        return await middleware(request, call_next)
    
    return cache_manager


# Global cache manager instance
_global_cache_manager = None


def get_cache_manager() -> EndpointCacheManager:
    """Get global cache manager instance."""
    global _global_cache_manager
    if _global_cache_manager is None:
        _global_cache_manager = EndpointCacheManager()
    return _global_cache_manager