"""
Custom Sensor Support System
Extensible sensor integration for marine engine monitoring
"""

import asyncio
import logging
import json
import struct
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
import numpy as np

logger = logging.getLogger(__name__)


class SensorType(Enum):
    """Supported sensor types"""
    TEMPERATURE = "temperature"
    PRESSURE = "pressure"
    FLOW_RATE = "flow_rate"
    LEVEL = "level"
    VOLTAGE = "voltage"
    CURRENT = "current"
    RPM = "rpm"
    VIBRATION = "vibration"
    STRAIN = "strain"
    PH = "ph"
    DISSOLVED_OXYGEN = "dissolved_oxygen"
    TURBIDITY = "turbidity"
    CONDUCTIVITY = "conductivity"
    GPS = "gps"
    GYROSCOPE = "gyroscope"
    ACCELEROMETER = "accelerometer"
    CUSTOM = "custom"


class SensorInterface(Enum):
    """Sensor interface types"""
    ANALOG_4_20MA = "analog_4_20ma"
    ANALOG_0_5V = "analog_0_5v"
    ANALOG_0_10V = "analog_0_10v"
    MODBUS_RTU = "modbus_rtu"
    MODBUS_TCP = "modbus_tcp"
    NMEA_0183 = "nmea_0183"
    NMEA_2000 = "nmea_2000"
    CAN_BUS = "can_bus"
    I2C = "i2c"
    SPI = "spi"
    UART = "uart"
    ETHERNET = "ethernet"
    WIRELESS = "wireless"
    ONEWIRE = "onewire"


class SensorStatus(Enum):
    """Sensor operational status"""
    ONLINE = "online"
    OFFLINE = "offline"
    ERROR = "error"
    MAINTENANCE = "maintenance"
    CALIBRATING = "calibrating"
    UNKNOWN = "unknown"


@dataclass
class SensorReading:
    """Individual sensor reading"""
    sensor_id: str
    value: float
    unit: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    quality: float = 1.0  # 0-1 quality indicator
    status: SensorStatus = SensorStatus.ONLINE
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'sensor_id': self.sensor_id,
            'value': self.value,
            'unit': self.unit,
            'timestamp': self.timestamp.isoformat(),
            'quality': self.quality,
            'status': self.status.value,
            'metadata': self.metadata
        }


@dataclass
class SensorCalibration:
    """Sensor calibration parameters"""
    sensor_id: str
    calibration_type: str  # linear, polynomial, lookup_table
    
    # Linear calibration: y = mx + b
    slope: float = 1.0
    offset: float = 0.0
    
    # Polynomial calibration coefficients
    polynomial_coeffs: List[float] = field(default_factory=list)
    
    # Lookup table calibration
    lookup_points: List[tuple] = field(default_factory=list)  # (input, output) pairs
    
    # Calibration metadata
    calibration_date: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    calibrated_by: str = ""
    reference_standards: List[str] = field(default_factory=list)
    
    def apply_calibration(self, raw_value: float) -> float:
        """Apply calibration to raw sensor value"""
        try:
            if self.calibration_type == "linear":
                return raw_value * self.slope + self.offset
            
            elif self.calibration_type == "polynomial":
                result = 0.0
                for i, coeff in enumerate(self.polynomial_coeffs):
                    result += coeff * (raw_value ** i)
                return result
            
            elif self.calibration_type == "lookup_table":
                if not self.lookup_points:
                    return raw_value
                
                # Linear interpolation between lookup points
                sorted_points = sorted(self.lookup_points, key=lambda x: x[0])
                
                if raw_value <= sorted_points[0][0]:
                    return sorted_points[0][1]
                
                if raw_value >= sorted_points[-1][0]:
                    return sorted_points[-1][1]
                
                # Find interpolation points
                for i in range(len(sorted_points) - 1):
                    x1, y1 = sorted_points[i]
                    x2, y2 = sorted_points[i + 1]
                    
                    if x1 <= raw_value <= x2:
                        # Linear interpolation
                        ratio = (raw_value - x1) / (x2 - x1)
                        return y1 + ratio * (y2 - y1)
                
                return raw_value
            
            else:
                return raw_value
                
        except Exception as e:
            logger.error(f"Error applying calibration: {e}")
            return raw_value


