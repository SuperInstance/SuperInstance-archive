"""
Medical Device Integration APIs
Secure integration framework for medical devices and IoT sensors.
"""
import asyncio
import datetime
import json
import logging
import uuid
from typing import Dict, List, Optional, Any, Union, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import threading
import time
from abc import ABC, abstractmethod


class DeviceType(Enum):
    """Types of medical devices"""
    VITAL_SIGNS_MONITOR = "vital_signs_monitor"
    ECG_MONITOR = "ecg_monitor"
    BLOOD_PRESSURE_MONITOR = "blood_pressure_monitor"
    PULSE_OXIMETER = "pulse_oximeter"
    GLUCOSE_METER = "glucose_meter"
    THERMOMETER = "thermometer"
    WEIGHT_SCALE = "weight_scale"
    VENTILATOR = "ventilator"
    INFUSION_PUMP = "infusion_pump"
    DEFIBRILLATOR = "defibrillator"
    IMAGING_DEVICE = "imaging_device"
    PATIENT_MONITOR = "patient_monitor"
    IOT_SENSOR = "iot_sensor"


class DeviceStatus(Enum):
    """Device connection status"""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    MAINTENANCE = "maintenance"
    CALIBRATING = "calibrating"


class DataType(Enum):
    """Types of medical data"""
    HEART_RATE = "heart_rate"
    BLOOD_PRESSURE = "blood_pressure"
    TEMPERATURE = "temperature"
    OXYGEN_SATURATION = "oxygen_saturation"
    GLUCOSE_LEVEL = "glucose_level"
    WEIGHT = "weight"
    ECG_WAVEFORM = "ecg_waveform"
    RESPIRATORY_RATE = "respiratory_rate"
    MEDICATION_DELIVERY = "medication_delivery"
    ALARM = "alarm"
    STATUS_UPDATE = "status_update"


