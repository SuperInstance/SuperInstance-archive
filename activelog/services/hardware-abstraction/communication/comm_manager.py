"""
Communication Manager
Handles all device communication protocols and abstractions
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from abc import ABC, abstractmethod
import json

from .base_protocol import CommunicationProtocol, ProtocolType, QoSLevel

logger = logging.getLogger(__name__)

class CommunicationProtocol(ABC):
    """Base class for communication protocols"""
    
    def __init__(self):
        self.protocol_name = ""
        self.supported_speeds = []
        self.max_devices = 1
        self.active_connections = {}
    
    @abstractmethod
    async def connect(self, device_id: str, connection_params: Dict[str, Any]) -> bool:
        """Connect to a device"""
        pass
    
    @abstractmethod
    async def disconnect(self, device_id: str) -> bool:
        """Disconnect from a device"""
        pass
    
    @abstractmethod
    async def send_data(self, device_id: str, data: bytes) -> bool:
        """Send data to device"""
        pass
    
    @abstractmethod
    async def receive_data(self, device_id: str, size: int = 1024) -> bytes:
        """Receive data from device"""
        pass
    
    @abstractmethod
    async def get_connection_status(self, device_id: str) -> Dict[str, Any]:
        """Get connection status"""
        pass
    
    async def validate_connection_params(self, params: Dict[str, Any]) -> bool:
        """Validate connection parameters"""
        return True

class CommunicationManager:
    """Central communication manager for all protocols"""
    
    def __init__(self, config):
        self.config = config
        self.protocols: Dict[str, CommunicationProtocol] = {}
        self.device_connections: Dict[str, str] = {}  # device_id -> protocol
        self.bandwidth_manager = BandwidthManager()
        self.qos_manager = QoSManager()
        self.load_balancer = LoadBalancer()
        
    async def initialize(self):
        """Initialize communication manager and protocols"""
        logger.info("Initializing Communication Manager...")
        
        # Import protocol classes at runtime to avoid circular imports
        try:
            from .protocols import (
                USBProtocol, ThunderboltProtocol, PCIeProtocol, EthernetProtocol,
                WiFiProtocol, BluetoothProtocol, ZigbeeProtocol, ZWaveProtocol,
                LoRaProtocol, SerialProtocol, I2CProtocol, SPIProtocol,
                CANProtocol, MQTTProtocol, HTTPProtocol, WebSocketProtocol,
                ModbusProtocol, OPCUAProtocol, QuantumProtocol
            )
        except ImportError as e:
            logger.error(f"Failed to import protocol classes: {e}")
            # Create minimal protocol set for basic functionality
            from .base_protocol import CommunicationProtocol
            class DummyProtocol(CommunicationProtocol):
                async def initialize(self, config): return True
                async def connect(self, device_id, params): return True
                async def disconnect(self, device_id): return True
                async def send_data(self, device_id, data, qos=None): return True
                async def receive_data(self, device_id, timeout=5.0): return b""
                async def get_status(self, device_id): return {"status": "ok"}
            
            USBProtocol = ThunderboltProtocol = PCIeProtocol = DummyProtocol
            EthernetProtocol = WiFiProtocol = BluetoothProtocol = DummyProtocol
            ZigbeeProtocol = ZWaveProtocol = LoRaProtocol = DummyProtocol
            SerialProtocol = I2CProtocol = SPIProtocol = DummyProtocol
            CANProtocol = MQTTProtocol = HTTPProtocol = DummyProtocol
            WebSocketProtocol = ModbusProtocol = OPCUAProtocol = DummyProtocol
            QuantumProtocol = CellularProtocol = SatelliteProtocol = DummyProtocol
        
        # Initialize all protocol handlers
        protocol_classes = {
            'usb': USBProtocol,
            'thunderbolt': ThunderboltProtocol,
            'pcie': PCIeProtocol,
            'ethernet': EthernetProtocol,
            'wifi': WiFiProtocol,
            'bluetooth': BluetoothProtocol,
            'zigbee': ZigbeeProtocol,
            'zwave': ZWaveProtocol,
            'lora': LoRaProtocol,
            'cellular': CellularProtocol,
            'satellite': SatelliteProtocol,
            'quantum': QuantumProtocol,
            'serial': SerialProtocol,
            'can': CANProtocol,
            'modbus': ModbusProtocol,
            'opcua': OPCUAProtocol
        }
        
        for protocol_name, protocol_class in protocol_classes.items():
            try:
                protocol = protocol_class()
                await protocol.initialize()
                self.protocols[protocol_name] = protocol
                logger.info(f"Initialized protocol: {protocol_name}")
            except Exception as e:
                logger.error(f"Failed to initialize protocol {protocol_name}: {e}")
        
        # Initialize managers
        await self.bandwidth_manager.initialize()
        await self.qos_manager.initialize()
        await self.load_balancer.initialize()
        
        logger.info(f"Communication Manager initialized with {len(self.protocols)} protocols")
    
    async def connect_device(self, device_id: str, protocol: str = None, 
                           connection_params: Dict[str, Any] = None) -> bool:
        """Connect to a device using specified or auto-detected protocol"""
        try:
            if protocol is None:
                protocol = await self.auto_detect_protocol(device_id, connection_params)
            
            if protocol not in self.protocols:
                logger.error(f"Protocol not supported: {protocol}")
                return False
            
            protocol_handler = self.protocols[protocol]
            
            # Validate connection parameters
            if connection_params and not await protocol_handler.validate_connection_params(connection_params):
                logger.error(f"Invalid connection parameters for {protocol}")
                return False
            
            # Check bandwidth availability
            if not await self.bandwidth_manager.check_availability(protocol, connection_params):
                logger.warning(f"Insufficient bandwidth for {device_id} on {protocol}")
                return False
            
            # Attempt connection
            success = await protocol_handler.connect(device_id, connection_params or {})
            
            if success:
                self.device_connections[device_id] = protocol
                
                # Allocate bandwidth
                await self.bandwidth_manager.allocate(device_id, protocol, connection_params)
                
                # Setup QoS
                await self.qos_manager.setup_device_qos(device_id, protocol)
                
                logger.info(f"Device connected: {device_id} via {protocol}")
                return True
            else:
                logger.error(f"Failed to connect device: {device_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error connecting device {device_id}: {e}")
            return False
    
    async def disconnect_device(self, device_id: str) -> bool:
        """Disconnect a device"""
        try:
            if device_id not in self.device_connections:
                logger.warning(f"Device not connected: {device_id}")
                return False
            
            protocol = self.device_connections[device_id]
            protocol_handler = self.protocols[protocol]
            
            success = await protocol_handler.disconnect(device_id)
            
            if success:
                # Release bandwidth
                await self.bandwidth_manager.release(device_id)
                
                # Remove QoS
                await self.qos_manager.remove_device_qos(device_id)
                
                # Remove from connections
                del self.device_connections[device_id]
                
                logger.info(f"Device disconnected: {device_id}")
                return True
            else:
                logger.error(f"Failed to disconnect device: {device_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error disconnecting device {device_id}: {e}")
            return False
    
    async def send_command(self, device_id: str, command: Dict[str, Any]) -> Dict[str, Any]:
        """Send command to device"""
        try:
            if device_id not in self.device_connections:
                return {"error": "Device not connected"}
            
            protocol = self.device_connections[device_id]
            protocol_handler = self.protocols[protocol]
            
            # Serialize command
            command_data = json.dumps(command).encode('utf-8')
            
            # Send command
            success = await protocol_handler.send_data(device_id, command_data)
            
            if not success:
                return {"error": "Failed to send command"}
            
            # Wait for response
            try:
                response_data = await asyncio.wait_for(
                    protocol_handler.receive_data(device_id),
                    timeout=30.0
                )
                
                if response_data:
                    response = json.loads(response_data.decode('utf-8'))
                    return response
                else:
                    return {"result": "command_sent", "no_response": True}
                    
            except asyncio.TimeoutError:
                return {"result": "command_sent", "timeout": True}
            except json.JSONDecodeError:
                return {"result": "command_sent", "invalid_response": True}
            
        except Exception as e:
            logger.error(f"Error sending command to {device_id}: {e}")
            return {"error": str(e)}
    
    async def auto_detect_protocol(self, device_id: str, 
                                 connection_params: Dict[str, Any] = None) -> str:
        """Auto-detect best protocol for device"""
        
        # Default detection logic
        if connection_params:
            # Check for specific protocol hints
            if 'usb_vendor_id' in connection_params:
                return 'usb'
            elif 'ip_address' in connection_params:
                return 'ethernet'
            elif 'mac_address' in connection_params:
                if 'wifi' in connection_params.get('interface_type', ''):
                    return 'wifi'
                else:
                    return 'bluetooth'
            elif 'serial_port' in connection_params:
                return 'serial'
            elif 'can_interface' in connection_params:
                return 'can'
        
        # Default fallback
        return 'ethernet'
    
    async def get_connection_status(self, device_id: str) -> Dict[str, Any]:
        """Get connection status for device"""
        if device_id not in self.device_connections:
            return {"connected": False}
        
        protocol = self.device_connections[device_id]
        protocol_handler = self.protocols[protocol]
        
        status = await protocol_handler.get_connection_status(device_id)
        status.update({
            "protocol": protocol,
            "bandwidth_allocation": await self.bandwidth_manager.get_allocation(device_id),
            "qos_profile": await self.qos_manager.get_qos_profile(device_id)
        })
        
        return status
    
    def get_active_channels(self) -> List[str]:
        """Get list of active communication channels"""
        return list(self.protocols.keys())
    
    async def optimize_connections(self):
        """Optimize all active connections"""
        try:
            # Load balance connections
            await self.load_balancer.rebalance_connections(self.device_connections)
            
            # Optimize bandwidth allocation
            await self.bandwidth_manager.optimize()
            
            # Adjust QoS parameters
            await self.qos_manager.optimize()
            
        except Exception as e:
            logger.error(f"Error optimizing connections: {e}")

class BandwidthManager:
    """Manages bandwidth allocation across protocols"""
    
    def __init__(self):
        self.total_bandwidth = {}  # protocol -> total bandwidth
        self.allocated_bandwidth = {}  # protocol -> allocated bandwidth
        self.device_allocations = {}  # device_id -> allocation info
    
    async def initialize(self):
        """Initialize bandwidth manager"""
        # Set default bandwidth limits (would be discovered from actual hardware)
        self.total_bandwidth = {
            'usb': 480,  # Mbps (USB 2.0)
            'usb3': 5000,  # Mbps (USB 3.0)
            'thunderbolt': 40000,  # Mbps (Thunderbolt 3)
            'pcie': 32000,  # Mbps (PCIe 4.0 x16)
            'ethernet': 1000,  # Mbps (Gigabit)
            'wifi': 866,  # Mbps (Wi-Fi 5)
            'bluetooth': 3,  # Mbps (Bluetooth 5)
            'zigbee': 0.25,  # Mbps
            'zwave': 0.1,  # Mbps
            'lora': 0.05,  # Mbps
            'cellular': 1000,  # Mbps (5G)
            'satellite': 100,  # Mbps
            'serial': 0.115,  # Mbps (115200 baud)
            'can': 1,  # Mbps
            'modbus': 0.0384,  # Mbps
        }
        
        self.allocated_bandwidth = {protocol: 0 for protocol in self.total_bandwidth}
    
    async def check_availability(self, protocol: str, params: Dict[str, Any]) -> bool:
        """Check if bandwidth is available"""
        if protocol not in self.total_bandwidth:
            return True  # Unknown protocols assumed to have no limits
        
        required = params.get('bandwidth_requirement', 10)  # Default 10 Mbps
        available = self.total_bandwidth[protocol] - self.allocated_bandwidth[protocol]
        
        return available >= required
    
    async def allocate(self, device_id: str, protocol: str, params: Dict[str, Any]):
        """Allocate bandwidth for device"""
        required = params.get('bandwidth_requirement', 10)
        
        if protocol in self.allocated_bandwidth:
            self.allocated_bandwidth[protocol] += required
        
        self.device_allocations[device_id] = {
            'protocol': protocol,
            'allocated': required,
            'timestamp': datetime.utcnow()
        }
    
    async def release(self, device_id: str):
        """Release bandwidth allocation"""
        if device_id in self.device_allocations:
            allocation = self.device_allocations[device_id]
            protocol = allocation['protocol']
            
            if protocol in self.allocated_bandwidth:
                self.allocated_bandwidth[protocol] -= allocation['allocated']
                self.allocated_bandwidth[protocol] = max(0, self.allocated_bandwidth[protocol])
            
            del self.device_allocations[device_id]
    
    async def get_allocation(self, device_id: str) -> Dict[str, Any]:
        """Get bandwidth allocation for device"""
        return self.device_allocations.get(device_id, {})
    
    async def optimize(self):
        """Optimize bandwidth allocation"""
        # Could implement bandwidth optimization algorithms here
        pass

class QoSManager:
    """Quality of Service manager"""
    
    def __init__(self):
        self.qos_profiles = {}
        self.device_qos = {}
    
    async def initialize(self):
        """Initialize QoS manager"""
        # Define QoS profiles
        self.qos_profiles = {
            'real_time': {
                'priority': 1,
                'max_latency': 10,  # ms
                'min_bandwidth': 100,  # Mbps
                'jitter_tolerance': 1  # ms
            },
            'interactive': {
                'priority': 2,
                'max_latency': 50,
                'min_bandwidth': 10,
                'jitter_tolerance': 5
            },
            'bulk': {
                'priority': 3,
                'max_latency': 1000,
                'min_bandwidth': 1,
                'jitter_tolerance': 100
            },
            'background': {
                'priority': 4,
                'max_latency': 5000,
                'min_bandwidth': 0.1,
                'jitter_tolerance': 1000
            }
        }
    
    async def setup_device_qos(self, device_id: str, protocol: str):
        """Setup QoS for device"""
        # Auto-assign QoS profile based on device type and protocol
        if protocol in ['usb', 'thunderbolt', 'pcie']:
            profile = 'real_time'
        elif protocol in ['ethernet', 'wifi']:
            profile = 'interactive'
        else:
            profile = 'bulk'
        
        self.device_qos[device_id] = {
            'profile': profile,
            'settings': self.qos_profiles[profile].copy(),
            'protocol': protocol
        }
    
    async def remove_device_qos(self, device_id: str):
        """Remove QoS settings for device"""
        if device_id in self.device_qos:
            del self.device_qos[device_id]
    
    async def get_qos_profile(self, device_id: str) -> Dict[str, Any]:
        """Get QoS profile for device"""
        return self.device_qos.get(device_id, {})
    
    async def optimize(self):
        """Optimize QoS settings"""
        # Could implement dynamic QoS optimization
        pass

class LoadBalancer:
    """Load balances connections across available channels"""
    
    def __init__(self):
        self.channel_loads = {}
    
    async def initialize(self):
        """Initialize load balancer"""
        pass
    
    async def rebalance_connections(self, device_connections: Dict[str, str]):
        """Rebalance device connections across channels"""
        # Count connections per protocol
        protocol_counts = {}
        for device_id, protocol in device_connections.items():
            protocol_counts[protocol] = protocol_counts.get(protocol, 0) + 1
        
        self.channel_loads = protocol_counts
        
        # Could implement more sophisticated load balancing
        # For now, just log the current distribution
        logger.debug(f"Channel loads: {self.channel_loads}")
    
    async def get_best_channel(self, requirements: Dict[str, Any]) -> str:
        """Get best channel for requirements"""
        # Simple load-based selection
        if not self.channel_loads:
            return 'ethernet'  # Default
        
        # Return channel with lowest load
        return min(self.channel_loads.items(), key=lambda x: x[1])[0]