import asyncio
import aiohttp
import json
import logging
import time
import hashlib
import hmac
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
import jwt
from datetime import datetime, timedelta
import redis
import ssl

class ProxyMode(Enum):
    TRANSPARENT = "transparent"
    FILTERING = "filtering"
    CACHING = "caching"
    RATE_LIMITED = "rate_limited"
    SECURE = "secure"

class AuthMethod(Enum):
    NONE = "none"
    API_KEY = "api_key"
    JWT = "jwt"
    OAUTH = "oauth"
    CUSTOM = "custom"

@dataclass
class ProxyRule:
    path_pattern: str
    target_url: str
    auth_required: bool = False
    rate_limit: Optional[int] = None  # requests per minute
    cache_ttl: Optional[int] = None  # seconds
    allowed_methods: List[str] = field(default_factory=lambda: ["GET", "POST", "PUT", "DELETE"])
    headers_to_add: Dict[str, str] = field(default_factory=dict)
    headers_to_remove: List[str] = field(default_factory=list)
    request_transform: Optional[Callable] = None
    response_transform: Optional[Callable] = None

@dataclass
class ProxyMetrics:
    requests_total: int = 0
    requests_successful: int = 0
    requests_failed: int = 0
    avg_response_time: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    rate_limit_hits: int = 0
    last_reset: datetime = field(default_factory=datetime.utcnow)

