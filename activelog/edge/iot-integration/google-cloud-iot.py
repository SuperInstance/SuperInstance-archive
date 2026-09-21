#!/usr/bin/env python3
"""
Google Cloud IoT Core Integration Template
Provides secure connection and data publishing to Google Cloud IoT Core
"""

import json
import jwt
import ssl
import time
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import asyncio
import paho.mqtt.client as mqtt

class GoogleCloudIoT:
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Google Cloud IoT Core connection
        
        Required config:
        - project_id: GCP project ID
        - cloud_region: GCP region (e.g., us-central1)
        - registry_id: IoT registry ID
        - device_id: Device ID
        - private_key_file: Path to private key file
        - algorithm: JWT algorithm (RS256 or ES256)
        """
        self.config = config
        self.client = None
        self.connected = False
        self.logger = logging.getLogger(__name__)
        self.jwt_token = None
        self.jwt_expires_at = None
        
    def create_jwt_token(self) -> str:
        """Create a JWT token for authentication"""
        try:
            with open(self.config['private_key_file'], 'r') as f:
                private_key = f.read()
                
            now = datetime.utcnow()
            expires = now + timedelta(minutes=60)  # Token valid for 1 hour
            
            payload = {
                'iat': now,
                'exp': expires,
                'aud': self.config['project_id']
            }
            
            token = jwt.encode(
                payload, 
                private_key, 
                algorithm=self.config.get('algorithm', 'RS256')
            )
            
            self.jwt_expires_at = expires
            self.jwt_token = token
            
            return token
            
        except Exception as e:
            self.logger.error(f"JWT token creation failed: {e}")
            raise
            
    def setup_client(self) -> mqtt.Client:
        """Setup MQTT client for Google Cloud IoT"""
        client_id = f"projects/{self.config['project_id']}/locations/{self.config['cloud_region']}/registries/{self.config['registry_id']}/devices/{self.config['device_id']}"
        
        client = mqtt.Client(client_id=client_id)
        
        # Use JWT token as password
        jwt_token = self.create_jwt_token()
        client.username_pw_set(
            username='unused',
            password=jwt_token
        )
        
        # Configure TLS
        client.tls_set(ca_certs=None, certfile=None, keyfile=None,
                      cert_reqs=ssl.CERT_REQUIRED,
                      tls_version=ssl.PROTOCOL_TLSv1_2,
                      ciphers=None)
        
        client.on_connect = self._on_connect
        client.on_disconnect = self._on_disconnect
        client.on_message = self._on_message
        client.on_publish = self._on_publish
        
        return client
        
    async def connect(self) -> bool:
        """Connect to Google Cloud IoT Core"""
        try:
            self.client = self.setup_client()
            
            # Connect to Google Cloud IoT MQTT bridge
            result = self.client.connect('mqtt.googleapis.com', 8883, 60)
            
            if result == mqtt.MQTT_ERR_SUCCESS:
                self.client.loop_start()
                
                # Wait for connection
                timeout = 30
                while not self.connected and timeout > 0:
                    await asyncio.sleep(1)
                    timeout -= 1
                    
                if self.connected:
                    # Subscribe to config and command topics
                    await self._subscribe_to_topics()
                    
                return self.connected
            return False
            
        except Exception as e:
            self.logger.error(f"Google Cloud IoT connection failed: {e}")
            return False
            
    async def _subscribe_to_topics(self):
        """Subscribe to device configuration and command topics"""
        config_topic = f"/devices/{self.config['device_id']}/config"
        commands_topic = f"/devices/{self.config['device_id']}/commands/#"
        
        self.client.subscribe(config_topic, qos=1)
        self.client.subscribe(commands_topic, qos=0)
        
        self.logger.info(f"Subscribed to config and commands topics")
        
    def _on_connect(self, client, userdata, flags, rc):
        """Handle connection callback"""
        if rc == 0:
            self.connected = True
            self.logger.info("Connected to Google Cloud IoT Core")
        else:
            self.logger.error(f"Connection failed with code: {rc}")
            
    def _on_disconnect(self, client, userdata, rc):
        """Handle disconnection"""
        self.connected = False
        self.logger.warning("Disconnected from Google Cloud IoT Core")
        
    def _on_message(self, client, userdata, msg):
        """Handle incoming messages"""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            
            self.logger.info(f"Message received on {topic}: {payload}")
            
            if "/config" in topic:
                self._handle_config_update(payload)
            elif "/commands/" in topic:
                self._handle_command(topic, payload)
                
        except Exception as e:
            self.logger.error(f"Message handling error: {e}")
            
    def _on_publish(self, client, userdata, mid):
        """Handle publish acknowledgment"""
        self.logger.debug(f"Message {mid} published successfully")
        
    def _handle_config_update(self, payload: str):
        """Handle device configuration updates"""
        try:
            config = json.loads(payload)
            self.logger.info(f"Configuration update: {config}")
            
            # Process configuration changes
            if 'telemetry_interval' in config:
                self._update_telemetry_interval(config['telemetry_interval'])
                
            if 'power_mode' in config:
                self._update_power_mode(config['power_mode'])
                
        except json.JSONDecodeError:
            self.logger.error("Invalid JSON in config update")
        except Exception as e:
            self.logger.error(f"Config update handling failed: {e}")
            
    def _handle_command(self, topic: str, payload: str):
        """Handle device commands"""
        try:
            command_data = json.loads(payload) if payload else {}
            
            # Extract subfolder from topic (commands/{subfolder})
            subfolder = topic.split('/')[-1] if '/' in topic else 'default'
            
            self.logger.info(f"Command '{subfolder}' received: {command_data}")
            
            # Route commands
            if subfolder == 'reboot':
                self._handle_reboot_command(command_data)
            elif subfolder == 'update':
                self._handle_update_command(command_data)
            elif subfolder == 'config':
                self._handle_runtime_config(command_data)
                
        except Exception as e:
            self.logger.error(f"Command handling failed: {e}")
            
    async def publish_telemetry(self, data: Dict[str, Any], subfolder: str = "") -> bool:
        """Publish telemetry data to Google Cloud IoT"""
        if not self.connected:
            return False
            
        # Check if JWT token needs refresh
        if self._jwt_needs_refresh():
            await self._refresh_jwt_token()
            
        try:
            # Build topic path
            topic_path = f"/devices/{self.config['device_id']}/events"
            if subfolder:
                topic_path += f"/{subfolder}"
                
            payload = {
                "timestamp": datetime.utcnow().isoformat(),
                "device_id": self.config['device_id'],
                "data": data
            }
            
            result = self.client.publish(
                topic_path,
                json.dumps(payload),
                qos=1
            )
            
            return result.rc == mqtt.MQTT_ERR_SUCCESS
            
        except Exception as e:
            self.logger.error(f"Telemetry publish failed: {e}")
            return False
            
    async def publish_state(self, state: Dict[str, Any]) -> bool:
        """Publish device state"""
        if not self.connected:
            return False
            
        try:
            topic = f"/devices/{self.config['device_id']}/state"
            
            payload = {
                "timestamp": datetime.utcnow().isoformat(),
                "state": state
            }
            
            result = self.client.publish(
                topic,
                json.dumps(payload),
                qos=1
            )
            
            return result.rc == mqtt.MQTT_ERR_SUCCESS
            
        except Exception as e:
            self.logger.error(f"State publish failed: {e}")
            return False
            
    def _jwt_needs_refresh(self) -> bool:
        """Check if JWT token needs refresh"""
        if not self.jwt_expires_at:
            return True
            
        # Refresh 5 minutes before expiry
        return datetime.utcnow() >= (self.jwt_expires_at - timedelta(minutes=5))
        
    async def _refresh_jwt_token(self):
        """Refresh JWT token and reconnect"""
        try:
            self.logger.info("Refreshing JWT token")
            
            # Disconnect current client
            if self.client:
                self.client.disconnect()
                
            # Create new client with fresh token
            self.client = self.setup_client()
            
            # Reconnect
            result = self.client.connect('mqtt.googleapis.com', 8883, 60)
            
            if result == mqtt.MQTT_ERR_SUCCESS:
                self.client.loop_start()
                await self._subscribe_to_topics()
                self.logger.info("JWT token refreshed successfully")
            else:
                self.logger.error("Failed to reconnect with new JWT token")
                
        except Exception as e:
            self.logger.error(f"JWT token refresh failed: {e}")
            
    def _update_telemetry_interval(self, interval: int):
        """Update telemetry reporting interval"""
        self.logger.info(f"Updating telemetry interval to {interval} seconds")
        # Implement interval update logic
        
    def _update_power_mode(self, power_mode: str):
        """Update device power mode"""
        self.logger.info(f"Updating power mode to {power_mode}")
        # Implement power mode change logic
        
    def _handle_reboot_command(self, command_data: Dict[str, Any]):
        """Handle device reboot command"""
        self.logger.info("Reboot command received")
        # Implement reboot logic
        
    def _handle_update_command(self, command_data: Dict[str, Any]):
        """Handle device update command"""
        update_url = command_data.get('update_url')
        self.logger.info(f"Update command received: {update_url}")
        # Implement update logic
        
    def _handle_runtime_config(self, config_data: Dict[str, Any]):
        """Handle runtime configuration changes"""
        self.logger.info(f"Runtime config update: {config_data}")
        # Implement runtime config changes
        
    def disconnect(self):
        """Disconnect from Google Cloud IoT Core"""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            self.connected = False

# Example usage
async def main():
    config = {
        "project_id": "your-project-id",
        "cloud_region": "us-central1",
        "registry_id": "your-registry",
        "device_id": "edge-device-001",
        "private_key_file": "/path/to/private_key.pem",
        "algorithm": "RS256"
    }
    
    iot_client = GoogleCloudIoT(config)
    
    if await iot_client.connect():
        # Publish device state
        await iot_client.publish_state({
            "power_mode": "balanced",
            "status": "online",
            "firmware_version": "1.0.0"
        })
        
        # Publish telemetry data
        telemetry = {
            "temperature": 24.5,
            "humidity": 58.0,
            "cpu_usage": 42.1
        }
        
        await iot_client.publish_telemetry(telemetry, "sensors")
        
        # Keep connection alive
        await asyncio.sleep(30)
        
        iot_client.disconnect()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())