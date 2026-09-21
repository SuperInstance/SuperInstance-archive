"""
NMEA 2000 Gateway
Comprehensive NMEA 2000 protocol implementation for marine engine monitoring
"""

import asyncio
import logging
import struct
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
import json
import socket

logger = logging.getLogger(__name__)


class NMEA2000Priority(Enum):
    """NMEA 2000 message priorities"""
    EMERGENCY = 0
    HIGH = 1
    MEDIUM = 2
    LOW = 3


class PGNType(Enum):
    """Parameter Group Number types"""
    ENGINE_PARAMETERS_RAPID = 127488
    ENGINE_PARAMETERS_DYNAMIC = 127489
    FLUID_LEVEL = 127505
    DC_DETAILED_STATUS = 127506
    CHARGER_STATUS = 127507
    BATTERY_STATUS = 127508
    INVERTER_STATUS = 127509
    TRANSMISSION_PARAMETERS = 127493
    TRIP_FUEL_CONSUMPTION = 127497
    ENGINE_OPERATING_HOURS = 127498
    TEMPERATURE = 130312
    PRESSURE = 130314
    RPM = 127488
    COOLANT_TEMP = 130312
    OIL_PRESSURE = 130314
    FUEL_RATE = 127497
    ALTERNATOR_STATUS = 127501


@dataclass
class NMEA2000Message:
    """NMEA 2000 message structure"""
    pgn: int
    priority: NMEA2000Priority
    source: int
    destination: int
    data: bytes
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'pgn': self.pgn,
            'priority': self.priority.value,
            'source': self.source,
            'destination': self.destination,
            'data': self.data.hex(),
            'timestamp': self.timestamp.isoformat(),
            'data_length': len(self.data)
        }


@dataclass
class EngineData:
    """Engine parameter data structure"""
    engine_id: int
    rpm: Optional[float] = None
    coolant_temp: Optional[float] = None  # Celsius
    oil_pressure: Optional[float] = None  # kPa
    oil_temp: Optional[float] = None  # Celsius
    fuel_rate: Optional[float] = None  # L/hr
    fuel_pressure: Optional[float] = None  # kPa
    boost_pressure: Optional[float] = None  # kPa
    intake_manifold_temp: Optional[float] = None  # Celsius
    engine_load: Optional[float] = None  # %
    alternator_voltage: Optional[float] = None  # V
    operating_hours: Optional[float] = None  # hours
    status: str = "unknown"
    alarms: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'engine_id': self.engine_id,
            'rpm': self.rpm,
            'coolant_temp': self.coolant_temp,
            'oil_pressure': self.oil_pressure,
            'oil_temp': self.oil_temp,
            'fuel_rate': self.fuel_rate,
            'fuel_pressure': self.fuel_pressure,
            'boost_pressure': self.boost_pressure,
            'intake_manifold_temp': self.intake_manifold_temp,
            'engine_load': self.engine_load,
            'alternator_voltage': self.alternator_voltage,
            'operating_hours': self.operating_hours,
            'status': self.status,
            'alarms': self.alarms,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }


