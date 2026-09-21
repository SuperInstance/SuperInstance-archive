"""
ESP32/ESP8266 Specialized Code Generator
"""

import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..database import DeviceType, Device, CodeGeneration
from ..nlp.code_generator import ArduinoCodeGenerator


class ESPCodeGenerator(ArduinoCodeGenerator):
    """Specialized code generator for ESP32 and ESP8266 devices"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session)
        
        # ESP-specific configurations
        self.esp32_config = {
            "cpu_frequencies": [80, 160, 240],
            "wifi_modes": ["STA", "AP", "STA+AP"],
            "bluetooth_modes": ["classic", "ble", "both"],
            "deep_sleep_pins": [0, 2, 4, 12, 13, 14, 15, 25, 26, 27, 32, 33],
            "adc_pins": [32, 33, 34, 35, 36, 37, 38, 39],
            "dac_pins": [25, 26],
            "touch_pins": [0, 2, 4, 12, 13, 14, 15, 27, 32, 33]
        }
        
        self.esp8266_config = {
            "cpu_frequencies": [80, 160],
            "wifi_modes": ["STA", "AP", "STA+AP"],
            "deep_sleep_pin": 16,
            "adc_pin": 0
        }
        
        # ESP-specific libraries and frameworks
        self.esp_libraries = {
            "wifi_manager": ["WiFiManager.h"],
            "web_server": ["WebServer.h", "ESPAsyncWebServer.h"],
            "mqtt": ["PubSubClient.h", "AsyncMqttClient.h"],
            "ota_updates": ["ArduinoOTA.h", "HTTPUpdate.h"],
            "file_system": ["SPIFFS.h", "LittleFS.h", "SD.h"],
            "json": ["ArduinoJson.h"],
            "time": ["time.h", "NTPClient.h"],
            "deep_sleep": ["esp_sleep.h"],
            "preferences": ["Preferences.h"],
            "bluetooth_serial": ["BluetoothSerial.h"],
            "ble": ["BLEDevice.h", "BLEServer.h", "BLEClient.h"]
        }
        
        # IoT platform integrations
        self.iot_platforms = {
            "activelog": {
                "endpoint": "https://api.activelog.com/iot",
                "headers": ["Authorization", "Content-Type"],
                "payload_format": "json"
            },
            "aws_iot": {
                "endpoint": "https://iot.amazonaws.com",
                "libraries": ["WiFiClientSecure.h", "MQTTClient.h"]
            },
            "azure_iot": {
                "endpoint": "https://azure-devices.net",
                "libraries": ["AzureIoTHub.h", "AzureIoTProtocol_HTTPS.h"]
            },
            "google_iot": {
                "endpoint": "https://cloudiot-device.googleapis.com",
                "libraries": ["CloudIoTCore.h", "WiFiClientSecure.h"]
            }
        }
    
    async def generate_esp_code(
        self,
        user_id: uuid.UUID,
        natural_language: str,
        device_type: DeviceType,
        esp_config: Optional[Dict[str, Any]] = None,
        iot_integration: Optional[str] = None,
        device_id: Optional[uuid.UUID] = None
    ) -> uuid.UUID:
        """Generate ESP32/ESP8266 specific code"""
        
        if device_type not in [DeviceType.ESP32, DeviceType.ESP8266]:
            raise ValueError(f"Device type {device_type} is not supported by ESPCodeGenerator")
        
        # Parse requirements with ESP-specific enhancements
        requirements = await self._parse_requirements(natural_language)
        
        # Add ESP-specific requirements
        await self._enhance_esp_requirements(requirements, device_type, esp_config, iot_integration)
        
        # Generate code using parent class with ESP enhancements
        generation_id = await self.generate_code_from_nl(
            user_id, natural_language, device_type, device_id
        )
        
        return generation_id
    
    async def _enhance_esp_requirements(
        self,
        requirements: Dict[str, Any],
        device_type: DeviceType,
        esp_config: Optional[Dict[str, Any]],
        iot_integration: Optional[str]
    ):
        """Enhance requirements with ESP-specific features"""
        
        # Add WiFi if not explicitly mentioned but IoT integration requested
        if iot_integration and "wifi" not in requirements["communication"]:
            requirements["communication"].append("wifi")
            requirements["libraries"].update(["WiFi.h"])
        
        # Add ESP-specific libraries based on requirements
        if "wifi" in requirements["communication"]:
            requirements["libraries"].update(["WiFi.h"])
            if esp_config and esp_config.get("wifi_manager"):
                requirements["libraries"].update(self.esp_libraries["wifi_manager"])
        
        if "web_server" in requirements.get("features", []):
            requirements["libraries"].update(self.esp_libraries["web_server"])
        
        if "mqtt" in requirements.get("protocols", []):
            requirements["libraries"].update(self.esp_libraries["mqtt"])
        
        if "ota" in requirements.get("features", []):
            requirements["libraries"].update(self.esp_libraries["ota_updates"])
        
        if "file_storage" in requirements.get("features", []):
            requirements["libraries"].update(self.esp_libraries["file_system"])
        
        # Add IoT platform specific requirements
        if iot_integration and iot_integration in self.iot_platforms:
            platform = self.iot_platforms[iot_integration]
            if "libraries" in platform:
                requirements["libraries"].update(platform["libraries"])
            requirements["iot_platform"] = iot_integration
        
        # Add power management features
        if "power_saving" in requirements.get("features", []):
            requirements["libraries"].update(self.esp_libraries["deep_sleep"])
            requirements["power_management"] = True
        
        # Store ESP config
        requirements["esp_config"] = esp_config or {}
    
    def _generate_esp_includes(self, requirements: Dict[str, Any]) -> str:
        """Generate ESP-specific includes"""
        includes = []
        
        # Standard ESP includes
        for library in sorted(requirements["libraries"]):
            includes.append(f"#include <{library}>")
        
        # Add conditional includes
        if requirements.get("iot_platform") == "activelog":
            includes.extend([
                "#include <HTTPClient.h>",
                "#include <ArduinoJson.h>"
            ])
        
        return "\n".join(includes) if includes else ""
    
    def _generate_esp_globals(
        self,
        requirements: Dict[str, Any],
        device_type: DeviceType
    ) -> str:
        """Generate ESP-specific global variables"""
        globals_lines = []
        
        # WiFi credentials
        if "wifi" in requirements["communication"]:
            globals_lines.extend([
                'const char* ssid = "YOUR_WIFI_SSID";',
                'const char* password = "YOUR_WIFI_PASSWORD";'
            ])
        
        # Web server
        if "web_server" in requirements.get("features", []):
            globals_lines.append("WebServer server(80);")
        
        # MQTT client
        if "mqtt" in requirements.get("protocols", []):
            globals_lines.extend([
                "WiFiClient espClient;",
                "PubSubClient client(espClient);",
                'const char* mqtt_server = "your.mqtt.broker.com";'
            ])
        
        # IoT platform configuration
        if requirements.get("iot_platform") == "activelog":
            globals_lines.extend([
                'const char* activelog_endpoint = "https://api.activelog.com/iot/data";',
                'const char* device_token = "YOUR_DEVICE_TOKEN";'
            ])
        
        # Sensor variables (call parent method and extend)
        parent_globals = super()._generate_globals(
            requirements, 
            self.device_specifications[device_type]
        )
        
        if parent_globals:
            globals_lines.append(parent_globals)
        
        return "\n".join(globals_lines)
    
    def _generate_esp_setup(
        self,
        requirements: Dict[str, Any],
        device_type: DeviceType
    ) -> str:
        """Generate ESP-specific setup function"""
        setup_lines = [
            "void setup() {",
            "  Serial.begin(115200);",
            "  delay(1000);"
        ]
        
        # WiFi initialization
        if "wifi" in requirements["communication"]:
            setup_lines.extend([
                "  // Connect to WiFi",
                "  WiFi.begin(ssid, password);",
                "  Serial.print(\"Connecting to WiFi\");",
                "  while (WiFi.status() != WL_CONNECTED) {",
                "    delay(500);",
                "    Serial.print(\".\");",
                "  }",
                "  Serial.println();",
                "  Serial.println(\"WiFi connected!\");",
                "  Serial.print(\"IP address: \");",
                "  Serial.println(WiFi.localIP());"
            ])
        
        # Web server setup
        if "web_server" in requirements.get("features", []):
            setup_lines.extend([
                "  // Setup web server routes",
                "  server.on(\"/\", handleRoot);",
                "  server.on(\"/data\", handleData);",
                "  server.begin();",
                "  Serial.println(\"Web server started\");"
            ])
        
        # MQTT setup
        if "mqtt" in requirements.get("protocols", []):
            setup_lines.extend([
                "  client.setServer(mqtt_server, 1883);",
                "  client.setCallback(callback);"
            ])
        
        # OTA setup
        if "ota" in requirements.get("features", []):
            setup_lines.extend([
                "  // Setup OTA",
                "  ArduinoOTA.setHostname(\"esp-device\");",
                "  ArduinoOTA.begin();",
                "  Serial.println(\"OTA ready\");"
            ])
        
        # File system initialization
        if "file_storage" in requirements.get("features", []):
            setup_lines.extend([
                "  // Initialize SPIFFS",
                "  if (!SPIFFS.begin(true)) {",
                "    Serial.println(\"SPIFFS Mount Failed\");",
                "  }"
            ])
        
        # Sensor initialization (call parent method)
        parent_setup = super()._generate_setup(requirements, device_type)
        sensor_init = "\n".join(parent_setup.split("\n")[2:-1])  # Remove function wrapper
        if sensor_init.strip():
            setup_lines.append(sensor_init)
        
        setup_lines.extend([
            "  Serial.println(\"Setup complete!\");",
            "}"
        ])
        
        return "\n".join(setup_lines)
    
    def _generate_esp_loop(self, requirements: Dict[str, Any]) -> str:
        """Generate ESP-specific loop function"""
        loop_lines = [
            "void loop() {"
        ]
        
        # Handle web server
        if "web_server" in requirements.get("features", []):
            loop_lines.append("  server.handleClient();")
        
        # Handle OTA updates
        if "ota" in requirements.get("features", []):
            loop_lines.append("  ArduinoOTA.handle();")
        
        # MQTT keep alive
        if "mqtt" in requirements.get("protocols", []):
            loop_lines.extend([
                "  if (!client.connected()) {",
                "    reconnectMQTT();",
                "  }",
                "  client.loop();"
            ])
        
        # Sensor reading and data transmission
        if "read_sensor" in requirements["functions"]:
            loop_lines.append("  // Read sensors")
            
            # Add parent sensor reading logic
            parent_loop = super()._generate_loop(requirements)
            sensor_code = "\n".join(parent_loop.split("\n")[1:-2])  # Extract sensor code
            loop_lines.append(sensor_code)
            
            # Send data to IoT platform
            if requirements.get("iot_platform") == "activelog":
                loop_lines.extend([
                    "  // Send data to ActiveLog",
                    "  sendToActiveLog();"
                ])
        
        # Power management
        if requirements.get("power_management"):
            esp_config = requirements.get("esp_config", {})
            sleep_time = esp_config.get("sleep_time", 10)  # seconds
            
            loop_lines.extend([
                f"  // Deep sleep for {sleep_time} seconds",
                f"  esp_sleep_enable_timer_wakeup({sleep_time} * 1000000);",
                "  esp_deep_sleep_start();"
            ])
        else:
            loop_lines.append("  delay(5000);")
        
        loop_lines.append("}")
        
        return "\n".join(loop_lines)
    
    def _generate_esp_helper_functions(self, requirements: Dict[str, Any]) -> str:
        """Generate ESP-specific helper functions"""
        helpers = []
        
        # Web server handlers
        if "web_server" in requirements.get("features", []):
            helpers.append("""
