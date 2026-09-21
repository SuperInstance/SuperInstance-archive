"""
Tests for Medical Device Integration APIs
"""
import unittest
import asyncio
import datetime
from unittest.mock import Mock, patch, AsyncMock
from ..src.device_integration import (
    DeviceManager, DeviceInfo, DeviceReading, DeviceAlarm,
    DeviceType, DeviceStatus, DataType, AlarmSeverity,
    HL7DeviceProtocol, MQTTDeviceProtocol, DeviceDataProcessor
)


class TestHL7DeviceProtocol(unittest.TestCase):
    
    def setUp(self):
        self.protocol = HL7DeviceProtocol()
        self.device_info = DeviceInfo(
            device_id="hl7_monitor_001",
            device_type=DeviceType.VITAL_SIGNS_MONITOR,
            manufacturer="MedTech Inc",
            model="VM-2000",
            serial_number="SN123456",
            firmware_version="1.2.3"
        )
    
    def test_connect_device(self):
        """Test HL7 device connection"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                self.protocol.connect(self.device_info)
            )
            
            self.assertTrue(result)
            self.assertIn(self.device_info.device_id, self.protocol.connections)
        finally:
            loop.close()
    
    def test_disconnect_device(self):
        """Test HL7 device disconnection"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Connect first
            loop.run_until_complete(self.protocol.connect(self.device_info))
            
            # Then disconnect
            result = loop.run_until_complete(
                self.protocol.disconnect(self.device_info.device_id)
            )
            
            self.assertTrue(result)
            self.assertNotIn(self.device_info.device_id, self.protocol.connections)
        finally:
            loop.close()
    
    def test_send_command(self):
        """Test sending HL7 command"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Connect device first
            loop.run_until_complete(self.protocol.connect(self.device_info))
            
            # Send command
            command = {'command': 'START_MONITORING', 'parameters': {}}
            result = loop.run_until_complete(
                self.protocol.send_command(self.device_info.device_id, command)
            )
            
            self.assertEqual(result['status'], 'success')
            self.assertIn('ACK', result['response'])
        finally:
            loop.close()
    
    def test_read_data(self):
        """Test reading HL7 device data"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Connect device first
            loop.run_until_complete(self.protocol.connect(self.device_info))
            
            # Read data
            readings = loop.run_until_complete(
                self.protocol.read_data(self.device_info.device_id)
            )
            
            self.assertIsInstance(readings, list)
            if readings:
                self.assertIsInstance(readings[0], DeviceReading)
                self.assertEqual(readings[0].device_id, self.device_info.device_id)
        finally:
            loop.close()


class TestMQTTDeviceProtocol(unittest.TestCase):
    
    def setUp(self):
        self.protocol = MQTTDeviceProtocol()
        self.device_info = DeviceInfo(
            device_id="mqtt_sensor_001",
            device_type=DeviceType.IOT_SENSOR,
            manufacturer="IoT Medical",
            model="Temp-Sensor-Pro",
            serial_number="TS789012",
            firmware_version="2.1.0"
        )
    
    def test_connect_device(self):
        """Test MQTT device connection"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                self.protocol.connect(self.device_info)
            )
            
            self.assertTrue(result)
            self.assertIn(self.device_info.device_id, self.protocol.connected_devices)
        finally:
            loop.close()
    
    def test_send_command(self):
        """Test sending MQTT command"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Connect device first
            loop.run_until_complete(self.protocol.connect(self.device_info))
            
            # Send command
            command = {'command': 'SET_INTERVAL', 'interval': 30}
            result = loop.run_until_complete(
                self.protocol.send_command(self.device_info.device_id, command)
            )
            
            self.assertEqual(result['status'], 'success')
            self.assertIn('topic', result)
        finally:
            loop.close()


