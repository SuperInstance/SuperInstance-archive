#!/usr/bin/env python3
"""
ActiveLog.ai Edge Device Discovery Agent

Bluetooth/WiFi device discovery protocol for edge network management.
Scans for nearby devices, maintains registry, provides device interaction API.
"""

import asyncio
import json
import logging
import sqlite3
import subprocess
import time
import socket
import struct
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path

try:
    import bluetooth
    BLUETOOTH_AVAILABLE = True
except ImportError:
    BLUETOOTH_AVAILABLE = False

try:
    import wifi
    from wifi import Cell
    WIFI_AVAILABLE = True
except ImportError:
    WIFI_AVAILABLE = False

@dataclass
class DiscoveredDevice:
    """Device information structure"""
    device_id: str
    device_type: str  # 'bluetooth', 'wifi', 'network', 'activelog'
    name: str
    address: str  # MAC address or IP
    rssi: Optional[int] = None
    services: List[str] = None
    metadata: Dict[str, Any] = None
    last_seen: str = None
    first_discovered: str = None
    is_trusted: bool = False
    activelog_capabilities: List[str] = None

    def __post_init__(self):
        if self.services is None:
            self.services = []
        if self.metadata is None:
            self.metadata = {}
        if self.activelog_capabilities is None:
            self.activelog_capabilities = []
        if self.last_seen is None:
            self.last_seen = datetime.now().isoformat()
        if self.first_discovered is None:
            self.first_discovered = self.last_seen

