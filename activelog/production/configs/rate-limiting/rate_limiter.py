"""
Advanced Rate Limiting for ActiveLog Production

Implements multiple rate limiting strategies:
- Token bucket algorithm
- Sliding window counter
- Fixed window counter
- Distributed rate limiting with Redis
- Per-user, per-IP, and per-endpoint limits
- Rate limit headers and responses
"""

import time
import json
import logging
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import hashlib
import redis
from flask import request, jsonify, g
from functools import wraps

logger = logging.getLogger(__name__)

class RateLimitAlgorithm(Enum):
    TOKEN_BUCKET = "token_bucket"
    SLIDING_WINDOW = "sliding_window"
    FIXED_WINDOW = "fixed_window"

@dataclass
class RateLimitConfig:
    requests_per_window: int = 100
    window_seconds: int = 60
    burst_allowance: int = 10
    algorithm: RateLimitAlgorithm = RateLimitAlgorithm.SLIDING_WINDOW
    key_prefix: str = "rate_limit"
    redis_host: str = "redis-master"
    redis_port: int = 6379
    redis_db: int = 1

class RateLimitError(Exception):
    """Rate limit exceeded exception"""
    def __init__(self, message: str, retry_after: int, limit: int, remaining: int):
        super().__init__(message)
        self.retry_after = retry_after
        self.limit = limit
        self.remaining = remaining

