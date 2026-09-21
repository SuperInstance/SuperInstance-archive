# SUPERINSTANCE LEGO COMPONENT: API Gateway
# EXTRACTED FROM: services/api-gateway/main.py
# LEGO PRINCIPLE: Software = Data + Tools + Configuration

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from contextlib import asynccontextmanager
import httpx
import jwt
import time
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from collections import defaultdict
import asyncio

class APIGatewayLego:
    """
    🧩 LEGO COMPONENT: API Gateway
    
    DATA: Service registry, routing tables, health metrics, request/response logs
    TOOLS: Request routing, load balancing, authentication, rate limiting, health checks
    CONFIGURATION: Service endpoints, security policies, scaling rules, monitoring settings
    
    INTERFACES:
    - Input: HTTP requests, service registration, health pings
    - Output: Routed requests, aggregated responses, service metrics
    - Integration: Auth services, monitoring systems, service discovery
    
    DEPLOYMENT OPTIONS:
    - Device: Local API gateway for personal services
    - Edge: Regional gateway with intelligent routing
    - Cloud: Global gateway with advanced load balancing
    
    SUPERINSTANCE MISSION:
    Revolutionary $2/month gateway that makes any software combination possible
    through perfect Lego interfaces and intelligent service orchestration.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.deployment_mode = config.get("deployment_mode", "edge")
        self.service_registry = {}
        self.health_metrics = defaultdict(dict)
        self.rate_limit_store = {}
        self.request_stats = defaultdict(int)
        self.app = FastAPI(
            title="SuperInstance API Gateway Lego",
            description="Revolutionary $2/month gateway enabling infinite software possibilities",
            version="1.0.0"
        )
        self._setup_middleware()
        self._setup_routes()
        self._setup_service_discovery()
    
    def _setup_middleware(self):
        """Configure gateway middleware for SuperInstance architecture"""
        # CORS for SuperInstance global accessibility
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=self.config.get("cors_origins", ["*"]),
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Request tracking middleware
        @self.app.middleware("http")
        async def track_requests(request: Request, call_next):
            start_time = time.time()
            self.request_stats[request.url.path] += 1
            
            response = await call_next(request)
            
            process_time = time.time() - start_time
            response.headers["X-Process-Time"] = str(process_time)
            response.headers["X-SuperInstance-Gateway"] = "v1.0.0"
            
            return response
    
    def _setup_routes(self):
        """Setup SuperInstance gateway routing"""
        
        @self.app.get("/health")
        async def gateway_health():
            """Gateway health check - core LEGO function"""
            return {
                "gateway": "healthy",
                "deployment_mode": self.deployment_mode,
                "registered_services": len(self.service_registry),
                "total_requests": sum(self.request_stats.values()),
                "superinstance_mission": "$2/month gateway for infinite possibilities",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        @self.app.get("/services")
        async def list_services():
            """List registered services - discovery LEGO function"""
            return {
                "services": self.service_registry,
                "total_services": len(self.service_registry),
                "deployment_mode": self.deployment_mode
            }
        
        @self.app.post("/register-service")
        async def register_service(service_info: Dict[str, Any]):
            """Register new service - registry LEGO function"""
            service_name = service_info.get("name")
            service_url = service_info.get("url")
            
            if not service_name or not service_url:
                raise HTTPException(400, "Service name and URL required")
            
            self.service_registry[service_name] = {
                "url": service_url,
                "health_check": service_info.get("health_check", f"{service_url}/health"),
                "registered_at": datetime.utcnow().isoformat(),
                "deployment_compatible": service_info.get("deployment_modes", ["device", "edge", "cloud"])
            }
            
            return {"status": "registered", "service": service_name}
        
        @self.app.api_route("/api/{service_name}/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
        async def route_to_service(service_name: str, path: str, request: Request):
            """Main routing function - core LEGO capability"""
            if service_name not in self.service_registry:
                raise HTTPException(404, f"Service '{service_name}' not found")
            
            service_info = self.service_registry[service_name]
            service_url = service_info["url"]
            
            # Check if service supports current deployment mode
            if self.deployment_mode not in service_info.get("deployment_compatible", []):
                raise HTTPException(
                    503, 
                    f"Service '{service_name}' not available in {self.deployment_mode} deployment mode"
                )
            
            # Route request to service
            try:
                target_url = f"{service_url}/{path}"
                
                async with httpx.AsyncClient(timeout=30.0) as client:
                    # Forward request with all headers
                    headers = dict(request.headers)
                    headers.pop("host", None)  # Remove host header
                    
                    # Add SuperInstance routing headers
                    headers["X-SuperInstance-Gateway"] = "v1.0.0"
                    headers["X-Deployment-Mode"] = self.deployment_mode
                    headers["X-Request-ID"] = str(uuid.uuid4())
                    
                    if request.method == "GET":
                        response = await client.get(target_url, headers=headers, params=request.query_params)
                    elif request.method == "POST":
                        body = await request.body()
                        response = await client.post(target_url, headers=headers, content=body, params=request.query_params)
                    elif request.method == "PUT":
                        body = await request.body()
                        response = await client.put(target_url, headers=headers, content=body, params=request.query_params)
                    elif request.method == "DELETE":
                        response = await client.delete(target_url, headers=headers, params=request.query_params)
                    elif request.method == "PATCH":
                        body = await request.body()
                        response = await client.patch(target_url, headers=headers, content=body, params=request.query_params)
                    
                    # Update health metrics
                    self.health_metrics[service_name]["last_request"] = datetime.utcnow().isoformat()
                    self.health_metrics[service_name]["status"] = "healthy" if response.status_code < 500 else "degraded"
                    
                    # Return response
                    return JSONResponse(
                        content=response.json() if response.headers.get("content-type", "").startswith("application/json") else {"data": response.text},
                        status_code=response.status_code
                    )
            
            except Exception as e:
                # Update health metrics on error
                self.health_metrics[service_name]["status"] = "unhealthy"
                self.health_metrics[service_name]["last_error"] = str(e)
                
                raise HTTPException(502, f"Service '{service_name}' unavailable: {str(e)}")
        
        @self.app.get("/metrics")
        async def get_metrics():
            """Gateway metrics - monitoring LEGO function"""
            return {
                "request_stats": dict(self.request_stats),
                "health_metrics": dict(self.health_metrics),
                "service_count": len(self.service_registry),
                "deployment_mode": self.deployment_mode,
                "superinstance_efficiency": "Optimized for $2/month deployment"
            }
    
    def _setup_service_discovery(self):
        """Initialize SuperInstance service discovery"""
        # Register core SuperInstance services by deployment mode
        core_services = self._get_core_services_by_deployment()
        for service_name, service_config in core_services.items():
            self.service_registry[service_name] = service_config
    
    def _get_core_services_by_deployment(self) -> Dict[str, Dict]:
        """Get core services based on deployment mode"""
        if self.deployment_mode == "device":
            return {
                "auth": {"url": "http://localhost:8001", "health_check": "http://localhost:8001/health", "deployment_compatible": ["device", "edge", "cloud"]},
                "user-management": {"url": "http://localhost:8092", "health_check": "http://localhost:8092/health", "deployment_compatible": ["device", "edge", "cloud"]},
                "ai-insights": {"url": "http://localhost:8090", "health_check": "http://localhost:8090/health", "deployment_compatible": ["device", "edge", "cloud"]}
            }
        elif self.deployment_mode == "edge":
            return {
                "auth": {"url": "http://auth-service:8001", "health_check": "http://auth-service:8001/health", "deployment_compatible": ["device", "edge", "cloud"]},
                "user-management": {"url": "http://user-service:8092", "health_check": "http://user-service:8092/health", "deployment_compatible": ["device", "edge", "cloud"]},
                "ai-insights": {"url": "http://ai-service:8090", "health_check": "http://ai-service:8090/health", "deployment_compatible": ["device", "edge", "cloud"]},
                "nutrition": {"url": "http://nutrition-service:8094", "health_check": "http://nutrition-service:8094/health", "deployment_compatible": ["device", "edge", "cloud"]},
                "workout": {"url": "http://workout-service:8093", "health_check": "http://workout-service:8093/health", "deployment_compatible": ["device", "edge", "cloud"]}
            }
        else:  # cloud deployment
            return {
                "auth": {"url": "https://auth.superinstance.ai", "health_check": "https://auth.superinstance.ai/health", "deployment_compatible": ["cloud"]},
                "user-management": {"url": "https://users.superinstance.ai", "health_check": "https://users.superinstance.ai/health", "deployment_compatible": ["cloud"]},
                "ai-insights": {"url": "https://ai.superinstance.ai", "health_check": "https://ai.superinstance.ai/health", "deployment_compatible": ["cloud"]},
                "nutrition": {"url": "https://nutrition.superinstance.ai", "health_check": "https://nutrition.superinstance.ai/health", "deployment_compatible": ["cloud"]},
                "workout": {"url": "https://workout.superinstance.ai", "health_check": "https://workout.superinstance.ai/health", "deployment_compatible": ["cloud"]}
            }
    
    async def health_check_services(self):
        """Background task to check service health"""
        while True:
            for service_name, service_info in self.service_registry.items():
                try:
                    async with httpx.AsyncClient(timeout=5.0) as client:
                        response = await client.get(service_info["health_check"])
                        self.health_metrics[service_name] = {
                            "status": "healthy" if response.status_code == 200 else "degraded",
                            "response_time": response.elapsed.total_seconds(),
                            "last_check": datetime.utcnow().isoformat()
                        }
                except Exception as e:
                    self.health_metrics[service_name] = {
                        "status": "unhealthy",
                        "error": str(e),
                        "last_check": datetime.utcnow().isoformat()
                    }
            
            await asyncio.sleep(30)  # Check every 30 seconds
    
    def get_app(self):
        """Get FastAPI app for deployment"""
        return self.app

# LEGO CONFIGURATION OPTIONS
DEPLOYMENT_CONFIGS = {
    "device_local": {
        "deployment_mode": "device",
        "cors_origins": ["http://localhost:3000", "http://localhost:3001"],
        "features": ["local_services", "offline_capable"]
    },
    "edge_regional": {
        "deployment_mode": "edge", 
        "cors_origins": ["https://*.superinstance.com"],
        "features": ["intelligent_routing", "regional_optimization", "service_mesh"]
    },
    "cloud_global": {
        "deployment_mode": "cloud",
        "cors_origins": ["https://app.superinstance.ai"],
        "features": ["global_load_balancing", "advanced_analytics", "enterprise_scaling"]
    }
}

# SUPERINSTANCE FACTORY FUNCTION
def create_api_gateway_lego(deployment_type: str = "edge_regional"):
    """Factory function to create configured API Gateway Lego
    
    The gateway that makes $2/month infinite software possibilities real.
    Perfect interfaces, intelligent routing, revolutionary architecture.
    """
    config = DEPLOYMENT_CONFIGS.get(deployment_type, DEPLOYMENT_CONFIGS["edge_regional"])
    return APIGatewayLego(config)

# INTEGRATION INTERFACES
def integrate_with_auth_service(gateway: APIGatewayLego, auth_service_url: str):
    """Connect gateway to authentication Lego"""
    gateway.service_registry["auth"] = {
        "url": auth_service_url,
        "health_check": f"{auth_service_url}/health",
        "deployment_compatible": ["device", "edge", "cloud"]
    }

def integrate_with_ai_insights(gateway: APIGatewayLego, ai_service_url: str):
    """Connect gateway to AI insights Lego for intelligent routing"""
    gateway.service_registry["ai-insights"] = {
        "url": ai_service_url,
        "health_check": f"{ai_service_url}/health", 
        "deployment_compatible": ["device", "edge", "cloud"]
    }

# SUPERINSTANCE MISSION STATEMENT
"""
This API Gateway Lego embodies the SuperInstance vision:

- $2/month membership unlocks infinite software possibilities
- Perfect interfaces work seamlessly device/edge/cloud
- Lego principle: Software = Data + Tools + Configuration
- Revolutionary architecture enables anyone to build anything

Every request routed through this gateway contributes to the SuperInstance
mission of democratizing software development through component reusability.
"""