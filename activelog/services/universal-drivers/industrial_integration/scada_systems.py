import asyncio
import time
import random
import json
import threading
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta
import numpy as np
import struct

class SCADAProtocol(Enum):
    MODBUS_TCP = "modbus_tcp"
    MODBUS_RTU = "modbus_rtu"
    DNP3 = "dnp3"
    IEC_61850 = "iec_61850"
    IEC_104 = "iec_104"
    OPC_UA = "opc_ua"
    ETHERNET_IP = "ethernet_ip"
    PROFINET = "profinet"
    BACNET = "bacnet"

class DataType(Enum):
    BOOLEAN = "boolean"
    INT16 = "int16"
    INT32 = "int32"
    FLOAT32 = "float32"
    FLOAT64 = "float64"
    STRING = "string"
    TIMESTAMP = "timestamp"

class AlarmSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class DeviceStatus(Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    ERROR = "error"
    MAINTENANCE = "maintenance"
    UNKNOWN = "unknown"

@dataclass
class SCADATag:
    tag_name: str
    device_id: str
    address: str
    data_type: DataType
    value: Any
    quality: str
    timestamp: datetime
    unit: str = ""
    description: str = ""
    
@dataclass
class AlarmCondition:
    tag_name: str
    condition_type: str  # high, low, deviation, etc.
    setpoint: float
    severity: AlarmSeverity
    message: str
    enabled: bool = True

@dataclass
class Alarm:
    alarm_id: str
    tag_name: str
    severity: AlarmSeverity
    message: str
    timestamp: datetime
    acknowledged: bool = False
    active: bool = True

class SCADADevice:
    def __init__(self, device_id: str, protocol: SCADAProtocol, address: str):
        self.device_id = device_id
        self.protocol = protocol
        self.address = address
        self.status = DeviceStatus.OFFLINE
        self.tags = {}
        self.last_communication = None
        self.error_count = 0
        self.response_time = 0.0
        
    def add_tag(self, tag: SCADATag):
        """Add a tag to this device"""
        self.tags[tag.tag_name] = tag
    
    def get_tag(self, tag_name: str) -> Optional[SCADATag]:
        """Get tag by name"""
        return self.tags.get(tag_name)
    
    def update_tag_value(self, tag_name: str, value: Any, quality: str = "GOOD"):
        """Update tag value"""
        if tag_name in self.tags:
            tag = self.tags[tag_name]
            tag.value = value
            tag.quality = quality
            tag.timestamp = datetime.now()
    
    async def read_tags(self) -> Dict[str, Any]:
        """Read all tags from device"""
        try:
            # Simulate communication delay
            await asyncio.sleep(random.uniform(0.01, 0.1))
            
            # Simulate occasional communication errors
            if random.random() < 0.05:  # 5% error rate
                self.error_count += 1
                self.status = DeviceStatus.ERROR
                raise Exception(f"Communication error with device {self.device_id}")
            
            self.status = DeviceStatus.ONLINE
            self.last_communication = datetime.now()
            self.response_time = random.uniform(0.01, 0.1)
            
            # Simulate reading values
            for tag in self.tags.values():
                tag.value = self._simulate_value(tag)
                tag.quality = "GOOD" if random.random() > 0.02 else "UNCERTAIN"
                tag.timestamp = datetime.now()
            
            return {tag_name: tag.value for tag_name, tag in self.tags.items()}
            
        except Exception as e:
            self.status = DeviceStatus.ERROR
            raise e
    
    async def write_tag(self, tag_name: str, value: Any) -> bool:
        """Write value to device tag"""
        try:
            await asyncio.sleep(random.uniform(0.01, 0.05))
            
            if random.random() < 0.03:  # 3% write error rate
                raise Exception(f"Write error to {tag_name}")
            
            if tag_name in self.tags:
                self.tags[tag_name].value = value
                self.tags[tag_name].timestamp = datetime.now()
                return True
            
            return False
            
        except Exception as e:
            print(f"Write error: {e}")
            return False
    
    def _simulate_value(self, tag: SCADATag) -> Any:
        """Simulate tag value based on type"""
        if tag.data_type == DataType.BOOLEAN:
            return random.choice([True, False])
        elif tag.data_type == DataType.INT16:
            return random.randint(-32768, 32767)
        elif tag.data_type == DataType.INT32:
            return random.randint(-2147483648, 2147483647)
        elif tag.data_type == DataType.FLOAT32:
            # Simulate realistic process values
            if "temperature" in tag.tag_name.lower():
                return round(random.uniform(20.0, 80.0), 2)
            elif "pressure" in tag.tag_name.lower():
                return round(random.uniform(0.8, 2.5), 3)
            elif "flow" in tag.tag_name.lower():
                return round(random.uniform(0.0, 100.0), 2)
            else:
                return round(random.uniform(0.0, 100.0), 2)
        elif tag.data_type == DataType.FLOAT64:
            return random.uniform(0.0, 1000.0)
        elif tag.data_type == DataType.STRING:
            return random.choice(["OK", "RUNNING", "STOPPED", "ALARM", "MAINTENANCE"])
        elif tag.data_type == DataType.TIMESTAMP:
            return datetime.now()
        else:
            return 0

class SCADASystem:
    def __init__(self, system_name: str):
        self.system_name = system_name
        self.devices = {}
        self.alarms = {}
        self.alarm_conditions = {}
        self.historical_data = []
        self.is_running = False
        self.scan_rate = 1.0  # seconds
        
        # Event callbacks
        self.callbacks = {
            'tag_update': [],
            'alarm': [],
            'device_status': [],
            'system_event': []
        }
        
        # Statistics
        self.stats = {
            'total_scans': 0,
            'successful_scans': 0,
            'communication_errors': 0,
            'active_alarms': 0,
            'start_time': None
        }
    
    def add_device(self, device: SCADADevice):
        """Add device to SCADA system"""
        self.devices[device.device_id] = device
        print(f"Added device {device.device_id} ({device.protocol.value})")
    
    def add_alarm_condition(self, condition: AlarmCondition):
        """Add alarm condition"""
        key = f"{condition.tag_name}_{condition.condition_type}"
        self.alarm_conditions[key] = condition
        print(f"Added alarm condition: {condition.tag_name} {condition.condition_type} {condition.setpoint}")
    
    def register_callback(self, event_type: str, callback: Callable):
        """Register event callback"""
        if event_type in self.callbacks:
            self.callbacks[event_type].append(callback)
    
    async def start_system(self):
        """Start SCADA system operation"""
        if self.is_running:
            return
        
        self.is_running = True
        self.stats['start_time'] = datetime.now()
        
        print(f"Starting SCADA system: {self.system_name}")
        
        # Start scan loop
        asyncio.create_task(self._scan_loop())
        
        # Start alarm processing
        asyncio.create_task(self._alarm_processor())
        
        # Start data historian
        asyncio.create_task(self._data_historian())
        
        self._trigger_system_event("system_started", {"system": self.system_name})
    
    async def stop_system(self):
        """Stop SCADA system"""
        self.is_running = False
        print(f"SCADA system {self.system_name} stopped")
        self._trigger_system_event("system_stopped", {"system": self.system_name})
    
    async def _scan_loop(self):
        """Main scanning loop"""
        while self.is_running:
            start_time = time.time()
            
            try:
                await self._scan_all_devices()
                self.stats['successful_scans'] += 1
                
            except Exception as e:
                self.stats['communication_errors'] += 1
                print(f"Scan error: {e}")
            
            self.stats['total_scans'] += 1
            
            # Wait for next scan
            elapsed = time.time() - start_time
            sleep_time = max(0, self.scan_rate - elapsed)
            await asyncio.sleep(sleep_time)
    
    async def _scan_all_devices(self):
        """Scan all devices"""
        scan_tasks = []
        
        for device in self.devices.values():
            task = asyncio.create_task(self._scan_device(device))
            scan_tasks.append(task)
        
        # Wait for all scans to complete
        await asyncio.gather(*scan_tasks, return_exceptions=True)
    
    async def _scan_device(self, device: SCADADevice):
        """Scan single device"""
        try:
            old_status = device.status
            tag_values = await device.read_tags()
            
            # Check for status change
            if old_status != device.status:
                self._trigger_device_status_change(device)
            
            # Process tag updates
            for tag_name, value in tag_values.items():
                tag = device.get_tag(tag_name)
                if tag:
                    self._trigger_tag_update(tag)
                    await self._check_alarms(tag)
            
        except Exception as e:
            device.status = DeviceStatus.ERROR
            print(f"Device scan error {device.device_id}: {e}")
    
    def _trigger_tag_update(self, tag: SCADATag):
        """Trigger tag update callbacks"""
        for callback in self.callbacks['tag_update']:
            try:
                callback(tag)
            except Exception as e:
                print(f"Tag update callback error: {e}")
    
    def _trigger_device_status_change(self, device: SCADADevice):
        """Trigger device status change callbacks"""
        for callback in self.callbacks['device_status']:
            try:
                callback(device)
            except Exception as e:
                print(f"Device status callback error: {e}")
        
        print(f"Device {device.device_id} status changed to {device.status.value}")
    
    def _trigger_system_event(self, event_type: str, data: Dict[str, Any]):
        """Trigger system event callbacks"""
        for callback in self.callbacks['system_event']:
            try:
                callback(event_type, data)
            except Exception as e:
                print(f"System event callback error: {e}")
    
    async def _check_alarms(self, tag: SCADATag):
        """Check alarm conditions for tag"""
        for condition_key, condition in self.alarm_conditions.items():
            if condition.tag_name != tag.tag_name or not condition.enabled:
                continue
            
            if tag.data_type not in [DataType.INT16, DataType.INT32, DataType.FLOAT32, DataType.FLOAT64]:
                continue
            
            alarm_triggered = False
            
            try:
                value = float(tag.value)
                
                if condition.condition_type == "high" and value > condition.setpoint:
                    alarm_triggered = True
                elif condition.condition_type == "low" and value < condition.setpoint:
                    alarm_triggered = True
                elif condition.condition_type == "deviation":
                    if abs(value - condition.setpoint) > condition.setpoint * 0.1:  # 10% deviation
                        alarm_triggered = True
                
                if alarm_triggered:
                    await self._create_alarm(condition, tag)
                    
            except (ValueError, TypeError):
                pass  # Skip non-numeric values
    
    async def _create_alarm(self, condition: AlarmCondition, tag: SCADATag):
        """Create new alarm"""
        alarm_id = f"{condition.tag_name}_{condition.condition_type}_{int(time.time())}"
        
        # Check if similar alarm already exists
        for alarm in self.alarms.values():
            if (alarm.tag_name == tag.tag_name and 
                alarm.active and 
                not alarm.acknowledged):
                return  # Don't create duplicate alarms
        
        alarm = Alarm(
            alarm_id=alarm_id,
            tag_name=tag.tag_name,
            severity=condition.severity,
            message=condition.message.format(
                tag_name=tag.tag_name,
                value=tag.value,
                setpoint=condition.setpoint
            ),
            timestamp=datetime.now()
        )
        
        self.alarms[alarm_id] = alarm
        self.stats['active_alarms'] += 1
        
        print(f"🚨 ALARM: {alarm.message}")
        
        # Trigger alarm callbacks
        for callback in self.callbacks['alarm']:
            try:
                callback(alarm)
            except Exception as e:
                print(f"Alarm callback error: {e}")
    
    async def _alarm_processor(self):
        """Process alarms"""
        while self.is_running:
            # Auto-acknowledge low priority alarms after 5 minutes
            current_time = datetime.now()
            for alarm in self.alarms.values():
                if (not alarm.acknowledged and 
                    alarm.severity == AlarmSeverity.LOW and
                    (current_time - alarm.timestamp).total_seconds() > 300):
                    alarm.acknowledged = True
                    alarm.active = False
                    self.stats['active_alarms'] = max(0, self.stats['active_alarms'] - 1)
                    print(f"Auto-acknowledged alarm: {alarm.alarm_id}")
            
            await asyncio.sleep(60)  # Check every minute
    
    async def _data_historian(self):
        """Store historical data"""
        while self.is_running:
            timestamp = datetime.now()
            
            # Collect current values from all devices
            historical_record = {
                'timestamp': timestamp,
                'devices': {}
            }
            
            for device_id, device in self.devices.items():
                device_data = {
                    'status': device.status.value,
                    'response_time': device.response_time,
                    'tags': {}
                }
                
                for tag_name, tag in device.tags.items():
                    device_data['tags'][tag_name] = {
                        'value': tag.value,
                        'quality': tag.quality
                    }
                
                historical_record['devices'][device_id] = device_data
            
            self.historical_data.append(historical_record)
            
            # Keep only last 1000 records
            if len(self.historical_data) > 1000:
                self.historical_data.pop(0)
            
            await asyncio.sleep(300)  # Store every 5 minutes
    
    def acknowledge_alarm(self, alarm_id: str) -> bool:
        """Acknowledge alarm"""
        if alarm_id in self.alarms:
            alarm = self.alarms[alarm_id]
            alarm.acknowledged = True
            alarm.active = False
            self.stats['active_alarms'] = max(0, self.stats['active_alarms'] - 1)
            print(f"Alarm acknowledged: {alarm_id}")
            return True
        return False
    
    def get_active_alarms(self) -> List[Alarm]:
        """Get list of active alarms"""
        return [alarm for alarm in self.alarms.values() if alarm.active]
    
    def get_device_status(self, device_id: str) -> Dict[str, Any]:
        """Get device status"""
        if device_id in self.devices:
            device = self.devices[device_id]
            return {
                'device_id': device_id,
                'status': device.status.value,
                'protocol': device.protocol.value,
                'address': device.address,
                'last_communication': device.last_communication.isoformat() if device.last_communication else None,
                'response_time': device.response_time,
                'error_count': device.error_count,
                'tag_count': len(device.tags)
            }
        return {}
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status"""
        online_devices = sum(1 for d in self.devices.values() if d.status == DeviceStatus.ONLINE)
        total_devices = len(self.devices)
        total_tags = sum(len(d.tags) for d in self.devices.values())
        
        uptime = (datetime.now() - self.stats['start_time']).total_seconds() if self.stats['start_time'] else 0
        
        return {
            'system_name': self.system_name,
            'running': self.is_running,
            'uptime_seconds': uptime,
            'devices': {
                'total': total_devices,
                'online': online_devices,
                'offline': total_devices - online_devices
            },
            'tags': {
                'total': total_tags
            },
            'alarms': {
                'active': self.stats['active_alarms'],
                'total': len(self.alarms)
            },
            'performance': {
                'scan_rate': self.scan_rate,
                'total_scans': self.stats['total_scans'],
                'successful_scans': self.stats['successful_scans'],
                'success_rate': (self.stats['successful_scans'] / max(1, self.stats['total_scans'])) * 100,
                'communication_errors': self.stats['communication_errors']
            }
        }
    
    def get_tag_value(self, device_id: str, tag_name: str) -> Optional[Any]:
        """Get current tag value"""
        device = self.devices.get(device_id)
        if device:
            tag = device.get_tag(tag_name)
            if tag:
                return tag.value
        return None
    
    async def write_tag_value(self, device_id: str, tag_name: str, value: Any) -> bool:
        """Write value to tag"""
        device = self.devices.get(device_id)
        if device:
            success = await device.write_tag(tag_name, value)
            if success:
                print(f"Written {value} to {device_id}.{tag_name}")
            return success
        return False
    
    def export_historical_data(self, filename: str, hours: int = 24):
        """Export historical data to file"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        filtered_data = [
            record for record in self.historical_data
            if record['timestamp'] >= cutoff_time
        ]
        
        with open(filename, 'w') as f:
            json.dump(filtered_data, f, indent=2, default=str)
        
        print(f"Exported {len(filtered_data)} historical records to {filename}")