class TestDeviceManager(unittest.TestCase):
    
    def setUp(self):
        self.device_manager = DeviceManager()
        self.device_info = DeviceInfo(
            device_id="test_device_001",
            device_type=DeviceType.VITAL_SIGNS_MONITOR,
            manufacturer="Test Corp",
            model="TestMonitor",
            serial_number="TEST123",
            firmware_version="1.0.0"
        )
    
    def test_register_device(self):
        """Test device registration"""
        result = self.device_manager.register_device(self.device_info, 'hl7')
        
        self.assertTrue(result)
        self.assertIn(self.device_info.device_id, self.device_manager.devices)
        self.assertEqual(
            self.device_manager.device_status[self.device_info.device_id],
            DeviceStatus.DISCONNECTED
        )
    
    def test_register_device_unknown_protocol(self):
        """Test registering device with unknown protocol"""
        result = self.device_manager.register_device(self.device_info, 'unknown')
        
        self.assertFalse(result)
        self.assertNotIn(self.device_info.device_id, self.device_manager.devices)
    
    def test_connect_device(self):
        """Test device connection"""
        # Register device first
        self.device_manager.register_device(self.device_info, 'hl7')
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                self.device_manager.connect_device(self.device_info.device_id, 'hl7')
            )
            
            self.assertTrue(result)
            self.assertEqual(
                self.device_manager.device_status[self.device_info.device_id],
                DeviceStatus.CONNECTED
            )
        finally:
            loop.close()
    
    def test_connect_unregistered_device(self):
        """Test connecting unregistered device"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                self.device_manager.connect_device("nonexistent", 'hl7')
            )
            
            self.assertFalse(result)
        finally:
            loop.close()
    
    def test_send_device_command(self):
        """Test sending command to device"""
        # Register and connect device
        self.device_manager.register_device(self.device_info, 'hl7')
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Connect device
            loop.run_until_complete(
                self.device_manager.connect_device(self.device_info.device_id, 'hl7')
            )
            
            # Send command
            command = {'command': 'STATUS_CHECK'}
            result = loop.run_until_complete(
                self.device_manager.send_device_command(
                    self.device_info.device_id, 'hl7', command
                )
            )
            
            self.assertEqual(result['status'], 'success')
        finally:
            loop.close()
    
    def test_add_data_callback(self):
        """Test adding data callback"""
        callback = Mock()
        
        self.device_manager.add_data_callback(callback)
        
        self.assertIn(callback, self.device_manager.data_callbacks)
    
    def test_add_alarm_callback(self):
        """Test adding alarm callback"""
        callback = Mock()
        
        self.device_manager.add_alarm_callback(callback)
        
        self.assertIn(callback, self.device_manager.alarm_callbacks)
    
    def test_acknowledge_alarm(self):
        """Test acknowledging alarm"""
        device_id = "test_device_001"
        alarm = DeviceAlarm(
            device_id=device_id,
            alarm_id="alarm_001",
            timestamp=datetime.datetime.utcnow(),
            severity=AlarmSeverity.MEDIUM,
            message="Test alarm",
            acknowledged=False
        )
        
        # Add alarm to active alarms
        self.device_manager.active_alarms[device_id] = [alarm]
        
        # Acknowledge alarm
        result = self.device_manager.acknowledge_alarm(
            device_id, "alarm_001", "nurse_jane"
        )
        
        self.assertTrue(result)
        self.assertTrue(alarm.acknowledged)
        self.assertEqual(alarm.acknowledged_by, "nurse_jane")
        self.assertIsNotNone(alarm.acknowledged_at)
    
    def test_get_device_status(self):
        """Test getting device status"""
        # Register device
        self.device_manager.register_device(self.device_info, 'hl7')
        
        status = self.device_manager.get_device_status(self.device_info.device_id)
        
        self.assertEqual(status, DeviceStatus.DISCONNECTED)
    
    def test_get_device_readings(self):
        """Test getting device readings"""
        device_id = "test_device_001"
        reading = DeviceReading(
            device_id=device_id,
            timestamp=datetime.datetime.utcnow(),
            data_type=DataType.HEART_RATE,
            value=75.0,
            unit="bpm"
        )
        
        # Add reading to active readings
        self.device_manager.active_readings[device_id] = [reading]
        
        readings = self.device_manager.get_device_readings(device_id)
        
        self.assertEqual(len(readings), 1)
        self.assertEqual(readings[0], reading)
    
    def test_get_device_alarms(self):
        """Test getting device alarms"""
        device_id = "test_device_001"
        alarm1 = DeviceAlarm(
            device_id=device_id,
            alarm_id="alarm_001",
            timestamp=datetime.datetime.utcnow(),
            severity=AlarmSeverity.MEDIUM,
            message="Test alarm 1",
            acknowledged=False
        )
        alarm2 = DeviceAlarm(
            device_id=device_id,
            alarm_id="alarm_002",
            timestamp=datetime.datetime.utcnow(),
            severity=AlarmSeverity.HIGH,
            message="Test alarm 2",
            acknowledged=True
        )
        
        # Add alarms to active alarms
        self.device_manager.active_alarms[device_id] = [alarm1, alarm2]
        
        # Get all alarms
        all_alarms = self.device_manager.get_device_alarms(device_id)
        self.assertEqual(len(all_alarms), 2)
        
        # Get only unacknowledged alarms
        unack_alarms = self.device_manager.get_device_alarms(device_id, acknowledged=False)
        self.assertEqual(len(unack_alarms), 1)
        self.assertEqual(unack_alarms[0].alarm_id, "alarm_001")
    
    def test_get_all_devices(self):
        """Test getting all device information"""
        # Register multiple devices
        device2 = DeviceInfo(
            device_id="test_device_002",
            device_type=DeviceType.PULSE_OXIMETER,
            manufacturer="Test Corp",
            model="TestOx",
            serial_number="TEST456",
            firmware_version="1.1.0"
        )
        
        self.device_manager.register_device(self.device_info, 'hl7')
        self.device_manager.register_device(device2, 'mqtt')
        
        all_devices = self.device_manager.get_all_devices()
        
        self.assertEqual(len(all_devices), 2)
        
        device_ids = [d['device_id'] for d in all_devices]
        self.assertIn(self.device_info.device_id, device_ids)
        self.assertIn(device2.device_id, device_ids)


class TestDeviceDataProcessor(unittest.TestCase):
    
    def setUp(self):
        self.processor = DeviceDataProcessor()
    
    def test_validate_reading_valid(self):
        """Test validating valid reading"""
        reading = DeviceReading(
            device_id="test_device",
            timestamp=datetime.datetime.utcnow(),
            data_type=DataType.HEART_RATE,
            value=75.0,
            unit="bpm"
        )
        
        errors = self.processor.validate_reading(reading)
        
        self.assertEqual(len(errors), 0)
    
    def test_validate_reading_invalid_high(self):
        """Test validating reading with too high value"""
        reading = DeviceReading(
            device_id="test_device",
            timestamp=datetime.datetime.utcnow(),
            data_type=DataType.HEART_RATE,
            value=250.0,  # Too high
            unit="bpm"
        )
        
        errors = self.processor.validate_reading(reading)
        
        self.assertGreater(len(errors), 0)
        self.assertIn("above maximum", errors[0])
    
    def test_validate_reading_invalid_low(self):
        """Test validating reading with too low value"""
        reading = DeviceReading(
            device_id="test_device",
            timestamp=datetime.datetime.utcnow(),
            data_type=DataType.HEART_RATE,
            value=20.0,  # Too low
            unit="bpm"
        )
        
        errors = self.processor.validate_reading(reading)
        
        self.assertGreater(len(errors), 0)
        self.assertIn("below minimum", errors[0])
    
    def test_validate_blood_pressure(self):
        """Test validating blood pressure reading"""
        valid_reading = DeviceReading(
            device_id="test_device",
            timestamp=datetime.datetime.utcnow(),
            data_type=DataType.BLOOD_PRESSURE,
            value={"systolic": 120, "diastolic": 80},
            unit="mmHg"
        )
        
        errors = self.processor.validate_reading(valid_reading)
        self.assertEqual(len(errors), 0)
        
        # Invalid reading
        invalid_reading = DeviceReading(
            device_id="test_device",
            timestamp=datetime.datetime.utcnow(),
            data_type=DataType.BLOOD_PRESSURE,
            value={"systolic": 300, "diastolic": 200},  # Too high
            unit="mmHg"
        )
        
        errors = self.processor.validate_reading(invalid_reading)
        self.assertGreater(len(errors), 0)
    
    def test_normalize_temperature_fahrenheit(self):
        """Test normalizing Fahrenheit temperature to Celsius"""
        reading = DeviceReading(
            device_id="test_device",
            timestamp=datetime.datetime.utcnow(),
            data_type=DataType.TEMPERATURE,
            value=98.6,  # Fahrenheit
            unit="F"
        )
        
        normalized = self.processor.normalize_reading(reading)
        
        self.assertEqual(normalized.unit, "°C")
        self.assertAlmostEqual(normalized.value, 37.0, places=1)  # ~37°C
    
    def test_normalize_reading_quality_indicator(self):
        """Test adding quality indicator during normalization"""
        reading = DeviceReading(
            device_id="test_device",
            timestamp=datetime.datetime.utcnow(),
            data_type=DataType.HEART_RATE,
            value=75.0,
            unit="bpm"
        )
        
        normalized = self.processor.normalize_reading(reading)
        
        self.assertEqual(normalized.quality_indicator, "good")
    
    def test_aggregate_readings(self):
        """Test aggregating device readings"""
        now = datetime.datetime.utcnow()
        readings = [
            DeviceReading(
                device_id="test_device",
                timestamp=now - datetime.timedelta(minutes=i),
                data_type=DataType.HEART_RATE,
                value=70.0 + i,
                unit="bpm"
            ) for i in range(5)
        ]
        
        aggregated = self.processor.aggregate_readings(readings)
        
        self.assertIn('heart_rate', aggregated)
        hr_stats = aggregated['heart_rate']
        
        self.assertEqual(hr_stats['count'], 5)
        self.assertEqual(hr_stats['min'], 70.0)
        self.assertEqual(hr_stats['max'], 74.0)
        self.assertEqual(hr_stats['avg'], 72.0)
        self.assertEqual(hr_stats['unit'], 'bpm')


if __name__ == '__main__':
    unittest.main()