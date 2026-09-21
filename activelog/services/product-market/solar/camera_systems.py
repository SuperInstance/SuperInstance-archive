#!/usr/bin/env python3
"""
Solar Camera Systems Marketplace - Specialized solar-powered camera solutions
"""

import asyncio
import json
import uuid
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
from enum import Enum
import hashlib
import base64

class CameraType(Enum):
    WILDLIFE = "wildlife"
    SECURITY = "security"
    TIMELAPSE = "timelapse"
    RESEARCH = "research"
    TRAFFIC = "traffic"
    MARINE = "marine"
    AERIAL = "aerial"

class TriggerType(Enum):
    MOTION = "motion"
    SOUND = "sound"
    THERMAL = "thermal"
    SCHEDULE = "schedule"
    MANUAL = "manual"
    AI_DETECTION = "ai_detection"

class PowerMode(Enum):
    SOLAR_ONLY = "solar_only"
    SOLAR_BATTERY = "solar_battery"
    HYBRID = "hybrid"
    AC_BACKUP = "ac_backup"

@dataclass
class CameraSpecs:
    """Camera sensor specifications"""
    sensor_type: str
    resolution_mp: float
    max_video_resolution: str
    night_vision: bool
    ir_range_meters: int
    lens_angle_degrees: int
    zoom_capability: str
    image_stabilization: bool
    hdr_support: bool
    raw_format_support: bool

@dataclass
class SolarSpecs:
    """Solar power system specifications"""
    panel_wattage: float
    panel_efficiency: float
    panel_type: str  # monocrystalline, polycrystalline
    battery_type: str
    battery_capacity_wh: float
    battery_voltage: float
    charge_controller_type: str  # PWM, MPPT
    max_charging_current: float
    low_voltage_protection: float
    estimated_autonomy_days: int

@dataclass
class EnvironmentalSpecs:
    """Environmental specifications"""
    operating_temp_min: float
    operating_temp_max: float
    storage_temp_min: float
    storage_temp_max: float
    humidity_max: float
    ip_rating: str
    wind_resistance_kmh: int
    shock_resistance_g: float
    vibration_resistance: bool
    salt_spray_resistance: bool
    uv_resistance_hours: int

@dataclass
class ConnectivitySpecs:
    """Connectivity specifications"""
    wifi_standards: List[str]
    cellular_bands: List[str]
    bluetooth_version: str
    lora_support: bool
    ethernet_support: bool
    satellite_support: bool
    max_range_meters: int
    data_encryption: bool
    vpn_support: bool

@dataclass
class AICapabilities:
    """AI and analytics capabilities"""
    species_detection: bool
    person_detection: bool
    vehicle_detection: bool
    object_counting: bool
    behavior_analysis: bool
    anomaly_detection: bool
    real_time_processing: bool
    cloud_ai_integration: bool
    custom_models_support: bool
    edge_processing_power: str

@dataclass
class SolarCameraSystem:
    """Complete solar camera system specification"""
    id: str
    name: str
    model: str
    manufacturer: str
    camera_type: CameraType
    description: str
    version: str
    
    # Technical specifications
    camera_specs: CameraSpecs
    solar_specs: SolarSpecs
    environmental_specs: EnvironmentalSpecs
    connectivity_specs: ConnectivitySpecs
    ai_capabilities: AICapabilities
    
    # Physical specifications
    dimensions_mm: Tuple[float, float, float]  # W, H, D
    weight_kg: float
    mounting_options: List[str]
    
    # Operational specifications
    trigger_types: List[TriggerType]
    power_mode: PowerMode
    storage_capacity_gb: int
    max_recording_duration_hours: int
    image_formats: List[str]
    video_formats: List[str]
    streaming_protocols: List[str]
    
    # Performance metrics
    trigger_speed_ms: int
    detection_range_meters: int
    battery_life_months: int
    solar_recharge_time_hours: int
    operating_temp_range: Tuple[float, float]
    
    # Features
    features: List[str]
    included_accessories: List[str]
    optional_accessories: List[str]
    
    # Commercial information
    price_usd: float
    target_market: List[str]
    use_cases: List[str]
    warranty_months: int
    support_level: str
    
    # Certifications
    certifications: List[str]
    environmental_certifications: List[str]
    
    # Integration
    activelog_compatible: bool
    third_party_integrations: List[str]
    api_available: bool
    sdk_available: bool
    
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