def create_demo_power_plant():
    """Create demonstration power plant SCADA system"""
    scada = SCADASystem("Demo Power Plant")
    
    # Generator device
    generator = SCADADevice("GEN_001", SCADAProtocol.MODBUS_TCP, "192.168.1.10")
    generator.add_tag(SCADATag("MW_OUTPUT", "GEN_001", "40001", DataType.FLOAT32, 0.0, "GOOD", datetime.now(), "MW", "Generator Power Output"))
    generator.add_tag(SCADATag("VOLTAGE", "GEN_001", "40002", DataType.FLOAT32, 0.0, "GOOD", datetime.now(), "kV", "Generator Voltage"))
    generator.add_tag(SCADATag("FREQUENCY", "GEN_001", "40003", DataType.FLOAT32, 0.0, "GOOD", datetime.now(), "Hz", "Generator Frequency"))
    generator.add_tag(SCADATag("TEMPERATURE", "GEN_001", "40004", DataType.FLOAT32, 0.0, "GOOD", datetime.now(), "°C", "Generator Temperature"))
    generator.add_tag(SCADATag("STATUS", "GEN_001", "40005", DataType.STRING, "STOPPED", "GOOD", datetime.now(), "", "Generator Status"))
    
    # Transformer device
    transformer = SCADADevice("XFMR_001", SCADAProtocol.DNP3, "192.168.1.11")
    transformer.add_tag(SCADATag("PRIMARY_VOLTAGE", "XFMR_001", "30001", DataType.FLOAT32, 0.0, "GOOD", datetime.now(), "kV", "Primary Voltage"))
    transformer.add_tag(SCADATag("SECONDARY_VOLTAGE", "XFMR_001", "30002", DataType.FLOAT32, 0.0, "GOOD", datetime.now(), "kV", "Secondary Voltage"))
    transformer.add_tag(SCADATag("OIL_TEMPERATURE", "XFMR_001", "30003", DataType.FLOAT32, 0.0, "GOOD", datetime.now(), "°C", "Oil Temperature"))
    transformer.add_tag(SCADATag("LOAD_CURRENT", "XFMR_001", "30004", DataType.FLOAT32, 0.0, "GOOD", datetime.now(), "A", "Load Current"))
    
    # Circuit breaker device
    breaker = SCADADevice("CB_001", SCADAProtocol.IEC_104, "192.168.1.12")
    breaker.add_tag(SCADATag("POSITION", "CB_001", "20001", DataType.BOOLEAN, False, "GOOD", datetime.now(), "", "Breaker Position (Open/Closed)"))
    breaker.add_tag(SCADATag("CURRENT_A", "CB_001", "20002", DataType.FLOAT32, 0.0, "GOOD", datetime.now(), "A", "Phase A Current"))
    breaker.add_tag(SCADATag("CURRENT_B", "CB_001", "20003", DataType.FLOAT32, 0.0, "GOOD", datetime.now(), "A", "Phase B Current"))
    breaker.add_tag(SCADATag("CURRENT_C", "CB_001", "20004", DataType.FLOAT32, 0.0, "GOOD", datetime.now(), "A", "Phase C Current"))
    
    # Add devices to SCADA system
    scada.add_device(generator)
    scada.add_device(transformer)
    scada.add_device(breaker)
    
    # Add alarm conditions
    scada.add_alarm_condition(AlarmCondition(
        tag_name="TEMPERATURE",
        condition_type="high",
        setpoint=85.0,
        severity=AlarmSeverity.HIGH,
        message="Generator temperature high: {value}°C (limit: {setpoint}°C)"
    ))
    
    scada.add_alarm_condition(AlarmCondition(
        tag_name="OIL_TEMPERATURE",
        condition_type="high",
        setpoint=75.0,
        severity=AlarmSeverity.MEDIUM,
        message="Transformer oil temperature high: {value}°C (limit: {setpoint}°C)"
    ))
    
    scada.add_alarm_condition(AlarmCondition(
        tag_name="FREQUENCY",
        condition_type="deviation",
        setpoint=50.0,
        severity=AlarmSeverity.CRITICAL,
        message="Frequency deviation detected: {value}Hz (nominal: {setpoint}Hz)"
    ))
    
    return scada