@dataclass
class SensorConfiguration:
    """Complete sensor configuration"""
    sensor_id: str
    name: str
    sensor_type: SensorType
    interface: SensorInterface
    
    # Interface-specific parameters
    interface_params: Dict[str, Any] = field(default_factory=dict)
    
    # Measurement parameters
    unit: str = ""
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    precision: int = 2
    sampling_rate_hz: float = 1.0
    
    # Calibration
    calibration: Optional[SensorCalibration] = None
    
    # Alarm thresholds
    low_alarm: Optional[float] = None
    high_alarm: Optional[float] = None
    low_warning: Optional[float] = None
    high_warning: Optional[float] = None
    
    # Metadata
    location: str = ""
    description: str = ""
    manufacturer: str = ""
    model: str = ""
    serial_number: str = ""
    installation_date: Optional[datetime] = None
    
    # Processing options
    enable_filtering: bool = True
    filter_window_size: int = 5
    enable_outlier_detection: bool = True
    outlier_threshold: float = 3.0  # Standard deviations
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'sensor_id': self.sensor_id,
            'name': self.name,
            'sensor_type': self.sensor_type.value,
            'interface': self.interface.value,
            'interface_params': self.interface_params,
            'unit': self.unit,
            'min_value': self.min_value,
            'max_value': self.max_value,
            'precision': self.precision,
            'sampling_rate_hz': self.sampling_rate_hz,
            'low_alarm': self.low_alarm,
            'high_alarm': self.high_alarm,
            'low_warning': self.low_warning,
            'high_warning': self.high_warning,
            'location': self.location,
            'description': self.description,
            'manufacturer': self.manufacturer,
            'model': self.model,
            'serial_number': self.serial_number,
            'installation_date': self.installation_date.isoformat() if self.installation_date else None
        }


class BaseSensorDriver(ABC):
    """Abstract base class for sensor drivers"""
    
    def __init__(self, config: SensorConfiguration):
        self.config = config
        self.is_connected = False
        self.last_reading = None
        self.error_count = 0
        
    @abstractmethod
    async def connect(self) -> bool:
        """Connect to sensor"""
        pass
        
    @abstractmethod
    async def disconnect(self):
        """Disconnect from sensor"""
        pass
        
    @abstractmethod
    async def read_raw_value(self) -> Optional[float]:
        """Read raw value from sensor"""
        pass
        
    async def read_sensor(self) -> Optional[SensorReading]:
        """Read calibrated sensor value"""
        try:
            raw_value = await self.read_raw_value()
            if raw_value is None:
                return None
            
            # Apply calibration if configured
            if self.config.calibration:
                calibrated_value = self.config.calibration.apply_calibration(raw_value)
            else:
                calibrated_value = raw_value
            
            # Apply precision
            calibrated_value = round(calibrated_value, self.config.precision)
            
            # Create sensor reading
            reading = SensorReading(
                sensor_id=self.config.sensor_id,
                value=calibrated_value,
                unit=self.config.unit,
                metadata={'raw_value': raw_value}
            )
            
            self.last_reading = reading
            return reading
            
        except Exception as e:
            logger.error(f"Error reading sensor {self.config.sensor_id}: {e}")
            self.error_count += 1
            return None


