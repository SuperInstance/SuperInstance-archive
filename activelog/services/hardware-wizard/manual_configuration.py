import asyncio
import json
import time
import uuid
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime
import random

class WizardStep(Enum):
    DEVICE_TYPE = "device_type"
    CONNECTION = "connection" 
    INTERFACE_CONFIG = "interface_config"
    DRIVER_SELECTION = "driver_selection"
    BASIC_CONFIG = "basic_config"
    ADVANCED_CONFIG = "advanced_config"
    TESTING = "testing"
    CALIBRATION = "calibration"
    FINALIZATION = "finalization"
    COMPLETE = "complete"

class ValidationResult(Enum):
    VALID = "valid"
    INVALID = "invalid"
    WARNING = "warning"
    PENDING = "pending"

class TroubleshootingLevel(Enum):
    BASIC = "basic"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"

@dataclass
class WizardStepDefinition:
    step: WizardStep
    title: str
    description: str
    fields: List[Dict[str, Any]]
    validations: List[Dict[str, Any]]
    help_content: str
    troubleshooting_tips: List[str]
    estimated_time: int  # minutes
    skippable: bool = False
    
@dataclass
class ValidationError:
    field: str
    message: str
    severity: ValidationResult
    suggestion: Optional[str] = None

@dataclass
class TroubleshootingSuggestion:
    issue: str
    level: TroubleshootingLevel
    steps: List[str]
    resources: List[str]
    estimated_time: int

@dataclass
class ManualConfigSession:
    session_id: str
    user_id: str
    device_name: str
    current_step: WizardStep
    completed_steps: List[WizardStep]
    step_data: Dict[WizardStep, Dict[str, Any]]
    validation_errors: List[ValidationError]
    created_at: datetime
    last_updated: datetime
    estimated_completion: Optional[datetime] = None
    troubleshooting_history: List[TroubleshootingSuggestion] = None
    
    def __post_init__(self):
        if self.troubleshooting_history is None:
            self.troubleshooting_history = []