class SolarCameraMarketplace:
    """Solar camera systems marketplace"""
    
    def __init__(self, systems_path: str = "./solar_cameras"):
        self.systems_path = Path(systems_path)
        self.systems_path.mkdir(exist_ok=True)
        
        # Camera systems registry
        self.systems: Dict[str, SolarCameraSystem] = {}
        
        # Initialize with product catalog
        self._initialize_product_catalog()
        
        # Performance analytics
        self.analytics = {
            "popular_features": {},
            "price_trends": [],
            "seasonal_demand": {},
            "roi_analysis": {}
        }
    
    def _initialize_product_catalog(self):
        """Initialize with solar camera product catalog"""
        
        # Professional Wildlife Camera
        wildlife_pro = SolarCameraSystem(
            id="SC-WILDLIFE-PRO-4K",
            name="WildTracker Pro 4K Solar Camera",
            model="WT-PRO-4K-SOL",
            manufacturer="NatureTech Systems",
            camera_type=CameraType.WILDLIFE,
            description="Professional-grade solar wildlife camera with 4K video, advanced AI species detection, and 6-month battery autonomy",
            version="3.2",
            
            camera_specs=CameraSpecs(
                sensor_type="CMOS 1/2.3\"",
                resolution_mp=20.0,
                max_video_resolution="4K@30fps",
                night_vision=True,
                ir_range_meters=25,
                lens_angle_degrees=60,
                zoom_capability="4x digital",
                image_stabilization=True,
                hdr_support=True,
                raw_format_support=True
            ),
            
            solar_specs=SolarSpecs(
                panel_wattage=12.0,
                panel_efficiency=22.5,
                panel_type="monocrystalline",
                battery_type="LiFePO4",
                battery_capacity_wh=144,
                battery_voltage=12.0,
                charge_controller_type="MPPT",
                max_charging_current=1.5,
                low_voltage_protection=10.8,
                estimated_autonomy_days=180
            ),
            
            environmental_specs=EnvironmentalSpecs(
                operating_temp_min=-30,
                operating_temp_max=60,
                storage_temp_min=-40,
                storage_temp_max=70,
                humidity_max=95,
                ip_rating="IP67",
                wind_resistance_kmh=120,
                shock_resistance_g=10,
                vibration_resistance=True,
                salt_spray_resistance=False,
                uv_resistance_hours=8760
            ),
            
            connectivity_specs=ConnectivitySpecs(
                wifi_standards=["802.11n", "802.11ac"],
                cellular_bands=["LTE-M", "NB-IoT"],
                bluetooth_version="5.0",
                lora_support=True,
                ethernet_support=False,
                satellite_support=False,
                max_range_meters=1000,
                data_encryption=True,
                vpn_support=True
            ),
            
            ai_capabilities=AICapabilities(
                species_detection=True,
                person_detection=True,
                vehicle_detection=True,
                object_counting=True,
                behavior_analysis=True,
                anomaly_detection=True,
                real_time_processing=True,
                cloud_ai_integration=True,
                custom_models_support=True,
                edge_processing_power="ARM Cortex-A78 @ 2.0GHz"
            ),
            
            dimensions_mm=(150, 120, 95),
            weight_kg=1.2,
            mounting_options=["tree_strap", "post_mount", "wall_bracket", "tripod"],
            
            trigger_types=[TriggerType.MOTION, TriggerType.THERMAL, TriggerType.AI_DETECTION, TriggerType.SCHEDULE],
            power_mode=PowerMode.SOLAR_BATTERY,
            storage_capacity_gb=128,
            max_recording_duration_hours=24,
            image_formats=["JPEG", "RAW", "HEIF"],
            video_formats=["MP4", "MOV", "AVI"],
            streaming_protocols=["RTMP", "RTSP", "WebRTC"],
            
            trigger_speed_ms=200,
            detection_range_meters=20,
            battery_life_months=6,
            solar_recharge_time_hours=8,
            operating_temp_range=(-30, 60),
            
            features=[
                "4K video recording",
                "AI species identification",
                "Solar charging with MPPT",
                "Cellular connectivity",
                "Real-time alerts",
                "Cloud storage integration",
                "Weather protection",
                "Anti-theft security",
                "Mobile app control",
                "Time-lapse mode"
            ],
            
            included_accessories=[
                "Solar panel (12W)",
                "Mounting hardware",
                "Security box",
                "8m cable",
                "SD card (32GB)",
                "Quick start guide"
            ],
            
            optional_accessories=[
                "Extended solar panel (20W)",
                "External battery pack",
                "Camouflage housing",
                "Security lock",
                "Cellular antenna booster"
            ],
            
            price_usd=899.00,
            target_market=["wildlife_research", "conservation", "hunting", "property_security"],
            use_cases=[
                "Wildlife behavior studies",
                "Species population monitoring",
                "Anti-poaching surveillance",
                "Property perimeter security",
                "Remote location monitoring"
            ],
            warranty_months=24,
            support_level="professional",
            
            certifications=["CE", "FCC", "IC", "RoHS"],
            environmental_certifications=["Energy Star", "RoHS"],
            
            activelog_compatible=True,
            third_party_integrations=[
                "AWS IoT",
                "Google Cloud IoT",
                "Microsoft Azure IoT",
                "iNaturalist",
                "eBird"
            ],
            api_available=True,
            sdk_available=True,
            
            tags=["wildlife", "4k", "ai", "professional", "long_range", "weatherproof"]
        )
        
        # Security Camera System
        security_system = SolarCameraSystem(
            id="SC-SECURITY-HD-SOL",
            name="SolarGuard HD Security System",
            model="SG-HD-SOL-V2",
            manufacturer="SecureSolar Inc",
            camera_type=CameraType.SECURITY,
            description="Complete solar security camera system with HD recording, motion detection, and smartphone alerts",
            version="2.5",
            
            camera_specs=CameraSpecs(
                sensor_type="CMOS 1/3\"",
                resolution_mp=8.0,
                max_video_resolution="1080p@60fps",
                night_vision=True,
                ir_range_meters=15,
                lens_angle_degrees=90,
                zoom_capability="2x digital",
                image_stabilization=False,
                hdr_support=True,
                raw_format_support=False
            ),
            
            solar_specs=SolarSpecs(
                panel_wattage=8.0,
                panel_efficiency=20.0,
                panel_type="polycrystalline",
                battery_type="Li-ion",
                battery_capacity_wh=74,
                battery_voltage=7.4,
                charge_controller_type="PWM",
                max_charging_current=2.0,
                low_voltage_protection=6.0,
                estimated_autonomy_days=30
            ),
            
            environmental_specs=EnvironmentalSpecs(
                operating_temp_min=-20,
                operating_temp_max=50,
                storage_temp_min=-30,
                storage_temp_max=60,
                humidity_max=85,
                ip_rating="IP65",
                wind_resistance_kmh=100,
                shock_resistance_g=5,
                vibration_resistance=False,
                salt_spray_resistance=False,
                uv_resistance_hours=5000
            ),
            
            connectivity_specs=ConnectivitySpecs(
                wifi_standards=["802.11n"],
                cellular_bands=["4G LTE"],
                bluetooth_version="4.2",
                lora_support=False,
                ethernet_support=True,
                satellite_support=False,
                max_range_meters=300,
                data_encryption=True,
                vpn_support=False
            ),
            
            ai_capabilities=AICapabilities(
                species_detection=False,
                person_detection=True,
                vehicle_detection=True,
                object_counting=False,
                behavior_analysis=False,
                anomaly_detection=True,
                real_time_processing=False,
                cloud_ai_integration=True,
                custom_models_support=False,
                edge_processing_power="ARM Cortex-A53 @ 1.2GHz"
            ),
            
            dimensions_mm=(120, 85, 70),
            weight_kg=0.8,
            mounting_options=["wall_bracket", "pole_mount", "ceiling_mount"],
            
            trigger_types=[TriggerType.MOTION, TriggerType.SCHEDULE, TriggerType.MANUAL],
            power_mode=PowerMode.SOLAR_BATTERY,
            storage_capacity_gb=64,
            max_recording_duration_hours=12,
            image_formats=["JPEG"],
            video_formats=["MP4", "AVI"],
            streaming_protocols=["RTSP", "HTTP"],
            
            trigger_speed_ms=500,
            detection_range_meters=12,
            battery_life_months=1,
            solar_recharge_time_hours=6,
            operating_temp_range=(-20, 50),
            
            features=[
                "HD 1080p recording",
                "Two-way audio",
                "Motion detection",
                "Night vision",
                "Mobile alerts",
                "Cloud storage",
                "Local SD storage",
                "Weather resistant",
                "Easy installation"
            ],
            
            included_accessories=[
                "Solar panel (8W)",
                "Wall mounting bracket",
                "Ethernet cable (5m)",
                "Power adapter",
                "SD card (16GB)",
                "Installation manual"
            ],
            
            optional_accessories=[
                "Extended battery pack",
                "Weatherproof housing",
                "Additional mounting hardware",
                "Cellular data plan"
            ],
            
            price_usd=399.00,
            target_market=["home_security", "small_business", "remote_property"],
            use_cases=[
                "Home perimeter security",
                "Driveway monitoring",
                "Remote cabin security",
                "Construction site monitoring",
                "Farm equipment protection"
            ],
            warranty_months=12,
            support_level="standard",
            
            certifications=["CE", "FCC"],
            environmental_certifications=["RoHS"],
            
            activelog_compatible=True,
            third_party_integrations=[
                "Ring",
                "Nest",
                "SimpliSafe",
                "ADT"
            ],
            api_available=False,
            sdk_available=False,
            
            tags=["security", "hd", "affordable", "easy_install", "motion_detection"]
        )
        
        # Timelapse Research Camera
        timelapse_research = SolarCameraSystem(
            id="SC-TIMELAPSE-RES",
            name="ChronoLapse Research Camera",
            model="CL-RES-SOL-1",
            manufacturer="Scientific Imaging Corp",
            camera_type=CameraType.TIMELAPSE,
            description="Scientific-grade timelapse camera system for long-term research projects with precise scheduling and data logging",
            version="1.8",
            
            camera_specs=CameraSpecs(
                sensor_type="CCD 1/1.8\"",
                resolution_mp=24.0,
                max_video_resolution="1080p@24fps",
                night_vision=False,
                ir_range_meters=0,
                lens_angle_degrees=45,
                zoom_capability="None",
                image_stabilization=True,
                hdr_support=True,
                raw_format_support=True
            ),
            
            solar_specs=SolarSpecs(
                panel_wattage=15.0,
                panel_efficiency=24.0,
                panel_type="monocrystalline",
                battery_type="LiFePO4",
                battery_capacity_wh=192,
                battery_voltage=12.0,
                charge_controller_type="MPPT",
                max_charging_current=2.5,
                low_voltage_protection=11.0,
                estimated_autonomy_days=365
            ),
            
            environmental_specs=EnvironmentalSpecs(
                operating_temp_min=-40,
                operating_temp_max=70,
                storage_temp_min=-50,
                storage_temp_max=80,
                humidity_max=100,
                ip_rating="IP68",
                wind_resistance_kmh=150,
                shock_resistance_g=15,
                vibration_resistance=True,
                salt_spray_resistance=True,
                uv_resistance_hours=10000
            ),
            
            connectivity_specs=ConnectivitySpecs(
                wifi_standards=["802.11ac"],
                cellular_bands=["LTE-M", "NB-IoT", "Satellite"],
                bluetooth_version="5.1",
                lora_support=True,
                ethernet_support=True,
                satellite_support=True,
                max_range_meters=50000,
                data_encryption=True,
                vpn_support=True
            ),
            
            ai_capabilities=AICapabilities(
                species_detection=False,
                person_detection=False,
                vehicle_detection=False,
                object_counting=False,
                behavior_analysis=False,
                anomaly_detection=False,
                real_time_processing=False,
                cloud_ai_integration=False,
                custom_models_support=False,
                edge_processing_power="ARM Cortex-A55 @ 1.8GHz"
            ),
            
            dimensions_mm=(180, 140, 110),
            weight_kg=2.1,
            mounting_options=["scientific_tripod", "pole_mount", "ground_stake", "research_platform"],
            
            trigger_types=[TriggerType.SCHEDULE, TriggerType.MANUAL],
            power_mode=PowerMode.SOLAR_BATTERY,
            storage_capacity_gb=512,
            max_recording_duration_hours=8760,  # 1 year
            image_formats=["RAW", "TIFF", "JPEG"],
            video_formats=["ProRes", "MP4"],
            streaming_protocols=["RTSP", "FTP", "SFTP"],
            
            trigger_speed_ms=100,
            detection_range_meters=0,
            battery_life_months=12,
            solar_recharge_time_hours=4,
            operating_temp_range=(-40, 70),
            
            features=[
                "24MP scientific sensor",
                "Precise interval timing",
                "GPS synchronization",
                "Weather data logging",
                "RAW image capture",
                "Long-term deployment",
                "Research-grade accuracy",
                "Data validation",
                "Automatic calibration",
                "Scientific metadata"
            ],
            
            included_accessories=[
                "High-efficiency solar panel (15W)",
                "Research-grade tripod",
                "Weather station module",
                "GPS module",
                "Data logger",
                "Calibration targets",
                "Professional case",
                "Cable management system"
            ],
            
            optional_accessories=[
                "Spectral filters",
                "UV/IR filters",
                "Extended battery pack",
                "Satellite communication module",
                "Lightning protection kit"
            ],
            
            price_usd=2499.00,
            target_market=["research_institutions", "universities", "environmental_agencies"],
            use_cases=[
                "Climate change research",
                "Ecosystem monitoring",
                "Geological surveys",
                "Astronomical observations",
                "Long-term environmental studies"
            ],
            warranty_months=36,
            support_level="research",
            
            certifications=["CE", "FCC", "ISO 9001", "NIST"],
            environmental_certifications=["Energy Star", "EPEAT", "RoHS"],
            
            activelog_compatible=True,
            third_party_integrations=[
                "MATLAB",
                "ImageJ",
                "ArcGIS",
                "R Statistical Software",
                "Python Scientific Stack"
            ],
            api_available=True,
            sdk_available=True,
            
            tags=["research", "timelapse", "scientific", "long_term", "high_resolution", "weather_resistant"]
        )
        
        # Traffic Monitoring Camera
        traffic_camera = SolarCameraSystem(
            id="SC-TRAFFIC-AI-SOL",
            name="TrafficVision AI Solar Camera",
            model="TV-AI-SOL-1",
            manufacturer="SmartCity Solutions",
            camera_type=CameraType.TRAFFIC,
            description="AI-powered solar traffic monitoring camera with vehicle detection, counting, and speed estimation",
            version="1.3",
            
            camera_specs=CameraSpecs(
                sensor_type="CMOS 1/1.7\"",
                resolution_mp=16.0,
                max_video_resolution="4K@25fps",
                night_vision=True,
                ir_range_meters=30,
                lens_angle_degrees=120,
                zoom_capability="10x optical",
                image_stabilization=True,
                hdr_support=True,
                raw_format_support=False
            ),
            
            solar_specs=SolarSpecs(
                panel_wattage=30.0,
                panel_efficiency=23.0,
                panel_type="monocrystalline",
                battery_type="LiFePO4",
                battery_capacity_wh=480,
                battery_voltage=24.0,
                charge_controller_type="MPPT",
                max_charging_current=5.0,
                low_voltage_protection=21.0,
                estimated_autonomy_days=14
            ),
            
            environmental_specs=EnvironmentalSpecs(
                operating_temp_min=-30,
                operating_temp_max=65,
                storage_temp_min=-40,
                storage_temp_max=75,
                humidity_max=95,
                ip_rating="IP67",
                wind_resistance_kmh=200,
                shock_resistance_g=20,
                vibration_resistance=True,
                salt_spray_resistance=True,
                uv_resistance_hours=15000
            ),
            
            connectivity_specs=ConnectivitySpecs(
                wifi_standards=["802.11ac", "802.11ax"],
                cellular_bands=["5G", "LTE", "LTE-M"],
                bluetooth_version="5.2",
                lora_support=False,
                ethernet_support=True,
                satellite_support=False,
                max_range_meters=500,
                data_encryption=True,
                vpn_support=True
            ),
            
            ai_capabilities=AICapabilities(
                species_detection=False,
                person_detection=True,
                vehicle_detection=True,
                object_counting=True,
                behavior_analysis=True,
                anomaly_detection=True,
                real_time_processing=True,
                cloud_ai_integration=True,
                custom_models_support=True,
                edge_processing_power="NVIDIA Jetson Nano"
            ),
            
            dimensions_mm=(250, 180, 120),
            weight_kg=3.5,
            mounting_options=["traffic_pole", "overhead_gantry", "street_light", "dedicated_pole"],
            
            trigger_types=[TriggerType.MOTION, TriggerType.AI_DETECTION, TriggerType.SCHEDULE],
            power_mode=PowerMode.SOLAR_BATTERY,
            storage_capacity_gb=256,
            max_recording_duration_hours=168,  # 1 week
            image_formats=["JPEG", "PNG"],
            video_formats=["MP4", "H.265"],
            streaming_protocols=["RTMP", "RTSP", "WebRTC", "HLS"],
            
            trigger_speed_ms=50,
            detection_range_meters=100,
            battery_life_months=0,  # Continuous operation
            solar_recharge_time_hours=3,
            operating_temp_range=(-30, 65),
            
            features=[
                "AI vehicle detection",
                "License plate recognition",
                "Speed estimation",
                "Traffic flow analysis",
                "Incident detection",
                "Real-time alerts",
                "Data analytics",
                "Cloud integration",
                "Edge AI processing",
                "Traffic violation detection"
            ],
            
            included_accessories=[
                "High-power solar panel (30W)",
                "Traffic pole mounting kit",
                "Ethernet cable (20m)",
                "Control unit",
                "Configuration software",
                "Installation hardware"
            ],
            
            optional_accessories=[
                "License plate recognition module",
                "Speed radar integration",
                "Weather monitoring sensors",
                "Emergency communication system"
            ],
            
            price_usd=3499.00,
            target_market=["smart_cities", "transportation_agencies", "law_enforcement"],
            use_cases=[
                "Traffic flow monitoring",
                "Speed enforcement",
                "Intersection safety",
                "Incident detection",
                "Urban planning data collection"
            ],
            warranty_months=24,
            support_level="municipal",
            
            certifications=["CE", "FCC", "DOT", "NEMA"],
            environmental_certifications=["Energy Star", "LEED"],
            
            activelog_compatible=True,
            third_party_integrations=[
                "Traffic management systems",
                "Smart city platforms",
                "Emergency response systems",
                "Data analytics platforms"
            ],
            api_available=True,
            sdk_available=True,
            
            tags=["traffic", "ai", "smart_city", "license_plate", "speed_detection", "municipal"]
        )
        
        # Add systems to registry
        self.systems = {
            wildlife_pro.id: wildlife_pro,
            security_system.id: security_system,
            timelapse_research.id: timelapse_research,
            traffic_camera.id: traffic_camera
        }
    
    def get_system(self, system_id: str) -> Optional[SolarCameraSystem]:
        """Get system by ID"""
        return self.systems.get(system_id)
    
    def list_systems(self, 
                     category: Optional[CameraType] = None,
                     price_range: Optional[Tuple[float, float]] = None,
                     power_mode: Optional[PowerMode] = None,
                     ai_enabled: Optional[bool] = None,
                     activelog_compatible: Optional[bool] = None) -> List[SolarCameraSystem]:
        """List systems with optional filtering"""
        systems = list(self.systems.values())
        
        if category:
            systems = [s for s in systems if s.camera_type == category]
        
        if price_range:
            min_price, max_price = price_range
            systems = [s for s in systems if min_price <= s.price_usd <= max_price]
        
        if power_mode:
            systems = [s for s in systems if s.power_mode == power_mode]
        
        if ai_enabled is not None:
            systems = [s for s in systems if any([
                s.ai_capabilities.species_detection,
                s.ai_capabilities.person_detection,
                s.ai_capabilities.vehicle_detection,
                s.ai_capabilities.behavior_analysis,
                s.ai_capabilities.anomaly_detection
            ]) == ai_enabled]
        
        if activelog_compatible is not None:
            systems = [s for s in systems if s.activelog_compatible == activelog_compatible]
        
        return systems
    
    def search_systems(self, query: str) -> List[Tuple[SolarCameraSystem, float]]:
        """Search systems with relevance scoring"""
        query_lower = query.lower()
        results = []
        
        for system in self.systems.values():
            score = 0.0
            
            # Name and description matching
            if query_lower in system.name.lower():
                score += 5.0
            if query_lower in system.description.lower():
                score += 3.0
            
            # Feature matching
            for feature in system.features:
                if query_lower in feature.lower():
                    score += 2.0
            
            # Use case matching
            for use_case in system.use_cases:
                if query_lower in use_case.lower():
                    score += 1.0
            
            # Tag matching
            for tag in system.tags:
                if query_lower in tag.lower():
                    score += 1.0
            
            # Technical specification matching
            if hasattr(system.camera_specs, query_lower.replace(' ', '_')):
                score += 1.0
            
            if score > 0:
                results.append((system, score))
        
        results.sort(key=lambda x: x[1], reverse=True)
        return results
    
    def compare_systems(self, system_ids: List[str]) -> Dict[str, Any]:
        """Compare multiple systems side by side"""
        systems = [self.systems[id] for id in system_ids if id in self.systems]
        
        if len(systems) < 2:
            return {"error": "At least 2 systems required for comparison"}
        
        comparison = {
            "systems": systems,
            "comparison_matrix": {},
            "recommendations": []
        }
        
        # Price comparison
        prices = [s.price_usd for s in systems]
        comparison["comparison_matrix"]["price"] = {
            "min": min(prices),
            "max": max(prices),
            "range": max(prices) - min(prices),
            "values": {s.id: s.price_usd for s in systems}
        }
        
        # Resolution comparison
        resolutions = [s.camera_specs.resolution_mp for s in systems]
        comparison["comparison_matrix"]["resolution"] = {
            "min": min(resolutions),
            "max": max(resolutions),
            "values": {s.id: s.camera_specs.resolution_mp for s in systems}
        }
        
        # Battery life comparison
        battery_lives = [s.battery_life_months for s in systems]
        comparison["comparison_matrix"]["battery_life"] = {
            "min": min(battery_lives),
            "max": max(battery_lives),
            "values": {s.id: s.battery_life_months for s in systems}
        }
        
        # AI capabilities comparison
        comparison["comparison_matrix"]["ai_capabilities"] = {}
        for system in systems:
            ai_count = sum([
                system.ai_capabilities.species_detection,
                system.ai_capabilities.person_detection,
                system.ai_capabilities.vehicle_detection,
                system.ai_capabilities.behavior_analysis,
                system.ai_capabilities.anomaly_detection
            ])
            comparison["comparison_matrix"]["ai_capabilities"][system.id] = ai_count
        
        # Generate recommendations
        if min(prices) == max(prices):
            comparison["recommendations"].append("All systems are similarly priced")
        else:
            cheapest = min(systems, key=lambda s: s.price_usd)
            most_expensive = max(systems, key=lambda s: s.price_usd)
            comparison["recommendations"].append(
                f"{cheapest.name} offers the best value at ${cheapest.price_usd}"
            )
            comparison["recommendations"].append(
                f"{most_expensive.name} is the premium option at ${most_expensive.price_usd}"
            )
        
        # Resolution recommendations
        highest_res = max(systems, key=lambda s: s.camera_specs.resolution_mp)
        comparison["recommendations"].append(
            f"{highest_res.name} offers the highest resolution at {highest_res.camera_specs.resolution_mp}MP"
        )
        
        return comparison
    
    def calculate_roi(self, system_id: str, use_case_params: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate ROI for specific use case"""
        system = self.systems.get(system_id)
        if not system:
            return {"error": "System not found"}
        
        initial_cost = system.price_usd
        
        # Use case specific calculations
        if "security" in use_case_params.get("application", "").lower():
            # Security ROI calculation
            prevented_incidents_per_year = use_case_params.get("prevented_incidents", 2)
            cost_per_incident = use_case_params.get("incident_cost", 5000)
            annual_savings = prevented_incidents_per_year * cost_per_incident
            
            # Operating costs
            maintenance_cost_annual = initial_cost * 0.05  # 5% of initial cost
            electricity_savings = 300  # Solar power savings
            net_annual_savings = annual_savings - maintenance_cost_annual + electricity_savings
            
            payback_years = initial_cost / net_annual_savings if net_annual_savings > 0 else float('inf')
            
            return {
                "system_id": system_id,
                "initial_cost": initial_cost,
                "annual_savings": annual_savings,
                "annual_costs": maintenance_cost_annual,
                "net_annual_savings": net_annual_savings,
                "payback_period_years": payback_years,
                "roi_5_year": (net_annual_savings * 5 - initial_cost) / initial_cost * 100,
                "break_even_point": "Year " + str(int(payback_years)) if payback_years < 10 else "Beyond 10 years"
            }
        
        elif "research" in use_case_params.get("application", "").lower():
            # Research ROI calculation
            data_collection_value = use_case_params.get("data_value_annual", 10000)
            field_work_savings = use_case_params.get("field_work_savings", 15000)
            annual_value = data_collection_value + field_work_savings
            
            maintenance_cost_annual = initial_cost * 0.03  # Lower maintenance for research
            net_annual_value = annual_value - maintenance_cost_annual
            
            return {
                "system_id": system_id,
                "initial_cost": initial_cost,
                "annual_value": annual_value,
                "annual_costs": maintenance_cost_annual,
                "net_annual_value": net_annual_value,
                "payback_period_years": initial_cost / net_annual_value if net_annual_value > 0 else float('inf'),
                "roi_project_value": "High - enables continuous data collection",
                "scientific_impact": "Enables long-term studies not otherwise possible"
            }
        
        else:
            # Generic ROI calculation
            annual_operational_savings = use_case_params.get("annual_savings", 2000)
            maintenance_cost_annual = initial_cost * 0.08
            net_annual_savings = annual_operational_savings - maintenance_cost_annual
            
            return {
                "system_id": system_id,
                "initial_cost": initial_cost,
                "annual_savings": annual_operational_savings,
                "annual_costs": maintenance_cost_annual,
                "net_annual_savings": net_annual_savings,
                "payback_period_years": initial_cost / net_annual_savings if net_annual_savings > 0 else float('inf')
            }
    
    def generate_system_config(self, system_id: str, deployment_params: Dict[str, Any]) -> Dict[str, Any]:
        """Generate system configuration for deployment"""
        system = self.systems.get(system_id)
        if not system:
            return {"error": "System not found"}
        
        config = {
            "system_info": {
                "id": system.id,
                "name": system.name,
                "model": system.model
            },
            "deployment_config": {},
            "power_config": {},
            "network_config": {},
            "storage_config": {},
            "maintenance_schedule": {}
        }
        
        # Deployment configuration
        location = deployment_params.get("location", {})
        config["deployment_config"] = {
            "latitude": location.get("latitude", 0),
            "longitude": location.get("longitude", 0),
            "elevation": location.get("elevation", 0),
            "timezone": location.get("timezone", "UTC"),
            "mounting_height": deployment_params.get("mounting_height", 3.0),
            "camera_angle": deployment_params.get("camera_angle", 0),
            "detection_zone": deployment_params.get("detection_zone", "full_frame")
        }
        
        # Power configuration
        solar_hours = deployment_params.get("daily_solar_hours", 6)
        daily_power_generation = system.solar_specs.panel_wattage * solar_hours * system.solar_specs.panel_efficiency / 100
        daily_power_consumption = deployment_params.get("daily_usage_hours", 12) * max(system.solar_specs.max_charging_current, 1.0)
        
        config["power_config"] = {
            "solar_panel_angle": deployment_params.get("solar_panel_angle", 30),
            "solar_panel_orientation": deployment_params.get("solar_panel_orientation", "south"),
            "estimated_daily_generation_wh": daily_power_generation,
            "estimated_daily_consumption_wh": daily_power_consumption,
            "power_balance": daily_power_generation - daily_power_consumption,
            "recommended_battery_capacity": system.solar_specs.battery_capacity_wh,
            "low_power_mode_threshold": system.solar_specs.low_voltage_protection
        }
        
        # Network configuration
        config["network_config"] = {
            "primary_connection": deployment_params.get("primary_network", "wifi"),
            "backup_connection": deployment_params.get("backup_network", "cellular"),
            "wifi_ssid": deployment_params.get("wifi_ssid", ""),
            "cellular_apn": deployment_params.get("cellular_apn", ""),
            "data_transmission_schedule": deployment_params.get("transmission_schedule", "hourly"),
            "compression_enabled": True,
            "encryption_enabled": True
        }
        
        # Storage configuration
        recording_hours_per_day = deployment_params.get("recording_hours_per_day", 2)
        video_bitrate_mbps = deployment_params.get("video_quality", "medium") == "high" and 10 or 5
        daily_storage_gb = recording_hours_per_day * video_bitrate_mbps * 0.45  # Conversion factor
        
        config["storage_config"] = {
            "recording_mode": deployment_params.get("recording_mode", "motion_trigger"),
            "video_quality": deployment_params.get("video_quality", "medium"),
            "estimated_daily_storage_gb": daily_storage_gb,
            "storage_retention_days": min(system.storage_capacity_gb / daily_storage_gb, 30),
            "cloud_backup_enabled": deployment_params.get("cloud_backup", False),
            "local_storage_only": not deployment_params.get("cloud_backup", False)
        }
        
        # Maintenance schedule
        config["maintenance_schedule"] = {
            "solar_panel_cleaning": "monthly",
            "battery_check": "quarterly",
            "firmware_updates": "as_available",
            "lens_cleaning": "monthly",
            "housing_inspection": "quarterly",
            "connectivity_test": "weekly",
            "data_backup_verification": "weekly"
        }
        
        return config
    
    def get_market_trends(self) -> Dict[str, Any]:
        """Get solar camera market trends and analytics"""
        trends = {
            "popular_features": {
                "ai_detection": 85,
                "4k_recording": 78,
                "cellular_connectivity": 65,
                "long_battery_life": 92,
                "weatherproof": 88,
                "mobile_app": 95,
                "cloud_storage": 70,
                "night_vision": 90
            },
            "price_segments": {
                "budget": {"range": "< $500", "market_share": 35, "growth": 15},
                "mid_range": {"range": "$500 - $1500", "market_share": 45, "growth": 22},
                "professional": {"range": "> $1500", "market_share": 20, "growth": 18}
            },
            "application_growth": {
                "wildlife_monitoring": {"growth_rate": 25, "market_size": 180},
                "security": {"growth_rate": 18, "market_size": 450},
                "research": {"growth_rate": 30, "market_size": 85},
                "construction": {"growth_rate": 20, "market_size": 120},
                "agriculture": {"growth_rate": 35, "market_size": 95}
            },
            "technology_trends": {
                "ai_integration": {"adoption_rate": 65, "projected_growth": 40},
                "5g_connectivity": {"adoption_rate": 25, "projected_growth": 120},
                "edge_computing": {"adoption_rate": 35, "projected_growth": 85},
                "solar_efficiency": {"current_avg": 22, "projected_improvement": 15}
            },
            "seasonal_demand": {
                "spring": 120,  # Index: 100 = average
                "summer": 140,
                "fall": 110,
                "winter": 70
            }
        }
        
        return trends
    
    def export_catalog(self, format: str = "json") -> str:
        """Export solar camera catalog"""
        if format == "json":
            return json.dumps(
                {system_id: asdict(system) for system_id, system in self.systems.items()},
                indent=2,
                default=str
            )
        elif format == "csv":
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Header
            writer.writerow([
                "ID", "Name", "Type", "Price", "Resolution", "Solar Panel", 
                "Battery Life", "AI Capabilities", "Activelog Compatible"
            ])
            
            # Data
            for system in self.systems.values():
                ai_features = sum([
                    system.ai_capabilities.species_detection,
                    system.ai_capabilities.person_detection,
                    system.ai_capabilities.vehicle_detection,
                    system.ai_capabilities.behavior_analysis,
                    system.ai_capabilities.anomaly_detection
                ])
                
                writer.writerow([
                    system.id,
                    system.name,
                    system.camera_type.value,
                    system.price_usd,
                    f"{system.camera_specs.resolution_mp}MP",
                    f"{system.solar_specs.panel_wattage}W",
                    f"{system.battery_life_months} months",
                    f"{ai_features} AI features",
                    "Yes" if system.activelog_compatible else "No"
                ])
            
            return output.getvalue()
        else:
            raise ValueError(f"Unsupported export format: {format}")

# Example usage and testing
async def main():
    marketplace = SolarCameraMarketplace()
    
    # List all systems
    print("Solar Camera Systems:")
    for system in marketplace.list_systems():
        print(f"- {system.name} ({system.camera_type.value}): ${system.price_usd}")
    
    # Search functionality
    print("\nSearch results for 'wildlife':")
    results = marketplace.search_systems("wildlife")
    for system, score in results:
        print(f"- {system.name} (relevance: {score:.1f})")
    
    # Filter by price range
    print("\nAffordable systems (< $1000):")
    affordable = marketplace.list_systems(price_range=(0, 1000))
    for system in affordable:
        print(f"- {system.name}: ${system.price_usd}")
    
    # Compare systems
    print("\nSystem comparison:")
    comparison = marketplace.compare_systems(["SC-WILDLIFE-PRO-4K", "SC-SECURITY-HD-SOL"])
    print(f"Price range: ${comparison['comparison_matrix']['price']['min']} - ${comparison['comparison_matrix']['price']['max']}")
    
    # ROI calculation
    print("\nROI Analysis for security application:")
    roi = marketplace.calculate_roi("SC-SECURITY-HD-SOL", {
        "application": "security",
        "prevented_incidents": 3,
        "incident_cost": 8000
    })
    print(f"Payback period: {roi.get('payback_period_years', 'N/A'):.1f} years")
    
    # Market trends
    trends = marketplace.get_market_trends()
    print(f"\nTop features: {list(trends['popular_features'].keys())[:3]}")

if __name__ == "__main__":
    asyncio.run(main())