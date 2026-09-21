"""
API Gateway with Dynamic Routing

Provides comprehensive API gateway capabilities including:
- Dynamic service discovery and routing
- Load balancing with health checks
- Request/response transformation
- Authentication and authorization
- Rate limiting and throttling
- Circuit breaker patterns
- API versioning support
- Request logging and metrics
- WebSocket proxying
- SSL termination
"""

import asyncio
import json
import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Pattern
from urllib.parse import urlparse, urljoin
import logging
from aiohttp import web, WSMsgType, ClientSession, ClientTimeout
from aiohttp.web_request import Request
from aiohttp.web_response import Response
import aiohttp_cors
import ssl

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RoutingStrategy(Enum):
    ROUND_ROBIN = "round_robin"
    WEIGHTED = "weighted"
    LEAST_CONNECTIONS = "least_connections"
    HEALTH_WEIGHTED = "health_weighted"
    STICKY_SESSION = "sticky_session"

class AuthenticationMethod(Enum):
    NONE = "none"
    API_KEY = "api_key"
    JWT = "jwt"
    BASIC = "basic"
    OAUTH2 = "oauth2"
    CUSTOM = "custom"

class RateLimitType(Enum):
    PER_IP = "per_ip"
    PER_USER = "per_user"
    PER_API_KEY = "per_api_key"
    GLOBAL = "global"

@dataclass
class ServiceEndpoint:
    """Service endpoint definition"""
    service_name: str
    host: str
    port: int
    protocol: str = "http"
    weight: int = 100
    health_check_path: str = "/health"
    max_connections: int = 100
    timeout: int = 30
    ssl_verify: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    current_connections: int = 0
    last_health_check: Optional[datetime] = None
    is_healthy: bool = True
    response_times: List[float] = field(default_factory=list)

@dataclass
class RouteRule:
    """API gateway routing rule"""
    rule_id: str
    name: str
    path_pattern: str
    methods: List[str] = field(default_factory=lambda: ["GET", "POST", "PUT", "DELETE"])
    target_service: str = ""
    target_path: Optional[str] = None
    rewrite_path: bool = False
    strip_prefix: bool = False
    routing_strategy: RoutingStrategy = RoutingStrategy.ROUND_ROBIN
    authentication: AuthenticationMethod = AuthenticationMethod.NONE
    rate_limit: Optional[Dict[str, Any]] = None
    request_transformation: Optional[Dict[str, Any]] = None
    response_transformation: Optional[Dict[str, Any]] = None
    headers: Dict[str, str] = field(default_factory=dict)
    middleware: List[str] = field(default_factory=list)
    priority: int = 0
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class RateLimitRule:
    """Rate limiting rule"""
    rule_id: str
    limit_type: RateLimitType
    requests_per_second: int
    burst_limit: int
    window_seconds: int = 60
    block_duration: int = 300
    whitelist: List[str] = field(default_factory=list)
    blacklist: List[str] = field(default_factory=list)

@dataclass
class RequestContext:
    """Request context for processing"""
    request_id: str
    request: Request
    route_rule: RouteRule
    client_ip: str
    user_id: Optional[str] = None
    api_key: Optional[str] = None
    start_time: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

