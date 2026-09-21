"""
Comprehensive REST API Routes for Hardware Abstraction System
Advanced endpoints with full CRUD operations, filtering, pagination, and real-time capabilities
"""

from fastapi import APIRouter, HTTPException, Depends, Query, WebSocket, BackgroundTasks
from fastapi.responses import StreamingResponse
from typing import List, Dict, Any, Optional
import json
import asyncio
from datetime import datetime
import logging

from core.udp_core import DeviceManifest, DeviceCapability
from device_types.device_registry import DeviceRegistry
from communication.comm_manager import CommunicationManager
from capability.negotiation import CapabilityNegotiator
from monitoring.health_monitor import DeviceHealthMonitor
from api.models import *
from api.auth import get_current_user, require_permissions
from api.validation import validate_config_update, get_security_config
from utils.analytics import AnalyticsEngine
from utils.ml_classifier import DeviceClassifier

logger = logging.getLogger(__name__)

# API Router
router = APIRouter()

# Global system components (will be injected)
device_registry: DeviceRegistry = None
comm_manager: CommunicationManager = None
capability_negotiator: CapabilityNegotiator = None
health_monitor: DeviceHealthMonitor = None
analytics_engine: AnalyticsEngine = None
ml_classifier: DeviceClassifier = None

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.device_subscribers: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        # Remove from device subscriptions
        for device_id, subs in self.device_subscribers.items():
            if websocket in subs:
                subs.remove(websocket)
    
    async def broadcast(self, message: dict):
        """Broadcast to all connections"""
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except:
                await self.disconnect(connection)
    
    async def send_to_device_subscribers(self, device_id: str, message: dict):
        """Send message to subscribers of specific device"""
        if device_id in self.device_subscribers:
            for connection in self.device_subscribers[device_id].copy():
                try:
                    await connection.send_text(json.dumps(message))
                except:
                    self.device_subscribers[device_id].remove(connection)

connection_manager = ConnectionManager()

# ===== ENHANCED DEVICE MANAGEMENT ENDPOINTS =====

@router.get("/devices", response_model=DeviceListResponse)
async def list_devices(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=1000, description="Items per page"),
    device_type: Optional[str] = Query(None, description="Filter by device type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    protocol: Optional[str] = Query(None, description="Filter by protocol"),
    search: Optional[str] = Query(None, description="Search in device names/IDs"),
    sort_by: Optional[str] = Query("created_at", description="Sort field"),
    sort_order: Optional[str] = Query("desc", description="Sort order (asc/desc)"),
    user = Depends(get_current_user)
):
    """Enhanced device listing with advanced filtering, pagination, and search"""
    try:
        # Get all devices
        all_devices = await device_registry.get_all_devices()
        
        # Apply filters
        filtered_devices = all_devices
        if device_type:
            filtered_devices = [d for d in filtered_devices if d.device_type == device_type]
        if status:
            filtered_devices = [d for d in filtered_devices if await device_registry.get_device_status(d.device_id) == status]
        if protocol:
            filtered_devices = [d for d in filtered_devices if protocol in d.supported_protocols]
        if search:
            search_lower = search.lower()
            filtered_devices = [d for d in filtered_devices 
                             if search_lower in d.device_id.lower() or 
                                search_lower in d.name.lower() or
                                search_lower in d.description.lower()]
        
        # Sort devices
        reverse = sort_order.lower() == "desc"
        if sort_by == "name":
            filtered_devices.sort(key=lambda x: x.name, reverse=reverse)
        elif sort_by == "type":
            filtered_devices.sort(key=lambda x: x.device_type, reverse=reverse)
        elif sort_by == "created_at":
            filtered_devices.sort(key=lambda x: x.created_at, reverse=reverse)
        
        # Paginate
        total_items = len(filtered_devices)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_devices = filtered_devices[start_idx:end_idx]
        
        # Enhance with real-time status and analytics
        enhanced_devices = []
        for device in paginated_devices:
            device_data = device.to_dict()
            device_data["current_status"] = await device_registry.get_device_status(device.device_id)
            device_data["health_score"] = await health_monitor.get_device_health_score(device.device_id)
            device_data["analytics"] = await analytics_engine.get_device_metrics(device.device_id)
            enhanced_devices.append(device_data)
        
        return DeviceListResponse(
            devices=enhanced_devices,
            pagination=PaginationInfo(
                page=page,
                page_size=page_size,
                total_items=total_items,
                total_pages=(total_items + page_size - 1) // page_size
            ),
            filters={
                "device_type": device_type,
                "status": status,
                "protocol": protocol,
                "search": search
            }
        )
    
    except Exception as e:
        logger.error(f"Error listing devices: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/devices/{device_id}", response_model=DeviceDetailResponse)
