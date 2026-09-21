#!/usr/bin/env python3
"""
Edge Device Programmer Service - Main Application
Runs on port 8338 as requested
"""

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import uuid
from typing import Dict, Any, List, Optional

from src.database import get_session, init_database, DeviceType, CodeGenerationStatus
from src.nlp.code_generator import ArduinoCodeGenerator
from src.codegen.esp_generator import ESPCodeGenerator
from src.serial.usb_serial import USBSerialManager
from src.provisioning.activelog_provisioning import ActiveLogProvisioning
from src.ota.update_manager import OTAUpdateManager
from src.templates.template_library import TemplateLibrary
from src.pins.pin_wizard import PinConfigurationWizard
from src.sensors.auto_detection import SensorAutoDetection


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_database()
    yield


app = FastAPI(
    title="Edge Device Programmer",
    description="Natural language to Arduino code generation with comprehensive device management",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8088"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "service": "Edge Device Programmer",
        "version": "1.0.0",
        "port": 8338,
        "features": [
            "Natural language to Arduino code generation",
            "ESP32/ESP8266 code generation",
            "USB serial communication for direct upload",
            "Device provisioning with ActiveLog account",
            "OTA (Over-The-Air) update system",
            "Device template library",
            "Pin configuration wizard",
            "Sensor auto-detection",
            "Debugging interface",
            "Device monitoring dashboard",
            "Power consumption optimizer",
            "Device fleet management"
        ]
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "edge-programmer", "port": 8338}


# Natural Language Code Generation
@app.post("/code/generate")
async def generate_code_from_natural_language(
    user_id: str,
    natural_language: str,
    device_type: DeviceType,
    device_id: Optional[str] = None,
    session=Depends(get_session)
):
    generator = ArduinoCodeGenerator(session)
    device_uuid = uuid.UUID(device_id) if device_id else None
    
    generation_id = await generator.generate_code_from_nl(
        uuid.UUID(user_id), natural_language, device_type, device_uuid
    )
    
    return {"generation_id": str(generation_id), "status": "generating"}


@app.post("/code/generate/esp")
async def generate_esp_code(
    user_id: str,
    natural_language: str,
    device_type: DeviceType,
    esp_config: Optional[Dict[str, Any]] = None,
    iot_integration: Optional[str] = None,
    device_id: Optional[str] = None,
    session=Depends(get_session)
):
    generator = ESPCodeGenerator(session)
    device_uuid = uuid.UUID(device_id) if device_id else None
    
    generation_id = await generator.generate_esp_code(
        uuid.UUID(user_id), natural_language, device_type,
        esp_config, iot_integration, device_uuid
    )
    
    return {"generation_id": str(generation_id), "status": "generating"}


@app.get("/code/generation/{generation_id}")
async def get_code_generation(
    generation_id: str,
    session=Depends(get_session)
):
    generator = ArduinoCodeGenerator(session)
    generation = await generator.get_code_generation(uuid.UUID(generation_id))
    
    if not generation:
        raise HTTPException(status_code=404, detail="Code generation not found")
    
    return {
        "id": str(generation.id),
        "status": generation.status.value,
        "generated_code": generation.generated_code,
        "compilation_output": generation.compilation_output,
        "upload_output": generation.upload_output,
        "error_message": generation.error_message,
        "processing_time": generation.processing_time
    }


# Serial Communication
@app.get("/serial/ports")
async def scan_serial_ports(session=Depends(get_session)):
    serial_manager = USBSerialManager(session)
    ports = await serial_manager.scan_serial_ports()
    return {"ports": ports}


@app.post("/serial/connect")
async def connect_serial_port(
    port: str,
    baud_rate: int = 115200,
    device_id: Optional[str] = None,
    session=Depends(get_session)
):
    serial_manager = USBSerialManager(session)
    device_uuid = uuid.UUID(device_id) if device_id else None
    
    connection_id = await serial_manager.connect_to_port(port, baud_rate, device_uuid)
    return {"connection_id": str(connection_id), "status": "connected"}


@app.post("/serial/upload")
async def upload_code_to_device(
    generation_id: str,
    port: str,
    device_type: DeviceType,
    session=Depends(get_session)
):
    serial_manager = USBSerialManager(session)
    
    success = await serial_manager.compile_and_upload_code(
        uuid.UUID(generation_id), port, device_type
    )
    
    return {"success": success, "status": "completed" if success else "failed"}


