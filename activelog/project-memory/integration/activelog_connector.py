"""
ActiveLog Project Memory - Service Integration Connector
Integration with existing ActiveLog services and monitoring
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import aiohttp
import websockets
import json
import logging
from datetime import datetime, timezone
import os
from pathlib import Path

class ServiceStatus(Enum):
    """Service health status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"

@dataclass
class ServiceInfo:
    """Information about an ActiveLog service"""
    name: str
    port: int
    phase: str
    status: ServiceStatus
    url: str
    health_endpoint: str = "/health"
    websocket_endpoint: Optional[str] = None
    last_check: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    response_time: float = 0.0
    features: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)

class ActiveLogConnector:
    """
    Connector for integrating with existing ActiveLog services
    Monitors service health and provides unified access
    """
    
    def __init__(self, project_root: str = "/home/activeloguser/activelog"):
        self.project_root = Path(project_root)
        self.services = self._initialize_services()
        self.session: Optional[aiohttp.ClientSession] = None
        self.websocket_connections = {}
        self.monitoring_tasks = []
        self.logger = logging.getLogger(__name__)
        
    def _initialize_services(self) -> Dict[str, ServiceInfo]:
        """Initialize known ActiveLog services"""
        return {
            # Phase 1: Bot Orchestration
            "bot-orchestrator": ServiceInfo(
                name="bot-orchestrator",
                port=8450,
                phase="Phase 1",
                status=ServiceStatus.UNKNOWN,
                url="http://localhost:8450",
                features=["Claude API integration", "Task decomposition", "Bot allocation"],
                dependencies=["redis", "postgresql"]
            ),
            "bot-ecosystem": ServiceInfo(
                name="bot-ecosystem",
                port=8451,
                phase="Phase 1",
                status=ServiceStatus.UNKNOWN,
                url="http://localhost:8451",
                features=["Multi-LLM support", "Intelligent routing"],
                dependencies=["ollama", "redis"]
            ),
            "auto-scheduler": ServiceInfo(
                name="auto-scheduler",
                port=8452,
                phase="Phase 1",
                status=ServiceStatus.UNKNOWN,
                url="http://localhost:8452",
                features=["Session management", "Backup automation"],
                dependencies=["redis"]
            ),
            
            # Phase 2: LucidDreamer System
            "luciddreamer-core": ServiceInfo(
                name="luciddreamer-core",
                port=8430,
                phase="Phase 2",
                status=ServiceStatus.UNKNOWN,
                url="http://localhost:8430",
                websocket_endpoint="/ws",
                features=["Quantum dream engine", "Reality simulation"],
                dependencies=["redis", "postgresql"]
            ),
            "dream-simulator": ServiceInfo(
                name="dream-simulator",
                port=8431,
                phase="Phase 2",
                status=ServiceStatus.UNKNOWN,
                url="http://localhost:8431",
                features=["Variable-speed simulation", "Business modeling"],
                dependencies=["luciddreamer-core", "redis"]
            ),
            
            # Phase 3: Business Platforms
            "compute-sharing": ServiceInfo(
                name="compute-sharing",
                port=8440,
                phase="Phase 3",
                status=ServiceStatus.UNKNOWN,
                url="http://localhost:8440",
                features=["Device power sharing", "Task allocation"],
                dependencies=["redis"]
            ),
            "hatchery-manager": ServiceInfo(
                name="hatchery-manager",
                port=8441,
                phase="Phase 3",
                status=ServiceStatus.UNKNOWN,
                url="http://localhost:8441",
                features=["NSRAA compliance", "Aquaculture management"],
                dependencies=["postgresql", "redis"]
            ),
            "business-platform": ServiceInfo(
                name="business-platform",
                port=8442,
                phase="Phase 3",
                status=ServiceStatus.UNKNOWN,
                url="http://localhost:8442",
                features=["Portfolio analytics", "Financial intelligence"],
                dependencies=["postgresql"]
            ),
            "municipal-platform": ServiceInfo(
                name="municipal-platform",
                port=8443,
                phase="Phase 3",
                status=ServiceStatus.UNKNOWN,
                url="http://localhost:8443",
                features=["Government services", "Public safety"],
                dependencies=["postgresql"]
            ),
            
            # Phase 4: Market Infrastructure
            "dividend-shares": ServiceInfo(
                name="dividend-shares",
                port=8444,
                phase="Phase 4",
                status=ServiceStatus.UNKNOWN,
                url="http://localhost:8444",
                features=["Dividend management", "Equity calculations"],
                dependencies=["postgresql"]
            ),
            "paper-trading": ServiceInfo(
                name="paper-trading",
                port=8445,
                phase="Phase 4",
                status=ServiceStatus.UNKNOWN,
                url="http://localhost:8445",
                features=["Market simulation", "Portfolio management"],
                dependencies=["postgresql", "market-data"]
            ),
            
            # Phase 5: Developer Tools
            "code-director": ServiceInfo(
                name="code-director",
                port=8446,
                phase="Phase 5",
                status=ServiceStatus.UNKNOWN,
                url="http://localhost:8446",
                features=["AI code generation", "Architecture analysis"],
                dependencies=["bot-orchestrator"]
            ),
            
            # Project Memory (Current Service)
            "project-memory": ServiceInfo(
                name="project-memory",
                port=8460,
                phase="Memory System",
                status=ServiceStatus.HEALTHY,  # Self-reported as healthy
                url="http://localhost:8460",
                features=["Knowledge graph", "Context optimization", "Bot views"],
                dependencies=["redis"]
            )
        }
    
    async def start_monitoring(self):
        """Start service monitoring and health checks"""
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10))
        
        # Start monitoring tasks for each service
        for service_name, service in self.services.items():
            if service_name != "project-memory":  # Don't monitor self
                task = asyncio.create_task(self._monitor_service(service))
                self.monitoring_tasks.append(task)
        
        self.logger.info("Started monitoring for all ActiveLog services")
    
    async def stop_monitoring(self):
        """Stop service monitoring"""
        # Cancel monitoring tasks
        for task in self.monitoring_tasks:
            task.cancel()
        
        # Close websocket connections
        for ws in self.websocket_connections.values():
            if ws and not ws.closed:
                await ws.close()
        
        # Close HTTP session
        if self.session:
            await self.session.close()
        
        self.logger.info("Stopped service monitoring")
    
    async def _monitor_service(self, service: ServiceInfo):
        """Monitor individual service health"""
        while True:
            try:
                await self._check_service_health(service)
                await asyncio.sleep(30)  # Check every 30 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error monitoring {service.name}: {e}")
                service.status = ServiceStatus.UNKNOWN
                await asyncio.sleep(60)  # Wait longer on error
    
    async def _check_service_health(self, service: ServiceInfo):
        """Check health of a specific service"""
        start_time = datetime.now()
        
        try:
            health_url = f"{service.url}{service.health_endpoint}"
            
            async with self.session.get(health_url) as response:
                service.response_time = (datetime.now() - start_time).total_seconds()
                service.last_check = datetime.now(timezone.utc)
                
                if response.status == 200:
                    data = await response.json()
                    
                    # Update service info from health response
                    if isinstance(data, dict):
                        if data.get("status") == "healthy":
                            service.status = ServiceStatus.HEALTHY
                        elif data.get("status") == "degraded":
                            service.status = ServiceStatus.DEGRADED
                        else:
                            service.status = ServiceStatus.UNHEALTHY
                        
                        # Update features if provided
                        if "features" in data:
                            service.features = data["features"]
                        
                        # Update dependencies if provided
                        if "dependencies" in data:
                            service.dependencies = data["dependencies"]
                    else:
                        service.status = ServiceStatus.HEALTHY
                
                else:
                    service.status = ServiceStatus.UNHEALTHY
        
        except asyncio.TimeoutError:
            service.status = ServiceStatus.UNHEALTHY
            service.response_time = 10.0  # Timeout value
        except aiohttp.ClientConnectorError:
            service.status = ServiceStatus.UNHEALTHY
            service.response_time = 0.0
        except Exception as e:
            self.logger.error(f"Health check failed for {service.name}: {e}")
            service.status = ServiceStatus.UNKNOWN
    
    async def get_service_info(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific service"""
        if service_name not in self.services:
            return None
        
        service = self.services[service_name]
        
        # Try to get additional info from service
        try:
            info_url = f"{service.url}/info"
            async with self.session.get(info_url) as response:
                if response.status == 200:
                    additional_info = await response.json()
                else:
                    additional_info = {}
        except:
            additional_info = {}
        
        return {
            "name": service.name,
            "port": service.port,
            "phase": service.phase,
            "status": service.status.value,
            "url": service.url,
            "response_time": service.response_time,
            "last_check": service.last_check.isoformat(),
            "features": service.features,
            "dependencies": service.dependencies,
            **additional_info
        }
    
    async def get_all_services_status(self) -> Dict[str, Any]:
        """Get status of all ActiveLog services"""
        services_status = {}
        
        for name, service in self.services.items():
            services_status[name] = {
                "status": service.status.value,
                "response_time": service.response_time,
                "last_check": service.last_check.isoformat(),
                "port": service.port,
                "phase": service.phase
            }
        
        # Calculate overall system health
        healthy_services = sum(1 for s in self.services.values() 
                              if s.status == ServiceStatus.HEALTHY)
        total_services = len(self.services)
        
        overall_health = "healthy" if healthy_services > total_services * 0.8 else \
                        "degraded" if healthy_services > total_services * 0.5 else "unhealthy"
        
        return {
            "overall_health": overall_health,
            "healthy_services": healthy_services,
            "total_services": total_services,
            "services": services_status,
            "last_update": datetime.now(timezone.utc).isoformat()
        }
    
    async def connect_to_service_websocket(self, service_name: str) -> bool:
        """Connect to a service's WebSocket endpoint"""
        if service_name not in self.services:
            return False
        
        service = self.services[service_name]
        if not service.websocket_endpoint:
            return False
        
        try:
            ws_url = f"ws://localhost:{service.port}{service.websocket_endpoint}"
            ws = await websockets.connect(ws_url)
            self.websocket_connections[service_name] = ws
            
            # Start listening task
            task = asyncio.create_task(self._listen_to_websocket(service_name, ws))
            self.monitoring_tasks.append(task)
            
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to connect to {service_name} WebSocket: {e}")
            return False
    
    async def _listen_to_websocket(self, service_name: str, websocket):
        """Listen to WebSocket messages from a service"""
        try:
            async for message in websocket:
                data = json.loads(message)
                await self._handle_websocket_message(service_name, data)
        except websockets.exceptions.ConnectionClosed:
            self.logger.info(f"WebSocket connection to {service_name} closed")
        except Exception as e:
            self.logger.error(f"WebSocket error for {service_name}: {e}")
        finally:
            if service_name in self.websocket_connections:
                del self.websocket_connections[service_name]
    
    async def _handle_websocket_message(self, service_name: str, message: Dict[str, Any]):
        """Handle incoming WebSocket messages from services"""
        message_type = message.get("type")
        
        if message_type == "service_update":
            # Update service information
            service = self.services.get(service_name)
            if service:
                service.last_check = datetime.now(timezone.utc)
                if "status" in message:
                    service.status = ServiceStatus(message["status"])
        
        elif message_type == "project_context":
            # Handle project context updates
            await self._handle_context_update(service_name, message.get("data", {}))
        
        elif message_type == "knowledge_update":
            # Handle knowledge graph updates
            await self._handle_knowledge_update(service_name, message.get("data", {}))
    
    async def _handle_context_update(self, service_name: str, context_data: Dict[str, Any]):
        """Handle context updates from services"""
        self.logger.info(f"Received context update from {service_name}")
        # This would integrate with the project memory system
        # to update the knowledge graph or context optimizer
    
    async def _handle_knowledge_update(self, service_name: str, knowledge_data: Dict[str, Any]):
        """Handle knowledge updates from services"""
        self.logger.info(f"Received knowledge update from {service_name}")
        # This would integrate with the knowledge graph system
    
    async def send_to_service(self, service_name: str, endpoint: str, 
                             data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Send data to a specific service endpoint"""
        if service_name not in self.services:
            return None
        
        service = self.services[service_name]
        url = f"{service.url}{endpoint}"
        
        try:
            async with self.session.post(url, json=data) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {"error": f"HTTP {response.status}"}
        except Exception as e:
            return {"error": str(e)}
    
    async def broadcast_to_all_services(self, endpoint: str, 
                                      data: Dict[str, Any]) -> Dict[str, Any]:
        """Broadcast data to all healthy services"""
        results = {}
        
        for service_name, service in self.services.items():
            if service.status == ServiceStatus.HEALTHY and service_name != "project-memory":
                result = await self.send_to_service(service_name, endpoint, data)
                results[service_name] = result
        
        return results
    
    async def get_service_capabilities(self) -> Dict[str, List[str]]:
        """Get capabilities of all services for intelligent routing"""
        capabilities = {}
        
        for name, service in self.services.items():
            if service.status == ServiceStatus.HEALTHY:
                try:
                    capabilities_url = f"{service.url}/capabilities"
                    async with self.session.get(capabilities_url) as response:
                        if response.status == 200:
                            data = await response.json()
                            capabilities[name] = data.get("capabilities", service.features)
                        else:
                            capabilities[name] = service.features
                except:
                    capabilities[name] = service.features
        
        return capabilities
    
    async def find_best_service_for_task(self, task_description: str, 
                                       task_type: str = None) -> Optional[str]:
        """Find the best service to handle a specific task"""
        capabilities = await self.get_service_capabilities()
        
        # Simple keyword matching for service selection
        task_lower = task_description.lower()
        
        service_keywords = {
            "bot-orchestrator": ["bot", "ai", "claude", "task", "orchestration"],
            "luciddreamer-core": ["dream", "simulation", "quantum", "reality"],
            "business-platform": ["business", "financial", "portfolio", "analytics"],
            "paper-trading": ["trading", "market", "portfolio", "stock"],
            "code-director": ["code", "development", "programming", "architecture"],
            "project-memory": ["memory", "knowledge", "context", "documentation"]
        }
        
        best_service = None
        best_score = 0
        
        for service_name, keywords in service_keywords.items():
            if service_name in self.services and self.services[service_name].status == ServiceStatus.HEALTHY:
                score = sum(1 for keyword in keywords if keyword in task_lower)
                if score > best_score:
                    best_score = score
                    best_service = service_name
        
        return best_service
    
    async def get_dependency_graph(self) -> Dict[str, Any]:
        """Generate dependency graph for all services"""
        graph = {
            "services": [],
            "dependencies": [],
            "external_dependencies": set()
        }
        
        for service_name, service in self.services.items():
            graph["services"].append({
                "name": service_name,
                "port": service.port,
                "phase": service.phase,
                "status": service.status.value
            })
            
            for dep in service.dependencies:
                if dep in self.services:
                    # Internal dependency
                    graph["dependencies"].append({
                        "from": service_name,
                        "to": dep,
                        "type": "internal"
                    })
                else:
                    # External dependency
                    graph["external_dependencies"].add(dep)
                    graph["dependencies"].append({
                        "from": service_name,
                        "to": dep,
                        "type": "external"
                    })
        
        graph["external_dependencies"] = list(graph["external_dependencies"])
        return graph
    
    async def optimize_service_communication(self) -> Dict[str, Any]:
        """Optimize communication patterns between services"""
        # This would analyze communication patterns and suggest optimizations
        dependency_graph = await self.get_dependency_graph()
        
        optimization_suggestions = []
        
        # Find circular dependencies
        visited = set()
        rec_stack = set()
        
        def has_cycle(service, dependencies, visited, rec_stack):
            visited.add(service)
            rec_stack.add(service)
            
            for dep in dependencies.get(service, []):
                if dep not in visited:
                    if has_cycle(dep, dependencies, visited, rec_stack):
                        return True
                elif dep in rec_stack:
                    return True
            
            rec_stack.remove(service)
            return False
        
        # Build dependency map
        dep_map = {}
        for dep in dependency_graph["dependencies"]:
            if dep["type"] == "internal":
                if dep["from"] not in dep_map:
                    dep_map[dep["from"]] = []
                dep_map[dep["from"]].append(dep["to"])
        
        # Check for cycles
        for service in dep_map:
            if service not in visited:
                if has_cycle(service, dep_map, visited, rec_stack):
                    optimization_suggestions.append({
                        "type": "circular_dependency",
                        "description": f"Circular dependency detected involving {service}",
                        "severity": "high"
                    })
        
        return {
            "suggestions": optimization_suggestions,
            "dependency_graph": dependency_graph,
            "analysis_timestamp": datetime.now(timezone.utc).isoformat()
        }