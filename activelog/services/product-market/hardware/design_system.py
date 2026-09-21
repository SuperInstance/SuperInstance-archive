#!/usr/bin/env python3
"""
Custom Hardware Design System - CAD integration and design management
"""

import asyncio
import json
import uuid
import os
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib
import base64
from PIL import Image, ImageDraw
import io
import zipfile
import shutil

@dataclass
class Component:
    """Hardware component specification"""
    id: str
    name: str
    type: str  # resistor, capacitor, ic, sensor, etc.
    value: str
    package: str  # SMD0805, DIP8, QFN32, etc.
    manufacturer: str
    part_number: str
    datasheet_url: str
    price: float
    availability: str
    footprint: Dict[str, Any]  # PCB footprint data
    schematic_symbol: Dict[str, Any]  # Schematic symbol data
    specifications: Dict[str, Any]
    created_at: str = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()

@dataclass
class PCBLayer:
    """PCB layer specification"""
    name: str
    type: str  # signal, power, ground, mechanical
    thickness: float  # in mm
    material: str
    copper_weight: float  # in oz/ft²
    traces: List[Dict[str, Any]]
    vias: List[Dict[str, Any]]
    pads: List[Dict[str, Any]]

@dataclass
class HardwareDesign:
    """Complete hardware design specification"""
    id: str
    name: str
    version: str
    description: str
    category: str
    designer_id: str
    components: List[Component]
    schematic: Dict[str, Any]
    pcb_layout: Dict[str, Any]
    pcb_layers: List[PCBLayer]
    bill_of_materials: List[Dict[str, Any]]
    assembly_notes: str
    test_procedures: str
    certifications: List[str]
    design_files: Dict[str, str]  # file_type: file_path
    renders: List[str]  # 3D render image URLs
    specifications: Dict[str, Any]
    power_requirements: Dict[str, Any]
    environmental_specs: Dict[str, Any]
    mechanical_specs: Dict[str, Any]
    interface_specs: Dict[str, Any]
    activelog_integration: Dict[str, Any]
    license_type: str
    tags: List[str]
    difficulty_level: str
    estimated_cost: float
    assembly_time_hours: float
    tools_required: List[str]
    created_at: str = None
    updated_at: str = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()
        if self.updated_at is None:
            self.updated_at = self.created_at

