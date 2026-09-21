# IoT Platform Integration Templates

This directory contains ready-to-use integration templates for connecting ActiveLog edge devices to major IoT platforms and protocols.

## Supported Platforms

### Cloud IoT Platforms

#### AWS IoT Core (`aws-iot-core.py`)
- **Features**: Device shadows, telemetry publishing, command handling
- **Authentication**: X.509 certificates
- **Protocols**: MQTT over TLS
- **Configuration**:
  ```python
  config = {
      "endpoint": "your-endpoint.iot.region.amazonaws.com",
      "device_id": "edge-device-001", 
      "cert_file": "/path/to/device.pem.crt",
      "key_file": "/path/to/private.pem.key",
      "ca_file": "/path/to/AmazonRootCA1.pem",
      "topic_prefix": "activelog/devices"
  }
  ```

#### Azure IoT Hub (`azure-iot-hub.py`)
- **Features**: Device twins, direct methods, C2D messages
- **Authentication**: Connection string or certificates
- **Protocols**: AMQP/MQTT over TLS
- **Configuration**:
  ```python
  connection_string = "HostName=hub.azure-devices.net;DeviceId=device;SharedAccessKey=key"
  ```

#### Google Cloud IoT Core (`google-cloud-iot.py`)
- **Features**: Device state, telemetry, configuration updates
- **Authentication**: JWT tokens with RSA/ES256 keys
- **Protocols**: MQTT over TLS
- **Configuration**:
  ```python
  config = {
      "project_id": "your-project-id",
      "cloud_region": "us-central1",
      "registry_id": "your-registry",
      "device_id": "edge-device-001",
      "private_key_file": "/path/to/private_key.pem",
      "algorithm": "RS256"
  }
  ```

### Generic Protocols

#### MQTT Broker (`mqtt-broker.py`)
- **Features**: Generic MQTT client for any broker
- **Authentication**: Username/password, TLS certificates
- **Protocols**: MQTT/MQTTS
- **Supported Brokers**: Mosquitto, HiveMQ, AWS IoT, Azure IoT, etc.
- **Configuration**:
  ```python
  config = {
      "broker_host": "mqtt.example.com",
      "broker_port": 8883,
      "device_id": "edge-device-001",
      "use_tls": True,
      "username": "device_user",
      "password": "device_password",
      "topic_prefix": "activelog/devices"
  }
  ```

#### LoRaWAN Gateway (`lorawan-gateway.py`)
- **Features**: LoRaWAN packet forwarding, device management
- **Protocols**: LoRaWAN over UDP (Semtech protocol)
- **Networks**: The Things Network, Chirpstack, etc.
- **Configuration**:
  ```python
  config = {
      "gateway_id": "AA555A0000000000",
      "server_address": "router.eu.thethings.network", 
      "server_port": 1700,
      "frequency_plan": "EU868",
      "network_session_key": "...",
      "app_session_key": "...",
      "device_addresses": [0x12345678]
  }
  ```

## Integration Manager (`integration-manager.py`)

Centralized manager for handling multiple IoT platform connections simultaneously.

### Features
- **Multi-platform support**: Connect to multiple platforms at once
- **Data routing**: Configure primary/backup platforms for telemetry and events
- **Local storage**: Backup data locally for offline operation
- **Health monitoring**: Track connection status and perform health checks
- **Automatic retry**: Built-in retry logic with exponential backoff

### Usage
```python
from integration_manager import IoTIntegrationManager

manager = IoTIntegrationManager("/etc/activelog/iot-integrations.json")

# Start all enabled integrations
await manager.start()

# Publish telemetry to all platforms
results = await manager.publish_telemetry({
    "temperature": 25.5,
    "humidity": 60.2
})

# Publish event with routing
await manager.publish_event("motion_detected", {
    "location": "front_door",
    "confidence": 0.95
})

# Health check
health = await manager.health_check()
```

## Configuration

Each integration requires platform-specific configuration. The Integration Manager uses a JSON configuration file:

```json
{
    "enabled_platforms": ["aws_iot_core", "mqtt_broker"],
    "platforms": {
        "aws_iot_core": {
            "enabled": true,
            "endpoint": "your-endpoint.iot.region.amazonaws.com",
            "device_id": "edge-device-001",
            "cert_file": "/path/to/cert.pem",
            "key_file": "/path/to/key.pem",
            "ca_file": "/path/to/ca.pem",
            "topic_prefix": "activelog/devices"
        }
    },
    "data_routing": {
        "telemetry": {
            "primary_platform": "aws_iot_core",
            "backup_platforms": ["mqtt_broker"],
            "local_storage": true
        }
    }
}
```

## Security

All integrations implement security best practices:

- **TLS/SSL encryption** for all network communications
- **Certificate-based authentication** where supported
- **Token-based authentication** with automatic renewal
- **Data integrity** verification with checksums/signatures
- **Secure key storage** recommendations

## Dependencies

```bash
# Core dependencies
pip install paho-mqtt asyncio aiofiles

# AWS IoT Core
pip install paho-mqtt

# Azure IoT Hub  
pip install azure-iot-device

# Google Cloud IoT Core
pip install PyJWT cryptography

# LoRaWAN
pip install cryptography

# General
pip install psutil logging
```

## Examples

See the `main()` function in each integration file for complete usage examples.

## Error Handling

All integrations include comprehensive error handling:
- Connection failures with automatic retry
- Message publish failures with logging
- Authentication errors with detailed messages
- Network timeouts with configurable limits

## Monitoring

Integration health can be monitored through:
- Connection status tracking
- Message success/failure rates  
- Last activity timestamps
- Error counters and logging

## Extending

To add support for a new IoT platform:

1. Create a new integration class following the existing patterns
2. Implement required methods: `connect()`, `disconnect()`, `publish_telemetry()`
3. Add the platform to `integration-manager.py`
4. Update configuration schema
5. Add platform-specific dependencies

## License

These integration templates are part of the ActiveLog edge device system.