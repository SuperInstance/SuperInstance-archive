"""
Natural Language to Arduino Code Generator
"""

import re
import uuid
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import asyncio
import openai
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from ..database import CodeGeneration, DeviceType, CodeGenerationStatus, Device


class ArduinoCodeGenerator:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.device_specifications = {
            DeviceType.ARDUINO_UNO: {
                "digital_pins": list(range(2, 14)),
                "analog_pins": list(range(14, 20)),
                "pwm_pins": [3, 5, 6, 9, 10, 11],
                "i2c_pins": {"sda": 18, "scl": 19},
                "spi_pins": {"mosi": 11, "miso": 12, "sck": 13},
                "voltage": 5,
                "flash_memory": 32,
                "sram": 2,
                "eeprom": 1
            },
            DeviceType.ESP32: {
                "digital_pins": list(range(0, 40)),
                "analog_pins": [32, 33, 34, 35, 36, 37, 38, 39],
                "pwm_pins": list(range(0, 16)),
                "i2c_pins": {"sda": 21, "scl": 22},
                "spi_pins": {"mosi": 23, "miso": 19, "sck": 18},
                "voltage": 3.3,
                "flash_memory": 4096,
                "sram": 520,
                "wifi": True,
                "bluetooth": True
            },
            DeviceType.ESP8266: {
                "digital_pins": [0, 1, 2, 3, 4, 5, 12, 13, 14, 15, 16],
                "analog_pins": [17],
                "pwm_pins": [0, 1, 2, 3, 4, 5, 12, 13, 14, 15, 16],
                "i2c_pins": {"sda": 4, "scl": 5},
                "spi_pins": {"mosi": 13, "miso": 12, "sck": 14},
                "voltage": 3.3,
                "flash_memory": 4096,
                "sram": 80,
                "wifi": True
            }
        }
        
        self.sensor_libraries = {
            "temperature": ["DHT.h", "OneWire.h", "DallasTemperature.h"],
            "humidity": ["DHT.h"],
            "pressure": ["Adafruit_BMP280.h", "Wire.h"],
            "light": ["BH1750.h", "Wire.h"],
            "motion": [],
            "distance": ["NewPing.h"],
            "accelerometer": ["Adafruit_MPU6050.h", "Wire.h"],
            "gps": ["SoftwareSerial.h", "TinyGPS++.h"],
            "wifi": ["WiFi.h"],
            "bluetooth": ["BluetoothSerial.h"]
        }
        
    async def generate_code_from_nl(
        self,
        user_id: uuid.UUID,
        natural_language: str,
        device_type: DeviceType,
        device_id: Optional[uuid.UUID] = None
    ) -> uuid.UUID:
        """Generate Arduino code from natural language description"""
        
        # Create code generation record
        code_gen = CodeGeneration(
            user_id=user_id,
            natural_language_input=natural_language,
            device_type=device_type,
            device_id=device_id,
            status=CodeGenerationStatus.GENERATING
        )
        
        self.session.add(code_gen)
        await self.session.commit()
        await self.session.refresh(code_gen)
        
        try:
            start_time = datetime.utcnow()
            
            # Parse natural language input
            requirements = await self._parse_requirements(natural_language)
            
            # Generate code based on device type and requirements
            generated_code = await self._generate_arduino_code(
                requirements, device_type
            )
            
            # Update code generation record
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            await self.session.execute(
                update(CodeGeneration)
                .where(CodeGeneration.id == code_gen.id)
                .values(
                    generated_code=generated_code,
                    status=CodeGenerationStatus.COMPLETED,
                    processing_time=processing_time,
                    completed_at=datetime.utcnow()
                )
            )
            await self.session.commit()
            
        except Exception as e:
            await self.session.execute(
                update(CodeGeneration)
                .where(CodeGeneration.id == code_gen.id)
                .values(
                    status=CodeGenerationStatus.FAILED,
                    error_message=str(e)
                )
            )
            await self.session.commit()
            raise
        
        return code_gen.id
    
    async def _parse_requirements(self, natural_language: str) -> Dict[str, Any]:
        """Parse natural language to extract requirements"""
        requirements = {
            "sensors": [],
            "actuators": [],
            "communication": [],
            "functions": [],
            "pins": {},
            "libraries": set()
        }
        
        text = natural_language.lower()
        
        # Detect sensors
        sensor_patterns = {
            "temperature": ["temperature", "temp", "thermometer", "heat", "cold"],
            "humidity": ["humidity", "moisture", "damp"],
            "pressure": ["pressure", "barometric", "atmospheric"],
            "light": ["light", "brightness", "photocell", "ldr"],
            "motion": ["motion", "pir", "movement", "detection"],
            "distance": ["distance", "ultrasonic", "range", "proximity"],
            "accelerometer": ["accelerometer", "acceleration", "tilt", "orientation"],
            "gps": ["gps", "location", "coordinates", "position"]
        }
        
        for sensor_type, keywords in sensor_patterns.items():
            if any(keyword in text for keyword in keywords):
                requirements["sensors"].append(sensor_type)
                requirements["libraries"].update(self.sensor_libraries.get(sensor_type, []))
        
        # Detect actuators
        actuator_patterns = {
            "led": ["led", "light", "lamp", "bulb"],
            "motor": ["motor", "servo", "stepper", "rotation"],
            "buzzer": ["buzzer", "alarm", "sound", "beep"],
            "relay": ["relay", "switch", "control", "power"],
            "display": ["display", "lcd", "oled", "screen", "monitor"]
        }
        
        for actuator_type, keywords in actuator_patterns.items():
            if any(keyword in text for keyword in keywords):
                requirements["actuators"].append(actuator_type)
        
        # Detect communication methods
        comm_patterns = {
            "wifi": ["wifi", "wireless", "internet", "web", "http"],
            "bluetooth": ["bluetooth", "ble", "wireless"],
            "serial": ["serial", "uart", "communication"],
            "i2c": ["i2c", "wire", "bus"],
            "spi": ["spi", "bus"]
        }
        
        for comm_type, keywords in comm_patterns.items():
            if any(keyword in text for keyword in keywords):
                requirements["communication"].append(comm_type)
                if comm_type in self.sensor_libraries:
                    requirements["libraries"].update(self.sensor_libraries[comm_type])
        
        # Detect functions and behaviors
        function_patterns = {
            "read_sensor": ["read", "measure", "detect", "sense"],
            "control_actuator": ["control", "turn on", "turn off", "activate"],
            "send_data": ["send", "transmit", "upload", "post"],
            "receive_data": ["receive", "download", "get", "fetch"],
            "store_data": ["store", "save", "log", "record"],
            "display_data": ["display", "show", "print", "output"]
        }
        
        for function_type, keywords in function_patterns.items():
            if any(keyword in text for keyword in keywords):
                requirements["functions"].append(function_type)
        
        return requirements
    
    async def _generate_arduino_code(
        self,
        requirements: Dict[str, Any],
        device_type: DeviceType
    ) -> str:
        """Generate Arduino code based on requirements"""
        
        device_spec = self.device_specifications.get(device_type)
        if not device_spec:
            raise ValueError(f"Unsupported device type: {device_type}")
        
        code_parts = []
        
        # Generate includes
        includes = self._generate_includes(requirements)
        if includes:
            code_parts.append(includes)
        
        # Generate global variables and pin definitions
        globals_section = self._generate_globals(requirements, device_spec)
        if globals_section:
            code_parts.append(globals_section)
        
        # Generate setup function
        setup_section = self._generate_setup(requirements, device_type)
        code_parts.append(setup_section)
        
        # Generate loop function
        loop_section = self._generate_loop(requirements)
        code_parts.append(loop_section)
        
        # Generate helper functions
        helpers = self._generate_helper_functions(requirements)
        if helpers:
            code_parts.append(helpers)
        
        return "\n\n".join(code_parts)
    
    def _generate_includes(self, requirements: Dict[str, Any]) -> str:
        """Generate #include statements"""
        includes = []
        
        for library in sorted(requirements["libraries"]):
            includes.append(f"#include <{library}>")
        
        if not includes:
            return ""
        
        return "\n".join(includes)
    
    def _generate_globals(
        self,
        requirements: Dict[str, Any],
        device_spec: Dict[str, Any]
    ) -> str:
        """Generate global variables and pin definitions"""
        globals_lines = []
        
        # Pin definitions
        pin_counter = 2  # Start from pin 2
        
        for sensor in requirements["sensors"]:
            if sensor == "temperature" and "DHT.h" in requirements["libraries"]:
                globals_lines.append(f"#define DHT_PIN {pin_counter}")
                globals_lines.append("#define DHT_TYPE DHT22")
                globals_lines.append("DHT dht(DHT_PIN, DHT_TYPE);")
                pin_counter += 1
            elif sensor == "distance":
                globals_lines.append(f"#define TRIGGER_PIN {pin_counter}")
                globals_lines.append(f"#define ECHO_PIN {pin_counter + 1}")
                globals_lines.append("NewPing sonar(TRIGGER_PIN, ECHO_PIN, 200);")
                pin_counter += 2
            elif sensor == "light":
                if pin_counter in device_spec.get("analog_pins", []):
                    globals_lines.append(f"#define LIGHT_PIN A{pin_counter - 14}")
                else:
                    globals_lines.append(f"#define LIGHT_PIN {pin_counter}")
                pin_counter += 1
        
        for actuator in requirements["actuators"]:
            if actuator == "led":
                globals_lines.append(f"#define LED_PIN {pin_counter}")
                pin_counter += 1
            elif actuator == "buzzer":
                globals_lines.append(f"#define BUZZER_PIN {pin_counter}")
                pin_counter += 1
            elif actuator == "motor":
                if pin_counter in device_spec.get("pwm_pins", []):
                    globals_lines.append(f"#define MOTOR_PIN {pin_counter}")
                    pin_counter += 1
        
        # Communication objects
        if "wifi" in requirements["communication"] and device_spec.get("wifi"):
            globals_lines.append('const char* ssid = "YOUR_WIFI_SSID";')
            globals_lines.append('const char* password = "YOUR_WIFI_PASSWORD";')
        
        if "bluetooth" in requirements["communication"] and device_spec.get("bluetooth"):
            globals_lines.append("BluetoothSerial SerialBT;")
        
        return "\n".join(globals_lines) if globals_lines else ""
    
    def _generate_setup(
        self,
        requirements: Dict[str, Any],
        device_type: DeviceType
    ) -> str:
        """Generate setup() function"""
        setup_lines = [
            "void setup() {",
            "  Serial.begin(115200);",
            "  delay(1000);"
        ]
        
        # Initialize sensors
        for sensor in requirements["sensors"]:
            if sensor == "temperature" and "DHT.h" in requirements["libraries"]:
                setup_lines.append("  dht.begin();")
            elif sensor == "pressure":
                setup_lines.append("  Wire.begin();")
                setup_lines.append("  // Initialize BMP280 sensor")
            elif sensor == "accelerometer":
                setup_lines.append("  Wire.begin();")
                setup_lines.append("  // Initialize MPU6050 sensor")
        
        # Initialize actuators
        for actuator in requirements["actuators"]:
            if actuator == "led":
                setup_lines.append("  pinMode(LED_PIN, OUTPUT);")
            elif actuator == "buzzer":
                setup_lines.append("  pinMode(BUZZER_PIN, OUTPUT);")
        
        # Initialize communication
        if "wifi" in requirements["communication"]:
            if device_type in [DeviceType.ESP32, DeviceType.ESP8266]:
                setup_lines.extend([
                    "  WiFi.begin(ssid, password);",
                    "  while (WiFi.status() != WL_CONNECTED) {",
                    "    delay(1000);",
                    "    Serial.println(\"Connecting to WiFi...\");",
                    "  }",
                    "  Serial.println(\"Connected to WiFi\");"
                ])
        
        if "bluetooth" in requirements["communication"]:
            setup_lines.append('  SerialBT.begin("ESP32");')
        
        setup_lines.append("}")
        return "\n".join(setup_lines)
    
    def _generate_loop(self, requirements: Dict[str, Any]) -> str:
        """Generate loop() function"""
        loop_lines = [
            "void loop() {"
        ]
        
        # Read sensors
        if "read_sensor" in requirements["functions"]:
            for sensor in requirements["sensors"]:
                if sensor == "temperature":
                    loop_lines.extend([
                        "  float temperature = dht.readTemperature();",
                        "  Serial.print(\"Temperature: \");",
                        "  Serial.println(temperature);"
                    ])
                elif sensor == "humidity":
                    loop_lines.extend([
                        "  float humidity = dht.readHumidity();",
                        "  Serial.print(\"Humidity: \");",
                        "  Serial.println(humidity);"
                    ])
                elif sensor == "distance":
                    loop_lines.extend([
                        "  int distance = sonar.ping_cm();",
                        "  Serial.print(\"Distance: \");",
                        "  Serial.println(distance);"
                    ])
                elif sensor == "light":
                    loop_lines.extend([
                        "  int lightLevel = analogRead(LIGHT_PIN);",
                        "  Serial.print(\"Light Level: \");",
                        "  Serial.println(lightLevel);"
                    ])
        
        # Control actuators
        if "control_actuator" in requirements["functions"]:
            for actuator in requirements["actuators"]:
                if actuator == "led":
                    loop_lines.extend([
                        "  digitalWrite(LED_PIN, HIGH);",
                        "  delay(1000);",
                        "  digitalWrite(LED_PIN, LOW);",
                        "  delay(1000);"
                    ])
        
        loop_lines.extend([
            "  delay(2000);",
            "}"
        ])
        
        return "\n".join(loop_lines)
    
    def _generate_helper_functions(self, requirements: Dict[str, Any]) -> str:
        """Generate helper functions"""
        helpers = []
        
        if "send_data" in requirements["functions"]:
            if "wifi" in requirements["communication"]:
                helpers.append("""
void sendData(String data) {
  if (WiFi.status() == WL_CONNECTED) {
    // Send data via HTTP POST
    // Implementation depends on specific endpoint
    Serial.println("Sending data: " + data);
  }
}""")
        
        if "store_data" in requirements["functions"]:
            helpers.append("""
void storeData(String data) {
  // Store data to EEPROM or local storage
  Serial.println("Storing data: " + data);
}""")
        
        return "\n".join(helpers) if helpers else ""
    
    async def get_code_generation(self, generation_id: uuid.UUID) -> Optional[CodeGeneration]:
        """Get code generation by ID"""
        result = await self.session.execute(
            select(CodeGeneration).where(CodeGeneration.id == generation_id)
        )
        return result.scalar_one_or_none()
    
    async def get_user_code_generations(
        self,
        user_id: uuid.UUID,
        limit: int = 10
    ) -> List[CodeGeneration]:
        """Get user's code generations"""
        result = await self.session.execute(
            select(CodeGeneration)
            .where(CodeGeneration.user_id == user_id)
            .order_by(CodeGeneration.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()