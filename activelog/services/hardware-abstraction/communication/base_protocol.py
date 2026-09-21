"""
Base Communication Protocol Class
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from enum import Enum

class ProtocolType(Enum):
    USB = "usb"
    ETHERNET = "ethernet"
    WIFI = "wifi"
    BLUETOOTH = "bluetooth"
    SERIAL = "serial"
    I2C = "i2c"
    SPI = "spi"
    CAN = "can"
    PCIE = "pcie"
    THUNDERBOLT = "thunderbolt"
    MQTT = "mqtt"
    HTTP = "http"
    WEBSOCKET = "websocket"
    MODBUS = "modbus"
    OPCUA = "opcua"
    ZIGBEE = "zigbee"
    LORA = "lora"
    QUANTUM = "quantum"

class QoSLevel(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

class CommunicationProtocol(ABC):
    """Base class for all communication protocols"""
    
    def __init__(self, protocol_type: ProtocolType):
        self.protocol_type = protocol_type
        self.is_connected = False
        self.max_bandwidth = 0
        self.current_bandwidth = 0
        self.latency = 0.0
        self.reliability = 0.95
        self.supported_qos_levels = [QoSLevel.LOW, QoSLevel.MEDIUM]
        self.devices = {}
        self.connection_params = {}
    
    @abstractmethod
    async def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize the protocol"""
        pass
    
    @abstractmethod
    async def connect(self, device_id: str, connection_params: Dict[str, Any]) -> bool:
        """Connect to a device"""
        pass
    
    @abstractmethod
    async def disconnect(self, device_id: str) -> bool:
        """Disconnect from a device"""
        pass
    
    @abstractmethod
    async def send_data(self, device_id: str, data: bytes, qos: QoSLevel = QoSLevel.MEDIUM) -> bool:
        """Send data to a device"""
        pass
    
    @abstractmethod
    async def receive_data(self, device_id: str, timeout: float = 5.0) -> Optional[bytes]:
        """Receive data from a device"""
        pass
    
    @abstractmethod
    async def get_status(self, device_id: str) -> Dict[str, Any]:
        """Get connection status"""
        pass
    
    def get_bandwidth_usage(self) -> float:
        """Get current bandwidth usage percentage"""
        if self.max_bandwidth == 0:
            return 0.0
        return (self.current_bandwidth / self.max_bandwidth) * 100
    
    def can_handle_qos(self, qos: QoSLevel) -> bool:
        """Check if protocol can handle specified QoS level"""
        return qos in self.supported_qos_levels
    
    def get_protocol_info(self) -> Dict[str, Any]:
        """Get protocol information"""
        return {
            "type": self.protocol_type.value,
            "max_bandwidth": self.max_bandwidth,
            "current_bandwidth": self.current_bandwidth,
            "latency": self.latency,
            "reliability": self.reliability,
            "connected_devices": len(self.devices),
            "bandwidth_usage": self.get_bandwidth_usage()
        }