class DeviceRegistry:
    """SQLite-based device registry"""
    
    def __init__(self, db_path: str = "/tmp/activelog_device_registry.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS devices (
                device_id TEXT PRIMARY KEY,
                device_type TEXT NOT NULL,
                name TEXT NOT NULL,
                address TEXT NOT NULL,
                rssi INTEGER,
                services TEXT,
                metadata TEXT,
                last_seen TEXT NOT NULL,
                first_discovered TEXT NOT NULL,
                is_trusted BOOLEAN DEFAULT FALSE,
                activelog_capabilities TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_device_type ON devices(device_type)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_last_seen ON devices(last_seen)
        ''')
        
        conn.commit()
        conn.close()
    
    def add_or_update_device(self, device: DiscoveredDevice):
        """Add or update device in registry"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if device exists
        cursor.execute('SELECT first_discovered FROM devices WHERE device_id = ?', (device.device_id,))
        existing = cursor.fetchone()
        
        if existing:
            device.first_discovered = existing[0]
        
        cursor.execute('''
            INSERT OR REPLACE INTO devices 
            (device_id, device_type, name, address, rssi, services, metadata, 
             last_seen, first_discovered, is_trusted, activelog_capabilities)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            device.device_id,
            device.device_type,
            device.name,
            device.address,
            device.rssi,
            json.dumps(device.services),
            json.dumps(device.metadata),
            device.last_seen,
            device.first_discovered,
            device.is_trusted,
            json.dumps(device.activelog_capabilities)
        ))
        
        conn.commit()
        conn.close()
    
    def get_device(self, device_id: str) -> Optional[DiscoveredDevice]:
        """Get device by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM devices WHERE device_id = ?', (device_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return DiscoveredDevice(
            device_id=row[0],
            device_type=row[1],
            name=row[2],
            address=row[3],
            rssi=row[4],
            services=json.loads(row[5]) if row[5] else [],
            metadata=json.loads(row[6]) if row[6] else {},
            last_seen=row[7],
            first_discovered=row[8],
            is_trusted=bool(row[9]),
            activelog_capabilities=json.loads(row[10]) if row[10] else []
        )
    
    def get_devices_by_type(self, device_type: str) -> List[DiscoveredDevice]:
        """Get all devices of specific type"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM devices WHERE device_type = ? ORDER BY last_seen DESC', (device_type,))
        rows = cursor.fetchall()
        conn.close()
        
        devices = []
        for row in rows:
            devices.append(DiscoveredDevice(
                device_id=row[0],
                device_type=row[1],
                name=row[2],
                address=row[3],
                rssi=row[4],
                services=json.loads(row[5]) if row[5] else [],
                metadata=json.loads(row[6]) if row[6] else {},
                last_seen=row[7],
                first_discovered=row[8],
                is_trusted=bool(row[9]),
                activelog_capabilities=json.loads(row[10]) if row[10] else []
            ))
        
        return devices
    
    def get_all_devices(self) -> List[DiscoveredDevice]:
        """Get all devices"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM devices ORDER BY last_seen DESC')
        rows = cursor.fetchall()
        conn.close()
        
        devices = []
        for row in rows:
            devices.append(DiscoveredDevice(
                device_id=row[0],
                device_type=row[1],
                name=row[2],
                address=row[3],
                rssi=row[4],
                services=json.loads(row[5]) if row[5] else [],
                metadata=json.loads(row[6]) if row[6] else {},
                last_seen=row[7],
                first_discovered=row[8],
                is_trusted=bool(row[9]),
                activelog_capabilities=json.loads(row[10]) if row[10] else []
            ))
        
        return devices
    
    def cleanup_old_devices(self, max_age_hours: int = 24):
        """Remove devices not seen for specified hours"""
        cutoff_time = (datetime.now() - timedelta(hours=max_age_hours)).isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM devices WHERE last_seen < ? AND is_trusted = FALSE', (cutoff_time,))
        deleted = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        return deleted

class BluetoothScanner:
    """Bluetooth device scanner"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.available = BLUETOOTH_AVAILABLE
        
        if not self.available:
            self.logger.warning("Bluetooth not available - install pybluez: pip install pybluez")
    
    async def scan_devices(self, duration: int = 10) -> List[DiscoveredDevice]:
        """Scan for Bluetooth devices"""
        if not self.available:
            return []
        
        devices = []
        
        try:
            self.logger.info(f"Starting Bluetooth scan for {duration} seconds...")
            
            # Discover nearby devices
            nearby_devices = bluetooth.discover_devices(duration=duration, lookup_names=True)
            
            for addr, name in nearby_devices:
                device_id = f"bt_{addr.replace(':', '_')}"
                
                # Get device services
                services = []
                try:
                    service_matches = bluetooth.find_service(address=addr)
                    services = [s.get('name', 'Unknown') for s in service_matches]
                except Exception as e:
                    self.logger.debug(f"Could not get services for {addr}: {e}")
                
                # Check if it's an ActiveLog device
                activelog_capabilities = []
                if any('activelog' in s.lower() for s in services):
                    activelog_capabilities = await self._probe_activelog_device(addr)
                
                device = DiscoveredDevice(
                    device_id=device_id,
                    device_type='bluetooth',
                    name=name or f"Unknown Bluetooth Device",
                    address=addr,
                    services=services,
                    activelog_capabilities=activelog_capabilities
                )
                
                devices.append(device)
                self.logger.info(f"Found Bluetooth device: {name} ({addr})")
        
        except Exception as e:
            self.logger.error(f"Bluetooth scan failed: {e}")
        
        return devices
    
    async def _probe_activelog_device(self, address: str) -> List[str]:
        """Probe for ActiveLog-specific capabilities"""
        capabilities = []
        
        try:
            # Try to connect to ActiveLog service port
            sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
            sock.settimeout(5)
            
            # Common ActiveLog service port
            sock.connect((address, 1))
            
            # Send capability query
            sock.send(b"ACTIVELOG_QUERY_CAPABILITIES\n")
            response = sock.recv(1024).decode('utf-8').strip()
            
            if response.startswith("ACTIVELOG_CAPS:"):
                capabilities = response.replace("ACTIVELOG_CAPS:", "").split(",")
            
            sock.close()
        
        except Exception:
            pass  # Not an ActiveLog device or connection failed
        
        return capabilities