class AlarmSeverity(Enum):
    """Medical alarm severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class DeviceReading:
    """Medical device reading"""
    device_id: str
    timestamp: datetime.datetime
    data_type: DataType
    value: Union[float, str, Dict[str, Any]]
    unit: Optional[str] = None
    patient_id: Optional[str] = None
    quality_indicator: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class DeviceAlarm:
    """Medical device alarm"""
    device_id: str
    alarm_id: str
    timestamp: datetime.datetime
    severity: AlarmSeverity
    message: str
    alarm_code: Optional[str] = None
    patient_id: Optional[str] = None
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime.datetime] = None


@dataclass
class DeviceInfo:
    """Medical device information"""
    device_id: str
    device_type: DeviceType
    manufacturer: str
    model: str
    serial_number: str
    firmware_version: str
    location: Optional[str] = None
    patient_id: Optional[str] = None
    last_calibration: Optional[datetime.datetime] = None
    next_maintenance: Optional[datetime.datetime] = None
    capabilities: Optional[List[str]] = None


class DeviceProtocol(ABC):
    """Abstract base class for device communication protocols"""
    
    @abstractmethod
    async def connect(self, device_info: DeviceInfo) -> bool:
        """Connect to device"""
        pass
    
    @abstractmethod
    async def disconnect(self, device_id: str) -> bool:
        """Disconnect from device"""
        pass
    
    @abstractmethod
    async def send_command(self, device_id: str, command: Dict[str, Any]) -> Dict[str, Any]:
        """Send command to device"""
        pass
    
    @abstractmethod
    async def read_data(self, device_id: str) -> List[DeviceReading]:
        """Read data from device"""
        pass


class HL7DeviceProtocol(DeviceProtocol):
    """HL7 protocol implementation for medical devices"""
    
    def __init__(self):
        self.connections = {}
    
    async def connect(self, device_info: DeviceInfo) -> bool:
        """Connect to HL7-enabled device"""
        try:
            # Simulate HL7 connection
            self.connections[device_info.device_id] = {
                'status': 'connected',
                'last_heartbeat': datetime.datetime.utcnow(),
                'device_info': device_info
            }
            
            logging.info(f"HL7 connection established with device {device_info.device_id}")
            return True
            
        except Exception as e:
            logging.error(f"Failed to connect to HL7 device {device_info.device_id}: {e}")
            return False
    
    async def disconnect(self, device_id: str) -> bool:
        """Disconnect from HL7 device"""
        if device_id in self.connections:
            del self.connections[device_id]
            logging.info(f"HL7 device {device_id} disconnected")
            return True
        return False
    
    async def send_command(self, device_id: str, command: Dict[str, Any]) -> Dict[str, Any]:
        """Send HL7 command to device"""
        if device_id not in self.connections:
            return {'status': 'error', 'message': 'Device not connected'}
        
        # Simulate HL7 command processing
        hl7_message = self._build_hl7_command(command)
        
        # Simulate device response
        return {
            'status': 'success',
            'response': f"ACK|{command.get('command', 'UNKNOWN')}",
            'timestamp': datetime.datetime.utcnow().isoformat()
        }
    
    async def read_data(self, device_id: str) -> List[DeviceReading]:
        """Read data from HL7 device"""
        if device_id not in self.connections:
            return []
        
        # Simulate reading HL7 messages
        device_info = self.connections[device_id]['device_info']
        readings = []
        
        # Generate sample readings based on device type
        if device_info.device_type == DeviceType.VITAL_SIGNS_MONITOR:
            readings.extend([
                DeviceReading(
                    device_id=device_id,
                    timestamp=datetime.datetime.utcnow(),
                    data_type=DataType.HEART_RATE,
                    value=72.0,
                    unit="bpm",
                    patient_id=device_info.patient_id
                ),
                DeviceReading(
                    device_id=device_id,
                    timestamp=datetime.datetime.utcnow(),
                    data_type=DataType.BLOOD_PRESSURE,
                    value={"systolic": 120, "diastolic": 80},
                    unit="mmHg",
                    patient_id=device_info.patient_id
                )
            ])
        
        return readings
    
    def _build_hl7_command(self, command: Dict[str, Any]) -> str:
        """Build HL7 message for command"""
        # Simplified HL7 message construction
        msh = "MSH|^~\\&|SYSTEM|FACILITY|DEVICE|LOCATION|"
        msh += datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")
        msh += f"||{command.get('message_type', 'CMD')}|{uuid.uuid4()}|P|2.5"
        
        return msh


class MQTTDeviceProtocol(DeviceProtocol):
    """MQTT protocol implementation for IoT medical devices"""
    
    def __init__(self, broker_host: str = "localhost", broker_port: int = 1883):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.connected_devices = {}
        self.client = None
    
    async def connect(self, device_info: DeviceInfo) -> bool:
        """Connect to MQTT-enabled device"""
        try:
            # Simulate MQTT connection
            topic = f"medical_devices/{device_info.device_id}"
            
            self.connected_devices[device_info.device_id] = {
                'topic': topic,
                'device_info': device_info,
                'last_message': datetime.datetime.utcnow()
            }
            
            logging.info(f"MQTT device {device_info.device_id} connected on topic {topic}")
            return True
            
        except Exception as e:
            logging.error(f"Failed to connect MQTT device {device_info.device_id}: {e}")
            return False
    
    async def disconnect(self, device_id: str) -> bool:
        """Disconnect from MQTT device"""
        if device_id in self.connected_devices:
            del self.connected_devices[device_id]
            logging.info(f"MQTT device {device_id} disconnected")
            return True
        return False
    
    async def send_command(self, device_id: str, command: Dict[str, Any]) -> Dict[str, Any]:
        """Send command via MQTT"""
        if device_id not in self.connected_devices:
            return {'status': 'error', 'message': 'Device not connected'}
        
        topic = self.connected_devices[device_id]['topic'] + "/commands"
        
        # Simulate MQTT publish
        logging.info(f"Sending MQTT command to {topic}: {command}")
        
        return {
            'status': 'success',
            'message': 'Command sent via MQTT',
            'topic': topic
        }
    
    async def read_data(self, device_id: str) -> List[DeviceReading]:
        """Read data from MQTT device"""
        if device_id not in self.connected_devices:
            return []
        
        # Simulate MQTT data reception
        device_info = self.connected_devices[device_id]['device_info']
        
        # Generate sample IoT sensor readings
        if device_info.device_type == DeviceType.IOT_SENSOR:
            return [
                DeviceReading(
                    device_id=device_id,
                    timestamp=datetime.datetime.utcnow(),
                    data_type=DataType.TEMPERATURE,
                    value=36.5,
                    unit="°C",
                    patient_id=device_info.patient_id
                )
            ]
        
        return []


class DeviceManager:
    """Central manager for medical device integration"""
    
    def __init__(self):
        self.devices: Dict[str, DeviceInfo] = {}
        self.protocols: Dict[str, DeviceProtocol] = {
            'hl7': HL7DeviceProtocol(),
            'mqtt': MQTTDeviceProtocol()
        }
        self.device_status: Dict[str, DeviceStatus] = {}
        self.data_callbacks: List[Callable[[DeviceReading], None]] = []
        self.alarm_callbacks: List[Callable[[DeviceAlarm], None]] = []
        self.active_readings = {}
        self.active_alarms = {}
        self.running = False
        self.monitoring_thread = None
    
    def register_device(self, device_info: DeviceInfo, protocol_name: str) -> bool:
        """Register a new medical device"""
        try:
            if protocol_name not in self.protocols:
                logging.error(f"Unknown protocol: {protocol_name}")
                return False
            
            self.devices[device_info.device_id] = device_info
            self.device_status[device_info.device_id] = DeviceStatus.DISCONNECTED
            
            logging.info(f"Device registered: {device_info.device_id} ({device_info.device_type.value})")
            return True
            
        except Exception as e:
            logging.error(f"Failed to register device {device_info.device_id}: {e}")
            return False
    
    async def connect_device(self, device_id: str, protocol_name: str) -> bool:
        """Connect to a registered device"""
        if device_id not in self.devices:
            logging.error(f"Device {device_id} not registered")
            return False
        
        if protocol_name not in self.protocols:
            logging.error(f"Protocol {protocol_name} not available")
            return False
        
        device_info = self.devices[device_id]
        protocol = self.protocols[protocol_name]
        
        success = await protocol.connect(device_info)
        
        if success:
            self.device_status[device_id] = DeviceStatus.CONNECTED
            logging.info(f"Device {device_id} connected successfully")
        else:
            self.device_status[device_id] = DeviceStatus.ERROR
            logging.error(f"Failed to connect device {device_id}")
        
        return success
    
    async def disconnect_device(self, device_id: str, protocol_name: str) -> bool:
        """Disconnect from a device"""
        if protocol_name not in self.protocols:
            return False
        
        protocol = self.protocols[protocol_name]
        success = await protocol.disconnect(device_id)
        
        if success:
            self.device_status[device_id] = DeviceStatus.DISCONNECTED
        
        return success
    
    async def send_device_command(self, device_id: str, protocol_name: str, 
                                command: Dict[str, Any]) -> Dict[str, Any]:
        """Send command to device"""
        if device_id not in self.devices:
            return {'status': 'error', 'message': 'Device not registered'}
        
        if self.device_status.get(device_id) != DeviceStatus.CONNECTED:
            return {'status': 'error', 'message': 'Device not connected'}
        
        if protocol_name not in self.protocols:
            return {'status': 'error', 'message': 'Protocol not available'}
        
        protocol = self.protocols[protocol_name]
        return await protocol.send_command(device_id, command)
    
    def add_data_callback(self, callback: Callable[[DeviceReading], None]):
        """Add callback for device data"""
        self.data_callbacks.append(callback)
    
    def add_alarm_callback(self, callback: Callable[[DeviceAlarm], None]):
        """Add callback for device alarms"""
        self.alarm_callbacks.append(callback)
    
    def start_monitoring(self):
        """Start device monitoring"""
        if self.running:
            return
        
        self.running = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        logging.info("Device monitoring started")
    
    def stop_monitoring(self):
        """Stop device monitoring"""
        self.running = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        logging.info("Device monitoring stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            while self.running:
                loop.run_until_complete(self._check_devices())
                time.sleep(1)  # Check every second
        except Exception as e:
            logging.error(f"Monitoring loop error: {e}")
        finally:
            loop.close()
    
    async def _check_devices(self):
        """Check all connected devices for data and alarms"""
        tasks = []
        
        for device_id, status in self.device_status.items():
            if status == DeviceStatus.CONNECTED:
                # Check each protocol that might have this device
                for protocol_name, protocol in self.protocols.items():
                    task = self._check_device_data(device_id, protocol)
                    tasks.append(task)
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _check_device_data(self, device_id: str, protocol: DeviceProtocol):
        """Check single device for new data"""
        try:
            readings = await protocol.read_data(device_id)
            
            for reading in readings:
                # Store reading
                if device_id not in self.active_readings:
                    self.active_readings[device_id] = []
                self.active_readings[device_id].append(reading)
                
                # Trigger callbacks
                for callback in self.data_callbacks:
                    try:
                        callback(reading)
                    except Exception as e:
                        logging.error(f"Data callback error: {e}")
                
                # Check for alarm conditions
                alarm = self._check_for_alarms(reading)
                if alarm:
                    self._handle_alarm(alarm)
        
        except Exception as e:
            logging.error(f"Error checking device {device_id}: {e}")
            self.device_status[device_id] = DeviceStatus.ERROR
    
    def _check_for_alarms(self, reading: DeviceReading) -> Optional[DeviceAlarm]:
        """Check if reading triggers any alarms"""
        # Simple alarm logic - in practice this would be more sophisticated
        if reading.data_type == DataType.HEART_RATE and isinstance(reading.value, (int, float)):
            if reading.value > 100 or reading.value < 60:
                return DeviceAlarm(
                    device_id=reading.device_id,
                    alarm_id=str(uuid.uuid4()),
                    timestamp=reading.timestamp,
                    severity=AlarmSeverity.MEDIUM,
                    message=f"Heart rate {reading.value} {reading.unit} is outside normal range",
                    alarm_code="HR_ABNORMAL",
                    patient_id=reading.patient_id
                )
        
        elif reading.data_type == DataType.OXYGEN_SATURATION and isinstance(reading.value, (int, float)):
            if reading.value < 90:
                return DeviceAlarm(
                    device_id=reading.device_id,
                    alarm_id=str(uuid.uuid4()),
                    timestamp=reading.timestamp,
                    severity=AlarmSeverity.HIGH,
                    message=f"Oxygen saturation {reading.value}% is critically low",
                    alarm_code="SPO2_CRITICAL",
                    patient_id=reading.patient_id
                )
        
        return None
    
    def _handle_alarm(self, alarm: DeviceAlarm):
        """Handle device alarm"""
        # Store alarm
        if alarm.device_id not in self.active_alarms:
            self.active_alarms[alarm.device_id] = []
        self.active_alarms[alarm.device_id].append(alarm)
        
        # Trigger callbacks
        for callback in self.alarm_callbacks:
            try:
                callback(alarm)
            except Exception as e:
                logging.error(f"Alarm callback error: {e}")
        
        logging.warning(f"DEVICE ALARM [{alarm.severity.value.upper()}]: {alarm.message}")
    
    def acknowledge_alarm(self, device_id: str, alarm_id: str, 
                         acknowledged_by: str) -> bool:
        """Acknowledge a device alarm"""
        if device_id not in self.active_alarms:
            return False
        
        for alarm in self.active_alarms[device_id]:
            if alarm.alarm_id == alarm_id and not alarm.acknowledged:
                alarm.acknowledged = True
                alarm.acknowledged_by = acknowledged_by
                alarm.acknowledged_at = datetime.datetime.utcnow()
                
                logging.info(f"Alarm {alarm_id} acknowledged by {acknowledged_by}")
                return True
        
        return False
    
    def get_device_status(self, device_id: str) -> Optional[DeviceStatus]:
        """Get current status of a device"""
        return self.device_status.get(device_id)
    
    def get_device_readings(self, device_id: str, 
                          since: Optional[datetime.datetime] = None) -> List[DeviceReading]:
        """Get readings from a device"""
        if device_id not in self.active_readings:
            return []
        
        readings = self.active_readings[device_id]
        
        if since:
            readings = [r for r in readings if r.timestamp >= since]
        
        return readings
    
    def get_device_alarms(self, device_id: str, 
                         acknowledged: Optional[bool] = None) -> List[DeviceAlarm]:
        """Get alarms from a device"""
        if device_id not in self.active_alarms:
            return []
        
        alarms = self.active_alarms[device_id]
        
        if acknowledged is not None:
            alarms = [a for a in alarms if a.acknowledged == acknowledged]
        
        return alarms
    
    def get_all_devices(self) -> List[Dict[str, Any]]:
        """Get information about all registered devices"""
        devices = []
        
        for device_id, device_info in self.devices.items():
            devices.append({
                'device_id': device_id,
                'device_info': asdict(device_info),
                'status': self.device_status.get(device_id, DeviceStatus.DISCONNECTED).value,
                'recent_readings_count': len(self.active_readings.get(device_id, [])),
                'active_alarms_count': len([a for a in self.active_alarms.get(device_id, []) 
                                          if not a.acknowledged])
            })
        
        return devices


class DeviceDataProcessor:
    """Process and validate medical device data"""
    
    def __init__(self):
        self.validation_rules = {
            DataType.HEART_RATE: {'min': 30, 'max': 200, 'unit': 'bpm'},
            DataType.BLOOD_PRESSURE: {'systolic_max': 250, 'diastolic_max': 150},
            DataType.TEMPERATURE: {'min': 32.0, 'max': 42.0, 'unit': '°C'},
            DataType.OXYGEN_SATURATION: {'min': 70, 'max': 100, 'unit': '%'},
            DataType.GLUCOSE_LEVEL: {'min': 50, 'max': 500, 'unit': 'mg/dL'}
        }
    
    def validate_reading(self, reading: DeviceReading) -> List[str]:
        """Validate device reading against rules"""
        errors = []
        
        if reading.data_type in self.validation_rules:
            rules = self.validation_rules[reading.data_type]
            
            if isinstance(reading.value, (int, float)):
                if 'min' in rules and reading.value < rules['min']:
                    errors.append(f"Value {reading.value} below minimum {rules['min']}")
                if 'max' in rules and reading.value > rules['max']:
                    errors.append(f"Value {reading.value} above maximum {rules['max']}")
                    
            elif isinstance(reading.value, dict) and reading.data_type == DataType.BLOOD_PRESSURE:
                systolic = reading.value.get('systolic', 0)
                diastolic = reading.value.get('diastolic', 0)
                
                if systolic > rules.get('systolic_max', 300):
                    errors.append(f"Systolic pressure {systolic} too high")
                if diastolic > rules.get('diastolic_max', 200):
                    errors.append(f"Diastolic pressure {diastolic} too high")
        
        return errors
    
    def normalize_reading(self, reading: DeviceReading) -> DeviceReading:
        """Normalize reading data"""
        normalized = reading
        
        # Convert units if needed
        if reading.data_type == DataType.TEMPERATURE:
            if reading.unit == 'F':
                # Convert Fahrenheit to Celsius
                normalized.value = (reading.value - 32) * 5/9
                normalized.unit = '°C'
        
        # Add quality indicators
        if not reading.quality_indicator:
            errors = self.validate_reading(reading)
            if not errors:
                normalized.quality_indicator = 'good'
            elif len(errors) == 1:
                normalized.quality_indicator = 'questionable'
            else:
                normalized.quality_indicator = 'poor'
        
        return normalized
    
    def aggregate_readings(self, readings: List[DeviceReading], 
                         window_minutes: int = 5) -> Dict[str, Any]:
        """Aggregate readings over time window"""
        if not readings:
            return {}
        
        # Group by data type
        by_type = {}
        for reading in readings:
            data_type = reading.data_type
            if data_type not in by_type:
                by_type[data_type] = []
            by_type[data_type].append(reading)
        
        aggregated = {}
        
        for data_type, type_readings in by_type.items():
            if all(isinstance(r.value, (int, float)) for r in type_readings):
                values = [r.value for r in type_readings]
                
                aggregated[data_type.value] = {
                    'count': len(values),
                    'min': min(values),
                    'max': max(values),
                    'avg': sum(values) / len(values),
                    'latest': values[-1],
                    'unit': type_readings[-1].unit,
                    'window_start': min(r.timestamp for r in type_readings),
                    'window_end': max(r.timestamp for r in type_readings)
                }
        
        return aggregated