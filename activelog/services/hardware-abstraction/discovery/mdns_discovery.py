"""
mDNS/Zeroconf Device Discovery System
Automatically discovers devices on the network using mDNS, Zeroconf, and other protocols
"""

import asyncio
import logging
import socket
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
import ipaddress

from zeroconf import ServiceBrowser, ServiceListener, Zeroconf, ServiceInfo
from zeroconf.asyncio import AsyncZeroconf

from core.udp_core import DeviceManifest, DeviceCapability

logger = logging.getLogger(__name__)

@dataclass
class DiscoveredDevice:
    """Represents a discovered device"""
    device_id: str
    name: str
    address: str
    port: int
    service_type: str
    properties: Dict[str, Any]
    discovery_method: str
    first_seen: datetime
    last_seen: datetime
    confidence_score: float

class DeviceDiscoveryListener(ServiceListener):
    """Zeroconf service listener for device discovery"""
    
    def __init__(self, discovery_manager):
        self.discovery_manager = discovery_manager
    
    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        """Called when a service is updated"""
        asyncio.create_task(self.discovery_manager.handle_service_update(zc, type_, name))
    
    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        """Called when a service is removed"""
        asyncio.create_task(self.discovery_manager.handle_service_removal(zc, type_, name))
    
    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        """Called when a service is added"""
        asyncio.create_task(self.discovery_manager.handle_service_addition(zc, type_, name))