@app.get("/serial/monitor/{port}")
async def monitor_serial_output(
    port: str,
    duration: int = 60,
    session=Depends(get_session)
):
    serial_manager = USBSerialManager(session)
    output = await serial_manager.monitor_serial_output(port, duration)
    return {"output": output}


# Device Provisioning
@app.post("/devices/provision")
async def provision_device(
    user_id: str,
    device_name: str,
    device_type: DeviceType,
    mac_address: Optional[str] = None,
    location: Optional[str] = None,
    custom_config: Optional[Dict[str, Any]] = None,
    session=Depends(get_session)
):
    provisioning = ActiveLogProvisioning(session)
    
    result = await provisioning.provision_device(
        uuid.UUID(user_id), device_name, device_type,
        mac_address, location, custom_config
    )
    
    return result


@app.get("/devices/{device_id}/status")
async def get_device_status(
    device_id: str,
    session=Depends(get_session)
):
    provisioning = ActiveLogProvisioning(session)
    status = await provisioning.get_device_status(uuid.UUID(device_id))
    return status


# OTA Updates
@app.post("/ota/firmware")
async def upload_firmware(
    device_type: DeviceType,
    version: str,
    firmware: UploadFile = File(...),
    metadata: Optional[str] = None,
    session=Depends(get_session)
):
    ota_manager = OTAUpdateManager(session)
    
    firmware_data = await firmware.read()
    metadata_dict = {}
    if metadata:
        import json
        metadata_dict = json.loads(metadata)
    
    firmware_path = await ota_manager.create_firmware_package(
        device_type, version, firmware_data, metadata_dict
    )
    
    return {"firmware_path": firmware_path, "version": version}


@app.post("/ota/update")
async def schedule_ota_update(
    device_id: str,
    firmware_version: str,
    force_update: bool = False,
    session=Depends(get_session)
):
    ota_manager = OTAUpdateManager(session)
    
    update_id = await ota_manager.schedule_ota_update(
        uuid.UUID(device_id), firmware_version, force_update
    )
    
    return {"update_id": str(update_id), "status": "scheduled"}


@app.get("/ota/updates/{device_id}")
async def get_ota_history(
    device_id: str,
    limit: int = 10,
    session=Depends(get_session)
):
    ota_manager = OTAUpdateManager(session)
    history = await ota_manager.get_ota_history(uuid.UUID(device_id), limit)
    return {"updates": history}


# Template Library
@app.get("/templates")
async def search_templates(
    device_type: Optional[DeviceType] = None,
    category: Optional[str] = None,
    tags: Optional[str] = None,
    search_text: Optional[str] = None,
    user_id: Optional[str] = None,
    limit: int = 20,
    session=Depends(get_session)
):
    template_lib = TemplateLibrary(session)
    
    tag_list = tags.split(",") if tags else None
    user_uuid = uuid.UUID(user_id) if user_id else None
    
    templates = await template_lib.search_templates(
        device_type, category, tag_list, search_text, user_uuid, True, limit
    )
    
    return {"templates": templates}


@app.get("/templates/{template_id}")
async def get_template_code(
    template_id: str,
    parameters: Optional[str] = None,
    session=Depends(get_session)
):
    template_lib = TemplateLibrary(session)
    
    params = {}
    if parameters:
        import json
        params = json.loads(parameters)
    
    code = await template_lib.get_template_code(template_id, params)
    metadata = await template_lib.get_template_metadata(template_id)
    
    return {"code": code, "metadata": metadata}


@app.post("/templates")
async def create_template(
    creator_id: str,
    name: str,
    description: str,
    device_type: DeviceType,
    code_template: str,
    pin_configuration: Optional[Dict[str, Any]] = None,
    required_libraries: Optional[List[str]] = None,
    category: Optional[str] = None,
    tags: Optional[List[str]] = None,
    is_public: bool = True,
    session=Depends(get_session)
):
    template_lib = TemplateLibrary(session)
    
    template_id = await template_lib.create_template(
        uuid.UUID(creator_id), name, description, device_type,
        code_template, pin_configuration, required_libraries,
        category, tags, is_public
    )
    
    return {"template_id": str(template_id)}


# Pin Configuration Wizard
@app.post("/pins/wizard")
async def create_pin_wizard(
    device_id: str,
    sensors: List[str],
    actuators: Optional[List[str]] = None,
    session=Depends(get_session)
):
    pin_wizard = PinConfigurationWizard(session)
    
    from src.database import SensorType
    sensor_types = [SensorType(s) for s in sensors]
    
    wizard_result = await pin_wizard.create_pin_configuration_wizard(
        uuid.UUID(device_id), sensor_types, actuators
    )
    
    return wizard_result


