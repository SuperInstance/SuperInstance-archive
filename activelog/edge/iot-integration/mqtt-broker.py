#!/usr/bin/env python3
"""
Generic MQTT Broker Integration Template
Provides flexible connection to any MQTT broker (Mosquitto, HiveMQ, etc.)
"""

import json
import ssl
import logging
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime
import asyncio
import paho.mqtt.client as mqtt

class MQTTBrokerClient:
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize MQTT broker connection
        
        Required config:
        - broker_host: MQTT broker hostname
        - broker_port: MQTT broker port (usually 1883 or 8883)
        - device_id: Unique device identifier
        - use_tls: Whether to use TLS/SSL
        - username: Optional username for authentication
        - password: Optional password for authentication
        - ca_cert_file: Optional CA certificate file for TLS
        - cert_file: Optional client certificate file
        - key_file: Optional client private key file
        - topic_prefix: Base topic prefix (e.g., "activelog/devices")
        """
        self.config = config
        self.client = None
        self.connected = False
        self.logger = logging.getLogger(__name__)
        self.message_callbacks = {}
        self.subscription_topics = []
        
    def setup_client(self) -> mqtt.Client:
        """Setup MQTT client with configuration"""
        client_id = f"{self.config['device_id']}_{int(datetime.now().timestamp())}"
        client = mqtt.Client(client_id=client_id)
        
        # Authentication
        if self.config.get('username') and self.config.get('password'):
            client.username_pw_set(
                self.config['username'],
                self.config['password']
            )
            
        # TLS/SSL Configuration
        if self.config.get('use_tls', False):
            ca_certs = self.config.get('ca_cert_file')
            certfile = self.config.get('cert_file')
            keyfile = self.config.get('key_file')
            
            client.tls_set(
                ca_certs=ca_certs,
                certfile=certfile,
                keyfile=keyfile,
                cert_reqs=ssl.CERT_REQUIRED,
                tls_version=ssl.PROTOCOL_TLS,
                ciphers=None
            )
            
        # Set callbacks
        client.on_connect = self._on_connect
        client.on_disconnect = self._on_disconnect
        client.on_message = self._on_message
        client.on_publish = self._on_publish
        client.on_subscribe = self._on_subscribe
        client.on_unsubscribe = self._on_unsubscribe
        
        # Set last will and testament
        will_topic = f"{self.config['topic_prefix']}/{self.config['device_id']}/status"
        will_payload = json.dumps({
            "status": "offline",
            "timestamp": datetime.utcnow().isoformat()
        })
        client.will_set(will_topic, will_payload, qos=1, retain=True)
        
        return client
        
    async def connect(self) -> bool:
        """Connect to MQTT broker"""
        try:
            self.client = self.setup_client()
            
            result = self.client.connect(
                self.config['broker_host'],
                self.config.get('broker_port', 1883),
                60  # keepalive
            )
            
            if result == mqtt.MQTT_ERR_SUCCESS:
                self.client.loop_start()
                
                # Wait for connection
                timeout = 30
                while not self.connected and timeout > 0:
                    await asyncio.sleep(1)
                    timeout -= 1
                    
                if self.connected:
                    # Publish online status
                    await self._publish_status("online")
                    
                return self.connected
            return False
            
        except Exception as e:
            self.logger.error(f"MQTT broker connection failed: {e}")
            return False
            
    def _on_connect(self, client, userdata, flags, rc):
        """Handle connection callback"""
        if rc == 0:
            self.connected = True
            self.logger.info(f"Connected to MQTT broker at {self.config['broker_host']}")
            
            # Re-subscribe to topics if any
            for topic in self.subscription_topics:
                client.subscribe(topic)
                
        else:
            error_messages = {
                1: "Connection refused - incorrect protocol version",
                2: "Connection refused - invalid client identifier",
                3: "Connection refused - server unavailable",
                4: "Connection refused - bad username or password",
                5: "Connection refused - not authorised"
            }
            self.logger.error(f"Connection failed: {error_messages.get(rc, f'Unknown error {rc}')}")
            
    def _on_disconnect(self, client, userdata, rc):
        """Handle disconnection"""
        self.connected = False
        if rc != 0:
            self.logger.warning("Unexpected disconnection from MQTT broker")
        else:
            self.logger.info("Disconnected from MQTT broker")
            
    def _on_message(self, client, userdata, msg):
        """Handle incoming messages"""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            
            self.logger.debug(f"Message received on {topic}: {payload}")
            
            # Check for registered callbacks
            for pattern, callback in self.message_callbacks.items():
                if self._topic_matches_pattern(topic, pattern):
                    try:
                        data = json.loads(payload) if payload else {}
                        asyncio.create_task(callback(topic, data))
                    except json.JSONDecodeError:
                        asyncio.create_task(callback(topic, payload))
                    except Exception as e:
                        self.logger.error(f"Message callback failed: {e}")
                        
        except Exception as e:
            self.logger.error(f"Message handling error: {e}")
            
    def _on_publish(self, client, userdata, mid):
        """Handle publish acknowledgment"""
        self.logger.debug(f"Message {mid} published successfully")
        
    def _on_subscribe(self, client, userdata, mid, granted_qos):
        """Handle subscription acknowledgment"""
        self.logger.debug(f"Subscription {mid} granted with QoS {granted_qos}")
        
    def _on_unsubscribe(self, client, userdata, mid):
        """Handle unsubscription acknowledgment"""
        self.logger.debug(f"Unsubscription {mid} confirmed")
        
    def _topic_matches_pattern(self, topic: str, pattern: str) -> bool:
        """Check if topic matches pattern (supports + and # wildcards)"""
        topic_parts = topic.split('/')
        pattern_parts = pattern.split('/')
        
        i = j = 0
        
        while i < len(topic_parts) and j < len(pattern_parts):
            if pattern_parts[j] == '#':
                return True
            elif pattern_parts[j] == '+':
                i += 1
                j += 1
            elif topic_parts[i] == pattern_parts[j]:
                i += 1
                j += 1
            else:
                return False
                
        return i == len(topic_parts) and j == len(pattern_parts)
        
    async def subscribe(self, topic: str, callback: Optional[Callable] = None, qos: int = 0) -> bool:
        """Subscribe to a topic with optional callback"""
        if not self.connected:
            return False
            
        try:
            result = self.client.subscribe(topic, qos)
            
            if result[0] == mqtt.MQTT_ERR_SUCCESS:
                if topic not in self.subscription_topics:
                    self.subscription_topics.append(topic)
                    
                if callback:
                    self.message_callbacks[topic] = callback
                    
                self.logger.info(f"Subscribed to topic: {topic}")
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"Subscription failed: {e}")
            return False
            
    async def unsubscribe(self, topic: str) -> bool:
        """Unsubscribe from a topic"""
        if not self.connected:
            return False
            
        try:
            result = self.client.unsubscribe(topic)
            
            if result[0] == mqtt.MQTT_ERR_SUCCESS:
                if topic in self.subscription_topics:
                    self.subscription_topics.remove(topic)
                    
                if topic in self.message_callbacks:
                    del self.message_callbacks[topic]
                    
                self.logger.info(f"Unsubscribed from topic: {topic}")
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"Unsubscription failed: {e}")
            return False
            
    async def publish(self, topic: str, payload: Any, qos: int = 0, retain: bool = False) -> bool:
        """Publish message to topic"""
        if not self.connected:
            return False
            
        try:
            if isinstance(payload, (dict, list)):
                payload = json.dumps(payload)
            elif not isinstance(payload, str):
                payload = str(payload)
                
            result = self.client.publish(topic, payload, qos, retain)
            
            return result.rc == mqtt.MQTT_ERR_SUCCESS
            
        except Exception as e:
            self.logger.error(f"Publish failed: {e}")
            return False
            
    async def publish_telemetry(self, data: Dict[str, Any], qos: int = 0) -> bool:
        """Publish telemetry data"""
        topic = f"{self.config['topic_prefix']}/{self.config['device_id']}/telemetry"
        
        payload = {
            "timestamp": datetime.utcnow().isoformat(),
            "device_id": self.config['device_id'],
            "data": data
        }
        
        return await self.publish(topic, payload, qos)
        
    async def publish_event(self, event_type: str, event_data: Dict[str, Any], qos: int = 0) -> bool:
        """Publish event data"""
        topic = f"{self.config['topic_prefix']}/{self.config['device_id']}/events/{event_type}"
        
        payload = {
            "timestamp": datetime.utcnow().isoformat(),
            "device_id": self.config['device_id'],
            "event_type": event_type,
            "data": event_data
        }
        
        return await self.publish(topic, payload, qos)
        
    async def _publish_status(self, status: str) -> bool:
        """Publish device status"""
        topic = f"{self.config['topic_prefix']}/{self.config['device_id']}/status"
        
        payload = {
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
            "device_id": self.config['device_id']
        }
        
        return await self.publish(topic, payload, qos=1, retain=True)
        
    async def setup_command_subscriptions(self):
        """Setup subscriptions for device commands"""
        command_topic = f"{self.config['topic_prefix']}/{self.config['device_id']}/commands/+"
        config_topic = f"{self.config['topic_prefix']}/{self.config['device_id']}/config"
        
        await self.subscribe(command_topic, self._handle_command)
        await self.subscribe(config_topic, self._handle_config_update)
        
    async def _handle_command(self, topic: str, data: Any):
        """Handle device commands"""
        command = topic.split('/')[-1]
        self.logger.info(f"Command '{command}' received: {data}")
        
        # Route commands
        if command == "reboot":
            await self._handle_reboot(data)
        elif command == "update":
            await self._handle_update(data)
        elif command == "config":
            await self._handle_runtime_config(data)
            
    async def _handle_config_update(self, topic: str, data: Any):
        """Handle configuration updates"""
        self.logger.info(f"Configuration update: {data}")
        # Implement configuration update logic
        
    async def _handle_reboot(self, data: Any):
        """Handle reboot command"""
        self.logger.info("Processing reboot command")
        # Implement reboot logic
        
    async def _handle_update(self, data: Any):
        """Handle update command"""
        update_url = data.get("update_url") if isinstance(data, dict) else None
        self.logger.info(f"Processing update command: {update_url}")
        # Implement update logic
        
    async def _handle_runtime_config(self, data: Any):
        """Handle runtime configuration"""
        self.logger.info(f"Processing runtime config: {data}")
        # Implement runtime configuration logic
        
    def disconnect(self):
        """Disconnect from MQTT broker"""
        if self.client and self.connected:
            # Publish offline status before disconnecting
            asyncio.create_task(self._publish_status("offline"))
            
            self.client.loop_stop()
            self.client.disconnect()
            self.connected = False

# Example usage
async def main():
    config = {
        "broker_host": "mqtt.example.com",
        "broker_port": 8883,
        "device_id": "edge-device-001",
        "use_tls": True,
        "username": "device_user",
        "password": "device_password",
        "ca_cert_file": "/path/to/ca.crt",
        "topic_prefix": "activelog/devices"
    }
    
    mqtt_client = MQTTBrokerClient(config)
    
    if await mqtt_client.connect():
        # Setup command subscriptions
        await mqtt_client.setup_command_subscriptions()
        
        # Publish telemetry
        telemetry = {
            "temperature": 23.5,
            "humidity": 62.0,
            "cpu_usage": 38.7
        }
        
        await mqtt_client.publish_telemetry(telemetry)
        
        # Publish an event
        await mqtt_client.publish_event("motion_detected", {
            "location": "front_door",
            "confidence": 0.95
        })
        
        # Keep connection alive
        await asyncio.sleep(30)
        
        mqtt_client.disconnect()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())