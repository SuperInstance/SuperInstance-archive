import asyncio
import json
import time
import random
import uuid
import hashlib
import subprocess
import threading
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime
import socket
import struct
import requests
from urllib.parse import urljoin

class InterfaceType(Enum):
    USB = "usb"
    SERIAL = "serial"
    ETHERNET = "ethernet"
    BLUETOOTH = "bluetooth"
    WIFI = "wifi"
    I2C = "i2c"
    SPI = "spi"
    CAN = "can"
    MODBUS = "modbus"
    ZIGBEE = "zigbee"
    LORA = "lora"
    NFC = "nfc"

class DeviceCategory(Enum):
    SENSOR = "sensor"
    ACTUATOR = "actuator"
    CONTROLLER = "controller"
    DISPLAY = "display"
    STORAGE = "storage"
    NETWORK = "network"
    MEDICAL = "medical"
    INDUSTRIAL = "industrial"
    AUTOMOTIVE = "automotive"
    IOT = "iot"
    UNKNOWN = "unknown"

class DetectionStatus(Enum):
    SCANNING = "scanning"
    FOUND = "found"
    IDENTIFIED = "identified"
    CONFIGURED = "configured"
    TESTED = "tested"
    REGISTERED = "registered"
    READY = "ready"
    FAILED = "failed"

@dataclass
class DetectedDevice:
    device_id: str
    interface: InterfaceType
    address: str
    vendor_id: Optional[str] = None
    product_id: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    firmware_version: Optional[str] = None
    category: DeviceCategory = DeviceCategory.UNKNOWN
    capabilities: List[str] = None
    detection_method: str = ""
    confidence: float = 0.0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = []
        if self.metadata is None:
            self.metadata = {}

@dataclass
class OnboardingSession:
    session_id: str
    device: DetectedDevice
    status: DetectionStatus
    steps_completed: List[str]
    current_step: str
    start_time: datetime
    completion_time: Optional[datetime] = None
    driver_info: Optional[Dict[str, Any]] = None
    configuration: Dict[str, Any] = None
    test_results: Dict[str, Any] = None
    errors: List[str] = None
    
    def __post_init__(self):
        if self.configuration is None:
            self.configuration = {}
        if self.test_results is None:
            self.test_results = {}
        if self.errors is None:
            self.errors = []