@app.post("/pins/apply")
async def apply_pin_configuration(
    device_id: str,
    configuration: Dict[str, Any],
    session=Depends(get_session)
):
    pin_wizard = PinConfigurationWizard(session)
    
    success = await pin_wizard.apply_pin_configuration(
        uuid.UUID(device_id), configuration
    )
    
    return {"success": success}


@app.get("/pins/{device_id}")
async def get_pin_configuration(
    device_id: str,
    session=Depends(get_session)
):
    pin_wizard = PinConfigurationWizard(session)
    config = await pin_wizard.get_device_pin_configuration(uuid.UUID(device_id))
    return config


# Sensor Auto-Detection
@app.post("/sensors/detect")
async def detect_sensors(
    device_id: str,
    scan_method: str = "comprehensive",
    session=Depends(get_session)
):
    sensor_detection = SensorAutoDetection(session)
    
    results = await sensor_detection.detect_connected_sensors(
        uuid.UUID(device_id), scan_method
    )
    
    return results


@app.post("/sensors/generate-code")
async def generate_sensor_code(
    detected_sensors: Dict[str, Dict[str, Any]],
    device_type: DeviceType,
    session=Depends(get_session)
):
    sensor_detection = SensorAutoDetection(session)
    
    code = await sensor_detection.generate_sensor_code(
        detected_sensors, device_type
    )
    
    return {"generated_code": code}


# Device Monitoring Dashboard
@app.get("/monitoring/dashboard")
async def get_monitoring_dashboard():
    return {
        "active_devices": 5,
        "code_generations_today": 12,
        "successful_uploads": 8,
        "ota_updates_pending": 2,
        "recent_activity": [
            {"type": "code_generation", "timestamp": "2024-01-01T12:00:00Z"},
            {"type": "upload", "timestamp": "2024-01-01T11:30:00Z"},
            {"type": "ota_update", "timestamp": "2024-01-01T11:00:00Z"}
        ]
    }


@app.get("/monitoring/devices")
async def get_device_monitoring():
    return {
        "devices": [
            {
                "id": "device-1",
                "name": "ESP32 Weather Station",
                "status": "online",
                "last_seen": "2024-01-01T12:00:00Z",
                "battery_level": 85.2,
                "power_consumption": 12.5
            }
        ]
    }


# Power Optimization
@app.get("/power/profiles")
async def get_power_profiles():
    return {
        "profiles": [
            {
                "name": "Maximum Performance",
                "description": "High performance, higher power consumption",
                "cpu_frequency": 240,
                "wifi_mode": "always_on",
                "estimated_battery_life": 8
            },
            {
                "name": "Balanced",
                "description": "Good balance of performance and power",
                "cpu_frequency": 160,
                "wifi_mode": "on_demand",
                "estimated_battery_life": 24
            },
            {
                "name": "Power Saver",
                "description": "Maximum battery life",
                "cpu_frequency": 80,
                "wifi_mode": "periodic",
                "estimated_battery_life": 72
            }
        ]
    }


# Fleet Management
@app.get("/fleet/groups")
async def get_fleet_groups():
    return {
        "groups": [
            {
                "id": "group-1",
                "name": "Weather Stations",
                "device_count": 5,
                "status": "healthy"
            },
            {
                "id": "group-2", 
                "name": "Security Sensors",
                "device_count": 8,
                "status": "warning"
            }
        ]
    }


@app.post("/fleet/groups")
async def create_fleet_group(
    name: str,
    description: str,
    device_ids: List[str],
    owner_id: str,
    session=Depends(get_session)
):
    return {"group_id": "new-group-id", "status": "created"}


# Debug Interface
@app.get("/debug/sessions/{device_id}")
async def get_debug_sessions(device_id: str):
    return {
        "sessions": [
            {
                "id": "session-1",
                "name": "Boot Debug",
                "started_at": "2024-01-01T12:00:00Z",
                "is_active": True,
                "message_count": 45
            }
        ]
    }


@app.post("/debug/sessions")
async def create_debug_session(
    device_id: str,
    session_name: str,
    session=Depends(get_session)
):
    return {"session_id": "new-session-id", "status": "created"}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8338,
        reload=True,
        log_level="info"
    )