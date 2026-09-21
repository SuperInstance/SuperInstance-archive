"""
ActiveLog Integration Hub - API Gateway Router
Auto-configures routing for all discovered services with load balancing,
rate limiting, authentication, and service mesh capabilities
"""

import asyncio
import aiohttp
from aiohttp import web, ClientSession, ClientTimeout
import json
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Any, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime, timedelta
import hashlib
import uuid
import jwt
from service_discovery import ServiceDiscovery, ServiceInfo, ServiceStatus
from health_monitor import HealthMonitor
import random
import statistics

class RoutingStrategy(Enum):
    ROUND_ROBIN = "round_robin"
    WEIGHTED = "weighted"
    LEAST_CONNECTIONS = "least_connections"
    RESPONSE_TIME = "response_time"
    RANDOM = "random"

class AuthenticationMethod(Enum):
    NONE = "none"
    API_KEY = "api_key"
    JWT = "jwt"
    OAUTH = "oauth"
    CUSTOM = "custom"

@dataclass
class RouteConfig:
    path: str
    methods: List[str]
    target_service: str
    auth_required: bool = False
    auth_method: AuthenticationMethod = AuthenticationMethod.NONE
    rate_limit_per_minute: int = 1000
    timeout_seconds: int = 30
    retry_count: int = 3
    cache_ttl_seconds: int = 0
    strip_prefix: bool = False
    rewrite_path: Optional[str] = None
    headers_to_add: Dict[str, str] = field(default_factory=dict)
    headers_to_remove: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class LoadBalancerConfig:
    strategy: RoutingStrategy = RoutingStrategy.ROUND_ROBIN
    health_check_enabled: bool = True
    sticky_sessions: bool = False
    weights: Dict[str, int] = field(default_factory=dict)
    circuit_breaker_enabled: bool = True
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: int = 60

@dataclass
class ServiceInstance:
    service_name: str
    host: str
    port: int
    weight: int = 1
    active_connections: int = 0
    total_requests: int = 0
    failed_requests: int = 0
    last_response_time: float = 0
    avg_response_time: float = 0
    health_score: float = 1.0
    last_health_check: Optional[datetime] = None
    circuit_breaker_state: str = "closed"  # closed, open, half-open
    circuit_breaker_failures: int = 0
    circuit_breaker_last_failure: Optional[datetime] = None

@dataclass
class RequestMetrics:
    request_id: str
    method: str
    path: str
    target_service: str
    target_instance: str
    start_time: datetime
    end_time: Optional[datetime] = None
    response_time_ms: float = 0
    status_code: int = 0
    bytes_sent: int = 0
    bytes_received: int = 0
    error: Optional[str] = None
    user_id: Optional[str] = None

class RateLimiter:
    def __init__(self):
        self.requests: Dict[str, List[datetime]] = {}
        self.cleanup_interval = 300  # 5 minutes
        self.last_cleanup = datetime.now()
    
    def is_allowed(self, identifier: str, limit_per_minute: int) -> bool:
        """Check if request is allowed based on rate limit"""
        now = datetime.now()
        
        # Cleanup old entries
        if (now - self.last_cleanup).seconds > self.cleanup_interval:
            self.cleanup_old_entries()
        
        if identifier not in self.requests:
            self.requests[identifier] = []
        
        # Remove requests older than 1 minute
        minute_ago = now - timedelta(minutes=1)
        self.requests[identifier] = [
            req_time for req_time in self.requests[identifier] 
            if req_time > minute_ago
        ]
        
        # Check if under limit
        if len(self.requests[identifier]) >= limit_per_minute:
            return False
        
        # Add current request
        self.requests[identifier].append(now)
        return True
    
    def cleanup_old_entries(self):
        """Remove old rate limit entries"""
        minute_ago = datetime.now() - timedelta(minutes=1)
        
        for identifier in list(self.requests.keys()):
            self.requests[identifier] = [
                req_time for req_time in self.requests[identifier] 
                if req_time > minute_ago
            ]
            
            if not self.requests[identifier]:
                del self.requests[identifier]
        
        self.last_cleanup = datetime.now()

