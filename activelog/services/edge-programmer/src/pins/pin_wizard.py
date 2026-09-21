"""
Pin Configuration Wizard
"""

import uuid
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from ..database import PinConfiguration, Device, DeviceType, PinType, SensorType


class PinConfigurationWizard:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.device_pin_maps = {
            DeviceType.ARDUINO_UNO: {
                "digital_pins": list(range(0, 14)),
                "analog_pins": list(range(14, 20)),  # A0-A5 mapped to 14-19
                "pwm_pins": [3, 5, 6, 9, 10, 11],
                "i2c": {"sda": 18, "scl": 19},  # A4, A5
                "spi": {"mosi": 11, "miso": 12, "sck": 13, "ss": 10},
                "uart": {"tx": 1, "rx": 0}
            },
            DeviceType.ESP32: {
                "digital_pins": list(range(0, 40)),
                "analog_pins": [32, 33, 34, 35, 36, 37, 38, 39],
                "pwm_pins": list(range(0, 16)),
                "i2c": {"sda": 21, "scl": 22},
                "spi": {"mosi": 23, "miso": 19, "sck": 18, "ss": 5},
                "uart": {"tx": 1, "rx": 3}
            },
            DeviceType.ESP8266: {
                "digital_pins": [0, 1, 2, 3, 4, 5, 12, 13, 14, 15, 16],
                "analog_pins": [17],  # A0
                "pwm_pins": [0, 1, 2, 3, 4, 5, 12, 13, 14, 15, 16],
                "i2c": {"sda": 4, "scl": 5},
                "spi": {"mosi": 13, "miso": 12, "sck": 14, "ss": 15},
                "uart": {"tx": 1, "rx": 3}
            }
        }
        
        self.sensor_pin_requirements = {
            SensorType.TEMPERATURE: {"type": PinType.DIGITAL, "count": 1},
            SensorType.HUMIDITY: {"type": PinType.DIGITAL, "count": 1},
            SensorType.PRESSURE: {"type": PinType.I2C_SDA, "count": 2},
            SensorType.LIGHT: {"type": PinType.ANALOG, "count": 1},
            SensorType.MOTION: {"type": PinType.DIGITAL, "count": 1},
            SensorType.DISTANCE: {"type": PinType.DIGITAL, "count": 2},
            SensorType.ACCELEROMETER: {"type": PinType.I2C_SDA, "count": 2},
            SensorType.GPS: {"type": PinType.UART_RX, "count": 2},
        }
    
    async def create_pin_configuration_wizard(
        self,
        device_id: uuid.UUID,
        sensors: List[SensorType],
        actuators: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Create a guided pin configuration for the device"""
        
        device = await self._get_device(device_id)
        if not device:
            raise ValueError(f"Device {device_id} not found")
        
        pin_map = self.device_pin_maps.get(device.device_type)
        if not pin_map:
            raise ValueError(f"Pin mapping not available for {device.device_type}")
        
        # Generate suggested configuration
        suggestions = await self._generate_pin_suggestions(
            device.device_type, sensors, actuators or []
        )
        
        # Check for conflicts
        conflicts = self._check_pin_conflicts(suggestions)
        
        # Generate alternative configurations if conflicts exist
        alternatives = []
        if conflicts:
            alternatives = await self._generate_alternative_configurations(
                device.device_type, sensors, actuators or [], conflicts
            )
        
        return {
            "device_id": str(device_id),
            "device_type": device.device_type.value,
            "suggested_configuration": suggestions,
            "conflicts": conflicts,
            "alternatives": alternatives,
            "pin_map": pin_map
        }
    
    async def _get_device(self, device_id: uuid.UUID) -> Optional[Device]:
        """Get device from database"""
        result = await self.session.execute(
            select(Device).where(Device.id == device_id)
        )
        return result.scalar_one_or_none()
    
    async def _generate_pin_suggestions(
        self,
        device_type: DeviceType,
        sensors: List[SensorType],
        actuators: List[str]
    ) -> Dict[str, Any]:
        """Generate pin configuration suggestions"""
        
        pin_map = self.device_pin_maps[device_type]
        suggestions = {
            "sensors": {},
            "actuators": {},
            "communication": {},
            "power": {},
            "reserved": []
        }
        
        used_pins = set()
        
        # Reserve system pins first
        if device_type == DeviceType.ARDUINO_UNO:
            used_pins.update([0, 1])  # Serial
            suggestions["reserved"] = [0, 1]
        elif device_type == DeviceType.ESP32:
            used_pins.update([1, 3])  # Serial
            suggestions["reserved"] = [1, 3]
        elif device_type == DeviceType.ESP8266:
            used_pins.update([1, 3])  # Serial
            suggestions["reserved"] = [1, 3]
        
        # Configure sensors
        for sensor in sensors:
            sensor_config = await self._suggest_sensor_pins(
                sensor, device_type, pin_map, used_pins
            )
            if sensor_config:
                suggestions["sensors"][sensor.value] = sensor_config
                used_pins.update(sensor_config.get("pins", []))
        
        # Configure actuators
        actuator_pin = 2 if 2 not in used_pins else None
        for i, actuator in enumerate(actuators):
            while actuator_pin in used_pins and actuator_pin < max(pin_map["digital_pins"]):
                actuator_pin += 1
            
            if actuator_pin in pin_map["digital_pins"]:
                if actuator in ["led", "relay", "buzzer"]:
                    pin_type = PinType.PWM if actuator_pin in pin_map.get("pwm_pins", []) else PinType.DIGITAL
                    suggestions["actuators"][actuator] = {
                        "pins": [actuator_pin],
                        "type": pin_type.value,
                        "description": f"{actuator.title()} control pin"
                    }
                    used_pins.add(actuator_pin)
                    actuator_pin += 1
        
        # Add communication pins
        if pin_map.get("i2c"):
            suggestions["communication"]["i2c"] = {
                "sda": pin_map["i2c"]["sda"],
                "scl": pin_map["i2c"]["scl"],
                "description": "I2C communication bus"
            }
        
        if pin_map.get("spi"):
            suggestions["communication"]["spi"] = {
                "mosi": pin_map["spi"]["mosi"],
                "miso": pin_map["spi"]["miso"],
                "sck": pin_map["spi"]["sck"],
                "ss": pin_map["spi"]["ss"],
                "description": "SPI communication bus"
            }
        
        # Add power pins
        suggestions["power"] = {
            "vcc": "3.3V" if device_type in [DeviceType.ESP32, DeviceType.ESP8266] else "5V",
            "gnd": "Ground pins available"
        }
        
        return suggestions
    
    async def _suggest_sensor_pins(
        self,
        sensor: SensorType,
        device_type: DeviceType,
        pin_map: Dict[str, Any],
        used_pins: set
    ) -> Optional[Dict[str, Any]]:
        """Suggest pins for a specific sensor"""
        
        sensor_req = self.sensor_pin_requirements.get(sensor)
        if not sensor_req:
            return None
        
        config = {
            "sensor": sensor.value,
            "pins": [],
            "type": sensor_req["type"].value,
            "description": f"Pin configuration for {sensor.value} sensor"
        }
        
        if sensor in [SensorType.TEMPERATURE, SensorType.HUMIDITY]:
            # DHT sensors use digital pins
            for pin in pin_map["digital_pins"]:
                if pin not in used_pins:
                    config["pins"] = [pin]
                    config["library"] = "DHT.h"
                    break
        
        elif sensor == SensorType.LIGHT:
            # Light sensors use analog pins
            for pin in pin_map["analog_pins"]:
                if pin not in used_pins:
                    config["pins"] = [pin]
                    config["type"] = PinType.ANALOG.value
                    break
        
        elif sensor == SensorType.MOTION:
            # PIR sensors use digital pins
            for pin in pin_map["digital_pins"]:
                if pin not in used_pins:
                    config["pins"] = [pin]
                    config["description"] = "PIR motion sensor pin"
                    break
        
        elif sensor == SensorType.DISTANCE:
            # Ultrasonic sensors need trigger and echo pins
            available_pins = [p for p in pin_map["digital_pins"] if p not in used_pins]
            if len(available_pins) >= 2:
                config["pins"] = available_pins[:2]
                config["pin_names"] = ["trigger", "echo"]
                config["library"] = "NewPing.h"
        
        elif sensor in [SensorType.PRESSURE, SensorType.ACCELEROMETER]:
            # I2C sensors
            if pin_map.get("i2c"):
                config["pins"] = [pin_map["i2c"]["sda"], pin_map["i2c"]["scl"]]
                config["type"] = PinType.I2C_SDA.value
                config["pin_names"] = ["sda", "scl"]
                config["library"] = "Wire.h"
        
        elif sensor == SensorType.GPS:
            # GPS modules need TX/RX pins
            available_pins = [p for p in pin_map["digital_pins"] if p not in used_pins]
            if len(available_pins) >= 2:
                config["pins"] = available_pins[:2]
                config["pin_names"] = ["rx", "tx"]
                config["library"] = "SoftwareSerial.h"
        
        return config if config["pins"] else None
    
    def _check_pin_conflicts(self, suggestions: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for pin conflicts in the suggested configuration"""
        
        conflicts = []
        all_used_pins = {}
        
        # Collect all pin assignments
        for category, items in suggestions.items():
            if category == "reserved":
                for pin in items:
                    all_used_pins[pin] = "reserved"
            elif isinstance(items, dict):
                for item_name, item_config in items.items():
                    if isinstance(item_config, dict) and "pins" in item_config:
                        for pin in item_config["pins"]:
                            if pin in all_used_pins:
                                conflicts.append({
                                    "pin": pin,
                                    "conflict": f"Pin {pin} assigned to both {all_used_pins[pin]} and {category}.{item_name}",
                                    "severity": "error"
                                })
                            else:
                                all_used_pins[pin] = f"{category}.{item_name}"
        
        return conflicts
    
    async def _generate_alternative_configurations(
        self,
        device_type: DeviceType,
        sensors: List[SensorType],
        actuators: List[str],
        conflicts: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate alternative configurations to resolve conflicts"""
        
        alternatives = []
        pin_map = self.device_pin_maps[device_type]
        
        # Alternative 1: Different pin assignment strategy
        alt1 = await self._generate_pin_suggestions_alt_strategy(
            device_type, sensors, actuators, "sequential"
        )
        alternatives.append({
            "name": "Sequential Pin Assignment",
            "description": "Assigns pins sequentially to avoid conflicts",
            "configuration": alt1
        })
        
        # Alternative 2: Optimized for fewer pins
        alt2 = await self._generate_pin_suggestions_alt_strategy(
            device_type, sensors, actuators, "minimal"
        )
        alternatives.append({
            "name": "Minimal Pin Usage",
            "description": "Uses fewer pins by sharing communication buses",
            "configuration": alt2
        })
        
        return alternatives
    
    async def _generate_pin_suggestions_alt_strategy(
        self,
        device_type: DeviceType,
        sensors: List[SensorType],
        actuators: List[str],
        strategy: str
    ) -> Dict[str, Any]:
        """Generate alternative pin suggestions with different strategy"""
        
        # Simplified alternative generation - in practice, this would be more sophisticated
        suggestions = await self._generate_pin_suggestions(device_type, sensors, actuators)
        
        if strategy == "minimal":
            # Try to use I2C for multiple sensors
            i2c_sensors = [s for s in sensors if s in [SensorType.PRESSURE, SensorType.ACCELEROMETER]]
            if i2c_sensors:
                for sensor in i2c_sensors:
                    if sensor.value in suggestions["sensors"]:
                        suggestions["sensors"][sensor.value]["shared_bus"] = "i2c"
        
        return suggestions
    
    async def apply_pin_configuration(
        self,
        device_id: uuid.UUID,
        configuration: Dict[str, Any]
    ) -> bool:
        """Apply pin configuration to device"""
        
        # Clear existing pin configurations
        await self.session.execute(
            select(PinConfiguration).where(PinConfiguration.device_id == device_id)
        )
        existing_configs = await self.session.execute(
            select(PinConfiguration).where(PinConfiguration.device_id == device_id)
        )
        for config in existing_configs.scalars().all():
            await self.session.delete(config)
        
        # Apply new configurations
        for category, items in configuration.items():
            if category in ["sensors", "actuators"] and isinstance(items, dict):
                for item_name, item_config in items.items():
                    if isinstance(item_config, dict) and "pins" in item_config:
                        for i, pin in enumerate(item_config["pins"]):
                            pin_config = PinConfiguration(
                                pin_number=pin,
                                pin_type=PinType(item_config["type"]),
                                function=f"{category}_{item_name}",
                                sensor_type=SensorType(item_name) if category == "sensors" else None,
                                configuration={
                                    "category": category,
                                    "item_name": item_name,
                                    "pin_index": i,
                                    "description": item_config.get("description", ""),
                                    "library": item_config.get("library", "")
                                },
                                device_id=device_id
                            )
                            self.session.add(pin_config)
        
        await self.session.commit()
        return True
    
    async def get_device_pin_configuration(
        self,
        device_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Get current pin configuration for device"""
        
        result = await self.session.execute(
            select(PinConfiguration).where(PinConfiguration.device_id == device_id)
        )
        configs = result.scalars().all()
        
        configuration = {
            "device_id": str(device_id),
            "pins": {},
            "sensors": {},
            "actuators": {},
            "communication": {}
        }
        
        for config in configs:
            pin_info = {
                "pin_number": config.pin_number,
                "pin_type": config.pin_type.value,
                "function": config.function,
                "sensor_type": config.sensor_type.value if config.sensor_type else None,
                "is_active": config.is_active,
                "configuration": config.configuration
            }
            
            configuration["pins"][config.pin_number] = pin_info
            
            # Categorize pins
            if config.configuration and config.configuration.get("category") == "sensors":
                sensor_name = config.configuration.get("item_name")
                if sensor_name not in configuration["sensors"]:
                    configuration["sensors"][sensor_name] = []
                configuration["sensors"][sensor_name].append(pin_info)
            elif config.configuration and config.configuration.get("category") == "actuators":
                actuator_name = config.configuration.get("item_name")
                if actuator_name not in configuration["actuators"]:
                    configuration["actuators"][actuator_name] = []
                configuration["actuators"][actuator_name].append(pin_info)
        
        return configuration
    
    async def validate_pin_configuration(
        self,
        device_type: DeviceType,
        configuration: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate a pin configuration"""
        
        pin_map = self.device_pin_maps.get(device_type)
        if not pin_map:
            return {"valid": False, "errors": ["Unsupported device type"]}
        
        errors = []
        warnings = []
        used_pins = set()
        
        # Check each pin assignment
        for category, items in configuration.items():
            if isinstance(items, dict):
                for item_name, item_config in items.items():
                    if isinstance(item_config, dict) and "pins" in item_config:
                        for pin in item_config["pins"]:
                            # Check if pin exists on device
                            if pin not in pin_map["digital_pins"] + pin_map["analog_pins"]:
                                errors.append(f"Pin {pin} does not exist on {device_type.value}")
                            
                            # Check for conflicts
                            if pin in used_pins:
                                errors.append(f"Pin {pin} is assigned multiple times")
                            else:
                                used_pins.add(pin)
                            
                            # Check pin type compatibility
                            pin_type = item_config.get("type")
                            if pin_type == "analog" and pin not in pin_map["analog_pins"]:
                                errors.append(f"Pin {pin} cannot be used as analog input")
                            elif pin_type == "pwm" and pin not in pin_map.get("pwm_pins", []):
                                warnings.append(f"Pin {pin} does not support PWM output")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "used_pins": list(used_pins),
            "available_pins": [p for p in pin_map["digital_pins"] if p not in used_pins]
        }