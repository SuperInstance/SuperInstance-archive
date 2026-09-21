"""
Device Registry and Type Management System
Manages all device types and their handlers
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Type, Callable
from abc import ABC, abstractmethod

from core.udp_core import DeviceManifest, DeviceCapability
from .base_handler import BaseDeviceHandler

logger = logging.getLogger(__name__)


class DeviceRegistry:
    """Central registry for all device types and their handlers"""
    
    def __init__(self, config):
        self.config = config
        self.devices: Dict[str, DeviceManifest] = {}
        self.device_handlers: Dict[str, BaseDeviceHandler] = {}
        self.type_handlers: Dict[str, Type[BaseDeviceHandler]] = {}
        self.capability_callback: Optional[Callable] = None
        
        # Initialize device type handlers
        self.register_device_handlers()
    
    def register_device_handlers(self):
        """Register all device type handlers"""
        
        # Import handlers at runtime to avoid circular imports
        from .input_devices import (
            CameraHandler, WebcamHandler, ThermalCameraHandler, DepthCameraHandler,
            Camera360Handler, DSLRCameraHandler, GenericSensorHandler, TemperatureSensorHandler,
            PressureSensorHandler, MotionSensorHandler, BiometricSensorHandler, MicrophoneHandler,
            USBMicrophoneHandler, XLRMicrophoneHandler, MicrophoneArrayHandler, UltrasonicMicrophoneHandler,
            ControllerHandler, GamepadHandler, MIDIControllerHandler, CustomControllerHandler,
            ScannerHandler, DocumentScannerHandler, Scanner3DHandler, BarcodeScannerHandler,
            RFIDScannerHandler, GPSHandler, GNSSHandler, SDRHandler, BCIHandler, QuantumSensorHandler
        )
        from .output_devices import (
            DisplayHandler, MonitorHandler, ARDisplayHandler, VRDisplayHandler, HolographicDisplayHandler,
            PrinterHandler, Printer2DHandler, Printer3DHandler, ResinPrinterHandler, MetalPrinterHandler,
            BioPrinterHandler, ActuatorHandler, MotorHandler, ServoHandler, SolenoidHandler,
            SpeakerHandler, StereoSpeakerHandler, SurroundSpeakerHandler, UltrasonicSpeakerHandler,
            LightHandler, RGBLightHandler, UVLightHandler, IRLightHandler, LaserHandler,
            HapticDeviceHandler, CNCMachineHandler, RoboticArmHandler, QuantumEmitterHandler
        )
        from .storage_devices import (
            GenericStorageHandler, HDDHandler, SSDHandler, OpticalStorageHandler,
            CDHandler, DVDHandler, BlurayHandler, HolographicStorageHandler, DNAStorageHandler,
            TapeStorageHandler, DistributedStorageHandler
        )
        from .compute_devices import (
            CPUHandler, x86CPUHandler, ARMCPUHandler, RISCVCPUHandler, GPUHandler, 
            NVIDIAGPUHandler, AMDGPUHandler, IntelGPUHandler, FPGAHandler, XilinxFPGAHandler,
            IntelFPGAHandler, LatticeFPGAHandler, ASICHandler, CryptoASICHandler, AIASICHandler,
            CustomASICHandler, NeuromorphicChipHandler, QuantumProcessorHandler, 
            OpticalProcessorHandler, BiologicalComputerHandler
        )
        
        # Input Device Handlers
        self.type_handlers.update({
            'camera': CameraHandler,
            'webcam': WebcamHandler,
            'thermal_camera': ThermalCameraHandler,
            'depth_camera': DepthCameraHandler,
            '360_camera': Camera360Handler,
            'dslr_camera': DSLRCameraHandler,
            
            'sensor': GenericSensorHandler,
            'temperature_sensor': TemperatureSensorHandler,
            'pressure_sensor': PressureSensorHandler,
            'motion_sensor': MotionSensorHandler,
            'biometric_sensor': BiometricSensorHandler,
            
            'microphone': MicrophoneHandler,
            'usb_microphone': USBMicrophoneHandler,
            'xlr_microphone': XLRMicrophoneHandler,
            'microphone_array': MicrophoneArrayHandler,
            'ultrasonic_microphone': UltrasonicMicrophoneHandler,
            
            'controller': ControllerHandler,
            'gamepad': GamepadHandler,
            'midi_controller': MIDIControllerHandler,
            'custom_controller': CustomControllerHandler,
            
            'scanner': ScannerHandler,
            'document_scanner': DocumentScannerHandler,
            '3d_scanner': Scanner3DHandler,
            'barcode_scanner': BarcodeScannerHandler,
            'rfid_scanner': RFIDScannerHandler,
            
            'gps': GPSHandler,
            'gnss': GNSSHandler,
            'sdr': SDRHandler,
            'bci': BCIHandler,
            'quantum_sensor': QuantumSensorHandler
        })
        
        # Output Device Handlers
        self.type_handlers.update({
            'display': DisplayHandler,
            'monitor': MonitorHandler,
            'ar_display': ARDisplayHandler,
            'vr_display': VRDisplayHandler,
            'holographic_display': HolographicDisplayHandler,
            
            'printer': PrinterHandler,
            '2d_printer': Printer2DHandler,
            '3d_printer': Printer3DHandler,
            'resin_printer': ResinPrinterHandler,
            'metal_printer': MetalPrinterHandler,
            'bio_printer': BioPrinterHandler,
            
            'actuator': ActuatorHandler,
            'motor': MotorHandler,
            'servo': ServoHandler,
            'solenoid': SolenoidHandler,
            
            'speaker': SpeakerHandler,
            'stereo_speaker': StereoSpeakerHandler,
            'surround_speaker': SurroundSpeakerHandler,
            'ultrasonic_speaker': UltrasonicSpeakerHandler,
            
            'light': LightHandler,
            'rgb_light': RGBLightHandler,
            'uv_light': UVLightHandler,
            'ir_light': IRLightHandler,
            'laser': LaserHandler,
            
            'haptic_device': HapticDeviceHandler,
            'cnc_machine': CNCMachineHandler,
            'robotic_arm': RoboticArmHandler,
            'quantum_emitter': QuantumEmitterHandler
        })
        
        # Storage Device Handlers
        self.type_handlers.update({
            'storage': GenericStorageHandler,
            'hdd': HDDHandler,
            'ssd': SSDHandler,
            'optical_storage': OpticalStorageHandler,
            'cd_drive': CDHandler,
            'dvd_drive': DVDHandler,
            'bluray_drive': BlurayHandler,
            'holographic_storage': HolographicStorageHandler,
            'tape_storage': TapeStorageHandler,
            'dna_storage': DNAStorageHandler,
            'distributed_storage': DistributedStorageHandler
        })
        
        # Compute Device Handlers
        self.type_handlers.update({
            'cpu': CPUHandler,
            'x86_cpu': x86CPUHandler,
            'arm_cpu': ARMCPUHandler,
            'riscv_cpu': RISCVCPUHandler,
            
            'gpu': GPUHandler,
            'nvidia_gpu': NVIDIAGPUHandler,
            'amd_gpu': AMDGPUHandler,
            'intel_gpu': IntelGPUHandler,
            
            'fpga': FPGAHandler,
            'xilinx_fpga': XilinxFPGAHandler,
            'intel_fpga': IntelFPGAHandler,
            'lattice_fpga': LatticeFPGAHandler,
            
            'asic': ASICHandler,
            'crypto_asic': CryptoASICHandler,
            'ai_asic': AIASICHandler,
            'custom_asic': CustomASICHandler,
            
            'neuromorphic_chip': NeuromorphicChipHandler,
            'quantum_processor': QuantumProcessorHandler,
            'optical_processor': OpticalProcessorHandler,
            'biological_computer': BiologicalComputerHandler
        })
    
    async def initialize(self):
        """Initialize the device registry"""
        logger.info("Initializing device registry...")
        
        # Initialize all handler classes
        for device_type, handler_class in self.type_handlers.items():
            try:
                handler = handler_class()
                # Don't store the handler yet, create on demand
                logger.debug(f"Registered handler for device type: {device_type}")
            except Exception as e:
                logger.error(f"Failed to register handler for {device_type}: {e}")
        
        logger.info(f"Device registry initialized with {len(self.type_handlers)} device type handlers")
    
    async def register_device(self, manifest: DeviceManifest) -> bool:
        """Register a new device"""
        try:
            device_id = manifest.device_id
            
            # Get appropriate handler
            handler = await self.get_device_handler(manifest.device_type)
            if not handler:
                logger.error(f"No handler found for device type: {manifest.device_type}")
                return False
            
            # Initialize device with handler
            if not await handler.initialize_device(manifest):
                logger.error(f"Failed to initialize device: {device_id}")
                return False
            
            # Store device and handler
            self.devices[device_id] = manifest
            self.device_handlers[device_id] = handler
            
            # Notify capability callback
            if self.capability_callback:
                await self.capability_callback(manifest)
            
            logger.info(f"Device registered successfully: {device_id} ({manifest.device_type})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register device {manifest.device_id}: {e}")
            return False
    
    async def unregister_device(self, device_id: str) -> bool:
        """Unregister a device"""
        try:
            if device_id in self.device_handlers:
                handler = self.device_handlers[device_id]
                await handler.disconnect_device(device_id)
                del self.device_handlers[device_id]
            
            if device_id in self.devices:
                del self.devices[device_id]
            
            logger.info(f"Device unregistered: {device_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unregister device {device_id}: {e}")
            return False
    
    async def get_device_handler(self, device_type: str) -> Optional[BaseDeviceHandler]:
        """Get handler for device type"""
        if device_type in self.type_handlers:
            try:
                handler_class = self.type_handlers[device_type]
                handler = handler_class()
                return handler
            except Exception as e:
                logger.error(f"Failed to create handler for {device_type}: {e}")
        
        # Try to find a generic handler
        generic_types = {
            'input': GenericInputHandler,
            'output': GenericOutputHandler,
            'storage': GenericStorageHandler,
            'compute': GenericComputeHandler
        }
        
        for generic_type, handler_class in generic_types.items():
            if generic_type in device_type.lower():
                try:
                    return handler_class()
                except Exception as e:
                    logger.error(f"Failed to create generic handler {generic_type}: {e}")
        
        return None
    
    async def connect_device(self, device_id: str) -> bool:
        """Connect to a device"""
        if device_id in self.device_handlers:
            handler = self.device_handlers[device_id]
            return await handler.connect_device(device_id)
        return False
    
    async def disconnect_device(self, device_id: str) -> bool:
        """Disconnect from a device"""
        if device_id in self.device_handlers:
            handler = self.device_handlers[device_id]
            return await handler.disconnect_device(device_id)
        return False
    
    async def send_command(self, device_id: str, command: Dict[str, Any]) -> Dict[str, Any]:
        """Send command to device"""
        if device_id in self.device_handlers:
            handler = self.device_handlers[device_id]
            if await handler.validate_command(device_id, command):
                return await handler.send_command(device_id, command)
            else:
                return {"error": "Invalid command"}
        return {"error": "Device handler not found"}
    
    async def get_device_status(self, device_id: str) -> Dict[str, Any]:
        """Get device status"""
        if device_id in self.device_handlers:
            handler = self.device_handlers[device_id]
            return await handler.get_device_status(device_id)
        return {"error": "Device handler not found"}
    
    async def get_device_capabilities(self, device_id: str) -> List[DeviceCapability]:
        """Get device capabilities"""
        if device_id in self.device_handlers:
            handler = self.device_handlers[device_id]
            return await handler.get_capabilities(device_id)
        return []
    
    def get_device(self, device_id: str) -> Optional[DeviceManifest]:
        """Get device manifest"""
        return self.devices.get(device_id)
    
    def get_all_devices(self) -> List[DeviceManifest]:
        """Get all registered devices"""
        return list(self.devices.values())
    
    def get_devices_by_type(self, device_type: str) -> List[DeviceManifest]:
        """Get devices by type"""
        return [device for device in self.devices.values() if device.device_type == device_type]
    
    def get_devices_by_capability(self, capability_name: str) -> List[DeviceManifest]:
        """Get devices with specific capability"""
        matching_devices = []
        for device in self.devices.values():
            for cap in device.capabilities:
                if cap.name == capability_name:
                    matching_devices.append(device)
                    break
        return matching_devices
    
    def set_capability_callback(self, callback: Callable):
        """Set callback for capability notifications"""
        self.capability_callback = callback
    
    async def handle_hot_swap(self, old_device_id: str, new_manifest: DeviceManifest) -> bool:
        """Handle device hot-swap"""
        try:
            # Get handler for old device
            if old_device_id in self.device_handlers:
                old_handler = self.device_handlers[old_device_id]
                
                # Register new device
                await self.register_device(new_manifest)
                
                # Handle hot-swap in handler
                if new_manifest.device_id in self.device_handlers:
                    new_handler = self.device_handlers[new_manifest.device_id]
                    
                    if hasattr(old_handler, 'transfer_state'):
                        state = await old_handler.get_device_state(old_device_id)
                        await new_handler.set_device_state(new_manifest.device_id, state)
                
                # Unregister old device
                await self.unregister_device(old_device_id)
                
                return True
            
        except Exception as e:
            logger.error(f"Hot-swap failed: {e}")
        
        return False

# Generic handlers for fallback
class GenericInputHandler(BaseDeviceHandler):
    """Generic input device handler"""
    
    def __init__(self):
        super().__init__()
        self.device_type = "generic_input"
        self.supported_protocols = ["tcp", "udp", "http", "serial"]
    
    async def initialize_device(self, manifest: DeviceManifest) -> bool:
        return True
    
    async def connect_device(self, device_id: str) -> bool:
        return True
    
    async def disconnect_device(self, device_id: str) -> bool:
        return True
    
    async def get_device_status(self, device_id: str) -> Dict[str, Any]:
        return {"status": "connected", "type": "generic_input"}
    
    async def send_command(self, device_id: str, command: Dict[str, Any]) -> Dict[str, Any]:
        return {"result": "command_sent", "command": command}
    
    async def get_capabilities(self, device_id: str) -> List[DeviceCapability]:
        return [
            DeviceCapability(
                name="generic_input",
                type="input",
                category="generic",
                version="1.0",
                parameters={},
                quality_metrics={}
            )
        ]

class GenericOutputHandler(BaseDeviceHandler):
    """Generic output device handler"""
    
    def __init__(self):
        super().__init__()
        self.device_type = "generic_output"
        self.supported_protocols = ["tcp", "udp", "http", "serial"]
    
    async def initialize_device(self, manifest: DeviceManifest) -> bool:
        return True
    
    async def connect_device(self, device_id: str) -> bool:
        return True
    
    async def disconnect_device(self, device_id: str) -> bool:
        return True
    
    async def get_device_status(self, device_id: str) -> Dict[str, Any]:
        return {"status": "connected", "type": "generic_output"}
    
    async def send_command(self, device_id: str, command: Dict[str, Any]) -> Dict[str, Any]:
        return {"result": "command_sent", "command": command}
    
    async def get_capabilities(self, device_id: str) -> List[DeviceCapability]:
        return [
            DeviceCapability(
                name="generic_output",
                type="output",
                category="generic",
                version="1.0",
                parameters={},
                quality_metrics={}
            )
        ]

class GenericComputeHandler(BaseDeviceHandler):
    """Generic compute device handler"""
    
    def __init__(self):
        super().__init__()
        self.device_type = "generic_compute"
        self.supported_protocols = ["tcp", "http", "pcie"]
    
    async def initialize_device(self, manifest: DeviceManifest) -> bool:
        return True
    
    async def connect_device(self, device_id: str) -> bool:
        return True
    
    async def disconnect_device(self, device_id: str) -> bool:
        return True
    
    async def get_device_status(self, device_id: str) -> Dict[str, Any]:
        return {"status": "connected", "type": "generic_compute"}
    
    async def send_command(self, device_id: str, command: Dict[str, Any]) -> Dict[str, Any]:
        return {"result": "command_sent", "command": command}
    
    async def get_capabilities(self, device_id: str) -> List[DeviceCapability]:
        return [
            DeviceCapability(
                name="generic_compute",
                type="compute",
                category="generic",
                version="1.0",
                parameters={},
                quality_metrics={}
            )
        ]