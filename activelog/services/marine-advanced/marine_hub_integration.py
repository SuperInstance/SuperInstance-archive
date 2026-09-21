"""
Marine Services Integration Hub
Centralized hub connecting all marine services to marine-advanced
"""

import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import json
import uuid

logger = logging.getLogger(__name__)

class MarineServiceStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"

class OperationType(str, Enum):
    FISHING = "fishing"
    NAVIGATION = "navigation"
    FLEET_COMMAND = "fleet_command"
    EMERGENCY = "emergency"
    LOGISTICS = "logistics"
    INSPECTION = "inspection"

@dataclass
class MarineServiceInfo:
    service_name: str
    service_url: str
    port: int
    capabilities: List[str]
    status: MarineServiceStatus
    last_health_check: datetime
    version: str = "1.0.0"
    priority: int = 1  # 1=highest, 5=lowest

@dataclass
class MarineOperation:
    operation_id: str
    operation_type: OperationType
    service: str
    parameters: Dict[str, Any]
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class MarineLoadBalancer:
    """Load balancer for marine services"""
    
    def __init__(self):
        self.service_weights = {}
        self.current_loads = {}
    
    def select_service(self, operation_type: OperationType, available_services: List[MarineServiceInfo]) -> Optional[MarineServiceInfo]:
        """Select best service for operation based on load and capability"""
        # Filter services that can handle the operation
        capable_services = [s for s in available_services if self._can_handle_operation(s, operation_type)]
        
        if not capable_services:
            return None
        
        # Select service with lowest load and highest priority
        best_service = min(capable_services, key=lambda s: (
            self.current_loads.get(s.service_name, 0),
            s.priority,
            s.status != MarineServiceStatus.HEALTHY
        ))
        
        return best_service
    
    def _can_handle_operation(self, service: MarineServiceInfo, operation_type: OperationType) -> bool:
        """Check if service can handle specific operation type"""
        capability_map = {
            OperationType.FISHING: ["fishing_management", "catch_logging", "quota_management"],
            OperationType.NAVIGATION: ["navigation", "route_planning", "position_tracking"],
            OperationType.FLEET_COMMAND: ["fleet_management", "vessel_command", "logistics"],
            OperationType.EMERGENCY: ["emergency_response", "search_rescue", "medical_assistance"],
            OperationType.LOGISTICS: ["supply_coordination", "fuel_management", "port_scheduling"],
            OperationType.INSPECTION: ["vessel_inspection", "compliance_check", "certification"]
        }
        
        required_capabilities = capability_map.get(operation_type, [])
        service_capabilities = service.capabilities
        
        return any(cap in service_capabilities for cap in required_capabilities)

class MarineRequestRouter:
    """Request router for marine operations"""
    
    def __init__(self):
        self.routing_rules = {}
        self.failover_services = {}
    
    def route_operation(self, operation: MarineOperation, services: Dict[str, MarineServiceInfo]) -> Optional[str]:
        """Route operation to appropriate service"""
        # Check for specific routing rules
        if operation.operation_type in self.routing_rules:
            preferred_service = self.routing_rules[operation.operation_type]
            if preferred_service in services and services[preferred_service].status == MarineServiceStatus.HEALTHY:
                return preferred_service
        
        # Default routing based on operation type
        routing_map = {
            OperationType.FISHING: "marine-fishing",
            OperationType.NAVIGATION: "cocapn",
            OperationType.FLEET_COMMAND: "capitaine",
            OperationType.EMERGENCY: "cocapn",  # Co-captain handles emergencies
            OperationType.LOGISTICS: "capitaine",  # Captain handles fleet logistics
            OperationType.INSPECTION: "capitaine"  # Captain manages inspections
        }
        
        preferred_service = routing_map.get(operation.operation_type)
        if preferred_service and preferred_service in services:
            if services[preferred_service].status == MarineServiceStatus.HEALTHY:
                return preferred_service
        
        # Fallback to any available service that can handle the operation
        for service_name, service_info in services.items():
            if service_info.status == MarineServiceStatus.HEALTHY:
                load_balancer = MarineLoadBalancer()
                if load_balancer._can_handle_operation(service_info, operation.operation_type):
                    return service_name
        
        return None

