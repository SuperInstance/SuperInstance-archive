"""
Universal Hardware Abstraction System
Main service entry point for comprehensive device management and abstraction
Port: 8420
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import json

from core.udp_core import UniversalDeviceProtocol
from discovery.mdns_discovery import mDNSDeviceDiscovery
from device_types.device_registry import DeviceRegistry
from communication.comm_manager import CommunicationManager
from capability.negotiation import CapabilityNegotiator
from monitoring.health_monitor import DeviceHealthMonitor
from utils.config import Config
from utils.logger import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Hardware Abstraction System",
    description="Universal Device Protocol for comprehensive hardware management",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
config = Config()
udp_core: Optional[UniversalDeviceProtocol] = None
device_discovery: Optional[mDNSDeviceDiscovery] = None
device_registry: Optional[DeviceRegistry] = None
comm_manager: Optional[CommunicationManager] = None
capability_negotiator: Optional[CapabilityNegotiator] = None
health_monitor: Optional[DeviceHealthMonitor] = None

# WebSocket connections for real-time updates
active_connections: List[WebSocket] = []

@app.on_event("startup")
async def startup_event():
    """Initialize all hardware abstraction components"""
    global udp_core, device_discovery, device_registry, comm_manager
    global capability_negotiator, health_monitor
    
    logger.info("Starting Hardware Abstraction System...")
    
    try:
        # Initialize core UDP system
        udp_core = UniversalDeviceProtocol(config)
        await udp_core.initialize()
        
        # Initialize device discovery
        device_discovery = mDNSDeviceDiscovery(config)
        await device_discovery.start()
        
        # Initialize device registry
        device_registry = DeviceRegistry(config)
        await device_registry.initialize()
        
        # Initialize communication manager
        comm_manager = CommunicationManager(config)
        await comm_manager.initialize()
        
        # Initialize capability negotiator
        capability_negotiator = CapabilityNegotiator(config, comm_manager)
        await capability_negotiator.initialize()
        
        # Initialize health monitor
        health_monitor = DeviceHealthMonitor(config, device_registry)
        await health_monitor.start_monitoring()
        
        # Connect all components
        await connect_components()
        
        logger.info("Hardware Abstraction System started successfully")
        
    except Exception as e:
        logger.error(f"Failed to start Hardware Abstraction System: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup all components"""
    logger.info("Shutting down Hardware Abstraction System...")
    
    if health_monitor:
        await health_monitor.stop_monitoring()
    if device_discovery:
        await device_discovery.stop()
    if udp_core:
        await udp_core.shutdown()
    
    logger.info("Hardware Abstraction System shutdown complete")

async def connect_components():
    """Connect all system components together"""
    # Connect discovery to registry
    device_discovery.set_device_callback(device_registry.register_device)
    
    # Connect registry to capability negotiator
    device_registry.set_capability_callback(capability_negotiator.negotiate_capabilities)
    
    # Connect health monitor to WebSocket broadcasts
    health_monitor.set_status_callback(broadcast_device_status)