class ResponseCache:
    def __init__(self, max_size: int = 1000):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.max_size = max_size
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cached response"""
        if key in self.cache:
            entry = self.cache[key]
            if datetime.now() < entry['expires']:
                return entry
            else:
                del self.cache[key]
        return None
    
    def set(self, key: str, response: Dict[str, Any], ttl_seconds: int):
        """Cache response"""
        if len(self.cache) >= self.max_size:
            # Remove oldest entry
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k]['cached_at'])
            del self.cache[oldest_key]
        
        self.cache[key] = {
            'response': response,
            'cached_at': datetime.now(),
            'expires': datetime.now() + timedelta(seconds=ttl_seconds)
        }
    
    def generate_key(self, method: str, path: str, query_params: str, headers: Dict[str, str]) -> str:
        """Generate cache key for request"""
        # Include relevant headers in cache key
        relevant_headers = {k: v for k, v in headers.items() 
                          if k.lower() in ['accept', 'accept-language', 'user-agent']}
        
        key_data = {
            'method': method,
            'path': path,
            'query': query_params,
            'headers': relevant_headers
        }
        
        return hashlib.md5(json.dumps(key_data, sort_keys=True).encode()).hexdigest()

class LoadBalancer:
    def __init__(self, config: LoadBalancerConfig):
        self.config = config
        self.instances: Dict[str, List[ServiceInstance]] = {}
        self.round_robin_counters: Dict[str, int] = {}
        self.session_affinity: Dict[str, str] = {}  # session_id -> instance_id
    
    def add_service_instances(self, service_name: str, instances: List[ServiceInstance]):
        """Add service instances for load balancing"""
        self.instances[service_name] = instances
        self.round_robin_counters[service_name] = 0
    
    def get_healthy_instances(self, service_name: str) -> List[ServiceInstance]:
        """Get healthy instances for a service"""
        if service_name not in self.instances:
            return []
        
        healthy = []
        for instance in self.instances[service_name]:
            if (instance.circuit_breaker_state == "closed" or 
                (instance.circuit_breaker_state == "half-open" and 
                 instance.circuit_breaker_failures < self.config.circuit_breaker_threshold)):
                healthy.append(instance)
        
        return healthy
    
    def select_instance(self, service_name: str, session_id: Optional[str] = None) -> Optional[ServiceInstance]:
        """Select best instance based on configured strategy"""
        healthy_instances = self.get_healthy_instances(service_name)
        
        if not healthy_instances:
            return None
        
        # Sticky sessions
        if self.config.sticky_sessions and session_id:
            if session_id in self.session_affinity:
                instance_id = self.session_affinity[session_id]
                for instance in healthy_instances:
                    if f"{instance.service_name}-{instance.host}:{instance.port}" == instance_id:
                        return instance
        
        # Select based on strategy
        if self.config.strategy == RoutingStrategy.ROUND_ROBIN:
            instance = self.round_robin_selection(service_name, healthy_instances)
        elif self.config.strategy == RoutingStrategy.WEIGHTED:
            instance = self.weighted_selection(healthy_instances)
        elif self.config.strategy == RoutingStrategy.LEAST_CONNECTIONS:
            instance = self.least_connections_selection(healthy_instances)
        elif self.config.strategy == RoutingStrategy.RESPONSE_TIME:
            instance = self.response_time_selection(healthy_instances)
        else:  # RANDOM
            instance = random.choice(healthy_instances)
        
        # Store session affinity
        if self.config.sticky_sessions and session_id and instance:
            instance_id = f"{instance.service_name}-{instance.host}:{instance.port}"
            self.session_affinity[session_id] = instance_id
        
        return instance
    
    def round_robin_selection(self, service_name: str, instances: List[ServiceInstance]) -> ServiceInstance:
        """Round robin instance selection"""
        counter = self.round_robin_counters[service_name]
        instance = instances[counter % len(instances)]
        self.round_robin_counters[service_name] = (counter + 1) % len(instances)
        return instance
    
    def weighted_selection(self, instances: List[ServiceInstance]) -> ServiceInstance:
        """Weighted random selection"""
        total_weight = sum(instance.weight for instance in instances)
        if total_weight == 0:
            return random.choice(instances)
        
        rand_val = random.uniform(0, total_weight)
        current_weight = 0
        
        for instance in instances:
            current_weight += instance.weight
            if rand_val <= current_weight:
                return instance
        
        return instances[-1]
    
    def least_connections_selection(self, instances: List[ServiceInstance]) -> ServiceInstance:
        """Select instance with least active connections"""
        return min(instances, key=lambda i: i.active_connections)
    
    def response_time_selection(self, instances: List[ServiceInstance]) -> ServiceInstance:
        """Select instance with best average response time"""
        return min(instances, key=lambda i: i.avg_response_time or float('inf'))
    
    def update_instance_metrics(self, instance: ServiceInstance, response_time: float, success: bool):
        """Update instance metrics after request"""
        instance.total_requests += 1
        instance.last_response_time = response_time
        
        if success:
            # Update average response time
            if instance.avg_response_time == 0:
                instance.avg_response_time = response_time
            else:
                # Exponential moving average
                alpha = 0.1
                instance.avg_response_time = (alpha * response_time + 
                                            (1 - alpha) * instance.avg_response_time)
            
            # Reset circuit breaker on success
            if instance.circuit_breaker_state == "half-open":
                instance.circuit_breaker_state = "closed"
                instance.circuit_breaker_failures = 0
        else:
            instance.failed_requests += 1
            instance.circuit_breaker_failures += 1
            instance.circuit_breaker_last_failure = datetime.now()
            
            # Check circuit breaker threshold
            if (instance.circuit_breaker_failures >= self.config.circuit_breaker_threshold and
                instance.circuit_breaker_state == "closed"):
                instance.circuit_breaker_state = "open"
        
        # Check if circuit breaker should go to half-open
        if (instance.circuit_breaker_state == "open" and
            instance.circuit_breaker_last_failure and
            (datetime.now() - instance.circuit_breaker_last_failure).seconds >= self.config.circuit_breaker_timeout):
            instance.circuit_breaker_state = "half-open"

class APIGateway:
    def __init__(self, discovery: ServiceDiscovery, health_monitor: HealthMonitor, port: int = 8100):
        self.discovery = discovery
        self.health_monitor = health_monitor
        self.port = port
        self.app = web.Application(middlewares=[
            self.logging_middleware,
            self.auth_middleware,
            self.rate_limit_middleware,
            self.metrics_middleware
        ])
        self.session: Optional[ClientSession] = None
        
        # Components
        self.rate_limiter = RateLimiter()
        self.response_cache = ResponseCache()
        self.load_balancer = LoadBalancer(LoadBalancerConfig())
        
        # Configuration
        self.routes: Dict[str, RouteConfig] = {}
        self.service_instances: Dict[str, List[ServiceInstance]] = {}
        self.request_metrics: List[RequestMetrics] = []
        self.auth_handlers: Dict[AuthenticationMethod, Callable] = {}
        
        # Auto-configuration
        self.auto_configure_enabled = True
        self.route_refresh_interval = 60  # seconds
        
        # Setup routes
        self.setup_management_routes()
        
    async def initialize(self):
        """Initialize the API Gateway"""
        self.session = ClientSession(
            timeout=ClientTimeout(total=30),
            connector=aiohttp.TCPConnector(limit=1000, limit_per_host=100)
        )
        
        # Auto-configure routes from discovered services
        if self.auto_configure_enabled:
            await self.auto_configure_routes()
        
        # Setup authentication handlers
        self.setup_auth_handlers()
        
        # Start background tasks
        asyncio.create_task(self.route_refresh_task())
        asyncio.create_task(self.metrics_collection_task())
        
        print(f"API Gateway initialized on port {self.port}")
        print(f"Configured {len(self.routes)} routes for {len(self.service_instances)} services")
    
    async def auto_configure_routes(self):
        """Auto-configure routes based on discovered services"""
        await self.discovery.discover_all_services()
        
        for service_name, service_info in self.discovery.services.items():
            if service_info.port > 0 and service_info.status == ServiceStatus.HEALTHY:
                # Create service instances
                instances = [ServiceInstance(
                    service_name=service_name,
                    host=service_info.host,
                    port=service_info.port
                )]
                
                self.service_instances[service_name] = instances
                self.load_balancer.add_service_instances(service_name, instances)
                
                # Configure routes for service endpoints
                if service_info.endpoints:
                    for endpoint in service_info.endpoints:
                        route_path = f"/{service_name}{endpoint.path}"
                        
                        # Normalize path
                        if not route_path.startswith('/'):
                            route_path = '/' + route_path
                        route_path = route_path.replace('//', '/')
                        
                        # Create route configuration
                        route_config = RouteConfig(
                            path=route_path,
                            methods=[endpoint.method],
                            target_service=service_name,
                            auth_required=endpoint.requires_auth,
                            rate_limit_per_minute=1000,
                            timeout_seconds=30,
                            strip_prefix=True,
                            rewrite_path=endpoint.path
                        )
                        
                        self.routes[f"{endpoint.method}:{route_path}"] = route_config
                else:
                    # Create default catch-all route for service
                    default_route = RouteConfig(
                        path=f"/{service_name}/*",
                        methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
                        target_service=service_name,
                        strip_prefix=True
                    )
                    
                    for method in default_route.methods:
                        self.routes[f"{method}:/{service_name}/*"] = default_route
        
        # Setup route handlers
        await self.setup_route_handlers()
    
    async def setup_route_handlers(self):
        """Setup aiohttp route handlers"""
        self.app.router._resources.clear()  # Clear existing routes
        
        for route_key, route_config in self.routes.items():
            method, path = route_key.split(':', 1)
            
            # Convert path patterns
            aiohttp_path = path.replace('*', '{path:.*}')
            
            if method == "GET":
                self.app.router.add_get(aiohttp_path, self.handle_request)
            elif method == "POST":
                self.app.router.add_post(aiohttp_path, self.handle_request)
            elif method == "PUT":
                self.app.router.add_put(aiohttp_path, self.handle_request)
            elif method == "DELETE":
                self.app.router.add_delete(aiohttp_path, self.handle_request)
            elif method == "PATCH":
                self.app.router.add_patch(aiohttp_path, self.handle_request)
    
    def setup_management_routes(self):
        """Setup management and monitoring routes"""
        self.app.router.add_get('/gateway/health', self.health_check)
        self.app.router.add_get('/gateway/routes', self.list_routes)
        self.app.router.add_get('/gateway/services', self.list_services)
        self.app.router.add_get('/gateway/metrics', self.get_metrics)
        self.app.router.add_get('/gateway/config', self.get_config)
        self.app.router.add_post('/gateway/refresh', self.refresh_routes)
        self.app.router.add_get('/gateway/circuit-breakers', self.get_circuit_breakers)
    
    def setup_auth_handlers(self):
        """Setup authentication handlers"""
        self.auth_handlers = {
            AuthenticationMethod.NONE: self.no_auth,
            AuthenticationMethod.API_KEY: self.api_key_auth,
            AuthenticationMethod.JWT: self.jwt_auth,
            AuthenticationMethod.OAUTH: self.oauth_auth,
            AuthenticationMethod.CUSTOM: self.custom_auth
        }
    
    async def handle_request(self, request: web.Request) -> web.Response:
        """Main request handler"""
        request_id = str(uuid.uuid4())
        start_time = datetime.now()
        
        # Find matching route
        route_config = await self.find_matching_route(request)
        if not route_config:
            return web.Response(text="Route not found", status=404)
        
        # Create request metrics
        metrics = RequestMetrics(
            request_id=request_id,
            method=request.method,
            path=request.path_qs,
            target_service=route_config.target_service,
            target_instance="",
            start_time=start_time
        )
        
        try:
            # Check cache
            if route_config.cache_ttl_seconds > 0:
                cache_key = self.response_cache.generate_key(
                    request.method, request.path_qs, request.query_string, dict(request.headers)
                )
                cached_response = self.response_cache.get(cache_key)
                if cached_response:
                    return web.Response(
                        body=cached_response['response']['body'],
                        status=cached_response['response']['status'],
                        headers=cached_response['response']['headers']
                    )
            
            # Select target instance
            session_id = request.cookies.get('session_id')
            instance = self.load_balancer.select_instance(route_config.target_service, session_id)
            
            if not instance:
                return web.Response(text="Service unavailable", status=503)
            
            metrics.target_instance = f"{instance.host}:{instance.port}"
            instance.active_connections += 1
            
            try:
                # Build target URL
                target_path = await self.build_target_path(request, route_config)
                target_url = f"http://{instance.host}:{instance.port}{target_path}"
                
                # Prepare headers
                headers = await self.prepare_request_headers(request, route_config)
                
                # Make request with retries
                response = await self.make_request_with_retry(
                    request, target_url, headers, route_config, instance
                )
                
                # Update metrics
                end_time = datetime.now()
                response_time = (end_time - start_time).total_seconds() * 1000
                
                metrics.end_time = end_time
                metrics.response_time_ms = response_time
                metrics.status_code = response.status
                
                self.load_balancer.update_instance_metrics(instance, response_time, response.status < 500)
                
                # Cache response if configured
                if route_config.cache_ttl_seconds > 0 and response.status == 200:
                    response_data = {
                        'body': await response.read(),
                        'status': response.status,
                        'headers': dict(response.headers)
                    }
                    self.response_cache.set(cache_key, response_data, route_config.cache_ttl_seconds)
                
                return response
                
            finally:
                instance.active_connections -= 1
        
        except Exception as e:
            metrics.error = str(e)
            logging.error(f"Request {request_id} failed: {e}")
            return web.Response(text="Internal server error", status=500)
        
        finally:
            self.request_metrics.append(metrics)
    
    async def find_matching_route(self, request: web.Request) -> Optional[RouteConfig]:
        """Find matching route configuration"""
        method = request.method
        path = request.path
        
        # Try exact match first
        route_key = f"{method}:{path}"
        if route_key in self.routes:
            return self.routes[route_key]
        
        # Try pattern matching
        for route_key, route_config in self.routes.items():
            route_method, route_path = route_key.split(':', 1)
            
            if route_method == method or route_method in route_config.methods:
                # Handle wildcard patterns
                if route_path.endswith('/*'):
                    prefix = route_path[:-2]
                    if path.startswith(prefix):
                        return route_config
                elif route_path == path:
                    return route_config
        
        return None
    
    async def build_target_path(self, request: web.Request, route_config: RouteConfig) -> str:
        """Build target service path"""
        path = request.path_qs
        
        if route_config.rewrite_path:
            return route_config.rewrite_path
        
        if route_config.strip_prefix:
            # Strip service prefix
            service_prefix = f"/{route_config.target_service}"
            if path.startswith(service_prefix):
                path = path[len(service_prefix):]
            
            if not path.startswith('/'):
                path = '/' + path
        
        return path
    
    async def prepare_request_headers(self, request: web.Request, route_config: RouteConfig) -> Dict[str, str]:
        """Prepare headers for target request"""
        headers = dict(request.headers)
        
        # Remove hop-by-hop headers
        hop_by_hop_headers = [
            'connection', 'keep-alive', 'proxy-authenticate',
            'proxy-authorization', 'te', 'trailers', 'transfer-encoding', 'upgrade'
        ]
        
        for header in hop_by_hop_headers:
            headers.pop(header, None)
        
        # Add configured headers
        headers.update(route_config.headers_to_add)
        
        # Remove configured headers
        for header in route_config.headers_to_remove:
            headers.pop(header, None)
        
        # Add gateway headers
        headers['X-Gateway-Request-ID'] = request.get('request_id', str(uuid.uuid4()))
        headers['X-Gateway-Service'] = route_config.target_service
        headers['X-Forwarded-For'] = request.remote
        headers['X-Forwarded-Proto'] = 'http'
        
        return headers
    
    async def make_request_with_retry(self, request: web.Request, target_url: str, 
                                    headers: Dict[str, str], route_config: RouteConfig,
                                    instance: ServiceInstance) -> web.Response:
        """Make request with retry logic"""
        last_error = None
        
        for attempt in range(route_config.retry_count):
            try:
                # Read request body
                body = None
                if request.can_read_body:
                    body = await request.read()
                
                # Make request
                async with self.session.request(
                    method=request.method,
                    url=target_url,
                    headers=headers,
                    data=body,
                    timeout=ClientTimeout(total=route_config.timeout_seconds)
                ) as response:
                    
                    # Read response
                    response_body = await response.read()
                    response_headers = dict(response.headers)
                    
                    # Remove hop-by-hop headers from response
                    for header in ['connection', 'keep-alive', 'transfer-encoding']:
                        response_headers.pop(header, None)
                    
                    return web.Response(
                        body=response_body,
                        status=response.status,
                        headers=response_headers
                    )
            
            except Exception as e:
                last_error = e
                if attempt < route_config.retry_count - 1:
                    await asyncio.sleep(0.1 * (attempt + 1))  # Exponential backoff
        
        # All retries failed
        raise last_error or Exception("Request failed")
    
    # Middleware
    @web.middleware
    async def logging_middleware(self, request: web.Request, handler):
        """Logging middleware"""
        start_time = time.time()
        request['request_id'] = str(uuid.uuid4())
        
        try:
            response = await handler(request)
            duration = (time.time() - start_time) * 1000
            
            logging.info(
                f"{request['request_id']} {request.method} {request.path} "
                f"-> {response.status} ({duration:.1f}ms)"
            )
            
            return response
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            logging.error(
                f"{request['request_id']} {request.method} {request.path} "
                f"-> ERROR: {e} ({duration:.1f}ms)"
            )
            raise
    
    @web.middleware
    async def auth_middleware(self, request: web.Request, handler):
        """Authentication middleware"""
        # Skip auth for management endpoints
        if request.path.startswith('/gateway/'):
            return await handler(request)
        
        route_config = await self.find_matching_route(request)
        
        if route_config and route_config.auth_required:
            auth_handler = self.auth_handlers.get(route_config.auth_method, self.no_auth)
            auth_result = await auth_handler(request)
            
            if not auth_result['success']:
                return web.Response(text=auth_result['error'], status=401)
            
            # Add user info to request
            request['user'] = auth_result.get('user')
        
        return await handler(request)
    
    @web.middleware
    async def rate_limit_middleware(self, request: web.Request, handler):
        """Rate limiting middleware"""
        # Skip rate limiting for management endpoints
        if request.path.startswith('/gateway/'):
            return await handler(request)
        
        route_config = await self.find_matching_route(request)
        
        if route_config:
            # Use IP address as identifier (could also use user ID if authenticated)
            identifier = request.remote
            
            if not self.rate_limiter.is_allowed(identifier, route_config.rate_limit_per_minute):
                return web.Response(text="Rate limit exceeded", status=429)
        
        return await handler(request)
    
    @web.middleware
    async def metrics_middleware(self, request: web.Request, handler):
        """Metrics collection middleware"""
        # This middleware is handled in the main request handler
        return await handler(request)
    
    # Authentication handlers
    async def no_auth(self, request: web.Request) -> Dict[str, Any]:
        """No authentication required"""
        return {'success': True}
    
    async def api_key_auth(self, request: web.Request) -> Dict[str, Any]:
        """API key authentication"""
        api_key = request.headers.get('X-API-Key') or request.query.get('api_key')
        
        if not api_key:
            return {'success': False, 'error': 'API key required'}
        
        # Validate API key (implement your logic here)
        if api_key == 'valid_api_key':
            return {'success': True, 'user': {'api_key': api_key}}
        
        return {'success': False, 'error': 'Invalid API key'}
    
    async def jwt_auth(self, request: web.Request) -> Dict[str, Any]:
        """JWT authentication"""
        auth_header = request.headers.get('Authorization', '')
        
        if not auth_header.startswith('Bearer '):
            return {'success': False, 'error': 'Bearer token required'}
        
        token = auth_header.split(' ', 1)[1]
        
        try:
            # Decode JWT (implement your logic here)
            payload = jwt.decode(token, 'secret', algorithms=['HS256'])
            return {'success': True, 'user': payload}
        except jwt.InvalidTokenError:
            return {'success': False, 'error': 'Invalid token'}
    
    async def oauth_auth(self, request: web.Request) -> Dict[str, Any]:
        """OAuth authentication"""
        # Implement OAuth validation
        return {'success': False, 'error': 'OAuth not implemented'}
    
    async def custom_auth(self, request: web.Request) -> Dict[str, Any]:
        """Custom authentication"""
        # Implement custom authentication logic
        return {'success': True}
    
    # Management endpoints
    async def health_check(self, request: web.Request) -> web.Response:
        """Gateway health check"""
        return web.json_response({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'services': len(self.service_instances),
            'routes': len(self.routes)
        })
    
    async def list_routes(self, request: web.Request) -> web.Response:
        """List all configured routes"""
        routes_data = {}
        for route_key, route_config in self.routes.items():
            routes_data[route_key] = asdict(route_config)
        
        return web.json_response(routes_data)
    
    async def list_services(self, request: web.Request) -> web.Response:
        """List all service instances"""
        services_data = {}
        for service_name, instances in self.service_instances.items():
            services_data[service_name] = [asdict(instance) for instance in instances]
        
        return web.json_response(services_data)
    
    async def get_metrics(self, request: web.Request) -> web.Response:
        """Get gateway metrics"""
        recent_metrics = self.request_metrics[-1000:]  # Last 1000 requests
        
        if not recent_metrics:
            return web.json_response({'message': 'No metrics available'})
        
        # Calculate statistics
        response_times = [m.response_time_ms for m in recent_metrics if m.response_time_ms > 0]
        status_codes = [m.status_code for m in recent_metrics if m.status_code > 0]
        
        metrics = {
            'total_requests': len(recent_metrics),
            'avg_response_time_ms': statistics.mean(response_times) if response_times else 0,
            'p95_response_time_ms': statistics.quantiles(response_times, n=20)[18] if len(response_times) > 20 else 0,
            'error_rate': len([s for s in status_codes if s >= 400]) / len(status_codes) if status_codes else 0,
            'requests_per_service': {},
            'status_code_distribution': {}
        }
        
        # Group by service
        for metric in recent_metrics:
            service = metric.target_service
            metrics['requests_per_service'][service] = metrics['requests_per_service'].get(service, 0) + 1
        
        # Status code distribution
        for code in status_codes:
            code_range = f"{code//100}xx"
            metrics['status_code_distribution'][code_range] = metrics['status_code_distribution'].get(code_range, 0) + 1
        
        return web.json_response(metrics)
    
    async def get_config(self, request: web.Request) -> web.Response:
        """Get gateway configuration"""
        return web.json_response({
            'port': self.port,
            'auto_configure_enabled': self.auto_configure_enabled,
            'route_refresh_interval': self.route_refresh_interval,
            'load_balancer_config': asdict(self.load_balancer.config),
            'services_discovered': len(self.discovery.services),
            'routes_configured': len(self.routes)
        })
    
    async def refresh_routes(self, request: web.Request) -> web.Response:
        """Manually refresh routes"""
        await self.auto_configure_routes()
        return web.json_response({
            'message': 'Routes refreshed',
            'routes_count': len(self.routes),
            'services_count': len(self.service_instances)
        })
    
    async def get_circuit_breakers(self, request: web.Request) -> web.Response:
        """Get circuit breaker status"""
        circuit_breakers = {}
        
        for service_name, instances in self.service_instances.items():
            circuit_breakers[service_name] = []
            for instance in instances:
                circuit_breakers[service_name].append({
                    'instance': f"{instance.host}:{instance.port}",
                    'state': instance.circuit_breaker_state,
                    'failures': instance.circuit_breaker_failures,
                    'last_failure': instance.circuit_breaker_last_failure.isoformat() if instance.circuit_breaker_last_failure else None,
                    'success_rate': ((instance.total_requests - instance.failed_requests) / instance.total_requests * 100) if instance.total_requests > 0 else 100
                })
        
        return web.json_response(circuit_breakers)
    
    # Background tasks
    async def route_refresh_task(self):
        """Background task to refresh routes periodically"""
        while True:
            try:
                await asyncio.sleep(self.route_refresh_interval)
                if self.auto_configure_enabled:
                    await self.auto_configure_routes()
                    logging.info(f"Routes refreshed: {len(self.routes)} routes configured")
            except Exception as e:
                logging.error(f"Route refresh error: {e}")
    
    async def metrics_collection_task(self):
        """Background task to collect and clean up metrics"""
        while True:
            try:
                await asyncio.sleep(300)  # 5 minutes
                
                # Keep only recent metrics
                cutoff_time = datetime.now() - timedelta(hours=24)
                self.request_metrics = [
                    m for m in self.request_metrics 
                    if m.start_time > cutoff_time
                ]
                
                logging.info(f"Metrics cleanup: {len(self.request_metrics)} metrics retained")
                
            except Exception as e:
                logging.error(f"Metrics collection error: {e}")
    
    async def start_server(self):
        """Start the API Gateway server"""
        await self.initialize()
        
        runner = web.AppRunner(self.app)
        await runner.setup()
        
        site = web.TCPSite(runner, '0.0.0.0', self.port)
        await site.start()
        
        print(f"API Gateway running on port {self.port}")
        
        # Keep running
        try:
            await asyncio.Future()  # Run forever
        finally:
            await runner.cleanup()

# Example usage
async def main():
    discovery = ServiceDiscovery()
    health_monitor = HealthMonitor(discovery)
    gateway = APIGateway(discovery, health_monitor, port=8100)
    
    await gateway.start_server()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())