class RedisRateLimiter:
    """Redis-based distributed rate limiter"""
    
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.redis_client = redis.Redis(
            host=config.redis_host,
            port=config.redis_port,
            db=config.redis_db,
            decode_responses=True
        )
    
    def _get_key(self, identifier: str, endpoint: str = "global") -> str:
        """Generate Redis key for rate limiting"""
        return f"{self.config.key_prefix}:{endpoint}:{identifier}"
    
    def _sliding_window_check(self, key: str, limit: int, window: int) -> Tuple[bool, Dict[str, Any]]:
        """Sliding window rate limiting algorithm"""
        now = time.time()
        window_start = now - window
        
        pipe = self.redis_client.pipeline()
        pipe.multi()
        
        # Remove expired entries
        pipe.zremrangebyscore(key, 0, window_start)
        
        # Count current requests
        pipe.zcard(key)
        
        # Add current request
        pipe.zadd(key, {str(now): now})
        
        # Set expiration
        pipe.expire(key, window + 1)
        
        results = pipe.execute()
        current_requests = results[1]
        
        allowed = current_requests < limit
        remaining = max(0, limit - current_requests - 1)
        
        return allowed, {
            "limit": limit,
            "remaining": remaining,
            "reset_time": int(now + window),
            "retry_after": window if not allowed else 0
        }
    
    def _fixed_window_check(self, key: str, limit: int, window: int) -> Tuple[bool, Dict[str, Any]]:
        """Fixed window rate limiting algorithm"""
        now = int(time.time())
        window_key = f"{key}:{now // window}"
        
        pipe = self.redis_client.pipeline()
        pipe.multi()
        
        # Increment counter
        pipe.incr(window_key)
        
        # Set expiration on first request
        pipe.expire(window_key, window)
        
        results = pipe.execute()
        current_requests = results[0]
        
        allowed = current_requests <= limit
        remaining = max(0, limit - current_requests)
        reset_time = ((now // window) + 1) * window
        
        return allowed, {
            "limit": limit,
            "remaining": remaining,
            "reset_time": reset_time,
            "retry_after": reset_time - now if not allowed else 0
        }
    
    def _token_bucket_check(self, key: str, limit: int, window: int, burst: int = None) -> Tuple[bool, Dict[str, Any]]:
        """Token bucket rate limiting algorithm"""
        if burst is None:
            burst = limit
        
        now = time.time()
        bucket_key = f"{key}:bucket"
        
        # Get current bucket state
        bucket_data = self.redis_client.hgetall(bucket_key)
        
        if bucket_data:
            tokens = float(bucket_data.get('tokens', burst))
            last_refill = float(bucket_data.get('last_refill', now))
        else:
            tokens = float(burst)
            last_refill = now
        
        # Calculate token refill
        time_passed = now - last_refill
        tokens_to_add = time_passed * (limit / window)
        tokens = min(burst, tokens + tokens_to_add)
        
        allowed = tokens >= 1.0
        
        if allowed:
            tokens -= 1.0
        
        # Update bucket state
        pipe = self.redis_client.pipeline()
        pipe.hset(bucket_key, mapping={
            'tokens': str(tokens),
            'last_refill': str(now)
        })
        pipe.expire(bucket_key, window * 2)
        pipe.execute()
        
        return allowed, {
            "limit": limit,
            "remaining": int(tokens),
            "reset_time": int(now + (burst - tokens) * (window / limit)),
            "retry_after": int((1.0 - tokens) * (window / limit)) if not allowed else 0
        }
    
    def check_rate_limit(self, identifier: str, endpoint: str = "global") -> Tuple[bool, Dict[str, Any]]:
        """Check if request is within rate limits"""
        key = self._get_key(identifier, endpoint)
        
        try:
            if self.config.algorithm == RateLimitAlgorithm.SLIDING_WINDOW:
                return self._sliding_window_check(
                    key, self.config.requests_per_window, self.config.window_seconds
                )
            elif self.config.algorithm == RateLimitAlgorithm.FIXED_WINDOW:
                return self._fixed_window_check(
                    key, self.config.requests_per_window, self.config.window_seconds
                )
            elif self.config.algorithm == RateLimitAlgorithm.TOKEN_BUCKET:
                return self._token_bucket_check(
                    key, self.config.requests_per_window, self.config.window_seconds, 
                    self.config.burst_allowance
                )
            else:
                # Default to allowing request if algorithm unknown
                return True, {"limit": self.config.requests_per_window, "remaining": self.config.requests_per_window - 1}
                
        except Exception as e:
            logger.error(f"Rate limiting error: {e}")
            # Fail open - allow request on error
            return True, {"limit": self.config.requests_per_window, "remaining": self.config.requests_per_window - 1, "error": str(e)}

class RateLimitManager:
    """Manages multiple rate limiters with different configs"""
    
    def __init__(self):
        self.limiters: Dict[str, RedisRateLimiter] = {}
        self.default_config = RateLimitConfig()
    
    def add_limiter(self, name: str, config: RateLimitConfig):
        """Add a rate limiter with specific configuration"""
        self.limiters[name] = RedisRateLimiter(config)
    
    def get_limiter(self, name: str) -> RedisRateLimiter:
        """Get rate limiter by name"""
        if name not in self.limiters:
            self.limiters[name] = RedisRateLimiter(self.default_config)
        return self.limiters[name]
    
    def check_limits(self, identifier: str, endpoint: str, limiter_names: list = None) -> Tuple[bool, Dict[str, Any]]:
        """Check multiple rate limits and return most restrictive"""
        if limiter_names is None:
            limiter_names = ["default"]
        
        most_restrictive = None
        all_allowed = True
        
        for limiter_name in limiter_names:
            limiter = self.get_limiter(limiter_name)
            allowed, info = limiter.check_rate_limit(identifier, endpoint)
            
            if not allowed:
                all_allowed = False
                if most_restrictive is None or info.get("retry_after", 0) > most_restrictive.get("retry_after", 0):
                    most_restrictive = info
            elif most_restrictive is None:
                most_restrictive = info
        
        return all_allowed, most_restrictive or {}

# Global rate limit manager
rate_limit_manager = RateLimitManager()

def init_rate_limiters():
    """Initialize rate limiters with different configurations"""
    
    # Default API rate limit (100 requests per minute)
    rate_limit_manager.add_limiter("api", RateLimitConfig(
        requests_per_window=100,
        window_seconds=60,
        algorithm=RateLimitAlgorithm.SLIDING_WINDOW
    ))
    
    # Strict rate limit for authentication endpoints (10 requests per minute)
    rate_limit_manager.add_limiter("auth", RateLimitConfig(
        requests_per_window=10,
        window_seconds=60,
        algorithm=RateLimitAlgorithm.FIXED_WINDOW
    ))
    
    # Upload rate limit (5 requests per minute with burst of 10)
    rate_limit_manager.add_limiter("upload", RateLimitConfig(
        requests_per_window=5,
        window_seconds=60,
        burst_allowance=10,
        algorithm=RateLimitAlgorithm.TOKEN_BUCKET
    ))
    
    # Search rate limit (50 requests per minute)
    rate_limit_manager.add_limiter("search", RateLimitConfig(
        requests_per_window=50,
        window_seconds=60,
        algorithm=RateLimitAlgorithm.SLIDING_WINDOW
    ))
    
    # AI processing rate limit (20 requests per hour)
    rate_limit_manager.add_limiter("ai", RateLimitConfig(
        requests_per_window=20,
        window_seconds=3600,
        algorithm=RateLimitAlgorithm.SLIDING_WINDOW
    ))

def get_client_identifier() -> str:
    """Get client identifier for rate limiting"""
    # Try to get user ID from authentication
    user_id = getattr(g, 'user_id', None)
    if user_id:
        return f"user:{user_id}"
    
    # Fall back to IP address
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if client_ip:
        # Take first IP in case of multiple proxies
        client_ip = client_ip.split(',')[0].strip()
        return f"ip:{client_ip}"
    
    # Last resort: use a hash of user agent
    user_agent = request.headers.get('User-Agent', 'unknown')
    return f"ua:{hashlib.md5(user_agent.encode()).hexdigest()[:12]}"

def get_endpoint_identifier() -> str:
    """Get endpoint identifier for rate limiting"""
    # Use the route pattern instead of full path to group similar endpoints
    endpoint = request.endpoint or request.path
    method = request.method
    return f"{method}:{endpoint}"

def rate_limit_response(error: RateLimitError) -> tuple:
    """Create rate limit response"""
    response_data = {
        "error": "rate_limit_exceeded",
        "message": str(error),
        "limit": error.limit,
        "remaining": error.remaining,
        "retry_after": error.retry_after
    }
    
    response = jsonify(response_data)
    response.status_code = 429
    response.headers['X-RateLimit-Limit'] = str(error.limit)
    response.headers['X-RateLimit-Remaining'] = str(error.remaining)
    response.headers['X-RateLimit-Reset'] = str(int(time.time()) + error.retry_after)
    response.headers['Retry-After'] = str(error.retry_after)
    
    return response, 429

def rate_limit(limiter_names: list = None, per_user: bool = True, per_ip: bool = False):
    """Decorator for rate limiting endpoints"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get identifiers
            if per_user:
                identifier = get_client_identifier()
            elif per_ip:
                identifier = f"ip:{request.headers.get('X-Forwarded-For', request.remote_addr)}"
            else:
                identifier = "global"
            
            endpoint = get_endpoint_identifier()
            
            # Check rate limits
            allowed, info = rate_limit_manager.check_limits(identifier, endpoint, limiter_names)
            
            if not allowed:
                error = RateLimitError(
                    f"Rate limit exceeded for {endpoint}",
                    info.get("retry_after", 60),
                    info.get("limit", 100),
                    info.get("remaining", 0)
                )
                return rate_limit_response(error)
            
            # Add rate limit headers to successful responses
            response = func(*args, **kwargs)
            
            if hasattr(response, 'headers'):
                response.headers['X-RateLimit-Limit'] = str(info.get("limit", 100))
                response.headers['X-RateLimit-Remaining'] = str(info.get("remaining", 0))
                response.headers['X-RateLimit-Reset'] = str(info.get("reset_time", int(time.time()) + 60))
            
            return response
        return wrapper
    return decorator

# Flask middleware for automatic rate limiting
def rate_limit_middleware(app):
    """Flask middleware to apply rate limiting to all requests"""
    
    @app.before_request
    def before_request():
        # Skip rate limiting for health checks and static files
        if request.path in ['/health', '/metrics', '/status']:
            return
        
        if request.path.startswith('/static/'):
            return
        
        # Determine rate limiter based on endpoint
        limiter_names = ["api"]  # Default
        
        if request.path.startswith('/auth/'):
            limiter_names = ["auth"]
        elif request.path.startswith('/upload/'):
            limiter_names = ["upload"]
        elif request.path.startswith('/search/'):
            limiter_names = ["search"]
        elif request.path.startswith('/ai/'):
            limiter_names = ["ai"]
        
        # Get identifiers
        identifier = get_client_identifier()
        endpoint = get_endpoint_identifier()
        
        # Check rate limits
        allowed, info = rate_limit_manager.check_limits(identifier, endpoint, limiter_names)
        
        if not allowed:
            error = RateLimitError(
                f"Rate limit exceeded for {endpoint}",
                info.get("retry_after", 60),
                info.get("limit", 100),
                info.get("remaining", 0)
            )
            
            # Log rate limit violation
            logger.warning(f"Rate limit exceeded for {identifier} on {endpoint}: {info}")
            
            return rate_limit_response(error)
        
        # Store rate limit info in g for use in after_request
        g.rate_limit_info = info
    
    @app.after_request
    def after_request(response):
        # Add rate limit headers to all responses
        if hasattr(g, 'rate_limit_info') and g.rate_limit_info:
            info = g.rate_limit_info
            response.headers['X-RateLimit-Limit'] = str(info.get("limit", 100))
            response.headers['X-RateLimit-Remaining'] = str(info.get("remaining", 0))
            response.headers['X-RateLimit-Reset'] = str(info.get("reset_time", int(time.time()) + 60))
        
        return response

# Rate limiting metrics
def get_rate_limit_metrics() -> Dict[str, Any]:
    """Get rate limiting metrics"""
    metrics = {}
    
    for limiter_name, limiter in rate_limit_manager.limiters.items():
        try:
            # Get Redis info for this limiter
            redis_info = limiter.redis_client.info()
            
            # Count active rate limit keys
            pattern = f"{limiter.config.key_prefix}:*"
            keys = limiter.redis_client.keys(pattern)
            
            metrics[limiter_name] = {
                "algorithm": limiter.config.algorithm.value,
                "requests_per_window": limiter.config.requests_per_window,
                "window_seconds": limiter.config.window_seconds,
                "active_keys": len(keys),
                "redis_connected": True,
                "redis_used_memory": redis_info.get("used_memory_human", "unknown")
            }
        except Exception as e:
            metrics[limiter_name] = {
                "error": str(e),
                "redis_connected": False
            }
    
    return metrics

# Example usage configurations
AUTH_RATE_LIMIT = ["auth"]
UPLOAD_RATE_LIMIT = ["upload", "api"] 
SEARCH_RATE_LIMIT = ["search"]
AI_RATE_LIMIT = ["ai"]

# IP-based rate limiting for public endpoints
def ip_rate_limit(requests_per_minute: int = 60):
    """IP-based rate limiting decorator"""
    config = RateLimitConfig(
        requests_per_window=requests_per_minute,
        window_seconds=60,
        algorithm=RateLimitAlgorithm.SLIDING_WINDOW
    )
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            limiter = RedisRateLimiter(config)
            client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
            identifier = f"ip:{client_ip}"
            endpoint = get_endpoint_identifier()
            
            allowed, info = limiter.check_rate_limit(identifier, endpoint)
            
            if not allowed:
                error = RateLimitError(
                    f"Rate limit exceeded for IP {client_ip}",
                    info.get("retry_after", 60),
                    info.get("limit", requests_per_minute),
                    info.get("remaining", 0)
                )
                return rate_limit_response(error)
            
            return func(*args, **kwargs)
        return wrapper
    return decorator