void handleRoot() {
  String html = "<h1>ESP Device</h1>";
  html += "<p><a href='/data'>View Sensor Data</a></p>";
  server.send(200, "text/html", html);
}

void handleData() {
  String json = "{";
  // Add sensor data to JSON
  json += "}";
  server.send(200, "application/json", json);
}""")
        
        # MQTT functions
        if "mqtt" in requirements.get("protocols", []):
            helpers.append("""
void callback(char* topic, byte* payload, unsigned int length) {
  Serial.print("Message arrived [");
  Serial.print(topic);
  Serial.print("] ");
  for (int i = 0; i < length; i++) {
    Serial.print((char)payload[i]);
  }
  Serial.println();
}

void reconnectMQTT() {
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    if (client.connect("ESPClient")) {
      Serial.println("connected");
      client.subscribe("device/command");
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");
      delay(5000);
    }
  }
}""")
        
        # ActiveLog integration
        if requirements.get("iot_platform") == "activelog":
            helpers.append("""
void sendToActiveLog() {
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(activelog_endpoint);
    http.addHeader("Content-Type", "application/json");
    http.addHeader("Authorization", "Bearer " + String(device_token));
    
    // Create JSON payload
    String payload = "{";
    payload += "\\"device_id\\": \\"" + WiFi.macAddress() + "\\",";
    payload += "\\"timestamp\\": " + String(millis()) + ",";
    payload += "\\"data\\": {";
    // Add sensor data
    payload += "}";
    payload += "}";
    
    int httpResponseCode = http.POST(payload);
    
    if (httpResponseCode > 0) {
      String response = http.getString();
      Serial.println("Data sent to ActiveLog: " + response);
    } else {
      Serial.println("Error sending data: " + String(httpResponseCode));
    }
    
    http.end();
  }
}""")
        
        # Power management functions
        if requirements.get("power_management"):
            helpers.append("""
