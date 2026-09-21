#!/usr/bin/env python3
"""
ActiveLog.ai Edge Device Management Dashboard

Web-based dashboard for monitoring and managing edge devices.
Provides real-time device status, configuration, and control capabilities.
"""

import asyncio
import json
import logging
import sqlite3
import time
import psutil
import os
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path
import threading
import requests
from urllib.parse import urlparse

# Web framework
try:
    from flask import Flask, render_template, jsonify, request, websocket
    from flask_socketio import SocketIO, emit
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False

@dataclass
class EdgeDevice:
    """Edge device information"""
    device_id: str
    device_type: str  # 'raspberry-pi', 'jetson-nano', 'camera', 'generic'
    name: str
    ip_address: str
    mac_address: str
    status: str  # 'online', 'offline', 'error', 'maintenance'
    last_heartbeat: str
    version: str
    capabilities: List[str]
    metrics: Dict[str, Any]
    configuration: Dict[str, Any]
    location: Optional[str] = None
    group: Optional[str] = None

    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = []
        if self.metrics is None:
            self.metrics = {}
        if self.configuration is None:
            self.configuration = {}

@dataclass
class DeviceMetrics:
    """Device performance metrics"""
    device_id: str
    timestamp: str
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    temperature: Optional[float] = None
    network_rx: int = 0
    network_tx: int = 0
    uptime: int = 0
    load_average: float = 0.0
    custom_metrics: Dict[str, Any] = None

    def __post_init__(self):
        if self.custom_metrics is None:
            self.custom_metrics = {}