class mDNSDeviceDiscovery:
    """Main mDNS/Zeroconf device discovery system"""
    
    def __init__(self, config):
        self.config = config
        self.discovered_devices: Dict[str, DiscoveredDevice] = {}
        self.device_callback: Optional[Callable] = None
        self.zeroconf: Optional[AsyncZeroconf] = None
        self.browsers: List[ServiceBrowser] = []
        self.active = False
        
        # Service types to discover
        self.service_types = [
            "_http._tcp.local.",
            "_https._tcp.local.",
            "_ssh._tcp.local.",
            "_ftp._tcp.local.",
            "_printer._tcp.local.",
            "_ipp._tcp.local.",
            "_camera._tcp.local.",
            "_device._tcp.local.",
            "_udp-device._tcp.local.",
            "_activelog._tcp.local.",
            "_mqtt._tcp.local.",
            "_coap._udp.local.",
            "_websocket._tcp.local.",
            "_rtsp._tcp.local.",
            "_sip._udp.local.",
            "_arduino._tcp.local.",
            "_esp32._tcp.local.",
            "_raspberrypi._tcp.local.",
            "_homeassistant._tcp.local.",
            "_octoprint._tcp.local.",
            "_3dprinter._tcp.local.",
            "_plc._tcp.local.",
            "_modbus._tcp.local.",
            "_opcua._tcp.local.",
            "_bacnet._udp.local.",
            "_zigbee._tcp.local.",
            "_zwave._tcp.local."
        ]
        
        # Discovery protocols
        self.discovery_protocols = []
        self.setup_discovery_protocols()
    
    def setup_discovery_protocols(self):
        """Setup additional discovery protocols"""
        from .protocols import (
            USBDeviceDiscovery, 
            BluetoothDiscovery,
            SerialPortDiscovery,
            NetworkScanDiscovery,
            UPnPDiscovery
        )
        
        self.discovery_protocols = [
            USBDeviceDiscovery(),
            BluetoothDiscovery(),
            SerialPortDiscovery(),
            NetworkScanDiscovery(),
            UPnPDiscovery()
        ]
    
    async def start(self):
        """Start the discovery system"""
        logger.info("Starting mDNS device discovery...")
        
        try:
            # Initialize Zeroconf
            self.zeroconf = AsyncZeroconf()
            
            # Setup service browsers
            listener = DeviceDiscoveryListener(self)
            for service_type in self.service_types:
                browser = ServiceBrowser(self.zeroconf.zeroconf, service_type, listener)
                self.browsers.append(browser)
            
            # Start additional discovery protocols
            for protocol in self.discovery_protocols:
                await protocol.start()
                protocol.set_callback(self.handle_protocol_discovery)
            
            # Start background tasks
            asyncio.create_task(self.periodic_scan_task())
            asyncio.create_task(self.device_cleanup_task())
            
            self.active = True
            logger.info("mDNS device discovery started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start mDNS discovery: {e}")
            raise
    
    async def stop(self):
        """Stop the discovery system"""
        logger.info("Stopping mDNS device discovery...")
        
        self.active = False
        
        # Stop browsers
        for browser in self.browsers:
            browser.cancel()
        self.browsers.clear()
        
        # Close Zeroconf
        if self.zeroconf:
            await self.zeroconf.async_close()
        
        # Stop additional discovery protocols
        for protocol in self.discovery_protocols:
            await protocol.stop()
        
        logger.info("mDNS device discovery stopped")
    
    def set_device_callback(self, callback: Callable):
        """Set callback for device registration"""
        self.device_callback = callback
    
    async def scan(self):
        """Trigger an immediate discovery scan"""
        logger.info("Starting immediate device discovery scan...")
        
        try:
            # Trigger all discovery protocols
            for protocol in self.discovery_protocols:
                await protocol.scan()
            
            # Additional network scan
            await self.network_scan()
            
            logger.info(f"Discovery scan completed. Found {len(self.discovered_devices)} devices")
            
        except Exception as e:
            logger.error(f"Discovery scan failed: {e}")
    
    async def handle_service_addition(self, zc: Zeroconf, type_: str, name: str):
        """Handle new mDNS service discovery"""
        try:
            info = zc.get_service_info(type_, name)
            if info:
                await self.process_service_info(info, "mdns_addition")
        except Exception as e:
            logger.error(f"Error handling service addition {name}: {e}")
    
    async def handle_service_update(self, zc: Zeroconf, type_: str, name: str):
        """Handle mDNS service update"""
        try:
            info = zc.get_service_info(type_, name)
            if info:
                await self.process_service_info(info, "mdns_update")
        except Exception as e:
            logger.error(f"Error handling service update {name}: {e}")
    
    async def handle_service_removal(self, zc: Zeroconf, type_: str, name: str):
        """Handle mDNS service removal"""
        try:
            device_id = self.generate_device_id_from_name(name)
            if device_id in self.discovered_devices:
                logger.info(f"Device removed: {name}")
                del self.discovered_devices[device_id]
        except Exception as e:
            logger.error(f"Error handling service removal {name}: {e}")
    
    async def process_service_info(self, info: ServiceInfo, method: str):
        """Process discovered service information"""
        try:
            # Extract device information
            addresses = [socket.inet_ntoa(addr) for addr in info.addresses]
            if not addresses:
                return
            
            properties = {}
            if info.properties:
                for key, value in info.properties.items():
                    try:
                        if isinstance(value, bytes):
                            properties[key.decode('utf-8')] = value.decode('utf-8')
                        else:
                            properties[key] = str(value)
                    except:
                        pass
            
            device_id = self.generate_device_id(info.name, addresses[0], info.port)
            
            discovered_device = DiscoveredDevice(
                device_id=device_id,
                name=info.name,
                address=addresses[0],
                port=info.port,
                service_type=info.type,
                properties=properties,
                discovery_method=method,
                first_seen=datetime.utcnow() if device_id not in self.discovered_devices else self.discovered_devices[device_id].first_seen,
                last_seen=datetime.utcnow(),
                confidence_score=0.8
            )
            
            self.discovered_devices[device_id] = discovered_device
            
            # Attempt to get device manifest
            manifest = await self.create_device_manifest(discovered_device)
            if manifest and self.device_callback:
                await self.device_callback(manifest)
                
        except Exception as e:
            logger.error(f"Error processing service info: {e}")
    
    async def handle_protocol_discovery(self, device_info: Dict[str, Any]):
        """Handle discovery from additional protocols"""
        try:
            device_id = device_info.get('device_id') or self.generate_device_id_from_info(device_info)
            
            discovered_device = DiscoveredDevice(
                device_id=device_id,
                name=device_info.get('name', 'Unknown Device'),
                address=device_info.get('address', ''),
                port=device_info.get('port', 0),
                service_type=device_info.get('service_type', 'unknown'),
                properties=device_info.get('properties', {}),
                discovery_method=device_info.get('method', 'protocol'),
                first_seen=datetime.utcnow() if device_id not in self.discovered_devices else self.discovered_devices[device_id].first_seen,
                last_seen=datetime.utcnow(),
                confidence_score=device_info.get('confidence', 0.7)
            )
            
            self.discovered_devices[device_id] = discovered_device
            
            # Create device manifest
            manifest = await self.create_device_manifest(discovered_device)
            if manifest and self.device_callback:
                await self.device_callback(manifest)
                
        except Exception as e:
            logger.error(f"Error handling protocol discovery: {e}")
    
    async def create_device_manifest(self, discovered_device: DiscoveredDevice) -> Optional[DeviceManifest]:
        """Create device manifest from discovered device"""
        try:
            # Attempt to communicate with device to get capabilities
            capabilities = await self.probe_device_capabilities(discovered_device)
            
            # Generate device manifest
            manifest = DeviceManifest(
                device_id=discovered_device.device_id,
                device_name=discovered_device.name,
                manufacturer=discovered_device.properties.get('manufacturer', 'Unknown'),
                model=discovered_device.properties.get('model', 'Unknown'),
                firmware_version=discovered_device.properties.get('firmware', '1.0.0'),
                hardware_revision=discovered_device.properties.get('hardware', '1.0'),
                device_type=self.determine_device_type(discovered_device),
                capabilities=capabilities,
                communication_protocols=self.determine_protocols(discovered_device),
                power_profile={'max_power': 0.0, 'idle_power': 0.0},
                thermal_profile={'max_temp': 85.0, 'idle_temp': 25.0},
                physical_dimensions={'width': 0, 'height': 0, 'depth': 0},
                certification_info={},
                supported_standards=[],
                fingerprint='',
                last_updated=datetime.utcnow(),
                hot_swap_supported=True,
                plug_and_play=True
            )
            
            return manifest
            
        except Exception as e:
            logger.error(f"Error creating device manifest: {e}")
            return None
    
    async def probe_device_capabilities(self, discovered_device: DiscoveredDevice) -> List[DeviceCapability]:
        """Probe device to discover its capabilities"""
        capabilities = []
        
        try:
            # Try different probing methods based on service type
            if 'camera' in discovered_device.service_type.lower():
                capabilities.extend(await self.probe_camera_capabilities(discovered_device))
            elif 'printer' in discovered_device.service_type.lower():
                capabilities.extend(await self.probe_printer_capabilities(discovered_device))
            elif 'sensor' in discovered_device.properties.get('type', '').lower():
                capabilities.extend(await self.probe_sensor_capabilities(discovered_device))
            elif 'arduino' in discovered_device.service_type.lower() or 'esp32' in discovered_device.service_type.lower():
                capabilities.extend(await self.probe_microcontroller_capabilities(discovered_device))
            
            # Default HTTP probing
            if discovered_device.port in [80, 443, 8080, 8443]:
                capabilities.extend(await self.probe_http_capabilities(discovered_device))
            
            # If no specific capabilities found, add generic ones
            if not capabilities:
                capabilities.append(DeviceCapability(
                    name="network_communication",
                    type="communication",
                    category="network",
                    version="1.0",
                    parameters={"protocol": "tcp", "port": discovered_device.port},
                    quality_metrics={"reliability": 0.8}
                ))
            
        except Exception as e:
            logger.error(f"Error probing device capabilities: {e}")
        
        return capabilities
    
    async def probe_camera_capabilities(self, device: DiscoveredDevice) -> List[DeviceCapability]:
        """Probe camera-specific capabilities"""
        capabilities = []
        
        # Try common camera endpoints
        try:
            import aiohttp
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                # Try RTSP
                if device.port == 554:
                    capabilities.append(DeviceCapability(
                        name="video_stream",
                        type="input",
                        category="camera",
                        version="1.0",
                        parameters={"protocol": "rtsp", "resolution": "1920x1080"},
                        quality_metrics={"fps": 30}
                    ))
                
                # Try HTTP video stream
                try:
                    async with session.get(f"http://{device.address}:{device.port}/video") as resp:
                        if resp.status == 200:
                            capabilities.append(DeviceCapability(
                                name="http_video_stream",
                                type="input", 
                                category="camera",
                                version="1.0",
                                parameters={"protocol": "http", "endpoint": "/video"},
                                quality_metrics={"quality": 0.8}
                            ))
                except:
                    pass
                
        except ImportError:
            pass
        except Exception as e:
            logger.debug(f"Camera probe error: {e}")
        
        return capabilities
    
    async def probe_printer_capabilities(self, device: DiscoveredDevice) -> List[DeviceCapability]:
        """Probe printer-specific capabilities"""
        capabilities = []
        
        # Common printer capabilities
        capabilities.append(DeviceCapability(
            name="document_printing",
            type="output",
            category="printer",
            version="1.0",
            parameters={"formats": ["pdf", "postscript"], "color": True},
            quality_metrics={"dpi": 300}
        ))
        
        # Check for 3D printer
        if '3d' in device.name.lower() or '3d' in device.properties.get('type', '').lower():
            capabilities.append(DeviceCapability(
                name="3d_printing",
                type="output",
                category="3d_printer", 
                version="1.0",
                parameters={"materials": ["PLA", "ABS"], "build_volume": "200x200x200"},
                quality_metrics={"layer_height": 0.1}
            ))
        
        return capabilities
    
    async def probe_sensor_capabilities(self, device: DiscoveredDevice) -> List[DeviceCapability]:
        """Probe sensor-specific capabilities"""
        capabilities = []
        
        sensor_type = device.properties.get('sensor_type', 'generic')
        
        capabilities.append(DeviceCapability(
            name=f"{sensor_type}_sensing",
            type="input",
            category="sensor",
            version="1.0", 
            parameters={"type": sensor_type, "units": "varies"},
            quality_metrics={"accuracy": 0.95, "precision": 0.01}
        ))
        
        return capabilities
    
    async def probe_microcontroller_capabilities(self, device: DiscoveredDevice) -> List[DeviceCapability]:
        """Probe microcontroller capabilities"""
        capabilities = []
        
        # GPIO capabilities
        capabilities.append(DeviceCapability(
            name="digital_io",
            type="input_output",
            category="gpio",
            version="1.0",
            parameters={"pins": 32, "voltage": 3.3},
            quality_metrics={"switching_frequency": 10000}
        ))
        
        # ADC capabilities  
        capabilities.append(DeviceCapability(
            name="analog_input",
            type="input",
            category="adc", 
            version="1.0",
            parameters={"channels": 8, "resolution": 12},
            quality_metrics={"sampling_rate": 1000}
        ))
        
        return capabilities
    
    async def probe_http_capabilities(self, device: DiscoveredDevice) -> List[DeviceCapability]:
        """Probe HTTP-based capabilities"""
        capabilities = []
        
        try:
            import aiohttp
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                # Try common endpoints
                endpoints = ['/api', '/status', '/info', '/capabilities']
                
                for endpoint in endpoints:
                    try:
                        url = f"http://{device.address}:{device.port}{endpoint}"
                        async with session.get(url) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                
                                # Parse capabilities from response
                                if 'capabilities' in data:
                                    for cap_data in data['capabilities']:
                                        capability = DeviceCapability(
                                            name=cap_data.get('name', 'unknown'),
                                            type=cap_data.get('type', 'unknown'),
                                            category=cap_data.get('category', 'http'),
                                            version=cap_data.get('version', '1.0'),
                                            parameters=cap_data.get('parameters', {}),
                                            quality_metrics=cap_data.get('quality_metrics', {})
                                        )
                                        capabilities.append(capability)
                                
                                break
                    except:
                        continue
                
        except ImportError:
            pass
        except Exception as e:
            logger.debug(f"HTTP probe error: {e}")
        
        return capabilities
    
    def determine_device_type(self, device: DiscoveredDevice) -> str:
        """Determine device type from discovery information"""
        service_type = device.service_type.lower()
        name = device.name.lower()
        
        if 'camera' in service_type or 'camera' in name:
            return 'camera'
        elif 'printer' in service_type or 'printer' in name:
            return '3d_printer' if '3d' in name else 'printer'
        elif 'sensor' in name or 'sensor' in device.properties.get('type', '').lower():
            return 'sensor'
        elif 'arduino' in service_type or 'esp32' in service_type:
            return 'microcontroller'
        elif 'speaker' in name or 'audio' in name:
            return 'speaker'
        elif 'display' in name or 'monitor' in name:
            return 'display'
        else:
            return 'generic_device'
    
    def determine_protocols(self, device: DiscoveredDevice) -> List[str]:
        """Determine communication protocols"""
        protocols = []
        
        if device.port == 80:
            protocols.append('http')
        elif device.port == 443:
            protocols.append('https')
        elif device.port == 22:
            protocols.append('ssh')
        elif device.port == 554:
            protocols.append('rtsp')
        elif device.port == 1883:
            protocols.append('mqtt')
        elif device.port == 5683:
            protocols.append('coap')
        else:
            protocols.append('tcp')
        
        # Add protocol from service type
        if '_tcp.' in device.service_type:
            protocols.append('tcp')
        elif '_udp.' in device.service_type:
            protocols.append('udp')
        
        return list(set(protocols))  # Remove duplicates
    
    def generate_device_id(self, name: str, address: str, port: int) -> str:
        """Generate unique device ID"""
        import hashlib
        unique_string = f"{name}:{address}:{port}"
        return hashlib.md5(unique_string.encode()).hexdigest()[:12]
    
    def generate_device_id_from_name(self, name: str) -> str:
        """Generate device ID from service name"""
        import hashlib
        return hashlib.md5(name.encode()).hexdigest()[:12]
    
    def generate_device_id_from_info(self, info: Dict[str, Any]) -> str:
        """Generate device ID from info dict"""
        import hashlib
        unique_string = f"{info.get('name', '')}:{info.get('address', '')}:{info.get('port', 0)}"
        return hashlib.md5(unique_string.encode()).hexdigest()[:12]
    
    async def network_scan(self):
        """Perform network scan for devices"""
        try:
            # Get local network range
            local_networks = await self.get_local_networks()
            
            for network in local_networks:
                await self.scan_network_range(network)
                
        except Exception as e:
            logger.error(f"Network scan error: {e}")
    
    async def get_local_networks(self) -> List[str]:
        """Get local network ranges"""
        networks = []
        
        try:
            import netifaces
            
            for interface in netifaces.interfaces():
                addresses = netifaces.ifaddresses(interface)
                if netifaces.AF_INET in addresses:
                    for addr_info in addresses[netifaces.AF_INET]:
                        ip = addr_info.get('addr')
                        netmask = addr_info.get('netmask')
                        
                        if ip and netmask and not ip.startswith('127.'):
                            try:
                                network = ipaddress.IPv4Network(f"{ip}/{netmask}", strict=False)
                                networks.append(str(network))
                            except:
                                pass
        except ImportError:
            # Fallback to common local networks
            networks = ['192.168.1.0/24', '192.168.0.0/24', '10.0.0.0/24']
        
        return networks
    
    async def scan_network_range(self, network_range: str):
        """Scan a network range for devices"""
        try:
            network = ipaddress.IPv4Network(network_range)
            
            # Limit scan size for performance
            if network.num_addresses > 256:
                return
            
            tasks = []
            for ip in network.hosts():
                task = asyncio.create_task(self.scan_host(str(ip)))
                tasks.append(task)
                
                # Limit concurrent scans
                if len(tasks) >= 50:
                    await asyncio.gather(*tasks, return_exceptions=True)
                    tasks.clear()
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
                
        except Exception as e:
            logger.error(f"Network range scan error: {e}")
    
    async def scan_host(self, ip: str):
        """Scan a single host for services"""
        try:
            # Common service ports
            ports = [22, 23, 53, 80, 443, 554, 631, 1883, 5683, 8080, 8443, 9100]
            
            for port in ports:
                try:
                    future = asyncio.open_connection(ip, port)
                    reader, writer = await asyncio.wait_for(future, timeout=1.0)
                    writer.close()
                    await writer.wait_closed()
                    
                    # Found open port, create discovered device
                    device_info = {
                        'device_id': self.generate_device_id(f"network_scan_{ip}", ip, port),
                        'name': f"Network Device {ip}:{port}",
                        'address': ip,
                        'port': port,
                        'service_type': f'_tcp_scan_{port}._tcp.local.',
                        'properties': {'discovered_via': 'network_scan'},
                        'method': 'network_scan',
                        'confidence': 0.6
                    }
                    
                    await self.handle_protocol_discovery(device_info)
                    
                except asyncio.TimeoutError:
                    pass
                except Exception:
                    pass
                    
        except Exception:
            pass
    
    def is_active(self) -> bool:
        """Check if discovery is active"""
        return self.active
    
    async def get_status(self) -> Dict[str, Any]:
        """Get discovery status"""
        return {
            'active': self.active,
            'discovered_devices': len(self.discovered_devices),
            'service_types_monitored': len(self.service_types),
            'discovery_protocols': len(self.discovery_protocols),
            'last_scan': datetime.utcnow().isoformat()
        }
    
    async def periodic_scan_task(self):
        """Periodic background scanning"""
        while self.active:
            try:
                await asyncio.sleep(300)  # Scan every 5 minutes
                await self.scan()
            except Exception as e:
                logger.error(f"Periodic scan error: {e}")
                await asyncio.sleep(60)
    
    async def device_cleanup_task(self):
        """Clean up old devices"""
        while self.active:
            try:
                await asyncio.sleep(600)  # Check every 10 minutes
                
                cutoff_time = datetime.utcnow() - timedelta(hours=1)
                devices_to_remove = []
                
                for device_id, device in self.discovered_devices.items():
                    if device.last_seen < cutoff_time:
                        devices_to_remove.append(device_id)
                
                for device_id in devices_to_remove:
                    logger.info(f"Removing stale device: {device_id}")
                    del self.discovered_devices[device_id]
                    
            except Exception as e:
                logger.error(f"Device cleanup error: {e}")
                await asyncio.sleep(300)