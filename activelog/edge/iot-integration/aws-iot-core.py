#!/usr/bin/env python3
"""
AWS IoT Core Integration Template
Provides secure connection and data publishing to AWS IoT Core
"""

import json
import ssl
import time
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import asyncio
from paho.mqtt import client as mqtt_client

class AWSIoTCore:
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize AWS IoT Core connection
        
        Required config:
        - endpoint: AWS IoT endpoint URL
        - device_id: Unique device identifier
        - cert_file: Path to device certificate
        - key_file: Path to private key
        - ca_file: Path to root CA certificate
        - topic_prefix: Base topic for publishing (e.g., "activelog/devices")
        """
        self.config = config
        self.client = None
        self.connected = False
        self.logger = logging.getLogger(__name__)
        
    def setup_client(self) -> mqtt_client.Client:
        """Setup MQTT client with AWS IoT certificates"""
        client = mqtt_client.Client(client_id=self.config['device_id'])
        
        # Configure TLS/SSL
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        context.check_hostname = False
        context.load_verify_locations(self.config['ca_file'])
        context.load_cert_chain(
            self.config['cert_file'], 
            self.config['key_file']
        )
        
        client.tls_set_context(context)
        client.on_connect = self._on_connect
        client.on_disconnect = self._on_disconnect
        client.on_message = self._on_message
        
        return client
        
    async def connect(self) -> bool:
        """Connect to AWS IoT Core"""
        try:
            self.client = self.setup_client()
            result = self.client.connect(
                self.config['endpoint'], 
                8883, 
                60
            )
            
            if result == 0:
                self.client.loop_start()
                
                # Wait for connection
                timeout = 30
                while not self.connected and timeout > 0:
                    await asyncio.sleep(1)
                    timeout -= 1
                    
                return self.connected
            return False
            
        except Exception as e:
            self.logger.error(f"AWS IoT connection failed: {e}")
            return False
            
    def _on_connect(self, client, userdata, flags, rc):
        """Handle connection callback"""
        if rc == 0:
            self.connected = True
            self.logger.info("Connected to AWS IoT Core")
            
            # Subscribe to device shadow updates
            shadow_topic = f"$aws/things/{self.config['device_id']}/shadow/update/delta"
            client.subscribe(shadow_topic)
            
        else:
            self.logger.error(f"AWS IoT connection failed with code: {rc}")
            
    def _on_disconnect(self, client, userdata, rc):
        """Handle disconnection"""
        self.connected = False
        self.logger.warning("Disconnected from AWS IoT Core")
        
    def _on_message(self, client, userdata, msg):
        """Handle incoming messages"""
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode())
            
            if "/shadow/update/delta" in topic:
                self._handle_shadow_update(payload)
            else:
                self._handle_command(topic, payload)
                
        except Exception as e:
            self.logger.error(f"Message handling error: {e}")
            
    def _handle_shadow_update(self, payload: Dict[str, Any]):
        """Handle device shadow updates from AWS"""
        state = payload.get('state', {})
        self.logger.info(f"Shadow update received: {state}")
        # Implement device state changes based on shadow updates
        
    def _handle_command(self, topic: str, payload: Dict[str, Any]):
        """Handle device commands"""
        self.logger.info(f"Command received on {topic}: {payload}")
        # Implement command handling logic
        
    async def publish_telemetry(self, data: Dict[str, Any]) -> bool:
        """Publish telemetry data to AWS IoT"""
        if not self.connected:
            return False
            
        try:
            topic = f"{self.config['topic_prefix']}/{self.config['device_id']}/telemetry"
            
            payload = {
                "timestamp": datetime.utcnow().isoformat(),
                "device_id": self.config['device_id'],
                "data": data
            }
            
            result = self.client.publish(
                topic, 
                json.dumps(payload),
                qos=1
            )
            
            return result.rc == 0
            
        except Exception as e:
            self.logger.error(f"Telemetry publish failed: {e}")
            return False
            
    async def update_shadow(self, desired_state: Dict[str, Any]) -> bool:
        """Update device shadow in AWS IoT"""
        if not self.connected:
            return False
            
        try:
            topic = f"$aws/things/{self.config['device_id']}/shadow/update"
            
            payload = {
                "state": {
                    "reported": desired_state
                },
                "timestamp": int(time.time())
            }
            
            result = self.client.publish(
                topic,
                json.dumps(payload),
                qos=1
            )
            
            return result.rc == 0
            
        except Exception as e:
            self.logger.error(f"Shadow update failed: {e}")
            return False
            
    def disconnect(self):
        """Disconnect from AWS IoT Core"""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            self.connected = False

# Example usage
async def main():
    config = {
        "endpoint": "your-endpoint.iot.region.amazonaws.com",
        "device_id": "edge-device-001",
        "cert_file": "/path/to/device.pem.crt",
        "key_file": "/path/to/private.pem.key", 
        "ca_file": "/path/to/AmazonRootCA1.pem",
        "topic_prefix": "activelog/devices"
    }
    
    iot_client = AWSIoTCore(config)
    
    if await iot_client.connect():
        # Publish sample telemetry
        telemetry = {
            "temperature": 25.5,
            "humidity": 60.2,
            "cpu_usage": 45.3
        }
        
        await iot_client.publish_telemetry(telemetry)
        
        # Update device shadow
        shadow_state = {
            "power_mode": "balanced",
            "status": "online"
        }
        
        await iot_client.update_shadow(shadow_state)
        
        await asyncio.sleep(5)
        iot_client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())