void enterDeepSleep(int seconds) {
  Serial.println("Entering deep sleep for " + String(seconds) + " seconds");
  esp_sleep_enable_timer_wakeup(seconds * 1000000);
  esp_deep_sleep_start();
}""")
        
        return "\n".join(helpers) if helpers else ""
    
    async def _generate_arduino_code(
        self,
        requirements: Dict[str, Any],
        device_type: DeviceType
    ) -> str:
        """Override parent method with ESP-specific generation"""
        
        code_parts = []
        
        # Generate includes
        includes = self._generate_esp_includes(requirements)
        if includes:
            code_parts.append(includes)
        
        # Generate globals
        globals_section = self._generate_esp_globals(requirements, device_type)
        if globals_section:
            code_parts.append(globals_section)
        
        # Generate setup
        setup_section = self._generate_esp_setup(requirements, device_type)
        code_parts.append(setup_section)
        
        # Generate loop
        loop_section = self._generate_esp_loop(requirements)
        code_parts.append(loop_section)
        
        # Generate helpers
        helpers = self._generate_esp_helper_functions(requirements)
        if helpers:
            code_parts.append(helpers)
        
        return "\n\n".join(code_parts)
    
    async def generate_iot_integration_code(
        self,
        user_id: uuid.UUID,
        device_id: uuid.UUID,
        platform: str,
        config: Dict[str, Any]
    ) -> str:
        """Generate IoT platform integration code"""
        
        device = await self.session.execute(
            select(Device).where(Device.id == device_id)
        )
        device = device.scalar_one_or_none()
        
        if not device:
            raise ValueError(f"Device {device_id} not found")
        
        if device.device_type not in [DeviceType.ESP32, DeviceType.ESP8266]:
            raise ValueError("IoT integration only supported for ESP devices")
        
        # Generate platform-specific integration code
        if platform == "activelog":
            return await self._generate_activelog_integration(device, config)
        elif platform == "aws_iot":
            return await self._generate_aws_iot_integration(device, config)
        elif platform == "azure_iot":
            return await self._generate_azure_iot_integration(device, config)
        else:
            raise ValueError(f"Unsupported IoT platform: {platform}")
    
    async def _generate_activelog_integration(
        self,
        device: Device,
        config: Dict[str, Any]
    ) -> str:
        """Generate ActiveLog specific integration code"""
        
        template = f"""