class AnalogSensorDriver(BaseSensorDriver):
    """Driver for analog sensors (4-20mA, 0-5V, etc.)"""
    
    async def connect(self) -> bool:
        """Connect to analog sensor interface"""
        try:
            # Initialize ADC or analog input interface
            logger.info(f"Connecting to analog sensor {self.config.sensor_id}")
            self.is_connected = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to analog sensor: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from analog sensor"""
        self.is_connected = False
        
    async def read_raw_value(self) -> Optional[float]:
        """Read raw analog value"""
        try:
            if not self.is_connected:
                return None
            
            # Simulate analog reading based on interface type
            if self.config.interface == SensorInterface.ANALOG_4_20MA:
                # 4-20mA current loop (4mA = min, 20mA = max)
                import random
                current_ma = 4 + random.uniform(0, 16)  # 4-20mA range
                
                # Convert current to percentage of range
                percentage = (current_ma - 4) / 16
                
                # Scale to sensor range
                if self.config.min_value is not None and self.config.max_value is not None:
                    value_range = self.config.max_value - self.config.min_value
                    raw_value = self.config.min_value + (percentage * value_range)
                else:
                    raw_value = percentage * 100
                
                return raw_value
                
            elif self.config.interface == SensorInterface.ANALOG_0_5V:
                # 0-5V voltage input
                import random
                voltage = random.uniform(0, 5)
                percentage = voltage / 5
                
                if self.config.min_value is not None and self.config.max_value is not None:
                    value_range = self.config.max_value - self.config.min_value
                    raw_value = self.config.min_value + (percentage * value_range)
                else:
                    raw_value = percentage * 100
                
                return raw_value
                
            else:
                # Generic analog input
                import random
                return random.uniform(0, 100)
                
        except Exception as e:
            logger.error(f"Error reading analog sensor: {e}")
            return None


class ModbusSensorDriver(BaseSensorDriver):
    """Driver for Modbus sensors"""
    
    async def connect(self) -> bool:
        """Connect to Modbus sensor"""
        try:
            # Initialize Modbus client
            logger.info(f"Connecting to Modbus sensor {self.config.sensor_id}")
            self.is_connected = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Modbus sensor: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from Modbus sensor"""
        self.is_connected = False
        
    async def read_raw_value(self) -> Optional[float]:
        """Read value via Modbus"""
        try:
            if not self.is_connected:
                return None
            
            # Simulate Modbus reading
            import random
            
            # Get Modbus parameters from interface_params
            slave_id = self.config.interface_params.get('slave_id', 1)
            register_address = self.config.interface_params.get('register_address', 0)
            register_count = self.config.interface_params.get('register_count', 1)
            data_type = self.config.interface_params.get('data_type', 'float32')
            
            # Simulate register read
            raw_registers = [random.randint(0, 65535) for _ in range(register_count)]
            
            # Convert based on data type
            if data_type == 'float32' and len(raw_registers) >= 2:
                # Convert two 16-bit registers to float32
                combined = (raw_registers[0] << 16) | raw_registers[1]
                raw_value = struct.unpack('>f', struct.pack('>I', combined))[0]
            elif data_type == 'int16':
                raw_value = float(raw_registers[0])
            else:
                raw_value = float(raw_registers[0])
            
            return raw_value
            
        except Exception as e:
            logger.error(f"Error reading Modbus sensor: {e}")
            return None


