import asyncio
import csv
import json
import time
import uuid
import qrcode
import random
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime
from io import StringIO, BytesIO
import base64
import hashlib

class ProvisioningMethod(Enum):
    CSV_IMPORT = "csv_import"
    QR_CODE_SCAN = "qr_code_scan"
    NFC_TAP = "nfc_tap"
    TEMPLATE_CLONE = "template_clone"
    BATCH_DISCOVERY = "batch_discovery"
    API_IMPORT = "api_import"

class ProvisioningStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

class ValidationLevel(Enum):
    BASIC = "basic"
    STRICT = "strict"
    PERMISSIVE = "permissive"

@dataclass
class DeviceTemplate:
    template_id: str
    name: str
    category: str
    interface: str
    default_config: Dict[str, Any]
    driver_info: Dict[str, Any]
    tags: List[str]
    description: str
    created_by: str
    created_at: datetime
    usage_count: int = 0
    
@dataclass
class BulkDevice:
    device_id: str
    name: str
    template_id: Optional[str] = None
    override_config: Optional[Dict[str, Any]] = None
    group_assignments: List[str] = None
    custom_properties: Dict[str, Any] = None
    expected_location: Optional[str] = None
    provisioning_data: Optional[str] = None  # QR code data, NFC data, etc.
    
    def __post_init__(self):
        if self.group_assignments is None:
            self.group_assignments = []
        if self.custom_properties is None:
            self.custom_properties = {}

