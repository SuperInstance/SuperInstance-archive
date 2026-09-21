"""
CAN Bus Integration System
Comprehensive CAN bus communication for marine engine monitoring
"""

import asyncio
import logging
import struct
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
import json

logger = logging.getLogger(__name__)


class CANProtocol(Enum):
    """CAN protocol types"""
    CAN_2_0A = "can_2_0a"  # 11-bit identifier
    CAN_2_0B = "can_2_0b"  # 29-bit identifier
    CAN_FD = "can_fd"      # CAN with Flexible Data-Rate


class MessageType(Enum):
    """CAN message types"""
    DATA = "data"
    REMOTE = "remote"
    ERROR = "error"


class CANBitRate(Enum):
    """Standard CAN bit rates"""
    RATE_125K = 125000
    RATE_250K = 250000
    RATE_500K = 500000
    RATE_1M = 1000000


@dataclass
class CANMessage:
    """CAN bus message structure"""
    can_id: int
    data: bytes
    dlc: int  # Data Length Code
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_extended: bool = False
    is_remote: bool = False
    is_error: bool = False
    channel: str = "can0"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'can_id': hex(self.can_id),
            'can_id_dec': self.can_id,
            'data': self.data.hex(),
            'dlc': self.dlc,
            'timestamp': self.timestamp.isoformat(),
            'is_extended': self.is_extended,
            'is_remote': self.is_remote,
            'is_error': self.is_error,
            'channel': self.channel
        }


@dataclass
class CANFilter:
    """CAN message filter"""
    filter_id: str
    can_id: int
    mask: int = 0x7FF  # Default 11-bit mask
    description: str = ""
    enabled: bool = True
    
    def matches(self, message: CANMessage) -> bool:
        """Check if message matches filter"""
        return (message.can_id & self.mask) == (self.can_id & self.mask)


@dataclass
class EngineCANData:
    """Engine data from CAN bus"""
    engine_id: int
    can_messages: Dict[int, CANMessage] = field(default_factory=dict)
    
    # Parsed engine parameters
    rpm: Optional[float] = None
    coolant_temp: Optional[float] = None
    oil_pressure: Optional[float] = None
    fuel_pressure: Optional[float] = None
    intake_manifold_pressure: Optional[float] = None
    exhaust_gas_temp: Optional[float] = None
    turbo_boost: Optional[float] = None
    fuel_rate: Optional[float] = None
    throttle_position: Optional[float] = None
    battery_voltage: Optional[float] = None
    alternator_load: Optional[float] = None
    
    # Status indicators
    engine_running: bool = False
    alarms: List[str] = field(default_factory=list)
    fault_codes: List[str] = field(default_factory=list)
    
    last_update: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'engine_id': self.engine_id,
            'rpm': self.rpm,
            'coolant_temp': self.coolant_temp,
            'oil_pressure': self.oil_pressure,
            'fuel_pressure': self.fuel_pressure,
            'intake_manifold_pressure': self.intake_manifold_pressure,
            'exhaust_gas_temp': self.exhaust_gas_temp,
            'turbo_boost': self.turbo_boost,
            'fuel_rate': self.fuel_rate,
            'throttle_position': self.throttle_position,
            'battery_voltage': self.battery_voltage,
            'alternator_load': self.alternator_load,
            'engine_running': self.engine_running,
            'alarms': self.alarms,
            'fault_codes': self.fault_codes,
            'last_update': self.last_update.isoformat()
        }