class InterfaceScanner:
    def __init__(self, interface_type: InterfaceType):
        self.interface_type = interface_type
        self.is_scanning = False
        self.scan_interval = 5.0  # seconds
        self.devices_cache = {}
        
    async def start_scanning(self) -> List[DetectedDevice]:
        """Start scanning for devices on this interface"""
        self.is_scanning = True
        devices = []
        
        try:
            if self.interface_type == InterfaceType.USB:
                devices = await self._scan_usb()
            elif self.interface_type == InterfaceType.SERIAL:
                devices = await self._scan_serial()
            elif self.interface_type == InterfaceType.ETHERNET:
                devices = await self._scan_ethernet()
            elif self.interface_type == InterfaceType.BLUETOOTH:
                devices = await self._scan_bluetooth()
            elif self.interface_type == InterfaceType.WIFI:
                devices = await self._scan_wifi()
            elif self.interface_type == InterfaceType.I2C:
                devices = await self._scan_i2c()
            elif self.interface_type == InterfaceType.MODBUS:
                devices = await self._scan_modbus()
            elif self.interface_type == InterfaceType.CAN:
                devices = await self._scan_can()
            else:
                devices = await self._scan_generic()
                
        except Exception as e:
            print(f"Scan error for {self.interface_type.value}: {e}")
        
        self.is_scanning = False
        return devices
    
    async def _scan_usb(self) -> List[DetectedDevice]:
        """Scan for USB devices"""
        devices = []
        
        # Simulate USB device enumeration
        for i in range(random.randint(2, 8)):
            vendor_id = f"{random.randint(0x1000, 0xFFFF):04X}"
            product_id = f"{random.randint(0x0001, 0xFFFF):04X}"
            
            device = DetectedDevice(
                device_id=f"usb_{vendor_id}_{product_id}_{uuid.uuid4().hex[:8]}",
                interface=InterfaceType.USB,
                address=f"usb://{vendor_id}:{product_id}",
                vendor_id=vendor_id,
                product_id=product_id,
                manufacturer=random.choice(["Arduino", "Raspberry Pi Foundation", "FTDI", "Texas Instruments", "STMicroelectronics"]),
                serial_number=f"USB{random.randint(100000, 999999)}",
                detection_method="usb_enumeration",
                confidence=0.95
            )
            
            # Categorize based on vendor/product patterns
            device.category = self._categorize_usb_device(device)
            device.capabilities = self._get_usb_capabilities(device)
            
            devices.append(device)
            await asyncio.sleep(0.1)  # Simulate enumeration delay
        
        return devices
    
    async def _scan_serial(self) -> List[DetectedDevice]:
        """Scan for serial/UART devices"""
        devices = []
        
        # Simulate serial port enumeration
        ports = [f"/dev/ttyUSB{i}" for i in range(random.randint(1, 4))]
        ports.extend([f"/dev/ttyACM{i}" for i in range(random.randint(0, 2))])
        
        for port in ports:
            try:
                # Simulate opening port and probing
                await asyncio.sleep(0.5)
                
                device = DetectedDevice(
                    device_id=f"serial_{hashlib.md5(port.encode()).hexdigest()[:8]}",
                    interface=InterfaceType.SERIAL,
                    address=port,
                    manufacturer="Unknown",
                    detection_method="serial_probe",
                    confidence=0.7,
                    metadata={"baud_rate": random.choice([9600, 115200, 230400])}
                )
                
                # Try to identify device by sending probe commands
                device_info = await self._probe_serial_device(port)
                if device_info:
                    device.manufacturer = device_info.get("manufacturer", "Unknown")
                    device.model = device_info.get("model", "Unknown")
                    device.firmware_version = device_info.get("firmware", "Unknown")
                    device.confidence = 0.9
                
                device.category = DeviceCategory.CONTROLLER
                device.capabilities = ["uart", "gpio", "analog"]
                
                devices.append(device)
                
            except Exception as e:
                print(f"Error probing serial port {port}: {e}")
        
        return devices
    
    async def _scan_ethernet(self) -> List[DetectedDevice]:
        """Scan for Ethernet-connected devices"""
        devices = []
        
        # Simulate network discovery
        base_ip = "192.168.1."
        scan_tasks = []
        
        for i in range(1, 255, 10):  # Sample every 10th IP
            task = asyncio.create_task(self._probe_ip_address(f"{base_ip}{i}"))
            scan_tasks.append(task)
        
        results = await asyncio.gather(*scan_tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, DetectedDevice):
                devices.append(result)
        
        return devices
    
    async def _scan_bluetooth(self) -> List[DetectedDevice]:
        """Scan for Bluetooth devices"""
        devices = []
        
        # Simulate Bluetooth LE scan
        await asyncio.sleep(2)  # BLE scan duration
        
        for i in range(random.randint(1, 6)):
            mac_address = ":".join([f"{random.randint(0, 255):02X}" for _ in range(6)])
            
            device = DetectedDevice(
                device_id=f"ble_{mac_address.replace(':', '')}",
                interface=InterfaceType.BLUETOOTH,
                address=mac_address,
                manufacturer=random.choice(["Apple", "Samsung", "Google", "Nordic", "Dialog"]),
                detection_method="bluetooth_scan",
                confidence=0.8,
                metadata={
                    "rssi": random.randint(-80, -20),
                    "tx_power": random.randint(-20, 10)
                }
            )
            
            device.category = DeviceCategory.IOT
            device.capabilities = ["ble", "gatt"]
            
            devices.append(device)
        
        return devices
    
    async def _scan_wifi(self) -> List[DetectedDevice]:
        """Scan for WiFi devices"""
        devices = []
        
        # Simulate WiFi network scan and device discovery
        await asyncio.sleep(3)
        
        for i in range(random.randint(2, 8)):
            device = DetectedDevice(
                device_id=f"wifi_{uuid.uuid4().hex[:12]}",
                interface=InterfaceType.WIFI,
                address=f"192.168.1.{random.randint(100, 200)}",
                manufacturer=random.choice(["Espressif", "Realtek", "Broadcom", "Qualcomm"]),
                detection_method="wifi_discovery",
                confidence=0.85,
                metadata={
                    "ssid": f"Device_{random.randint(1000, 9999)}",
                    "channel": random.randint(1, 11),
                    "security": random.choice(["WPA2", "WPA3", "Open"])
                }
            )
            
            device.category = DeviceCategory.IOT
            device.capabilities = ["wifi", "tcp", "udp", "http"]
            
            devices.append(device)
        
        return devices
    
    async def _scan_i2c(self) -> List[DetectedDevice]:
        """Scan for I2C devices"""
        devices = []
        
        # Simulate I2C bus scan
        for addr in [0x48, 0x68, 0x76, 0x3C, 0x57]:  # Common I2C addresses
            if random.random() < 0.7:  # 70% chance device present
                device = DetectedDevice(
                    device_id=f"i2c_{addr:02X}",
                    interface=InterfaceType.I2C,
                    address=f"0x{addr:02X}",
                    detection_method="i2c_scan",
                    confidence=0.9,
                    metadata={"bus": 1, "clock_speed": 100000}
                )
                
                # Identify common I2C devices by address
                device_info = self._identify_i2c_device(addr)
                device.manufacturer = device_info["manufacturer"]
                device.model = device_info["model"]
                device.category = device_info["category"]
                device.capabilities = device_info["capabilities"]
                
                devices.append(device)
        
        return devices
    
    async def _scan_modbus(self) -> List[DetectedDevice]:
        """Scan for Modbus devices"""
        devices = []
        
        # Simulate Modbus RTU/TCP scan
        for slave_id in range(1, 10):
            if random.random() < 0.3:  # 30% chance device present
                device = DetectedDevice(
                    device_id=f"modbus_{slave_id}",
                    interface=InterfaceType.MODBUS,
                    address=f"slave_{slave_id}",
                    manufacturer=random.choice(["Schneider Electric", "Siemens", "ABB", "Honeywell"]),
                    detection_method="modbus_scan",
                    confidence=0.8,
                    metadata={"slave_id": slave_id, "baud_rate": 9600}
                )
                
                device.category = DeviceCategory.INDUSTRIAL
                device.capabilities = ["modbus_rtu", "holding_registers", "input_registers"]
                
                devices.append(device)
        
        return devices
    
    async def _scan_can(self) -> List[DetectedDevice]:
        """Scan for CAN bus devices"""
        devices = []
        
        # Simulate CAN bus scan
        for node_id in [0x123, 0x456, 0x789]:
            if random.random() < 0.5:
                device = DetectedDevice(
                    device_id=f"can_{node_id:03X}",
                    interface=InterfaceType.CAN,
                    address=f"0x{node_id:03X}",
                    manufacturer=random.choice(["Bosch", "Vector", "Peak System", "Kvaser"]),
                    detection_method="can_scan",
                    confidence=0.85,
                    metadata={"bitrate": 500000, "node_id": node_id}
                )
                
                device.category = DeviceCategory.AUTOMOTIVE
                device.capabilities = ["can_2.0", "extended_frame"]
                
                devices.append(device)
        
        return devices
    
    async def _scan_generic(self) -> List[DetectedDevice]:
        """Generic scanner for other interfaces"""
        devices = []
        
        # Simulate generic device discovery
        device = DetectedDevice(
            device_id=f"{self.interface_type.value}_{uuid.uuid4().hex[:8]}",
            interface=self.interface_type,
            address="auto",
            manufacturer="Generic",
            detection_method="generic_scan",
            confidence=0.5
        )
        
        devices.append(device)
        return devices
    
    def _categorize_usb_device(self, device: DetectedDevice) -> DeviceCategory:
        """Categorize USB device based on vendor/product ID"""
        vid = device.vendor_id.lower() if device.vendor_id else ""
        manufacturer = device.manufacturer.lower() if device.manufacturer else ""
        
        if "arduino" in manufacturer or vid in ["2341"]:
            return DeviceCategory.CONTROLLER
        elif "ftdi" in manufacturer or vid in ["0403"]:
            return DeviceCategory.CONTROLLER
        elif "raspberry" in manufacturer:
            return DeviceCategory.CONTROLLER
        elif "texas" in manufacturer or "ti" in manufacturer:
            return DeviceCategory.SENSOR
        else:
            return DeviceCategory.UNKNOWN
    
    def _get_usb_capabilities(self, device: DetectedDevice) -> List[str]:
        """Get USB device capabilities"""
        capabilities = ["usb"]
        
        if device.category == DeviceCategory.CONTROLLER:
            capabilities.extend(["gpio", "uart", "i2c", "spi"])
        elif device.category == DeviceCategory.SENSOR:
            capabilities.extend(["adc", "temperature", "humidity"])
        
        return capabilities
    
    async def _probe_serial_device(self, port: str) -> Optional[Dict[str, str]]:
        """Probe serial device for identification"""
        # Simulate serial communication
        await asyncio.sleep(0.2)
        
        if random.random() < 0.6:  # 60% success rate
            return {
                "manufacturer": random.choice(["Arduino", "Espressif", "STMicroelectronics"]),
                "model": f"Model-{random.randint(100, 999)}",
                "firmware": f"v{random.randint(1, 5)}.{random.randint(0, 9)}.{random.randint(0, 9)}"
            }
        return None
    
    async def _probe_ip_address(self, ip: str) -> Optional[DetectedDevice]:
        """Probe IP address for devices"""
        try:
            # Simulate network probe
            await asyncio.sleep(0.1)
            
            if random.random() < 0.1:  # 10% chance device found
                device = DetectedDevice(
                    device_id=f"eth_{ip.replace('.', '_')}",
                    interface=InterfaceType.ETHERNET,
                    address=ip,
                    manufacturer=random.choice(["Siemens", "Schneider", "Rockwell", "Honeywell"]),
                    detection_method="tcp_probe",
                    confidence=0.8,
                    metadata={"port": random.choice([80, 443, 502, 102])}
                )
                
                device.category = DeviceCategory.INDUSTRIAL
                device.capabilities = ["tcp", "http", "modbus_tcp"]
                
                return device
                
        except Exception:
            pass
        
        return None
    
    def _identify_i2c_device(self, address: int) -> Dict[str, Any]:
        """Identify I2C device by address"""
        i2c_devices = {
            0x48: {"manufacturer": "Texas Instruments", "model": "TMP75", "category": DeviceCategory.SENSOR, "capabilities": ["temperature"]},
            0x68: {"manufacturer": "InvenSense", "model": "MPU6050", "category": DeviceCategory.SENSOR, "capabilities": ["accelerometer", "gyroscope"]},
            0x76: {"manufacturer": "Bosch", "model": "BME280", "category": DeviceCategory.SENSOR, "capabilities": ["temperature", "humidity", "pressure"]},
            0x3C: {"manufacturer": "Solomon Systech", "model": "SSD1306", "category": DeviceCategory.DISPLAY, "capabilities": ["oled", "128x64"]},
            0x57: {"manufacturer": "Microchip", "model": "24LC256", "category": DeviceCategory.STORAGE, "capabilities": ["eeprom", "32kb"]}
        }
        
        return i2c_devices.get(address, {
            "manufacturer": "Unknown",
            "model": f"I2C_0x{address:02X}",
            "category": DeviceCategory.UNKNOWN,
            "capabilities": ["i2c"]
        })

