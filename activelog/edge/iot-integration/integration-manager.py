#!/usr/bin/env python3
"""
IoT Integration Manager
Centralized manager for all IoT platform integrations
"""

import json
import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

# Import platform-specific clients
from .aws_iot_core import AWSIoTCore
from .azure_iot_hub import AzureIoTHub  
from .google_cloud_iot import GoogleCloudIoT
from .mqtt_broker import MQTTBrokerClient
from .lorawan_gateway import LoRaWANGateway

class IoTIntegrationManager:
    def __init__(self, config_path: str = "/etc/activelog/iot-integrations.json"):
        """
        Initialize IoT Integration Manager
        
        Args:
            config_path: Path to integration configuration file
        """
        self.config_path = config_path
        self.config = {}
        self.integrations = {}
        self.running = False
        self.logger = logging.getLogger(__name__)
        
        # Platform mapping
        self.platform_classes = {
            'aws_iot_core': AWSIoTCore,
            'azure_iot_hub': AzureIoTHub,
            'google_cloud_iot': GoogleCloudIoT,
            'mqtt_broker': MQTTBrokerClient,
            'lorawan_gateway': LoRaWANGateway
        }
        
    async def load_config(self) -> bool:
        """Load integration configuration"""
        try:
            if Path(self.config_path).exists():
                with open(self.config_path, 'r') as f:
                    self.config = json.load(f)
                    
                self.logger.info(f"Loaded configuration from {self.config_path}")
                return True
            else:
                # Create default configuration
                await self._create_default_config()
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            return False
            
    async def _create_default_config(self):
        """Create default configuration file"""
        default_config = {
            "enabled_platforms": [],
            "platforms": {
                "aws_iot_core": {
                    "enabled": False,
                    "endpoint": "your-endpoint.iot.region.amazonaws.com",
                    "device_id": "edge-device-001",
                    "cert_file": "/path/to/device.pem.crt",
                    "key_file": "/path/to/private.pem.key",
                    "ca_file": "/path/to/AmazonRootCA1.pem",
                    "topic_prefix": "activelog/devices"
                },
                "azure_iot_hub": {
                    "enabled": False,
                    "connection_string": "HostName=your-hub.azure-devices.net;DeviceId=your-device;SharedAccessKey=your-key"
                },
                "google_cloud_iot": {
                    "enabled": False,
                    "project_id": "your-project-id",
                    "cloud_region": "us-central1",
                    "registry_id": "your-registry",
                    "device_id": "edge-device-001",
                    "private_key_file": "/path/to/private_key.pem",
                    "algorithm": "RS256"
                },
                "mqtt_broker": {
                    "enabled": False,
                    "broker_host": "mqtt.example.com",
                    "broker_port": 8883,
                    "device_id": "edge-device-001",
                    "use_tls": True,
                    "username": "device_user",
                    "password": "device_password",
                    "topic_prefix": "activelog/devices"
                },
                "lorawan_gateway": {
                    "enabled": False,
                    "gateway_id": "AA555A0000000000",
                    "server_address": "router.eu.thethings.network",
                    "server_port": 1700,
                    "frequency_plan": "EU868",
                    "network_session_key": "00000000000000000000000000000000",
                    "app_session_key": "00000000000000000000000000000000",
                    "device_addresses": []
                }
            },
            "data_routing": {
                "telemetry": {
                    "primary_platform": "",
                    "backup_platforms": [],
                    "local_storage": True
                },
                "events": {
                    "primary_platform": "",
                    "backup_platforms": [],
                    "local_storage": True
                },
                "commands": {
                    "platforms": []
                }
            },
            "retry_settings": {
                "max_retries": 3,
                "retry_delay": 5,
                "exponential_backoff": True
            }
        }
        
        # Ensure directory exists
        Path(self.config_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.config_path, 'w') as f:
            json.dump(default_config, f, indent=4)
            
        self.config = default_config
        self.logger.info(f"Created default configuration at {self.config_path}")
        
    async def start(self) -> bool:
        """Start all enabled integrations"""
        try:
            if not await self.load_config():
                return False
                
            enabled_platforms = self.config.get('enabled_platforms', [])
            
            for platform_name in enabled_platforms:
                platform_config = self.config['platforms'].get(platform_name, {})
                
                if platform_config.get('enabled', False):
                    success = await self._start_integration(platform_name, platform_config)
                    
                    if success:
                        self.logger.info(f"Started {platform_name} integration")
                    else:
                        self.logger.error(f"Failed to start {platform_name} integration")
                        
            self.running = True
            self.logger.info("IoT Integration Manager started")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start integrations: {e}")
            return False
            
    async def _start_integration(self, platform_name: str, platform_config: Dict[str, Any]) -> bool:
        """Start a specific platform integration"""
        try:
            if platform_name not in self.platform_classes:
                self.logger.error(f"Unknown platform: {platform_name}")
                return False
                
            platform_class = self.platform_classes[platform_name]
            
            if platform_name == 'azure_iot_hub':
                # Azure IoT Hub uses connection string directly
                integration = platform_class(platform_config['connection_string'])
            else:
                # Other platforms use config dict
                integration = platform_class(platform_config)
                
            # Connect to the platform
            if hasattr(integration, 'connect'):
                success = await integration.connect()
            elif hasattr(integration, 'start'):
                success = await integration.start()
            else:
                success = False
                
            if success:
                self.integrations[platform_name] = integration
                return True
            else:
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to start {platform_name}: {e}")
            return False
            
    async def stop(self):
        """Stop all integrations"""
        self.running = False
        
        for platform_name, integration in self.integrations.items():
            try:
                if hasattr(integration, 'disconnect'):
                    await integration.disconnect()
                elif hasattr(integration, 'stop'):
                    await integration.stop()
                    
                self.logger.info(f"Stopped {platform_name} integration")
                
            except Exception as e:
                self.logger.error(f"Error stopping {platform_name}: {e}")
                
        self.integrations.clear()
        self.logger.info("IoT Integration Manager stopped")
        
    async def publish_telemetry(self, data: Dict[str, Any], platform: Optional[str] = None) -> Dict[str, bool]:
        """
        Publish telemetry data to IoT platforms
        
        Args:
            data: Telemetry data to publish
            platform: Specific platform to publish to (None for all)
            
        Returns:
            Dict mapping platform names to success status
        """
        results = {}
        
        routing_config = self.config.get('data_routing', {}).get('telemetry', {})
        
        if platform:
            # Publish to specific platform
            platforms = [platform] if platform in self.integrations else []
        else:
            # Publish based on routing configuration
            platforms = []
            
            primary = routing_config.get('primary_platform')
            if primary and primary in self.integrations:
                platforms.append(primary)
                
            # Add backup platforms if primary fails
            backup_platforms = routing_config.get('backup_platforms', [])
            platforms.extend([p for p in backup_platforms if p in self.integrations])
            
            # If no routing config, publish to all
            if not platforms:
                platforms = list(self.integrations.keys())
                
        for platform_name in platforms:
            try:
                integration = self.integrations[platform_name]
                
                if hasattr(integration, 'publish_telemetry'):
                    success = await integration.publish_telemetry(data)
                elif hasattr(integration, 'send_telemetry'):
                    success = await integration.send_telemetry(data)
                else:
                    success = False
                    
                results[platform_name] = success
                
                if success:
                    self.logger.debug(f"Telemetry published to {platform_name}")
                else:
                    self.logger.error(f"Failed to publish telemetry to {platform_name}")
                    
            except Exception as e:
                self.logger.error(f"Error publishing telemetry to {platform_name}: {e}")
                results[platform_name] = False
                
        # Store locally if configured
        if routing_config.get('local_storage', False):
            await self._store_locally('telemetry', data)
            
        return results
        
    async def publish_event(self, event_type: str, event_data: Dict[str, Any], 
                           platform: Optional[str] = None) -> Dict[str, bool]:
        """
        Publish event data to IoT platforms
        
        Args:
            event_type: Type of event
            event_data: Event data
            platform: Specific platform to publish to (None for routing-based)
            
        Returns:
            Dict mapping platform names to success status
        """
        results = {}
        
        routing_config = self.config.get('data_routing', {}).get('events', {})
        
        if platform:
            platforms = [platform] if platform in self.integrations else []
        else:
            platforms = []
            
            primary = routing_config.get('primary_platform')
            if primary and primary in self.integrations:
                platforms.append(primary)
                
            backup_platforms = routing_config.get('backup_platforms', [])
            platforms.extend([p for p in backup_platforms if p in self.integrations])
            
            if not platforms:
                platforms = list(self.integrations.keys())
                
        for platform_name in platforms:
            try:
                integration = self.integrations[platform_name]
                success = False
                
                if hasattr(integration, 'publish_event'):
                    success = await integration.publish_event(event_type, event_data)
                elif hasattr(integration, 'publish'):
                    # Generic publish method
                    topic_suffix = f"events/{event_type}"
                    success = await integration.publish(topic_suffix, event_data)
                    
                results[platform_name] = success
                
            except Exception as e:
                self.logger.error(f"Error publishing event to {platform_name}: {e}")
                results[platform_name] = False
                
        # Store locally if configured
        if routing_config.get('local_storage', False):
            event_record = {
                'event_type': event_type,
                'event_data': event_data
            }
            await self._store_locally('events', event_record)
            
        return results
        
    async def _store_locally(self, data_type: str, data: Dict[str, Any]):
        """Store data locally for backup/offline operation"""
        try:
            storage_dir = Path("/var/log/activelog/iot-data")
            storage_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.utcnow().isoformat()
            filename = f"{data_type}_{timestamp.replace(':', '-')}.json"
            filepath = storage_dir / filename
            
            record = {
                'timestamp': timestamp,
                'type': data_type,
                'data': data
            }
            
            with open(filepath, 'w') as f:
                json.dump(record, f, indent=2)
                
            self.logger.debug(f"Stored {data_type} data locally: {filepath}")
            
        except Exception as e:
            self.logger.error(f"Failed to store data locally: {e}")
            
    async def get_integration_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all integrations"""
        status = {}
        
        for platform_name, integration in self.integrations.items():
            platform_status = {
                'connected': False,
                'last_activity': None,
                'errors': 0
            }
            
            # Check connection status
            if hasattr(integration, 'connected'):
                platform_status['connected'] = integration.connected
            elif hasattr(integration, 'running'):
                platform_status['connected'] = integration.running
                
            status[platform_name] = platform_status
            
        return status
        
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on all integrations"""
        health_status = {
            'overall_health': 'healthy',
            'integrations': {},
            'timestamp': datetime.utcnow().isoformat()
        }
        
        unhealthy_count = 0
        
        for platform_name, integration in self.integrations.items():
            platform_health = {
                'status': 'healthy',
                'connected': False,
                'issues': []
            }
            
            try:
                # Check connection
                if hasattr(integration, 'connected'):
                    platform_health['connected'] = integration.connected
                    if not integration.connected:
                        platform_health['status'] = 'unhealthy'
                        platform_health['issues'].append('disconnected')
                        unhealthy_count += 1
                        
            except Exception as e:
                platform_health['status'] = 'error'
                platform_health['issues'].append(f'health_check_failed: {str(e)}')
                unhealthy_count += 1
                
            health_status['integrations'][platform_name] = platform_health
            
        # Overall health assessment
        if unhealthy_count == 0:
            health_status['overall_health'] = 'healthy'
        elif unhealthy_count < len(self.integrations):
            health_status['overall_health'] = 'degraded'
        else:
            health_status['overall_health'] = 'critical'
            
        return health_status

# Example usage
async def main():
    manager = IoTIntegrationManager()
    
    if await manager.start():
        # Publish sample telemetry
        telemetry_data = {
            "temperature": 25.5,
            "humidity": 60.2,
            "cpu_usage": 45.3,
            "memory_usage": 67.8
        }
        
        results = await manager.publish_telemetry(telemetry_data)
        print(f"Telemetry publish results: {results}")
        
        # Publish sample event
        event_results = await manager.publish_event("motion_detected", {
            "location": "front_door",
            "confidence": 0.95,
            "timestamp": datetime.utcnow().isoformat()
        })
        print(f"Event publish results: {event_results}")
        
        # Get integration status
        status = await manager.get_integration_status()
        print(f"Integration status: {status}")
        
        # Health check
        health = await manager.health_check()
        print(f"Health check: {health}")
        
        # Keep running for demonstration
        await asyncio.sleep(30)
        
        await manager.stop()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())