class WiFiScanner:
    """WiFi device scanner"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.available = WIFI_AVAILABLE
        
        if not self.available:
            self.logger.warning("WiFi scanning not available - install wifi: pip install wifi")
    
    async def scan_networks(self) -> List[DiscoveredDevice]:
        """Scan for WiFi networks and connected devices"""
        devices = []
        
        # Scan WiFi networks
        networks = await self._scan_wifi_networks()
        devices.extend(networks)
        
        # Scan network devices on current subnet
        network_devices = await self._scan_network_devices()
        devices.extend(network_devices)
        
        return devices
    
    async def _scan_wifi_networks(self) -> List[DiscoveredDevice]:
        """Scan for WiFi access points"""
        if not self.available:
            return []
        
        devices = []
        
        try:
            self.logger.info("Scanning WiFi networks...")
            
            # Get available cells
            cells = list(Cell.all('wlan0'))
            
            for cell in cells:
                device_id = f"wifi_{cell.ssid.replace(' ', '_')}"
                
                device = DiscoveredDevice(
                    device_id=device_id,
                    device_type='wifi',
                    name=cell.ssid,
                    address=cell.address,
                    rssi=cell.signal,
                    metadata={
                        'encryption': cell.encryption_type,
                        'frequency': cell.frequency,
                        'channel': cell.channel
                    }
                )
                
                devices.append(device)
                self.logger.info(f"Found WiFi network: {cell.ssid} ({cell.signal}dBm)")
        
        except Exception as e:
            self.logger.error(f"WiFi scan failed: {e}")
            
            # Fallback using iwlist
            try:
                result = subprocess.run(['iwlist', 'wlan0', 'scan'], 
                                      capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    devices.extend(self._parse_iwlist_output(result.stdout))
            except Exception as e2:
                self.logger.error(f"Fallback WiFi scan failed: {e2}")
        
        return devices
    
    async def _scan_network_devices(self) -> List[DiscoveredDevice]:
        """Scan for devices on current network subnet"""
        devices = []
        
        try:
            # Get current network info
            network_info = self._get_network_info()
            if not network_info:
                return devices
            
            self.logger.info(f"Scanning network devices on {network_info['network']}")
            
            # Use nmap if available
            try:
                result = subprocess.run(['nmap', '-sn', network_info['network']], 
                                      capture_output=True, text=True, timeout=60)
                if result.returncode == 0:
                    devices.extend(self._parse_nmap_output(result.stdout))
            except FileNotFoundError:
                # Fallback using ping sweep
                devices.extend(await self._ping_sweep(network_info))
            
        except Exception as e:
            self.logger.error(f"Network device scan failed: {e}")
        
        return devices
    
    def _get_network_info(self) -> Optional[Dict[str, str]]:
        """Get current network information"""
        try:
            # Get default route
            result = subprocess.run(['ip', 'route', 'show', 'default'], 
                                  capture_output=True, text=True)
            if result.returncode != 0:
                return None
            
            # Parse default gateway
            gateway = None
            interface = None
            for line in result.stdout.split('\n'):
                if 'default via' in line:
                    parts = line.split()
                    if len(parts) >= 5:
                        gateway = parts[2]
                        interface = parts[4]
                    break
            
            if not gateway or not interface:
                return None
            
            # Get interface IP
            result = subprocess.run(['ip', 'addr', 'show', interface], 
                                  capture_output=True, text=True)
            if result.returncode != 0:
                return None
            
            # Parse IP and subnet
            for line in result.stdout.split('\n'):
                if 'inet ' in line and 'scope global' in line:
                    parts = line.strip().split()
                    for part in parts:
                        if '/' in part and '.' in part:
                            ip_cidr = part
                            ip, cidr = ip_cidr.split('/')
                            
                            # Calculate network
                            ip_int = struct.unpack("!I", socket.inet_aton(ip))[0]
                            mask = (0xffffffff >> (32 - int(cidr))) << (32 - int(cidr))
                            network_int = ip_int & mask
                            network_ip = socket.inet_ntoa(struct.pack("!I", network_int))
                            
                            return {
                                'ip': ip,
                                'gateway': gateway,
                                'network': f"{network_ip}/{cidr}",
                                'interface': interface
                            }
        
        except Exception as e:
            self.logger.error(f"Failed to get network info: {e}")
        
        return None
    
    async def _ping_sweep(self, network_info: Dict[str, str]) -> List[DiscoveredDevice]:
        """Perform ping sweep to find active hosts"""
        devices = []
        
        try:
            # Parse network
            network, cidr = network_info['network'].split('/')
            network_int = struct.unpack("!I", socket.inet_aton(network))[0]
            
            # Calculate host range
            host_bits = 32 - int(cidr)
            max_hosts = (2 ** host_bits) - 2  # Exclude network and broadcast
            
            # Limit scan to reasonable range
            max_hosts = min(max_hosts, 254)
            
            tasks = []
            for i in range(1, max_hosts + 1):
                host_ip = socket.inet_ntoa(struct.pack("!I", network_int + i))
                tasks.append(self._ping_host(host_ip))
            
            # Run ping tasks concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, DiscoveredDevice):
                    devices.append(result)
        
        except Exception as e:
            self.logger.error(f"Ping sweep failed: {e}")
        
        return devices
    
    async def _ping_host(self, ip: str) -> Optional[DiscoveredDevice]:
        """Ping single host and create device entry if responsive"""
        try:
            result = await asyncio.create_subprocess_exec(
                'ping', '-c', '1', '-W', '1', ip,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await result.wait()
            
            if result.returncode == 0:
                # Host is alive, try to get hostname
                hostname = ip
                try:
                    hostname = socket.gethostbyaddr(ip)[0]
                except:
                    pass
                
                device_id = f"net_{ip.replace('.', '_')}"
                
                # Check if it's an ActiveLog device
                activelog_capabilities = await self._probe_activelog_network_device(ip)
                
                device = DiscoveredDevice(
                    device_id=device_id,
                    device_type='network' if not activelog_capabilities else 'activelog',
                    name=hostname,
                    address=ip,
                    activelog_capabilities=activelog_capabilities
                )
                
                return device
        
        except Exception:
            pass
        
        return None
    
    async def _probe_activelog_network_device(self, ip: str) -> List[str]:
        """Probe network device for ActiveLog capabilities"""
        capabilities = []
        
        # Common ActiveLog service ports
        activelog_ports = [8080, 8443, 9001, 3000]
        
        for port in activelog_ports:
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(ip, port), timeout=2
                )
                
                # Send HTTP request for capabilities
                request = f"GET /activelog/capabilities HTTP/1.1\r\nHost: {ip}\r\n\r\n"
                writer.write(request.encode())
                await writer.drain()
                
                response = await asyncio.wait_for(reader.read(1024), timeout=2)
                response_str = response.decode('utf-8', errors='ignore')
                
                writer.close()
                await writer.wait_closed()
                
                # Parse capabilities from response
                if 'activelog-capabilities:' in response_str.lower():
                    for line in response_str.split('\n'):
                        if 'activelog-capabilities:' in line.lower():
                            caps = line.split(':', 1)[1].strip().split(',')
                            capabilities.extend([cap.strip() for cap in caps])
                            break
                
                # If we found capabilities, no need to check other ports
                if capabilities:
                    break
            
            except Exception:
                continue
        
        return capabilities
    
    def _parse_iwlist_output(self, output: str) -> List[DiscoveredDevice]:
        """Parse iwlist scan output"""
        devices = []
        
        try:
            current_cell = {}
            
            for line in output.split('\n'):
                line = line.strip()
                
                if 'Cell ' in line and 'Address: ' in line:
                    # Save previous cell
                    if current_cell:
                        devices.append(self._create_wifi_device(current_cell))
                    
                    # Start new cell
                    current_cell = {}
                    addr_part = line.split('Address: ')[1]
                    current_cell['address'] = addr_part.strip()
                
                elif 'ESSID:' in line:
                    essid = line.split('ESSID:')[1].strip().strip('"')
                    current_cell['ssid'] = essid
                
                elif 'Signal level=' in line:
                    signal_part = line.split('Signal level=')[1].split()[0]
                    try:
                        current_cell['signal'] = int(signal_part)
                    except:
                        pass
                
                elif 'Encryption key:' in line:
                    if 'on' in line:
                        current_cell['encrypted'] = True
            
            # Save last cell
            if current_cell:
                devices.append(self._create_wifi_device(current_cell))
        
        except Exception as e:
            self.logger.error(f"Failed to parse iwlist output: {e}")
        
        return devices
    
    def _create_wifi_device(self, cell_data: Dict) -> DiscoveredDevice:
        """Create DiscoveredDevice from cell data"""
        ssid = cell_data.get('ssid', 'Hidden Network')
        device_id = f"wifi_{ssid.replace(' ', '_')}"
        
        return DiscoveredDevice(
            device_id=device_id,
            device_type='wifi',
            name=ssid,
            address=cell_data.get('address', ''),
            rssi=cell_data.get('signal'),
            metadata={
                'encrypted': cell_data.get('encrypted', False)
            }
        )
    
    def _parse_nmap_output(self, output: str) -> List[DiscoveredDevice]:
        """Parse nmap scan output"""
        devices = []
        
        try:
            lines = output.split('\n')
            current_host = None
            
            for line in lines:
                line = line.strip()
                
                if line.startswith('Nmap scan report for '):
                    # Extract hostname and IP
                    host_info = line.replace('Nmap scan report for ', '')
                    
                    if '(' in host_info and ')' in host_info:
                        # Format: hostname (ip)
                        hostname = host_info.split('(')[0].strip()
                        ip = host_info.split('(')[1].split(')')[0]
                    else:
                        # Format: ip
                        hostname = host_info
                        ip = host_info
                    
                    current_host = {'hostname': hostname, 'ip': ip}
                
                elif line.startswith('Host is up') and current_host:
                    # Host is responsive
                    device_id = f"net_{current_host['ip'].replace('.', '_')}"
                    
                    device = DiscoveredDevice(
                        device_id=device_id,
                        device_type='network',
                        name=current_host['hostname'],
                        address=current_host['ip']
                    )
                    
                    devices.append(device)
                    current_host = None
        
        except Exception as e:
            self.logger.error(f"Failed to parse nmap output: {e}")
        
        return devices

class DeviceDiscoveryAgent:
    """Main device discovery agent"""
    
    def __init__(self, config_file: str = "/etc/activelog/discovery.json"):
        self.config_file = config_file
        self.config = self._load_config()
        self.registry = DeviceRegistry(self.config['registry_db_path'])
        self.bluetooth_scanner = BluetoothScanner()
        self.wifi_scanner = WiFiScanner()
        
        # Setup logging
        logging.basicConfig(
            level=getattr(logging, self.config['log_level']),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.config['log_file']),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        self.running = False
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file"""
        default_config = {
            'scan_interval': 60,
            'bluetooth_scan_duration': 10,
            'cleanup_interval': 3600,
            'max_device_age_hours': 24,
            'registry_db_path': '/tmp/activelog_device_registry.db',
            'log_file': '/tmp/activelog_discovery.log',
            'log_level': 'INFO',
            'enable_bluetooth': True,
            'enable_wifi': True,
            'enable_network_scan': True,
            'trusted_device_patterns': ['activelog-*', 'pi-*'],
            'api_port': 8765
        }
        
        try:
            if Path(self.config_file).exists():
                with open(self.config_file, 'r') as f:
                    file_config = json.load(f)
                default_config.update(file_config)
        except Exception as e:
            print(f"Failed to load config from {self.config_file}: {e}")
        
        return default_config
    
    async def start_discovery(self):
        """Start the discovery process"""
        self.running = True
        self.logger.info("Starting device discovery agent...")
        
        # Start background tasks
        tasks = [
            asyncio.create_task(self._discovery_loop()),
            asyncio.create_task(self._cleanup_loop()),
            asyncio.create_task(self._start_api_server())
        ]
        
        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            self.logger.info("Received interrupt signal")
        finally:
            self.running = False
            self.logger.info("Device discovery agent stopped")
    
    async def _discovery_loop(self):
        """Main discovery loop"""
        while self.running:
            try:
                self.logger.info("Starting device discovery scan...")
                
                all_devices = []
                
                # Bluetooth scan
                if self.config['enable_bluetooth']:
                    bluetooth_devices = await self.bluetooth_scanner.scan_devices(
                        duration=self.config['bluetooth_scan_duration']
                    )
                    all_devices.extend(bluetooth_devices)
                
                # WiFi and network scan
                if self.config['enable_wifi'] or self.config['enable_network_scan']:
                    network_devices = await self.wifi_scanner.scan_networks()
                    all_devices.extend(network_devices)
                
                # Update registry
                for device in all_devices:
                    # Check if device should be trusted
                    device.is_trusted = self._is_trusted_device(device)
                    
                    self.registry.add_or_update_device(device)
                    
                    if device.activelog_capabilities:
                        self.logger.info(f"Found ActiveLog device: {device.name} with capabilities: {device.activelog_capabilities}")
                    else:
                        self.logger.debug(f"Updated device: {device.name} ({device.device_type})")
                
                self.logger.info(f"Discovery scan completed - found {len(all_devices)} devices")
                
            except Exception as e:
                self.logger.error(f"Discovery scan failed: {e}")
            
            # Wait for next scan
            await asyncio.sleep(self.config['scan_interval'])
    
    async def _cleanup_loop(self):
        """Cleanup old devices periodically"""
        while self.running:
            try:
                await asyncio.sleep(self.config['cleanup_interval'])
                
                deleted = self.registry.cleanup_old_devices(
                    self.config['max_device_age_hours']
                )
                
                if deleted > 0:
                    self.logger.info(f"Cleaned up {deleted} old devices")
            
            except Exception as e:
                self.logger.error(f"Cleanup failed: {e}")
    
    async def _start_api_server(self):
        """Start HTTP API server for device queries"""
        from http.server import HTTPServer, BaseHTTPRequestHandler
        import threading
        
        class DeviceAPIHandler(BaseHTTPRequestHandler):
            def __init__(self, discovery_agent, *args, **kwargs):
                self.discovery_agent = discovery_agent
                super().__init__(*args, **kwargs)
            
            def do_GET(self):
                if self.path == '/devices':
                    devices = self.discovery_agent.registry.get_all_devices()
                    response = json.dumps([asdict(d) for d in devices], indent=2)
                    
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Content-Length', str(len(response)))
                    self.end_headers()
                    self.wfile.write(response.encode())
                
                elif self.path.startswith('/devices/'):
                    device_id = self.path.split('/')[2]
                    device = self.discovery_agent.registry.get_device(device_id)
                    
                    if device:
                        response = json.dumps(asdict(device), indent=2)
                        self.send_response(200)
                    else:
                        response = json.dumps({'error': 'Device not found'})
                        self.send_response(404)
                    
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Content-Length', str(len(response)))
                    self.end_headers()
                    self.wfile.write(response.encode())
                
                else:
                    self.send_response(404)
                    self.end_headers()
            
            def log_message(self, format, *args):
                pass  # Suppress HTTP server logs
        
        # Create handler with discovery agent reference
        handler = lambda *args, **kwargs: DeviceAPIHandler(self, *args, **kwargs)
        
        # Start HTTP server in thread
        def run_server():
            server = HTTPServer(('0.0.0.0', self.config['api_port']), handler)
            self.logger.info(f"API server started on port {self.config['api_port']}")
            
            while self.running:
                try:
                    server.timeout = 1
                    server.handle_request()
                except Exception as e:
                    if self.running:
                        self.logger.error(f"API server error: {e}")
        
        # Run server in background thread
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        
        # Keep this coroutine alive
        while self.running:
            await asyncio.sleep(1)
    
    def _is_trusted_device(self, device: DiscoveredDevice) -> bool:
        """Check if device matches trusted patterns"""
        for pattern in self.config['trusted_device_patterns']:
            if pattern.endswith('*'):
                prefix = pattern[:-1]
                if device.name.lower().startswith(prefix.lower()):
                    return True
            elif pattern.startswith('*'):
                suffix = pattern[1:]
                if device.name.lower().endswith(suffix.lower()):
                    return True
            elif pattern.lower() == device.name.lower():
                return True
        
        # Trust devices with ActiveLog capabilities
        if device.activelog_capabilities:
            return True
        
        return False
    
    async def get_devices(self, device_type: str = None) -> List[DiscoveredDevice]:
        """Get devices from registry"""
        if device_type:
            return self.registry.get_devices_by_type(device_type)
        return self.registry.get_all_devices()
    
    async def get_device(self, device_id: str) -> Optional[DiscoveredDevice]:
        """Get specific device"""
        return self.registry.get_device(device_id)
    
    async def trust_device(self, device_id: str):
        """Mark device as trusted"""
        device = self.registry.get_device(device_id)
        if device:
            device.is_trusted = True
            self.registry.add_or_update_device(device)
            return True
        return False
    
    async def untrust_device(self, device_id: str):
        """Remove device from trusted list"""
        device = self.registry.get_device(device_id)
        if device:
            device.is_trusted = False
            self.registry.add_or_update_device(device)
            return True
        return False

async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='ActiveLog Device Discovery Agent')
    parser.add_argument('--config', default='/etc/activelog/discovery.json',
                       help='Configuration file path')
    parser.add_argument('--daemon', action='store_true',
                       help='Run as daemon')
    args = parser.parse_args()
    
    agent = DeviceDiscoveryAgent(args.config)
    
    if args.daemon:
        # Fork to background
        import os
        import sys
        
        pid = os.fork()
        if pid > 0:
            # Parent process
            print(f"Started device discovery daemon with PID: {pid}")
            sys.exit(0)
        
        # Child process
        os.setsid()
        os.chdir('/')
    
    await agent.start_discovery()

if __name__ == '__main__':
    asyncio.run(main())