@dataclass
class ProvisioningJob:
    job_id: str
    name: str
    method: ProvisioningMethod
    devices: List[BulkDevice]
    template: Optional[DeviceTemplate] = None
    created_by: str = ""
    created_at: datetime = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: ProvisioningStatus = ProvisioningStatus.PENDING
    progress: float = 0.0
    results: Dict[str, Any] = None
    errors: List[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.results is None:
            self.results = {}
        if self.errors is None:
            self.errors = []

@dataclass
class DeviceGroup:
    group_id: str
    name: str
    description: str
    policies: Dict[str, Any]
    member_count: int
    created_at: datetime
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []

@dataclass
class ProvisioningPolicy:
    policy_id: str
    name: str
    rules: Dict[str, Any]
    validation_level: ValidationLevel
    auto_approve: bool
    require_verification: bool
    allowed_groups: List[str]
    inheritance_rules: Dict[str, Any]

class CSVImporter:
    def __init__(self):
        self.required_columns = ["name", "category", "interface"]
        self.optional_columns = [
            "manufacturer", "model", "address", "driver", "template", 
            "group", "location", "description", "tags", "config_json"
        ]
        
    def validate_csv(self, csv_content: str) -> Dict[str, Any]:
        """Validate CSV structure and content"""
        try:
            csv_reader = csv.DictReader(StringIO(csv_content))
            headers = csv_reader.fieldnames or []
            
            # Check required columns
            missing_columns = [col for col in self.required_columns if col not in headers]
            if missing_columns:
                return {
                    "valid": False,
                    "error": f"Missing required columns: {missing_columns}",
                    "missing_columns": missing_columns
                }
            
            # Validate rows
            rows = list(csv_reader)
            validation_errors = []
            
            for i, row in enumerate(rows, 1):
                row_errors = self._validate_row(row, i)
                validation_errors.extend(row_errors)
            
            return {
                "valid": len(validation_errors) == 0,
                "total_rows": len(rows),
                "headers": headers,
                "errors": validation_errors,
                "preview": rows[:5]  # First 5 rows for preview
            }
            
        except Exception as e:
            return {
                "valid": False,
                "error": f"CSV parsing error: {str(e)}"
            }
    
    def _validate_row(self, row: Dict[str, str], row_number: int) -> List[str]:
        """Validate individual CSV row"""
        errors = []
        
        # Required field validation
        for field in self.required_columns:
            if not row.get(field, "").strip():
                errors.append(f"Row {row_number}: '{field}' is required")
        
        # Category validation
        valid_categories = ["sensor", "actuator", "controller", "display", "storage", "network", "industrial", "medical"]
        if row.get("category") and row["category"].lower() not in valid_categories:
            errors.append(f"Row {row_number}: Invalid category '{row['category']}'")
        
        # Interface validation
        valid_interfaces = ["usb", "serial", "i2c", "spi", "ethernet", "wifi", "bluetooth", "can", "modbus"]
        if row.get("interface") and row["interface"].lower() not in valid_interfaces:
            errors.append(f"Row {row_number}: Invalid interface '{row['interface']}'")
        
        # JSON validation for config field
        if row.get("config_json"):
            try:
                json.loads(row["config_json"])
            except json.JSONDecodeError:
                errors.append(f"Row {row_number}: Invalid JSON in config_json field")
        
        return errors
    
    def parse_csv(self, csv_content: str) -> List[BulkDevice]:
        """Parse CSV into BulkDevice objects"""
        csv_reader = csv.DictReader(StringIO(csv_content))
        devices = []
        
        for i, row in enumerate(csv_reader, 1):
            try:
                device_id = row.get("device_id") or f"bulk_device_{uuid.uuid4().hex[:8]}"
                
                # Parse configuration JSON
                config = {}
                if row.get("config_json"):
                    try:
                        config = json.loads(row["config_json"])
                    except json.JSONDecodeError:
                        config = {}
                
                # Parse tags
                tags = []
                if row.get("tags"):
                    tags = [tag.strip() for tag in row["tags"].split(",")]
                
                # Parse groups
                groups = []
                if row.get("group"):
                    groups = [group.strip() for group in row["group"].split(",")]
                
                device = BulkDevice(
                    device_id=device_id,
                    name=row["name"].strip(),
                    group_assignments=groups,
                    custom_properties={
                        "category": row.get("category", "").lower(),
                        "interface": row.get("interface", "").lower(),
                        "manufacturer": row.get("manufacturer", ""),
                        "model": row.get("model", ""),
                        "address": row.get("address", ""),
                        "driver": row.get("driver", ""),
                        "location": row.get("location", ""),
                        "description": row.get("description", ""),
                        "tags": tags,
                        "config": config,
                        "row_number": i
                    }
                )
                
                devices.append(device)
                
            except Exception as e:
                print(f"Error parsing row {i}: {e}")
                continue
        
        return devices

class QRCodeGenerator:
    def __init__(self):
        self.qr_version = 1
        self.error_correction = qrcode.constants.ERROR_CORRECT_M
        self.box_size = 10
        self.border = 4
    
    def generate_device_qr(self, device_info: Dict[str, Any]) -> str:
        """Generate QR code for device provisioning"""
        # Create provisioning data structure
        provisioning_data = {
            "type": "device_provisioning",
            "version": "1.0",
            "device": device_info,
            "timestamp": datetime.now().isoformat(),
            "checksum": hashlib.sha256(json.dumps(device_info, sort_keys=True).encode()).hexdigest()[:16]
        }
        
        # Create QR code
        qr = qrcode.QRCode(
            version=self.qr_version,
            error_correction=self.error_correction,
            box_size=self.box_size,
            border=self.border
        )
        
        qr.add_data(json.dumps(provisioning_data))
        qr.make(fit=True)
        
        # Generate image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        return f"data:image/png;base64,{img_str}"
    
    def generate_batch_qr_codes(self, devices: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """Generate QR codes for multiple devices"""
        qr_codes = []
        
        for device in devices:
            qr_data = self.generate_device_qr(device)
            qr_codes.append({
                "device_id": device.get("device_id", "unknown"),
                "name": device.get("name", "Unknown Device"),
                "qr_code": qr_data,
                "provisioning_url": f"https://hardware-wizard.activelog.ai/provision/{device.get('device_id')}"
            })
        
        return qr_codes
    
    def decode_qr_data(self, qr_data: str) -> Dict[str, Any]:
        """Decode QR code provisioning data"""
        try:
            data = json.loads(qr_data)
            
            # Validate structure
            if data.get("type") != "device_provisioning":
                raise ValueError("Invalid QR code type")
            
            # Verify checksum
            device_info = data.get("device", {})
            expected_checksum = hashlib.sha256(json.dumps(device_info, sort_keys=True).encode()).hexdigest()[:16]
            
            if data.get("checksum") != expected_checksum:
                raise ValueError("QR code checksum validation failed")
            
            return data
            
        except Exception as e:
            raise ValueError(f"Failed to decode QR data: {e}")

class NFCHandler:
    def __init__(self):
        self.ndef_record_type = "text/plain"
        
    def create_nfc_data(self, device_info: Dict[str, Any]) -> str:
        """Create NFC NDEF data for device provisioning"""
        # Create compact provisioning data for NFC
        nfc_data = {
            "id": device_info.get("device_id"),
            "name": device_info.get("name"),
            "type": device_info.get("category"),
            "if": device_info.get("interface"),  # Abbreviated for space
            "cfg": device_info.get("config", {}),
            "ts": int(datetime.now().timestamp())
        }
        
        # Create JSON string
        json_data = json.dumps(nfc_data, separators=(',', ':'))
        
        # Add protocol identifier
        return f"hw-provision:{json_data}"
    
    def parse_nfc_data(self, nfc_data: str) -> Dict[str, Any]:
        """Parse NFC provisioning data"""
        try:
            if not nfc_data.startswith("hw-provision:"):
                raise ValueError("Invalid NFC provisioning data format")
            
            json_data = nfc_data[13:]  # Remove prefix
            data = json.loads(json_data)
            
            # Expand abbreviated fields
            expanded_data = {
                "device_id": data.get("id"),
                "name": data.get("name"),
                "category": data.get("type"),
                "interface": data.get("if"),
                "config": data.get("cfg", {}),
                "timestamp": data.get("ts")
            }
            
            return expanded_data
            
        except Exception as e:
            raise ValueError(f"Failed to parse NFC data: {e}")

class TemplateManager:
    def __init__(self):
        self.templates = {}
        self.template_usage = {}
        
        # Create some default templates
        self._create_default_templates()
    
    def _create_default_templates(self):
        """Create default device templates"""
        templates = [
            DeviceTemplate(
                template_id="arduino_sensor",
                name="Arduino Sensor Template",
                category="sensor",
                interface="serial",
                default_config={
                    "baud_rate": 115200,
                    "data_bits": 8,
                    "stop_bits": 1,
                    "parity": "none",
                    "sampling_rate": 1.0,
                    "auto_start": True
                },
                driver_info={
                    "name": "arduino_serial_driver",
                    "version": "1.2.0",
                    "language": "python"
                },
                tags=["arduino", "sensor", "serial"],
                description="Standard template for Arduino-based sensors with serial communication",
                created_by="system",
                created_at=datetime.now()
            ),
            DeviceTemplate(
                template_id="raspberry_pi_controller",
                name="Raspberry Pi Controller Template",
                category="controller",
                interface="ethernet",
                default_config={
                    "port": 22,
                    "protocol": "ssh",
                    "timeout": 30,
                    "gpio_pins": list(range(2, 28)),
                    "i2c_enabled": True,
                    "spi_enabled": True
                },
                driver_info={
                    "name": "raspberry_pi_driver",
                    "version": "2.1.0",
                    "language": "python"
                },
                tags=["raspberry-pi", "controller", "gpio"],
                description="Template for Raspberry Pi devices with GPIO and communication interfaces",
                created_by="system",
                created_at=datetime.now()
            ),
            DeviceTemplate(
                template_id="industrial_modbus",
                name="Industrial Modbus Device Template",
                category="industrial",
                interface="modbus",
                default_config={
                    "slave_id": 1,
                    "baud_rate": 9600,
                    "data_bits": 8,
                    "stop_bits": 1,
                    "parity": "none",
                    "timeout": 3000,
                    "register_layout": {
                        "holding_registers": 100,
                        "input_registers": 50
                    }
                },
                driver_info={
                    "name": "modbus_rtu_driver",
                    "version": "1.5.0",
                    "language": "python"
                },
                tags=["industrial", "modbus", "scada"],
                description="Template for industrial Modbus RTU devices",
                created_by="system",
                created_at=datetime.now()
            )
        ]
        
        for template in templates:
            self.templates[template.template_id] = template
    
    def get_template(self, template_id: str) -> Optional[DeviceTemplate]:
        """Get device template"""
        return self.templates.get(template_id)
    
    def list_templates(self, category: str = None, interface: str = None) -> List[DeviceTemplate]:
        """List available templates with optional filtering"""
        templates = list(self.templates.values())
        
        if category:
            templates = [t for t in templates if t.category == category]
        
        if interface:
            templates = [t for t in templates if t.interface == interface]
        
        # Sort by usage count (most used first)
        templates.sort(key=lambda t: self.template_usage.get(t.template_id, 0), reverse=True)
        
        return templates
    
    def create_template(self, template: DeviceTemplate) -> bool:
        """Create new device template"""
        if template.template_id in self.templates:
            return False
        
        self.templates[template.template_id] = template
        self.template_usage[template.template_id] = 0
        return True
    
    def clone_template(self, template_id: str, new_name: str, modifications: Dict[str, Any] = None) -> Optional[str]:
        """Clone existing template with modifications"""
        original = self.get_template(template_id)
        if not original:
            return None
        
        new_template_id = f"{template_id}_clone_{uuid.uuid4().hex[:8]}"
        
        # Create cloned template
        cloned_config = original.default_config.copy()
        if modifications:
            cloned_config.update(modifications.get("config", {}))
        
        cloned_template = DeviceTemplate(
            template_id=new_template_id,
            name=new_name,
            category=modifications.get("category", original.category),
            interface=modifications.get("interface", original.interface),
            default_config=cloned_config,
            driver_info=original.driver_info.copy(),
            tags=original.tags + modifications.get("additional_tags", []),
            description=modifications.get("description", f"Cloned from {original.name}"),
            created_by=modifications.get("created_by", "user"),
            created_at=datetime.now()
        )
        
        self.templates[new_template_id] = cloned_template
        self.template_usage[new_template_id] = 0
        
        return new_template_id
    
    def update_usage(self, template_id: str, count: int = 1):
        """Update template usage statistics"""
        if template_id in self.templates:
            self.template_usage[template_id] = self.template_usage.get(template_id, 0) + count

class GroupManager:
    def __init__(self):
        self.groups = {}
        self.group_memberships = {}  # device_id -> [group_ids]
        
        # Create default groups
        self._create_default_groups()
    
    def _create_default_groups(self):
        """Create default device groups"""
        default_groups = [
            DeviceGroup(
                group_id="sensors",
                name="Sensor Devices",
                description="All sensor devices in the system",
                policies={
                    "auto_discovery": True,
                    "monitoring_interval": 5,
                    "alert_threshold": "medium"
                },
                member_count=0,
                created_at=datetime.now(),
                tags=["sensor", "monitoring"]
            ),
            DeviceGroup(
                group_id="controllers",
                name="Controller Devices",
                description="Microcontrollers and control systems",
                policies={
                    "firmware_updates": "auto",
                    "backup_config": True,
                    "security_level": "high"
                },
                member_count=0,
                created_at=datetime.now(),
                tags=["controller", "automation"]
            ),
            DeviceGroup(
                group_id="industrial",
                name="Industrial Equipment",
                description="Industrial and SCADA devices",
                policies={
                    "safety_checks": True,
                    "redundancy": "required",
                    "maintenance_window": "weekend"
                },
                member_count=0,
                created_at=datetime.now(),
                tags=["industrial", "scada", "safety"]
            ),
            DeviceGroup(
                group_id="development",
                name="Development Devices",
                description="Devices used for development and testing",
                policies={
                    "debug_mode": True,
                    "logging_level": "verbose",
                    "update_channel": "beta"
                },
                member_count=0,
                created_at=datetime.now(),
                tags=["development", "testing"]
            )
        ]
        
        for group in default_groups:
            self.groups[group.group_id] = group
    
    def create_group(self, group: DeviceGroup) -> bool:
        """Create new device group"""
        if group.group_id in self.groups:
            return False
        
        self.groups[group.group_id] = group
        return True
    
    def get_group(self, group_id: str) -> Optional[DeviceGroup]:
        """Get device group"""
        return self.groups.get(group_id)
    
    def list_groups(self) -> List[DeviceGroup]:
        """List all device groups"""
        return list(self.groups.values())
    
    def assign_device_to_groups(self, device_id: str, group_ids: List[str]):
        """Assign device to groups"""
        # Remove from existing groups
        if device_id in self.group_memberships:
            for old_group_id in self.group_memberships[device_id]:
                if old_group_id in self.groups:
                    self.groups[old_group_id].member_count -= 1
        
        # Assign to new groups
        self.group_memberships[device_id] = group_ids
        for group_id in group_ids:
            if group_id in self.groups:
                self.groups[group_id].member_count += 1
    
    def get_device_groups(self, device_id: str) -> List[str]:
        """Get groups for device"""
        return self.group_memberships.get(device_id, [])
    
    def get_group_policies(self, device_id: str) -> Dict[str, Any]:
        """Get combined policies for device from all its groups"""
        group_ids = self.get_device_groups(device_id)
        combined_policies = {}
        
        for group_id in group_ids:
            group = self.get_group(group_id)
            if group:
                combined_policies.update(group.policies)
        
        return combined_policies

class BulkProvisioning:
    def __init__(self):
        self.jobs = {}
        self.csv_importer = CSVImporter()
        self.qr_generator = QRCodeGenerator()
        self.nfc_handler = NFCHandler()
        self.template_manager = TemplateManager()
        self.group_manager = GroupManager()
        
        self.callbacks = {
            "job_started": [],
            "job_progress": [],
            "job_completed": [],
            "device_provisioned": []
        }
    
    def register_callback(self, event_type: str, callback: Callable):
        """Register event callback"""
        if event_type in self.callbacks:
            self.callbacks[event_type].append(callback)
    
    def create_csv_job(self, name: str, csv_content: str, created_by: str = "user") -> Dict[str, Any]:
        """Create bulk provisioning job from CSV"""
        # Validate CSV
        validation_result = self.csv_importer.validate_csv(csv_content)
        if not validation_result["valid"]:
            return {
                "success": False,
                "error": validation_result["error"],
                "validation": validation_result
            }
        
        # Parse devices
        devices = self.csv_importer.parse_csv(csv_content)
        
        # Create job
        job_id = f"csv_job_{uuid.uuid4().hex[:12]}"
        job = ProvisioningJob(
            job_id=job_id,
            name=name,
            method=ProvisioningMethod.CSV_IMPORT,
            devices=devices,
            created_by=created_by,
            results={"validation": validation_result}
        )
        
        self.jobs[job_id] = job
        
        return {
            "success": True,
            "job_id": job_id,
            "device_count": len(devices),
            "preview": validation_result.get("preview", [])
        }
    
    def create_qr_batch_job(self, name: str, devices: List[Dict[str, Any]], created_by: str = "user") -> Dict[str, Any]:
        """Create QR code batch provisioning job"""
        # Convert to BulkDevice objects
        bulk_devices = []
        for device in devices:
            bulk_device = BulkDevice(
                device_id=device.get("device_id", f"qr_device_{uuid.uuid4().hex[:8]}"),
                name=device["name"],
                custom_properties=device
            )
            bulk_devices.append(bulk_device)
        
        # Generate QR codes
        qr_codes = self.qr_generator.generate_batch_qr_codes(devices)
        
        # Create job
        job_id = f"qr_job_{uuid.uuid4().hex[:12]}"
        job = ProvisioningJob(
            job_id=job_id,
            name=name,
            method=ProvisioningMethod.QR_CODE_SCAN,
            devices=bulk_devices,
            created_by=created_by,
            results={"qr_codes": qr_codes}
        )
        
        self.jobs[job_id] = job
        
        return {
            "success": True,
            "job_id": job_id,
            "device_count": len(bulk_devices),
            "qr_codes": qr_codes
        }
    
    def create_template_job(self, name: str, template_id: str, device_list: List[Dict[str, Any]], created_by: str = "user") -> Dict[str, Any]:
        """Create provisioning job from template"""
        template = self.template_manager.get_template(template_id)
        if not template:
            return {
                "success": False,
                "error": f"Template {template_id} not found"
            }
        
        # Create devices with template configuration
        bulk_devices = []
        for device_info in device_list:
            # Merge template config with device overrides
            merged_config = template.default_config.copy()
            merged_config.update(device_info.get("config_overrides", {}))
            
            bulk_device = BulkDevice(
                device_id=device_info.get("device_id", f"template_device_{uuid.uuid4().hex[:8]}"),
                name=device_info["name"],
                template_id=template_id,
                override_config=merged_config,
                group_assignments=device_info.get("groups", []),
                custom_properties=device_info.get("properties", {}),
                expected_location=device_info.get("location")
            )
            bulk_devices.append(bulk_device)
        
        # Create job
        job_id = f"template_job_{uuid.uuid4().hex[:12]}"
        job = ProvisioningJob(
            job_id=job_id,
            name=name,
            method=ProvisioningMethod.TEMPLATE_CLONE,
            devices=bulk_devices,
            template=template,
            created_by=created_by
        )
        
        self.jobs[job_id] = job
        
        # Update template usage
        self.template_manager.update_usage(template_id, len(bulk_devices))
        
        return {
            "success": True,
            "job_id": job_id,
            "device_count": len(bulk_devices),
            "template": asdict(template)
        }
    
    def create_nfc_job(self, name: str, nfc_data_list: List[str], created_by: str = "user") -> Dict[str, Any]:
        """Create provisioning job from NFC tap data"""
        bulk_devices = []
        parsing_errors = []
        
        for i, nfc_data in enumerate(nfc_data_list):
            try:
                device_info = self.nfc_handler.parse_nfc_data(nfc_data)
                
                bulk_device = BulkDevice(
                    device_id=device_info["device_id"],
                    name=device_info["name"],
                    custom_properties=device_info,
                    provisioning_data=nfc_data
                )
                bulk_devices.append(bulk_device)
                
            except Exception as e:
                parsing_errors.append(f"NFC data {i+1}: {str(e)}")
        
        if not bulk_devices:
            return {
                "success": False,
                "error": "No valid NFC data found",
                "parsing_errors": parsing_errors
            }
        
        # Create job
        job_id = f"nfc_job_{uuid.uuid4().hex[:12]}"
        job = ProvisioningJob(
            job_id=job_id,
            name=name,
            method=ProvisioningMethod.NFC_TAP,
            devices=bulk_devices,
            created_by=created_by,
            results={"parsing_errors": parsing_errors}
        )
        
        self.jobs[job_id] = job
        
        return {
            "success": True,
            "job_id": job_id,
            "device_count": len(bulk_devices),
            "parsing_errors": parsing_errors
        }
    
    async def execute_job(self, job_id: str) -> Dict[str, Any]:
        """Execute provisioning job"""
        job = self.jobs.get(job_id)
        if not job:
            return {"success": False, "error": "Job not found"}
        
        if job.status != ProvisioningStatus.PENDING:
            return {"success": False, "error": "Job already started or completed"}
        
        # Start job
        job.status = ProvisioningStatus.IN_PROGRESS
        job.started_at = datetime.now()
        
        # Trigger job started callback
        for callback in self.callbacks["job_started"]:
            try:
                callback(job_id, job)
            except Exception as e:
                print(f"Job started callback error: {e}")
        
        try:
            # Process devices
            provisioned_devices = []
            failed_devices = []
            
            total_devices = len(job.devices)
            
            for i, device in enumerate(job.devices):
                try:
                    # Simulate device provisioning
                    await self._provision_device(device, job)
                    provisioned_devices.append(device.device_id)
                    
                    # Trigger device provisioned callback
                    for callback in self.callbacks["device_provisioned"]:
                        try:
                            callback(job_id, device)
                        except Exception as e:
                            print(f"Device provisioned callback error: {e}")
                    
                except Exception as e:
                    failed_devices.append({
                        "device_id": device.device_id,
                        "error": str(e)
                    })
                    job.errors.append(f"Device {device.device_id}: {str(e)}")
                
                # Update progress
                job.progress = ((i + 1) / total_devices) * 100
                
                # Trigger progress callback
                for callback in self.callbacks["job_progress"]:
                    try:
                        callback(job_id, job.progress)
                    except Exception as e:
                        print(f"Job progress callback error: {e}")
                
                # Small delay to simulate processing
                await asyncio.sleep(0.1)
            
            # Complete job
            job.status = ProvisioningStatus.COMPLETED
            job.completed_at = datetime.now()
            job.results.update({
                "provisioned_devices": provisioned_devices,
                "failed_devices": failed_devices,
                "success_rate": len(provisioned_devices) / total_devices * 100
            })
            
            # Trigger job completed callback
            for callback in self.callbacks["job_completed"]:
                try:
                    callback(job_id, job)
                except Exception as e:
                    print(f"Job completed callback error: {e}")
            
            return {
                "success": True,
                "provisioned_count": len(provisioned_devices),
                "failed_count": len(failed_devices),
                "success_rate": job.results["success_rate"]
            }
            
        except Exception as e:
            job.status = ProvisioningStatus.FAILED
            job.errors.append(f"Job execution failed: {str(e)}")
            
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _provision_device(self, device: BulkDevice, job: ProvisioningJob):
        """Provision individual device"""
        # Simulate device provisioning steps
        steps = [
            "Validating configuration",
            "Downloading driver",
            "Establishing connection", 
            "Uploading configuration",
            "Testing functionality",
            "Assigning to groups",
            "Setting permissions",
            "Registering in system"
        ]
        
        for step in steps:
            # Simulate processing time
            await asyncio.sleep(random.uniform(0.1, 0.3))
            
            # Simulate occasional failures
            if random.random() < 0.05:  # 5% failure rate
                raise Exception(f"Failed at step: {step}")
        
        # Apply template configuration if specified
        if device.template_id and job.template:
            final_config = job.template.default_config.copy()
            if device.override_config:
                final_config.update(device.override_config)
        else:
            final_config = device.override_config or {}
        
        # Assign to groups
        if device.group_assignments:
            self.group_manager.assign_device_to_groups(device.device_id, device.group_assignments)
        
        # Simulate device registration
        device.custom_properties["provisioned_at"] = datetime.now().isoformat()
        device.custom_properties["final_config"] = final_config
        device.custom_properties["status"] = "provisioned"
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get provisioning job status"""
        job = self.jobs.get(job_id)
        if not job:
            return None
        
        return {
            "job_id": job.job_id,
            "name": job.name,
            "method": job.method.value,
            "status": job.status.value,
            "progress": job.progress,
            "device_count": len(job.devices),
            "created_at": job.created_at.isoformat(),
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "results": job.results,
            "errors": job.errors
        }
    
    def list_jobs(self, user_id: str = None) -> List[Dict[str, Any]]:
        """List provisioning jobs"""
        jobs = list(self.jobs.values())
        
        if user_id:
            jobs = [job for job in jobs if job.created_by == user_id]
        
        # Sort by creation time (newest first)
        jobs.sort(key=lambda j: j.created_at, reverse=True)
        
        return [self.get_job_status(job.job_id) for job in jobs]
    
    def get_template_manager(self) -> TemplateManager:
        """Get template manager"""
        return self.template_manager
    
    def get_group_manager(self) -> GroupManager:
        """Get group manager"""
        return self.group_manager
    
    def get_provisioning_statistics(self) -> Dict[str, Any]:
        """Get provisioning statistics"""
        total_jobs = len(self.jobs)
        completed_jobs = sum(1 for job in self.jobs.values() if job.status == ProvisioningStatus.COMPLETED)
        failed_jobs = sum(1 for job in self.jobs.values() if job.status == ProvisioningStatus.FAILED)
        in_progress_jobs = sum(1 for job in self.jobs.values() if job.status == ProvisioningStatus.IN_PROGRESS)
        
        total_devices = sum(len(job.devices) for job in self.jobs.values())
        
        # Method statistics
        method_stats = {}
        for method in ProvisioningMethod:
            method_stats[method.value] = sum(1 for job in self.jobs.values() if job.method == method)
        
        return {
            "total_jobs": total_jobs,
            "completed_jobs": completed_jobs,
            "failed_jobs": failed_jobs,
            "in_progress_jobs": in_progress_jobs,
            "success_rate": (completed_jobs / max(1, total_jobs)) * 100,
            "total_devices_processed": total_devices,
            "method_statistics": method_stats,
            "template_count": len(self.template_manager.templates),
            "group_count": len(self.group_manager.groups)
        }

if __name__ == "__main__":
    print("Bulk Provisioning System")
    print("=" * 50)
    
    async def demo():
        # Create bulk provisioning system
        bulk_system = BulkProvisioning()
        
        # Register callbacks
        def on_job_started(job_id, job):
            print(f"🚀 Job started: {job.name} ({job_id})")
        
        def on_job_progress(job_id, progress):
            print(f"📊 Job progress: {progress:.1f}%")
        
        def on_job_completed(job_id, job):
            print(f"✅ Job completed: {job.name}")
            print(f"   Success rate: {job.results.get('success_rate', 0):.1f}%")
        
        def on_device_provisioned(job_id, device):
            print(f"   📱 Device provisioned: {device.name}")
        
        bulk_system.register_callback("job_started", on_job_started)
        bulk_system.register_callback("job_progress", on_job_progress)
        bulk_system.register_callback("job_completed", on_job_completed)
        bulk_system.register_callback("device_provisioned", on_device_provisioned)
        
        # Demonstrate CSV import
        print("--- CSV Import Demo ---")
        csv_data = """name,category,interface,manufacturer,model,group,config_json
Sensor-001,sensor,serial,Arduino,Uno R3,sensors,"{""baud_rate"": 115200}"
Sensor-002,sensor,serial,Arduino,Uno R3,sensors,"{""baud_rate"": 115200}"
Controller-001,controller,ethernet,Raspberry Pi,4B,controllers,"{""port"": 22}"
Display-001,display,i2c,Adafruit,SSD1306,sensors,"{""address"": ""0x3C""}"
Motor-001,actuator,usb,Pololu,Servo,controllers,"{""max_speed"": 100}"
"""
        
        csv_result = bulk_system.create_csv_job("Sensor Network Deployment", csv_data)
        if csv_result["success"]:
            print(f"Created CSV job with {csv_result['device_count']} devices")
            
            # Execute the job
            job_id = csv_result["job_id"]
            execution_result = await bulk_system.execute_job(job_id)
            print(f"CSV job execution: {'✅ Success' if execution_result['success'] else '❌ Failed'}")
        
        # Demonstrate QR code generation
        print(f"\n--- QR Code Batch Demo ---")
        qr_devices = [
            {"device_id": "qr_sensor_001", "name": "QR Sensor 1", "category": "sensor", "interface": "i2c"},
            {"device_id": "qr_sensor_002", "name": "QR Sensor 2", "category": "sensor", "interface": "i2c"},
            {"device_id": "qr_display_001", "name": "QR Display 1", "category": "display", "interface": "spi"}
        ]
        
        qr_result = bulk_system.create_qr_batch_job("QR Code Deployment", qr_devices)
        if qr_result["success"]:
            print(f"Generated {len(qr_result['qr_codes'])} QR codes")
            for qr in qr_result["qr_codes"][:2]:  # Show first 2
                print(f"  {qr['name']}: {qr['provisioning_url']}")
        
        # Demonstrate template-based provisioning
        print(f"\n--- Template-Based Demo ---")
        template_devices = [
            {"name": "Lab Sensor A", "groups": ["sensors", "development"], "location": "Lab Room 101"},
            {"name": "Lab Sensor B", "groups": ["sensors", "development"], "location": "Lab Room 102"},
            {"name": "Lab Sensor C", "groups": ["sensors", "development"], "location": "Lab Room 103"}
        ]
        
        template_result = bulk_system.create_template_job(
            "Lab Sensor Deployment", 
            "arduino_sensor", 
            template_devices
        )
        
        if template_result["success"]:
            print(f"Created template job with {template_result['device_count']} devices")
            
            # Execute the job
            job_id = template_result["job_id"]
            execution_result = await bulk_system.execute_job(job_id)
            print(f"Template job execution: {'✅ Success' if execution_result['success'] else '❌ Failed'}")
        
        # Show templates
        print(f"\n--- Available Templates ---")
        templates = bulk_system.get_template_manager().list_templates()
        for template in templates:
            print(f"  {template.name} ({template.template_id})")
            print(f"    Category: {template.category}, Interface: {template.interface}")
        
        # Show groups
        print(f"\n--- Device Groups ---")
        groups = bulk_system.get_group_manager().list_groups()
        for group in groups:
            print(f"  {group.name} ({group.group_id}): {group.member_count} members")
        
        # Show statistics
        print(f"\n--- Provisioning Statistics ---")
        stats = bulk_system.get_provisioning_statistics()
        print(f"Total jobs: {stats['total_jobs']}")
        print(f"Success rate: {stats['success_rate']:.1f}%")
        print(f"Total devices processed: {stats['total_devices_processed']}")
        print(f"Available templates: {stats['template_count']}")
        print(f"Device groups: {stats['group_count']}")
        
        print("\nBulk provisioning demo completed")
    
    asyncio.run(demo())