class HardwareDesignSystem:
    """Advanced hardware design system with CAD integration"""
    
    def __init__(self, designs_path: str = "./designs"):
        self.designs_path = Path(designs_path)
        self.designs_path.mkdir(exist_ok=True)
        
        # Component libraries
        self.component_libraries = {
            "basic": self._load_basic_components(),
            "sensors": self._load_sensor_components(),
            "microcontrollers": self._load_microcontroller_components(),
            "solar": self._load_solar_components(),
            "activelog": self._load_activelog_components()
        }
        
        # Design templates
        self.design_templates = {
            "solar_camera": self._create_solar_camera_template(),
            "fish_counter": self._create_fish_counter_template(),
            "sensor_node": self._create_sensor_node_template(),
            "activelog_gateway": self._create_activelog_gateway_template(),
            "environmental_monitor": self._create_environmental_monitor_template()
        }
        
        # PCB manufacturing specs
        self.pcb_manufacturing = {
            "standard": {
                "min_track_width": 0.1,  # mm
                "min_via_size": 0.2,  # mm
                "layer_count": 2,
                "thickness": 1.6,  # mm
                "copper_weight": 1.0,  # oz/ft²
                "soldermask_color": "green",
                "silkscreen_color": "white"
            },
            "advanced": {
                "min_track_width": 0.075,  # mm
                "min_via_size": 0.15,  # mm
                "layer_count": 4,
                "thickness": 1.6,  # mm
                "copper_weight": 1.0,  # oz/ft²
                "soldermask_color": "black",
                "silkscreen_color": "white"
            }
        }
    
    def _load_basic_components(self) -> List[Component]:
        """Load basic electronic components library"""
        return [
            Component(
                id="RES_0805_10K",
                name="10kΩ Resistor",
                type="resistor",
                value="10kΩ",
                package="0805",
                manufacturer="Yageo",
                part_number="RC0805FR-0710KL",
                datasheet_url="https://www.yageo.com/documents/recent/PYu-RC_Group_51_RoHS_L_11.pdf",
                price=0.02,
                availability="in_stock",
                footprint={
                    "width": 2.0,
                    "height": 1.25,
                    "pad_width": 0.7,
                    "pad_height": 1.0
                },
                schematic_symbol={
                    "type": "resistor",
                    "width": 10,
                    "height": 4
                },
                specifications={
                    "resistance": "10kΩ",
                    "tolerance": "±1%",
                    "power_rating": "0.125W",
                    "temperature_coefficient": "±100ppm/°C"
                }
            ),
            Component(
                id="CAP_0805_100NF",
                name="100nF Capacitor",
                type="capacitor",
                value="100nF",
                package="0805",
                manufacturer="Murata",
                part_number="GRM21BR71C104KA01L",
                datasheet_url="https://www.murata.com/products/productdata/8796738977822/GRM21BR71C104KA01.pdf",
                price=0.05,
                availability="in_stock",
                footprint={
                    "width": 2.0,
                    "height": 1.25,
                    "pad_width": 0.7,
                    "pad_height": 1.0
                },
                schematic_symbol={
                    "type": "capacitor",
                    "width": 8,
                    "height": 6
                },
                specifications={
                    "capacitance": "100nF",
                    "tolerance": "±10%",
                    "voltage_rating": "16V",
                    "dielectric": "X7R"
                }
            )
        ]
    
    def _load_sensor_components(self) -> List[Component]:
        """Load sensor components library"""
        return [
            Component(
                id="SENSOR_BME280",
                name="BME280 Environmental Sensor",
                type="sensor",
                value="BME280",
                package="LGA8",
                manufacturer="Bosch",
                part_number="BME280",
                datasheet_url="https://www.bosch-sensortec.com/media/boschsensortec/downloads/datasheets/bst-bme280-ds002.pdf",
                price=3.50,
                availability="in_stock",
                footprint={
                    "width": 2.5,
                    "height": 2.5,
                    "pad_width": 0.5,
                    "pad_height": 0.25
                },
                schematic_symbol={
                    "type": "ic",
                    "width": 20,
                    "height": 15,
                    "pins": 8
                },
                specifications={
                    "temperature_range": "-40°C to +85°C",
                    "humidity_range": "0% to 100% RH",
                    "pressure_range": "300 to 1100 hPa",
                    "interface": "I2C/SPI",
                    "supply_voltage": "1.7V to 3.6V"
                }
            ),
            Component(
                id="SENSOR_VL53L0X",
                name="VL53L0X Time-of-Flight Distance Sensor",
                type="sensor",
                value="VL53L0X",
                package="LGA12",
                manufacturer="STMicroelectronics",
                part_number="VL53L0X",
                datasheet_url="https://www.st.com/resource/en/datasheet/vl53l0x.pdf",
                price=5.25,
                availability="in_stock",
                footprint={
                    "width": 4.4,
                    "height": 2.4,
                    "pad_width": 0.4,
                    "pad_height": 0.6
                },
                schematic_symbol={
                    "type": "ic",
                    "width": 25,
                    "height": 15,
                    "pins": 12
                },
                specifications={
                    "ranging_distance": "2m",
                    "accuracy": "±3%",
                    "interface": "I2C",
                    "supply_voltage": "2.6V to 3.5V",
                    "field_of_view": "25°"
                }
            )
        ]
    
    def _load_microcontroller_components(self) -> List[Component]:
        """Load microcontroller components library"""
        return [
            Component(
                id="MCU_ESP32_S3",
                name="ESP32-S3 Microcontroller",
                type="microcontroller",
                value="ESP32-S3",
                package="QFN56",
                manufacturer="Espressif",
                part_number="ESP32-S3-WROOM-1",
                datasheet_url="https://www.espressif.com/sites/default/files/documentation/esp32-s3_datasheet_en.pdf",
                price=4.50,
                availability="in_stock",
                footprint={
                    "width": 18.0,
                    "height": 31.0,
                    "pad_width": 0.9,
                    "pad_height": 1.5
                },
                schematic_symbol={
                    "type": "ic",
                    "width": 40,
                    "height": 30,
                    "pins": 56
                },
                specifications={
                    "cpu_cores": "Dual-core Xtensa LX7",
                    "clock_speed": "240MHz",
                    "flash_memory": "8MB",
                    "ram": "512KB",
                    "wifi": "802.11 b/g/n",
                    "bluetooth": "BLE 5.0",
                    "gpio_pins": 45,
                    "supply_voltage": "3.0V to 3.6V"
                }
            ),
            Component(
                id="MCU_ATMEGA328P",
                name="ATmega328P Microcontroller",
                type="microcontroller",
                value="ATmega328P",
                package="TQFP32",
                manufacturer="Microchip",
                part_number="ATMEGA328P-AU",
                datasheet_url="https://ww1.microchip.com/downloads/en/DeviceDoc/Atmel-7810-Automotive-Microcontrollers-ATmega328P_Datasheet.pdf",
                price=2.25,
                availability="in_stock",
                footprint={
                    "width": 9.0,
                    "height": 9.0,
                    "pad_width": 1.4,
                    "pad_height": 0.27
                },
                schematic_symbol={
                    "type": "ic",
                    "width": 30,
                    "height": 25,
                    "pins": 32
                },
                specifications={
                    "cpu_cores": "Single-core AVR",
                    "clock_speed": "20MHz",
                    "flash_memory": "32KB",
                    "ram": "2KB",
                    "eeprom": "1KB",
                    "gpio_pins": 23,
                    "supply_voltage": "1.8V to 5.5V"
                }
            )
        ]
    
    def _load_solar_components(self) -> List[Component]:
        """Load solar power components library"""
        return [
            Component(
                id="SOLAR_PANEL_6V_2W",
                name="6V 2W Solar Panel",
                type="solar_panel",
                value="6V 2W",
                package="MODULE",
                manufacturer="Voltaic Systems",
                part_number="P126",
                datasheet_url="https://www.voltaicsystems.com/6-watt-solar-panel",
                price=25.00,
                availability="in_stock",
                footprint={
                    "width": 136.0,
                    "height": 110.0,
                    "thickness": 3.0
                },
                schematic_symbol={
                    "type": "solar_panel",
                    "width": 15,
                    "height": 10
                },
                specifications={
                    "max_power": "2W",
                    "voltage_at_max_power": "5.5V",
                    "current_at_max_power": "364mA",
                    "open_circuit_voltage": "6.6V",
                    "short_circuit_current": "400mA",
                    "efficiency": "22%"
                }
            ),
            Component(
                id="BATTERY_LIPO_3S_2200",
                name="LiPo Battery 3S 2200mAh",
                type="battery",
                value="3S 2200mAh",
                package="MODULE",
                manufacturer="Turnigy",
                part_number="TGY-2200-3S-25C",
                datasheet_url="https://hobbyking.com/en_us/turnigy-2200mah-3s-25c-lipo-pack.html",
                price=18.50,
                availability="in_stock",
                footprint={
                    "width": 106.0,
                    "height": 34.0,
                    "thickness": 22.0
                },
                schematic_symbol={
                    "type": "battery",
                    "width": 12,
                    "height": 8
                },
                specifications={
                    "capacity": "2200mAh",
                    "voltage": "11.1V",
                    "discharge_rate": "25C",
                    "charge_rate": "2C",
                    "chemistry": "LiPo",
                    "cells": 3
                }
            )
        ]
    
    def _load_activelog_components(self) -> List[Component]:
        """Load Activelog-specific components library"""
        return [
            Component(
                id="ACTIVELOG_CONNECTOR",
                name="Activelog Data Connector",
                type="connector",
                value="AL-CONN-8P",
                package="CUSTOM",
                manufacturer="Activelog",
                part_number="AL-CONN-8P-V1",
                datasheet_url="https://docs.activelog.com/hardware/connectors/al-conn-8p",
                price=3.75,
                availability="in_stock",
                footprint={
                    "width": 12.0,
                    "height": 8.0,
                    "pad_width": 1.0,
                    "pad_height": 1.5
                },
                schematic_symbol={
                    "type": "connector",
                    "width": 15,
                    "height": 12,
                    "pins": 8
                },
                specifications={
                    "pins": 8,
                    "current_rating": "2A per pin",
                    "voltage_rating": "24V",
                    "contact_material": "Gold plated",
                    "housing_material": "PA66",
                    "ip_rating": "IP67"
                }
            ),
            Component(
                id="ACTIVELOG_RADIO",
                name="Activelog Radio Module",
                type="radio",
                value="AL-RADIO-915",
                package="MODULE",
                manufacturer="Activelog",
                part_number="AL-RADIO-915-V2",
                datasheet_url="https://docs.activelog.com/hardware/radio/al-radio-915",
                price=12.50,
                availability="in_stock",
                footprint={
                    "width": 25.0,
                    "height": 15.0,
                    "thickness": 3.2
                },
                schematic_symbol={
                    "type": "radio",
                    "width": 20,
                    "height": 15
                },
                specifications={
                    "frequency": "915MHz",
                    "power_output": "20dBm",
                    "sensitivity": "-148dBm",
                    "range": "10km line-of-sight",
                    "modulation": "LoRa",
                    "interface": "SPI",
                    "supply_voltage": "3.3V"
                }
            )
        ]
    
    def _create_solar_camera_template(self) -> HardwareDesign:
        """Create solar camera design template"""
        return HardwareDesign(
            id="TEMPLATE_SOLAR_CAMERA",
            name="Solar-Powered Wildlife Camera",
            version="1.0",
            description="Autonomous solar-powered camera system for wildlife monitoring and time-lapse photography",
            category="solar_cameras",
            designer_id="activelog_team",
            components=[
                self.component_libraries["microcontrollers"][0],  # ESP32-S3
                self.component_libraries["solar"][0],  # Solar panel
                self.component_libraries["solar"][1],  # LiPo battery
                self.component_libraries["sensors"][0],  # BME280
                self.component_libraries["activelog"][1]   # Radio module
            ],
            schematic={
                "pages": 1,
                "components": {},
                "nets": {},
                "design_rules": {}
            },
            pcb_layout={
                "board_size": {"width": 80, "height": 60},
                "layer_count": 4,
                "components": {},
                "traces": {},
                "vias": {}
            },
            pcb_layers=[
                PCBLayer(
                    name="Top",
                    type="signal",
                    thickness=0.035,
                    material="copper",
                    copper_weight=1.0,
                    traces=[],
                    vias=[],
                    pads=[]
                )
            ],
            bill_of_materials=[],
            assembly_notes="Assembly requires SMD soldering skills. Camera module connects via ribbon cable.",
            test_procedures="1. Power-on test\n2. Solar charging test\n3. Camera functionality test\n4. Radio transmission test",
            certifications=["CE", "FCC"],
            design_files={
                "schematic": "solar_camera_schematic.pdf",
                "pcb": "solar_camera_pcb.kicad_pcb",
                "gerber": "solar_camera_gerbers.zip",
                "bom": "solar_camera_bom.csv"
            },
            renders=[],
            specifications={
                "camera_resolution": "12MP",
                "video_recording": "1080p@30fps",
                "night_vision": "850nm IR LEDs",
                "trigger_speed": "0.3 seconds",
                "detection_range": "20 meters",
                "battery_life": "6 months",
                "operating_temperature": "-20°C to +60°C"
            },
            power_requirements={
                "input_voltage": "5V - 12V",
                "peak_current": "2A",
                "standby_current": "10mA",
                "solar_panel_min": "2W",
                "battery_capacity_min": "2200mAh"
            },
            environmental_specs={
                "ip_rating": "IP65",
                "operating_humidity": "10% - 95% RH",
                "storage_temperature": "-30°C to +70°C"
            },
            mechanical_specs={
                "enclosure_material": "ABS plastic",
                "dimensions": "120 x 80 x 60 mm",
                "weight": "450g",
                "mounting": "1/4-20 tripod thread"
            },
            interface_specs={
                "wireless": "LoRa 915MHz",
                "data_storage": "microSD up to 128GB",
                "configuration": "Web interface over WiFi",
                "firmware_update": "OTA via WiFi"
            },
            activelog_integration={
                "compatible": True,
                "data_streaming": "Real-time image transmission",
                "remote_config": "Full camera settings",
                "power_management": "Solar charging status",
                "environmental_data": "Temperature, humidity, pressure"
            },
            license_type="Creative Commons BY-SA",
            tags=["solar", "camera", "wildlife", "outdoor", "autonomous"],
            difficulty_level="intermediate",
            estimated_cost=85.50,
            assembly_time_hours=4.0,
            tools_required=["Soldering iron", "SMD tweezers", "Multimeter", "Hot air station"]
        )
    
    def _create_fish_counter_template(self) -> HardwareDesign:
        """Create fish counter design template"""
        return HardwareDesign(
            id="TEMPLATE_FISH_COUNTER",
            name="Automated Fish Counter System",
            version="1.0",
            description="Computer vision-based fish counting system for aquaculture and research",
            category="fish_counters",
            designer_id="activelog_team",
            components=[
                self.component_libraries["microcontrollers"][0],  # ESP32-S3
                self.component_libraries["sensors"][1],  # VL53L0X distance sensor
                self.component_libraries["activelog"][1],  # Radio module
                self.component_libraries["basic"][0],  # Resistor
                self.component_libraries["basic"][1]   # Capacitor
            ],
            schematic={
                "pages": 1,
                "components": {},
                "nets": {},
                "design_rules": {}
            },
            pcb_layout={
                "board_size": {"width": 60, "height": 40},
                "layer_count": 2,
                "components": {},
                "traces": {},
                "vias": {}
            },
            pcb_layers=[
                PCBLayer(
                    name="Top",
                    type="signal",
                    thickness=0.035,
                    material="copper",
                    copper_weight=1.0,
                    traces=[],
                    vias=[],
                    pads=[]
                )
            ],
            bill_of_materials=[],
            assembly_notes="Waterproof enclosure required. Sensor placement critical for accurate counting.",
            test_procedures="1. Sensor calibration\n2. Fish detection test\n3. Counting accuracy validation\n4. Data transmission test",
            certifications=["CE", "IP68"],
            design_files={
                "schematic": "fish_counter_schematic.pdf",
                "pcb": "fish_counter_pcb.kicad_pcb",
                "enclosure": "fish_counter_enclosure.step"
            },
            renders=[],
            specifications={
                "detection_method": "Computer vision + ToF sensor",
                "accuracy": "95%",
                "max_counting_rate": "10 fish/second",
                "species_identification": "Basic size classification",
                "data_logging": "Local storage + cloud sync"
            },
            power_requirements={
                "input_voltage": "12V DC",
                "peak_current": "1.5A",
                "standby_current": "50mA",
                "power_consumption": "3W average"
            },
            environmental_specs={
                "ip_rating": "IP68",
                "operating_temperature": "0°C to +40°C",
                "max_depth": "5 meters"
            },
            mechanical_specs={
                "enclosure_material": "Marine grade aluminum",
                "dimensions": "200 x 150 x 100 mm",
                "weight": "1.2kg",
                "mounting": "Clamp or bolt-on"
            },
            interface_specs={
                "wireless": "LoRa 915MHz",
                "data_storage": "32GB internal",
                "configuration": "Mobile app",
                "alerts": "Real-time notifications"
            },
            activelog_integration={
                "compatible": True,
                "data_streaming": "Fish count data",
                "analytics": "Population trends",
                "alerts": "Unusual activity detection",
                "integration": "Aquaculture management systems"
            },
            license_type="GPL v3",
            tags=["fish", "counting", "aquaculture", "computer-vision", "underwater"],
            difficulty_level="advanced",
            estimated_cost=125.00,
            assembly_time_hours=6.0,
            tools_required=["Soldering iron", "Waterproofing tools", "Calibration equipment"]
        )
    
    def _create_sensor_node_template(self) -> HardwareDesign:
        """Create environmental sensor node template"""
        return HardwareDesign(
            id="TEMPLATE_SENSOR_NODE",
            name="Multi-Sensor Environmental Node",
            version="1.0",
            description="Wireless sensor node for environmental monitoring with multiple sensor inputs",
            category="sensor_packages",
            designer_id="activelog_team",
            components=[
                self.component_libraries["microcontrollers"][1],  # ATmega328P
                self.component_libraries["sensors"][0],  # BME280
                self.component_libraries["activelog"][1],  # Radio module
                self.component_libraries["solar"][1]   # Battery
            ],
            schematic={},
            pcb_layout={"board_size": {"width": 50, "height": 30}},
            pcb_layers=[],
            bill_of_materials=[],
            assembly_notes="Low-power design for long-term deployment",
            test_procedures="Sensor calibration and power consumption test",
            certifications=["CE"],
            design_files={},
            renders=[],
            specifications={
                "sensors": "Temperature, humidity, pressure, light",
                "transmission_range": "10km",
                "battery_life": "2 years",
                "data_rate": "1 sample/minute"
            },
            power_requirements={
                "input_voltage": "3.3V",
                "sleep_current": "10µA",
                "active_current": "50mA"
            },
            environmental_specs={"ip_rating": "IP54"},
            mechanical_specs={"dimensions": "80 x 50 x 25 mm"},
            interface_specs={"wireless": "LoRa"},
            activelog_integration={
                "compatible": True,
                "data_streaming": "Environmental data",
                "power_management": "Battery monitoring"
            },
            license_type="MIT",
            tags=["sensors", "environmental", "wireless", "low-power"],
            difficulty_level="beginner",
            estimated_cost=35.00,
            assembly_time_hours=2.0,
            tools_required=["Soldering iron", "Multimeter"]
        )
    
    def _create_activelog_gateway_template(self) -> HardwareDesign:
        """Create Activelog gateway template"""
        return HardwareDesign(
            id="TEMPLATE_ACTIVELOG_GATEWAY",
            name="Activelog Data Gateway",
            version="1.0",
            description="Central gateway for Activelog device network with cloud connectivity",
            category="activelog_devices",
            designer_id="activelog_team",
            components=[
                self.component_libraries["microcontrollers"][0],  # ESP32-S3
                self.component_libraries["activelog"][0],  # Connector
                self.component_libraries["activelog"][1]   # Radio
            ],
            schematic={},
            pcb_layout={"board_size": {"width": 100, "height": 70}},
            pcb_layers=[],
            bill_of_materials=[],
            assembly_notes="Professional gateway device for network management",
            test_procedures="Network connectivity and device management tests",
            certifications=["CE", "FCC", "IC"],
            design_files={},
            renders=[],
            specifications={
                "network_capacity": "1000 devices",
                "connectivity": "WiFi, Ethernet, Cellular",
                "local_storage": "1TB",
                "processing_power": "Dual-core ARM"
            },
            power_requirements={
                "input_voltage": "12V DC / PoE+",
                "power_consumption": "15W"
            },
            environmental_specs={
                "ip_rating": "IP40",
                "operating_temperature": "0°C to +50°C"
            },
            mechanical_specs={
                "enclosure": "19\" rack mount",
                "dimensions": "482 x 44 x 200 mm"
            },
            interface_specs={
                "ethernet": "Gigabit",
                "wifi": "802.11ac",
                "cellular": "4G LTE",
                "usb": "USB 3.0"
            },
            activelog_integration={
                "compatible": True,
                "role": "Central gateway",
                "features": "Device management, data aggregation, cloud sync"
            },
            license_type="Commercial",
            tags=["gateway", "networking", "activelog", "professional"],
            difficulty_level="advanced",
            estimated_cost=250.00,
            assembly_time_hours=8.0,
            tools_required=["SMD rework station", "Test equipment", "Programming tools"]
        )
    
    def _create_environmental_monitor_template(self) -> HardwareDesign:
        """Create environmental monitoring template"""
        return HardwareDesign(
            id="TEMPLATE_ENV_MONITOR",
            name="Environmental Monitoring Station",
            version="1.0",
            description="Comprehensive environmental monitoring station with weather sensors",
            category="sensor_packages",
            designer_id="activelog_team",
            components=[
                self.component_libraries["microcontrollers"][0],
                self.component_libraries["sensors"][0],
                self.component_libraries["solar"][0],
                self.component_libraries["solar"][1]
            ],
            schematic={},
            pcb_layout={"board_size": {"width": 120, "height": 80}},
            pcb_layers=[],
            bill_of_materials=[],
            assembly_notes="Weather-resistant design for outdoor deployment",
            test_procedures="Full environmental sensor calibration",
            certifications=["CE", "NIST"],
            design_files={},
            renders=[],
            specifications={
                "parameters": "Temperature, humidity, pressure, wind, rain, UV, air quality",
                "accuracy": "Research grade",
                "data_rate": "1 minute intervals",
                "connectivity": "LoRa + WiFi + Cellular backup"
            },
            power_requirements={
                "solar_panel": "20W",
                "battery": "12V 7Ah",
                "power_budget": "5W average"
            },
            environmental_specs={
                "ip_rating": "IP65",
                "wind_resistance": "200 km/h",
                "temperature_range": "-40°C to +70°C"
            },
            mechanical_specs={
                "mounting": "Pole mount with guy wires",
                "height": "2 meters",
                "weight": "15kg"
            },
            interface_specs={
                "data_output": "JSON over MQTT",
                "configuration": "Web interface",
                "calibration": "Remote calibration capability"
            },
            activelog_integration={
                "compatible": True,
                "data_streaming": "Real-time weather data",
                "alerts": "Severe weather warnings",
                "analytics": "Climate trend analysis"
            },
            license_type="GPL v3",
            tags=["weather", "environmental", "monitoring", "research"],
            difficulty_level="advanced",
            estimated_cost=450.00,
            assembly_time_hours=12.0,
            tools_required=["Professional assembly tools", "Calibration equipment"]
        )
    
    async def create_design(self, design_data: Dict[str, Any]) -> HardwareDesign:
        """Create a new hardware design"""
        design = HardwareDesign(
            id=str(uuid.uuid4()),
            name=design_data['name'],
            version=design_data.get('version', '1.0'),
            description=design_data['description'],
            category=design_data['category'],
            designer_id=design_data['designer_id'],
            components=design_data.get('components', []),
            schematic=design_data.get('schematic', {}),
            pcb_layout=design_data.get('pcb_layout', {}),
            pcb_layers=design_data.get('pcb_layers', []),
            bill_of_materials=design_data.get('bill_of_materials', []),
            assembly_notes=design_data.get('assembly_notes', ''),
            test_procedures=design_data.get('test_procedures', ''),
            certifications=design_data.get('certifications', []),
            design_files=design_data.get('design_files', {}),
            renders=design_data.get('renders', []),
            specifications=design_data.get('specifications', {}),
            power_requirements=design_data.get('power_requirements', {}),
            environmental_specs=design_data.get('environmental_specs', {}),
            mechanical_specs=design_data.get('mechanical_specs', {}),
            interface_specs=design_data.get('interface_specs', {}),
            activelog_integration=design_data.get('activelog_integration', {}),
            license_type=design_data.get('license_type', 'MIT'),
            tags=design_data.get('tags', []),
            difficulty_level=design_data.get('difficulty_level', 'intermediate'),
            estimated_cost=design_data.get('estimated_cost', 0.0),
            assembly_time_hours=design_data.get('assembly_time_hours', 1.0),
            tools_required=design_data.get('tools_required', [])
        )
        
        # Save design
        await self.save_design(design)
        
        return design
    
    async def save_design(self, design: HardwareDesign):
        """Save design to storage"""
        design_dir = self.designs_path / design.id
        design_dir.mkdir(exist_ok=True)
        
        # Save design metadata
        with open(design_dir / "design.json", "w") as f:
            json.dump(asdict(design), f, indent=2, default=str)
        
        print(f"Design saved: {design.name} ({design.id})")
    
    async def load_design(self, design_id: str) -> Optional[HardwareDesign]:
        """Load design from storage"""
        design_path = self.designs_path / design_id / "design.json"
        
        if not design_path.exists():
            return None
        
        with open(design_path, "r") as f:
            data = json.load(f)
        
        return HardwareDesign(**data)
    
    async def generate_schematic_preview(self, design: HardwareDesign) -> str:
        """Generate schematic preview image"""
        fig, ax = plt.subplots(1, 1, figsize=(12, 8))
        
        # Simplified schematic generation
        # In a real implementation, this would use proper EDA tools
        
        components = design.components
        if not components:
            ax.text(0.5, 0.5, 'No components defined', 
                   ha='center', va='center', transform=ax.transAxes)
        else:
            # Draw simplified component layout
            cols = int(np.sqrt(len(components))) + 1
            for i, component in enumerate(components):
                x = (i % cols) * 2
                y = (i // cols) * 2
                
                # Draw component box
                rect = plt.Rectangle((x, y), 1.5, 0.8, 
                                   fill=False, edgecolor='blue')
                ax.add_patch(rect)
                
                # Add component name
                ax.text(x + 0.75, y + 0.4, component.name, 
                       ha='center', va='center', fontsize=8)
        
        ax.set_xlim(-0.5, cols * 2)
        ax.set_ylim(-0.5, ((len(components) // cols) + 1) * 2)
        ax.set_aspect('equal')
        ax.set_title(f"Schematic Preview: {design.name}")
        ax.grid(True, alpha=0.3)
        
        # Save preview
        preview_path = self.designs_path / design.id / "schematic_preview.png"
        plt.savefig(preview_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        return str(preview_path)
    
    async def generate_pcb_preview(self, design: HardwareDesign) -> str:
        """Generate PCB layout preview"""
        fig, ax = plt.subplots(1, 1, figsize=(10, 8))
        
        # PCB board outline
        board = design.pcb_layout
        if board:
            width = board.get("board_size", {}).get("width", 80)
            height = board.get("board_size", {}).get("height", 60)
            
            # Draw board outline
            rect = plt.Rectangle((0, 0), width, height, 
                               fill=False, edgecolor='green', linewidth=2)
            ax.add_patch(rect)
            
            # Draw simplified component placement
            components = design.components
            if components:
                for i, component in enumerate(components):
                    # Random placement for demo
                    x = np.random.uniform(5, width - 15)
                    y = np.random.uniform(5, height - 10)
                    
                    footprint = component.footprint
                    comp_width = footprint.get("width", 5)
                    comp_height = footprint.get("height", 3)
                    
                    # Draw component footprint
                    comp_rect = plt.Rectangle((x, y), comp_width, comp_height,
                                            fill=True, facecolor='lightblue', 
                                            edgecolor='blue', alpha=0.7)
                    ax.add_patch(comp_rect)
                    
                    # Add component reference
                    ax.text(x + comp_width/2, y + comp_height/2, 
                           component.type[:3].upper(),
                           ha='center', va='center', fontsize=6)
        
        ax.set_xlim(-5, width + 5 if board else 85)
        ax.set_ylim(-5, height + 5 if board else 65)
        ax.set_aspect('equal')
        ax.set_title(f"PCB Layout Preview: {design.name}")
        ax.set_facecolor('darkgreen')
        ax.grid(True, alpha=0.2, color='white')
        
        # Save preview
        preview_path = self.designs_path / design.id / "pcb_preview.png"
        plt.savefig(preview_path, dpi=150, bbox_inches='tight', 
                   facecolor='darkgreen')
        plt.close()
        
        return str(preview_path)
    
    async def generate_bom(self, design: HardwareDesign) -> str:
        """Generate Bill of Materials"""
        bom_data = []
        total_cost = 0.0
        
        # Component summary
        component_counts = {}
        for component in design.components:
            key = f"{component.manufacturer}_{component.part_number}"
            if key in component_counts:
                component_counts[key]['quantity'] += 1
            else:
                component_counts[key] = {
                    'component': component,
                    'quantity': 1
                }
        
        # Generate BOM entries
        for item in component_counts.values():
            component = item['component']
            quantity = item['quantity']
            line_cost = component.price * quantity
            total_cost += line_cost
            
            bom_data.append({
                'part_number': component.part_number,
                'manufacturer': component.manufacturer,
                'description': component.name,
                'value': component.value,
                'package': component.package,
                'quantity': quantity,
                'unit_price': component.price,
                'line_cost': line_cost,
                'datasheet': component.datasheet_url
            })
        
        # Save BOM as CSV
        bom_path = self.designs_path / design.id / "bom.csv"
        import csv
        with open(bom_path, "w", newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'part_number', 'manufacturer', 'description', 'value', 
                'package', 'quantity', 'unit_price', 'line_cost', 'datasheet'
            ])
            writer.writeheader()
            writer.writerows(bom_data)
        
        # Update design cost estimate
        design.estimated_cost = total_cost * 1.15  # Add 15% margin
        
        return str(bom_path)
    
    async def validate_design(self, design: HardwareDesign) -> Dict[str, Any]:
        """Validate hardware design for common issues"""
        issues = []
        warnings = []
        
        # Check component compatibility
        voltage_levels = set()
        for component in design.components:
            specs = component.specifications
            if 'supply_voltage' in specs:
                voltage_levels.add(specs['supply_voltage'])
        
        if len(voltage_levels) > 2:
            warnings.append("Multiple voltage levels detected - ensure proper power regulation")
        
        # Check power budget
        if design.power_requirements:
            peak_current = design.power_requirements.get('peak_current')
            input_voltage = design.power_requirements.get('input_voltage')
            
            if peak_current and input_voltage:
                power_estimate = float(peak_current.replace('A', '')) * float(input_voltage.replace('V', ''))
                if power_estimate > 10:  # 10W threshold
                    warnings.append(f"High power consumption: {power_estimate:.1f}W - consider thermal management")
        
        # Check Activelog compatibility
        if design.activelog_integration.get('compatible') and not design.activelog_integration.get('data_streaming'):
            warnings.append("Activelog compatibility claimed but no data streaming interface defined")
        
        # Check certification requirements
        if 'FCC' in design.certifications and not any('radio' in comp.type for comp in design.components):
            warnings.append("FCC certification listed but no radio components found")
        
        # Check difficulty vs complexity
        component_count = len(design.components)
        if design.difficulty_level == 'beginner' and component_count > 10:
            warnings.append("High component count for beginner difficulty level")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "component_count": component_count,
            "estimated_cost": design.estimated_cost,
            "complexity_score": min(100, component_count * 5 + len(design.tags) * 2)
        }
    
    def get_design_templates(self) -> List[HardwareDesign]:
        """Get all available design templates"""
        return list(self.design_templates.values())
    
    def get_component_library(self, library_name: str) -> List[Component]:
        """Get components from a specific library"""
        return self.component_libraries.get(library_name, [])
    
    def search_components(self, query: str, filters: Dict[str, Any] = None) -> List[Component]:
        """Search components across all libraries"""
        all_components = []
        for library in self.component_libraries.values():
            all_components.extend(library)
        
        if not query:
            return all_components
        
        # Simple text search
        query_lower = query.lower()
        matches = []
        
        for component in all_components:
            score = 0
            if query_lower in component.name.lower():
                score += 3
            if query_lower in component.type.lower():
                score += 2
            if query_lower in component.manufacturer.lower():
                score += 1
            if any(query_lower in tag.lower() for tag in component.specifications.keys()):
                score += 1
            
            if score > 0:
                matches.append((score, component))
        
        # Sort by relevance
        matches.sort(key=lambda x: x[0], reverse=True)
        return [comp for _, comp in matches]

# Example usage and testing
async def main():
    design_system = HardwareDesignSystem()
    
    # Create a custom design
    custom_design_data = {
        "name": "Custom Environmental Sensor",
        "description": "A custom environmental monitoring device",
        "category": "sensor_packages",
        "designer_id": "user123",
        "components": design_system.component_libraries["sensors"][:2],
        "specifications": {
            "measurement_range": "-40°C to +85°C",
            "accuracy": "±0.5°C"
        },
        "power_requirements": {
            "input_voltage": "3.3V",
            "current": "50mA"
        },
        "tags": ["temperature", "humidity", "outdoor"],
        "difficulty_level": "intermediate",
        "estimated_cost": 25.00,
        "assembly_time_hours": 2.0,
        "tools_required": ["Soldering iron", "Multimeter"]
    }
    
    design = await design_system.create_design(custom_design_data)
    print(f"Created design: {design.name}")
    
    # Generate previews
    await design_system.generate_schematic_preview(design)
    await design_system.generate_pcb_preview(design)
    await design_system.generate_bom(design)
    
    # Validate design
    validation = await design_system.validate_design(design)
    print(f"Validation result: {validation}")
    
    # Search components
    components = design_system.search_components("temperature sensor")
    print(f"Found {len(components)} temperature sensor components")

if __name__ == "__main__":
    asyncio.run(main())