class DriverManager:
    def __init__(self):
        self.driver_registry = {}
        self.download_cache = {}
        self.driver_repositories = [
            "https://drivers.activelog.ai/",
            "https://github.com/universal-drivers/",
            "https://registry.npmjs.org/@universal-drivers/"
        ]
    
    async def find_driver(self, device: DetectedDevice) -> Optional[Dict[str, Any]]:
        """Find appropriate driver for device"""
        # Generate driver search key
        search_keys = []
        
        if device.vendor_id and device.product_id:
            search_keys.append(f"{device.vendor_id}:{device.product_id}")
        
        if device.manufacturer and device.model:
            search_keys.append(f"{device.manufacturer}_{device.model}")
        
        search_keys.append(f"{device.interface.value}_{device.category.value}")
        
        # Search for driver
        for key in search_keys:
            driver_info = await self._search_driver_repositories(key)
            if driver_info:
                return driver_info
        
        # Try generic driver
        return await self._get_generic_driver(device)
    
    async def _search_driver_repositories(self, search_key: str) -> Optional[Dict[str, Any]]:
        """Search driver repositories"""
        # Simulate driver search
        await asyncio.sleep(0.5)
        
        if random.random() < 0.7:  # 70% chance of finding driver
            return {
                "name": f"driver_{search_key.lower()}",
                "version": f"{random.randint(1, 5)}.{random.randint(0, 9)}.{random.randint(0, 9)}",
                "repository": random.choice(self.driver_repositories),
                "download_url": f"https://drivers.activelog.ai/{search_key}/driver.zip",
                "checksum": hashlib.sha256(search_key.encode()).hexdigest(),
                "languages": random.sample(["python", "c", "javascript", "rust"], random.randint(1, 3)),
                "protocols": ["usb", "serial", "i2c"],
                "documentation": f"https://docs.activelog.ai/drivers/{search_key}",
                "examples": [
                    f"https://github.com/examples/{search_key}/basic.py",
                    f"https://github.com/examples/{search_key}/advanced.py"
                ],
                "license": "MIT",
                "rating": round(random.uniform(4.0, 5.0), 1),
                "downloads": random.randint(1000, 100000)
            }
        
        return None
    
    async def _get_generic_driver(self, device: DetectedDevice) -> Dict[str, Any]:
        """Get generic driver for device category"""
        return {
            "name": f"generic_{device.category.value}",
            "version": "1.0.0",
            "repository": "builtin",
            "download_url": None,
            "languages": ["python"],
            "protocols": [device.interface.value],
            "documentation": f"https://docs.activelog.ai/generic/{device.category.value}",
            "license": "MIT",
            "rating": 3.5,
            "downloads": 50000,
            "generic": True
        }
    
    async def download_driver(self, driver_info: Dict[str, Any]) -> str:
        """Download driver package"""
        if driver_info.get("generic") or not driver_info.get("download_url"):
            return "builtin"
        
        # Simulate driver download
        download_url = driver_info["download_url"]
        print(f"Downloading driver from {download_url}...")
        
        await asyncio.sleep(random.uniform(1.0, 3.0))  # Simulate download time
        
        # Simulate download path
        driver_path = f"/tmp/drivers/{driver_info['name']}"
        
        # Cache download
        self.download_cache[driver_info["name"]] = {
            "path": driver_path,
            "downloaded_at": datetime.now(),
            "info": driver_info
        }
        
        print(f"Driver downloaded to {driver_path}")
        return driver_path

