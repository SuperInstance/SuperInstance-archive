#!/usr/bin/env python3
"""
Advanced API Ecosystem Management Service
Comprehensive API lifecycle, governance, and developer experience platform
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
import uuid
import hashlib
from dataclasses import dataclass, asdict
from enum import Enum
import threading
from collections import defaultdict, deque
import websockets
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import uvicorn
from pydantic import BaseModel
import sqlite3
from contextlib import asynccontextmanager
import aiofiles
import aiohttp
import yaml
import jsonschema
from jinja2 import Template
import subprocess
import tempfile

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class APIStatus(Enum):
    DRAFT = "draft"
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"
    DEPRECATED = "deprecated"
    RETIRED = "retired"

class APIType(Enum):
    REST = "rest"
    GRAPHQL = "graphql"
    WEBSOCKET = "websocket"
    GRPC = "grpc"
    EVENT_DRIVEN = "event_driven"

class GovernancePolicy(Enum):
    SECURITY = "security"
    VERSIONING = "versioning"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    MONITORING = "monitoring"
    DEPRECATION = "deprecation"

class DeveloperTier(Enum):
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"

@dataclass
class APIDefinition:
    api_id: str
    name: str
    description: str
    version: str
    type: APIType
    status: APIStatus
    owner: str
    team: str
    specification: Dict[str, Any]
    endpoints: List[Dict[str, Any]]
    dependencies: List[str]
    consumers: Set[str]
    tags: List[str]
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime]

@dataclass
class APIContract:
    contract_id: str
    api_id: str
    consumer_id: str
    sla_tier: DeveloperTier
    rate_limits: Dict[str, int]
    quotas: Dict[str, int]
    permissions: List[str]
    created_at: datetime
    expires_at: Optional[datetime]
    is_active: bool

@dataclass
class APIMetrics:
    api_id: str
    timestamp: datetime
    requests_per_minute: int
    avg_response_time_ms: float
    error_rate: float
    success_rate: float
    p95_latency_ms: float
    active_consumers: int
    data_transfer_mb: float

@dataclass
class DeveloperPortalUser:
    user_id: str
    email: str
    name: str
    organization: str
    tier: DeveloperTier
    api_keys: List[str]
    subscriptions: List[str]
    usage_stats: Dict[str, Any]
    created_at: datetime
    last_active: datetime

class APISpecValidator:
    """Validates API specifications against standards"""
    
    def __init__(self):
        self.openapi_schema = self._load_openapi_schema()
        self.governance_rules = {
            GovernancePolicy.SECURITY: self._security_rules,
            GovernancePolicy.VERSIONING: self._versioning_rules,
            GovernancePolicy.DOCUMENTATION: self._documentation_rules,
            GovernancePolicy.TESTING: self._testing_rules
        }
    
    def _load_openapi_schema(self) -> Dict[str, Any]:
        """Load OpenAPI 3.0 schema for validation"""
        # Simplified OpenAPI schema
        return {
            "type": "object",
            "required": ["openapi", "info", "paths"],
            "properties": {
                "openapi": {"type": "string", "pattern": "^3\\.0\\.\\d+$"},
                "info": {
                    "type": "object",
                    "required": ["title", "version"],
                    "properties": {
                        "title": {"type": "string"},
                        "version": {"type": "string"},
                        "description": {"type": "string"}
                    }
                },
                "paths": {"type": "object"}
            }
        }
    
    def validate_specification(self, spec: Dict[str, Any], api_type: APIType) -> Dict[str, Any]:
        """Validate API specification"""
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "score": 100
        }
        
        try:
            if api_type == APIType.REST:
                self._validate_openapi_spec(spec, validation_result)
            elif api_type == APIType.GRAPHQL:
                self._validate_graphql_spec(spec, validation_result)
            elif api_type == APIType.GRPC:
                self._validate_grpc_spec(spec, validation_result)
            
            # Apply governance rules
            for policy, rule_func in self.governance_rules.items():
                rule_func(spec, validation_result)
            
        except Exception as e:
            validation_result["valid"] = False
            validation_result["errors"].append(f"Validation error: {str(e)}")
            validation_result["score"] = 0
        
        return validation_result
    
    def _validate_openapi_spec(self, spec: Dict[str, Any], result: Dict[str, Any]):
        """Validate OpenAPI specification"""
        try:
            jsonschema.validate(spec, self.openapi_schema)
        except jsonschema.ValidationError as e:
            result["valid"] = False
            result["errors"].append(f"OpenAPI validation error: {e.message}")
            result["score"] -= 20
        
        # Check for common issues
        if "paths" in spec:
            for path, methods in spec["paths"].items():
                for method, operation in methods.items():
                    if method.upper() in ["GET", "POST", "PUT", "DELETE"]:
                        # Check for response definitions
                        if "responses" not in operation:
                            result["warnings"].append(f"Missing responses for {method.upper()} {path}")
                            result["score"] -= 5
                        
                        # Check for parameter descriptions
                        if "parameters" in operation:
                            for param in operation["parameters"]:
                                if "description" not in param:
                                    result["warnings"].append(f"Missing parameter description in {method.upper()} {path}")
                                    result["score"] -= 2
    
    def _validate_graphql_spec(self, spec: Dict[str, Any], result: Dict[str, Any]):
        """Validate GraphQL specification"""
        required_fields = ["schema", "types"]
        
        for field in required_fields:
            if field not in spec:
                result["errors"].append(f"Missing required field: {field}")
                result["valid"] = False
                result["score"] -= 25
    
    def _validate_grpc_spec(self, spec: Dict[str, Any], result: Dict[str, Any]):
        """Validate gRPC specification"""
        if "proto_file" not in spec:
            result["errors"].append("Missing proto_file definition")
            result["valid"] = False
            result["score"] -= 50
    
    def _security_rules(self, spec: Dict[str, Any], result: Dict[str, Any]):
        """Apply security governance rules"""
        if "security" not in spec:
            result["warnings"].append("No security schemes defined")
            result["score"] -= 15
        
        if "securityDefinitions" in spec or "components" in spec:
            # Check for proper authentication schemes
            pass
        else:
            result["warnings"].append("No authentication schemes found")
            result["score"] -= 10
    
    def _versioning_rules(self, spec: Dict[str, Any], result: Dict[str, Any]):
        """Apply versioning governance rules"""
        if "info" in spec and "version" in spec["info"]:
            version = spec["info"]["version"]
            if not self._is_semantic_version(version):
                result["warnings"].append(f"Version {version} is not semantic (e.g., 1.0.0)")
                result["score"] -= 5
        
        # Check for version in paths
        has_versioned_paths = False
        if "paths" in spec:
            for path in spec["paths"].keys():
                if "/v" in path.lower():
                    has_versioned_paths = True
                    break
        
        if not has_versioned_paths:
            result["warnings"].append("No versioned paths found (consider /v1/, /v2/, etc.)")
            result["score"] -= 5
    
    def _documentation_rules(self, spec: Dict[str, Any], result: Dict[str, Any]):
        """Apply documentation governance rules"""
        if "info" in spec:
            if "description" not in spec["info"]:
                result["warnings"].append("Missing API description")
                result["score"] -= 10
            
            if "contact" not in spec["info"]:
                result["warnings"].append("Missing contact information")
                result["score"] -= 5
        
        # Check for endpoint documentation
        if "paths" in spec:
            undocumented_endpoints = 0
            for path, methods in spec["paths"].items():
                for method, operation in methods.items():
                    if "description" not in operation and "summary" not in operation:
                        undocumented_endpoints += 1
            
            if undocumented_endpoints > 0:
                result["warnings"].append(f"{undocumented_endpoints} endpoints lack documentation")
                result["score"] -= min(20, undocumented_endpoints * 2)
    
    def _testing_rules(self, spec: Dict[str, Any], result: Dict[str, Any]):
        """Apply testing governance rules"""
        if "paths" in spec:
            for path, methods in spec["paths"].items():
                for method, operation in methods.items():
                    if "examples" not in operation:
                        result["warnings"].append(f"Missing examples for {method.upper()} {path}")
                        result["score"] -= 2
    
    def _is_semantic_version(self, version: str) -> bool:
        """Check if version follows semantic versioning"""
        import re
        pattern = r'^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)))?(?:\+([0-9a-zA-Z-]+))?$'
        return bool(re.match(pattern, version))

class APIGateway:
    """API Gateway with routing and middleware"""
    
    def __init__(self):
        self.routes: Dict[str, Dict[str, Any]] = {}
        self.middleware_stack = [
            self._authentication_middleware,
            self._rate_limiting_middleware,
            self._logging_middleware,
            self._metrics_middleware
        ]
        self.rate_limits: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self.metrics_collector = defaultdict(list)
    
    def register_api_route(self, api_id: str, path_pattern: str, 
                          upstream_url: str, methods: List[str]):
        """Register API route"""
        route_id = f"{api_id}_{hashlib.md5(path_pattern.encode()).hexdigest()[:8]}"
        
        self.routes[route_id] = {
            "api_id": api_id,
            "pattern": path_pattern,
            "upstream": upstream_url,
            "methods": methods,
            "created_at": datetime.now()
        }
        
        logger.info(f"Registered route {path_pattern} -> {upstream_url}")
    
    async def handle_request(self, request: Request, api_key: str) -> Dict[str, Any]:
        """Handle incoming API request through gateway"""
        start_time = time.time()
        
        try:
            # Find matching route
            route = self._find_matching_route(request.url.path, request.method)
            
            if not route:
                return {
                    "error": "Route not found",
                    "status_code": 404
                }
            
            # Apply middleware
            for middleware in self.middleware_stack:
                result = await middleware(request, route, api_key)
                if result.get("error"):
                    return result
            
            # Forward request to upstream
            response = await self._forward_request(request, route)
            
            # Record metrics
            duration = time.time() - start_time
            self._record_metrics(route["api_id"], request.method, duration, 200)
            
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            if route:
                self._record_metrics(route["api_id"], request.method, duration, 500)
            
            logger.error(f"Gateway error: {e}")
            return {
                "error": "Internal gateway error",
                "status_code": 500
            }
    
    def _find_matching_route(self, path: str, method: str) -> Optional[Dict[str, Any]]:
        """Find matching route for request"""
        for route_id, route in self.routes.items():
            if method.upper() in [m.upper() for m in route["methods"]]:
                # Simple pattern matching (could be enhanced with regex)
                if self._path_matches_pattern(path, route["pattern"]):
                    return route
        return None
    
    def _path_matches_pattern(self, path: str, pattern: str) -> bool:
        """Check if path matches pattern"""
        # Simple wildcard matching
        if "*" in pattern:
            pattern_parts = pattern.split("*")
            return path.startswith(pattern_parts[0])
        return path == pattern
    
    async def _authentication_middleware(self, request: Request, route: Dict[str, Any], 
                                       api_key: str) -> Dict[str, Any]:
        """Authentication middleware"""
        if not api_key:
            return {
                "error": "Missing API key",
                "status_code": 401
            }
        
        # Validate API key (simplified)
        if not self._validate_api_key(api_key):
            return {
                "error": "Invalid API key",
                "status_code": 401
            }
        
        return {"success": True}
    
    async def _rate_limiting_middleware(self, request: Request, route: Dict[str, Any],
                                      api_key: str) -> Dict[str, Any]:
        """Rate limiting middleware"""
        api_id = route["api_id"]
        now = time.time()
        
        # Clean old entries
        cutoff = now - 60  # 1 minute window
        if api_key in self.rate_limits:
            self.rate_limits[api_key] = {
                k: v for k, v in self.rate_limits[api_key].items()
                if v > cutoff
            }
        
        # Count requests in window
        request_count = len(self.rate_limits[api_key])
        
        # Check limit (100 requests per minute default)
        if request_count >= 100:
            return {
                "error": "Rate limit exceeded",
                "status_code": 429
            }
        
        # Record request
        self.rate_limits[api_key][str(uuid.uuid4())] = now
        
        return {"success": True}
    
    async def _logging_middleware(self, request: Request, route: Dict[str, Any],
                                api_key: str) -> Dict[str, Any]:
        """Logging middleware"""
        logger.info(f"API Gateway: {request.method} {request.url.path} -> {route['upstream']}")
        return {"success": True}
    
    async def _metrics_middleware(self, request: Request, route: Dict[str, Any],
                                api_key: str) -> Dict[str, Any]:
        """Metrics collection middleware"""
        # Metrics are recorded in handle_request
        return {"success": True}
    
    async def _forward_request(self, request: Request, route: Dict[str, Any]) -> Dict[str, Any]:
        """Forward request to upstream service"""
        # Simplified request forwarding
        try:
            async with aiohttp.ClientSession() as session:
                url = route["upstream"] + request.url.path
                
                async with session.request(
                    request.method,
                    url,
                    params=request.query_params,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    content = await response.text()
                    
                    return {
                        "content": content,
                        "status_code": response.status,
                        "headers": dict(response.headers)
                    }
                    
        except Exception as e:
            return {
                "error": f"Upstream error: {str(e)}",
                "status_code": 502
            }
    
    def _validate_api_key(self, api_key: str) -> bool:
        """Validate API key (simplified)"""
        # In real implementation, would check against database
        return len(api_key) >= 20
    
    def _record_metrics(self, api_id: str, method: str, duration: float, status_code: int):
        """Record request metrics"""
        metric = {
            "timestamp": datetime.now(),
            "api_id": api_id,
            "method": method,
            "duration": duration,
            "status_code": status_code
        }
        self.metrics_collector[api_id].append(metric)

class DeveloperPortal:
    """Developer portal for API discovery and management"""
    
    def __init__(self):
        self.users: Dict[str, DeveloperPortalUser] = {}
        self.api_keys: Dict[str, str] = {}  # key -> user_id
        self.documentation_cache: Dict[str, str] = {}
        
    def register_developer(self, email: str, name: str, organization: str) -> str:
        """Register new developer"""
        user_id = str(uuid.uuid4())
        
        user = DeveloperPortalUser(
            user_id=user_id,
            email=email,
            name=name,
            organization=organization,
            tier=DeveloperTier.BRONZE,
            api_keys=[],
            subscriptions=[],
            usage_stats={},
            created_at=datetime.now(),
            last_active=datetime.now()
        )
        
        self.users[user_id] = user
        logger.info(f"Registered developer: {email}")
        
        return user_id
    
    def generate_api_key(self, user_id: str) -> str:
        """Generate API key for user"""
        if user_id not in self.users:
            raise ValueError("User not found")
        
        api_key = f"ak_{secrets.token_urlsafe(32)}"
        
        self.users[user_id].api_keys.append(api_key)
        self.api_keys[api_key] = user_id
        
        logger.info(f"Generated API key for user {user_id}")
        return api_key
    
    def subscribe_to_api(self, user_id: str, api_id: str) -> bool:
        """Subscribe user to API"""
        if user_id not in self.users:
            return False
        
        user = self.users[user_id]
        
        if api_id not in user.subscriptions:
            user.subscriptions.append(api_id)
            logger.info(f"User {user_id} subscribed to API {api_id}")
        
        return True
    
    def generate_documentation(self, api_definition: APIDefinition) -> str:
        """Generate HTML documentation for API"""
        if api_definition.api_id in self.documentation_cache:
            return self.documentation_cache[api_definition.api_id]
        
        template = Template('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>{{ api.name }} - API Documentation</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                h1 { color: #333; }
                h2 { color: #666; border-bottom: 1px solid #eee; }
                .endpoint { background: #f5f5f5; padding: 15px; margin: 10px 0; }
                .method { font-weight: bold; color: #007cba; }
                .description { color: #666; margin: 5px 0; }
                code { background: #f0f0f0; padding: 2px 5px; }
            </style>
        </head>
        <body>
            <h1>{{ api.name }}</h1>
            <p>{{ api.description }}</p>
            
            <h2>API Information</h2>
            <ul>
                <li><strong>Version:</strong> {{ api.version }}</li>
                <li><strong>Type:</strong> {{ api.type.value }}</li>
                <li><strong>Status:</strong> {{ api.status.value }}</li>
                <li><strong>Owner:</strong> {{ api.owner }}</li>
            </ul>
            
            <h2>Endpoints</h2>
            {% for endpoint in api.endpoints %}
            <div class="endpoint">
                <div class="method">{{ endpoint.method }} {{ endpoint.path }}</div>
                <div class="description">{{ endpoint.description }}</div>
                {% if endpoint.parameters %}
                <h4>Parameters:</h4>
                <ul>
                    {% for param in endpoint.parameters %}
                    <li><code>{{ param.name }}</code> ({{ param.type }}) - {{ param.description }}</li>
                    {% endfor %}
                </ul>
                {% endif %}
            </div>
            {% endfor %}
        </body>
        </html>
        ''')
        
        html = template.render(api=api_definition)
        self.documentation_cache[api_definition.api_id] = html
        
        return html

class APIEcosystemManager:
    """Main API ecosystem management service"""
    
    def __init__(self):
        self.apis: Dict[str, APIDefinition] = {}
        self.contracts: Dict[str, APIContract] = {}
        self.validator = APISpecValidator()
        self.gateway = APIGateway()
        self.portal = DeveloperPortal()
        self.metrics: Dict[str, List[APIMetrics]] = defaultdict(list)
        
        # Initialize database
        self._init_database()
        
        # Background tasks
        self._start_background_tasks()
        
        logger.info("API Ecosystem Manager initialized")
    
    def _init_database(self):
        """Initialize SQLite database"""
        os.makedirs("data", exist_ok=True)
        self.db_path = "data/api_ecosystem.db"
        
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS apis (
                    api_id TEXT PRIMARY KEY,
                    name TEXT,
                    description TEXT,
                    version TEXT,
                    type TEXT,
                    status TEXT,
                    owner TEXT,
                    team TEXT,
                    specification TEXT,
                    endpoints TEXT,
                    dependencies TEXT,
                    consumers TEXT,
                    tags TEXT,
                    created_at TIMESTAMP,
                    updated_at TIMESTAMP,
                    published_at TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS api_contracts (
                    contract_id TEXT PRIMARY KEY,
                    api_id TEXT,
                    consumer_id TEXT,
                    sla_tier TEXT,
                    rate_limits TEXT,
                    quotas TEXT,
                    permissions TEXT,
                    created_at TIMESTAMP,
                    expires_at TIMESTAMP,
                    is_active BOOLEAN
                );
                
                CREATE TABLE IF NOT EXISTS portal_users (
                    user_id TEXT PRIMARY KEY,
                    email TEXT UNIQUE,
                    name TEXT,
                    organization TEXT,
                    tier TEXT,
                    api_keys TEXT,
                    subscriptions TEXT,
                    usage_stats TEXT,
                    created_at TIMESTAMP,
                    last_active TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS api_metrics (
                    api_id TEXT,
                    timestamp TIMESTAMP,
                    requests_per_minute INTEGER,
                    avg_response_time_ms REAL,
                    error_rate REAL,
                    success_rate REAL,
                    p95_latency_ms REAL,
                    active_consumers INTEGER,
                    data_transfer_mb REAL,
                    PRIMARY KEY (api_id, timestamp)
                );
            """)
    
    def create_api(self, name: str, description: str, version: str, 
                   api_type: str, specification: Dict[str, Any],
                   owner: str, team: str) -> str:
        """Create new API definition"""
        api_id = str(uuid.uuid4())
        
        try:
            type_enum = APIType(api_type)
        except ValueError:
            raise ValueError(f"Invalid API type: {api_type}")
        
        # Validate specification
        validation_result = self.validator.validate_specification(specification, type_enum)
        
        if not validation_result["valid"]:
            raise ValueError(f"Invalid specification: {validation_result['errors']}")
        
        # Extract endpoints from specification
        endpoints = self._extract_endpoints(specification, type_enum)
        
        api_def = APIDefinition(
            api_id=api_id,
            name=name,
            description=description,
            version=version,
            type=type_enum,
            status=APIStatus.DRAFT,
            owner=owner,
            team=team,
            specification=specification,
            endpoints=endpoints,
            dependencies=[],
            consumers=set(),
            tags=[],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            published_at=None
        )
        
        self.apis[api_id] = api_def
        
        # Save to database
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO apis VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                api_id, name, description, version, api_type, api_def.status.value,
                owner, team, json.dumps(specification), json.dumps(endpoints),
                json.dumps([]), json.dumps(list(api_def.consumers)),
                json.dumps([]), api_def.created_at.isoformat(),
                api_def.updated_at.isoformat(), None
            ))
        
        logger.info(f"Created API: {name} ({api_id})")
        return api_id
    
    def _extract_endpoints(self, spec: Dict[str, Any], api_type: APIType) -> List[Dict[str, Any]]:
        """Extract endpoints from API specification"""
        endpoints = []
        
        if api_type == APIType.REST and "paths" in spec:
            for path, methods in spec["paths"].items():
                for method, operation in methods.items():
                    if method.upper() in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                        endpoint = {
                            "path": path,
                            "method": method.upper(),
                            "description": operation.get("description", operation.get("summary", "")),
                            "parameters": operation.get("parameters", []),
                            "responses": operation.get("responses", {})
                        }
                        endpoints.append(endpoint)
        
        elif api_type == APIType.GRAPHQL and "schema" in spec:
            # Extract GraphQL queries and mutations
            if "queries" in spec:
                for query in spec["queries"]:
                    endpoints.append({
                        "path": "/graphql",
                        "method": "POST",
                        "type": "query",
                        "name": query.get("name", ""),
                        "description": query.get("description", "")
                    })
        
        return endpoints
    
    def publish_api(self, api_id: str) -> bool:
        """Publish API to production"""
        if api_id not in self.apis:
            return False
        
        api_def = self.apis[api_id]
        
        # Validate API is ready for production
        if api_def.status not in [APIStatus.TESTING, APIStatus.STAGING]:
            logger.error(f"API {api_id} not ready for publication (status: {api_def.status})")
            return False
        
        # Update status
        api_def.status = APIStatus.PRODUCTION
        api_def.published_at = datetime.now()
        
        # Register routes in gateway
        for endpoint in api_def.endpoints:
            upstream_url = f"http://localhost:8080/api/{api_def.name.lower()}"  # Default upstream
            self.gateway.register_api_route(
                api_id, endpoint["path"], upstream_url, [endpoint["method"]]
            )
        
        # Update database
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE apis SET status = ?, published_at = ?, updated_at = ?
                WHERE api_id = ?
            """, (
                api_def.status.value, api_def.published_at.isoformat(),
                datetime.now().isoformat(), api_id
            ))
        
        logger.info(f"Published API: {api_def.name} ({api_id})")
        return True
    
    def create_api_contract(self, api_id: str, consumer_id: str, 
                           sla_tier: str) -> str:
        """Create API contract for consumer"""
        if api_id not in self.apis:
            raise ValueError("API not found")
        
        contract_id = str(uuid.uuid4())
        
        try:
            tier_enum = DeveloperTier(sla_tier)
        except ValueError:
            raise ValueError(f"Invalid SLA tier: {sla_tier}")
        
        # Define rate limits based on tier
        rate_limits = {
            DeveloperTier.BRONZE: {"requests_per_minute": 100, "requests_per_day": 1000},
            DeveloperTier.SILVER: {"requests_per_minute": 500, "requests_per_day": 10000},
            DeveloperTier.GOLD: {"requests_per_minute": 2000, "requests_per_day": 100000},
            DeveloperTier.PLATINUM: {"requests_per_minute": 10000, "requests_per_day": 1000000}
        }
        
        contract = APIContract(
            contract_id=contract_id,
            api_id=api_id,
            consumer_id=consumer_id,
            sla_tier=tier_enum,
            rate_limits=rate_limits[tier_enum],
            quotas=rate_limits[tier_enum],
            permissions=["read"],
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(days=365),
            is_active=True
        )
        
        self.contracts[contract_id] = contract
        
        # Update API consumers
        self.apis[api_id].consumers.add(consumer_id)
        
        # Save to database
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO api_contracts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                contract_id, api_id, consumer_id, sla_tier,
                json.dumps(contract.rate_limits), json.dumps(contract.quotas),
                json.dumps(contract.permissions), contract.created_at.isoformat(),
                contract.expires_at.isoformat() if contract.expires_at else None,
                contract.is_active
            ))
        
        logger.info(f"Created API contract: {contract_id}")
        return contract_id
    
    def register_developer(self, email: str, name: str, organization: str) -> str:
        """Register developer in portal"""
        user_id = self.portal.register_developer(email, name, organization)
        
        # Save to database
        user = self.portal.users[user_id]
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO portal_users VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id, email, name, organization, user.tier.value,
                json.dumps(user.api_keys), json.dumps(user.subscriptions),
                json.dumps(user.usage_stats), user.created_at.isoformat(),
                user.last_active.isoformat()
            ))
        
        return user_id
    
    def generate_api_documentation(self, api_id: str) -> str:
        """Generate API documentation"""
        if api_id not in self.apis:
            raise ValueError("API not found")
        
        api_def = self.apis[api_id]
        return self.portal.generate_documentation(api_def)
    
    def _start_background_tasks(self):
        """Start background monitoring tasks"""
        def metrics_collector():
            while True:
                try:
                    self._collect_metrics()
                    time.sleep(60)  # Collect metrics every minute
                except Exception as e:
                    logger.error(f"Metrics collection error: {e}")
                    time.sleep(10)
        
        metrics_thread = threading.Thread(target=metrics_collector, daemon=True)
        metrics_thread.start()
    
    def _collect_metrics(self):
        """Collect API metrics"""
        for api_id, api_def in self.apis.items():
            # Collect from gateway metrics
            gateway_metrics = self.gateway.metrics_collector.get(api_id, [])
            
            if gateway_metrics:
                # Calculate aggregate metrics
                recent_metrics = [
                    m for m in gateway_metrics
                    if m["timestamp"] > datetime.now() - timedelta(minutes=1)
                ]
                
                if recent_metrics:
                    requests_per_minute = len(recent_metrics)
                    avg_response_time = sum(m["duration"] for m in recent_metrics) / len(recent_metrics) * 1000
                    error_count = len([m for m in recent_metrics if m["status_code"] >= 400])
                    error_rate = error_count / len(recent_metrics) if recent_metrics else 0
                    
                    # Calculate P95 latency
                    durations = sorted([m["duration"] * 1000 for m in recent_metrics])
                    p95_index = int(len(durations) * 0.95)
                    p95_latency = durations[p95_index] if durations else 0
                    
                    metrics = APIMetrics(
                        api_id=api_id,
                        timestamp=datetime.now(),
                        requests_per_minute=requests_per_minute,
                        avg_response_time_ms=avg_response_time,
                        error_rate=error_rate,
                        success_rate=1.0 - error_rate,
                        p95_latency_ms=p95_latency,
                        active_consumers=len(api_def.consumers),
                        data_transfer_mb=0.0  # Would calculate from actual data
                    )
                    
                    self.metrics[api_id].append(metrics)
                    
                    # Keep only recent metrics
                    cutoff = datetime.now() - timedelta(hours=24)
                    self.metrics[api_id] = [
                        m for m in self.metrics[api_id]
                        if m.timestamp > cutoff
                    ]
                    
                    # Save to database
                    with sqlite3.connect(self.db_path) as conn:
                        conn.execute("""
                            INSERT OR REPLACE INTO api_metrics VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            api_id, metrics.timestamp.isoformat(),
                            metrics.requests_per_minute, metrics.avg_response_time_ms,
                            metrics.error_rate, metrics.success_rate,
                            metrics.p95_latency_ms, metrics.active_consumers,
                            metrics.data_transfer_mb
                        ))
    
    def get_api_analytics(self, api_id: str, hours: int = 24) -> Dict[str, Any]:
        """Get API analytics"""
        if api_id not in self.apis:
            raise ValueError("API not found")
        
        cutoff = datetime.now() - timedelta(hours=hours)
        recent_metrics = [
            m for m in self.metrics.get(api_id, [])
            if m.timestamp > cutoff
        ]
        
        if not recent_metrics:
            return {
                "api_id": api_id,
                "period_hours": hours,
                "total_requests": 0,
                "avg_response_time_ms": 0,
                "error_rate": 0,
                "availability": 100.0
            }
        
        total_requests = sum(m.requests_per_minute for m in recent_metrics)
        avg_response_time = sum(m.avg_response_time_ms for m in recent_metrics) / len(recent_metrics)
        avg_error_rate = sum(m.error_rate for m in recent_metrics) / len(recent_metrics)
        
        return {
            "api_id": api_id,
            "period_hours": hours,
            "total_requests": total_requests,
            "avg_response_time_ms": avg_response_time,
            "error_rate": avg_error_rate,
            "availability": 100.0 - (avg_error_rate * 100),
            "peak_requests_per_minute": max(m.requests_per_minute for m in recent_metrics),
            "p95_latency_ms": max(m.p95_latency_ms for m in recent_metrics)
        }
    
    def get_ecosystem_overview(self) -> Dict[str, Any]:
        """Get ecosystem overview"""
        total_apis = len(self.apis)
        published_apis = len([a for a in self.apis.values() if a.status == APIStatus.PRODUCTION])
        total_developers = len(self.portal.users)
        total_contracts = len(self.contracts)
        
        # Calculate average API health score
        all_metrics = []
        for api_metrics in self.metrics.values():
            if api_metrics:
                latest = api_metrics[-1]
                health_score = (latest.success_rate * 100) - (latest.avg_response_time_ms / 10)
                all_metrics.append(max(0, min(100, health_score)))
        
        avg_health = sum(all_metrics) / len(all_metrics) if all_metrics else 100
        
        return {
            "total_apis": total_apis,
            "published_apis": published_apis,
            "draft_apis": len([a for a in self.apis.values() if a.status == APIStatus.DRAFT]),
            "deprecated_apis": len([a for a in self.apis.values() if a.status == APIStatus.DEPRECATED]),
            "total_developers": total_developers,
            "total_contracts": total_contracts,
            "active_contracts": len([c for c in self.contracts.values() if c.is_active]),
            "average_health_score": avg_health,
            "total_endpoints": sum(len(a.endpoints) for a in self.apis.values())
        }