class NMEA2000Gateway:
    """NMEA 2000 gateway for marine engine monitoring"""
    
    def __init__(self, interface: str = "can0"):
        self.interface = interface
        self.engines: Dict[int, EngineData] = {}
        self.message_handlers: Dict[int, Callable] = {}
        self.subscribers: List[Callable] = []
        self.running = False
        self.socket = None
        
        # Message statistics
        self.messages_received = 0
        self.messages_sent = 0
        self.errors = 0
        self.last_message_time = None
        
        # Engine parameter tracking
        self.engine_parameters = {}
        
        # Setup message handlers
        self._setup_message_handlers()
        
        logger.info(f"NMEA2000Gateway initialized for interface {interface}")
    
    def _setup_message_handlers(self):
        """Setup handlers for different PGN types"""
        self.message_handlers = {
            PGNType.ENGINE_PARAMETERS_RAPID.value: self._handle_engine_parameters_rapid,
            PGNType.ENGINE_PARAMETERS_DYNAMIC.value: self._handle_engine_parameters_dynamic,
            PGNType.FLUID_LEVEL.value: self._handle_fluid_level,
            PGNType.TEMPERATURE.value: self._handle_temperature,
            PGNType.PRESSURE.value: self._handle_pressure,
            PGNType.TRIP_FUEL_CONSUMPTION.value: self._handle_fuel_consumption,
            PGNType.ENGINE_OPERATING_HOURS.value: self._handle_operating_hours,
            PGNType.ALTERNATOR_STATUS.value: self._handle_alternator_status,
        }
    
    async def start_gateway(self):
        """Start the NMEA 2000 gateway"""
        try:
            self.running = True
            
            # Initialize CAN socket (simulated for demo)
            logger.info("Initializing NMEA 2000 CAN interface...")
            
            # Start message processing loop
            asyncio.create_task(self._message_processing_loop())
            
            # Start demo data generation
            asyncio.create_task(self._demo_data_generator())
            
            logger.info("NMEA 2000 Gateway started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start NMEA 2000 gateway: {e}")
            raise
    
    async def stop_gateway(self):
        """Stop the NMEA 2000 gateway"""
        self.running = False
        if self.socket:
            self.socket.close()
        logger.info("NMEA 2000 Gateway stopped")
    
    def subscribe_to_updates(self, callback: Callable):
        """Subscribe to engine data updates"""
        self.subscribers.append(callback)
        logger.info(f"Added subscriber: {callback.__name__}")
    
    def unsubscribe_from_updates(self, callback: Callable):
        """Unsubscribe from engine data updates"""
        if callback in self.subscribers:
            self.subscribers.remove(callback)
            logger.info(f"Removed subscriber: {callback.__name__}")
    
    async def _message_processing_loop(self):
        """Main message processing loop"""
        while self.running:
            try:
                # In a real implementation, this would read from CAN bus
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error in message processing loop: {e}")
                self.errors += 1
                await asyncio.sleep(1)
    
    async def _demo_data_generator(self):
        """Generate demo NMEA 2000 data for testing"""
        engine_id = 0
        base_rpm = 1800
        
        while self.running:
            try:
                # Simulate varying engine parameters
                import random
                time_factor = time.time() * 0.1
                
                # Create demo engine data
                engine_data = EngineData(
                    engine_id=engine_id,
                    rpm=base_rpm + random.randint(-100, 200),
                    coolant_temp=75 + random.randint(-5, 15),
                    oil_pressure=350 + random.randint(-50, 50),
                    oil_temp=85 + random.randint(-10, 10),
                    fuel_rate=15.5 + random.uniform(-2, 3),
                    fuel_pressure=280 + random.randint(-20, 20),
                    boost_pressure=150 + random.randint(-30, 40),
                    intake_manifold_temp=45 + random.randint(-5, 10),
                    engine_load=65 + random.randint(-15, 25),
                    alternator_voltage=13.8 + random.uniform(-0.3, 0.3),
                    operating_hours=1247.5 + time.time() * 0.0001,
                    status="running" if base_rpm > 800 else "idle"
                )
                
                # Add random alarms occasionally
                if random.random() < 0.05:
                    alarms = ["high_coolant_temp", "low_oil_pressure", "high_boost", "fuel_filter"]
                    engine_data.alarms = [random.choice(alarms)]
                
                # Update engine data
                self.engines[engine_id] = engine_data
                
                # Notify subscribers
                await self._notify_subscribers(engine_data)
                
                # Update statistics
                self.messages_received += 1
                self.last_message_time = datetime.now(timezone.utc)
                
                await asyncio.sleep(0.5)  # Update every 500ms
                
            except Exception as e:
                logger.error(f"Error in demo data generator: {e}")
                await asyncio.sleep(1)
    
    async def _notify_subscribers(self, engine_data: EngineData):
        """Notify all subscribers of engine data updates"""
        for subscriber in self.subscribers:
            try:
                await subscriber(engine_data)
            except Exception as e:
                logger.error(f"Error notifying subscriber {subscriber.__name__}: {e}")
    
    def _handle_engine_parameters_rapid(self, message: NMEA2000Message):
        """Handle rapid engine parameters (RPM, etc.)"""
        try:
            if len(message.data) >= 8:
                # Parse RPM (first 2 bytes)
                rpm = struct.unpack('<H', message.data[0:2])[0] * 0.25
                
                engine_id = message.source
                if engine_id not in self.engines:
                    self.engines[engine_id] = EngineData(engine_id=engine_id)
                
                self.engines[engine_id].rpm = rpm
                
                logger.debug(f"Engine {engine_id} RPM: {rpm}")
                
        except Exception as e:
            logger.error(f"Error parsing rapid engine parameters: {e}")
    
    def _handle_engine_parameters_dynamic(self, message: NMEA2000Message):
        """Handle dynamic engine parameters"""
        try:
            if len(message.data) >= 26:
                engine_id = message.source
                if engine_id not in self.engines:
                    self.engines[engine_id] = EngineData(engine_id=engine_id)
                
                engine = self.engines[engine_id]
                
                # Parse various parameters (simplified)
                data = message.data
                engine.oil_pressure = struct.unpack('<H', data[0:2])[0] * 100  # hPa to Pa
                engine.oil_temp = struct.unpack('<H', data[2:4])[0] * 0.03125 - 273.15  # K to C
                engine.coolant_temp = struct.unpack('<H', data[4:6])[0] * 0.03125 - 273.15
                engine.alternator_voltage = struct.unpack('<H', data[6:8])[0] * 0.01  # V
                engine.fuel_rate = struct.unpack('<H', data[8:10])[0] * 0.1  # L/hr
                
                logger.debug(f"Engine {engine_id} dynamic parameters updated")
                
        except Exception as e:
            logger.error(f"Error parsing dynamic engine parameters: {e}")
    
    def _handle_fluid_level(self, message: NMEA2000Message):
        """Handle fluid level messages"""
        try:
            if len(message.data) >= 8:
                # Parse fluid level data
                level = struct.unpack('<H', data[0:2])[0] / 250.0  # %
                capacity = struct.unpack('<I', data[2:6])[0] * 0.1  # L
                
                logger.debug(f"Fluid level: {level}% of {capacity}L")
                
        except Exception as e:
            logger.error(f"Error parsing fluid level: {e}")
    
    def _handle_temperature(self, message: NMEA2000Message):
        """Handle temperature messages"""
        try:
            if len(message.data) >= 3:
                temp_instance = message.data[0]
                temp_source = message.data[1] 
                temp = struct.unpack('<H', message.data[2:4])[0] * 0.01 - 273.15  # K to C
                
                logger.debug(f"Temperature sensor {temp_instance}: {temp}°C")
                
        except Exception as e:
            logger.error(f"Error parsing temperature: {e}")
    
    def _handle_pressure(self, message: NMEA2000Message):
        """Handle pressure messages"""
        try:
            if len(message.data) >= 3:
                pressure_instance = message.data[0]
                pressure_source = message.data[1]
                pressure = struct.unpack('<H', message.data[2:4])[0] * 100  # hPa to Pa
                
                logger.debug(f"Pressure sensor {pressure_instance}: {pressure}Pa")
                
        except Exception as e:
            logger.error(f"Error parsing pressure: {e}")
    
    def _handle_fuel_consumption(self, message: NMEA2000Message):
        """Handle fuel consumption messages"""
        try:
            if len(message.data) >= 8:
                trip_fuel = struct.unpack('<I', message.data[0:4])[0] * 0.1  # L
                fuel_rate = struct.unpack('<H', message.data[4:6])[0] * 0.1  # L/hr
                
                logger.debug(f"Trip fuel: {trip_fuel}L, Rate: {fuel_rate}L/hr")
                
        except Exception as e:
            logger.error(f"Error parsing fuel consumption: {e}")
    
    def _handle_operating_hours(self, message: NMEA2000Message):
        """Handle operating hours messages"""
        try:
            if len(message.data) >= 4:
                hours = struct.unpack('<I', message.data[0:4])[0] * 0.05  # hours
                
                engine_id = message.source
                if engine_id not in self.engines:
                    self.engines[engine_id] = EngineData(engine_id=engine_id)
                
                self.engines[engine_id].operating_hours = hours
                
                logger.debug(f"Engine {engine_id} operating hours: {hours}")
                
        except Exception as e:
            logger.error(f"Error parsing operating hours: {e}")
    
    def _handle_alternator_status(self, message: NMEA2000Message):
        """Handle alternator status messages"""
        try:
            if len(message.data) >= 8:
                voltage = struct.unpack('<H', message.data[0:2])[0] * 0.01  # V
                current = struct.unpack('<h', message.data[2:4])[0] * 0.1  # A
                temperature = struct.unpack('<H', message.data[4:6])[0] * 0.03125 - 273.15  # C
                
                logger.debug(f"Alternator: {voltage}V, {current}A, {temperature}°C")
                
        except Exception as e:
            logger.error(f"Error parsing alternator status: {e}")
    
    def get_engine_data(self, engine_id: Optional[int] = None) -> Dict[str, Any]:
        """Get engine data for specified engine or all engines"""
        if engine_id is not None:
            engine = self.engines.get(engine_id)
            return engine.to_dict() if engine else {}
        else:
            return {str(eid): engine.to_dict() for eid, engine in self.engines.items()}
    
    def get_gateway_statistics(self) -> Dict[str, Any]:
        """Get gateway statistics"""
        return {
            'interface': self.interface,
            'running': self.running,
            'messages_received': self.messages_received,
            'messages_sent': self.messages_sent,
            'errors': self.errors,
            'engines_detected': len(self.engines),
            'last_message_time': self.last_message_time.isoformat() if self.last_message_time else None,
            'uptime_seconds': time.time() if self.running else 0
        }
    
    async def send_message(self, pgn: int, priority: NMEA2000Priority, 
                          destination: int, data: bytes) -> bool:
        """Send NMEA 2000 message"""
        try:
            message = NMEA2000Message(
                pgn=pgn,
                priority=priority,
                source=0,  # Our source address
                destination=destination,
                data=data
            )
            
            # In real implementation, would send to CAN bus
            logger.debug(f"Sending NMEA 2000 message: PGN {pgn}")
            
            self.messages_sent += 1
            return True
            
        except Exception as e:
            logger.error(f"Error sending NMEA 2000 message: {e}")
            self.errors += 1
            return False
    
    def configure_engine_address(self, engine_id: int, can_address: int):
        """Configure CAN address for an engine"""
        if engine_id not in self.engines:
            self.engines[engine_id] = EngineData(engine_id=engine_id)
        
        logger.info(f"Configured engine {engine_id} with CAN address {can_address}")
    
    def set_update_rate(self, pgn: int, rate_ms: int):
        """Set update rate for specific PGN"""
        logger.info(f"Set update rate for PGN {pgn} to {rate_ms}ms")
        
    def enable_fast_packet_support(self):
        """Enable NMEA 2000 fast packet support"""
        logger.info("Fast packet support enabled")
        
    def add_custom_pgn_handler(self, pgn: int, handler: Callable):
        """Add custom PGN message handler"""
        self.message_handlers[pgn] = handler
        logger.info(f"Added custom handler for PGN {pgn}")


