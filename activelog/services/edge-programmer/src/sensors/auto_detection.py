"""
Sensor Auto-Detection System
"""

import uuid
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..database import Device, SensorReading, SensorType, PinConfiguration
from ..serial.usb_serial import USBSerialManager


class SensorAutoDetection:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.serial_manager = USBSerialManager(session)
        
        # Sensor detection patterns and methods
        self.detection_methods = {
            SensorType.TEMPERATURE: {
                "i2c_addresses": [0x48, 0x49, 0x4A, 0x4B],  # TMP102, etc.
                "analog_threshold": {"min": 100, "max": 900},
                "digital_patterns": ["DHT", "DS18B20"],
                "detection_code": self._generate_temperature_detection_code
            },
            SensorType.HUMIDITY: {
                "i2c_addresses": [0x40, 0x44],  # HTU21D, SHT30
                "digital_patterns": ["DHT", "AM2302"],
                "detection_code": self._generate_humidity_detection_code
            },
            SensorType.PRESSURE: {
                "i2c_addresses": [0x76, 0x77],  # BMP280, BME280
                "detection_code": self._generate_pressure_detection_code
            },
            SensorType.LIGHT: {
                "i2c_addresses": [0x23, 0x5C],  # BH1750, TSL2561
                "analog_threshold": {"min": 0, "max": 1023},
                "detection_code": self._generate_light_detection_code
            },
            SensorType.ACCELEROMETER: {
                "i2c_addresses": [0x68, 0x69],  # MPU6050, MPU9250
                "spi_patterns": ["ADXL"],
                "detection_code": self._generate_accelerometer_detection_code
            },
            SensorType.GYROSCOPE: {
                "i2c_addresses": [0x68, 0x69],  # MPU6050, MPU9250
                "detection_code": self._generate_gyroscope_detection_code
            },
            SensorType.MAGNETOMETER: {
                "i2c_addresses": [0x1E, 0x0C],  # HMC5883L, AK8963
                "detection_code": self._generate_magnetometer_detection_code
            },
            SensorType.DISTANCE: {
                "digital_patterns": ["HC-SR04", "VL53L0X"],
                "detection_code": self._generate_distance_detection_code
            },
            SensorType.GPS: {
                "uart_patterns": ["$GPGGA", "$GPRMC"],
                "detection_code": self._generate_gps_detection_code
            }
        }
    
    async def detect_connected_sensors(
        self,
        device_id: uuid.UUID,
        scan_method: str = "comprehensive"
    ) -> Dict[str, Any]:
        """Detect sensors connected to the device"""
        
        device = await self._get_device(device_id)
        if not device:
            raise ValueError(f"Device {device_id} not found")
        
        detection_results = {
            "device_id": str(device_id),
            "device_type": device.device_type.value,
            "scan_method": scan_method,
            "detected_sensors": {},
            "i2c_devices": [],
            "analog_readings": {},
            "digital_states": {},
            "uart_data": [],
            "scan_duration": 0,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        start_time = datetime.utcnow()
        
        try:
            if scan_method in ["comprehensive", "i2c"]:
                detection_results["i2c_devices"] = await self._scan_i2c_bus(device)
            
            if scan_method in ["comprehensive", "analog"]:
                detection_results["analog_readings"] = await self._scan_analog_pins(device)
            
            if scan_method in ["comprehensive", "digital"]:
                detection_results["digital_states"] = await self._scan_digital_pins(device)
            
            if scan_method in ["comprehensive", "uart"]:
                detection_results["uart_data"] = await self._scan_uart_ports(device)
            
            # Analyze results and identify sensors
            detected_sensors = await self._analyze_detection_results(detection_results)
            detection_results["detected_sensors"] = detected_sensors
            
            # Calculate scan duration
            scan_duration = (datetime.utcnow() - start_time).total_seconds()
            detection_results["scan_duration"] = scan_duration
            
            return detection_results
            
        except Exception as e:
            detection_results["error"] = str(e)
            return detection_results
    
    async def _get_device(self, device_id: uuid.UUID) -> Optional[Device]:
        """Get device from database"""
        result = await self.session.execute(
            select(Device).where(Device.id == device_id)
        )
        return result.scalar_one_or_none()
    
    async def _scan_i2c_bus(self, device: Device) -> List[Dict[str, Any]]:
        """Scan I2C bus for connected devices"""
        
        if not device.ip_address:
            return []
        
        try:
            # Generate and upload I2C scanner code
            scanner_code = self._generate_i2c_scanner_code(device.device_type)
            
            # This would upload the scanner code and read results
            # For now, return simulated results
            detected_devices = []
            
            # Simulate I2C scan results
            common_addresses = [0x23, 0x40, 0x48, 0x68, 0x76]
            for addr in common_addresses:
                # In real implementation, this would come from device
                detected_devices.append({
                    "address": f"0x{addr:02X}",
                    "address_decimal": addr,
                    "possible_sensors": self._identify_i2c_device(addr)
                })
            
            return detected_devices
            
        except Exception as e:
            print(f"I2C scan failed: {str(e)}")
            return []
    
    async def _scan_analog_pins(self, device: Device) -> Dict[str, Any]:
        """Scan analog pins for sensor readings"""
        
        analog_readings = {}
        
        # Get device pin configuration
        pin_config = await self._get_device_pins(device.id)
        analog_pins = [p for p in pin_config if pin_config[p].get("type") == "analog"]
        
        try:
            # Generate analog scanner code
            scanner_code = self._generate_analog_scanner_code(device.device_type, analog_pins)
            
            # Simulate analog readings
            for pin in analog_pins:
                # In real implementation, read from device
                analog_readings[f"A{pin}"] = {
                    "raw_value": 512,  # 0-1023 for Arduino, 0-4095 for ESP32
                    "voltage": 2.5,
                    "possible_sensors": self._analyze_analog_value(512)
                }
            
            return analog_readings
            
        except Exception as e:
            print(f"Analog scan failed: {str(e)}")
            return {}
    
    async def _scan_digital_pins(self, device: Device) -> Dict[str, Any]:
        """Scan digital pins for sensor signals"""
        
        digital_states = {}
        
        # Get device pin configuration
        pin_config = await self._get_device_pins(device.id)
        digital_pins = [p for p in pin_config if pin_config[p].get("type") == "digital"]
        
        try:
            # Monitor digital pins for activity
            for pin in digital_pins[:5]:  # Limit to first 5 pins
                digital_states[f"D{pin}"] = {
                    "state": "LOW",  # Would read from device
                    "activity": "stable",
                    "possible_sensors": self._analyze_digital_activity("stable")
                }
            
            return digital_states
            
        except Exception as e:
            print(f"Digital scan failed: {str(e)}")
            return {}
    
    async def _scan_uart_ports(self, device: Device) -> List[Dict[str, Any]]:
        """Scan UART ports for sensor data"""
        
        uart_data = []
        
        try:
            # Monitor serial data for GPS or other UART sensors
            # This would listen to actual UART data
            uart_data.append({
                "port": "Serial1",
                "baud_rate": 9600,
                "data_sample": "$GPGGA,123456,1234.567,N,12345.678,E,1,04,1.2,100.0,M,50.0,M,,*7F",
                "possible_sensors": [SensorType.GPS.value]
            })
            
            return uart_data
            
        except Exception as e:
            print(f"UART scan failed: {str(e)}")
            return []
    
    async def _get_device_pins(self, device_id: uuid.UUID) -> Dict[int, Dict[str, Any]]:
        """Get device pin configuration"""
        
        result = await self.session.execute(
            select(PinConfiguration).where(PinConfiguration.device_id == device_id)
        )
        configs = result.scalars().all()
        
        pins = {}
        for config in configs:
            pins[config.pin_number] = {
                "type": config.pin_type.value,
                "function": config.function,
                "sensor_type": config.sensor_type.value if config.sensor_type else None
            }
        
        return pins
    
    def _identify_i2c_device(self, address: int) -> List[str]:
        """Identify possible sensors based on I2C address"""
        
        possible_sensors = []
        
        for sensor_type, detection_info in self.detection_methods.items():
            if address in detection_info.get("i2c_addresses", []):
                possible_sensors.append(sensor_type.value)
        
        return possible_sensors
    
    def _analyze_analog_value(self, value: int) -> List[str]:
        """Analyze analog value to identify possible sensors"""
        
        possible_sensors = []
        
        # Light sensor patterns
        if 0 <= value <= 1023:
            possible_sensors.append(SensorType.LIGHT.value)
        
        # Temperature sensor patterns (if using analog temperature sensors)
        if 100 <= value <= 900:
            possible_sensors.append(SensorType.TEMPERATURE.value)
        
        return possible_sensors
    
    def _analyze_digital_activity(self, activity: str) -> List[str]:
        """Analyze digital pin activity to identify sensors"""
        
        possible_sensors = []
        
        if activity == "periodic":
            possible_sensors.extend([
                SensorType.MOTION.value,
                SensorType.DISTANCE.value
            ])
        elif activity == "stable":
            possible_sensors.append("button_or_switch")
        
        return possible_sensors
    
    async def _analyze_detection_results(
        self,
        results: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        """Analyze all detection results to identify sensors"""
        
        detected_sensors = {}
        
        # Analyze I2C devices
        for i2c_device in results.get("i2c_devices", []):
            address = i2c_device["address"]
            for sensor_type in i2c_device["possible_sensors"]:
                if sensor_type not in detected_sensors:
                    detected_sensors[sensor_type] = {
                        "confidence": 0.8,
                        "detection_method": "i2c",
                        "address": address,
                        "suggested_library": self._get_sensor_library(sensor_type),
                        "pin_requirements": self._get_pin_requirements(sensor_type)
                    }
        
        # Analyze analog readings
        for pin, reading in results.get("analog_readings", {}).items():
            for sensor_type in reading["possible_sensors"]:
                if sensor_type not in detected_sensors:
                    detected_sensors[sensor_type] = {
                        "confidence": 0.6,
                        "detection_method": "analog",
                        "pin": pin,
                        "value": reading["raw_value"],
                        "suggested_library": self._get_sensor_library(sensor_type)
                    }
        
        # Analyze UART data
        for uart_info in results.get("uart_data", []):
            for sensor_type in uart_info["possible_sensors"]:
                if sensor_type not in detected_sensors:
                    detected_sensors[sensor_type] = {
                        "confidence": 0.9,
                        "detection_method": "uart",
                        "port": uart_info["port"],
                        "baud_rate": uart_info["baud_rate"],
                        "suggested_library": self._get_sensor_library(sensor_type)
                    }
        
        return detected_sensors
    
    def _get_sensor_library(self, sensor_type: str) -> str:
        """Get recommended library for sensor type"""
        
        libraries = {
            SensorType.TEMPERATURE.value: "DHT.h or OneWire.h",
            SensorType.HUMIDITY.value: "DHT.h",
            SensorType.PRESSURE.value: "Adafruit_BMP280.h",
            SensorType.LIGHT.value: "BH1750.h or analog read",
            SensorType.ACCELEROMETER.value: "Adafruit_MPU6050.h",
            SensorType.GYROSCOPE.value: "Adafruit_MPU6050.h",
            SensorType.GPS.value: "SoftwareSerial.h, TinyGPS++.h"
        }
        
        return libraries.get(sensor_type, "Unknown")
    
    def _get_pin_requirements(self, sensor_type: str) -> Dict[str, Any]:
        """Get pin requirements for sensor type"""
        
        requirements = {
            SensorType.TEMPERATURE.value: {"digital": 1},
            SensorType.HUMIDITY.value: {"digital": 1},
            SensorType.PRESSURE.value: {"i2c": 2},
            SensorType.LIGHT.value: {"analog": 1},
            SensorType.ACCELEROMETER.value: {"i2c": 2},
            SensorType.GPS.value: {"uart": 2}
        }
        
        return requirements.get(sensor_type, {})
    
    def _generate_i2c_scanner_code(self, device_type) -> str:
        """Generate I2C scanner code for the device"""
        
        return """
#include <Wire.h>

void setup() {
  Serial.begin(115200);
  Wire.begin();
  Serial.println("I2C Scanner Starting...");
}

void loop() {
  byte error, address;
  int devices = 0;
  
  Serial.println("Scanning I2C bus...");
  
  for(address = 1; address < 127; address++) {
    Wire.beginTransmission(address);
    error = Wire.endTransmission();
    
    if (error == 0) {
      Serial.print("I2C device found at address 0x");
      if (address < 16) Serial.print("0");
      Serial.println(address, HEX);
      devices++;
    }
  }
  
  if (devices == 0) {
    Serial.println("No I2C devices found");
  } else {
    Serial.print("Found ");
    Serial.print(devices);
    Serial.println(" I2C devices");
  }
  
  delay(5000);
}
"""
    
    def _generate_analog_scanner_code(self, device_type, pins) -> str:
        """Generate analog scanner code"""
        
        pin_reads = ""
        for pin in pins:
            pin_reads += f'  Serial.print("A{pin}: "); Serial.println(analogRead(A{pin}));\\n'
        
        return f"""
void setup() {{
  Serial.begin(115200);
  Serial.println("Analog Scanner Starting...");
}}

void loop() {{
  Serial.println("Analog Pin Readings:");
{pin_reads}
  delay(2000);
}}
"""
    
    def _generate_temperature_detection_code(self) -> str:
        return "// Temperature sensor detection code"
    
    def _generate_humidity_detection_code(self) -> str:
        return "// Humidity sensor detection code"
    
    def _generate_pressure_detection_code(self) -> str:
        return "// Pressure sensor detection code"
    
    def _generate_light_detection_code(self) -> str:
        return "// Light sensor detection code"
    
    def _generate_accelerometer_detection_code(self) -> str:
        return "// Accelerometer detection code"
    
    def _generate_gyroscope_detection_code(self) -> str:
        return "// Gyroscope detection code"
    
    def _generate_magnetometer_detection_code(self) -> str:
        return "// Magnetometer detection code"
    
    def _generate_distance_detection_code(self) -> str:
        return "// Distance sensor detection code"
    
    def _generate_gps_detection_code(self) -> str:
        return "// GPS detection code"
    
    async def generate_sensor_code(
        self,
        detected_sensors: Dict[str, Dict[str, Any]],
        device_type
    ) -> str:
        """Generate Arduino code for detected sensors"""
        
        includes = set()
        globals_section = []
        setup_code = []
        loop_code = []
        
        for sensor_type, sensor_info in detected_sensors.items():
            # Add includes
            if sensor_type == SensorType.TEMPERATURE.value:
                includes.add("#include <DHT.h>")
                pin = sensor_info.get("pin", "2")
                globals_section.extend([
                    f"#define DHT_PIN {pin}",
                    "#define DHT_TYPE DHT22",
                    "DHT dht(DHT_PIN, DHT_TYPE);"
                ])
                setup_code.append("  dht.begin();")
                loop_code.extend([
                    "  float temperature = dht.readTemperature();",
                    "  Serial.print(\"Temperature: \");",
                    "  Serial.println(temperature);"
                ])
            
            elif sensor_type == SensorType.LIGHT.value:
                pin = sensor_info.get("pin", "A0")
                loop_code.extend([
                    f"  int lightLevel = analogRead({pin});",
                    "  Serial.print(\"Light Level: \");",
                    "  Serial.println(lightLevel);"
                ])
        
        # Build complete code
        code_parts = []
        
        if includes:
            code_parts.append("\\n".join(sorted(includes)))
        
        if globals_section:
            code_parts.append("\\n".join(globals_section))
        
        setup_section = ["void setup() {", "  Serial.begin(115200);"] + setup_code + ["}"]
        code_parts.append("\\n".join(setup_section))
        
        loop_section = ["void loop() {"] + loop_code + ["  delay(2000);", "}"]
        code_parts.append("\\n".join(loop_section))
        
        return "\\n\\n".join(code_parts)
    
    async def save_detection_results(
        self,
        device_id: uuid.UUID,
        detection_results: Dict[str, Any]
    ) -> bool:
        """Save detection results to database for future reference"""
        
        try:
            # Update device metadata with detection results
            device = await self._get_device(device_id)
            if device:
                metadata = device.metadata or {}
                metadata["last_sensor_scan"] = detection_results
                metadata["last_scan_timestamp"] = datetime.utcnow().isoformat()
                
                # Update device
                from sqlalchemy import update
                await self.session.execute(
                    update(Device)
                    .where(Device.id == device_id)
                    .values(metadata=metadata)
                )
                await self.session.commit()
                
                return True
            
            return False
            
        except Exception as e:
            print(f"Failed to save detection results: {str(e)}")
            return False