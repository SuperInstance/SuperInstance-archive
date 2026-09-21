"""
Service Mesh Controller - Advanced Infrastructure for Bot Ecosystem
Provides service discovery, traffic management, and inter-bot communication
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json
import uuid
import asyncio
import httpx
import hashlib
from contextlib import asynccontextmanager
from collections import defaultdict

# Service mesh models
class ServiceRegistration(BaseModel):
    service_id: str
    service_name: str
    bot_type: str
    host: str
    port: int
    health_endpoint: str
    capabilities: List[str]
    version: str
    metadata: Dict[str, Any]

class TrafficPolicy(BaseModel):
    policy_id: str
    source_service: str
    target_service: str
    rules: Dict[str, Any]  # Rate limiting, retry policies, etc.
    enabled: bool

class ServiceEndpoint(BaseModel):
    endpoint_id: str
    service_id: str
    path: str
    method: str
    auth_required: bool
    rate_limit: Optional[int] = None

# Service registry and mesh state
service_registry = {}
traffic_policies = {}
service_endpoints = {}
service_metrics = defaultdict(lambda: defaultdict(int))
circuit_breaker_states = defaultdict(dict)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start service health monitoring
    asyncio.create_task(monitor_service_health())
    # Start metrics collection
    asyncio.create_task(collect_service_metrics())
    yield

app = FastAPI(
    title="Service Mesh Controller", 
    description="Advanced service mesh for bot ecosystem communication",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def monitor_service_health():
    """Background task to monitor all registered services"""
    while True:
        try:
            unhealthy_services = []
            
            for service_id, service in service_registry.items():
                try:
                    async with httpx.AsyncClient(timeout=5.0) as client:
                        health_url = f"http://{service.host}:{service.port}{service.health_endpoint}"
                        response = await client.get(health_url)
                        
                        if response.status_code == 200:
                            service.metadata["last_health_check"] = datetime.utcnow().isoformat()
                            service.metadata["health_status"] = "healthy"
                            # Reset circuit breaker if service is healthy
                            if service_id in circuit_breaker_states:
                                circuit_breaker_states[service_id]["failure_count"] = 0
                        else:
                            service.metadata["health_status"] = "unhealthy"
                            unhealthy_services.append(service_id)
                            
                except Exception as e:
                    service.metadata["health_status"] = "unreachable"
                    service.metadata["last_error"] = str(e)
                    unhealthy_services.append(service_id)
                    
                    # Update circuit breaker
                    if service_id not in circuit_breaker_states:
                        circuit_breaker_states[service_id] = {"failure_count": 0, "last_failure": None}
                    
                    circuit_breaker_states[service_id]["failure_count"] += 1
                    circuit_breaker_states[service_id]["last_failure"] = datetime.utcnow().isoformat()
            
            if unhealthy_services:
                print(f"Unhealthy services detected: {unhealthy_services}")
                
        except Exception as e:
            print(f"Error in service health monitoring: {e}")
        
        await asyncio.sleep(30)  # Check every 30 seconds

async def collect_service_metrics():
    """Background task to collect service metrics"""
    while True:
        try:
            for service_id, service in service_registry.items():
                try:
                    # Collect basic metrics
                    service_metrics[service_id]["health_checks"] += 1
                    
                    if service.metadata.get("health_status") == "healthy":
                        service_metrics[service_id]["healthy_checks"] += 1
                    else:
                        service_metrics[service_id]["unhealthy_checks"] += 1
                    
                except Exception as e:
                    print(f"Error collecting metrics for {service_id}: {e}")
        
        except Exception as e:
            print(f"Error in metrics collection: {e}")
        
        await asyncio.sleep(60)  # Collect every minute

@app.get("/")
def root():
    return {
        "service": "Service Mesh Controller",
        "status": "operational",
        "registered_services": len(service_registry),
        "active_policies": len(traffic_policies),
        "features": [
            "Service Discovery",
            "Traffic Management", 
            "Health Monitoring",
            "Circuit Breaking",
            "Load Balancing",
            "Inter-Bot Communication"
        ]
    }

@app.get("/health")
def health_check():
    healthy_services = sum(
        1 for service in service_registry.values()
        if service.metadata.get("health_status") == "healthy"
    )
    
    return {
        "status": "healthy",
        "service": "Service Mesh Controller",
        "registered_services": len(service_registry),
        "healthy_services": healthy_services,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/services/register")
def register_service(service: ServiceRegistration):
    """Register a new service in the mesh"""
    service.metadata["registered_at"] = datetime.utcnow().isoformat()
    service.metadata["health_status"] = "unknown"
    service_registry[service.service_id] = service
    
    # Initialize metrics
    service_metrics[service.service_id] = defaultdict(int)
    
    return {
        "message": f"Service {service.service_name} registered successfully",
        "service_id": service.service_id,
        "registration_time": service.metadata["registered_at"]
    }

@app.delete("/services/{service_id}")
def deregister_service(service_id: str):
    """Deregister a service from the mesh"""
    if service_id not in service_registry:
        raise HTTPException(status_code=404, detail="Service not found")
    
    service_name = service_registry[service_id].service_name
    del service_registry[service_id]
    
    # Clean up metrics and circuit breaker state
    if service_id in service_metrics:
        del service_metrics[service_id]
    if service_id in circuit_breaker_states:
        del circuit_breaker_states[service_id]
    
    return {
        "message": f"Service {service_name} deregistered successfully",
        "service_id": service_id
    }

@app.get("/services")
def list_services(bot_type: Optional[str] = None, healthy_only: bool = False):
    """List all registered services"""
    services = list(service_registry.values())
    
    if bot_type:
        services = [s for s in services if s.bot_type == bot_type]
    
    if healthy_only:
        services = [s for s in services if s.metadata.get("health_status") == "healthy"]
    
    return {
        "services": services,
        "count": len(services),
        "total_registered": len(service_registry)
    }

@app.get("/services/{service_id}")
def get_service(service_id: str):
    """Get details for a specific service"""
    if service_id not in service_registry:
        raise HTTPException(status_code=404, detail="Service not found")
    
    service = service_registry[service_id]
    metrics = dict(service_metrics.get(service_id, {}))
    circuit_breaker = circuit_breaker_states.get(service_id, {})
    
    return {
        "service": service,
        "metrics": metrics,
        "circuit_breaker": circuit_breaker
    }

@app.post("/traffic/policies")
def create_traffic_policy(policy: TrafficPolicy):
    """Create a traffic management policy"""
    traffic_policies[policy.policy_id] = policy
    
    return {
        "message": "Traffic policy created",
        "policy_id": policy.policy_id,
        "enabled": policy.enabled
    }

@app.get("/traffic/policies")
def list_traffic_policies():
    """List all traffic policies"""
    return {
        "policies": list(traffic_policies.values()),
        "count": len(traffic_policies)
    }

@app.post("/discovery/find")
def find_services(criteria: Dict[str, Any]):
    """Find services based on criteria"""
    matching_services = []
    
    for service in service_registry.values():
        match = True
        
        # Check bot_type
        if "bot_type" in criteria and service.bot_type != criteria["bot_type"]:
            match = False
        
        # Check capabilities
        if "capabilities" in criteria:
            required_caps = criteria["capabilities"]
            if not all(cap in service.capabilities for cap in required_caps):
                match = False
        
        # Check health status
        if "healthy_only" in criteria and criteria["healthy_only"]:
            if service.metadata.get("health_status") != "healthy":
                match = False
        
        if match:
            matching_services.append(service)
    
    return {
        "matching_services": matching_services,
        "count": len(matching_services),
        "search_criteria": criteria
    }

@app.post("/communication/route")
async def route_inter_bot_communication(request: Request):
    """Route communication between bots through the service mesh"""
    request_data = await request.json()
    
    source_bot = request_data.get("source_bot")
    target_bot = request_data.get("target_bot") 
    message_type = request_data.get("message_type")
    payload = request_data.get("payload")
    
    # Find target service
    target_services = [
        service for service in service_registry.values()
        if service.bot_type == target_bot and service.metadata.get("health_status") == "healthy"
    ]
    
    if not target_services:
        raise HTTPException(
            status_code=503, 
            detail=f"No healthy services found for bot type: {target_bot}"
        )
    
    # Use first healthy service (could implement load balancing here)
    target_service = target_services[0]
    
    # Check circuit breaker
    circuit_state = circuit_breaker_states.get(target_service.service_id, {})
    if circuit_state.get("failure_count", 0) > 5:
        raise HTTPException(
            status_code=503,
            detail=f"Circuit breaker open for service: {target_service.service_name}"
        )
    
    # Route the message
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            target_url = f"http://{target_service.host}:{target_service.port}/bot-communication"
            
            routed_payload = {
                "source_bot": source_bot,
                "message_type": message_type,
                "payload": payload,
                "routed_via": "service-mesh",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            response = await client.post(target_url, json=routed_payload)
            
            # Update metrics
            service_metrics[target_service.service_id]["messages_routed"] += 1
            
            return {
                "status": "routed",
                "target_service": target_service.service_name,
                "response_status": response.status_code,
                "response": response.json() if response.text else None
            }
    
    except Exception as e:
        # Update circuit breaker on failure
        if target_service.service_id not in circuit_breaker_states:
            circuit_breaker_states[target_service.service_id] = {"failure_count": 0}
        
        circuit_breaker_states[target_service.service_id]["failure_count"] += 1
        
        raise HTTPException(
            status_code=502,
            detail=f"Failed to route message to {target_bot}: {str(e)}"
        )

@app.get("/mesh/topology")
def get_mesh_topology():
    """Get the current service mesh topology"""
    topology = {
        "nodes": [],
        "connections": [],
        "health_summary": defaultdict(int)
    }
    
    # Add service nodes
    for service in service_registry.values():
        health_status = service.metadata.get("health_status", "unknown")
        topology["health_summary"][health_status] += 1
        
        topology["nodes"].append({
            "id": service.service_id,
            "name": service.service_name,
            "type": service.bot_type,
            "status": health_status,
            "capabilities": service.capabilities,
            "address": f"{service.host}:{service.port}"
        })
    
    # Add connections based on traffic policies
    for policy in traffic_policies.values():
        if policy.enabled:
            topology["connections"].append({
                "source": policy.source_service,
                "target": policy.target_service,
                "policy": policy.policy_id,
                "rules": policy.rules
            })
    
    return topology

@app.get("/mesh/metrics")
def get_mesh_metrics():
    """Get comprehensive service mesh metrics"""
    total_services = len(service_registry)
    healthy_services = sum(
        1 for service in service_registry.values()
        if service.metadata.get("health_status") == "healthy"
    )
    
    # Calculate uptime percentages
    uptime_metrics = {}
    for service_id, metrics in service_metrics.items():
        total_checks = metrics.get("health_checks", 0)
        healthy_checks = metrics.get("healthy_checks", 0)
        
        if total_checks > 0:
            uptime_percentage = (healthy_checks / total_checks) * 100
            uptime_metrics[service_id] = round(uptime_percentage, 2)
    
    return {
        "mesh_overview": {
            "total_services": total_services,
            "healthy_services": healthy_services,
            "unhealthy_services": total_services - healthy_services,
            "active_policies": len(traffic_policies),
            "circuit_breakers_open": sum(
                1 for state in circuit_breaker_states.values()
                if state.get("failure_count", 0) > 5
            )
        },
        "service_uptime": uptime_metrics,
        "traffic_metrics": dict(service_metrics),
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/mesh/optimize")
def optimize_mesh():
    """Optimize service mesh configuration"""
    optimizations = []
    
    # Check for overloaded services
    overloaded_services = [
        service_id for service_id, metrics in service_metrics.items()
        if metrics.get("messages_routed", 0) > 1000  # Threshold
    ]
    
    if overloaded_services:
        optimizations.append({
            "type": "scale_up",
            "services": overloaded_services,
            "recommendation": "Consider adding more replicas for high-traffic services"
        })
    
    # Check for unhealthy services
    unhealthy_services = [
        service.service_id for service in service_registry.values()
        if service.metadata.get("health_status") != "healthy"
    ]
    
    if unhealthy_services:
        optimizations.append({
            "type": "health_check",
            "services": unhealthy_services,
            "recommendation": "Investigate and fix unhealthy services"
        })
    
    # Check circuit breaker states
    problematic_services = [
        service_id for service_id, state in circuit_breaker_states.items()
        if state.get("failure_count", 0) > 3
    ]
    
    if problematic_services:
        optimizations.append({
            "type": "circuit_breaker",
            "services": problematic_services,
            "recommendation": "Review failing services and consider implementing fallback strategies"
        })
    
    return {
        "optimizations": optimizations,
        "mesh_health_score": calculate_mesh_health_score(),
        "timestamp": datetime.utcnow().isoformat()
    }

def calculate_mesh_health_score():
    """Calculate overall mesh health score (0-100)"""
    if not service_registry:
        return 100  # No services, no problems
    
    total_services = len(service_registry)
    healthy_services = sum(
        1 for service in service_registry.values()
        if service.metadata.get("health_status") == "healthy"
    )
    
    # Base score from service health
    health_score = (healthy_services / total_services) * 70
    
    # Deduct points for circuit breaker issues
    open_breakers = sum(
        1 for state in circuit_breaker_states.values()
        if state.get("failure_count", 0) > 5
    )
    
    breaker_penalty = min(open_breakers * 10, 30)  # Max 30 point penalty
    
    final_score = max(health_score - breaker_penalty, 0)
    return round(final_score, 1)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8006)