// ActiveLog IoT Integration for {device.name}
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

const char* activelog_endpoint = "{config.get('endpoint', 'https://api.activelog.com/iot/data')}";
const char* device_token = "{config.get('device_token', 'YOUR_DEVICE_TOKEN')}";
const char* device_id = "{device.id}";

void sendToActiveLog(JsonObject& sensorData) {{
  if (WiFi.status() == WL_CONNECTED) {{
    HTTPClient http;
    http.begin(activelog_endpoint);
    http.addHeader("Content-Type", "application/json");
    http.addHeader("Authorization", "Bearer " + String(device_token));
    
    DynamicJsonDocument doc(1024);
    doc["device_id"] = device_id;
    doc["timestamp"] = millis();
    doc["data"] = sensorData;
    
    String payload;
    serializeJson(doc, payload);
    
    int httpResponseCode = http.POST(payload);
    
    if (httpResponseCode == 200) {{
      String response = http.getString();
      Serial.println("✓ Data sent to ActiveLog: " + response);
    }} else {{
      Serial.println("✗ Error sending data: " + String(httpResponseCode));
    }}
    
    http.end();
  }} else {{
    Serial.println("✗ WiFi not connected");
  }}
}}
"""
        return template.strip()
    
    async def _generate_aws_iot_integration(
        self,
        device: Device,
        config: Dict[str, Any]
    ) -> str:
        """Generate AWS IoT Core integration code"""
        
        template = f"""