# FastAPI application
app = FastAPI(title="API Ecosystem Management Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global ecosystem manager
ecosystem = APIEcosystemManager()
security = HTTPBearer()

import secrets

# Pydantic models
class APICreateRequest(BaseModel):
    name: str
    description: str
    version: str
    type: str
    specification: Dict[str, Any]
    owner: str
    team: str

class ContractRequest(BaseModel):
    consumer_id: str
    sla_tier: str

class DeveloperRequest(BaseModel):
    email: str
    name: str
    organization: str

class GatewayRequest(BaseModel):
    path: str
    method: str

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "API Ecosystem Management",
        "status": "operational",
        "version": "1.0.0",
        "ecosystem_ready": True
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    overview = ecosystem.get_ecosystem_overview()
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "ecosystem_overview": overview
    }

@app.post("/apis")
async def create_api(request: APICreateRequest):
    """Create new API"""
    try:
        api_id = ecosystem.create_api(
            request.name, request.description, request.version,
            request.type, request.specification, request.owner, request.team
        )
        
        return {
            "success": True,
            "api_id": api_id
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/apis")
async def list_apis(status: Optional[str] = None):
    """List APIs"""
    apis = []
    for api_def in ecosystem.apis.values():
        if status and api_def.status.value != status:
            continue
        
        apis.append({
            "api_id": api_def.api_id,
            "name": api_def.name,
            "description": api_def.description,
            "version": api_def.version,
            "type": api_def.type.value,
            "status": api_def.status.value,
            "owner": api_def.owner,
            "endpoints_count": len(api_def.endpoints),
            "consumers_count": len(api_def.consumers)
        })
    
    return {"apis": apis}

@app.get("/apis/{api_id}")
async def get_api(api_id: str):
    """Get API details"""
    if api_id not in ecosystem.apis:
        raise HTTPException(status_code=404, detail="API not found")
    
    api_def = ecosystem.apis[api_id]
    return {
        "api_id": api_def.api_id,
        "name": api_def.name,
        "description": api_def.description,
        "version": api_def.version,
        "type": api_def.type.value,
        "status": api_def.status.value,
        "owner": api_def.owner,
        "team": api_def.team,
        "endpoints": api_def.endpoints,
        "consumers": list(api_def.consumers),
        "created_at": api_def.created_at.isoformat(),
        "updated_at": api_def.updated_at.isoformat()
    }

@app.post("/apis/{api_id}/publish")
async def publish_api(api_id: str):
    """Publish API"""
    success = ecosystem.publish_api(api_id)
    
    if not success:
        raise HTTPException(status_code=400, detail="Failed to publish API")
    
    return {"success": True}

@app.post("/apis/{api_id}/contracts")
async def create_contract(api_id: str, request: ContractRequest):
    """Create API contract"""
    try:
        contract_id = ecosystem.create_api_contract(
            api_id, request.consumer_id, request.sla_tier
        )
        
        return {
            "success": True,
            "contract_id": contract_id
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/apis/{api_id}/documentation")
async def get_documentation(api_id: str):
    """Get API documentation"""
    try:
        html = ecosystem.generate_api_documentation(api_id)
        return {"html": html}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/apis/{api_id}/analytics")
async def get_analytics(api_id: str, hours: int = 24):
    """Get API analytics"""
    try:
        analytics = ecosystem.get_api_analytics(api_id, hours)
        return analytics
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/developers")
async def register_developer(request: DeveloperRequest):
    """Register developer"""
    try:
        user_id = ecosystem.register_developer(
            request.email, request.name, request.organization
        )
        
        return {
            "success": True,
            "user_id": user_id
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/developers/{user_id}/api-keys")
async def generate_api_key(user_id: str):
    """Generate API key for developer"""
    try:
        api_key = ecosystem.portal.generate_api_key(user_id)
        return {
            "success": True,
            "api_key": api_key
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/gateway/proxy")
async def gateway_proxy(request: GatewayRequest, http_request: Request, 
                       credentials: HTTPAuthorizationCredentials = Depends(security)):
    """API Gateway proxy endpoint"""
    api_key = credentials.credentials if credentials else ""
    
    # Create a mock request for gateway processing
    class MockRequest:
        def __init__(self, path: str, method: str):
            self.url = type('obj', (object,), {'path': path})()
            self.method = method
            self.query_params = {}
    
    mock_request = MockRequest(request.path, request.method)
    result = await ecosystem.gateway.handle_request(mock_request, api_key)
    
    if result.get("error"):
        raise HTTPException(
            status_code=result.get("status_code", 400),
            detail=result["error"]
        )
    
    return result

@app.get("/overview")
async def get_overview():
    """Get ecosystem overview"""
    return ecosystem.get_ecosystem_overview()

@app.websocket("/ws/ecosystem")
async def ecosystem_websocket(websocket: WebSocket):
    """WebSocket endpoint for real-time ecosystem updates"""
    await websocket.accept()
    
    try:
        while True:
            # Send ecosystem status
            overview = ecosystem.get_ecosystem_overview()
            
            # Get recent API metrics
            recent_metrics = {}
            for api_id, metrics_list in ecosystem.metrics.items():
                if metrics_list:
                    latest = metrics_list[-1]
                    recent_metrics[api_id] = {
                        "requests_per_minute": latest.requests_per_minute,
                        "avg_response_time_ms": latest.avg_response_time_ms,
                        "error_rate": latest.error_rate,
                        "success_rate": latest.success_rate
                    }
            
            status = {
                "type": "ecosystem_status",
                "timestamp": datetime.now().isoformat(),
                "overview": overview,
                "recent_metrics": recent_metrics
            }
            
            await websocket.send_text(json.dumps(status))
            await asyncio.sleep(5)
            
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket error: {e}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8859))
    uvicorn.run(app, host="0.0.0.0", port=port)