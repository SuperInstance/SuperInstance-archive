"""
Device Provisioning with ActiveLog Account Integration
"""

import uuid
import jwt
import hashlib
import secrets
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import asyncio
import aiohttp
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from cryptography.fernet import Fernet

from ..database import Device, User, DeviceType, DeviceStatus


class ActiveLogProvisioning:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.activelog_api_base = "https://api.activelog.com/v1"
        self.device_registry_endpoint = f"{self.activelog_api_base}/devices"
        self.user_auth_endpoint = f"{self.activelog_api_base}/auth"
        
        # Generate or load encryption key for device secrets
        self.encryption_key = self._get_or_create_encryption_key()
        self.cipher_suite = Fernet(self.encryption_key)
        
        # Provisioning templates for different device types
        self.provisioning_templates = {
            DeviceType.ESP32: {
                "firmware_template": "esp32_activelog_base.bin",
                "required_libraries": ["WiFi.h", "HTTPClient.h", "ArduinoJson.h", "ActiveLogSDK.h"],
                "memory_requirements": {"flash": 1024, "ram": 256},
                "default_config": {
                    "reporting_interval": 300,  # 5 minutes
                    "batch_size": 10,
                    "retry_attempts": 3,
                    "deep_sleep_enabled": True
                }
            },
            DeviceType.ESP8266: {
                "firmware_template": "esp8266_activelog_base.bin",
                "required_libraries": ["ESP8266WiFi.h", "ESP8266HTTPClient.h", "ArduinoJson.h", "ActiveLogSDK.h"],
                "memory_requirements": {"flash": 512, "ram": 64},
                "default_config": {
                    "reporting_interval": 600,  # 10 minutes
                    "batch_size": 5,
                    "retry_attempts": 2,
                    "deep_sleep_enabled": True
                }
            },
            DeviceType.ARDUINO_UNO: {
                "firmware_template": "arduino_activelog_bridge.ino",
                "required_libraries": ["SoftwareSerial.h", "ActiveLogBridge.h"],
                "memory_requirements": {"flash": 32, "ram": 2},
                "default_config": {
                    "reporting_interval": 1800,  # 30 minutes
                    "batch_size": 3,
                    "retry_attempts": 1,
                    "bridge_mode": "serial"  # Requires WiFi bridge device
                }
            }
        }
    
    def _get_or_create_encryption_key(self) -> bytes:
        """Get or create encryption key for device secrets"""
        key_file = "/tmp/edge_programmer_key"
        
        try:
            with open(key_file, 'rb') as f:
                return f.read()
        except FileNotFoundError:
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            return key
    
    async def provision_device(
        self,
        user_id: uuid.UUID,
        device_name: str,
        device_type: DeviceType,
        mac_address: Optional[str] = None,
        location: Optional[str] = None,
        custom_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Provision a new device with ActiveLog account"""
        
        # Get user information
        user = await self._get_user(user_id)
        if not user:
            raise Exception(f"User {user_id} not found")
        
        # Validate user's ActiveLog account
        if not user.activelog_account_id:
            raise Exception("User must have an ActiveLog account to provision devices")
        
        # Generate device credentials
        device_credentials = await self._generate_device_credentials(device_name, device_type)
        
        # Register device with ActiveLog platform
        activelog_device = await self._register_with_activelog(
            user, device_name, device_type, device_credentials, mac_address, location
        )
        
        # Create device record in local database
        device = Device(
            name=device_name,
            device_type=device_type,
            mac_address=mac_address,
            status=DeviceStatus.PROVISIONING,
            location=location,
            metadata={
                "activelog_device_id": activelog_device["device_id"],
                "provisioning_date": datetime.utcnow().isoformat(),
                "custom_config": custom_config or {}
            },
            owner_id=user_id
        )
        
        self.session.add(device)
        await self.session.commit()
        await self.session.refresh(device)
        
        # Generate provisioning package
        provisioning_package = await self._create_provisioning_package(
            device, device_credentials, activelog_device
        )
        
        # Update device status
        await self.session.execute(
            update(Device)
            .where(Device.id == device.id)
            .values(status=DeviceStatus.OFFLINE)  # Ready to come online
        )
        await self.session.commit()
        
        return {
            "device_id": str(device.id),
            "activelog_device_id": activelog_device["device_id"],
            "provisioning_package": provisioning_package,
            "status": "provisioned"
        }
    
    async def _get_user(self, user_id: uuid.UUID) -> Optional[User]:
        """Get user from database"""
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def _generate_device_credentials(
        self,
        device_name: str,
        device_type: DeviceType
    ) -> Dict[str, str]:
        """Generate secure credentials for device"""
        
        # Generate device-specific credentials
        device_id = str(uuid.uuid4())
        device_secret = secrets.token_urlsafe(32)
        api_key = secrets.token_urlsafe(16)
        
        # Create device certificate (simplified)
        certificate_data = {
            "device_id": device_id,
            "device_name": device_name,
            "device_type": device_type.value,
            "issued_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(days=365)).isoformat()
        }
        
        # Sign certificate with our key (in production, use proper PKI)
        certificate = jwt.encode(certificate_data, device_secret, algorithm="HS256")
        
        return {
            "device_id": device_id,
            "device_secret": device_secret,
            "api_key": api_key,
            "certificate": certificate
        }
    
    async def _register_with_activelog(
        self,
        user: User,
        device_name: str,
        device_type: DeviceType,
        credentials: Dict[str, str],
        mac_address: Optional[str],
        location: Optional[str]
    ) -> Dict[str, Any]:
        """Register device with ActiveLog platform"""
        
        registration_data = {
            "device_name": device_name,
            "device_type": device_type.value,
            "device_id": credentials["device_id"],
            "mac_address": mac_address,
            "location": location,
            "owner_account_id": user.activelog_account_id,
            "capabilities": self._get_device_capabilities(device_type),
            "metadata": {
                "provisioned_via": "edge-programmer",
                "provisioned_at": datetime.utcnow().isoformat()
            }
        }
        
        headers = {
            "Authorization": f"Bearer {user.api_key}",
            "Content-Type": "application/json"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.device_registry_endpoint,
                json=registration_data,
                headers=headers
            ) as response:
                if response.status == 201:
                    return await response.json()
                else:
                    error_msg = await response.text()
                    raise Exception(f"Failed to register device with ActiveLog: {error_msg}")
    
    def _get_device_capabilities(self, device_type: DeviceType) -> List[str]:
        """Get capabilities for device type"""
        
        base_capabilities = ["telemetry", "command_response", "status_reporting"]
        
        if device_type in [DeviceType.ESP32, DeviceType.ESP8266]:
            return base_capabilities + [
                "wifi_connectivity",
                "ota_updates",
                "web_server",
                "mqtt_client",
                "https_client",
                "deep_sleep",
                "sensor_data_collection"
            ]
        elif device_type in [DeviceType.ARDUINO_UNO, DeviceType.ARDUINO_NANO, DeviceType.ARDUINO_MEGA]:
            return base_capabilities + [
                "serial_communication",
                "sensor_data_collection",
                "bridge_mode"
            ]
        else:
            return base_capabilities
    
    async def _create_provisioning_package(
        self,
        device: Device,
        credentials: Dict[str, str],
        activelog_device: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create complete provisioning package for device"""
        
        template = self.provisioning_templates.get(device.device_type)
        if not template:
            raise Exception(f"No provisioning template for {device.device_type}")
        
        # Generate device configuration
        device_config = {
            "device_id": credentials["device_id"],
            "device_name": device.name,
            "activelog_device_id": activelog_device["device_id"],
            "activelog_endpoint": self.activelog_api_base,
            "api_key": credentials["api_key"],
            **template["default_config"],
            **device.metadata.get("custom_config", {})
        }
        
        # Encrypt sensitive data
        encrypted_secret = self.cipher_suite.encrypt(credentials["device_secret"].encode())
        encrypted_api_key = self.cipher_suite.encrypt(credentials["api_key"].encode())
        
        # Generate firmware configuration
        firmware_config = await self._generate_firmware_config(device, device_config)
        
        # Create provisioning code
        provisioning_code = await self._generate_provisioning_code(device, device_config)
        
        return {
            "device_config": device_config,
            "encrypted_credentials": {
                "device_secret": encrypted_secret.decode(),
                "api_key": encrypted_api_key.decode()
            },
            "firmware_config": firmware_config,
            "provisioning_code": provisioning_code,
            "required_libraries": template["required_libraries"],
            "setup_instructions": self._generate_setup_instructions(device.device_type)
        }
    
    async def _generate_firmware_config(
        self,
        device: Device,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate firmware-specific configuration"""
        
        if device.device_type in [DeviceType.ESP32, DeviceType.ESP8266]:
            return {
                "wifi_config": {
                    "ssid": "CONFIGURE_WIFI_SSID",
                    "password": "CONFIGURE_WIFI_PASSWORD",
                    "timeout": 30000,
                    "retry_attempts": 5
                },
                "activelog_config": {
                    "endpoint": config["activelog_endpoint"],
                    "device_id": config["device_id"],
                    "reporting_interval": config["reporting_interval"] * 1000,  # Convert to ms
                    "batch_size": config["batch_size"],
                    "retry_attempts": config["retry_attempts"]
                },
                "power_config": {
                    "deep_sleep_enabled": config.get("deep_sleep_enabled", True),
                    "sleep_duration": config.get("sleep_duration", 300),  # 5 minutes
                    "wake_on_sensor": True
                },
                "security_config": {
                    "use_https": True,
                    "verify_certificates": True,
                    "encryption_enabled": True
                }
            }
        else:
            # Arduino devices with bridge mode
            return {
                "bridge_config": {
                    "serial_baud": 115200,
                    "bridge_device_type": "esp32",
                    "command_timeout": 5000
                },
                "activelog_config": {
                    "device_id": config["device_id"],
                    "reporting_interval": config["reporting_interval"] * 1000
                }
            }
    
    async def _generate_provisioning_code(
        self,
        device: Device,
        config: Dict[str, Any]
    ) -> str:
        """Generate Arduino code for device provisioning"""
        
        if device.device_type == DeviceType.ESP32:
            return self._generate_esp32_provisioning_code(config)
        elif device.device_type == DeviceType.ESP8266:
            return self._generate_esp8266_provisioning_code(config)
        else:
            return self._generate_arduino_provisioning_code(config)
    
    def _generate_esp32_provisioning_code(self, config: Dict[str, Any]) -> str:
        """Generate ESP32-specific provisioning code"""
        
        return f"""
// ActiveLog Edge Programmer - ESP32 Provisioning Code
// Generated on {datetime.utcnow().isoformat()}

#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <Preferences.h>
#include <esp_sleep.h>

// Device Configuration
const char* DEVICE_ID = "{config['device_id']}";
const char* ACTIVELOG_ENDPOINT = "{config['activelog_endpoint']}";
const int REPORTING_INTERVAL = {config['reporting_interval']} * 1000;
const int BATCH_SIZE = {config['batch_size']};
const bool DEEP_SLEEP_ENABLED = {"true" if config.get('deep_sleep_enabled') else "false"};

// WiFi Configuration (to be set via WiFi Manager or web interface)
String wifi_ssid = "";
String wifi_password = "";
String api_key = "";

Preferences preferences;
HTTPClient http;

void setup() {{
  Serial.begin(115200);
  Serial.println("ActiveLog Edge Device Starting...");
  
  // Initialize preferences
  preferences.begin("activelog", false);
  
  // Load WiFi credentials
  wifi_ssid = preferences.getString("wifi_ssid", "");
  wifi_password = preferences.getString("wifi_password", "");
  api_key = preferences.getString("api_key", "");
  
  if (wifi_ssid == "" || api_key == "") {{
    Serial.println("Device not provisioned. Starting setup mode...");
    startSetupMode();
  }} else {{
    connectToWiFi();
    registerWithActiveLog();
  }}
}}

void loop() {{
  if (WiFi.status() == WL_CONNECTED) {{
    // Collect and send sensor data
    collectAndSendData();
    
    if (DEEP_SLEEP_ENABLED) {{
      enterDeepSleep();
    }} else {{
      delay(REPORTING_INTERVAL);
    }}
  }} else {{
    Serial.println("WiFi disconnected, attempting reconnect...");
    connectToWiFi();
  }}
}}

void startSetupMode() {{
  // Create WiFi access point for configuration
  WiFi.softAP("ActiveLog-" + String(DEVICE_ID).substring(0, 8));
  Serial.println("Setup mode: Connect to WiFi 'ActiveLog-" + String(DEVICE_ID).substring(0, 8) + "'");
  Serial.println("Then visit http://192.168.4.1 to configure");
  
  // Start web server for configuration
  // Implementation would include web server setup
}}

void connectToWiFi() {{
  WiFi.begin(wifi_ssid.c_str(), wifi_password.c_str());
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {{
    delay(500);
    Serial.print(".");
    attempts++;
  }}
  
  if (WiFi.status() == WL_CONNECTED) {{
    Serial.println("\\nWiFi connected!");
    Serial.println("IP address: " + WiFi.localIP().toString());
  }} else {{
    Serial.println("\\nWiFi connection failed!");
  }}
}}

void registerWithActiveLog() {{
  DynamicJsonDocument doc(1024);
  doc["device_id"] = DEVICE_ID;
  doc["status"] = "online";
  doc["ip_address"] = WiFi.localIP().toString();
  doc["mac_address"] = WiFi.macAddress();
  doc["firmware_version"] = "1.0.0";
  doc["timestamp"] = millis();
  
  String payload;
  serializeJson(doc, payload);
  
  http.begin(String(ACTIVELOG_ENDPOINT) + "/devices/" + DEVICE_ID + "/status");
  http.addHeader("Content-Type", "application/json");
  http.addHeader("Authorization", "Bearer " + api_key);
  
  int httpResponseCode = http.POST(payload);
  
  if (httpResponseCode == 200) {{
    Serial.println("✓ Registered with ActiveLog");
  }} else {{
    Serial.println("✗ Failed to register: " + String(httpResponseCode));
  }}
  
  http.end();
}}

void collectAndSendData() {{
  // Collect sensor data (implement based on connected sensors)
  DynamicJsonDocument doc(1024);
  doc["device_id"] = DEVICE_ID;
  doc["timestamp"] = millis();
  doc["data"]["uptime"] = millis() / 1000;
  doc["data"]["free_heap"] = ESP.getFreeHeap();
  doc["data"]["wifi_rssi"] = WiFi.RSSI();
  
  // Add sensor readings here
  // doc["data"]["temperature"] = readTemperature();
  // doc["data"]["humidity"] = readHumidity();
  
  String payload;
  serializeJson(doc, payload);
  
  http.begin(String(ACTIVELOG_ENDPOINT) + "/data");
  http.addHeader("Content-Type", "application/json");
  http.addHeader("Authorization", "Bearer " + api_key);
  
  int httpResponseCode = http.POST(payload);
  
  if (httpResponseCode == 200) {{
    Serial.println("✓ Data sent to ActiveLog");
  }} else {{
    Serial.println("✗ Failed to send data: " + String(httpResponseCode));
  }}
  
  http.end();
}}

void enterDeepSleep() {{
  Serial.println("Entering deep sleep for " + String(REPORTING_INTERVAL / 1000) + " seconds");
  esp_sleep_enable_timer_wakeup(REPORTING_INTERVAL * 1000);
  esp_deep_sleep_start();
}}

// Configuration web server functions would go here
// saveConfiguration(), handleConfigRequest(), etc.
"""
    
    def _generate_esp8266_provisioning_code(self, config: Dict[str, Any]) -> str:
        """Generate ESP8266-specific provisioning code"""
        
        return f"""
// ActiveLog Edge Programmer - ESP8266 Provisioning Code
// Generated on {datetime.utcnow().isoformat()}

#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <ArduinoJson.h>
#include <EEPROM.h>

// Device Configuration
const char* DEVICE_ID = "{config['device_id']}";
const char* ACTIVELOG_ENDPOINT = "{config['activelog_endpoint']}";
const int REPORTING_INTERVAL = {config['reporting_interval']} * 1000;

String wifi_ssid = "";
String wifi_password = "";
String api_key = "";

void setup() {{
  Serial.begin(115200);
  Serial.println("ActiveLog Edge Device (ESP8266) Starting...");
  
  EEPROM.begin(512);
  loadConfiguration();
  
  if (wifi_ssid == "" || api_key == "") {{
    Serial.println("Device not provisioned. Starting setup mode...");
    startSetupMode();
  }} else {{
    connectToWiFi();
    registerWithActiveLog();
  }}
}}

void loop() {{
  if (WiFi.status() == WL_CONNECTED) {{
    collectAndSendData();
    delay(REPORTING_INTERVAL);
  }} else {{
    connectToWiFi();
  }}
}}

void loadConfiguration() {{
  // Load configuration from EEPROM
  // Implementation would read stored WiFi credentials and API key
}}

void connectToWiFi() {{
  WiFi.begin(wifi_ssid.c_str(), wifi_password.c_str());
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {{
    delay(500);
    Serial.print(".");
    attempts++;
  }}
  
  if (WiFi.status() == WL_CONNECTED) {{
    Serial.println("\\nWiFi connected!");
  }}
}}

void registerWithActiveLog() {{
  // Similar to ESP32 implementation but adapted for ESP8266
}}

void collectAndSendData() {{
  // ESP8266-specific data collection and transmission
}}

void startSetupMode() {{
  // ESP8266 WiFi Manager setup
}}
"""
    
    def _generate_arduino_provisioning_code(self, config: Dict[str, Any]) -> str:
        """Generate Arduino (bridge mode) provisioning code"""
        
        return f"""
// ActiveLog Edge Programmer - Arduino Bridge Mode
// Generated on {datetime.utcnow().isoformat()}

#include <SoftwareSerial.h>

// Device Configuration
const char* DEVICE_ID = "{config['device_id']}";
const int REPORTING_INTERVAL = {config['reporting_interval']} * 1000;

SoftwareSerial bridgeSerial(2, 3); // RX, TX to WiFi bridge device

void setup() {{
  Serial.begin(115200);
  bridgeSerial.begin(115200);
  
  Serial.println("ActiveLog Edge Device (Arduino Bridge) Starting...");
  
  // Initialize sensors
  initializeSensors();
  
  // Register with bridge device
  registerWithBridge();
}}

void loop() {{
  // Collect sensor data
  String sensorData = collectSensorData();
  
  // Send to bridge device
  sendToBridge(sensorData);
  
  delay(REPORTING_INTERVAL);
}}

void initializeSensors() {{
  // Initialize connected sensors
  Serial.println("Initializing sensors...");
}}

String collectSensorData() {{
  // Collect data from sensors
  String data = "{{";
  data += "\\"device_id\\":\\"" + String(DEVICE_ID) + "\\",";
  data += "\\"timestamp\\":" + String(millis()) + ",";
  data += "\\"data\\":{{}};
  data += "}}";
  return data;
}}

void sendToBridge(String data) {{
  bridgeSerial.println("ACTIVELOG_DATA:" + data);
  
  // Wait for acknowledgment
  unsigned long timeout = millis() + 5000;
  while (millis() < timeout) {{
    if (bridgeSerial.available()) {{
      String response = bridgeSerial.readStringUntil('\\n');
      if (response.indexOf("ACK") >= 0) {{
        Serial.println("✓ Data sent via bridge");
        return;
      }}
    }}
  }}
  
  Serial.println("✗ Bridge communication timeout");
}}

void registerWithBridge() {{
  bridgeSerial.println("ACTIVELOG_REGISTER:" + String(DEVICE_ID));
}}
"""
    
    def _generate_setup_instructions(self, device_type: DeviceType) -> List[str]:
        """Generate setup instructions for device type"""
        
        if device_type in [DeviceType.ESP32, DeviceType.ESP8266]:
            return [
                "1. Upload the provisioning code to your ESP device",
                "2. Power on the device and look for the setup WiFi network",
                "3. Connect to the WiFi network 'ActiveLog-XXXXXXXX'",
                "4. Open a web browser and go to http://192.168.4.1",
                "5. Enter your WiFi credentials and device API key",
                "6. The device will restart and connect to ActiveLog",
                "7. Check the device status in the ActiveLog dashboard"
            ]
        else:
            return [
                "1. Upload the provisioning code to your Arduino device",
                "2. Connect an ESP32/ESP8266 as a WiFi bridge device",
                "3. Connect bridge device pins 2 and 3 to Arduino pins 2 and 3",
                "4. Configure the bridge device with WiFi and ActiveLog credentials",
                "5. Power on both devices - they will communicate via serial",
                "6. Arduino will send data through the bridge to ActiveLog"
            ]
    
    async def get_device_status(self, device_id: uuid.UUID) -> Dict[str, Any]:
        """Get device provisioning and connection status"""
        
        result = await self.session.execute(
            select(Device).where(Device.id == device_id)
        )
        device = result.scalar_one_or_none()
        
        if not device:
            raise Exception(f"Device {device_id} not found")
        
        # Check ActiveLog status
        activelog_status = await self._check_activelog_status(device)
        
        return {
            "device_id": str(device.id),
            "name": device.name,
            "type": device.device_type.value,
            "status": device.status.value,
            "last_seen": device.last_seen.isoformat() if device.last_seen else None,
            "activelog_status": activelog_status,
            "provisioned": device.metadata.get("activelog_device_id") is not None
        }
    
    async def _check_activelog_status(self, device: Device) -> Dict[str, Any]:
        """Check device status with ActiveLog platform"""
        
        activelog_device_id = device.metadata.get("activelog_device_id")
        if not activelog_device_id:
            return {"connected": False, "error": "Not registered with ActiveLog"}
        
        try:
            # Get user for API key
            user = await self._get_user(device.owner_id)
            if not user or not user.api_key:
                return {"connected": False, "error": "User API key not available"}
            
            headers = {"Authorization": f"Bearer {user.api_key}"}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.device_registry_endpoint}/{activelog_device_id}/status",
                    headers=headers
                ) as response:
                    if response.status == 200:
                        status_data = await response.json()
                        return {
                            "connected": True,
                            "last_seen": status_data.get("last_seen"),
                            "telemetry_count": status_data.get("telemetry_count", 0),
                            "status": status_data.get("status", "unknown")
                        }
                    else:
                        return {"connected": False, "error": f"HTTP {response.status}"}
        
        except Exception as e:
            return {"connected": False, "error": str(e)}
    
    async def deprovision_device(self, device_id: uuid.UUID) -> bool:
        """Deprovision device from ActiveLog"""
        
        result = await self.session.execute(
            select(Device).where(Device.id == device_id)
        )
        device = result.scalar_one_or_none()
        
        if not device:
            raise Exception(f"Device {device_id} not found")
        
        activelog_device_id = device.metadata.get("activelog_device_id")
        if activelog_device_id:
            # Remove from ActiveLog platform
            user = await self._get_user(device.owner_id)
            if user and user.api_key:
                try:
                    headers = {"Authorization": f"Bearer {user.api_key}"}
                    
                    async with aiohttp.ClientSession() as session:
                        async with session.delete(
                            f"{self.device_registry_endpoint}/{activelog_device_id}",
                            headers=headers
                        ) as response:
                            if response.status not in [200, 404]:
                                print(f"Warning: Failed to remove device from ActiveLog: {response.status}")
                
                except Exception as e:
                    print(f"Warning: Error removing device from ActiveLog: {str(e)}")
        
        # Update device status
        await self.session.execute(
            update(Device)
            .where(Device.id == device_id)
            .values(
                status=DeviceStatus.OFFLINE,
                metadata={**device.metadata, "deprovisioned_at": datetime.utcnow().isoformat()}
            )
        )
        await self.session.commit()
        
        return True