class CommunityDrivers:
    def __init__(self):
        self.community_db = {}
        self.ratings = {}
        self.download_stats = {}
        
    def search_drivers(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search community drivers"""
        # Simulate community driver search
        drivers = [
            {
                "id": f"community_driver_{i}",
                "name": f"Community Driver {i}",
                "author": random.choice(["TechGuru42", "HardwareHacker", "DeviceMaster", "OpenSourceDev"]),
                "description": f"Community-contributed driver for {query.get('device_type', 'unknown')} devices",
                "version": f"{random.randint(1, 3)}.{random.randint(0, 9)}.{random.randint(0, 9)}",
                "rating": round(random.uniform(3.5, 5.0), 1),
                "downloads": random.randint(100, 10000),
                "last_updated": (datetime.now()).isoformat(),
                "compatibility": random.sample(["Windows", "Linux", "macOS", "Raspberry Pi"], random.randint(2, 4)),
                "protocols": random.sample(["USB", "Serial", "I2C", "SPI", "Ethernet"], random.randint(1, 3)),
                "verified": random.random() > 0.3,  # 70% verified
                "license": random.choice(["MIT", "GPL-3.0", "Apache-2.0", "BSD-2-Clause"]),
                "source_url": f"https://github.com/community/{query.get('device_type', 'device')}_driver_{i}",
                "documentation": f"https://docs.community.drivers/{query.get('device_type', 'device')}/{i}",
                "examples": [
                    f"https://github.com/community/examples/{i}/basic.py",
                    f"https://github.com/community/examples/{i}/advanced.py"
                ]
            }
            for i in range(random.randint(3, 12))
        ]
        
        return drivers
    
    def get_driver_reviews(self, driver_id: str) -> List[Dict[str, Any]]:
        """Get driver reviews"""
        return [
            {
                "user": f"User{random.randint(100, 999)}",
                "rating": random.randint(3, 5),
                "comment": random.choice([
                    "Works great! Easy to install and configure.",
                    "Had some issues initially but got it working.",
                    "Excellent documentation and examples.",
                    "Perfect for my project, highly recommended.",
                    "Good driver but could use better error handling."
                ]),
                "date": datetime.now().isoformat(),
                "helpful_votes": random.randint(0, 20)
            }
            for _ in range(random.randint(2, 8))
        ]

class ProtocolBuilder:
    def __init__(self):
        self.protocol_templates = {
            "serial": {
                "name": "Custom Serial Protocol",
                "fields": [
                    {"name": "baud_rate", "type": "integer", "default": 115200, "options": [9600, 19200, 38400, 57600, 115200, 230400]},
                    {"name": "data_bits", "type": "integer", "default": 8, "options": [7, 8]},
                    {"name": "stop_bits", "type": "integer", "default": 1, "options": [1, 2]},
                    {"name": "parity", "type": "string", "default": "none", "options": ["none", "even", "odd"]},
                    {"name": "flow_control", "type": "string", "default": "none", "options": ["none", "hardware", "software"]},
                    {"name": "command_format", "type": "string", "default": "text", "options": ["text", "binary", "json", "custom"]},
                    {"name": "command_terminator", "type": "string", "default": "\\r\\n"},
                    {"name": "response_timeout", "type": "integer", "default": 1000, "unit": "ms"}
                ]
            },
            "tcp": {
                "name": "Custom TCP Protocol", 
                "fields": [
                    {"name": "port", "type": "integer", "default": 8080, "min": 1, "max": 65535},
                    {"name": "keepalive", "type": "boolean", "default": True},
                    {"name": "timeout", "type": "integer", "default": 5000, "unit": "ms"},
                    {"name": "message_format", "type": "string", "default": "json", "options": ["json", "xml", "binary", "text"]},
                    {"name": "header_size", "type": "integer", "default": 0, "min": 0, "max": 1024},
                    {"name": "endianness", "type": "string", "default": "big", "options": ["big", "little"]},
                    {"name": "compression", "type": "string", "default": "none", "options": ["none", "gzip", "lz4"]}
                ]
            },
            "modbus": {
                "name": "Custom Modbus Protocol",
                "fields": [
                    {"name": "variant", "type": "string", "default": "rtu", "options": ["rtu", "ascii", "tcp"]},
                    {"name": "slave_id", "type": "integer", "default": 1, "min": 1, "max": 247},
                    {"name": "function_codes", "type": "array", "default": [3, 4, 6, 16]},
                    {"name": "register_layout", "type": "object", "default": {}},
                    {"name": "byte_order", "type": "string", "default": "big_endian", "options": ["big_endian", "little_endian"]},
                    {"name": "word_order", "type": "string", "default": "big_endian", "options": ["big_endian", "little_endian"]}
                ]
            }
        }
    
    def get_protocol_template(self, protocol_type: str) -> Dict[str, Any]:
        """Get protocol template"""
        return self.protocol_templates.get(protocol_type, {})
    
    def validate_protocol_config(self, protocol_type: str, config: Dict[str, Any]) -> List[ValidationError]:
        """Validate protocol configuration"""
        errors = []
        template = self.get_protocol_template(protocol_type)
        
        if not template:
            errors.append(ValidationError("protocol_type", "Unknown protocol type", ValidationResult.INVALID))
            return errors
        
        for field in template.get("fields", []):
            field_name = field["name"]
            field_type = field["type"]
            value = config.get(field_name)
            
            if value is None and field.get("required", False):
                errors.append(ValidationError(field_name, f"{field_name} is required", ValidationResult.INVALID))
                continue
            
            if value is not None:
                # Type validation
                if field_type == "integer" and not isinstance(value, int):
                    errors.append(ValidationError(field_name, f"{field_name} must be an integer", ValidationResult.INVALID))
                elif field_type == "boolean" and not isinstance(value, bool):
                    errors.append(ValidationError(field_name, f"{field_name} must be a boolean", ValidationResult.INVALID))
                elif field_type == "string" and not isinstance(value, str):
                    errors.append(ValidationError(field_name, f"{field_name} must be a string", ValidationResult.INVALID))
                
                # Range validation
                if field_type == "integer":
                    if "min" in field and value < field["min"]:
                        errors.append(ValidationError(field_name, f"{field_name} must be >= {field['min']}", ValidationResult.INVALID))
                    if "max" in field and value > field["max"]:
                        errors.append(ValidationError(field_name, f"{field_name} must be <= {field['max']}", ValidationResult.INVALID))
                
                # Options validation
                if "options" in field and value not in field["options"]:
                    errors.append(ValidationError(field_name, f"{field_name} must be one of {field['options']}", ValidationResult.INVALID))
        
        return errors
    
    def generate_driver_code(self, protocol_type: str, config: Dict[str, Any], language: str = "python") -> str:
        """Generate driver code for custom protocol"""
        if language == "python":
            return self._generate_python_driver(protocol_type, config)
        elif language == "javascript":
            return self._generate_javascript_driver(protocol_type, config)
        elif language == "c":
            return self._generate_c_driver(protocol_type, config)
        else:
            return "# Unsupported language"
    
    def _generate_python_driver(self, protocol_type: str, config: Dict[str, Any]) -> str:
        """Generate Python driver code"""
        if protocol_type == "serial":
            return f"""
import serial
import time
import json
from typing import Dict, Any, Optional

class CustomSerialDriver:
    def __init__(self, port: str):
        self.port = port
        self.serial = None
        self.config = {json.dumps(config, indent=8)}
    
    def connect(self) -> bool:
        try:
            self.serial = serial.Serial(
                port=self.port,
                baudrate={config.get('baud_rate', 115200)},
                bytesize={config.get('data_bits', 8)},
                stopbits={config.get('stop_bits', 1)},
                parity='{config.get('parity', 'none')[0].upper()}',
                timeout={config.get('response_timeout', 1000) / 1000.0}
            )
            return True
        except Exception as e:
            print(f"Connection error: {{e}}")
            return False
    
    def send_command(self, command: str) -> Optional[str]:
        if not self.serial or not self.serial.is_open:
            return None
        
        try:
            # Send command with terminator
            terminator = config.get('command_terminator', '\\r\\n')
            full_command = command + terminator
            self.serial.write(full_command.encode())
            
            # Read response
            response = self.serial.readline().decode().strip()
            return response
        except Exception as e:
            print(f"Communication error: {e}")
            return None
    
    def disconnect(self):
        if self.serial and self.serial.is_open:
            self.serial.close()

# Usage example:
# driver = CustomSerialDriver('/dev/ttyUSB0')
# if driver.connect():
#     response = driver.send_command('STATUS')
#     print(f"Device response: {response}")
#     driver.disconnect()
"""
        elif protocol_type == "tcp":
            return f"""
import socket
import json
import struct
import time
from typing import Dict, Any, Optional

class CustomTCPDriver:
    def __init__(self, host: str, port: int = {config.get('port', 8080)}):
        self.host = host
        self.port = port
        self.socket = None
        self.config = {json.dumps(config, indent=8)}
    
    def connect(self) -> bool:
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout({config.get('timeout', 5000) / 1000.0})
            
            if {str(config.get('keepalive', True)).lower()}:
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            
            self.socket.connect((self.host, self.port))
            return True
        except Exception as e:
            print(f"Connection error: {{e}}")
            return False
    
    def send_message(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self.socket:
            return None
        
        try:
            # Serialize message
            message = json.dumps(data).encode('utf-8')
            
            # Send with header if configured
            header_size = {config.get('header_size', 0)}
            if header_size > 0:
                header = struct.pack('>I', len(message))
                self.socket.send(header + message)
            else:
                self.socket.send(message)
            
            # Receive response
            if header_size > 0:
                header_data = self.socket.recv(header_size)
                message_length = struct.unpack('>I', header_data)[0]
                response_data = self.socket.recv(message_length)
            else:
                response_data = self.socket.recv(4096)
            
            return json.loads(response_data.decode('utf-8'))
        except Exception as e:
            print(f"Communication error: {e}")
            return None
    
    def disconnect(self):
        if self.socket:
            self.socket.close()

# Usage example:
# driver = CustomTCPDriver('192.168.1.100')
# if driver.connect():
#     response = driver.send_message({{'command': 'status'}})
#     print(f"Device response: {response}")
#     driver.disconnect()
"""
        
        return "# Custom driver code generation not implemented for this protocol"
    
    def _generate_javascript_driver(self, protocol_type: str, config: Dict[str, Any]) -> str:
        """Generate JavaScript driver code"""
        return f"""
// Custom {protocol_type.upper()} Driver (JavaScript/Node.js)
// Configuration: {json.dumps(config, indent=2)}

const SerialPort = require('serialport');
const net = require('net');

class Custom{protocol_type.title()}Driver {{
    constructor(options) {{
        this.config = {json.dumps(config, indent=8)};
        this.connection = null;
    }}
    
    // Implementation specific to {protocol_type}
    // Add your custom logic here
}}

module.exports = Custom{protocol_type.title()}Driver;
"""
    
    def _generate_c_driver(self, protocol_type: str, config: Dict[str, Any]) -> str:
        """Generate C driver code"""
        return f"""
/*
 * Custom {protocol_type.upper()} Driver (C)
 * Configuration: {json.dumps(config, indent=4)}
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct {{
    // Add your device state variables here
    int connected;
    char address[256];
}} custom_{protocol_type}_device_t;

int custom_{protocol_type}_init(custom_{protocol_type}_device_t* device, const char* address) {{
    // Initialize device
    strcpy(device->address, address);
    device->connected = 0;
    return 0;
}}

int custom_{protocol_type}_connect(custom_{protocol_type}_device_t* device) {{
    // Implement connection logic
    device->connected = 1;
    return 0;
}}

int custom_{protocol_type}_disconnect(custom_{protocol_type}_device_t* device) {{
    // Implement disconnection logic
    device->connected = 0;
    return 0;
}}

// Add more functions as needed
"""

class TroubleshootingAssistant:
    def __init__(self):
        self.issue_database = {
            "connection_failed": {
                "description": "Device connection failed",
                "common_causes": [
                    "Incorrect cable connection",
                    "Wrong interface settings",
                    "Driver not installed",
                    "Port already in use",
                    "Power supply issue"
                ],
                "solutions": {
                    TroubleshootingLevel.BASIC: [
                        "Check all cable connections",
                        "Verify power supply is connected",
                        "Try a different USB/serial port",
                        "Restart the device"
                    ],
                    TroubleshootingLevel.INTERMEDIATE: [
                        "Check device manager for driver issues",
                        "Verify interface settings (baud rate, etc.)",
                        "Test with different cable",
                        "Check for resource conflicts"
                    ],
                    TroubleshootingLevel.ADVANCED: [
                        "Use oscilloscope to verify signal integrity",
                        "Check voltage levels on interface pins",
                        "Analyze communication protocol with logic analyzer",
                        "Review device datasheet for timing requirements"
                    ]
                }
            },
            "no_response": {
                "description": "Device connected but not responding",
                "common_causes": [
                    "Wrong protocol settings",
                    "Device in wrong mode",
                    "Timing issues",
                    "Command format incorrect"
                ],
                "solutions": {
                    TroubleshootingLevel.BASIC: [
                        "Verify device is powered on and ready",
                        "Check if device needs initialization sequence",
                        "Try different command format",
                        "Increase response timeout"
                    ],
                    TroubleshootingLevel.INTERMEDIATE: [
                        "Verify protocol settings match device requirements",
                        "Check device documentation for command format",
                        "Monitor communication with serial monitor",
                        "Test with manufacturer's software"
                    ],
                    TroubleshootingLevel.ADVANCED: [
                        "Analyze protocol timing with oscilloscope",
                        "Implement custom protocol analyzer",
                        "Check for hardware flow control issues",
                        "Review device firmware version compatibility"
                    ]
                }
            },
            "intermittent_errors": {
                "description": "Communication works sometimes but fails randomly",
                "common_causes": [
                    "Loose connections",
                    "EMI interference",
                    "Power supply noise",
                    "Buffer overflow",
                    "Timing races"
                ],
                "solutions": {
                    TroubleshootingLevel.BASIC: [
                        "Secure all connections",
                        "Move away from interference sources",
                        "Use shielded cables",
                        "Add ferrite beads to cables"
                    ],
                    TroubleshootingLevel.INTERMEDIATE: [
                        "Implement retry logic",
                        "Add error detection and correction",
                        "Use flow control",
                        "Monitor error patterns"
                    ],
                    TroubleshootingLevel.ADVANCED: [
                        "Analyze signal integrity",
                        "Implement robust error handling",
                        "Use protocol analyzers",
                        "Design custom filtering circuits"
                    ]
                }
            }
        }
    
    def diagnose_issue(self, symptoms: Dict[str, Any]) -> List[TroubleshootingSuggestion]:
        """Diagnose issues based on symptoms"""
        suggestions = []
        
        # Analyze symptoms and provide suggestions
        if symptoms.get("connection_status") == "failed":
            issue = self.issue_database["connection_failed"]
            for level in TroubleshootingLevel:
                suggestions.append(TroubleshootingSuggestion(
                    issue="Connection Failed",
                    level=level,
                    steps=issue["solutions"][level],
                    resources=[
                        "https://docs.activelog.ai/troubleshooting/connection",
                        "https://support.activelog.ai/connection-guide"
                    ],
                    estimated_time=5 * (level.value == "basic" and 1 or level.value == "intermediate" and 2 or 3)
                ))
        
        if symptoms.get("response_received") is False:
            issue = self.issue_database["no_response"]
            suggestions.append(TroubleshootingSuggestion(
                issue="No Response",
                level=TroubleshootingLevel.BASIC,
                steps=issue["solutions"][TroubleshootingLevel.BASIC],
                resources=[
                    "https://docs.activelog.ai/troubleshooting/no-response"
                ],
                estimated_time=10
            ))
        
        if symptoms.get("error_rate", 0) > 0.1:  # > 10% error rate
            issue = self.issue_database["intermittent_errors"]
            suggestions.append(TroubleshootingSuggestion(
                issue="Intermittent Errors",
                level=TroubleshootingLevel.INTERMEDIATE,
                steps=issue["solutions"][TroubleshootingLevel.INTERMEDIATE],
                resources=[
                    "https://docs.activelog.ai/troubleshooting/intermittent"
                ],
                estimated_time=15
            ))
        
        return suggestions
    
    def get_guided_solution(self, issue_type: str, level: TroubleshootingLevel) -> Dict[str, Any]:
        """Get guided troubleshooting solution"""
        if issue_type not in self.issue_database:
            return {"error": "Unknown issue type"}
        
        issue = self.issue_database[issue_type]
        
        return {
            "issue": issue_type,
            "description": issue["description"],
            "level": level.value,
            "steps": issue["solutions"][level],
            "common_causes": issue["common_causes"],
            "estimated_time": 5 * (level.value == "basic" and 1 or level.value == "intermediate" and 2 or 3),
            "next_steps": "If these steps don't resolve the issue, try the next difficulty level or contact support."
        }

class ManualConfigurationWizard:
    def __init__(self):
        self.sessions = {}
        self.community_drivers = CommunityDrivers()
        self.protocol_builder = ProtocolBuilder()
        self.troubleshooting = TroubleshootingAssistant()
        self.callbacks = {
            "step_completed": [],
            "validation_error": [],
            "session_completed": []
        }
        
        # Define wizard steps
        self.wizard_steps = self._initialize_wizard_steps()
    
    def _initialize_wizard_steps(self) -> Dict[WizardStep, WizardStepDefinition]:
        """Initialize wizard step definitions"""
        return {
            WizardStep.DEVICE_TYPE: WizardStepDefinition(
                step=WizardStep.DEVICE_TYPE,
                title="Device Type Selection",
                description="Select the type of device you want to configure",
                fields=[
                    {
                        "name": "category",
                        "type": "select",
                        "label": "Device Category",
                        "required": True,
                        "options": [
                            {"value": "sensor", "label": "Sensor Device"},
                            {"value": "actuator", "label": "Actuator/Motor"},
                            {"value": "controller", "label": "Microcontroller"},
                            {"value": "display", "label": "Display/Screen"},
                            {"value": "storage", "label": "Storage Device"},
                            {"value": "network", "label": "Network Device"},
                            {"value": "industrial", "label": "Industrial Equipment"},
                            {"value": "medical", "label": "Medical Device"},
                            {"value": "custom", "label": "Custom Device"}
                        ]
                    },
                    {
                        "name": "manufacturer",
                        "type": "text",
                        "label": "Manufacturer",
                        "placeholder": "e.g., Arduino, Raspberry Pi, Texas Instruments"
                    },
                    {
                        "name": "model",
                        "type": "text", 
                        "label": "Model Number",
                        "placeholder": "e.g., Uno R3, Zero 2W, TMP36"
                    },
                    {
                        "name": "description",
                        "type": "textarea",
                        "label": "Device Description",
                        "placeholder": "Brief description of what this device does"
                    }
                ],
                validations=[
                    {"field": "category", "type": "required", "message": "Device category is required"}
                ],
                help_content="""
                <h4>Choosing Device Category</h4>
                <p>Select the category that best describes your device:</p>
                <ul>
                    <li><strong>Sensor:</strong> Devices that measure physical properties (temperature, humidity, etc.)</li>
                    <li><strong>Actuator:</strong> Devices that control physical movement (motors, servos, etc.)</li>
                    <li><strong>Controller:</strong> Programmable devices (Arduino, Raspberry Pi, etc.)</li>
                    <li><strong>Display:</strong> Screens, LEDs, and visual output devices</li>
                    <li><strong>Storage:</strong> Memory cards, hard drives, and data storage</li>
                    <li><strong>Network:</strong> WiFi modules, Ethernet adapters, etc.</li>
                    <li><strong>Industrial:</strong> PLCs, SCADA devices, industrial sensors</li>
                    <li><strong>Medical:</strong> Medical instruments and monitoring devices</li>
                    <li><strong>Custom:</strong> Unique or specialized devices</li>
                </ul>
                """,
                troubleshooting_tips=[
                    "If unsure about category, choose 'Custom' and provide detailed description",
                    "Check device datasheet or manual for exact model number",
                    "Include firmware version if known"
                ],
                estimated_time=5
            ),
            
            WizardStep.CONNECTION: WizardStepDefinition(
                step=WizardStep.CONNECTION,
                title="Physical Connection",
                description="Configure how your device connects to the system",
                fields=[
                    {
                        "name": "interface_type",
                        "type": "select",
                        "label": "Connection Interface",
                        "required": True,
                        "options": [
                            {"value": "usb", "label": "USB"},
                            {"value": "serial", "label": "Serial/UART"},
                            {"value": "i2c", "label": "I2C"},
                            {"value": "spi", "label": "SPI"},
                            {"value": "ethernet", "label": "Ethernet"},
                            {"value": "wifi", "label": "WiFi"},
                            {"value": "bluetooth", "label": "Bluetooth"},
                            {"value": "can", "label": "CAN Bus"},
                            {"value": "modbus", "label": "Modbus"},
                            {"value": "custom", "label": "Custom Protocol"}
                        ]
                    },
                    {
                        "name": "connection_diagram",
                        "type": "image_upload",
                        "label": "Connection Diagram (Optional)",
                        "description": "Upload a photo or diagram of your connections"
                    },
                    {
                        "name": "power_source",
                        "type": "select",
                        "label": "Power Source",
                        "options": [
                            {"value": "usb", "label": "USB Power"},
                            {"value": "external_5v", "label": "External 5V"},
                            {"value": "external_3v3", "label": "External 3.3V"},
                            {"value": "external_12v", "label": "External 12V"},
                            {"value": "battery", "label": "Battery Powered"},
                            {"value": "poe", "label": "Power over Ethernet"}
                        ]
                    }
                ],
                validations=[
                    {"field": "interface_type", "type": "required", "message": "Connection interface is required"}
                ],
                help_content="""
                <h4>Connection Guide</h4>
                <div class="connection-guide">
                    <div class="interface-help">
                        <h5>Common Interfaces:</h5>
                        <ul>
                            <li><strong>USB:</strong> Plug-and-play, includes power</li>
                            <li><strong>Serial:</strong> TX/RX pins, common for microcontrollers</li>
                            <li><strong>I2C:</strong> SDA/SCL pins, multiple devices on same bus</li>
                            <li><strong>SPI:</strong> MOSI/MISO/SCK/CS pins, high-speed communication</li>
                            <li><strong>Ethernet:</strong> Network cable connection</li>
                            <li><strong>WiFi:</strong> Wireless network connection</li>
                        </ul>
                    </div>
                    <div class="wiring-tips">
                        <h5>Wiring Tips:</h5>
                        <ul>
                            <li>Double-check voltage levels (3.3V vs 5V)</li>
                            <li>Use pull-up resistors for I2C (4.7kΩ typical)</li>
                            <li>Keep wires short for high-speed signals</li>
                            <li>Use twisted pairs for differential signals</li>
                        </ul>
                    </div>
                </div>
                """,
                troubleshooting_tips=[
                    "Check voltage levels match between devices",
                    "Verify pin assignments in device datasheet",
                    "Use multimeter to check connections",
                    "Consider signal integrity for high-speed interfaces"
                ],
                estimated_time=15
            ),
            
            WizardStep.DRIVER_SELECTION: WizardStepDefinition(
                step=WizardStep.DRIVER_SELECTION,
                title="Driver Selection",
                description="Choose or create a driver for your device",
                fields=[
                    {
                        "name": "driver_source",
                        "type": "radio",
                        "label": "Driver Source",
                        "required": True,
                        "options": [
                            {"value": "auto", "label": "Automatic Detection"},
                            {"value": "community", "label": "Community Drivers"},
                            {"value": "custom", "label": "Custom Protocol"},
                            {"value": "upload", "label": "Upload Driver"}
                        ]
                    },
                    {
                        "name": "driver_language",
                        "type": "select",
                        "label": "Programming Language",
                        "options": [
                            {"value": "python", "label": "Python"},
                            {"value": "javascript", "label": "JavaScript/Node.js"},
                            {"value": "c", "label": "C/C++"},
                            {"value": "rust", "label": "Rust"}
                        ],
                        "default": "python"
                    }
                ],
                validations=[
                    {"field": "driver_source", "type": "required", "message": "Driver source selection is required"}
                ],
                help_content="""
                <h4>Driver Selection Guide</h4>
                <p>Choose the best driver source for your device:</p>
                <ul>
                    <li><strong>Automatic Detection:</strong> Let the system find the best driver</li>
                    <li><strong>Community Drivers:</strong> Browse user-contributed drivers</li>
                    <li><strong>Custom Protocol:</strong> Build your own protocol configuration</li>
                    <li><strong>Upload Driver:</strong> Use an existing driver file</li>
                </ul>
                """,
                troubleshooting_tips=[
                    "Try automatic detection first",
                    "Check community drivers for similar devices",
                    "Custom protocols work for unique communication needs"
                ],
                estimated_time=10
            )
        }
    
    def create_session(self, user_id: str, device_name: str) -> str:
        """Create new configuration session"""
        session_id = f"config_{uuid.uuid4().hex[:12]}"
        
        session = ManualConfigSession(
            session_id=session_id,
            user_id=user_id,
            device_name=device_name,
            current_step=WizardStep.DEVICE_TYPE,
            completed_steps=[],
            step_data={},
            validation_errors=[],
            created_at=datetime.now(),
            last_updated=datetime.now()
        )
        
        self.sessions[session_id] = session
        return session_id
    
    def get_session(self, session_id: str) -> Optional[ManualConfigSession]:
        """Get configuration session"""
        return self.sessions.get(session_id)
    
    def get_current_step(self, session_id: str) -> Optional[WizardStepDefinition]:
        """Get current wizard step definition"""
        session = self.get_session(session_id)
        if not session:
            return None
        
        return self.wizard_steps.get(session.current_step)
    
    def validate_step_data(self, session_id: str, step_data: Dict[str, Any]) -> List[ValidationError]:
        """Validate step data"""
        session = self.get_session(session_id)
        if not session:
            return [ValidationError("session", "Session not found", ValidationResult.INVALID)]
        
        step_def = self.get_current_step(session_id)
        if not step_def:
            return [ValidationError("step", "Step definition not found", ValidationResult.INVALID)]
        
        errors = []
        
        # Run field validations
        for validation in step_def.validations:
            field = validation["field"]
            validation_type = validation["type"]
            value = step_data.get(field)
            
            if validation_type == "required" and not value:
                errors.append(ValidationError(
                    field=field,
                    message=validation["message"],
                    severity=ValidationResult.INVALID,
                    suggestion=f"Please provide a value for {field}"
                ))
        
        # Custom validation logic
        if session.current_step == WizardStep.CONNECTION:
            interface_type = step_data.get("interface_type")
            if interface_type == "i2c" and not step_data.get("pullup_resistors"):
                errors.append(ValidationError(
                    field="pullup_resistors",
                    message="I2C requires pull-up resistors",
                    severity=ValidationResult.WARNING,
                    suggestion="Add 4.7kΩ pull-up resistors to SDA and SCL lines"
                ))
        
        return errors
    
    def submit_step(self, session_id: str, step_data: Dict[str, Any]) -> Dict[str, Any]:
        """Submit step data"""
        session = self.get_session(session_id)
        if not session:
            return {"success": False, "error": "Session not found"}
        
        # Validate data
        errors = self.validate_step_data(session_id, step_data)
        session.validation_errors = errors
        
        if any(error.severity == ValidationResult.INVALID for error in errors):
            return {
                "success": False,
                "errors": [asdict(error) for error in errors],
                "message": "Please fix validation errors before proceeding"
            }
        
        # Save step data
        session.step_data[session.current_step] = step_data
        session.completed_steps.append(session.current_step)
        session.last_updated = datetime.now()
        
        # Move to next step
        next_step = self._get_next_step(session.current_step, step_data)
        session.current_step = next_step
        
        # Trigger callbacks
        for callback in self.callbacks["step_completed"]:
            try:
                callback(session_id, session.current_step, step_data)
            except Exception as e:
                print(f"Step completed callback error: {e}")
        
        if next_step == WizardStep.COMPLETE:
            # Session completed
            for callback in self.callbacks["session_completed"]:
                try:
                    callback(session_id, session)
                except Exception as e:
                    print(f"Session completed callback error: {e}")
        
        return {
            "success": True,
            "next_step": next_step.value if next_step != WizardStep.COMPLETE else "complete",
            "warnings": [asdict(error) for error in errors if error.severity == ValidationResult.WARNING]
        }
    
    def _get_next_step(self, current_step: WizardStep, step_data: Dict[str, Any]) -> WizardStep:
        """Determine next step based on current step and data"""
        step_sequence = [
            WizardStep.DEVICE_TYPE,
            WizardStep.CONNECTION,
            WizardStep.INTERFACE_CONFIG,
            WizardStep.DRIVER_SELECTION,
            WizardStep.BASIC_CONFIG,
            WizardStep.ADVANCED_CONFIG,
            WizardStep.TESTING,
            WizardStep.CALIBRATION,
            WizardStep.FINALIZATION,
            WizardStep.COMPLETE
        ]
        
        try:
            current_index = step_sequence.index(current_step)
            
            # Skip steps based on conditions
            next_index = current_index + 1
            
            # Skip calibration for non-sensor devices
            if (step_sequence[next_index] == WizardStep.CALIBRATION and 
                step_data.get("category") != "sensor"):
                next_index += 1
            
            if next_index >= len(step_sequence):
                return WizardStep.COMPLETE
            
            return step_sequence[next_index]
            
        except ValueError:
            return WizardStep.COMPLETE
    
    def get_community_drivers(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search community drivers"""
        return self.community_drivers.search_drivers(query)
    
    def get_protocol_builder(self) -> ProtocolBuilder:
        """Get protocol builder instance"""
        return self.protocol_builder
    
    def get_troubleshooting_help(self, symptoms: Dict[str, Any]) -> List[TroubleshootingSuggestion]:
        """Get troubleshooting suggestions"""
        return self.troubleshooting.diagnose_issue(symptoms)
    
    def test_device_connection(self, session_id: str) -> Dict[str, Any]:
        """Test device connection"""
        session = self.get_session(session_id)
        if not session:
            return {"success": False, "error": "Session not found"}
        
        # Simulate connection test
        time.sleep(random.uniform(1.0, 3.0))
        
        success = random.random() > 0.2  # 80% success rate
        
        test_results = {
            "success": success,
            "connection_status": "connected" if success else "failed",
            "response_time_ms": random.uniform(10, 100) if success else None,
            "signal_quality": random.uniform(0.8, 1.0) if success else 0.0,
            "error_message": None if success else random.choice([
                "Device not responding",
                "Invalid baud rate",
                "Connection timeout",
                "Protocol mismatch"
            ])
        }
        
        if not success:
            # Provide troubleshooting suggestions
            symptoms = {
                "connection_status": "failed",
                "interface_type": session.step_data.get(WizardStep.CONNECTION, {}).get("interface_type")
            }
            suggestions = self.get_troubleshooting_help(symptoms)
            test_results["troubleshooting"] = [asdict(s) for s in suggestions[:3]]  # Top 3 suggestions
        
        return test_results
    
    def register_callback(self, event_type: str, callback: Callable):
        """Register event callback"""
        if event_type in self.callbacks:
            self.callbacks[event_type].append(callback)
    
    def export_configuration(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Export final configuration"""
        session = self.get_session(session_id)
        if not session or session.current_step != WizardStep.COMPLETE:
            return None
        
        return {
            "device_info": {
                "name": session.device_name,
                "category": session.step_data.get(WizardStep.DEVICE_TYPE, {}).get("category"),
                "manufacturer": session.step_data.get(WizardStep.DEVICE_TYPE, {}).get("manufacturer"),
                "model": session.step_data.get(WizardStep.DEVICE_TYPE, {}).get("model")
            },
            "connection": session.step_data.get(WizardStep.CONNECTION, {}),
            "interface_config": session.step_data.get(WizardStep.INTERFACE_CONFIG, {}),
            "driver": session.step_data.get(WizardStep.DRIVER_SELECTION, {}),
            "configuration": session.step_data.get(WizardStep.BASIC_CONFIG, {}),
            "advanced_config": session.step_data.get(WizardStep.ADVANCED_CONFIG, {}),
            "test_results": session.step_data.get(WizardStep.TESTING, {}),
            "calibration": session.step_data.get(WizardStep.CALIBRATION, {}),
            "session_info": {
                "session_id": session.session_id,
                "created_at": session.created_at.isoformat(),
                "completed_at": session.last_updated.isoformat(),
                "user_id": session.user_id
            }
        }

if __name__ == "__main__":
    print("Manual Configuration Wizard")
    print("=" * 50)
    
    async def demo():
        wizard = ManualConfigurationWizard()
        
        # Register callbacks
        def on_step_completed(session_id, step, data):
            print(f"✅ Step completed: {step.value}")
        
        def on_session_completed(session_id, session):
            print(f"🎉 Configuration completed for {session.device_name}!")
        
        wizard.register_callback("step_completed", on_step_completed)
        wizard.register_callback("session_completed", on_session_completed)
        
        # Create configuration session
        session_id = wizard.create_session("user123", "My Arduino Sensor")
        print(f"Created session: {session_id}")
        
        # Step 1: Device Type
        step_def = wizard.get_current_step(session_id)
        print(f"\nCurrent step: {step_def.title}")
        print(f"Description: {step_def.description}")
        
        step1_data = {
            "category": "sensor",
            "manufacturer": "Arduino",
            "model": "Uno R3",
            "description": "Temperature and humidity sensor"
        }
        
        result = wizard.submit_step(session_id, step1_data)
        print(f"Step 1 result: {result}")
        
        # Step 2: Connection
        step2_data = {
            "interface_type": "serial",
            "power_source": "usb"
        }
        
        result = wizard.submit_step(session_id, step2_data)
        print(f"Step 2 result: {result}")
        
        # Demonstrate community driver search
        print(f"\n--- Community Drivers ---")
        drivers = wizard.get_community_drivers({"device_type": "sensor", "interface": "serial"})
        for driver in drivers[:3]:  # Show first 3
            print(f"  {driver['name']} v{driver['version']} by {driver['author']}")
            print(f"    Rating: {driver['rating']}/5.0, Downloads: {driver['downloads']}")
        
        # Demonstrate protocol builder
        print(f"\n--- Custom Protocol Builder ---")
        protocol_builder = wizard.get_protocol_builder()
        template = protocol_builder.get_protocol_template("serial")
        print(f"Serial protocol template has {len(template.get('fields', []))} configuration fields")
        
        # Generate driver code
        config = {"baud_rate": 115200, "data_bits": 8, "command_terminator": "\\r\\n"}
        driver_code = protocol_builder.generate_driver_code("serial", config, "python")
        print(f"Generated driver code: {len(driver_code)} characters")
        
        # Test connection
        print(f"\n--- Connection Test ---")
        test_result = wizard.test_device_connection(session_id)
        print(f"Connection test: {'✅ Success' if test_result['success'] else '❌ Failed'}")
        
        if not test_result['success']:
            print("Troubleshooting suggestions:")
            for suggestion in test_result.get('troubleshooting', []):
                print(f"  - {suggestion['issue']}: {len(suggestion['steps'])} steps")
        
        # Show session status
        session = wizard.get_session(session_id)
        print(f"\n--- Session Status ---")
        print(f"Current step: {session.current_step.value}")
        print(f"Completed steps: {[s.value for s in session.completed_steps]}")
        print(f"Last updated: {session.last_updated}")
        
        print("\nManual configuration wizard demo completed")
    
    asyncio.run(demo())