class AutomaticDetection:
    def __init__(self):
        self.scanners = {}
        self.driver_manager = DriverManager()
        self.onboarding_sessions = {}
        self.registered_devices = {}
        self.callbacks = {
            "device_found": [],
            "session_updated": [],
            "device_registered": []
        }
        
        # Initialize scanners for all interface types
        for interface_type in InterfaceType:
            self.scanners[interface_type] = InterfaceScanner(interface_type)
    
    def register_callback(self, event_type: str, callback: Callable):
        """Register event callback"""
        if event_type in self.callbacks:
            self.callbacks[event_type].append(callback)
    
    async def start_discovery(self, interfaces: List[InterfaceType] = None) -> List[DetectedDevice]:
        """Start automatic device discovery"""
        if interfaces is None:
            interfaces = list(InterfaceType)
        
        print("Starting automatic device discovery...")
        
        all_devices = []
        scan_tasks = []
        
        # Start scanning on all specified interfaces
        for interface_type in interfaces:
            if interface_type in self.scanners:
                task = asyncio.create_task(self.scanners[interface_type].start_scanning())
                scan_tasks.append(task)
        
        # Wait for all scans to complete
        scan_results = await asyncio.gather(*scan_tasks, return_exceptions=True)
        
        # Collect all discovered devices
        for result in scan_results:
            if isinstance(result, list):
                all_devices.extend(result)
            elif isinstance(result, Exception):
                print(f"Scan error: {result}")
        
        print(f"Discovery complete: found {len(all_devices)} devices")
        
        # Trigger callbacks
        for device in all_devices:
            for callback in self.callbacks["device_found"]:
                try:
                    callback(device)
                except Exception as e:
                    print(f"Device found callback error: {e}")
        
        return all_devices
    
    async def onboard_device(self, device: DetectedDevice) -> OnboardingSession:
        """Start automatic onboarding process for device"""
        session_id = f"session_{uuid.uuid4().hex[:12]}"
        
        session = OnboardingSession(
            session_id=session_id,
            device=device,
            status=DetectionStatus.FOUND,
            steps_completed=[],
            current_step="identify",
            start_time=datetime.now()
        )
        
        self.onboarding_sessions[session_id] = session
        
        print(f"Starting onboarding for {device.device_id}")
        
        # Start onboarding process
        asyncio.create_task(self._onboard_device_async(session))
        
        return session
    
    async def _onboard_device_async(self, session: OnboardingSession):
        """Asynchronous onboarding process"""
        try:
            # Step 1: Identify device
            await self._identify_device(session)
            
            # Step 2: Find and download driver
            await self._download_driver(session)
            
            # Step 3: Configure device
            await self._configure_device(session)
            
            # Step 4: Test functionality
            await self._test_device(session)
            
            # Step 5: Register in system
            await self._register_device(session)
            
            # Step 6: Assign resources
            await self._assign_resources(session)
            
            # Step 7: Set permissions
            await self._set_permissions(session)
            
            # Step 8: Create dashboard
            await self._create_dashboard(session)
            
            # Step 9: Generate API keys
            await self._generate_api_keys(session)
            
            # Complete onboarding
            session.status = DetectionStatus.READY
            session.completion_time = datetime.now()
            session.current_step = "completed"
            
            print(f"✅ Device {session.device.device_id} onboarded successfully!")
            
        except Exception as e:
            session.status = DetectionStatus.FAILED
            session.errors.append(str(e))
            session.current_step = "failed"
            print(f"❌ Onboarding failed for {session.device.device_id}: {e}")
        
        # Trigger session update callback
        for callback in self.callbacks["session_updated"]:
            try:
                callback(session)
            except Exception as e:
                print(f"Session update callback error: {e}")
    
    async def _identify_device(self, session: OnboardingSession):
        """Step 1: Identify device"""
        session.current_step = "identify"
        print(f"Identifying device {session.device.device_id}...")
        
        # Simulate device identification
        await asyncio.sleep(1.0)
        
        # Enhanced identification based on interface
        device = session.device
        
        if device.interface == InterfaceType.USB and not device.manufacturer:
            # Try to get more USB details
            device.manufacturer = random.choice(["Arduino", "FTDI", "STMicroelectronics"])
            device.model = f"Device-{random.randint(1000, 9999)}"
            device.confidence = min(device.confidence + 0.2, 1.0)
        
        session.steps_completed.append("identify")
        session.status = DetectionStatus.IDENTIFIED
        
        print(f"Device identified: {device.manufacturer} {device.model}")
    
    async def _download_driver(self, session: OnboardingSession):
        """Step 2: Find and download driver"""
        session.current_step = "download_driver"
        print(f"Finding driver for {session.device.device_id}...")
        
        # Find appropriate driver
        driver_info = await self.driver_manager.find_driver(session.device)
        
        if not driver_info:
            raise Exception("No compatible driver found")
        
        session.driver_info = driver_info
        
        # Download driver
        driver_path = await self.driver_manager.download_driver(driver_info)
        session.driver_info["local_path"] = driver_path
        
        session.steps_completed.append("download_driver")
        
        print(f"Driver found: {driver_info['name']} v{driver_info['version']}")
    
    async def _configure_device(self, session: OnboardingSession):
        """Step 3: Configure device"""
        session.current_step = "configure"
        print(f"Configuring device {session.device.device_id}...")
        
        # Simulate device configuration
        await asyncio.sleep(0.5)
        
        # Generate configuration based on device type
        config = {
            "interface": session.device.interface.value,
            "address": session.device.address,
            "protocol_settings": {},
            "sampling_rate": random.choice([1, 10, 100, 1000]),  # Hz
            "buffer_size": random.choice([1024, 4096, 8192]),
            "timeout": 5.0,
            "auto_reconnect": True
        }
        
        # Interface-specific configuration
        if session.device.interface == InterfaceType.SERIAL:
            config["protocol_settings"] = {
                "baud_rate": session.device.metadata.get("baud_rate", 115200),
                "data_bits": 8,
                "stop_bits": 1,
                "parity": "none",
                "flow_control": "none"
            }
        elif session.device.interface == InterfaceType.I2C:
            config["protocol_settings"] = {
                "clock_speed": session.device.metadata.get("clock_speed", 100000),
                "address_mode": "7bit"
            }
        elif session.device.interface == InterfaceType.ETHERNET:
            config["protocol_settings"] = {
                "port": session.device.metadata.get("port", 502),
                "protocol": "tcp"
            }
        
        session.configuration = config
        session.steps_completed.append("configure")
        
        print("Device configuration completed")
    
    async def _test_device(self, session: OnboardingSession):
        """Step 4: Test device functionality"""
        session.current_step = "test"
        print(f"Testing device {session.device.device_id}...")
        
        # Simulate device testing
        await asyncio.sleep(2.0)
        
        test_results = {
            "connection_test": random.random() > 0.1,  # 90% pass rate
            "communication_test": random.random() > 0.05,  # 95% pass rate
            "functionality_test": random.random() > 0.15,  # 85% pass rate
            "performance_test": {
                "latency_ms": random.uniform(1.0, 50.0),
                "throughput_bps": random.randint(9600, 1000000),
                "error_rate": random.uniform(0.0, 0.01)
            }
        }
        
        session.test_results = test_results
        session.steps_completed.append("test")
        session.status = DetectionStatus.TESTED
        
        # Check if all tests passed
        basic_tests = ["connection_test", "communication_test", "functionality_test"]
        if not all(test_results.get(test, False) for test in basic_tests):
            raise Exception(f"Device tests failed: {test_results}")
        
        print("✅ All device tests passed")
    
    async def _register_device(self, session: OnboardingSession):
        """Step 5: Register device in system"""
        session.current_step = "register"
        print(f"Registering device {session.device.device_id}...")
        
        # Create device registration
        registration = {
            "device_id": session.device.device_id,
            "name": f"{session.device.manufacturer} {session.device.model}",
            "category": session.device.category.value,
            "interface": session.device.interface.value,
            "address": session.device.address,
            "driver": session.driver_info["name"],
            "configuration": session.configuration,
            "capabilities": session.device.capabilities,
            "registered_at": datetime.now().isoformat(),
            "status": "active"
        }
        
        # Register device
        self.registered_devices[session.device.device_id] = registration
        
        session.steps_completed.append("register")
        session.status = DetectionStatus.REGISTERED
        
        # Trigger device registered callback
        for callback in self.callbacks["device_registered"]:
            try:
                callback(registration)
            except Exception as e:
                print(f"Device registered callback error: {e}")
        
        print("Device registered in system")
    
    async def _assign_resources(self, session: OnboardingSession):
        """Step 6: Assign system resources"""
        session.current_step = "assign_resources"
        print(f"Assigning resources for {session.device.device_id}...")
        
        # Simulate resource assignment
        await asyncio.sleep(0.3)
        
        resources = {
            "cpu_allocation": random.uniform(0.1, 5.0),  # % CPU
            "memory_allocation": random.randint(1, 100),  # MB
            "network_bandwidth": random.randint(100, 10000),  # kbps
            "storage_quota": random.randint(10, 1000),  # MB
            "process_priority": random.choice(["low", "normal", "high"]),
            "thread_pool_size": random.randint(1, 8)
        }
        
        session.configuration["resources"] = resources
        session.steps_completed.append("assign_resources")
        
        print("System resources assigned")
    
    async def _set_permissions(self, session: OnboardingSession):
        """Step 7: Set device permissions"""
        session.current_step = "set_permissions"
        print(f"Setting permissions for {session.device.device_id}...")
        
        # Generate permission set based on device category
        permissions = {
            "read_data": True,
            "write_data": session.device.category in [DeviceCategory.ACTUATOR, DeviceCategory.CONTROLLER],
            "configure": False,  # Requires admin
            "firmware_update": False,  # Requires admin
            "diagnostic_access": True,
            "api_access": True,
            "dashboard_access": True
        }
        
        # Add interface-specific permissions
        if session.device.interface in [InterfaceType.ETHERNET, InterfaceType.WIFI]:
            permissions["network_access"] = True
        
        session.configuration["permissions"] = permissions
        session.steps_completed.append("set_permissions")
        
        print("Device permissions configured")
    
    async def _create_dashboard(self, session: OnboardingSession):
        """Step 8: Create device dashboard"""
        session.current_step = "create_dashboard"
        print(f"Creating dashboard for {session.device.device_id}...")
        
        # Simulate dashboard creation
        await asyncio.sleep(0.5)
        
        dashboard_config = {
            "dashboard_id": f"dash_{session.device.device_id}",
            "title": f"{session.device.manufacturer} {session.device.model}",
            "widgets": [],
            "layout": "auto",
            "refresh_interval": 5000,  # ms
            "theme": "default"
        }
        
        # Add widgets based on device category
        if session.device.category == DeviceCategory.SENSOR:
            dashboard_config["widgets"] = [
                {"type": "line_chart", "data_source": "sensor_readings", "title": "Sensor Data"},
                {"type": "gauge", "data_source": "current_value", "title": "Current Reading"},
                {"type": "status", "data_source": "connection_status", "title": "Connection Status"}
            ]
        elif session.device.category == DeviceCategory.CONTROLLER:
            dashboard_config["widgets"] = [
                {"type": "control_panel", "data_source": "controls", "title": "Device Controls"},
                {"type": "status_grid", "data_source": "gpio_states", "title": "GPIO Status"},
                {"type": "log_viewer", "data_source": "device_logs", "title": "Device Logs"}
            ]
        else:
            dashboard_config["widgets"] = [
                {"type": "status", "data_source": "device_status", "title": "Device Status"},
                {"type": "info_panel", "data_source": "device_info", "title": "Device Information"}
            ]
        
        session.configuration["dashboard"] = dashboard_config
        session.steps_completed.append("create_dashboard")
        
        print(f"Dashboard created: /dashboard/{dashboard_config['dashboard_id']}")
    
    async def _generate_api_keys(self, session: OnboardingSession):
        """Step 9: Generate API keys"""
        session.current_step = "generate_api_keys"
        print(f"Generating API keys for {session.device.device_id}...")
        
        # Generate API keys
        api_keys = {
            "read_key": f"rd_{uuid.uuid4().hex}",
            "write_key": f"wr_{uuid.uuid4().hex}" if session.configuration["permissions"]["write_data"] else None,
            "admin_key": f"ad_{uuid.uuid4().hex}",
            "webhook_secret": hashlib.sha256(f"{session.device.device_id}_{time.time()}".encode()).hexdigest()[:32]
        }
        
        # Remove None values
        api_keys = {k: v for k, v in api_keys.items() if v is not None}
        
        session.configuration["api_keys"] = api_keys
        session.steps_completed.append("generate_api_keys")
        
        print("API keys generated")
    
    def get_onboarding_status(self, session_id: str) -> Optional[OnboardingSession]:
        """Get onboarding session status"""
        return self.onboarding_sessions.get(session_id)
    
    def get_registered_devices(self) -> Dict[str, Any]:
        """Get all registered devices"""
        return self.registered_devices.copy()
    
    def get_discovery_statistics(self) -> Dict[str, Any]:
        """Get discovery statistics"""
        total_sessions = len(self.onboarding_sessions)
        completed_sessions = sum(1 for s in self.onboarding_sessions.values() if s.status == DetectionStatus.READY)
        failed_sessions = sum(1 for s in self.onboarding_sessions.values() if s.status == DetectionStatus.FAILED)
        
        return {
            "total_devices_discovered": sum(len(scanner.devices_cache) for scanner in self.scanners.values()),
            "total_onboarding_sessions": total_sessions,
            "completed_sessions": completed_sessions,
            "failed_sessions": failed_sessions,
            "success_rate": (completed_sessions / max(1, total_sessions)) * 100,
            "registered_devices": len(self.registered_devices),
            "interface_coverage": list(InterfaceType),
            "supported_categories": list(DeviceCategory)
        }