class NMEASensorDriver(BaseSensorDriver):
    """Driver for NMEA sensors"""
    
    async def connect(self) -> bool:
        """Connect to NMEA sensor"""
        try:
            logger.info(f"Connecting to NMEA sensor {self.config.sensor_id}")
            self.is_connected = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to NMEA sensor: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from NMEA sensor"""
        self.is_connected = False
        
    async def read_raw_value(self) -> Optional[float]:
        """Read value from NMEA sentence"""
        try:
            if not self.is_connected:
                return None
            
            # Simulate NMEA sentence parsing
            sentence_type = self.config.interface_params.get('sentence_type', 'MTW')
            field_index = self.config.interface_params.get('field_index', 1)
            
            import random
            
            if sentence_type == 'MTW':  # Mean Temperature of Water
                return random.uniform(15, 25)
            elif sentence_type == 'VPW':  # Speed - Measured Parallel to Wind
                return random.uniform(0, 30)
            elif sentence_type == 'DPT':  # Depth
                return random.uniform(1, 50)
            else:
                return random.uniform(0, 100)
                
        except Exception as e:
            logger.error(f"Error reading NMEA sensor: {e}")
            return None


class CustomSensorManager:
    """Main manager for custom sensors"""
    
    def __init__(self):
        self.sensors: Dict[str, SensorConfiguration] = {}
        self.drivers: Dict[str, BaseSensorDriver] = {}
        self.readings: Dict[str, List[SensorReading]] = {}
        self.subscribers: List[Callable] = []
        
        # Background tasks
        self.monitoring_tasks: Dict[str, asyncio.Task] = {}
        self.is_running = False
        
        # Processing
        self.reading_buffers: Dict[str, List[float]] = {}
        
        # Statistics
        self.total_readings = 0
        self.sensor_errors = {}
        
        logger.info("CustomSensorManager initialized")
    
    def add_sensor(self, config: SensorConfiguration) -> bool:
        """Add a new sensor"""
        try:
            self.sensors[config.sensor_id] = config
            self.readings[config.sensor_id] = []
            self.reading_buffers[config.sensor_id] = []
            self.sensor_errors[config.sensor_id] = 0
            
            # Create appropriate driver
            driver = self._create_driver(config)
            if driver:
                self.drivers[config.sensor_id] = driver
                logger.info(f"Added sensor {config.sensor_id} ({config.sensor_type.value})")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to add sensor {config.sensor_id}: {e}")
            return False
    
    def _create_driver(self, config: SensorConfiguration) -> Optional[BaseSensorDriver]:
        """Create appropriate driver for sensor"""
        try:
            if config.interface in [SensorInterface.ANALOG_4_20MA, SensorInterface.ANALOG_0_5V, SensorInterface.ANALOG_0_10V]:
                return AnalogSensorDriver(config)
            
            elif config.interface in [SensorInterface.MODBUS_RTU, SensorInterface.MODBUS_TCP]:
                return ModbusSensorDriver(config)
            
            elif config.interface in [SensorInterface.NMEA_0183, SensorInterface.NMEA_2000]:
                return NMEASensorDriver(config)
            
            else:
                # Default to analog driver for unknown interfaces
                return AnalogSensorDriver(config)
                
        except Exception as e:
            logger.error(f"Failed to create driver for sensor {config.sensor_id}: {e}")
            return None
    
    async def start_monitoring(self):
        """Start monitoring all sensors"""
        try:
            self.is_running = True
            
            # Connect all sensors
            for sensor_id, driver in self.drivers.items():
                success = await driver.connect()
                if not success:
                    logger.error(f"Failed to connect to sensor {sensor_id}")
            
            # Start monitoring tasks
            for sensor_id in self.sensors.keys():
                task = asyncio.create_task(self._monitor_sensor(sensor_id))
                self.monitoring_tasks[sensor_id] = task
            
            logger.info("Started custom sensor monitoring")
            
        except Exception as e:
            logger.error(f"Failed to start sensor monitoring: {e}")
            raise
    
    async def stop_monitoring(self):
        """Stop monitoring all sensors"""
        try:
            self.is_running = False
            
            # Cancel monitoring tasks
            for task in self.monitoring_tasks.values():
                task.cancel()
            
            # Wait for tasks to complete
            await asyncio.gather(*self.monitoring_tasks.values(), return_exceptions=True)
            self.monitoring_tasks.clear()
            
            # Disconnect sensors
            for driver in self.drivers.values():
                await driver.disconnect()
            
            logger.info("Stopped custom sensor monitoring")
            
        except Exception as e:
            logger.error(f"Error stopping sensor monitoring: {e}")
    
    async def _monitor_sensor(self, sensor_id: str):
        """Monitor individual sensor"""
        config = self.sensors[sensor_id]
        driver = self.drivers[sensor_id]
        
        interval = 1.0 / config.sampling_rate_hz
        
        while self.is_running:
            try:
                reading = await driver.read_sensor()
                
                if reading:
                    # Apply filtering if enabled
                    if config.enable_filtering:
                        reading.value = self._apply_filtering(sensor_id, reading.value, config)
                    
                    # Check for outliers
                    if config.enable_outlier_detection:
                        if self._is_outlier(sensor_id, reading.value, config):
                            reading.quality *= 0.5  # Reduce quality for outliers
                    
                    # Store reading
                    self._store_reading(reading)
                    
                    # Check alarms
                    self._check_alarms(reading, config)
                    
                    # Notify subscribers
                    await self._notify_subscribers(reading)
                    
                    self.total_readings += 1
                else:
                    self.sensor_errors[sensor_id] += 1
                
                await asyncio.sleep(interval)
                
            except Exception as e:
                logger.error(f"Error monitoring sensor {sensor_id}: {e}")
                self.sensor_errors[sensor_id] += 1
                await asyncio.sleep(1)
    
    def _apply_filtering(self, sensor_id: str, value: float, config: SensorConfiguration) -> float:
        """Apply filtering to sensor value"""
        try:
            buffer = self.reading_buffers[sensor_id]
            buffer.append(value)
            
            # Keep buffer size limited
            if len(buffer) > config.filter_window_size:
                buffer.pop(0)
            
            # Apply moving average filter
            return sum(buffer) / len(buffer)
            
        except Exception as e:
            logger.error(f"Error applying filter to sensor {sensor_id}: {e}")
            return value
    
    def _is_outlier(self, sensor_id: str, value: float, config: SensorConfiguration) -> bool:
        """Check if value is an outlier"""
        try:
            buffer = self.reading_buffers[sensor_id]
            
            if len(buffer) < 3:
                return False
            
            # Calculate mean and standard deviation
            mean = np.mean(buffer)
            std = np.std(buffer)
            
            if std == 0:
                return False
            
            # Check if value is beyond threshold standard deviations
            z_score = abs(value - mean) / std
            return z_score > config.outlier_threshold
            
        except Exception as e:
            logger.error(f"Error checking outlier for sensor {sensor_id}: {e}")
            return False
    
    def _store_reading(self, reading: SensorReading):
        """Store sensor reading"""
        readings = self.readings[reading.sensor_id]
        readings.append(reading)
        
        # Limit history size
        if len(readings) > 1000:
            readings.pop(0)
    
    def _check_alarms(self, reading: SensorReading, config: SensorConfiguration):
        """Check alarm conditions"""
        try:
            value = reading.value
            alarms = []
            
            if config.high_alarm is not None and value > config.high_alarm:
                alarms.append(f"HIGH_ALARM:{value}")
            
            if config.low_alarm is not None and value < config.low_alarm:
                alarms.append(f"LOW_ALARM:{value}")
            
            if config.high_warning is not None and value > config.high_warning:
                alarms.append(f"HIGH_WARNING:{value}")
            
            if config.low_warning is not None and value < config.low_warning:
                alarms.append(f"LOW_WARNING:{value}")
            
            if alarms:
                reading.metadata['alarms'] = alarms
                logger.warning(f"Sensor {reading.sensor_id} alarms: {alarms}")
            
        except Exception as e:
            logger.error(f"Error checking alarms for sensor {reading.sensor_id}: {e}")
    
    async def _notify_subscribers(self, reading: SensorReading):
        """Notify subscribers of new reading"""
        for subscriber in self.subscribers:
            try:
                await subscriber(reading)
            except Exception as e:
                logger.error(f"Error notifying subscriber: {e}")
    
    def get_sensor_reading(self, sensor_id: str) -> Optional[SensorReading]:
        """Get latest reading from sensor"""
        readings = self.readings.get(sensor_id, [])
        return readings[-1] if readings else None
    
    def get_sensor_history(self, sensor_id: str, limit: int = 100) -> List[SensorReading]:
        """Get sensor reading history"""
        readings = self.readings.get(sensor_id, [])
        return readings[-limit:]
    
    def get_all_sensors(self) -> Dict[str, SensorConfiguration]:
        """Get all sensor configurations"""
        return self.sensors.copy()
    
    def get_sensor_statistics(self, sensor_id: str) -> Dict[str, Any]:
        """Get statistics for sensor"""
        try:
            readings = self.readings.get(sensor_id, [])
            driver = self.drivers.get(sensor_id)
            
            if not readings:
                return {}
            
            values = [r.value for r in readings[-100:]]  # Last 100 readings
            
            return {
                'sensor_id': sensor_id,
                'total_readings': len(readings),
                'is_connected': driver.is_connected if driver else False,
                'error_count': self.sensor_errors.get(sensor_id, 0),
                'min_value': min(values) if values else None,
                'max_value': max(values) if values else None,
                'avg_value': sum(values) / len(values) if values else None,
                'last_reading': readings[-1].to_dict() if readings else None
            }
            
        except Exception as e:
            logger.error(f"Error getting statistics for sensor {sensor_id}: {e}")
            return {}
    
    def subscribe_to_readings(self, callback: Callable):
        """Subscribe to sensor reading updates"""
        self.subscribers.append(callback)
        logger.info("Added sensor reading subscriber")
    
    def calibrate_sensor(self, sensor_id: str, calibration: SensorCalibration) -> bool:
        """Update sensor calibration"""
        try:
            if sensor_id in self.sensors:
                self.sensors[sensor_id].calibration = calibration
                
                # Update driver calibration
                if sensor_id in self.drivers:
                    self.drivers[sensor_id].config.calibration = calibration
                
                logger.info(f"Updated calibration for sensor {sensor_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error calibrating sensor {sensor_id}: {e}")
            return False
    
    def set_alarm_thresholds(self, sensor_id: str, low_alarm: Optional[float] = None,
                           high_alarm: Optional[float] = None, low_warning: Optional[float] = None,
                           high_warning: Optional[float] = None) -> bool:
        """Update sensor alarm thresholds"""
        try:
            if sensor_id in self.sensors:
                config = self.sensors[sensor_id]
                config.low_alarm = low_alarm
                config.high_alarm = high_alarm
                config.low_warning = low_warning
                config.high_warning = high_warning
                
                logger.info(f"Updated alarm thresholds for sensor {sensor_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error setting alarm thresholds for sensor {sensor_id}: {e}")
            return False