async def get_device(
    device_id: str,
    include_metrics: bool = Query(True, description="Include performance metrics"),
    include_capabilities: bool = Query(True, description="Include device capabilities"),
    include_history: bool = Query(False, description="Include device history"),
    user = Depends(get_current_user)
):
    """Get comprehensive device information with optional detailed data"""
    try:
        device = await device_registry.get_device(device_id)
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")
        
        device_data = device.to_dict()
        
        # Add real-time status
        device_data["current_status"] = await device_registry.get_device_status(device_id)
        device_data["connection_info"] = await comm_manager.get_connection_info(device_id)
        device_data["health_score"] = await health_monitor.get_device_health_score(device_id)
        
        if include_capabilities:
            handler = await device_registry.get_device_handler(device.device_type)
            device_data["capabilities"] = await handler.get_device_capabilities(device_id)
            device_data["supported_commands"] = await handler.get_supported_commands()
        
        if include_metrics:
            device_data["metrics"] = await analytics_engine.get_detailed_metrics(device_id)
            device_data["performance_trends"] = await analytics_engine.get_performance_trends(device_id)
        
        if include_history:
            device_data["event_history"] = await analytics_engine.get_device_history(device_id, limit=100)
            device_data["maintenance_history"] = await health_monitor.get_maintenance_history(device_id)
        
        return DeviceDetailResponse(**device_data)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting device {device_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/devices/discover", response_model=DiscoveryResponse)
async def trigger_discovery(
    discovery_request: DiscoveryRequest,
    background_tasks: BackgroundTasks,
    user = Depends(require_permissions(["device:discover"]))
):
    """Trigger intelligent device discovery with ML classification"""
    try:
        discovery_id = f"discovery_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Start discovery in background
        background_tasks.add_task(
            run_enhanced_discovery,
            discovery_id,
            discovery_request
        )
        
        return DiscoveryResponse(
            discovery_id=discovery_id,
            status="started",
            estimated_duration=discovery_request.timeout or 30,
            protocols=discovery_request.protocols,
            filters=discovery_request.filters
        )
    
    except Exception as e:
        logger.error(f"Error starting discovery: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def run_enhanced_discovery(discovery_id: str, request: DiscoveryRequest):
    """Enhanced discovery with ML-based device classification"""
    try:
        # Notify start
        await connection_manager.broadcast({
            "type": "discovery_started",
            "discovery_id": discovery_id,
            "timestamp": datetime.now().isoformat()
        })
        
        # Run multi-protocol discovery
        discovered_devices = []
        for protocol in request.protocols:
            protocol_devices = await comm_manager.discover_devices(
                protocol, 
                timeout=request.timeout,
                filters=request.filters
            )
            discovered_devices.extend(protocol_devices)
        
        # Apply ML classification for unknown devices
        for device in discovered_devices:
            if not device.device_type or device.device_type == "unknown":
                classified_type = await ml_classifier.classify_device(device)
                device.device_type = classified_type
                device.confidence_score = await ml_classifier.get_classification_confidence(device)
        
        # Register discovered devices
        registered_count = 0
        for device in discovered_devices:
            if await device_registry.register_device(device):
                registered_count += 1
                
                # Notify new device
                await connection_manager.broadcast({
                    "type": "device_discovered",
                    "device": device.to_dict(),
                    "discovery_id": discovery_id,
                    "timestamp": datetime.now().isoformat()
                })
        
        # Notify completion
        await connection_manager.broadcast({
            "type": "discovery_completed",
            "discovery_id": discovery_id,
            "total_discovered": len(discovered_devices),
            "total_registered": registered_count,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Discovery {discovery_id} failed: {e}")
        await connection_manager.broadcast({
            "type": "discovery_failed",
            "discovery_id": discovery_id,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        })

# ===== REAL-TIME WEBSOCKET ENDPOINTS =====

@router.websocket("/ws/devices")
async def device_events_websocket(websocket: WebSocket):
    """Real-time device events WebSocket"""
    await connection_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and handle client messages
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "subscribe_device":
                device_id = message.get("device_id")
                if device_id not in connection_manager.device_subscribers:
                    connection_manager.device_subscribers[device_id] = []
                connection_manager.device_subscribers[device_id].append(websocket)
                
                await websocket.send_text(json.dumps({
                    "type": "subscription_confirmed",
                    "device_id": device_id,
                    "timestamp": datetime.now().isoformat()
                }))
            
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        connection_manager.disconnect(websocket)

@router.get("/devices/{device_id}/stream")
async def stream_device_data(device_id: str, user = Depends(get_current_user)):
    """Stream real-time device data via Server-Sent Events"""
    async def event_stream():
        try:
            while True:
                # Get current device metrics
                status = await device_registry.get_device_status(device_id)
                metrics = await analytics_engine.get_real_time_metrics(device_id)
                health = await health_monitor.get_device_health_score(device_id)
                
                data = {
                    "device_id": device_id,
                    "timestamp": datetime.now().isoformat(),
                    "status": status,
                    "metrics": metrics,
                    "health_score": health
                }
                
                yield f"data: {json.dumps(data)}\n\n"
                await asyncio.sleep(1)  # Update every second
                
        except Exception as e:
            logger.error(f"Stream error for device {device_id}: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(
        event_stream(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

# ===== ADVANCED DEVICE CONTROL ENDPOINTS =====

@router.post("/devices/{device_id}/commands", response_model=CommandResponse)
async def execute_device_command(
    device_id: str,
    command_request: DeviceCommandRequest,
    user = Depends(require_permissions(["device:control"]))
):
    """Execute advanced device commands with validation and monitoring"""
    try:
        # Validate device exists
        device = await device_registry.get_device(device_id)
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")
        
        # Get device handler
        handler = await device_registry.get_device_handler(device.device_type)
        if not handler:
            raise HTTPException(status_code=500, detail="No handler available for device type")
        
        # Validate command
        if not await handler.validate_command(device_id, command_request.command, command_request.parameters):
            raise HTTPException(status_code=400, detail="Invalid command or parameters")
        
        # Check device health before executing critical commands
        if command_request.command in ["reset", "firmware_update", "factory_reset"]:
            health_score = await health_monitor.get_device_health_score(device_id)
            if health_score < 0.7:
                raise HTTPException(
                    status_code=423, 
                    detail=f"Device health too low ({health_score:.2f}) for critical operation"
                )
        
        # Execute command with timeout
        execution_id = f"cmd_{device_id}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        # Notify command start
        await connection_manager.send_to_device_subscribers(device_id, {
            "type": "command_started",
            "device_id": device_id,
            "execution_id": execution_id,
            "command": command_request.command,
            "timestamp": datetime.now().isoformat()
        })
        
        # Execute command
        start_time = datetime.now()
        try:
            result = await asyncio.wait_for(
                handler.execute_command(device_id, command_request.command, command_request.parameters),
                timeout=command_request.timeout or 30
            )
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Log command execution
            await analytics_engine.log_command_execution(
                device_id, command_request.command, execution_time, "success", result
            )
            
            response = CommandResponse(
                execution_id=execution_id,
                device_id=device_id,
                command=command_request.command,
                status="completed",
                result=result,
                execution_time=execution_time,
                timestamp=datetime.now().isoformat()
            )
            
            # Notify completion
            await connection_manager.send_to_device_subscribers(device_id, {
                "type": "command_completed",
                **response.dict(),
                "timestamp": datetime.now().isoformat()
            })
            
            return response
            
        except asyncio.TimeoutError:
            await analytics_engine.log_command_execution(
                device_id, command_request.command, 
                (datetime.now() - start_time).total_seconds(), 
                "timeout", None
            )
            raise HTTPException(status_code=408, detail="Command execution timed out")
        
        except Exception as cmd_error:
            await analytics_engine.log_command_execution(
                device_id, command_request.command,
                (datetime.now() - start_time).total_seconds(),
                "error", str(cmd_error)
            )
            raise HTTPException(status_code=500, detail=f"Command execution failed: {str(cmd_error)}")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing command on device {device_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ===== ANALYTICS AND MONITORING ENDPOINTS =====

@router.get("/analytics/system", response_model=SystemAnalytics)
async def get_system_analytics(
    time_range: str = Query("24h", description="Time range (1h, 24h, 7d, 30d)"),
    user = Depends(get_current_user)
):
    """Get comprehensive system analytics and insights"""
    try:
        analytics = await analytics_engine.get_system_analytics(time_range)
        return SystemAnalytics(**analytics)
    except Exception as e:
        logger.error(f"Error getting system analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics/devices/{device_id}/insights", response_model=DeviceInsights)
async def get_device_insights(
    device_id: str,
    user = Depends(get_current_user)
):
    """Get AI-powered insights for specific device"""
    try:
        insights = await analytics_engine.generate_device_insights(device_id)
        return DeviceInsights(**insights)
    except Exception as e:
        logger.error(f"Error getting device insights for {device_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ===== HEALTH AND MAINTENANCE ENDPOINTS =====

@router.get("/health/summary", response_model=HealthSummary)
async def get_health_summary(user = Depends(get_current_user)):
    """Get system-wide health summary with predictive maintenance alerts"""
    try:
        summary = await health_monitor.get_system_health_summary()
        return HealthSummary(**summary)
    except Exception as e:
        logger.error(f"Error getting health summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/maintenance/predict", response_model=MaintenancePrediction)
async def predict_maintenance(
    prediction_request: MaintenancePredictionRequest,
    user = Depends(require_permissions(["maintenance:predict"]))
):
    """Get AI-powered predictive maintenance recommendations"""
    try:
        prediction = await health_monitor.predict_maintenance(
            prediction_request.device_id,
            prediction_request.prediction_horizon,
            prediction_request.include_cost_analysis
        )
        return MaintenancePrediction(**prediction)
    except Exception as e:
        logger.error(f"Error predicting maintenance: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ===== SYSTEM CONFIGURATION ENDPOINTS =====

@router.get("/config", response_model=SystemConfig)
async def get_system_config(
    user = Depends(require_permissions(["system:read"]))
):
    """Get current system configuration"""
    try:
        config = {
            "discovery": await device_registry.get_discovery_config(),
            "communication": await comm_manager.get_config(),
            "monitoring": await health_monitor.get_config(),
            "security": await get_security_config(),
            "performance": await analytics_engine.get_performance_config()
        }
        return SystemConfig(**config)
    except Exception as e:
        logger.error(f"Error getting system config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/config", response_model=ConfigUpdateResponse)
async def update_system_config(
    config_update: SystemConfigUpdate,
    user = Depends(require_permissions(["system:configure"]))
):
    """Update system configuration with validation"""
    try:
        # Validate configuration
        validation_result = await validate_config_update(config_update)
        if not validation_result.is_valid:
            raise HTTPException(status_code=400, detail=validation_result.errors)
        
        # Apply configuration updates
        update_results = {}
        
        if config_update.discovery:
            update_results["discovery"] = await device_registry.update_discovery_config(config_update.discovery)
        
        if config_update.communication:
            update_results["communication"] = await comm_manager.update_config(config_update.communication)
        
        if config_update.monitoring:
            update_results["monitoring"] = await health_monitor.update_config(config_update.monitoring)
        
        return ConfigUpdateResponse(
            success=True,
            updated_components=list(update_results.keys()),
            results=update_results,
            timestamp=datetime.now().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating system config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def setup_routes(
    registry: DeviceRegistry,
    comm: CommunicationManager, 
    negotiator: CapabilityNegotiator,
    monitor: DeviceHealthMonitor,
    analytics: AnalyticsEngine,
    classifier: DeviceClassifier
):
    """Initialize route dependencies"""
    global device_registry, comm_manager, capability_negotiator, health_monitor, analytics_engine, ml_classifier
    device_registry = registry
    comm_manager = comm
    capability_negotiator = negotiator
    health_monitor = monitor
    analytics_engine = analytics
    ml_classifier = classifier