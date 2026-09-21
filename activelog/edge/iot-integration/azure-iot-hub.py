#!/usr/bin/env python3
"""
Azure IoT Hub Integration Template
Provides secure connection and data publishing to Azure IoT Hub
"""

import json
import asyncio
import logging
from typing import Dict, Any, Optional, Callable
from datetime import datetime
from azure.iot.device import IoTHubDeviceClient, Message, MethodResponse
from azure.iot.device.exceptions import ConnectionFailedError, CredentialError

class AzureIoTHub:
    def __init__(self, connection_string: str):
        """
        Initialize Azure IoT Hub connection
        
        Args:
            connection_string: Azure IoT device connection string
        """
        self.connection_string = connection_string
        self.client = None
        self.connected = False
        self.logger = logging.getLogger(__name__)
        self.message_handlers = {}
        self.method_handlers = {}
        
    async def connect(self) -> bool:
        """Connect to Azure IoT Hub"""
        try:
            self.client = IoTHubDeviceClient.create_from_connection_string(
                self.connection_string
            )
            
            # Set up handlers
            self.client.on_twin_desired_properties_patch_received = self._handle_twin_patch
            self.client.on_method_request_received = self._handle_method_request
            self.client.on_message_received = self._handle_message
            
            await self.client.connect()
            self.connected = True
            self.logger.info("Connected to Azure IoT Hub")
            return True
            
        except (ConnectionFailedError, CredentialError) as e:
            self.logger.error(f"Azure IoT Hub connection failed: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected connection error: {e}")
            return False
            
    async def disconnect(self):
        """Disconnect from Azure IoT Hub"""
        if self.client and self.connected:
            await self.client.disconnect()
            self.connected = False
            self.logger.info("Disconnected from Azure IoT Hub")
            
    async def send_telemetry(self, data: Dict[str, Any]) -> bool:
        """Send telemetry data to Azure IoT Hub"""
        if not self.connected:
            self.logger.warning("Not connected to Azure IoT Hub")
            return False
            
        try:
            payload = {
                "timestamp": datetime.utcnow().isoformat(),
                "data": data
            }
            
            message = Message(json.dumps(payload))
            message.content_encoding = "utf-8"
            message.content_type = "application/json"
            
            # Add custom properties
            message.custom_properties["messageType"] = "telemetry"
            message.custom_properties["deviceType"] = "edge-device"
            
            await self.client.send_message(message)
            self.logger.debug(f"Telemetry sent: {data}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send telemetry: {e}")
            return False
            
    async def update_reported_properties(self, properties: Dict[str, Any]) -> bool:
        """Update device twin reported properties"""
        if not self.connected:
            return False
            
        try:
            reported_patch = {
                "reported": {
                    **properties,
                    "lastUpdate": datetime.utcnow().isoformat()
                }
            }
            
            await self.client.patch_twin_reported_properties(reported_patch)
            self.logger.debug(f"Reported properties updated: {properties}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update reported properties: {e}")
            return False
            
    async def get_twin(self) -> Optional[Dict[str, Any]]:
        """Get current device twin"""
        if not self.connected:
            return None
            
        try:
            twin = await self.client.get_twin()
            return twin
            
        except Exception as e:
            self.logger.error(f"Failed to get twin: {e}")
            return None
            
    def register_method_handler(self, method_name: str, handler: Callable):
        """Register a handler for direct method calls"""
        self.method_handlers[method_name] = handler
        
    def register_message_handler(self, handler: Callable):
        """Register a handler for cloud-to-device messages"""
        self.message_handlers["default"] = handler
        
    async def _handle_twin_patch(self, patch):
        """Handle device twin desired property updates"""
        try:
            self.logger.info(f"Twin patch received: {patch}")
            
            # Process specific property updates
            if "power_mode" in patch:
                await self._update_power_mode(patch["power_mode"])
                
            if "update_interval" in patch:
                await self._update_telemetry_interval(patch["update_interval"])
                
            # Report back the changes
            reported_properties = {}
            for key, value in patch.items():
                if key != "$version":
                    reported_properties[key] = {
                        "value": value,
                        "ac": 200,  # Accepted
                        "av": patch.get("$version", 1),
                        "ad": "Property updated successfully"
                    }
                    
            if reported_properties:
                await self.update_reported_properties(reported_properties)
                
        except Exception as e:
            self.logger.error(f"Twin patch handling failed: {e}")
            
    async def _handle_method_request(self, method_request):
        """Handle direct method requests"""
        try:
            method_name = method_request.name
            self.logger.info(f"Method '{method_name}' called with payload: {method_request.payload}")
            
            if method_name in self.method_handlers:
                result = await self.method_handlers[method_name](method_request.payload)
                status = 200
                payload = {"result": result, "status": "success"}
            else:
                status = 404
                payload = {"error": f"Method '{method_name}' not found"}
                
            method_response = MethodResponse.create_from_method_request(
                method_request, status, payload
            )
            
            await self.client.send_method_response(method_response)
            
        except Exception as e:
            self.logger.error(f"Method request handling failed: {e}")
            error_response = MethodResponse.create_from_method_request(
                method_request, 500, {"error": str(e)}
            )
            await self.client.send_method_response(error_response)
            
    async def _handle_message(self, message):
        """Handle cloud-to-device messages"""
        try:
            self.logger.info(f"Message received: {message.data}")
            
            if "default" in self.message_handlers:
                await self.message_handlers["default"](message)
                
        except Exception as e:
            self.logger.error(f"Message handling failed: {e}")
            
    async def _update_power_mode(self, power_mode: str):
        """Update device power mode"""
        self.logger.info(f"Updating power mode to: {power_mode}")
        # Implement power mode change logic
        
    async def _update_telemetry_interval(self, interval: int):
        """Update telemetry reporting interval"""
        self.logger.info(f"Updating telemetry interval to: {interval} seconds")
        # Implement interval change logic

# Device method handlers
async def reboot_device(payload):
    """Handle device reboot command"""
    logging.info("Reboot command received")
    # Implement reboot logic
    return "Reboot initiated"
    
async def update_firmware(payload):
    """Handle firmware update command"""
    firmware_url = payload.get("firmware_url")
    logging.info(f"Firmware update requested: {firmware_url}")
    # Implement firmware update logic
    return f"Firmware update started from {firmware_url}"

# Example usage
async def main():
    # Replace with your actual connection string
    connection_string = "HostName=your-hub.azure-devices.net;DeviceId=your-device;SharedAccessKey=your-key"
    
    iot_client = AzureIoTHub(connection_string)
    
    # Register method handlers
    iot_client.register_method_handler("reboot", reboot_device)
    iot_client.register_method_handler("updateFirmware", update_firmware)
    
    if await iot_client.connect():
        # Send initial reported properties
        await iot_client.update_reported_properties({
            "deviceType": "edge-device",
            "firmware_version": "1.0.0",
            "status": "online"
        })
        
        # Send sample telemetry
        telemetry_data = {
            "temperature": 22.5,
            "humidity": 55.0,
            "cpu_usage": 35.2,
            "memory_usage": 67.8
        }
        
        await iot_client.send_telemetry(telemetry_data)
        
        # Keep connection alive for demonstration
        await asyncio.sleep(30)
        
        await iot_client.disconnect()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())