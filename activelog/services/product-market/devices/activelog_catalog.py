#!/usr/bin/env python3
"""
Activelog Device Catalog - Comprehensive catalog of Activelog-ready devices
"""

import asyncio
import json
import uuid
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib
from enum import Enum

class DeviceCategory(Enum):
    GATEWAY = "gateway"
    SENSOR_NODE = "sensor_node"
    CAMERA = "camera"
    ACTUATOR = "actuator"
    POWER_MANAGEMENT = "power_management"
    COMMUNICATION = "communication"
    PROCESSING_UNIT = "processing_unit"
    STORAGE = "storage"
    DISPLAY = "display"
    INTERFACE = "interface"

class ConnectivityType(Enum):
    LORA = "lora"
    WIFI = "wifi"
    BLUETOOTH = "bluetooth"
    ZIGBEE = "zigbee"
    CELLULAR = "cellular"
    ETHERNET = "ethernet"
    USB = "usb"
    SERIAL = "serial"

class PowerSource(Enum):
    BATTERY = "battery"
    SOLAR = "solar"
    AC_ADAPTER = "ac_adapter"
    USB_POWER = "usb_power"
    POE = "poe"
    ENERGY_HARVESTING = "energy_harvesting"

@dataclass
class ActivelogProtocol:
    """Activelog protocol specification"""
    version: str
    data_format: str  # JSON, MessagePack, ProtoBuf
    compression: bool
    encryption: bool
    authentication: bool
    message_types: List[str]
    max_payload_size: int
    qos_levels: List[str]

@dataclass
class DeviceInterface:
    """Device interface specification"""
    type: str  # physical, wireless, API
    protocol: str
    connector_type: str
    pin_count: int
    voltage_levels: List[float]
    current_rating: float
    data_rate: str
    range_meters: Optional[float]

@dataclass
class DeviceCapabilities:
    """Device capability specification"""
    data_collection: List[str]
    data_processing: List[str]
    control_functions: List[str]
    storage_capacity: Optional[str]
    processing_power: Optional[str]
    ai_capabilities: List[str]
    real_time_processing: bool
    edge_computing: bool