class MarineHubIntegrator:
    """Central hub integrating all marine services"""
    
    def __init__(self):
        self.services = {}
        self.service_health = {}
        self.operations_queue = {}
        self.completed_operations = {}
        self.load_balancer = MarineLoadBalancer()
        self.request_router = MarineRequestRouter()
        
        # Initialize marine services
        self._initialize_marine_services()
        
        # Start background tasks
        self.health_check_task = None
        self.operation_processor_task = None
    
    def _initialize_marine_services(self):
        """Initialize all marine services"""
        marine_services = [
            MarineServiceInfo(
                service_name="marine-fishing",
                service_url="http://localhost:8027",
                port=8027,
                capabilities=[
                    "fishing_management", "catch_logging", "quota_management",
                    "trip_planning", "compliance_checking", "gear_optimization"
                ],
                status=MarineServiceStatus.HEALTHY,
                last_health_check=datetime.utcnow(),
                priority=2
            ),
            MarineServiceInfo(
                service_name="cocapn",
                service_url="http://localhost:8026",
                port=8026,
                capabilities=[
                    "navigation", "route_planning", "crew_coordination",
                    "weather_monitoring", "emergency_response", "position_tracking"
                ],
                status=MarineServiceStatus.HEALTHY,
                last_health_check=datetime.utcnow(),
                priority=1
            ),
            MarineServiceInfo(
                service_name="capitaine",
                service_url="http://localhost:8028",
                port=8028,
                capabilities=[
                    "fleet_management", "vessel_command", "logistics",
                    "inspection_management", "crew_management", "performance_monitoring"
                ],
                status=MarineServiceStatus.HEALTHY,
                last_health_check=datetime.utcnow(),
                priority=1
            )
        ]
        
        for service in marine_services:
            self.services[service.service_name] = service
            self.service_health[service.service_name] = {
                "status": service.status,
                "last_check": service.last_health_check,
                "response_time": 0.0,
                "error_rate": 0.0,
                "total_requests": 0,
                "failed_requests": 0
            }
    
    async def start_integration_hub(self):
        """Start the marine integration hub"""
        logger.info("Starting Marine Integration Hub...")
        
        # Start health checking
        self.health_check_task = asyncio.create_task(self._health_check_loop())
        
        # Start operation processing
        self.operation_processor_task = asyncio.create_task(self._operation_processor_loop())
        
        # Perform initial health checks
        await self._check_all_services_health()
        
        logger.info("Marine Integration Hub started successfully")
    
    async def stop_integration_hub(self):
        """Stop the marine integration hub"""
        if self.health_check_task:
            self.health_check_task.cancel()
        if self.operation_processor_task:
            self.operation_processor_task.cancel()
        
        logger.info("Marine Integration Hub stopped")
    
    async def register_marine_operation(self, operation_type: OperationType, parameters: Dict[str, Any], 
                                       priority: int = 1) -> str:
        """Register a new marine operation"""
        operation_id = str(uuid.uuid4())
        
        operation = MarineOperation(
            operation_id=operation_id,
            operation_type=operation_type,
            service="",  # Will be assigned during routing
            parameters=parameters,
            status="pending",
            created_at=datetime.utcnow()
        )
        
        # Route operation to appropriate service
        target_service = self.request_router.route_operation(operation, self.services)
        
        if not target_service:
            operation.status = "failed"
            operation.error = "No available service to handle operation"
            self.completed_operations[operation_id] = operation
            raise ValueError(f"No service available for operation type: {operation_type}")
        
        operation.service = target_service
        self.operations_queue[operation_id] = operation
        
        logger.info(f"Registered marine operation {operation_id} for service {target_service}")
        return operation_id
    
    async def execute_marine_operation(self, operation_id: str) -> Dict[str, Any]:
        """Execute a marine operation"""
        if operation_id not in self.operations_queue:
            if operation_id in self.completed_operations:
                return asdict(self.completed_operations[operation_id])
            raise ValueError(f"Operation {operation_id} not found")
        
        operation = self.operations_queue[operation_id]
        
        try:
            # Update operation status
            operation.status = "executing"
            
            # Get service info
            service_info = self.services[operation.service]
            
            # Execute operation on target service
            result = await self._execute_on_service(service_info, operation)
            
            # Update operation with result
            operation.result = result
            operation.status = "completed"
            operation.completed_at = datetime.utcnow()
            
            # Move to completed operations
            self.completed_operations[operation_id] = operation
            del self.operations_queue[operation_id]
            
            # Update service health metrics
            self._update_service_metrics(operation.service, success=True)
            
            return asdict(operation)
            
        except Exception as e:
            operation.status = "failed"
            operation.error = str(e)
            operation.completed_at = datetime.utcnow()
            
            # Move to completed operations
            self.completed_operations[operation_id] = operation
            del self.operations_queue[operation_id]
            
            # Update service health metrics
            self._update_service_metrics(operation.service, success=False)
            
            logger.error(f"Operation {operation_id} failed: {e}")
            return asdict(operation)
    
    async def get_marine_services_status(self) -> Dict[str, Any]:
        """Get status of all marine services"""
        service_statuses = {}
        
        for service_name, service_info in self.services.items():
            health_info = self.service_health[service_name]
            service_statuses[service_name] = {
                "service_info": asdict(service_info),
                "health_metrics": health_info,
                "capabilities": service_info.capabilities,
                "current_load": self.load_balancer.current_loads.get(service_name, 0)
            }
        
        return {
            "services": service_statuses,
            "total_services": len(self.services),
            "healthy_services": len([s for s in self.services.values() if s.status == MarineServiceStatus.HEALTHY]),
            "pending_operations": len(self.operations_queue),
            "completed_operations": len(self.completed_operations)
        }
    
    async def get_marine_operations_summary(self) -> Dict[str, Any]:
        """Get summary of marine operations"""
        # Analyze completed operations
        operation_stats = {
            "total_operations": len(self.completed_operations),
            "successful_operations": 0,
            "failed_operations": 0,
            "operations_by_type": {},
            "operations_by_service": {},
            "average_execution_time": 0.0
        }
        
        total_execution_time = 0.0
        
        for operation in self.completed_operations.values():
            # Count by status
            if operation.status == "completed":
                operation_stats["successful_operations"] += 1
            elif operation.status == "failed":
                operation_stats["failed_operations"] += 1
            
            # Count by type
            op_type = operation.operation_type
            operation_stats["operations_by_type"][op_type] = operation_stats["operations_by_type"].get(op_type, 0) + 1
            
            # Count by service
            service = operation.service
            operation_stats["operations_by_service"][service] = operation_stats["operations_by_service"].get(service, 0) + 1
            
            # Calculate execution time
            if operation.completed_at and operation.created_at:
                execution_time = (operation.completed_at - operation.created_at).total_seconds()
                total_execution_time += execution_time
        
        # Calculate average execution time
        if operation_stats["total_operations"] > 0:
            operation_stats["average_execution_time"] = total_execution_time / operation_stats["total_operations"]
        
        return {
            "summary": operation_stats,
            "pending_operations": len(self.operations_queue),
            "service_performance": await self._calculate_service_performance()
        }
    
    async def handle_marine_emergency(self, emergency_type: str, vessel_id: str, location: Dict[str, float], 
                                    details: Dict[str, Any]) -> str:
        """Handle marine emergency situation"""
        emergency_operation = await self.register_marine_operation(
            operation_type=OperationType.EMERGENCY,
            parameters={
                "emergency_type": emergency_type,
                "vessel_id": vessel_id,
                "location": location,
                "details": details,
                "priority": "critical"
            },
            priority=0  # Highest priority
        )
        
        # Execute immediately for emergencies
        result = await self.execute_marine_operation(emergency_operation)
        
        # Coordinate with other services if needed
        await self._coordinate_emergency_response(emergency_type, vessel_id, location, details)
        
        return emergency_operation
    
    # Helper methods
    
    async def _health_check_loop(self):
        """Background task for continuous health checking"""
        while True:
            try:
                await self._check_all_services_health()
                await asyncio.sleep(30)  # Check every 30 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def _operation_processor_loop(self):
        """Background task for processing queued operations"""
        while True:
            try:
                # Process pending operations
                pending_ops = list(self.operations_queue.keys())
                for op_id in pending_ops:
                    if len(pending_ops) > 10:  # Process in batches
                        await asyncio.sleep(0.1)
                    await self.execute_marine_operation(op_id)
                
                await asyncio.sleep(5)  # Process every 5 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Operation processor error: {e}")
                await asyncio.sleep(10)
    
    async def _check_all_services_health(self):
        """Check health of all marine services"""
        health_check_tasks = []
        
        for service_name, service_info in self.services.items():
            task = self._check_service_health(service_name, service_info)
            health_check_tasks.append(task)
        
        # Run health checks concurrently
        await asyncio.gather(*health_check_tasks, return_exceptions=True)
    
    async def _check_service_health(self, service_name: str, service_info: MarineServiceInfo):
        """Check health of a specific service"""
        try:
            start_time = datetime.utcnow()
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                async with session.get(f"{service_info.service_url}/health") as response:
                    if response.status == 200:
                        health_data = await response.json()
                        
                        # Update service status
                        service_info.status = MarineServiceStatus.HEALTHY
                        service_info.last_health_check = datetime.utcnow()
                        
                        # Update health metrics
                        response_time = (datetime.utcnow() - start_time).total_seconds()
                        self.service_health[service_name]["response_time"] = response_time
                        self.service_health[service_name]["status"] = MarineServiceStatus.HEALTHY
                        self.service_health[service_name]["last_check"] = datetime.utcnow()
                        
                        return True
                    else:
                        raise aiohttp.ClientError(f"HTTP {response.status}")
                        
        except Exception as e:
            # Mark service as offline
            service_info.status = MarineServiceStatus.OFFLINE
            self.service_health[service_name]["status"] = MarineServiceStatus.OFFLINE
            self.service_health[service_name]["last_check"] = datetime.utcnow()
            
            logger.error(f"Health check failed for {service_name}: {e}")
            return False
    
    async def _execute_on_service(self, service_info: MarineServiceInfo, operation: MarineOperation) -> Dict[str, Any]:
        """Execute operation on specific service"""
        # Determine endpoint based on operation type
        endpoint_map = {
            OperationType.FISHING: "/api/fishing/operation",
            OperationType.NAVIGATION: "/api/navigation/operation",
            OperationType.FLEET_COMMAND: "/api/fleet/command",
            OperationType.EMERGENCY: "/api/emergency/handle",
            OperationType.LOGISTICS: "/api/logistics/coordinate",
            OperationType.INSPECTION: "/api/vessel/inspection"
        }
        
        endpoint = endpoint_map.get(operation.operation_type, "/api/operation")
        url = f"{service_info.service_url}{endpoint}"
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=operation.parameters) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    raise aiohttp.ClientError(f"Service error: {response.status} - {error_text}")
    
    def _update_service_metrics(self, service_name: str, success: bool):
        """Update service performance metrics"""
        if service_name in self.service_health:
            metrics = self.service_health[service_name]
            metrics["total_requests"] += 1
            
            if not success:
                metrics["failed_requests"] += 1
            
            # Calculate error rate
            metrics["error_rate"] = metrics["failed_requests"] / metrics["total_requests"]
    
    async def _calculate_service_performance(self) -> Dict[str, Any]:
        """Calculate performance metrics for each service"""
        performance = {}
        
        for service_name, health_info in self.service_health.items():
            total_requests = health_info["total_requests"]
            success_rate = (total_requests - health_info["failed_requests"]) / total_requests * 100 if total_requests > 0 else 0
            
            performance[service_name] = {
                "success_rate": success_rate,
                "average_response_time": health_info["response_time"],
                "error_rate": health_info["error_rate"],
                "total_requests": total_requests,
                "status": health_info["status"]
            }
        
        return performance
    
    async def _coordinate_emergency_response(self, emergency_type: str, vessel_id: str, 
                                           location: Dict[str, float], details: Dict[str, Any]):
        """Coordinate emergency response across all marine services"""
        # Notify all services about the emergency
        emergency_notification = {
            "event_type": "emergency_declared",
            "emergency_type": emergency_type,
            "vessel_id": vessel_id,
            "location": location,
            "details": details,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Send to all healthy services
        for service_name, service_info in self.services.items():
            if service_info.status == MarineServiceStatus.HEALTHY:
                try:
                    async with aiohttp.ClientSession() as session:
                        await session.post(
                            f"{service_info.service_url}/api/emergency/notification",
                            json=emergency_notification
                        )
                except Exception as e:
                    logger.error(f"Failed to notify {service_name} about emergency: {e}")

# Singleton instance
marine_hub_integrator = MarineHubIntegrator()