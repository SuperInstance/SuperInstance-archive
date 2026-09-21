"""
IoT Platform Integration Templates
Provides ready-to-use integrations for major IoT platforms
"""

from .aws_iot_core import AWSIoTCore
from .azure_iot_hub import AzureIoTHub
from .google_cloud_iot import GoogleCloudIoT
from .mqtt_broker import MQTTBrokerClient
from .lorawan_gateway import LoRaWANGateway
from .integration_manager import IoTIntegrationManager

__all__ = [
    'AWSIoTCore',
    'AzureIoTHub', 
    'GoogleCloudIoT',
    'MQTTBrokerClient',
    'LoRaWANGateway',
    'IoTIntegrationManager'
]

__version__ = "1.0.0"