// AWS IoT Core Integration for {device.name}
#include <WiFiClientSecure.h>
#include <MQTTClient.h>
#include <ArduinoJson.h>

const char* aws_iot_endpoint = "{config.get('endpoint', 'your-endpoint.iot.region.amazonaws.com')}";
const char* thing_name = "{device.name}";
const char* shadow_update_topic = "$aws/things/{device.name}/shadow/update";

WiFiClientSecure net = WiFiClientSecure();
MQTTClient client = MQTTClient(256);

void connectToAWS() {{
  net.setCACert(AWS_CERT_CA);
  net.setCertificate(AWS_CERT_CRT);
  net.setPrivateKey(AWS_CERT_PRIVATE);
  
  client.begin(aws_iot_endpoint, 8883, net);
  
  Serial.print("Connecting to AWS IoT");
  while (!client.connect(thing_name)) {{
    Serial.print(".");
    delay(100);
  }}
  
  if (!client.connected()) {{
    Serial.println("AWS IoT Timeout!");
    return;
  }}
  
  Serial.println("AWS IoT Connected!");
}}

void publishToAWS(JsonObject& sensorData) {{
  DynamicJsonDocument doc(1024);
  doc["state"]["reported"] = sensorData;
  
  char jsonBuffer[512];
  serializeJson(doc, jsonBuffer);
  
  client.publish(shadow_update_topic, jsonBuffer);
}}
"""
        return template.strip()
    
    async def _generate_azure_iot_integration(
        self,
        device: Device,
        config: Dict[str, Any]
    ) -> str:
        """Generate Azure IoT Hub integration code"""
        
        template = f"""
// Azure IoT Hub Integration for {device.name}
#include <WiFiClientSecure.h>
#include <ArduinoJson.h>

const char* azure_iot_hub = "{config.get('iot_hub', 'your-hub.azure-devices.net')}";
const char* device_id = "{device.id}";
const char* device_key = "{config.get('device_key', 'YOUR_DEVICE_KEY')}";

void sendToAzure(JsonObject& sensorData) {{
  // Azure IoT Hub requires SAS token authentication
  // Implementation would include SAS token generation and MQTT connection
  
  DynamicJsonDocument doc(1024);
  doc["deviceId"] = device_id;
  doc["timestamp"] = millis();
  doc["telemetry"] = sensorData;
  
  String payload;
  serializeJson(doc, payload);
  
  // Send via HTTPS or MQTT to Azure IoT Hub
  Serial.println("Sending to Azure IoT Hub: " + payload);
}}
"""
        return template.strip()