@dataclass
class ActivelogDevice:
    """Complete Activelog device specification"""
    id: str
    name: str
    model: str
    manufacturer: str
    category: DeviceCategory
    description: str
    version: str
    firmware_version: str
    
    # Physical specifications
    dimensions: Dict[str, float]  # width, height, depth in mm
    weight: float  # grams
    enclosure_rating: str  # IP rating
    operating_temperature: Tuple[float, float]  # min, max in Celsius
    storage_temperature: Tuple[float, float]
    humidity_range: Tuple[float, float]  # % RH
    
    # Power specifications
    power_sources: List[PowerSource]
    input_voltage_range: Tuple[float, float]  # min, max volts
    power_consumption: Dict[str, float]  # mode: watts
    battery_life: Optional[str]
    charging_specs: Optional[Dict[str, Any]]
    
    # Connectivity
    connectivity_options: List[ConnectivityType]
    interfaces: List[DeviceInterface]
    network_topology: List[str]  # star, mesh, point-to-point
    
    # Activelog integration
    activelog_protocol: ActivelogProtocol
    compatibility_level: str  # basic, standard, advanced, professional
    device_capabilities: DeviceCapabilities
    supported_services: List[str]
    integration_apis: List[str]
    
    # Technical specifications
    processor: Optional[str]
    memory: Optional[str]
    storage: Optional[str]
    sensors: List[str]
    actuators: List[str]
    
    # Certification and compliance
    certifications: List[str]  # CE, FCC, UL, etc.
    compliance_standards: List[str]
    safety_rating: str
    
    # Commercial information
    price_usd: float
    availability: str
    lead_time_days: int
    warranty_months: int
    support_level: str
    
    # Documentation and resources
    documentation_urls: Dict[str, str]
    sdk_available: bool
    example_code_urls: List[str]
    integration_guides: List[str]
    
    # Metadata
    created_at: str = None
    updated_at: str = None
    tags: List[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()
        if self.updated_at is None:
            self.updated_at = self.created_at
        if self.tags is None:
            self.tags = []

class ActivelogCatalog:
    """Activelog device catalog management system"""
    
    def __init__(self, catalog_path: str = "./catalog"):
        self.catalog_path = Path(catalog_path)
        self.catalog_path.mkdir(exist_ok=True)
        
        # Device registry
        self.devices: Dict[str, ActivelogDevice] = {}
        
        # Compatibility matrix
        self.compatibility_matrix = {}
        
        # Initialize with device catalog
        self._initialize_catalog()
    
    def _initialize_catalog(self):
        """Initialize catalog with core Activelog devices"""
        
        # Core Gateway Device
        gateway = ActivelogDevice(
            id="AL-GATEWAY-PRO-V2",
            name="Activelog Gateway Pro",
            model="AL-GW-PRO-V2",
            manufacturer="Activelog Systems",
            category=DeviceCategory.GATEWAY,
            description="Professional-grade central gateway for large Activelog deployments with advanced networking and processing capabilities",
            version="2.1",
            firmware_version="2.1.3",
            
            dimensions={"width": 220, "height": 44, "depth": 180},
            weight=1200,
            enclosure_rating="IP40",
            operating_temperature=(-10, 60),
            storage_temperature=(-20, 70),
            humidity_range=(10, 90),
            
            power_sources=[PowerSource.AC_ADAPTER, PowerSource.POE],
            input_voltage_range=(12, 24),
            power_consumption={
                "idle": 8.0,
                "active": 15.0,
                "peak": 25.0
            },
            battery_life=None,
            charging_specs=None,
            
            connectivity_options=[
                ConnectivityType.ETHERNET,
                ConnectivityType.WIFI,
                ConnectivityType.CELLULAR,
                ConnectivityType.LORA
            ],
            interfaces=[
                DeviceInterface(
                    type="ethernet",
                    protocol="TCP/IP",
                    connector_type="RJ45",
                    pin_count=8,
                    voltage_levels=[3.3],
                    current_rating=0.5,
                    data_rate="1Gbps",
                    range_meters=100
                ),
                DeviceInterface(
                    type="lora",
                    protocol="LoRaWAN",
                    connector_type="SMA",
                    pin_count=1,
                    voltage_levels=[3.3],
                    current_rating=0.2,
                    data_rate="50kbps",
                    range_meters=15000
                )
            ],
            network_topology=["star", "mesh"],
            
            activelog_protocol=ActivelogProtocol(
                version="2.1",
                data_format="MessagePack",
                compression=True,
                encryption=True,
                authentication=True,
                message_types=[
                    "device_registration",
                    "sensor_data",
                    "command",
                    "status",
                    "alert",
                    "configuration"
                ],
                max_payload_size=65536,
                qos_levels=["at_most_once", "at_least_once", "exactly_once"]
            ),
            compatibility_level="professional",
            device_capabilities=DeviceCapabilities(
                data_collection=["all_sensor_types"],
                data_processing=["filtering", "aggregation", "analytics", "ml_inference"],
                control_functions=["device_management", "network_management", "security"],
                storage_capacity="1TB NVMe SSD",
                processing_power="Quad-core ARM Cortex-A78",
                ai_capabilities=["edge_ai", "anomaly_detection", "predictive_maintenance"],
                real_time_processing=True,
                edge_computing=True
            ),
            supported_services=[
                "device_discovery",
                "data_routing",
                "cloud_sync",
                "edge_analytics",
                "security_management",
                "firmware_updates"
            ],
            integration_apis=[
                "REST API",
                "GraphQL",
                "WebSocket",
                "MQTT",
                "gRPC"
            ],
            
            processor="ARM Cortex-A78 @ 2.0GHz",
            memory="8GB DDR4",
            storage="1TB NVMe SSD",
            sensors=[],
            actuators=["status_leds", "cooling_fan"],
            
            certifications=["CE", "FCC", "IC", "UL", "RoHS"],
            compliance_standards=["IEEE 802.11", "LoRaWAN 1.0.3", "ISO 27001"],
            safety_rating="Class II",
            
            price_usd=899.00,
            availability="in_stock",
            lead_time_days=5,
            warranty_months=24,
            support_level="professional",
            
            documentation_urls={
                "user_manual": "https://docs.activelog.com/gateway-pro/manual",
                "api_reference": "https://docs.activelog.com/gateway-pro/api",
                "installation_guide": "https://docs.activelog.com/gateway-pro/installation"
            },
            sdk_available=True,
            example_code_urls=[
                "https://github.com/activelog/gateway-examples",
                "https://docs.activelog.com/gateway-pro/examples"
            ],
            integration_guides=[
                "AWS IoT Core Integration",
                "Azure IoT Hub Integration",
                "Google Cloud IoT Integration"
            ],
            
            tags=["gateway", "professional", "enterprise", "networking", "edge_computing"]
        )
        
        # Environmental Sensor Node
        sensor_node = ActivelogDevice(
            id="AL-SENSOR-ENV-V3",
            name="Environmental Sensor Node",
            model="AL-ENV-V3",
            manufacturer="Activelog Systems",
            category=DeviceCategory.SENSOR_NODE,
            description="Multi-sensor environmental monitoring node with solar power and long-range connectivity",
            version="3.2",
            firmware_version="3.2.1",
            
            dimensions={"width": 85, "height": 65, "depth": 35},
            weight=180,
            enclosure_rating="IP67",
            operating_temperature=(-30, 70),
            storage_temperature=(-40, 80),
            humidity_range=(0, 100),
            
            power_sources=[PowerSource.BATTERY, PowerSource.SOLAR],
            input_voltage_range=(3.0, 5.0),
            power_consumption={
                "sleep": 0.01,
                "measurement": 0.5,
                "transmission": 1.2
            },
            battery_life="2+ years",
            charging_specs={
                "solar_panel": "2W monocrystalline",
                "battery_type": "LiPo 3.7V 2200mAh",
                "charge_controller": "MPPT"
            },
            
            connectivity_options=[ConnectivityType.LORA],
            interfaces=[
                DeviceInterface(
                    type="lora",
                    protocol="LoRaWAN",
                    connector_type="internal_antenna",
                    pin_count=0,
                    voltage_levels=[3.3],
                    current_rating=0.15,
                    data_rate="50kbps",
                    range_meters=10000
                )
            ],
            network_topology=["star"],
            
            activelog_protocol=ActivelogProtocol(
                version="2.1",
                data_format="JSON",
                compression=True,
                encryption=True,
                authentication=True,
                message_types=["sensor_data", "status", "alert"],
                max_payload_size=512,
                qos_levels=["at_least_once"]
            ),
            compatibility_level="standard",
            device_capabilities=DeviceCapabilities(
                data_collection=["temperature", "humidity", "pressure", "light", "uv", "soil_moisture"],
                data_processing=["calibration", "averaging", "threshold_detection"],
                control_functions=["sleep_management", "sampling_rate"],
                storage_capacity="32KB EEPROM",
                processing_power="32-bit ARM Cortex-M0+",
                ai_capabilities=[],
                real_time_processing=False,
                edge_computing=False
            ),
            supported_services=["data_collection", "alerts", "configuration"],
            integration_apis=["LoRaWAN"],
            
            processor="ARM Cortex-M0+ @ 48MHz",
            memory="256KB Flash, 64KB RAM",
            storage="32KB EEPROM",
            sensors=[
                "BME680 (temperature, humidity, pressure, gas)",
                "TSL2591 (light, UV)",
                "Capacitive soil moisture sensor"
            ],
            actuators=["status_led"],
            
            certifications=["CE", "FCC", "IC"],
            compliance_standards=["LoRaWAN 1.0.3"],
            safety_rating="Class III",
            
            price_usd=149.00,
            availability="in_stock",
            lead_time_days=3,
            warranty_months=12,
            support_level="standard",
            
            documentation_urls={
                "user_manual": "https://docs.activelog.com/sensor-env/manual",
                "installation_guide": "https://docs.activelog.com/sensor-env/installation"
            },
            sdk_available=False,
            example_code_urls=[],
            integration_guides=["Environmental Monitoring Setup"],
            
            tags=["sensor", "environmental", "solar", "outdoor", "weatherproof"]
        )
        
        # Solar Camera System
        solar_camera = ActivelogDevice(
            id="AL-CAMERA-SOLAR-V2",
            name="Solar Wildlife Camera",
            model="AL-CAM-SOL-V2",
            manufacturer="Activelog Systems",
            category=DeviceCategory.CAMERA,
            description="Solar-powered wildlife camera with AI-powered species detection and real-time streaming",
            version="2.0",
            firmware_version="2.0.5",
            
            dimensions={"width": 120, "height": 90, "depth": 75},
            weight=650,
            enclosure_rating="IP65",
            operating_temperature=(-20, 60),
            storage_temperature=(-30, 70),
            humidity_range=(10, 95),
            
            power_sources=[PowerSource.SOLAR, PowerSource.BATTERY],
            input_voltage_range=(6, 12),
            power_consumption={
                "standby": 0.05,
                "recording": 2.5,
                "streaming": 4.0,
                "ir_illumination": 1.5
            },
            battery_life="6+ months",
            charging_specs={
                "solar_panel": "6W monocrystalline",
                "battery_type": "Li-ion 18650 3.7V 3400mAh x2",
                "charge_controller": "MPPT with load disconnect"
            },
            
            connectivity_options=[ConnectivityType.LORA, ConnectivityType.WIFI],
            interfaces=[
                DeviceInterface(
                    type="lora",
                    protocol="LoRaWAN",
                    connector_type="external_antenna",
                    pin_count=1,
                    voltage_levels=[3.3],
                    current_rating=0.2,
                    data_rate="50kbps",
                    range_meters=15000
                ),
                DeviceInterface(
                    type="wifi",
                    protocol="802.11n",
                    connector_type="internal_antenna",
                    pin_count=0,
                    voltage_levels=[3.3],
                    current_rating=0.3,
                    data_rate="150Mbps",
                    range_meters=100
                )
            ],
            network_topology=["star", "point-to-point"],
            
            activelog_protocol=ActivelogProtocol(
                version="2.1",
                data_format="MessagePack",
                compression=True,
                encryption=True,
                authentication=True,
                message_types=["image", "video", "detection", "status", "alert"],
                max_payload_size=1048576,  # 1MB
                qos_levels=["at_least_once", "exactly_once"]
            ),
            compatibility_level="advanced",
            device_capabilities=DeviceCapabilities(
                data_collection=["images", "video", "motion_detection", "environmental"],
                data_processing=["image_processing", "ai_inference", "compression"],
                control_functions=["trigger_settings", "power_management", "streaming"],
                storage_capacity="64GB microSD",
                processing_power="ARM Cortex-A53 quad-core",
                ai_capabilities=["species_detection", "object_counting", "behavior_analysis"],
                real_time_processing=True,
                edge_computing=True
            ),
            supported_services=[
                "image_capture",
                "video_recording",
                "live_streaming",
                "species_detection",
                "data_sync"
            ],
            integration_apis=["REST API", "RTMP", "WebRTC"],
            
            processor="ARM Cortex-A53 @ 1.2GHz",
            memory="1GB LPDDR3",
            storage="64GB eMMC + microSD slot",
            sensors=[
                "12MP camera sensor",
                "PIR motion sensor",
                "Light sensor",
                "Temperature sensor"
            ],
            actuators=["IR LED array", "status LED", "trigger relay"],
            
            certifications=["CE", "FCC", "IC"],
            compliance_standards=["LoRaWAN 1.0.3", "IEEE 802.11"],
            safety_rating="Class III",
            
            price_usd=449.00,
            availability="in_stock",
            lead_time_days=7,
            warranty_months=18,
            support_level="advanced",
            
            documentation_urls={
                "user_manual": "https://docs.activelog.com/camera-solar/manual",
                "api_reference": "https://docs.activelog.com/camera-solar/api",
                "installation_guide": "https://docs.activelog.com/camera-solar/installation"
            },
            sdk_available=True,
            example_code_urls=[
                "https://github.com/activelog/camera-examples"
            ],
            integration_guides=[
                "Wildlife Monitoring Setup",
                "Security Camera Integration",
                "Research Data Collection"
            ],
            
            tags=["camera", "solar", "wildlife", "ai", "outdoor", "streaming"]
        )
        
        # Fish Counter Device
        fish_counter = ActivelogDevice(
            id="AL-FISHCOUNT-V1",
            name="Automated Fish Counter",
            model="AL-FISH-V1",
            manufacturer="Activelog Marine",
            category=DeviceCategory.SENSOR_NODE,
            description="Automated fish counting system using computer vision for aquaculture and research applications",
            version="1.5",
            firmware_version="1.5.2",
            
            dimensions={"width": 200, "height": 150, "depth": 100},
            weight=1800,
            enclosure_rating="IP68",
            operating_temperature=(0, 40),
            storage_temperature=(-10, 50),
            humidity_range=(0, 100),
            
            power_sources=[PowerSource.AC_ADAPTER, PowerSource.BATTERY],
            input_voltage_range=(12, 24),
            power_consumption={
                "idle": 2.0,
                "counting": 8.0,
                "processing": 12.0
            },
            battery_life="24 hours continuous",
            charging_specs={
                "battery_type": "LiFePO4 12V 10Ah",
                "charge_controller": "Built-in smart charger"
            },
            
            connectivity_options=[ConnectivityType.LORA, ConnectivityType.ETHERNET],
            interfaces=[
                DeviceInterface(
                    type="lora",
                    protocol="LoRaWAN",
                    connector_type="waterproof_antenna",
                    pin_count=1,
                    voltage_levels=[3.3],
                    current_rating=0.2,
                    data_rate="50kbps",
                    range_meters=5000
                ),
                DeviceInterface(
                    type="ethernet",
                    protocol="TCP/IP",
                    connector_type="waterproof_rj45",
                    pin_count=8,
                    voltage_levels=[3.3],
                    current_rating=0.5,
                    data_rate="100Mbps",
                    range_meters=100
                )
            ],
            network_topology=["star"],
            
            activelog_protocol=ActivelogProtocol(
                version="2.1",
                data_format="MessagePack",
                compression=True,
                encryption=True,
                authentication=True,
                message_types=["count_data", "image", "status", "alert", "calibration"],
                max_payload_size=2097152,  # 2MB
                qos_levels=["at_least_once", "exactly_once"]
            ),
            compatibility_level="advanced",
            device_capabilities=DeviceCapabilities(
                data_collection=["fish_count", "size_estimation", "species_classification", "images"],
                data_processing=["computer_vision", "ai_inference", "statistical_analysis"],
                control_functions=["counting_parameters", "image_capture", "calibration"],
                storage_capacity="256GB SSD",
                processing_power="ARM Cortex-A72 quad-core",
                ai_capabilities=["fish_detection", "species_classification", "size_estimation", "behavior_tracking"],
                real_time_processing=True,
                edge_computing=True
            ),
            supported_services=[
                "fish_counting",
                "species_identification",
                "data_analytics",
                "alerts",
                "calibration"
            ],
            integration_apis=["REST API", "WebSocket", "MQTT"],
            
            processor="ARM Cortex-A72 @ 1.5GHz",
            memory="4GB LPDDR4",
            storage="256GB SSD",
            sensors=[
                "Stereo camera system",
                "Ultrasonic distance sensor",
                "Water temperature sensor",
                "Turbidity sensor"
            ],
            actuators=["IR illumination", "status indicators"],
            
            certifications=["CE", "FCC", "IP68"],
            compliance_standards=["LoRaWAN 1.0.3", "IEEE 802.3"],
            safety_rating="Marine Grade",
            
            price_usd=2499.00,
            availability="made_to_order",
            lead_time_days=21,
            warranty_months=24,
            support_level="professional",
            
            documentation_urls={
                "user_manual": "https://docs.activelog.com/fish-counter/manual",
                "api_reference": "https://docs.activelog.com/fish-counter/api",
                "calibration_guide": "https://docs.activelog.com/fish-counter/calibration"
            },
            sdk_available=True,
            example_code_urls=[
                "https://github.com/activelog/fish-counter-examples"
            ],
            integration_guides=[
                "Aquaculture Integration",
                "Research Data Collection",
                "Fishway Monitoring"
            ],
            
            tags=["fish", "counting", "aquaculture", "computer_vision", "underwater", "research"]
        )
        
        # Power Management Unit
        power_unit = ActivelogDevice(
            id="AL-POWER-MGMT-V1",
            name="Smart Power Management Unit",
            model="AL-PWR-V1",
            manufacturer="Activelog Power",
            category=DeviceCategory.POWER_MANAGEMENT,
            description="Intelligent power management and distribution unit with solar MPPT and battery management",
            version="1.0",
            firmware_version="1.0.3",
            
            dimensions={"width": 150, "height": 100, "depth": 60},
            weight=800,
            enclosure_rating="IP54",
            operating_temperature=(-20, 70),
            storage_temperature=(-30, 80),
            humidity_range=(10, 90),
            
            power_sources=[PowerSource.SOLAR, PowerSource.AC_ADAPTER],
            input_voltage_range=(6, 30),
            power_consumption={
                "management": 0.5,
                "charging": 2.0
            },
            battery_life=None,
            charging_specs={
                "max_solar_input": "100W",
                "mppt_efficiency": "95%",
                "battery_types": ["LiPo", "Li-ion", "LiFePO4", "AGM"],
                "max_charge_current": "10A"
            },
            
            connectivity_options=[ConnectivityType.LORA, ConnectivityType.USB],
            interfaces=[
                DeviceInterface(
                    type="lora",
                    protocol="LoRaWAN",
                    connector_type="SMA",
                    pin_count=1,
                    voltage_levels=[3.3],
                    current_rating=0.15,
                    data_rate="50kbps",
                    range_meters=10000
                ),
                DeviceInterface(
                    type="usb",
                    protocol="USB 2.0",
                    connector_type="USB-C",
                    pin_count=24,
                    voltage_levels=[5.0],
                    current_rating=3.0,
                    data_rate="480Mbps",
                    range_meters=3
                )
            ],
            network_topology=["star"],
            
            activelog_protocol=ActivelogProtocol(
                version="2.1",
                data_format="JSON",
                compression=False,
                encryption=True,
                authentication=True,
                message_types=["power_status", "battery_status", "charging_status", "alert"],
                max_payload_size=1024,
                qos_levels=["at_least_once"]
            ),
            compatibility_level="standard",
            device_capabilities=DeviceCapabilities(
                data_collection=["power_metrics", "battery_health", "solar_performance"],
                data_processing=["power_optimization", "battery_management", "load_balancing"],
                control_functions=["output_switching", "charge_control", "protection"],
                storage_capacity="16KB EEPROM",
                processing_power="32-bit ARM Cortex-M4",
                ai_capabilities=["power_prediction", "load_optimization"],
                real_time_processing=True,
                edge_computing=False
            ),
            supported_services=[
                "power_monitoring",
                "battery_management",
                "solar_optimization",
                "load_control",
                "alerts"
            ],
            integration_apis=["LoRaWAN", "USB HID"],
            
            processor="ARM Cortex-M4 @ 168MHz",
            memory="512KB Flash, 128KB RAM",
            storage="16KB EEPROM",
            sensors=[
                "Voltage sensors (4x)",
                "Current sensors (4x)",
                "Temperature sensors (3x)",
                "Power meters (2x)"
            ],
            actuators=["Power switches (4x)", "Status LEDs", "Cooling fan"],
            
            certifications=["CE", "UL", "RoHS"],
            compliance_standards=["IEC 62133", "UN 38.3"],
            safety_rating="Class II",
            
            price_usd=329.00,
            availability="in_stock",
            lead_time_days=5,
            warranty_months=24,
            support_level="standard",
            
            documentation_urls={
                "user_manual": "https://docs.activelog.com/power-mgmt/manual",
                "installation_guide": "https://docs.activelog.com/power-mgmt/installation"
            },
            sdk_available=False,
            example_code_urls=[],
            integration_guides=["Solar Power Setup", "Battery Management"],
            
            tags=["power", "solar", "battery", "mppt", "management", "protection"]
        )
        
        # Add devices to registry
        self.devices = {
            gateway.id: gateway,
            sensor_node.id: sensor_node,
            solar_camera.id: solar_camera,
            fish_counter.id: fish_counter,
            power_unit.id: power_unit
        }
        
        # Initialize compatibility matrix
        self._build_compatibility_matrix()
    
    def _build_compatibility_matrix(self):
        """Build device compatibility matrix"""
        # Define compatibility relationships
        compatibility_rules = [
            # Gateway is compatible with all devices
            ("AL-GATEWAY-PRO-V2", "AL-SENSOR-ENV-V3", 1.0),
            ("AL-GATEWAY-PRO-V2", "AL-CAMERA-SOLAR-V2", 1.0),
            ("AL-GATEWAY-PRO-V2", "AL-FISHCOUNT-V1", 1.0),
            ("AL-GATEWAY-PRO-V2", "AL-POWER-MGMT-V1", 0.9),
            
            # Sensor node compatibility
            ("AL-SENSOR-ENV-V3", "AL-POWER-MGMT-V1", 1.0),
            ("AL-SENSOR-ENV-V3", "AL-CAMERA-SOLAR-V2", 0.8),
            
            # Camera compatibility
            ("AL-CAMERA-SOLAR-V2", "AL-POWER-MGMT-V1", 0.9),
            ("AL-CAMERA-SOLAR-V2", "AL-SENSOR-ENV-V3", 0.8),
            
            # Fish counter compatibility
            ("AL-FISHCOUNT-V1", "AL-POWER-MGMT-V1", 0.7),
            ("AL-FISHCOUNT-V1", "AL-SENSOR-ENV-V3", 0.6),
        ]
        
        for device1_id, device2_id, score in compatibility_rules:
            if device1_id not in self.compatibility_matrix:
                self.compatibility_matrix[device1_id] = {}
            if device2_id not in self.compatibility_matrix:
                self.compatibility_matrix[device2_id] = {}
            
            self.compatibility_matrix[device1_id][device2_id] = score
            self.compatibility_matrix[device2_id][device1_id] = score  # Bidirectional
    
    def get_device(self, device_id: str) -> Optional[ActivelogDevice]:
        """Get device by ID"""
        return self.devices.get(device_id)
    
    def list_devices(self, category: Optional[DeviceCategory] = None,
                    compatibility_level: Optional[str] = None,
                    price_range: Optional[Tuple[float, float]] = None,
                    tags: Optional[List[str]] = None) -> List[ActivelogDevice]:
        """List devices with optional filtering"""
        devices = list(self.devices.values())
        
        if category:
            devices = [d for d in devices if d.category == category]
        
        if compatibility_level:
            devices = [d for d in devices if d.compatibility_level == compatibility_level]
        
        if price_range:
            min_price, max_price = price_range
            devices = [d for d in devices if min_price <= d.price_usd <= max_price]
        
        if tags:
            devices = [d for d in devices if any(tag in d.tags for tag in tags)]
        
        return devices
    
    def search_devices(self, query: str, limit: int = 10) -> List[Tuple[ActivelogDevice, float]]:
        """Search devices with relevance scoring"""
        query_lower = query.lower()
        results = []
        
        for device in self.devices.values():
            score = 0.0
            
            # Name match (highest weight)
            if query_lower in device.name.lower():
                score += 5.0
            
            # Description match
            if query_lower in device.description.lower():
                score += 3.0
            
            # Category match
            if query_lower in device.category.value:
                score += 2.0
            
            # Tag match
            for tag in device.tags:
                if query_lower in tag.lower():
                    score += 1.0
            
            # Capability match
            for capability in device.device_capabilities.data_collection:
                if query_lower in capability.lower():
                    score += 1.0
            
            # Sensor match
            for sensor in device.sensors:
                if query_lower in sensor.lower():
                    score += 1.0
            
            if score > 0:
                results.append((device, score))
        
        # Sort by relevance
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]
    
    def get_compatible_devices(self, device_id: str, min_compatibility: float = 0.7) -> List[Tuple[ActivelogDevice, float]]:
        """Get devices compatible with the specified device"""
        if device_id not in self.compatibility_matrix:
            return []
        
        compatible = []
        for other_id, compatibility_score in self.compatibility_matrix[device_id].items():
            if compatibility_score >= min_compatibility:
                device = self.devices.get(other_id)
                if device:
                    compatible.append((device, compatibility_score))
        
        # Sort by compatibility score
        compatible.sort(key=lambda x: x[1], reverse=True)
        return compatible
    
    def recommend_system_configuration(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Recommend system configuration based on requirements"""
        config = {
            "gateway": None,
            "devices": [],
            "power_system": None,
            "estimated_cost": 0.0,
            "estimated_power": 0.0,
            "recommendations": []
        }
        
        # Always need a gateway for multi-device systems
        if requirements.get("device_count", 1) > 1:
            gateway = self.get_device("AL-GATEWAY-PRO-V2")
            if gateway:
                config["gateway"] = gateway
                config["estimated_cost"] += gateway.price_usd
                config["estimated_power"] += gateway.power_consumption.get("active", 15.0)
        
        # Add devices based on requirements
        if "environmental_monitoring" in requirements.get("applications", []):
            sensor = self.get_device("AL-SENSOR-ENV-V3")
            if sensor:
                config["devices"].append(sensor)
                config["estimated_cost"] += sensor.price_usd
                config["estimated_power"] += sensor.power_consumption.get("transmission", 1.2)
        
        if "wildlife_monitoring" in requirements.get("applications", []):
            camera = self.get_device("AL-CAMERA-SOLAR-V2")
            if camera:
                config["devices"].append(camera)
                config["estimated_cost"] += camera.price_usd
                config["estimated_power"] += camera.power_consumption.get("recording", 2.5)
        
        if "fish_counting" in requirements.get("applications", []):
            fish_counter = self.get_device("AL-FISHCOUNT-V1")
            if fish_counter:
                config["devices"].append(fish_counter)
                config["estimated_cost"] += fish_counter.price_usd
                config["estimated_power"] += fish_counter.power_consumption.get("counting", 8.0)
        
        # Add power management if needed
        if requirements.get("solar_powered", False) or config["estimated_power"] > 5.0:
            power_unit = self.get_device("AL-POWER-MGMT-V1")
            if power_unit:
                config["power_system"] = power_unit
                config["estimated_cost"] += power_unit.price_usd
        
        # Generate recommendations
        if config["estimated_power"] > 20:
            config["recommendations"].append("Consider multiple power units for high power requirements")
        
        if len(config["devices"]) > 5:
            config["recommendations"].append("Use gateway for device management and data aggregation")
        
        if not config["power_system"] and any("solar" in d.tags for d in config["devices"]):
            config["recommendations"].append("Add power management unit for optimal solar charging")
        
        return config
    
    def generate_integration_guide(self, device_ids: List[str]) -> Dict[str, Any]:
        """Generate integration guide for a set of devices"""
        devices = [self.devices[id] for id in device_ids if id in self.devices]
        
        guide = {
            "devices": devices,
            "network_topology": self._determine_network_topology(devices),
            "power_requirements": self._calculate_power_requirements(devices),
            "setup_steps": self._generate_setup_steps(devices),
            "configuration_examples": self._generate_config_examples(devices),
            "troubleshooting": self._generate_troubleshooting_guide(devices)
        }
        
        return guide
    
    def _determine_network_topology(self, devices: List[ActivelogDevice]) -> Dict[str, Any]:
        """Determine optimal network topology"""
        has_gateway = any(d.category == DeviceCategory.GATEWAY for d in devices)
        device_count = len(devices)
        
        if has_gateway and device_count > 3:
            topology = "star_with_gateway"
        elif device_count <= 3:
            topology = "point_to_point"
        else:
            topology = "mesh"
        
        return {
            "recommended_topology": topology,
            "gateway_required": has_gateway or device_count > 5,
            "max_range": min(d.interfaces[0].range_meters for d in devices if d.interfaces),
            "data_rate": min([i.data_rate for d in devices for i in d.interfaces if hasattr(i, 'data_rate')])
        }
    
    def _calculate_power_requirements(self, devices: List[ActivelogDevice]) -> Dict[str, Any]:
        """Calculate total power requirements"""
        total_idle = sum(d.power_consumption.get("idle", d.power_consumption.get("sleep", 0)) for d in devices)
        total_active = sum(max(d.power_consumption.values()) for d in devices)
        
        return {
            "total_idle_power": total_idle,
            "total_active_power": total_active,
            "estimated_daily_consumption": total_active * 0.1 + total_idle * 0.9,  # 10% active, 90% idle
            "recommended_battery_capacity": total_active * 24 * 1.5,  # 1.5 days backup
            "recommended_solar_panel": total_active * 1.3  # 30% margin
        }
    
    def _generate_setup_steps(self, devices: List[ActivelogDevice]) -> List[str]:
        """Generate setup steps"""
        steps = [
            "1. Plan device placement and network coverage",
            "2. Install gateway device (if required)",
            "3. Configure network settings and security",
            "4. Install and configure individual devices",
            "5. Test connectivity and data flow",
            "6. Set up monitoring and alerts",
            "7. Perform system validation"
        ]
        
        # Add device-specific steps
        if any(d.category == DeviceCategory.CAMERA for d in devices):
            steps.insert(4, "4a. Position cameras for optimal coverage")
        
        if any("solar" in d.tags for d in devices):
            steps.insert(1, "1a. Assess solar exposure and shading")
        
        return steps
    
    def _generate_config_examples(self, devices: List[ActivelogDevice]) -> Dict[str, Any]:
        """Generate configuration examples"""
        examples = {}
        
        for device in devices:
            examples[device.id] = {
                "basic_config": {
                    "device_id": device.id,
                    "network_id": "activelog_network",
                    "encryption_key": "your_encryption_key",
                    "reporting_interval": 60
                },
                "advanced_config": {
                    "power_management": "auto",
                    "data_compression": True,
                    "local_storage": True,
                    "alert_thresholds": {}
                }
            }
        
        return examples
    
    def _generate_troubleshooting_guide(self, devices: List[ActivelogDevice]) -> List[str]:
        """Generate troubleshooting guide"""
        guide = [
            "Device not connecting:",
            "- Check power supply and battery level",
            "- Verify network credentials and range",
            "- Check antenna connections",
            "",
            "Poor data quality:",
            "- Calibrate sensors according to manual",
            "- Check for interference sources",
            "- Verify proper mounting and orientation",
            "",
            "High power consumption:",
            "- Review sampling and transmission intervals",
            "- Check for stuck actuators or continuous processing",
            "- Verify sleep mode functionality"
        ]
        
        return guide
    
    def export_catalog(self, format: str = "json") -> str:
        """Export catalog in specified format"""
        if format == "json":
            return json.dumps(
                {device_id: asdict(device) for device_id, device in self.devices.items()},
                indent=2,
                default=str
            )
        elif format == "csv":
            # Implement CSV export
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Header
            writer.writerow([
                "ID", "Name", "Category", "Price", "Compatibility Level",
                "Power Consumption", "Connectivity", "Description"
            ])
            
            # Data
            for device in self.devices.values():
                writer.writerow([
                    device.id,
                    device.name,
                    device.category.value,
                    device.price_usd,
                    device.compatibility_level,
                    max(device.power_consumption.values()),
                    ", ".join([c.value for c in device.connectivity_options]),
                    device.description[:100] + "..." if len(device.description) > 100 else device.description
                ])
            
            return output.getvalue()
        else:
            raise ValueError(f"Unsupported export format: {format}")

# Example usage and testing
async def main():
    catalog = ActivelogCatalog()
    
    # List all devices
    print("All Activelog Devices:")
    for device in catalog.list_devices():
        print(f"- {device.name} ({device.category.value}): ${device.price_usd}")
    
    print("\nSolar-powered devices:")
    solar_devices = catalog.list_devices(tags=["solar"])
    for device in solar_devices:
        print(f"- {device.name}: {device.battery_life}")
    
    # Search functionality
    print("\nSearch results for 'camera':")
    results = catalog.search_devices("camera")
    for device, score in results:
        print(f"- {device.name} (score: {score:.1f})")
    
    # Compatibility check
    print("\nDevices compatible with Gateway Pro:")
    compatible = catalog.get_compatible_devices("AL-GATEWAY-PRO-V2")
    for device, score in compatible:
        print(f"- {device.name} (compatibility: {score:.1f})")
    
    # System recommendation
    print("\nRecommended system for environmental monitoring:")
    requirements = {
        "applications": ["environmental_monitoring", "wildlife_monitoring"],
        "device_count": 3,
        "solar_powered": True
    }
    config = catalog.recommend_system_configuration(requirements)
    print(f"Estimated cost: ${config['estimated_cost']:.2f}")
    print(f"Estimated power: {config['estimated_power']:.1f}W")
    
    # Export catalog
    json_export = catalog.export_catalog("json")
    print(f"\nCatalog exported: {len(json_export)} characters")

if __name__ == "__main__":
    asyncio.run(main())