class DeviceDatabase:
    """SQLite database for device management"""
    
    def __init__(self, db_path: str = "/tmp/activelog_edge_dashboard.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Devices table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS devices (
                device_id TEXT PRIMARY KEY,
                device_type TEXT NOT NULL,
                name TEXT NOT NULL,
                ip_address TEXT NOT NULL,
                mac_address TEXT,
                status TEXT NOT NULL,
                last_heartbeat TEXT NOT NULL,
                version TEXT,
                capabilities TEXT,
                configuration TEXT,
                location TEXT,
                group_name TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        ''')
        
        # Metrics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS device_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                cpu_usage REAL,
                memory_usage REAL,
                disk_usage REAL,
                temperature REAL,
                network_rx INTEGER,
                network_tx INTEGER,
                uptime INTEGER,
                load_average REAL,
                custom_metrics TEXT,
                FOREIGN KEY (device_id) REFERENCES devices (device_id)
            )
        ''')
        
        # Events table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS device_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                event_data TEXT,
                timestamp TEXT NOT NULL,
                severity TEXT DEFAULT 'info',
                FOREIGN KEY (device_id) REFERENCES devices (device_id)
            )
        ''')
        
        # Commands table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS device_commands (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                command TEXT NOT NULL,
                parameters TEXT,
                status TEXT DEFAULT 'pending',
                result TEXT,
                created_at TEXT NOT NULL,
                executed_at TEXT,
                FOREIGN KEY (device_id) REFERENCES devices (device_id)
            )
        ''')
        
        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_device_status ON devices(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_metrics_device_time ON device_metrics(device_id, timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_events_device_time ON device_events(device_id, timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_commands_status ON device_commands(status)')
        
        conn.commit()
        conn.close()
    
    def add_or_update_device(self, device: EdgeDevice):
        """Add or update device"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        
        # Check if device exists
        cursor.execute('SELECT created_at FROM devices WHERE device_id = ?', (device.device_id,))
        existing = cursor.fetchone()
        created_at = existing[0] if existing else now
        
        cursor.execute('''
            INSERT OR REPLACE INTO devices 
            (device_id, device_type, name, ip_address, mac_address, status, 
             last_heartbeat, version, capabilities, configuration, location, 
             group_name, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            device.device_id, device.device_type, device.name, device.ip_address,
            device.mac_address, device.status, device.last_heartbeat, device.version,
            json.dumps(device.capabilities), json.dumps(device.configuration),
            device.location, device.group, created_at, now
        ))
        
        conn.commit()
        conn.close()
    
    def get_device(self, device_id: str) -> Optional[EdgeDevice]:
        """Get device by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM devices WHERE device_id = ?', (device_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return EdgeDevice(
            device_id=row[0], device_type=row[1], name=row[2], ip_address=row[3],
            mac_address=row[4], status=row[5], last_heartbeat=row[6], version=row[7],
            capabilities=json.loads(row[8]) if row[8] else [],
            configuration=json.loads(row[9]) if row[9] else {},
            location=row[10], group=row[11]
        )
    
    def get_all_devices(self) -> List[EdgeDevice]:
        """Get all devices"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM devices ORDER BY name')
        rows = cursor.fetchall()
        conn.close()
        
        devices = []
        for row in rows:
            devices.append(EdgeDevice(
                device_id=row[0], device_type=row[1], name=row[2], ip_address=row[3],
                mac_address=row[4], status=row[5], last_heartbeat=row[6], version=row[7],
                capabilities=json.loads(row[8]) if row[8] else [],
                configuration=json.loads(row[9]) if row[9] else {},
                location=row[10], group=row[11]
            ))
        
        return devices
    
    def add_metrics(self, metrics: DeviceMetrics):
        """Add device metrics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO device_metrics 
            (device_id, timestamp, cpu_usage, memory_usage, disk_usage, 
             temperature, network_rx, network_tx, uptime, load_average, custom_metrics)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            metrics.device_id, metrics.timestamp, metrics.cpu_usage,
            metrics.memory_usage, metrics.disk_usage, metrics.temperature,
            metrics.network_rx, metrics.network_tx, metrics.uptime,
            metrics.load_average, json.dumps(metrics.custom_metrics)
        ))
        
        conn.commit()
        conn.close()
    
    def get_device_metrics(self, device_id: str, hours: int = 24) -> List[DeviceMetrics]:
        """Get device metrics for specified time period"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff_time = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        cursor.execute('''
            SELECT * FROM device_metrics 
            WHERE device_id = ? AND timestamp > ?
            ORDER BY timestamp DESC
        ''', (device_id, cutoff_time))
        
        rows = cursor.fetchall()
        conn.close()
        
        metrics = []
        for row in rows:
            metrics.append(DeviceMetrics(
                device_id=row[1], timestamp=row[2], cpu_usage=row[3],
                memory_usage=row[4], disk_usage=row[5], temperature=row[6],
                network_rx=row[7], network_tx=row[8], uptime=row[9],
                load_average=row[10], custom_metrics=json.loads(row[11]) if row[11] else {}
            ))
        
        return metrics
    
    def add_event(self, device_id: str, event_type: str, event_data: Dict[str, Any], severity: str = 'info'):
        """Add device event"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO device_events (device_id, event_type, event_data, timestamp, severity)
            VALUES (?, ?, ?, ?, ?)
        ''', (device_id, event_type, json.dumps(event_data), datetime.now().isoformat(), severity))
        
        conn.commit()
        conn.close()
    
    def get_device_events(self, device_id: str = None, hours: int = 24) -> List[Dict[str, Any]]:
        """Get device events"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff_time = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        if device_id:
            cursor.execute('''
                SELECT * FROM device_events 
                WHERE device_id = ? AND timestamp > ?
                ORDER BY timestamp DESC
            ''', (device_id, cutoff_time))
        else:
            cursor.execute('''
                SELECT * FROM device_events 
                WHERE timestamp > ?
                ORDER BY timestamp DESC
            ''', (cutoff_time,))
        
        rows = cursor.fetchall()
        conn.close()
        
        events = []
        for row in rows:
            events.append({
                'id': row[0],
                'device_id': row[1],
                'event_type': row[2],
                'event_data': json.loads(row[3]) if row[3] else {},
                'timestamp': row[4],
                'severity': row[5]
            })
        
        return events
    
    def add_command(self, device_id: str, command: str, parameters: Dict[str, Any] = None):
        """Add command for device execution"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO device_commands (device_id, command, parameters, created_at)
            VALUES (?, ?, ?, ?)
        ''', (device_id, command, json.dumps(parameters or {}), datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
        return cursor.lastrowid

class DeviceManager:
    """Device discovery and management"""
    
    def __init__(self, database: DeviceDatabase):
        self.database = database
        self.logger = logging.getLogger(__name__)
        self.discovery_sources = []
        
        # Try to connect to discovery service
        self._setup_discovery_sources()
    
    def _setup_discovery_sources(self):
        """Setup device discovery sources"""
        # ActiveLog Discovery Service
        try:
            response = requests.get('http://localhost:8765/devices', timeout=5)
            if response.status_code == 200:
                self.discovery_sources.append('http://localhost:8765')
                self.logger.info("Connected to ActiveLog Discovery Service")
        except:
            self.logger.warning("ActiveLog Discovery Service not available")
        
        # Add other discovery sources here
        # - mDNS/Bonjour
        # - SSDP
        # - Custom protocols
    
    async def discover_devices(self):
        """Discover and register edge devices"""
        discovered_devices = []
        
        # Discover from ActiveLog Discovery Service
        for source in self.discovery_sources:
            try:
                response = requests.get(f'{source}/devices', timeout=10)
                if response.status_code == 200:
                    devices_data = response.json()
                    
                    for device_data in devices_data:
                        if device_data.get('activelog_capabilities'):
                            # This is an ActiveLog edge device
                            edge_device = await self._create_edge_device_from_discovery(device_data)
                            if edge_device:
                                discovered_devices.append(edge_device)
                                self.database.add_or_update_device(edge_device)
            
            except Exception as e:
                self.logger.error(f"Failed to discover from {source}: {e}")
        
        # Discover devices by probing known ActiveLog ports
        await self._probe_network_for_edge_devices()
        
        return discovered_devices
    
    async def _create_edge_device_from_discovery(self, device_data: Dict[str, Any]) -> Optional[EdgeDevice]:
        """Create EdgeDevice from discovery service data"""
        try:
            # Determine device type from capabilities
            capabilities = device_data.get('activelog_capabilities', [])
            device_type = 'generic'
            
            if 'raspberry-pi' in capabilities:
                device_type = 'raspberry-pi'
            elif 'jetson-nano' in capabilities:
                device_type = 'jetson-nano'
            elif 'camera' in capabilities:
                device_type = 'camera'
            
            # Probe device for more information
            device_info = await self._probe_activelog_device(device_data['address'])
            
            return EdgeDevice(
                device_id=device_data['device_id'],
                device_type=device_type,
                name=device_data['name'],
                ip_address=device_data['address'],
                mac_address=device_data.get('metadata', {}).get('mac_address', ''),
                status='online',
                last_heartbeat=datetime.now().isoformat(),
                version=device_info.get('version', 'unknown'),
                capabilities=capabilities,
                configuration=device_info.get('configuration', {}),
                location=device_info.get('location'),
                group=device_info.get('group')
            )
        
        except Exception as e:
            self.logger.error(f"Failed to create edge device: {e}")
            return None
    
    async def _probe_activelog_device(self, ip_address: str) -> Dict[str, Any]:
        """Probe ActiveLog device for detailed information"""
        device_info = {}
        
        # Common ActiveLog service ports
        ports = [8080, 8443, 9001, 3000]
        
        for port in ports:
            try:
                url = f"http://{ip_address}:{port}/activelog/info"
                response = requests.get(url, timeout=5)
                
                if response.status_code == 200:
                    device_info = response.json()
                    break
            
            except:
                continue
        
        return device_info
    
    async def _probe_network_for_edge_devices(self):
        """Probe network for ActiveLog edge devices"""
        # Get current network
        try:
            result = subprocess.run(['ip', 'route', 'show', 'default'], 
                                  capture_output=True, text=True)
            # Parse network and scan for devices
            # This is a simplified version - full implementation would scan subnet
            pass
        except:
            pass
    
    async def update_device_status(self):
        """Update status of all registered devices"""
        devices = self.database.get_all_devices()
        
        for device in devices:
            try:
                # Ping device to check if it's online
                result = subprocess.run(['ping', '-c', '1', '-W', '2', device.ip_address],
                                      capture_output=True)
                
                if result.returncode == 0:
                    # Device is reachable, try to get detailed status
                    device_status = await self._get_device_detailed_status(device)
                    
                    if device_status:
                        device.status = device_status.get('status', 'online')
                        device.last_heartbeat = datetime.now().isoformat()
                        device.metrics = device_status.get('metrics', {})
                        
                        # Add metrics to database
                        if 'metrics' in device_status:
                            metrics = DeviceMetrics(
                                device_id=device.device_id,
                                timestamp=datetime.now().isoformat(),
                                **device_status['metrics']
                            )
                            self.database.add_metrics(metrics)
                    else:
                        device.status = 'online'
                        device.last_heartbeat = datetime.now().isoformat()
                else:
                    device.status = 'offline'
                
                self.database.add_or_update_device(device)
            
            except Exception as e:
                self.logger.error(f"Failed to update status for {device.device_id}: {e}")
                device.status = 'error'
                self.database.add_or_update_device(device)
    
    async def _get_device_detailed_status(self, device: EdgeDevice) -> Optional[Dict[str, Any]]:
        """Get detailed status from device"""
        ports = [8080, 8443, 9001, 3000]
        
        for port in ports:
            try:
                url = f"http://{device.ip_address}:{port}/activelog/status"
                response = requests.get(url, timeout=5)
                
                if response.status_code == 200:
                    return response.json()
            
            except:
                continue
        
        return None

class DashboardWebApp:
    """Flask web application for dashboard"""
    
    def __init__(self, database: DeviceDatabase, device_manager: DeviceManager):
        if not FLASK_AVAILABLE:
            raise ImportError("Flask not available - install with: pip install flask flask-socketio")
        
        self.database = database
        self.device_manager = device_manager
        self.app = Flask(__name__, template_folder='templates', static_folder='static')
        self.app.secret_key = 'activelog-dashboard-' + os.urandom(16).hex()
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")
        
        self._setup_routes()
        self._setup_websocket_events()
    
    def _setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/')
        def dashboard():
            return render_template('dashboard.html')
        
        @self.app.route('/api/devices')
        def api_devices():
            devices = self.database.get_all_devices()
            return jsonify([asdict(device) for device in devices])
        
        @self.app.route('/api/devices/<device_id>')
        def api_device_detail(device_id):
            device = self.database.get_device(device_id)
            if not device:
                return jsonify({'error': 'Device not found'}), 404
            
            # Get recent metrics
            metrics = self.database.get_device_metrics(device_id, hours=24)
            events = self.database.get_device_events(device_id, hours=24)
            
            return jsonify({
                'device': asdict(device),
                'metrics': [asdict(m) for m in metrics],
                'events': events
            })
        
        @self.app.route('/api/devices/<device_id>/metrics')
        def api_device_metrics(device_id):
            hours = int(request.args.get('hours', 24))
            metrics = self.database.get_device_metrics(device_id, hours)
            return jsonify([asdict(m) for m in metrics])
        
        @self.app.route('/api/devices/<device_id>/command', methods=['POST'])
        def api_device_command(device_id):
            data = request.get_json()
            command = data.get('command')
            parameters = data.get('parameters', {})
            
            if not command:
                return jsonify({'error': 'Command required'}), 400
            
            command_id = self.database.add_command(device_id, command, parameters)
            
            # TODO: Actually send command to device
            
            return jsonify({'command_id': command_id, 'status': 'sent'})
        
        @self.app.route('/api/events')
        def api_events():
            hours = int(request.args.get('hours', 24))
            events = self.database.get_device_events(hours=hours)
            return jsonify(events)
        
        @self.app.route('/api/stats')
        def api_stats():
            devices = self.database.get_all_devices()
            
            stats = {
                'total_devices': len(devices),
                'online_devices': len([d for d in devices if d.status == 'online']),
                'offline_devices': len([d for d in devices if d.status == 'offline']),
                'device_types': {},
                'groups': {}
            }
            
            for device in devices:
                # Count by type
                if device.device_type not in stats['device_types']:
                    stats['device_types'][device.device_type] = 0
                stats['device_types'][device.device_type] += 1
                
                # Count by group
                group = device.group or 'default'
                if group not in stats['groups']:
                    stats['groups'][group] = 0
                stats['groups'][group] += 1
            
            return jsonify(stats)
    
    def _setup_websocket_events(self):
        """Setup WebSocket events"""
        
        @self.socketio.on('connect')
        def handle_connect():
            print('Client connected')
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            print('Client disconnected')
        
        @self.socketio.on('subscribe_device')
        def handle_subscribe_device(data):
            device_id = data.get('device_id')
            if device_id:
                # Join device-specific room for real-time updates
                from flask_socketio import join_room
                join_room(f'device_{device_id}')
    
    def emit_device_update(self, device: EdgeDevice):
        """Emit device update to connected clients"""
        self.socketio.emit('device_update', asdict(device), room=f'device_{device.device_id}')
    
    def emit_metrics_update(self, metrics: DeviceMetrics):
        """Emit metrics update to connected clients"""
        self.socketio.emit('metrics_update', asdict(metrics), room=f'device_{metrics.device_id}')
    
    def run(self, host='0.0.0.0', port=5000, debug=False):
        """Run the web application"""
        self.socketio.run(self.app, host=host, port=port, debug=debug)

class EdgeDashboard:
    """Main dashboard controller"""
    
    def __init__(self, config_file: str = "/etc/activelog/dashboard.json"):
        self.config = self._load_config(config_file)
        self.database = DeviceDatabase(self.config['database_path'])
        self.device_manager = DeviceManager(self.database)
        
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
        
        # Setup web app
        if FLASK_AVAILABLE:
            self.web_app = DashboardWebApp(self.database, self.device_manager)
        else:
            self.web_app = None
            self.logger.warning("Flask not available - web interface disabled")
        
        self.running = False
    
    def _load_config(self, config_file: str) -> Dict[str, Any]:
        """Load configuration"""
        default_config = {
            'database_path': '/tmp/activelog_edge_dashboard.db',
            'log_file': '/var/log/activelog/dashboard.log',
            'log_level': 'INFO',
            'web_port': 5000,
            'web_host': '0.0.0.0',
            'discovery_interval': 300,
            'status_update_interval': 60,
            'metrics_retention_days': 30
        }
        
        try:
            if Path(config_file).exists():
                with open(config_file, 'r') as f:
                    file_config = json.load(f)
                default_config.update(file_config)
        except Exception as e:
            print(f"Failed to load config: {e}")
        
        return default_config
    
    async def start(self):
        """Start the dashboard"""
        self.running = True
        self.logger.info("Starting Edge Device Management Dashboard...")
        
        # Start background tasks
        tasks = []
        
        # Device discovery task
        tasks.append(asyncio.create_task(self._discovery_loop()))
        
        # Status update task
        tasks.append(asyncio.create_task(self._status_update_loop()))
        
        # Metrics cleanup task
        tasks.append(asyncio.create_task(self._cleanup_loop()))
        
        # Web interface task
        if self.web_app:
            tasks.append(asyncio.create_task(self._run_web_interface()))
        
        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            self.logger.info("Received interrupt signal")
        finally:
            self.running = False
            self.logger.info("Dashboard stopped")
    
    async def _discovery_loop(self):
        """Device discovery loop"""
        while self.running:
            try:
                self.logger.info("Running device discovery...")
                devices = await self.device_manager.discover_devices()
                self.logger.info(f"Discovered {len(devices)} devices")
                
                # Emit updates to web clients
                if self.web_app:
                    for device in devices:
                        self.web_app.emit_device_update(device)
                
            except Exception as e:
                self.logger.error(f"Discovery failed: {e}")
            
            await asyncio.sleep(self.config['discovery_interval'])
    
    async def _status_update_loop(self):
        """Device status update loop"""
        while self.running:
            try:
                await self.device_manager.update_device_status()
                
            except Exception as e:
                self.logger.error(f"Status update failed: {e}")
            
            await asyncio.sleep(self.config['status_update_interval'])
    
    async def _cleanup_loop(self):
        """Cleanup old data"""
        while self.running:
            try:
                # Sleep for 1 hour between cleanups
                await asyncio.sleep(3600)
                
                # Clean up old metrics
                cutoff_date = (datetime.now() - timedelta(days=self.config['metrics_retention_days'])).isoformat()
                
                conn = sqlite3.connect(self.database.db_path)
                cursor = conn.cursor()
                
                cursor.execute('DELETE FROM device_metrics WHERE timestamp < ?', (cutoff_date,))
                deleted_metrics = cursor.rowcount
                
                cursor.execute('DELETE FROM device_events WHERE timestamp < ?', (cutoff_date,))
                deleted_events = cursor.rowcount
                
                conn.commit()
                conn.close()
                
                if deleted_metrics > 0 or deleted_events > 0:
                    self.logger.info(f"Cleaned up {deleted_metrics} metrics and {deleted_events} events")
                
            except Exception as e:
                self.logger.error(f"Cleanup failed: {e}")
    
    async def _run_web_interface(self):
        """Run web interface in background"""
        if not self.web_app:
            return
        
        # Run Flask app in a separate thread
        def run_flask():
            self.web_app.run(
                host=self.config['web_host'],
                port=self.config['web_port'],
                debug=False
            )
        
        web_thread = threading.Thread(target=run_flask, daemon=True)
        web_thread.start()
        
        # Keep this coroutine alive
        while self.running:
            await asyncio.sleep(1)

async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='ActiveLog Edge Device Management Dashboard')
    parser.add_argument('--config', default='/etc/activelog/dashboard.json',
                       help='Configuration file path')
    args = parser.parse_args()
    
    dashboard = EdgeDashboard(args.config)
    await dashboard.start()

if __name__ == '__main__':
    asyncio.run(main())