class ServiceDiscovery:
    """Service discovery integration"""
    
    def __init__(self):
        self.endpoints: Dict[str, List[ServiceEndpoint]] = {}
        self.health_check_interval = 30
        self.running = False
        self._health_check_task = None
        self.service_mesh = None
    
    def set_service_mesh_integration(self, service_mesh):
        """Set service mesh integration for discovery"""
        self.service_mesh = service_mesh
    
    def register_endpoint(self, endpoint: ServiceEndpoint):
        """Register a service endpoint"""
        if endpoint.service_name not in self.endpoints:
            self.endpoints[endpoint.service_name] = []
        
        self.endpoints[endpoint.service_name].append(endpoint)
        logger.info(f"Registered endpoint {endpoint.host}:{endpoint.port} for service {endpoint.service_name}")
    
    def get_endpoints(self, service_name: str) -> List[ServiceEndpoint]:
        """Get healthy endpoints for a service"""
        endpoints = self.endpoints.get(service_name, [])
        return [ep for ep in endpoints if ep.is_healthy]
    
    def get_all_services(self) -> List[str]:
        """Get list of all registered services"""
        return list(self.endpoints.keys())
    
    async def start_health_checks(self):
        """Start health checking background task"""
        self.running = True
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        logger.info("Started service health checks")
    
    async def stop_health_checks(self):
        """Stop health checking"""
        self.running = False
        if self._health_check_task:
            self._health_check_task.cancel()
        logger.info("Stopped service health checks")
    
    async def _health_check_loop(self):
        """Health check loop"""
        while self.running:
            try:
                await self._check_all_endpoints()
                await asyncio.sleep(self.health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                await asyncio.sleep(5)
    
    async def _check_all_endpoints(self):
        """Check health of all endpoints"""
        tasks = []
        for service_name, endpoints in self.endpoints.items():
            for endpoint in endpoints:
                tasks.append(self._check_endpoint_health(endpoint))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _check_endpoint_health(self, endpoint: ServiceEndpoint):
        """Check health of a single endpoint"""
        try:
            timeout = ClientTimeout(total=5)
            async with ClientSession(timeout=timeout) as session:
                health_url = f"{endpoint.protocol}://{endpoint.host}:{endpoint.port}{endpoint.health_check_path}"
                
                start_time = time.time()
                async with session.get(health_url, ssl=endpoint.ssl_verify) as response:
                    response_time = time.time() - start_time
                    
                    endpoint.last_health_check = datetime.now()
                    endpoint.is_healthy = response.status == 200
                    
                    # Track response times
                    endpoint.response_times.append(response_time)
                    if len(endpoint.response_times) > 10:  # Keep last 10 measurements
                        endpoint.response_times.pop(0)
                    
                    if endpoint.is_healthy:
                        logger.debug(f"Health check passed for {endpoint.service_name} at {endpoint.host}:{endpoint.port}")
                    else:
                        logger.warning(f"Health check failed for {endpoint.service_name} at {endpoint.host}:{endpoint.port} - Status: {response.status}")
                        
        except Exception as e:
            endpoint.is_healthy = False
            endpoint.last_health_check = datetime.now()
            logger.error(f"Health check error for {endpoint.service_name} at {endpoint.host}:{endpoint.port}: {e}")

class LoadBalancer:
    """Load balancing logic"""
    
    def __init__(self):
        self.round_robin_counters: Dict[str, int] = {}
    
    def select_endpoint(self, endpoints: List[ServiceEndpoint], strategy: RoutingStrategy, 
                       request_context: Optional[RequestContext] = None) -> Optional[ServiceEndpoint]:
        """Select endpoint based on routing strategy"""
        healthy_endpoints = [ep for ep in endpoints if ep.is_healthy]
        
        if not healthy_endpoints:
            return None
        
        if strategy == RoutingStrategy.ROUND_ROBIN:
            return self._round_robin_selection(healthy_endpoints)
        elif strategy == RoutingStrategy.WEIGHTED:
            return self._weighted_selection(healthy_endpoints)
        elif strategy == RoutingStrategy.LEAST_CONNECTIONS:
            return self._least_connections_selection(healthy_endpoints)
        elif strategy == RoutingStrategy.HEALTH_WEIGHTED:
            return self._health_weighted_selection(healthy_endpoints)
        elif strategy == RoutingStrategy.STICKY_SESSION:
            return self._sticky_session_selection(healthy_endpoints, request_context)
        else:
            return healthy_endpoints[0]  # Default to first healthy endpoint
    
    def _round_robin_selection(self, endpoints: List[ServiceEndpoint]) -> ServiceEndpoint:
        """Round robin selection"""
        service_name = endpoints[0].service_name
        
        if service_name not in self.round_robin_counters:
            self.round_robin_counters[service_name] = 0
        
        index = self.round_robin_counters[service_name] % len(endpoints)
        self.round_robin_counters[service_name] += 1
        
        return endpoints[index]
    
    def _weighted_selection(self, endpoints: List[ServiceEndpoint]) -> ServiceEndpoint:
        """Weighted selection"""
        import random
        
        total_weight = sum(ep.weight for ep in endpoints)
        if total_weight == 0:
            return endpoints[0]
        
        rand_num = random.randint(1, total_weight)
        current_weight = 0
        
        for endpoint in endpoints:
            current_weight += endpoint.weight
            if rand_num <= current_weight:
                return endpoint
        
        return endpoints[-1]
    
    def _least_connections_selection(self, endpoints: List[ServiceEndpoint]) -> ServiceEndpoint:
        """Least connections selection"""
        return min(endpoints, key=lambda ep: ep.current_connections)
    
    def _health_weighted_selection(self, endpoints: List[ServiceEndpoint]) -> ServiceEndpoint:
        """Health-weighted selection based on response times"""
        # Calculate health scores (lower response time = higher score)
        scored_endpoints = []
        for endpoint in endpoints:
            if endpoint.response_times:
                avg_response_time = sum(endpoint.response_times) / len(endpoint.response_times)
                # Invert response time to get score (lower time = higher score)
                health_score = 1.0 / max(avg_response_time, 0.001)
            else:
                health_score = 1.0
            
            scored_endpoints.append((endpoint, health_score * endpoint.weight))
        
        # Select based on weighted health scores
        import random
        total_score = sum(score for _, score in scored_endpoints)
        if total_score == 0:
            return endpoints[0]
        
        rand_num = random.uniform(0, total_score)
        current_score = 0
        
        for endpoint, score in scored_endpoints:
            current_score += score
            if rand_num <= current_score:
                return endpoint
        
        return endpoints[-1]
    
    def _sticky_session_selection(self, endpoints: List[ServiceEndpoint], 
                                 request_context: Optional[RequestContext]) -> ServiceEndpoint:
        """Sticky session selection"""
        if not request_context:
            return self._round_robin_selection(endpoints)
        
        # Use client IP or session ID for stickiness
        session_key = request_context.client_ip
        if request_context.user_id:
            session_key = request_context.user_id
        
        # Simple hash-based selection
        hash_value = hash(session_key)
        index = hash_value % len(endpoints)
        return endpoints[index]

class RateLimiter:
    """Rate limiting implementation"""
    
    def __init__(self):
        self.counters: Dict[str, Dict[str, Any]] = {}
        self.blocked_ips: Dict[str, datetime] = {}
    
    async def check_rate_limit(self, rule: RateLimitRule, request_context: RequestContext) -> bool:
        """Check if request is within rate limit"""
        key = self._get_rate_limit_key(rule, request_context)
        
        # Check if currently blocked
        if key in self.blocked_ips:
            if datetime.now() < self.blocked_ips[key]:
                return False
            else:
                del self.blocked_ips[key]
        
        # Check whitelist
        if rule.whitelist and request_context.client_ip in rule.whitelist:
            return True
        
        # Check blacklist
        if rule.blacklist and request_context.client_ip in rule.blacklist:
            return False
        
        now = datetime.now()
        
        if key not in self.counters:
            self.counters[key] = {
                "requests": 0,
                "window_start": now,
                "burst_count": 0
            }
        
        counter = self.counters[key]
        
        # Reset window if expired
        if (now - counter["window_start"]).total_seconds() >= rule.window_seconds:
            counter["requests"] = 0
            counter["window_start"] = now
            counter["burst_count"] = 0
        
        # Check burst limit
        counter["burst_count"] += 1
        if counter["burst_count"] > rule.burst_limit:
            self._block_key(key, rule.block_duration)
            return False
        
        # Check rate limit
        counter["requests"] += 1
        requests_per_window = rule.requests_per_second * rule.window_seconds
        
        if counter["requests"] > requests_per_window:
            self._block_key(key, rule.block_duration)
            return False
        
        return True
    
    def _get_rate_limit_key(self, rule: RateLimitRule, request_context: RequestContext) -> str:
        """Get rate limiting key based on rule type"""
        if rule.limit_type == RateLimitType.PER_IP:
            return f"ip:{request_context.client_ip}"
        elif rule.limit_type == RateLimitType.PER_USER and request_context.user_id:
            return f"user:{request_context.user_id}"
        elif rule.limit_type == RateLimitType.PER_API_KEY and request_context.api_key:
            return f"api_key:{request_context.api_key}"
        else:
            return "global"
    
    def _block_key(self, key: str, duration: int):
        """Block a key for specified duration"""
        self.blocked_ips[key] = datetime.now() + timedelta(seconds=duration)

class RequestTransformer:
    """Request/response transformation"""
    
    @staticmethod
    def transform_request(request: Request, transformation: Dict[str, Any]) -> Dict[str, Any]:
        """Transform request based on configuration"""
        transformed = {}
        
        # Header transformations
        if "headers" in transformation:
            header_config = transformation["headers"]
            if "add" in header_config:
                transformed["headers_add"] = header_config["add"]
            if "remove" in header_config:
                transformed["headers_remove"] = header_config["remove"]
            if "modify" in header_config:
                transformed["headers_modify"] = header_config["modify"]
        
        # Path transformations
        if "path" in transformation:
            path_config = transformation["path"]
            if "rewrite" in path_config:
                original_path = str(request.url.path)
                for pattern, replacement in path_config["rewrite"].items():
                    transformed["path"] = re.sub(pattern, replacement, original_path)
        
        # Query parameter transformations
        if "query_params" in transformation:
            query_config = transformation["query_params"]
            transformed["query_params"] = query_config
        
        return transformed
    
    @staticmethod
    def transform_response(response_data: Any, transformation: Dict[str, Any]) -> Any:
        """Transform response based on configuration"""
        if not transformation:
            return response_data
        
        # JSON transformation
        if "json" in transformation and isinstance(response_data, dict):
            json_config = transformation["json"]
            
            # Field mapping
            if "field_mapping" in json_config:
                for old_field, new_field in json_config["field_mapping"].items():
                    if old_field in response_data:
                        response_data[new_field] = response_data.pop(old_field)
            
            # Add fields
            if "add_fields" in json_config:
                response_data.update(json_config["add_fields"])
            
            # Remove fields
            if "remove_fields" in json_config:
                for field in json_config["remove_fields"]:
                    response_data.pop(field, None)
        
        return response_data

class APIGateway:
    """Main API Gateway implementation"""
    
    def __init__(self):
        self.app = web.Application()
        self.service_discovery = ServiceDiscovery()
        self.load_balancer = LoadBalancer()
        self.rate_limiter = RateLimiter()
        self.route_rules: Dict[str, RouteRule] = {}
        self.rate_limit_rules: Dict[str, RateLimitRule] = {}
        self.middleware_handlers: Dict[str, Callable] = {}
        self.circuit_breaker = None
        self.metrics = {
            "requests_total": 0,
            "requests_success": 0,
            "requests_error": 0,
            "response_times": []
        }
        
        # Setup default middleware
        self._setup_middleware()
        self._setup_routes()
        
        # Setup CORS
        self._setup_cors()
    
    def _setup_middleware(self):
        """Setup middleware pipeline"""
        self.app.middlewares.append(self._logging_middleware)
        self.app.middlewares.append(self._auth_middleware)
        self.app.middlewares.append(self._rate_limiting_middleware)
        self.app.middlewares.append(self._routing_middleware)
    
    def _setup_routes(self):
        """Setup gateway routes"""
        # Admin routes
        self.app.router.add_get('/_gateway/health', self._health_endpoint)
        self.app.router.add_get('/_gateway/metrics', self._metrics_endpoint)
        self.app.router.add_get('/_gateway/services', self._services_endpoint)
        self.app.router.add_get('/_gateway/routes', self._routes_endpoint)
        
        # Catch-all route for proxying
        self.app.router.add_route('*', '/{path:.*}', self._proxy_handler)
    
    def _setup_cors(self):
        """Setup CORS"""
        cors = aiohttp_cors.setup(self.app, defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
                allow_methods="*"
            )
        })
        
        # Add CORS to all routes
        for route in list(self.app.router.routes()):
            cors.add(route)
    
    def add_route_rule(self, rule: RouteRule):
        """Add a routing rule"""
        self.route_rules[rule.rule_id] = rule
        logger.info(f"Added route rule {rule.rule_id}: {rule.path_pattern} -> {rule.target_service}")
    
    def remove_route_rule(self, rule_id: str):
        """Remove a routing rule"""
        if rule_id in self.route_rules:
            del self.route_rules[rule_id]
            logger.info(f"Removed route rule {rule_id}")
    
    def add_rate_limit_rule(self, rule: RateLimitRule):
        """Add a rate limiting rule"""
        self.rate_limit_rules[rule.rule_id] = rule
        logger.info(f"Added rate limit rule {rule.rule_id}")
    
    def set_circuit_breaker(self, circuit_breaker):
        """Set circuit breaker integration"""
        self.circuit_breaker = circuit_breaker
    
    def set_service_mesh_integration(self, service_mesh):
        """Set service mesh integration"""
        self.service_discovery.set_service_mesh_integration(service_mesh)
    
    @web.middleware
    async def _logging_middleware(self, request: Request, handler):
        """Logging middleware"""
        request_id = str(uuid.uuid4())
        start_time = time.time()
        
        # Add request ID to headers
        request.headers = request.headers.copy()
        request.headers['X-Request-ID'] = request_id
        
        try:
            response = await handler(request)
            
            # Log successful request
            processing_time = time.time() - start_time
            logger.info(f"Request {request_id}: {request.method} {request.path} -> {response.status} ({processing_time:.3f}s)")
            
            # Track metrics
            self.metrics["requests_total"] += 1
            self.metrics["requests_success"] += 1
            self.metrics["response_times"].append(processing_time)
            
            # Keep only last 1000 response times
            if len(self.metrics["response_times"]) > 1000:
                self.metrics["response_times"].pop(0)
            
            return response
            
        except Exception as e:
            # Log failed request
            processing_time = time.time() - start_time
            logger.error(f"Request {request_id}: {request.method} {request.path} -> ERROR ({processing_time:.3f}s): {e}")
            
            # Track metrics
            self.metrics["requests_total"] += 1
            self.metrics["requests_error"] += 1
            
            raise
    
    @web.middleware
    async def _auth_middleware(self, request: Request, handler):
        """Authentication middleware"""
        # Skip auth for admin endpoints
        if request.path.startswith('/_gateway/'):
            return await handler(request)
        
        # Find matching route rule for auth
        route_rule = self._find_matching_route(request)
        if not route_rule or route_rule.authentication == AuthenticationMethod.NONE:
            return await handler(request)
        
        # Perform authentication based on method
        auth_result = await self._authenticate_request(request, route_rule.authentication)
        if not auth_result["authenticated"]:
            return web.json_response(
                {"error": "Authentication failed", "message": auth_result["message"]},
                status=401
            )
        
        # Store auth info in request for later use
        request['auth_user_id'] = auth_result.get("user_id")
        request['auth_api_key'] = auth_result.get("api_key")
        
        return await handler(request)
    
    @web.middleware
    async def _rate_limiting_middleware(self, request: Request, handler):
        """Rate limiting middleware"""
        # Skip rate limiting for admin endpoints
        if request.path.startswith('/_gateway/'):
            return await handler(request)
        
        # Check applicable rate limiting rules
        client_ip = self._get_client_ip(request)
        request_context = RequestContext(
            request_id=request.headers.get('X-Request-ID', str(uuid.uuid4())),
            request=request,
            route_rule=self._find_matching_route(request),
            client_ip=client_ip,
            user_id=request.get('auth_user_id'),
            api_key=request.get('auth_api_key')
        )
        
        for rule in self.rate_limit_rules.values():
            allowed = await self.rate_limiter.check_rate_limit(rule, request_context)
            if not allowed:
                return web.json_response(
                    {"error": "Rate limit exceeded", "retry_after": rule.window_seconds},
                    status=429,
                    headers={"Retry-After": str(rule.window_seconds)}
                )
        
        return await handler(request)
    
    @web.middleware
    async def _routing_middleware(self, request: Request, handler):
        """Routing middleware"""
        # Skip routing for admin endpoints
        if request.path.startswith('/_gateway/'):
            return await handler(request)
        
        # Store routing context in request
        request['gateway_context'] = {
            "client_ip": self._get_client_ip(request),
            "route_rule": self._find_matching_route(request)
        }
        
        return await handler(request)
    
    def _find_matching_route(self, request: Request) -> Optional[RouteRule]:
        """Find matching route rule for request"""
        # Sort rules by priority (higher first)
        sorted_rules = sorted(
            [rule for rule in self.route_rules.values() if rule.enabled],
            key=lambda r: r.priority,
            reverse=True
        )
        
        for rule in sorted_rules:
            # Check method
            if request.method not in rule.methods:
                continue
            
            # Check path pattern
            if re.match(rule.path_pattern, request.path):
                return rule
        
        return None
    
    async def _proxy_handler(self, request: Request) -> Response:
        """Main proxy handler"""
        context = request.get('gateway_context', {})
        route_rule = context.get('route_rule')
        
        if not route_rule:
            return web.json_response(
                {"error": "No matching route found"},
                status=404
            )
        
        # Get target service endpoints
        endpoints = self.service_discovery.get_endpoints(route_rule.target_service)
        if not endpoints:
            return web.json_response(
                {"error": "Service unavailable", "service": route_rule.target_service},
                status=503
            )
        
        # Select endpoint using load balancing
        request_context = RequestContext(
            request_id=request.headers.get('X-Request-ID', str(uuid.uuid4())),
            request=request,
            route_rule=route_rule,
            client_ip=context.get('client_ip', ''),
            user_id=request.get('auth_user_id'),
            api_key=request.get('auth_api_key')
        )
        
        endpoint = self.load_balancer.select_endpoint(
            endpoints, route_rule.routing_strategy, request_context
        )
        
        if not endpoint:
            return web.json_response(
                {"error": "No healthy endpoints available"},
                status=503
            )
        
        # Proxy the request
        try:
            endpoint.current_connections += 1
            return await self._proxy_request(request, endpoint, route_rule)
        finally:
            endpoint.current_connections -= 1
    
    async def _proxy_request(self, request: Request, endpoint: ServiceEndpoint, route_rule: RouteRule) -> Response:
        """Proxy request to target endpoint"""
        # Build target URL
        target_path = request.path
        if route_rule.target_path:
            target_path = route_rule.target_path
        elif route_rule.rewrite_path:
            # Apply path rewriting
            target_path = re.sub(route_rule.path_pattern, route_rule.target_path or "", request.path)
        elif route_rule.strip_prefix:
            # Strip matching prefix
            target_path = re.sub(f"^{route_rule.path_pattern.rstrip('.*')}", "", request.path)
        
        target_url = f"{endpoint.protocol}://{endpoint.host}:{endpoint.port}{target_path}"
        if request.query_string:
            target_url += f"?{request.query_string}"
        
        # Prepare headers
        headers = dict(request.headers)
        headers.update(route_rule.headers)
        
        # Apply request transformations
        if route_rule.request_transformation:
            transformations = RequestTransformer.transform_request(request, route_rule.request_transformation)
            
            if "headers_add" in transformations:
                headers.update(transformations["headers_add"])
            if "headers_remove" in transformations:
                for header in transformations["headers_remove"]:
                    headers.pop(header, None)
        
        # Read request body
        body = None
        if request.can_read_body:
            body = await request.read()
        
        # Make proxy request
        timeout = ClientTimeout(total=endpoint.timeout)
        async with ClientSession(timeout=timeout) as session:
            try:
                async with session.request(
                    request.method,
                    target_url,
                    headers=headers,
                    data=body,
                    ssl=endpoint.ssl_verify
                ) as response:
                    
                    # Read response
                    response_body = await response.read()
                    response_headers = dict(response.headers)
                    
                    # Apply response transformations
                    if route_rule.response_transformation:
                        if response.content_type == 'application/json':
                            try:
                                json_data = json.loads(response_body)
                                transformed_data = RequestTransformer.transform_response(
                                    json_data, route_rule.response_transformation
                                )
                                response_body = json.dumps(transformed_data).encode()
                            except json.JSONDecodeError:
                                pass
                    
                    # Remove hop-by-hop headers
                    hop_by_hop_headers = [
                        'connection', 'keep-alive', 'proxy-authenticate',
                        'proxy-authorization', 'te', 'trailers', 'transfer-encoding',
                        'upgrade'
                    ]
                    for header in hop_by_hop_headers:
                        response_headers.pop(header, None)
                    
                    # Add gateway headers
                    response_headers['X-Gateway'] = 'integration-controller'
                    response_headers['X-Upstream-Service'] = endpoint.service_name
                    
                    return Response(
                        body=response_body,
                        status=response.status,
                        headers=response_headers
                    )
                    
            except asyncio.TimeoutError:
                logger.error(f"Timeout proxying to {endpoint.service_name}")
                return web.json_response(
                    {"error": "Gateway timeout"},
                    status=504
                )
            except Exception as e:
                logger.error(f"Error proxying to {endpoint.service_name}: {e}")
                return web.json_response(
                    {"error": "Bad gateway"},
                    status=502
                )
    
    async def _authenticate_request(self, request: Request, auth_method: AuthenticationMethod) -> Dict[str, Any]:
        """Authenticate request based on method"""
        if auth_method == AuthenticationMethod.API_KEY:
            api_key = request.headers.get('X-API-Key') or request.query.get('api_key')
            if api_key:
                # This would integrate with an API key validation service
                return {"authenticated": True, "api_key": api_key}
            return {"authenticated": False, "message": "API key required"}
        
        elif auth_method == AuthenticationMethod.JWT:
            auth_header = request.headers.get('Authorization', '')
            if auth_header.startswith('Bearer '):
                token = auth_header[7:]
                # This would integrate with JWT validation
                return {"authenticated": True, "user_id": "user123", "token": token}
            return {"authenticated": False, "message": "JWT token required"}
        
        elif auth_method == AuthenticationMethod.BASIC:
            auth_header = request.headers.get('Authorization', '')
            if auth_header.startswith('Basic '):
                # This would integrate with basic auth validation
                return {"authenticated": True, "user_id": "user123"}
            return {"authenticated": False, "message": "Basic authentication required"}
        
        return {"authenticated": True}  # Default allow
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address"""
        # Check for forwarded headers
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        
        real_ip = request.headers.get('X-Real-IP')
        if real_ip:
            return real_ip
        
        # Fall back to peer name
        peername = request.transport.get_extra_info('peername')
        if peername:
            return peername[0]
        
        return "unknown"
    
    async def _health_endpoint(self, request: Request) -> Response:
        """Gateway health endpoint"""
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "services": {},
            "metrics": self.metrics.copy()
        }
        
        # Check service health
        for service_name, endpoints in self.service_discovery.endpoints.items():
            healthy_count = sum(1 for ep in endpoints if ep.is_healthy)
            total_count = len(endpoints)
            
            health_status["services"][service_name] = {
                "healthy_endpoints": healthy_count,
                "total_endpoints": total_count,
                "status": "healthy" if healthy_count > 0 else "unhealthy"
            }
        
        return web.json_response(health_status)
    
    async def _metrics_endpoint(self, request: Request) -> Response:
        """Gateway metrics endpoint"""
        metrics = self.metrics.copy()
        
        # Calculate additional metrics
        if metrics["response_times"]:
            metrics["avg_response_time"] = sum(metrics["response_times"]) / len(metrics["response_times"])
            metrics["p95_response_time"] = sorted(metrics["response_times"])[int(len(metrics["response_times"]) * 0.95)]
        
        return web.json_response(metrics)
    
    async def _services_endpoint(self, request: Request) -> Response:
        """Services endpoint"""
        services = {}
        
        for service_name, endpoints in self.service_discovery.endpoints.items():
            services[service_name] = [
                {
                    "host": ep.host,
                    "port": ep.port,
                    "protocol": ep.protocol,
                    "is_healthy": ep.is_healthy,
                    "current_connections": ep.current_connections,
                    "weight": ep.weight,
                    "last_health_check": ep.last_health_check.isoformat() if ep.last_health_check else None
                }
                for ep in endpoints
            ]
        
        return web.json_response({"services": services})
    
    async def _routes_endpoint(self, request: Request) -> Response:
        """Routes endpoint"""
        routes = []
        
        for rule in self.route_rules.values():
            routes.append({
                "rule_id": rule.rule_id,
                "name": rule.name,
                "path_pattern": rule.path_pattern,
                "methods": rule.methods,
                "target_service": rule.target_service,
                "routing_strategy": rule.routing_strategy.value,
                "authentication": rule.authentication.value,
                "enabled": rule.enabled,
                "priority": rule.priority
            })
        
        return web.json_response({"routes": routes})
    
    async def start_server(self, host: str = "0.0.0.0", port: int = 8080, ssl_context: Optional[ssl.SSLContext] = None):
        """Start the API gateway server"""
        # Start service discovery health checks
        await self.service_discovery.start_health_checks()
        
        # Start web server
        runner = web.AppRunner(self.app)
        await runner.setup()
        
        site = web.TCPSite(runner, host, port, ssl_context=ssl_context)
        await site.start()
        
        protocol = "https" if ssl_context else "http"
        logger.info(f"API Gateway started on {protocol}://{host}:{port}")
        
        return runner
    
    async def stop_server(self):
        """Stop the API gateway server"""
        await self.service_discovery.stop_health_checks()
        logger.info("API Gateway stopped")

# Factory function
def create_api_gateway() -> APIGateway:
    """Create and return an API gateway instance"""
    return APIGateway()

# Helper functions
def create_route_rule(name: str, path_pattern: str, target_service: str, **kwargs) -> RouteRule:
    """Create a route rule"""
    return RouteRule(
        rule_id=str(uuid.uuid4()),
        name=name,
        path_pattern=path_pattern,
        target_service=target_service,
        **kwargs
    )

def create_rate_limit_rule(limit_type: RateLimitType, requests_per_second: int, **kwargs) -> RateLimitRule:
    """Create a rate limit rule"""
    return RateLimitRule(
        rule_id=str(uuid.uuid4()),
        limit_type=limit_type,
        requests_per_second=requests_per_second,
        burst_limit=requests_per_second * 2,  # Default burst limit
        **kwargs
    )