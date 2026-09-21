"""
Base Device Handler Class
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from datetime import datetime
from core.udp_core import DeviceManifest, DeviceCapability

class BaseDeviceHandler(ABC):
    """Base class for all device handlers"""
    
    def __init__(self):
        self.device_type = ""
        self.supported_protocols = []
        self.capabilities = []
    
    async def initialize_device(self, manifest: DeviceManifest) -> bool:
        """Initialize the device"""
        # Basic initialization - can be overridden in subclasses
        return True
    
    async def connect_device(self, device_id: str, manifest: Optional[DeviceManifest] = None) -> bool:
        """Connect to the device"""
        # Basic connection - can be overridden in subclasses
        return True
    
    async def disconnect_device(self, device_id: str) -> bool:
        """Disconnect from the device"""
        # Basic disconnection - can be overridden in subclasses  
        return True
    
    async def get_device_status(self, device_id: str) -> Dict[str, Any]:
        """Get current device status"""
        # Basic status - can be overridden in subclasses
        return {
            "device_id": device_id,
            "status": "connected",
            "health": "ok",
            "timestamp": datetime.now().isoformat()
        }
    
    async def execute_command(self, device_id: str, command: str, params: Dict[str, Any]) -> Any:
        """Execute a command on the device"""
        # Default implementation for basic commands
        if command == "get_status":
            return await self.get_device_status(device_id)
        elif command == "connect":
            return await self.connect_device(device_id)
        elif command == "disconnect":
            return await self.disconnect_device(device_id)
        else:
            # Return success for unknown commands (can be overridden in subclasses)
            return {"status": "success", "message": f"Command '{command}' executed"}
    
    async def get_device_capabilities(self, device_id: str) -> List[DeviceCapability]:
        """Get device capabilities"""
        # Return basic capabilities by default
        return self.capabilities or []
    
    def get_supported_capabilities(self) -> List[DeviceCapability]:
        """Get list of supported capabilities"""
        return self.capabilities
    
    def supports_protocol(self, protocol: str) -> bool:
        """Check if handler supports a specific protocol"""
        return protocol in self.supported_protocols