if __name__ == "__main__":
    print("SCADA System Simulation")
    print("=" * 50)
    
    async def demo():
        # Create demo power plant
        scada = create_demo_power_plant()
        
        # Register event callbacks
        def on_alarm(alarm):
            print(f"🚨 NEW ALARM: {alarm.severity.value.upper()} - {alarm.message}")
        
        def on_device_status(device):
            print(f"📡 Device {device.device_id} status: {device.status.value}")
        
        def on_system_event(event_type, data):
            print(f"⚙️  System event: {event_type}")
        
        scada.register_callback('alarm', on_alarm)
        scada.register_callback('device_status', on_device_status)
        scada.register_callback('system_event', on_system_event)
        
        # Start SCADA system
        await scada.start_system()
        
        print(f"\nSCADA system started with {len(scada.devices)} devices")
        
        try:
            # Run for demonstration period
            for i in range(20):  # 20 seconds
                await asyncio.sleep(1)
                
                # Print status every 5 seconds
                if i % 5 == 0:
                    status = scada.get_system_status()
                    print(f"\n--- System Status (t={i}s) ---")
                    print(f"Devices online: {status['devices']['online']}/{status['devices']['total']}")
                    print(f"Active alarms: {status['alarms']['active']}")
                    print(f"Success rate: {status['performance']['success_rate']:.1f}%")
                    
                    # Show some tag values
                    gen_power = scada.get_tag_value("GEN_001", "MW_OUTPUT")
                    gen_temp = scada.get_tag_value("GEN_001", "TEMPERATURE")
                    if gen_power is not None and gen_temp is not None:
                        print(f"Generator: {gen_power:.1f} MW, {gen_temp:.1f}°C")
                
                # Demonstrate writing a tag
                if i == 10:
                    print("\nDemonstrating tag write operation...")
                    await scada.write_tag_value("CB_001", "POSITION", True)
            
            # Show final statistics
            print("\n--- Final System Status ---")
            status = scada.get_system_status()
            print(json.dumps(status, indent=2, default=str))
            
            # Show active alarms
            active_alarms = scada.get_active_alarms()
            if active_alarms:
                print(f"\n--- Active Alarms ({len(active_alarms)}) ---")
                for alarm in active_alarms:
                    print(f"  {alarm.severity.value}: {alarm.message}")
        
        finally:
            await scada.stop_system()
        
        print("SCADA system demonstration completed")
    
    asyncio.run(demo())