class CANBusInterface:
    """CAN bus hardware interface abstraction"""
    
    def __init__(self, channel: str = "can0", bitrate: int = 250000):
        self.channel = channel
        self.bitrate = bitrate
        self.is_connected = False
        self.socket = None
        
    async def connect(self) -> bool:
        """Connect to CAN interface"""
        try:
            # In production, would initialize actual CAN interface
            logger.info(f"Connecting to CAN interface {self.channel} at {self.bitrate} bps")
            self.is_connected = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to CAN interface: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from CAN interface"""
        self.is_connected = False
        logger.info("CAN interface disconnected")
    
    async def send_message(self, message: CANMessage) -> bool:
        """Send CAN message"""
        try:
            if not self.is_connected:
                return False
            
            # In production, would send to actual CAN bus
            logger.debug(f"Sending CAN message: ID={hex(message.can_id)}, Data={message.data.hex()}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send CAN message: {e}")
            return False
    
    async def receive_message(self) -> Optional[CANMessage]:
        """Receive CAN message"""
        try:
            if not self.is_connected:
                return None
            
            # In production, would receive from actual CAN bus
            # For demo, return None (handled by simulator)
            return None
            
        except Exception as e:
            logger.error(f"Failed to receive CAN message: {e}")
            return None


class CANBusManager:
    """Main CAN bus management system"""
    
    def __init__(self):
        self.interfaces: Dict[str, CANBusInterface] = {}
        self.message_handlers: Dict[int, Callable] = {}
        self.filters: Dict[str, CANFilter] = {}
        self.subscribers: List[Callable] = []
        
        # Engine data tracking
        self.engines: Dict[int, EngineCANData] = {}
        
        # Message statistics
        self.messages_received = 0
        self.messages_sent = 0
        self.errors = 0
        
        # Background tasks
        self.running = False
        self.tasks: List[asyncio.Task] = []
        
        # Setup standard engine CAN message handlers
        self._setup_standard_handlers()
        
        logger.info("CANBusManager initialized")
    
    def _setup_standard_handlers(self):
        """Setup handlers for standard engine CAN messages"""
        # Common CAN IDs for marine engines (example values)
        self.message_handlers = {
            0x0CF00400: self._handle_engine_speed,      # Engine RPM
            0x0CFEF400: self._handle_engine_temp,       # Engine temperature
            0x0CFEF500: self._handle_oil_pressure,      # Oil pressure
            0x0CFEF600: self._handle_fuel_rate,         # Fuel consumption rate
            0x0CFEF700: self._handle_throttle_position, # Throttle position
            0x0CFEF800: self._handle_boost_pressure,    # Turbo boost pressure
            0x0CF00300: self._handle_transmission,      # Transmission data
            0x0CF00500: self._handle_electrical,        # Electrical system
            0x18FEF100: self._handle_diagnostic_codes,  # Diagnostic trouble codes
        }
        
        # Setup standard filters
        self._setup_standard_filters()
    
    def _setup_standard_filters(self):
        """Setup standard CAN filters for engine monitoring"""
        standard_filters = [
            CANFilter("engine_rpm", 0x0CF00400, 0x1FFFFFFF, "Engine RPM"),
            CANFilter("engine_temp", 0x0CFEF400, 0x1FFFFFFF, "Engine Temperature"),
            CANFilter("oil_pressure", 0x0CFEF500, 0x1FFFFFFF, "Oil Pressure"),
            CANFilter("fuel_rate", 0x0CFEF600, 0x1FFFFFFF, "Fuel Consumption"),
            CANFilter("throttle", 0x0CFEF700, 0x1FFFFFFF, "Throttle Position"),
            CANFilter("boost", 0x0CFEF800, 0x1FFFFFFF, "Boost Pressure"),
            CANFilter("electrical", 0x0CF00500, 0x1FFFFFFF, "Electrical System"),
            CANFilter("diagnostics", 0x18FEF100, 0x1FFFFFFF, "Diagnostic Codes"),
        ]
        
        for filter_obj in standard_filters:
            self.filters[filter_obj.filter_id] = filter_obj
    
    def add_interface(self, channel: str, bitrate: int = 250000) -> bool:
        """Add CAN interface"""
        try:
            interface = CANBusInterface(channel, bitrate)
            self.interfaces[channel] = interface
            logger.info(f"Added CAN interface {channel}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add CAN interface {channel}: {e}")
            return False
    
    async def start_monitoring(self):
        """Start CAN bus monitoring"""
        try:
            self.running = True
            
            # Connect all interfaces
            for channel, interface in self.interfaces.items():
                success = await interface.connect()
                if not success:
                    logger.error(f"Failed to connect to interface {channel}")
            
            # Start message processing tasks
            for channel in self.interfaces.keys():
                task = asyncio.create_task(self._message_processing_loop(channel))
                self.tasks.append(task)
            
            # Start demo data generator for testing
            demo_task = asyncio.create_task(self._demo_message_generator())
            self.tasks.append(demo_task)
            
            logger.info("CAN bus monitoring started")
            
        except Exception as e:
            logger.error(f"Failed to start CAN bus monitoring: {e}")
            raise
    
    async def stop_monitoring(self):
        """Stop CAN bus monitoring"""
        try:
            self.running = False
            
            # Cancel all tasks
            for task in self.tasks:
                task.cancel()
            
            # Wait for tasks to complete
            await asyncio.gather(*self.tasks, return_exceptions=True)
            self.tasks.clear()
            
            # Disconnect interfaces
            for interface in self.interfaces.values():
                await interface.disconnect()
            
            logger.info("CAN bus monitoring stopped")
            
        except Exception as e:
            logger.error(f"Error stopping CAN bus monitoring: {e}")
    
    async def _message_processing_loop(self, channel: str):
        """Process messages from CAN interface"""
        interface = self.interfaces[channel]
        
        while self.running:
            try:
                message = await interface.receive_message()
                if message:
                    await self._process_message(message)
                
                await asyncio.sleep(0.001)  # 1ms polling
                
            except Exception as e:
                logger.error(f"Error in message processing loop for {channel}: {e}")
                self.errors += 1
                await asyncio.sleep(0.1)
    
    async def _demo_message_generator(self):
        """Generate demo CAN messages for testing"""
        engine_id = 0
        message_counter = 0
        
        while self.running:
            try:
                import random
                
                # Generate various engine CAN messages
                messages = []
                
                # Engine RPM (0x0CF00400)
                rpm_value = 1800 + random.randint(-200, 400)
                rpm_data = struct.pack('<H', int(rpm_value * 8))  # RPM * 8 per spec
                rpm_data += b'\x00' * (8 - len(rpm_data))
                messages.append(CANMessage(0x0CF00400, rpm_data, 8))
                
                # Engine temperature (0x0CFEF400)
                temp_value = 85 + random.randint(-10, 15)
                temp_data = struct.pack('<H', int((temp_value + 273.15) * 32))  # Convert to Kelvin * 32
                temp_data += b'\x00' * (8 - len(temp_data))
                messages.append(CANMessage(0x0CFEF400, temp_data, 8))
                
                # Oil pressure (0x0CFEF500)
                pressure_value = 350 + random.randint(-50, 50)
                pressure_data = struct.pack('<H', int(pressure_value * 8))  # kPa * 8
                pressure_data += b'\x00' * (8 - len(pressure_data))
                messages.append(CANMessage(0x0CFEF500, pressure_data, 8))
                
                # Fuel rate (0x0CFEF600)
                fuel_rate = 15.5 + random.uniform(-2, 3)
                fuel_data = struct.pack('<H', int(fuel_rate * 20))  # L/hr * 20
                fuel_data += b'\x00' * (8 - len(fuel_data))
                messages.append(CANMessage(0x0CFEF600, fuel_data, 8))
                
                # Process generated messages
                for message in messages:
                    await self._process_message(message)
                
                message_counter += len(messages)
                await asyncio.sleep(0.1)  # 100ms interval
                
            except Exception as e:
                logger.error(f"Error in demo message generator: {e}")
                await asyncio.sleep(1)
    
    async def _process_message(self, message: CANMessage):
        """Process received CAN message"""
        try:
            self.messages_received += 1
            
            # Apply filters
            if not self._message_passes_filters(message):
                return
            
            # Route to appropriate handler
            handler = self.message_handlers.get(message.can_id)
            if handler:
                await handler(message)
            
            # Notify subscribers
            await self._notify_subscribers(message)
            
        except Exception as e:
            logger.error(f"Error processing CAN message: {e}")
            self.errors += 1
    
    def _message_passes_filters(self, message: CANMessage) -> bool:
        """Check if message passes active filters"""
        if not self.filters:
            return True  # No filters = accept all
        
        for filter_obj in self.filters.values():
            if filter_obj.enabled and filter_obj.matches(message):
                return True
        
        return False
    
    async def _notify_subscribers(self, message: CANMessage):
        """Notify subscribers of new CAN message"""
        for subscriber in self.subscribers:
            try:
                await subscriber(message)
            except Exception as e:
                logger.error(f"Error notifying subscriber: {e}")
    
    # Message handlers for different CAN IDs
    async def _handle_engine_speed(self, message: CANMessage):
        """Handle engine RPM message"""
        try:
            if len(message.data) >= 2:
                rpm = struct.unpack('<H', message.data[0:2])[0] / 8.0
                
                engine_id = self._extract_engine_id(message)
                engine_data = self._get_or_create_engine_data(engine_id)
                engine_data.rpm = rpm
                engine_data.engine_running = rpm > 100
                engine_data.last_update = message.timestamp
                
                logger.debug(f"Engine {engine_id} RPM: {rpm}")
                
        except Exception as e:
            logger.error(f"Error handling engine speed message: {e}")
    
    async def _handle_engine_temp(self, message: CANMessage):
        """Handle engine temperature message"""
        try:
            if len(message.data) >= 2:
                temp_kelvin = struct.unpack('<H', message.data[0:2])[0] / 32.0
                temp_celsius = temp_kelvin - 273.15
                
                engine_id = self._extract_engine_id(message)
                engine_data = self._get_or_create_engine_data(engine_id)
                engine_data.coolant_temp = temp_celsius
                engine_data.last_update = message.timestamp
                
                # Check for overheat alarm
                if temp_celsius > 95:
                    if "high_coolant_temp" not in engine_data.alarms:
                        engine_data.alarms.append("high_coolant_temp")
                else:
                    if "high_coolant_temp" in engine_data.alarms:
                        engine_data.alarms.remove("high_coolant_temp")
                
                logger.debug(f"Engine {engine_id} temperature: {temp_celsius:.1f}°C")
                
        except Exception as e:
            logger.error(f"Error handling engine temperature message: {e}")
    
    async def _handle_oil_pressure(self, message: CANMessage):
        """Handle oil pressure message"""
        try:
            if len(message.data) >= 2:
                pressure_kpa = struct.unpack('<H', message.data[0:2])[0] / 8.0
                
                engine_id = self._extract_engine_id(message)
                engine_data = self._get_or_create_engine_data(engine_id)
                engine_data.oil_pressure = pressure_kpa
                engine_data.last_update = message.timestamp
                
                # Check for low pressure alarm
                if pressure_kpa < 200:
                    if "low_oil_pressure" not in engine_data.alarms:
                        engine_data.alarms.append("low_oil_pressure")
                else:
                    if "low_oil_pressure" in engine_data.alarms:
                        engine_data.alarms.remove("low_oil_pressure")
                
                logger.debug(f"Engine {engine_id} oil pressure: {pressure_kpa:.1f} kPa")
                
        except Exception as e:
            logger.error(f"Error handling oil pressure message: {e}")
    
    async def _handle_fuel_rate(self, message: CANMessage):
        """Handle fuel consumption rate message"""
        try:
            if len(message.data) >= 2:
                fuel_rate = struct.unpack('<H', message.data[0:2])[0] / 20.0
                
                engine_id = self._extract_engine_id(message)
                engine_data = self._get_or_create_engine_data(engine_id)
                engine_data.fuel_rate = fuel_rate
                engine_data.last_update = message.timestamp
                
                logger.debug(f"Engine {engine_id} fuel rate: {fuel_rate:.1f} L/hr")
                
        except Exception as e:
            logger.error(f"Error handling fuel rate message: {e}")
    
    async def _handle_throttle_position(self, message: CANMessage):
        """Handle throttle position message"""
        try:
            if len(message.data) >= 1:
                throttle_pct = message.data[0] / 2.55  # Convert to percentage
                
                engine_id = self._extract_engine_id(message)
                engine_data = self._get_or_create_engine_data(engine_id)
                engine_data.throttle_position = throttle_pct
                engine_data.last_update = message.timestamp
                
                logger.debug(f"Engine {engine_id} throttle: {throttle_pct:.1f}%")
                
        except Exception as e:
            logger.error(f"Error handling throttle position message: {e}")
    
    async def _handle_boost_pressure(self, message: CANMessage):
        """Handle turbo boost pressure message"""
        try:
            if len(message.data) >= 2:
                boost_kpa = struct.unpack('<H', message.data[0:2])[0] / 8.0
                
                engine_id = self._extract_engine_id(message)
                engine_data = self._get_or_create_engine_data(engine_id)
                engine_data.turbo_boost = boost_kpa
                engine_data.last_update = message.timestamp
                
                logger.debug(f"Engine {engine_id} boost pressure: {boost_kpa:.1f} kPa")
                
        except Exception as e:
            logger.error(f"Error handling boost pressure message: {e}")
    
    async def _handle_transmission(self, message: CANMessage):
        """Handle transmission data message"""
        try:
            # Parse transmission-specific data
            logger.debug("Processing transmission data")
            
        except Exception as e:
            logger.error(f"Error handling transmission message: {e}")
    
    async def _handle_electrical(self, message: CANMessage):
        """Handle electrical system message"""
        try:
            if len(message.data) >= 4:
                voltage = struct.unpack('<H', message.data[0:2])[0] / 100.0
                current = struct.unpack('<h', message.data[2:4])[0] / 10.0
                
                engine_id = self._extract_engine_id(message)
                engine_data = self._get_or_create_engine_data(engine_id)
                engine_data.battery_voltage = voltage
                engine_data.alternator_load = abs(current)
                engine_data.last_update = message.timestamp
                
                logger.debug(f"Engine {engine_id} electrical: {voltage:.1f}V, {current:.1f}A")
                
        except Exception as e:
            logger.error(f"Error handling electrical message: {e}")
    
    async def _handle_diagnostic_codes(self, message: CANMessage):
        """Handle diagnostic trouble codes"""
        try:
            # Parse diagnostic trouble codes from message
            if len(message.data) >= 4:
                fault_code = struct.unpack('<I', message.data[0:4])[0]
                
                engine_id = self._extract_engine_id(message)
                engine_data = self._get_or_create_engine_data(engine_id)
                
                fault_code_str = f"P{fault_code:04X}"
                if fault_code_str not in engine_data.fault_codes:
                    engine_data.fault_codes.append(fault_code_str)
                    engine_data.last_update = message.timestamp
                    
                    logger.warning(f"Engine {engine_id} fault code: {fault_code_str}")
                
        except Exception as e:
            logger.error(f"Error handling diagnostic codes: {e}")
    
    def _extract_engine_id(self, message: CANMessage) -> int:
        """Extract engine ID from CAN message"""
        # In real implementation, would parse from CAN ID or message data
        # For demo, use simple mapping
        return 0  # Default engine
    
    def _get_or_create_engine_data(self, engine_id: int) -> EngineCANData:
        """Get or create engine data structure"""
        if engine_id not in self.engines:
            self.engines[engine_id] = EngineCANData(engine_id=engine_id)
        return self.engines[engine_id]
    
    # Public interface methods
    def add_message_handler(self, can_id: int, handler: Callable):
        """Add custom message handler"""
        self.message_handlers[can_id] = handler
        logger.info(f"Added handler for CAN ID 0x{can_id:X}")
    
    def add_filter(self, filter_obj: CANFilter):
        """Add CAN message filter"""
        self.filters[filter_obj.filter_id] = filter_obj
        logger.info(f"Added CAN filter: {filter_obj.description}")
    
    def subscribe_to_messages(self, callback: Callable):
        """Subscribe to CAN message updates"""
        self.subscribers.append(callback)
        logger.info(f"Added CAN message subscriber")
    
    async def send_message(self, channel: str, message: CANMessage) -> bool:
        """Send CAN message on specified channel"""
        interface = self.interfaces.get(channel)
        if interface:
            success = await interface.send_message(message)
            if success:
                self.messages_sent += 1
            return success
        return False
    
    def get_engine_data(self, engine_id: Optional[int] = None) -> Dict[str, Any]:
        """Get engine data from CAN bus"""
        if engine_id is not None:
            engine = self.engines.get(engine_id)
            return engine.to_dict() if engine else {}
        else:
            return {str(eid): engine.to_dict() for eid, engine in self.engines.items()}
    
    def get_can_statistics(self) -> Dict[str, Any]:
        """Get CAN bus statistics"""
        return {
            'interfaces': len(self.interfaces),
            'connected_interfaces': sum(1 for i in self.interfaces.values() if i.is_connected),
            'messages_received': self.messages_received,
            'messages_sent': self.messages_sent,
            'errors': self.errors,
            'active_filters': len([f for f in self.filters.values() if f.enabled]),
            'engines_detected': len(self.engines),
            'message_handlers': len(self.message_handlers),
            'subscribers': len(self.subscribers)
        }
    
    def diagnose_can_network(self) -> Dict[str, Any]:
        """Diagnose CAN network health"""
        diagnosis = {
            'overall_health': 'good',
            'issues': [],
            'recommendations': []
        }
        
        # Check message rates
        if self.messages_received == 0:
            diagnosis['issues'].append('No messages received')
            diagnosis['overall_health'] = 'poor'
        
        # Check error rates
        if self.errors > 0:
            error_rate = self.errors / max(self.messages_received, 1) * 100
            if error_rate > 5:
                diagnosis['issues'].append(f'High error rate: {error_rate:.1f}%')
                diagnosis['overall_health'] = 'fair'
        
        # Check engine responses
        for engine_id, engine_data in self.engines.items():
            age = (datetime.now(timezone.utc) - engine_data.last_update).total_seconds()
            if age > 5:  # No update in 5 seconds
                diagnosis['issues'].append(f'Engine {engine_id} not responding')
                diagnosis['overall_health'] = 'fair'
        
        return diagnosis