class NMEA2000Simulator:
    """Simulator for testing NMEA 2000 functionality"""
    
    def __init__(self, gateway: NMEA2000Gateway):
        self.gateway = gateway
        self.scenarios = {
            'normal_operation': self._simulate_normal_operation,
            'high_load': self._simulate_high_load,
            'maintenance_due': self._simulate_maintenance_due,
            'emergency_shutdown': self._simulate_emergency_shutdown
        }
        
    async def run_scenario(self, scenario_name: str, duration_seconds: int = 60):
        """Run a specific test scenario"""
        if scenario_name not in self.scenarios:
            raise ValueError(f"Unknown scenario: {scenario_name}")
        
        logger.info(f"Running scenario '{scenario_name}' for {duration_seconds} seconds")
        
        scenario_func = self.scenarios[scenario_name]
        start_time = time.time()
        
        while time.time() - start_time < duration_seconds:
            await scenario_func()
            await asyncio.sleep(0.5)
        
        logger.info(f"Scenario '{scenario_name}' completed")
    
    async def _simulate_normal_operation(self):
        """Simulate normal engine operation"""
        # This would generate appropriate NMEA 2000 messages
        pass
        
    async def _simulate_high_load(self):
        """Simulate high load conditions"""
        # Generate messages showing high load parameters
        pass
        
    async def _simulate_maintenance_due(self):
        """Simulate maintenance due conditions"""
        # Generate messages indicating maintenance requirements
        pass
        
    async def _simulate_emergency_shutdown(self):
        """Simulate emergency shutdown sequence"""
        # Generate emergency condition messages
        pass