async def broadcast_device_status(device_id: str, status: Dict[str, Any]):
    """Broadcast device status updates to WebSocket clients"""
    if active_connections:
        message = {
            "type": "device_status_update",
            "device_id": device_id,
            "status": status,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        disconnected = []
        for connection in active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except:
                disconnected.append(connection)
        
        # Remove disconnected clients
        for connection in disconnected:
            active_connections.remove(connection)

# === REST API Endpoints ===

@app.get("/")
async def root():
    """Root endpoint with system information"""
    return {
        "service": "Hardware Abstraction System",
        "version": "1.0.0",
        "status": "active",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {
            "udp_core": "Universal Device Protocol",
            "discovery": "mDNS Device Discovery",
            "registry": "Device Registry",
            "communication": "Communication Manager", 
            "capability": "Capability Negotiator",
            "health": "Device Health Monitor"
        }
    }

@app.get("/api/system/status")
async def get_system_status():
    """Get overall system status"""
    try:
        status = {
            "system_health": "healthy",
            "active_devices": len(device_registry.get_all_devices()) if device_registry else 0,
            "discovery_active": device_discovery.is_active() if device_discovery else False,
            "communication_channels": comm_manager.get_active_channels() if comm_manager else [],
            "uptime": (datetime.utcnow() - config.start_time).total_seconds() if hasattr(config, 'start_time') else 0
        }
        return status
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/devices")
async def get_devices():
    """Get all registered devices"""
    try:
        if not device_registry:
            raise HTTPException(status_code=503, detail="Device registry not initialized")
        
        devices = device_registry.get_all_devices()
        return {"devices": devices, "count": len(devices)}
    except Exception as e:
        logger.error(f"Error getting devices: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/devices/{device_id}")
async def get_device(device_id: str):
    """Get specific device information"""
    try:
        if not device_registry:
            raise HTTPException(status_code=503, detail="Device registry not initialized")
        
        device = device_registry.get_device(device_id)
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")
        
        return device
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting device {device_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/devices/{device_id}/connect")
async def connect_device(device_id: str):
    """Connect to a specific device"""
    try:
        if not comm_manager:
            raise HTTPException(status_code=503, detail="Communication manager not initialized")
        
        result = await comm_manager.connect_device(device_id)
        return {"status": "connected" if result else "failed", "device_id": device_id}
    except Exception as e:
        logger.error(f"Error connecting to device {device_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/devices/{device_id}/disconnect")
async def disconnect_device(device_id: str):
    """Disconnect from a specific device"""
    try:
        if not comm_manager:
            raise HTTPException(status_code=503, detail="Communication manager not initialized")
        
        result = await comm_manager.disconnect_device(device_id)
        return {"status": "disconnected" if result else "failed", "device_id": device_id}
    except Exception as e:
        logger.error(f"Error disconnecting device {device_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/devices/{device_id}/capabilities")
async def get_device_capabilities(device_id: str):
    """Get device capabilities"""
    try:
        if not capability_negotiator:
            raise HTTPException(status_code=503, detail="Capability negotiator not initialized")
        
        capabilities = await capability_negotiator.get_device_capabilities(device_id)
        return {"device_id": device_id, "capabilities": capabilities}
    except Exception as e:
        logger.error(f"Error getting capabilities for device {device_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/devices/{device_id}/command")
async def send_device_command(device_id: str, command: dict):
    """Send command to device"""
    try:
        if not comm_manager:
            raise HTTPException(status_code=503, detail="Communication manager not initialized")
        
        result = await comm_manager.send_command(device_id, command)
        return {"device_id": device_id, "command_result": result}
    except Exception as e:
        logger.error(f"Error sending command to device {device_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/discovery/scan")
async def trigger_discovery_scan():
    """Trigger a new device discovery scan"""
    try:
        if not device_discovery:
            raise HTTPException(status_code=503, detail="Device discovery not initialized")
        
        await device_discovery.scan()
        return {"status": "scan_initiated", "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error(f"Error triggering discovery scan: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/discovery/status")
async def get_discovery_status():
    """Get discovery system status"""
    try:
        if not device_discovery:
            raise HTTPException(status_code=503, detail="Device discovery not initialized")
        
        return await device_discovery.get_status()
    except Exception as e:
        logger.error(f"Error getting discovery status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    try:
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "components": {
                "udp_core": bool(udp_core),
                "device_discovery": bool(device_discovery),
                "device_registry": bool(device_registry),
                "comm_manager": bool(comm_manager),
                "capability_negotiator": bool(capability_negotiator),
                "health_monitor": bool(health_monitor)
            }
        }
        return health_status
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}, 503

# === WebSocket Endpoints ===

@app.websocket("/ws/devices")
async def device_websocket(websocket: WebSocket):
    """WebSocket endpoint for real-time device updates"""
    await websocket.accept()
    active_connections.append(websocket)
    
    try:
        while True:
            # Keep connection alive and handle client messages
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle different message types
            if message.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
            elif message.get("type") == "subscribe_device":
                # Handle device-specific subscriptions
                device_id = message.get("device_id")
                if device_id and health_monitor:
                    await health_monitor.subscribe_device(device_id, websocket)
            
    except WebSocketDisconnect:
        active_connections.remove(websocket)
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if websocket in active_connections:
            active_connections.remove(websocket)

if __name__ == "__main__":
    # Set start time
    Config.start_time = datetime.utcnow()
    
    # Run the application
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8420,
        reload=True,
        log_level="info",
        access_log=True
    )