class APIGatewayProxy:
    def __init__(self, redis_url: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        
        # Core configuration
        self.proxy_rules: Dict[str, ProxyRule] = {}
        self.auth_config: Dict[str, Any] = {}
        self.middleware: List[Callable] = []
        self.metrics = ProxyMetrics()
        
        # Redis for caching and rate limiting
        self.redis_client = None
        if redis_url:
            try:
                self.redis_client = redis.from_url(redis_url)
            except Exception as e:
                self.logger.warning(f"Failed to connect to Redis: {e}")
        
        # Rate limiting storage (fallback if no Redis)
        self.rate_limit_storage: Dict[str, List[float]] = {}
        
        # Request cache (in-memory fallback)
        self.request_cache: Dict[str, Tuple[Any, float]] = {}
        
        # SSL context for secure upstream connections
        self.ssl_context = ssl.create_default_context()

    async def configure_proxy_rules(self, rules: Dict[str, Dict[str, Any]]):
        """Configure proxy rules from configuration"""
        try:
            for rule_name, rule_config in rules.items():
                proxy_rule = ProxyRule(
                    path_pattern=rule_config["path_pattern"],
                    target_url=rule_config["target_url"],
                    auth_required=rule_config.get("auth_required", False),
                    rate_limit=rule_config.get("rate_limit"),
                    cache_ttl=rule_config.get("cache_ttl"),
                    allowed_methods=rule_config.get("allowed_methods", ["GET", "POST", "PUT", "DELETE"]),
                    headers_to_add=rule_config.get("headers_to_add", {}),
                    headers_to_remove=rule_config.get("headers_to_remove", [])
                )
                
                self.proxy_rules[rule_name] = proxy_rule
            
            self.logger.info(f"Configured {len(self.proxy_rules)} proxy rules")
            
        except Exception as e:
            self.logger.error(f"Error configuring proxy rules: {e}")
            raise

    async def configure_authentication(
        self,
        method: AuthMethod,
        config: Dict[str, Any]
    ):
        """Configure authentication method"""
        try:
            self.auth_config = {
                "method": method,
                "config": config
            }
            
            # Validate configuration based on method
            if method == AuthMethod.JWT:
                required_keys = ["secret_key", "algorithm"]
                if not all(key in config for key in required_keys):
                    raise ValueError(f"JWT auth requires: {required_keys}")
            
            elif method == AuthMethod.API_KEY:
                if "valid_keys" not in config:
                    raise ValueError("API key auth requires 'valid_keys'")
            
            self.logger.info(f"Configured authentication: {method.value}")
            
        except Exception as e:
            self.logger.error(f"Error configuring authentication: {e}")
            raise

    def add_middleware(self, middleware_func: Callable):
        """Add middleware function to the proxy pipeline"""
        self.middleware.append(middleware_func)
        self.logger.info(f"Added middleware: {middleware_func.__name__}")

    async def handle_request(
        self,
        method: str,
        path: str,
        headers: Dict[str, str],
        body: bytes,
        query_params: Dict[str, str],
        client_ip: str
    ) -> Tuple[int, Dict[str, str], bytes]:
        """Handle incoming proxy request"""
        start_time = time.time()
        
        try:
            # Find matching proxy rule
            proxy_rule = self._find_matching_rule(path)
            if not proxy_rule:
                return 404, {}, b"No proxy rule found for path"
            
            # Check method allowed
            if method not in proxy_rule.allowed_methods:
                return 405, {}, b"Method not allowed"
            
            # Apply middleware (pre-request)
            for middleware in self.middleware:
                result = await middleware("pre_request", {
                    "method": method,
                    "path": path,
                    "headers": headers,
                    "body": body,
                    "client_ip": client_ip
                })
                if result.get("block", False):
                    return result.get("status", 403), {}, result.get("body", b"Blocked by middleware")
            
            # Authentication check
            if proxy_rule.auth_required:
                auth_result = await self._authenticate_request(headers, body)
                if not auth_result["success"]:
                    return 401, {"WWW-Authenticate": "Bearer"}, auth_result["message"].encode()
            
            # Rate limiting check
            if proxy_rule.rate_limit:
                rate_limit_result = await self._check_rate_limit(client_ip, proxy_rule.rate_limit)
                if not rate_limit_result["allowed"]:
                    self.metrics.rate_limit_hits += 1
                    return 429, {"Retry-After": "60"}, b"Rate limit exceeded"
            
            # Check cache for GET requests
            if method == "GET" and proxy_rule.cache_ttl:
                cached_response = await self._get_cached_response(path, query_params)
                if cached_response:
                    self.metrics.cache_hits += 1
                    return cached_response
            
            # Transform request if configured
            if proxy_rule.request_transform:
                try:
                    headers, body = proxy_rule.request_transform(headers, body)
                except Exception as e:
                    self.logger.warning(f"Request transform failed: {e}")
            
            # Forward request to target
            response = await self._forward_request(
                proxy_rule, method, path, headers, body, query_params
            )
            
            # Transform response if configured
            if proxy_rule.response_transform:
                try:
                    response = proxy_rule.response_transform(response)
                except Exception as e:
                    self.logger.warning(f"Response transform failed: {e}")
            
            # Cache response if applicable
            if method == "GET" and proxy_rule.cache_ttl and response[0] == 200:
                await self._cache_response(path, query_params, response, proxy_rule.cache_ttl)
                self.metrics.cache_misses += 1
            
            # Apply middleware (post-response)
            for middleware in self.middleware:
                await middleware("post_response", {
                    "method": method,
                    "path": path,
                    "response": response,
                    "client_ip": client_ip
                })
            
            # Update metrics
            self._update_metrics(start_time, response[0])
            
            return response
            
        except Exception as e:
            self.logger.error(f"Proxy request failed: {e}")
            self.metrics.requests_failed += 1
            return 500, {}, b"Internal proxy error"

    def _find_matching_rule(self, path: str) -> Optional[ProxyRule]:
        """Find proxy rule matching the request path"""
        for rule_name, proxy_rule in self.proxy_rules.items():
            # Simple pattern matching - could be enhanced with regex
            pattern = proxy_rule.path_pattern
            
            if pattern.endswith("*"):
                # Prefix match
                if path.startswith(pattern[:-1]):
                    return proxy_rule
            elif pattern == path:
                # Exact match
                return proxy_rule
        
        return None

    async def _authenticate_request(
        self,
        headers: Dict[str, str],
        body: bytes
    ) -> Dict[str, Any]:
        """Authenticate incoming request"""
        try:
            auth_method = AuthMethod(self.auth_config["method"])
            config = self.auth_config["config"]
            
            if auth_method == AuthMethod.API_KEY:
                api_key = headers.get("X-API-Key") or headers.get("Authorization", "").replace("Bearer ", "")
                if api_key in config["valid_keys"]:
                    return {"success": True, "user": config["valid_keys"][api_key]}
                else:
                    return {"success": False, "message": "Invalid API key"}
            
            elif auth_method == AuthMethod.JWT:
                auth_header = headers.get("Authorization", "")
                if not auth_header.startswith("Bearer "):
                    return {"success": False, "message": "Missing or invalid Authorization header"}
                
                token = auth_header[7:]  # Remove "Bearer "
                try:
                    payload = jwt.decode(
                        token,
                        config["secret_key"],
                        algorithms=[config["algorithm"]]
                    )
                    return {"success": True, "user": payload}
                except jwt.ExpiredSignatureError:
                    return {"success": False, "message": "Token expired"}
                except jwt.InvalidTokenError:
                    return {"success": False, "message": "Invalid token"}
            
            elif auth_method == AuthMethod.CUSTOM:
                # Custom authentication function
                auth_func = config["auth_function"]
                return await auth_func(headers, body)
            
            return {"success": False, "message": "Authentication method not implemented"}
            
        except Exception as e:
            self.logger.error(f"Authentication error: {e}")
            return {"success": False, "message": "Authentication failed"}

    async def _check_rate_limit(self, client_id: str, limit_per_minute: int) -> Dict[str, Any]:
        """Check if client has exceeded rate limit"""
        try:
            current_time = time.time()
            minute_window = current_time - 60  # 1 minute window
            
            if self.redis_client:
                # Use Redis for distributed rate limiting
                key = f"rate_limit:{client_id}"
                
                # Add current request timestamp
                await self.redis_client.zadd(key, {str(current_time): current_time})
                
                # Remove old entries
                await self.redis_client.zremrangebyscore(key, 0, minute_window)
                
                # Count requests in window
                request_count = await self.redis_client.zcard(key)
                
                # Set expiry on key
                await self.redis_client.expire(key, 60)
                
                return {
                    "allowed": request_count <= limit_per_minute,
                    "count": request_count,
                    "limit": limit_per_minute
                }
            
            else:
                # Fallback to in-memory rate limiting
                if client_id not in self.rate_limit_storage:
                    self.rate_limit_storage[client_id] = []
                
                # Clean old entries
                self.rate_limit_storage[client_id] = [
                    timestamp for timestamp in self.rate_limit_storage[client_id]
                    if timestamp > minute_window
                ]
                
                # Add current request
                self.rate_limit_storage[client_id].append(current_time)
                
                request_count = len(self.rate_limit_storage[client_id])
                
                return {
                    "allowed": request_count <= limit_per_minute,
                    "count": request_count,
                    "limit": limit_per_minute
                }
                
        except Exception as e:
            self.logger.error(f"Rate limit check failed: {e}")
            return {"allowed": True}  # Fail open

    async def _get_cached_response(
        self,
        path: str,
        query_params: Dict[str, str]
    ) -> Optional[Tuple[int, Dict[str, str], bytes]]:
        """Get cached response if available and not expired"""
        try:
            cache_key = self._generate_cache_key(path, query_params)
            
            if self.redis_client:
                cached_data = await self.redis_client.get(f"cache:{cache_key}")
                if cached_data:
                    return json.loads(cached_data)
            else:
                # In-memory cache fallback
                if cache_key in self.request_cache:
                    cached_response, expiry_time = self.request_cache[cache_key]
                    if time.time() < expiry_time:
                        return cached_response
                    else:
                        del self.request_cache[cache_key]
            
            return None
            
        except Exception as e:
            self.logger.warning(f"Cache retrieval failed: {e}")
            return None

    async def _cache_response(
        self,
        path: str,
        query_params: Dict[str, str],
        response: Tuple[int, Dict[str, str], bytes],
        ttl: int
    ):
        """Cache response for future requests"""
        try:
            cache_key = self._generate_cache_key(path, query_params)
            expiry_time = time.time() + ttl
            
            # Only cache successful responses
            if response[0] != 200:
                return
            
            if self.redis_client:
                await self.redis_client.setex(
                    f"cache:{cache_key}",
                    ttl,
                    json.dumps(response)
                )
            else:
                # In-memory cache fallback
                self.request_cache[cache_key] = (response, expiry_time)
                
                # Simple cache size management
                if len(self.request_cache) > 1000:
                    # Remove oldest entries
                    sorted_items = sorted(self.request_cache.items(), key=lambda x: x[1][1])
                    for i in range(100):  # Remove 100 oldest
                        del self.request_cache[sorted_items[i][0]]
            
        except Exception as e:
            self.logger.warning(f"Response caching failed: {e}")

    def _generate_cache_key(self, path: str, query_params: Dict[str, str]) -> str:
        """Generate cache key from path and query parameters"""
        query_string = "&".join(f"{k}={v}" for k, v in sorted(query_params.items()))
        cache_input = f"{path}?{query_string}"
        return hashlib.md5(cache_input.encode()).hexdigest()

    async def _forward_request(
        self,
        proxy_rule: ProxyRule,
        method: str,
        path: str,
        headers: Dict[str, str],
        body: bytes,
        query_params: Dict[str, str]
    ) -> Tuple[int, Dict[str, str], bytes]:
        """Forward request to target service"""
        try:
            # Build target URL
            target_path = path.replace(proxy_rule.path_pattern.rstrip("*"), "").lstrip("/")
            target_url = f"{proxy_rule.target_url.rstrip('/')}/{target_path}"
            
            # Prepare headers
            forwarded_headers = headers.copy()
            
            # Add configured headers
            for key, value in proxy_rule.headers_to_add.items():
                forwarded_headers[key] = value
            
            # Remove configured headers
            for key in proxy_rule.headers_to_remove:
                forwarded_headers.pop(key, None)
            
            # Add proxy headers
            forwarded_headers["X-Forwarded-By"] = "ActiveLog-APIGateway"
            forwarded_headers["X-Proxy-Timestamp"] = str(int(time.time()))
            
            # Remove hop-by-hop headers
            hop_by_hop = ["connection", "keep-alive", "proxy-authenticate", 
                         "proxy-authorization", "te", "trailers", "transfer-encoding", "upgrade"]
            for hop_header in hop_by_hop:
                forwarded_headers.pop(hop_header, None)
            
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                connector=aiohttp.TCPConnector(ssl=self.ssl_context)
            ) as session:
                
                async with session.request(
                    method=method,
                    url=target_url,
                    headers=forwarded_headers,
                    data=body if body else None,
                    params=query_params,
                    ssl=self.ssl_context
                ) as response:
                    
                    # Read response
                    response_body = await response.read()
                    response_headers = dict(response.headers)
                    
                    # Remove hop-by-hop headers from response
                    for hop_header in hop_by_hop:
                        response_headers.pop(hop_header, None)
                    
                    return response.status, response_headers, response_body
            
        except aiohttp.ClientTimeout:
            self.logger.warning(f"Request timeout to {proxy_rule.target_url}")
            return 504, {}, b"Gateway timeout"
        
        except aiohttp.ClientConnectionError as e:
            self.logger.warning(f"Connection error to {proxy_rule.target_url}: {e}")
            return 502, {}, b"Bad gateway"
        
        except Exception as e:
            self.logger.error(f"Request forwarding failed: {e}")
            return 500, {}, b"Internal server error"

    def _update_metrics(self, start_time: float, status_code: int):
        """Update proxy metrics"""
        self.metrics.requests_total += 1
        
        if 200 <= status_code < 400:
            self.metrics.requests_successful += 1
        else:
            self.metrics.requests_failed += 1
        
        # Update average response time
        response_time = time.time() - start_time
        total_requests = self.metrics.requests_total
        self.metrics.avg_response_time = (
            (self.metrics.avg_response_time * (total_requests - 1) + response_time) / total_requests
        )

    async def get_metrics(self) -> Dict[str, Any]:
        """Get current proxy metrics"""
        return {
            "requests_total": self.metrics.requests_total,
            "requests_successful": self.metrics.requests_successful,
            "requests_failed": self.metrics.requests_failed,
            "success_rate": (
                self.metrics.requests_successful / self.metrics.requests_total 
                if self.metrics.requests_total > 0 else 0
            ),
            "avg_response_time": self.metrics.avg_response_time,
            "cache_hits": self.metrics.cache_hits,
            "cache_misses": self.metrics.cache_misses,
            "cache_hit_rate": (
                self.metrics.cache_hits / (self.metrics.cache_hits + self.metrics.cache_misses)
                if (self.metrics.cache_hits + self.metrics.cache_misses) > 0 else 0
            ),
            "rate_limit_hits": self.metrics.rate_limit_hits,
            "last_reset": self.metrics.last_reset.isoformat(),
            "uptime_seconds": (datetime.utcnow() - self.metrics.last_reset).total_seconds()
        }

    async def reset_metrics(self):
        """Reset proxy metrics"""
        self.metrics = ProxyMetrics()
        self.logger.info("Proxy metrics reset")

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on proxy and upstream services"""
        health_status = {
            "proxy_status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "upstream_services": {}
        }
        
        # Check each configured upstream service
        for rule_name, proxy_rule in self.proxy_rules.items():
            try:
                async with aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as session:
                    
                    # Try to connect to upstream service
                    health_url = f"{proxy_rule.target_url}/health"
                    async with session.get(health_url) as response:
                        upstream_healthy = response.status == 200
                        health_status["upstream_services"][rule_name] = {
                            "status": "healthy" if upstream_healthy else "unhealthy",
                            "response_time": response.headers.get("X-Response-Time"),
                            "last_checked": datetime.utcnow().isoformat()
                        }
            
            except Exception as e:
                health_status["upstream_services"][rule_name] = {
                    "status": "unhealthy",
                    "error": str(e),
                    "last_checked": datetime.utcnow().isoformat()
                }
        
        # Check Redis connection if configured
        if self.redis_client:
            try:
                await self.redis_client.ping()
                health_status["redis_status"] = "healthy"
            except Exception as e:
                health_status["redis_status"] = "unhealthy"
                health_status["redis_error"] = str(e)
        
        return health_status

    async def create_security_middleware(self) -> Callable:
        """Create security middleware for common attacks"""
        
        async def security_middleware(phase: str, context: Dict[str, Any]) -> Dict[str, Any]:
            if phase == "pre_request":
                headers = context["headers"]
                path = context["path"]
                body = context["body"]
                
                # Check for common attack patterns
                suspicious_patterns = [
                    "../", "..\\", "/etc/passwd", "/windows/system32",
                    "<script", "javascript:", "onerror=", "onload=",
                    "union select", "drop table", "insert into", "delete from"
                ]
                
                # Check path and headers for suspicious content
                check_content = f"{path} {' '.join(headers.values())}"
                if body:
                    check_content += " " + body.decode(errors='ignore')
                
                check_content_lower = check_content.lower()
                
                for pattern in suspicious_patterns:
                    if pattern in check_content_lower:
                        self.logger.warning(f"Suspicious pattern detected: {pattern} from {context['client_ip']}")
                        return {
                            "block": True,
                            "status": 403,
                            "body": b"Suspicious request blocked"
                        }
                
                # Rate limiting for suspicious IPs
                # Implementation would track repeat offenders
                
            return {"block": False}
        
        return security_middleware

    async def setup_default_configuration(self):
        """Set up default proxy configuration for ActiveLog services"""
        try:
            # Default proxy rules for ActiveLog services
            default_rules = {
                "main_api": {
                    "path_pattern": "/api/*",
                    "target_url": "http://localhost:8080",
                    "auth_required": True,
                    "rate_limit": 1000,  # 1000 requests per minute
                    "cache_ttl": 300,    # 5 minutes
                    "headers_to_add": {
                        "X-Service": "main-api",
                        "X-Version": "1.0"
                    }
                },
                "bot_orchestrator": {
                    "path_pattern": "/bots/*",
                    "target_url": "http://localhost:8450",
                    "auth_required": True,
                    "rate_limit": 500
                },
                "project_memory": {
                    "path_pattern": "/memory/*",
                    "target_url": "http://localhost:8460",
                    "auth_required": True,
                    "rate_limit": 200,
                    "cache_ttl": 600  # 10 minutes
                },
                "personal_server": {
                    "path_pattern": "/personal/*",
                    "target_url": "http://localhost:8471",
                    "auth_required": True,
                    "rate_limit": 100
                }
            }
            
            await self.configure_proxy_rules(default_rules)
            
            # Configure JWT authentication
            await self.configure_authentication(
                AuthMethod.JWT,
                {
                    "secret_key": "your-secret-key-change-in-production",
                    "algorithm": "HS256"
                }
            )
            
            # Add security middleware
            security_middleware = await self.create_security_middleware()
            self.add_middleware(security_middleware)
            
            self.logger.info("Default ActiveLog proxy configuration applied")
            
        except Exception as e:
            self.logger.error(f"Error setting up default configuration: {e}")
            raise