if __name__ == "__main__":
    print("Automatic Device Detection System")
    print("=" * 50)
    
    async def demo():
        # Create automatic detection system
        detector = AutomaticDetection()
        
        # Register callbacks
        def on_device_found(device):
            print(f"🔍 Device found: {device.manufacturer} {device.model} on {device.interface.value}")
        
        def on_session_updated(session):
            print(f"📊 Session {session.session_id}: {session.current_step} - {session.status.value}")
        
        def on_device_registered(registration):
            print(f"✅ Device registered: {registration['name']} ({registration['device_id']})")
        
        detector.register_callback("device_found", on_device_found)
        detector.register_callback("session_updated", on_session_updated)
        detector.register_callback("device_registered", on_device_registered)
        
        # Start device discovery
        interfaces = [InterfaceType.USB, InterfaceType.SERIAL, InterfaceType.I2C, InterfaceType.ETHERNET]
        devices = await detector.start_discovery(interfaces)
        
        print(f"\nDiscovered {len(devices)} devices:")
        for device in devices:
            print(f"  - {device.device_id}: {device.manufacturer} {device.model}")
            print(f"    Interface: {device.interface.value}, Confidence: {device.confidence:.1%}")
        
        # Start onboarding for first few devices
        onboarding_tasks = []
        for device in devices[:3]:  # Onboard first 3 devices
            task = asyncio.create_task(detector.onboard_device(device))
            onboarding_tasks.append(task)
        
        # Wait for onboarding to complete
        sessions = await asyncio.gather(*onboarding_tasks)
        
        # Wait a bit for async onboarding to complete
        await asyncio.sleep(10)
        
        # Show final statistics
        stats = detector.get_discovery_statistics()
        print(f"\n--- Discovery Statistics ---")
        print(f"Total devices discovered: {stats['total_devices_discovered']}")
        print(f"Onboarding sessions: {stats['total_onboarding_sessions']}")
        print(f"Success rate: {stats['success_rate']:.1f}%")
        print(f"Registered devices: {stats['registered_devices']}")
        
        # Show registered devices
        registered = detector.get_registered_devices()
        print(f"\n--- Registered Devices ({len(registered)}) ---")
        for device_id, info in registered.items():
            print(f"  {info['name']} ({device_id})")
            print(f"    Category: {info['category']}, Interface: {info['interface']}")
            print(f"    Driver: {info['driver']}")
        
        print("\nAutomatic detection demo completed")
    
    asyncio.run(demo())