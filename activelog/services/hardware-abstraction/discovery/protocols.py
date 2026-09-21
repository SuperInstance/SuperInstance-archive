"""
Additional Device Discovery Protocols
USB, Bluetooth, Serial, UPnP, and other discovery methods
"""

import asyncio
import logging
import subprocess
import json
import re
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class DiscoveryProtocol(ABC):
    """Base class for discovery protocols"""
    
    def __init__(self):
        self.callback: Optional[Callable] = None
        self.active = False
    
    def set_callback(self, callback: Callable):
        """Set discovery callback"""
        self.callback = callback
    
    @abstractmethod
    async def start(self):
        """Start the discovery protocol"""
        pass
    
    @abstractmethod
    async def stop(self):
        """Stop the discovery protocol"""
        pass
    
    @abstractmethod
    async def scan(self):
        """Perform immediate scan"""
        pass

class USBDeviceDiscovery(DiscoveryProtocol):
    """USB device discovery using lsusb and pyusb"""
    
    def __init__(self):
        super().__init__()
        self.known_devices: Dict[str, Dict] = {}
    
    async def start(self):
        """Start USB discovery"""
        logger.info("Starting USB device discovery...")
        self.active = True
        asyncio.create_task(self.monitor_usb_devices())
    
    async def stop(self):
        """Stop USB discovery"""
        logger.info("Stopping USB device discovery...")
        self.active = False
    
    async def scan(self):
        """Scan for USB devices"""
        try:
            # Use lsusb command
            result = await asyncio.create_subprocess_exec(
                'lsusb', '-v',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0:
                devices = await self.parse_lsusb_output(stdout.decode())
                
                for device in devices:
                    device_id = f"usb_{device['vendor_id']}_{device['product_id']}_{device['bus']}_{device['device']}"
                    
                    if device_id not in self.known_devices:
                        self.known_devices[device_id] = device
                        
                        device_info = {
                            'device_id': device_id,
                            'name': f"{device.get('manufacturer', 'Unknown')} {device.get('product', 'USB Device')}",
                            'address': f"bus-{device['bus']}-device-{device['device']}",
                            'port': 0,
                            'service_type': 'usb_device',
                            'properties': {
                                'vendor_id': device['vendor_id'],
                                'product_id': device['product_id'],
                                'manufacturer': device.get('manufacturer', ''),
                                'product': device.get('product', ''),
                                'serial': device.get('serial', ''),
                                'class': device.get('device_class', ''),
                                'protocol': 'usb'
                            },
                            'method': 'usb_discovery',
                            'confidence': 0.9
                        }
                        
                        if self.callback:
                            await self.callback(device_info)
            
            # Also try pyusb if available
            await self.scan_with_pyusb()
            
        except Exception as e:
            logger.error(f"USB scan error: {e}")
    
    async def parse_lsusb_output(self, output: str) -> List[Dict]:
        """Parse lsusb -v output"""
        devices = []
        current_device = {}
        
        lines = output.split('\n')
        for line in lines:
            line = line.strip()
            
            if line.startswith('Bus ') and 'Device ' in line:
                if current_device:
                    devices.append(current_device)
                
                # Parse bus and device info
                match = re.match(r'Bus (\d+) Device (\d+): ID ([0-9a-fA-F]{4}):([0-9a-fA-F]{4})', line)
                if match:
                    current_device = {
                        'bus': match.group(1),
                        'device': match.group(2),
                        'vendor_id': match.group(3),
                        'product_id': match.group(4)
                    }
            
            elif line.startswith('iManufacturer'):
                match = re.search(r'iManufacturer\s+\d+\s+(.+)', line)
                if match:
                    current_device['manufacturer'] = match.group(1)
            
            elif line.startswith('iProduct'):
                match = re.search(r'iProduct\s+\d+\s+(.+)', line)
                if match:
                    current_device['product'] = match.group(1)
            
            elif line.startswith('iSerial'):
                match = re.search(r'iSerial\s+\d+\s+(.+)', line)
                if match:
                    current_device['serial'] = match.group(1)
            
            elif line.startswith('bDeviceClass'):
                match = re.search(r'bDeviceClass\s+(\d+)', line)
                if match:
                    current_device['device_class'] = match.group(1)
        
        if current_device:
            devices.append(current_device)
        
        return devices
    
    async def scan_with_pyusb(self):
        """Scan using pyusb library"""
        try:
            import usb.core
            import usb.util
            
            devices = usb.core.find(find_all=True)
            
            for device in devices:
                try:
                    device_id = f"usb_{device.idVendor:04x}_{device.idProduct:04x}_{device.bus}_{device.address}"
                    
                    if device_id not in self.known_devices:
                        # Get string descriptors if available
                        manufacturer = ''
                        product = ''
                        serial = ''
                        
                        try:
                            if device.iManufacturer:
                                manufacturer = usb.util.get_string(device, device.iManufacturer)
                            if device.iProduct:
                                product = usb.util.get_string(device, device.iProduct)
                            if device.iSerialNumber:
                                serial = usb.util.get_string(device, device.iSerialNumber)
                        except:
                            pass
                        
                        self.known_devices[device_id] = {
                            'vendor_id': f'{device.idVendor:04x}',
                            'product_id': f'{device.idProduct:04x}',
                            'bus': str(device.bus),
                            'device': str(device.address),
                            'manufacturer': manufacturer,
                            'product': product,
                            'serial': serial
                        }
                        
                        device_info = {
                            'device_id': device_id,
                            'name': f"{manufacturer} {product}".strip() or f"USB Device {device.idVendor:04x}:{device.idProduct:04x}",
                            'address': f"bus-{device.bus}-device-{device.address}",
                            'port': 0,
                            'service_type': 'usb_device',
                            'properties': {
                                'vendor_id': f'{device.idVendor:04x}',
                                'product_id': f'{device.idProduct:04x}',
                                'manufacturer': manufacturer,
                                'product': product,
                                'serial': serial,
                                'class': str(device.bDeviceClass),
                                'protocol': 'usb'
                            },
                            'method': 'pyusb_discovery',
                            'confidence': 0.95
                        }
                        
                        if self.callback:
                            await self.callback(device_info)
                
                except Exception as e:
                    logger.debug(f"Error processing USB device: {e}")
        
        except ImportError:
            logger.debug("pyusb not available for USB discovery")
        except Exception as e:
            logger.error(f"PyUSB scan error: {e}")
    
    async def monitor_usb_devices(self):
        """Monitor USB device changes"""
        while self.active:
            try:
                await self.scan()
                await asyncio.sleep(30)  # Check every 30 seconds
            except Exception as e:
                logger.error(f"USB monitoring error: {e}")
                await asyncio.sleep(60)

class BluetoothDiscovery(DiscoveryProtocol):
    """Bluetooth device discovery using bleak"""
    
    def __init__(self):
        super().__init__()
        self.known_devices: Dict[str, Dict] = {}
    
    async def start(self):
        """Start Bluetooth discovery"""
        logger.info("Starting Bluetooth device discovery...")
        self.active = True
        asyncio.create_task(self.monitor_bluetooth_devices())
    
    async def stop(self):
        """Stop Bluetooth discovery"""
        logger.info("Stopping Bluetooth device discovery...")
        self.active = False
    
    async def scan(self):
        """Scan for Bluetooth devices"""
        try:
            import bleak
            
            scanner = bleak.BleakScanner()
            devices = await scanner.discover(timeout=10.0)
            
            for device in devices:
                device_id = f"bluetooth_{device.address.replace(':', '_')}"
                
                if device_id not in self.known_devices or self.known_devices[device_id]['name'] != device.name:
                    self.known_devices[device_id] = {
                        'address': device.address,
                        'name': device.name or 'Unknown Bluetooth Device',
                        'rssi': device.rssi
                    }
                    
                    device_info = {
                        'device_id': device_id,
                        'name': device.name or f"Bluetooth Device {device.address}",
                        'address': device.address,
                        'port': 0,
                        'service_type': 'bluetooth_device',
                        'properties': {
                            'mac_address': device.address,
                            'rssi': device.rssi,
                            'protocol': 'bluetooth_le'
                        },
                        'method': 'bluetooth_discovery',
                        'confidence': 0.8
                    }
                    
                    if self.callback:
                        await self.callback(device_info)
        
        except ImportError:
            logger.debug("bleak not available for Bluetooth discovery")
        except Exception as e:
            logger.error(f"Bluetooth scan error: {e}")
    
    async def monitor_bluetooth_devices(self):
        """Monitor Bluetooth device changes"""
        while self.active:
            try:
                await self.scan()
                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Bluetooth monitoring error: {e}")
                await asyncio.sleep(120)

class SerialPortDiscovery(DiscoveryProtocol):
    """Serial port device discovery"""
    
    def __init__(self):
        super().__init__()
        self.known_devices: Dict[str, Dict] = {}
    
    async def start(self):
        """Start serial port discovery"""
        logger.info("Starting serial port discovery...")
        self.active = True
        asyncio.create_task(self.monitor_serial_ports())
    
    async def stop(self):
        """Stop serial port discovery"""
        logger.info("Stopping serial port discovery...")
        self.active = False
    
    async def scan(self):
        """Scan for serial ports"""
        try:
            import serial.tools.list_ports
            
            ports = serial.tools.list_ports.comports()
            
            for port in ports:
                device_id = f"serial_{port.device.replace('/', '_')}"
                
                if device_id not in self.known_devices:
                    self.known_devices[device_id] = {
                        'device': port.device,
                        'description': port.description,
                        'hwid': port.hwid,
                        'vid': port.vid,
                        'pid': port.pid,
                        'serial_number': port.serial_number,
                        'manufacturer': port.manufacturer
                    }
                    
                    device_info = {
                        'device_id': device_id,
                        'name': port.description or f"Serial Device {port.device}",
                        'address': port.device,
                        'port': 0,
                        'service_type': 'serial_device',
                        'properties': {
                            'device_path': port.device,
                            'description': port.description,
                            'hwid': port.hwid,
                            'vendor_id': port.vid,
                            'product_id': port.pid,
                            'serial_number': port.serial_number,
                            'manufacturer': port.manufacturer,
                            'protocol': 'serial'
                        },
                        'method': 'serial_discovery',
                        'confidence': 0.85
                    }
                    
                    if self.callback:
                        await self.callback(device_info)
        
        except ImportError:
            logger.debug("pyserial not available for serial port discovery")
        except Exception as e:
            logger.error(f"Serial port scan error: {e}")
    
    async def monitor_serial_ports(self):
        """Monitor serial port changes"""
        while self.active:
            try:
                await self.scan()
                await asyncio.sleep(30)  # Check every 30 seconds
            except Exception as e:
                logger.error(f"Serial port monitoring error: {e}")
                await asyncio.sleep(60)

class NetworkScanDiscovery(DiscoveryProtocol):
    """Network-based device discovery"""
    
    def __init__(self):
        super().__init__()
        self.known_devices: Dict[str, Dict] = {}
    
    async def start(self):
        """Start network discovery"""
        logger.info("Starting network scan discovery...")
        self.active = True
    
    async def stop(self):
        """Stop network discovery"""
        logger.info("Stopping network scan discovery...")
        self.active = False
    
    async def scan(self):
        """Network scan - handled by main mDNS discovery"""
        pass

class UPnPDiscovery(DiscoveryProtocol):
    """UPnP/SSDP device discovery"""
    
    def __init__(self):
        super().__init__()
        self.known_devices: Dict[str, Dict] = {}
    
    async def start(self):
        """Start UPnP discovery"""
        logger.info("Starting UPnP discovery...")
        self.active = True
        asyncio.create_task(self.monitor_upnp_devices())
    
    async def stop(self):
        """Stop UPnP discovery"""
        logger.info("Stopping UPnP discovery...")
        self.active = False
    
    async def scan(self):
        """Scan for UPnP devices"""
        try:
            # Use SSDP multicast to discover devices
            import socket
            import struct
            
            # SSDP discover message
            ssdp_request = (
                'M-SEARCH * HTTP/1.1\r\n'
                'HOST: 239.255.255.250:1900\r\n'
                'MAN: "ssdp:discover"\r\n'
                'ST: upnp:rootdevice\r\n'
                'MX: 3\r\n\r\n'
            )
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(5.0)
            
            try:
                sock.sendto(ssdp_request.encode(), ('239.255.255.250', 1900))
                
                responses = []
                start_time = asyncio.get_event_loop().time()
                
                while asyncio.get_event_loop().time() - start_time < 3.0:
                    try:
                        data, addr = sock.recvfrom(1024)
                        responses.append((data.decode(), addr))
                    except socket.timeout:
                        break
                
                for response, addr in responses:
                    await self.process_ssdp_response(response, addr)
            
            finally:
                sock.close()
        
        except Exception as e:
            logger.error(f"UPnP scan error: {e}")
    
    async def process_ssdp_response(self, response: str, addr: tuple):
        """Process SSDP response"""
        try:
            lines = response.split('\r\n')
            headers = {}
            
            for line in lines[1:]:  # Skip the first line (HTTP status)
                if ':' in line:
                    key, value = line.split(':', 1)
                    headers[key.strip().lower()] = value.strip()
            
            if 'location' in headers:
                device_id = f"upnp_{addr[0].replace('.', '_')}"
                
                if device_id not in self.known_devices:
                    self.known_devices[device_id] = {
                        'location': headers['location'],
                        'server': headers.get('server', ''),
                        'st': headers.get('st', ''),
                        'usn': headers.get('usn', '')
                    }
                    
                    device_info = {
                        'device_id': device_id,
                        'name': f"UPnP Device {addr[0]}",
                        'address': addr[0],
                        'port': 0,
                        'service_type': 'upnp_device',
                        'properties': {
                            'location': headers['location'],
                            'server': headers.get('server', ''),
                            'service_type': headers.get('st', ''),
                            'usn': headers.get('usn', ''),
                            'protocol': 'upnp'
                        },
                        'method': 'upnp_discovery',
                        'confidence': 0.7
                    }
                    
                    if self.callback:
                        await self.callback(device_info)
        
        except Exception as e:
            logger.debug(f"Error processing SSDP response: {e}")
    
    async def monitor_upnp_devices(self):
        """Monitor UPnP devices"""
        while self.active:
            try:
                await self.scan()
                await asyncio.sleep(120)  # Check every 2 minutes
            except Exception as e:
                logger.error(f"UPnP monitoring error: {e}")
                await asyncio.sleep(120)