#!/usr/bin/env python3
"""
ActiveLog Remote Device Monitoring and Update System
Comprehensive remote monitoring, health checks, and OTA updates for edge devices
"""

import asyncio
import aiohttp
import json
import logging
import os
import hashlib
import zipfile
import shutil
import subprocess
import psutil
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
import sqlite3
from enum import Enum

class DeviceStatus(Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"
    UPDATING = "updating"
    ERROR = "error"

class UpdateStatus(Enum):
    AVAILABLE = "available"
    DOWNLOADING = "downloading"
    INSTALLING = "installing"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLBACK = "rollback"

@dataclass
class DeviceHealthMetrics:
    """Device health metrics structure"""
    timestamp: str
    device_id: str
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    temperature: Optional[float]
    uptime_seconds: int
    network_latency: Optional[float]
    error_count: int
    status: DeviceStatus
    custom_metrics: Dict[str, Any] = None

    def __post_init__(self):
        if self.custom_metrics is None:
            self.custom_metrics = {}

@dataclass
class UpdatePackage:
    """Software update package information"""
    package_id: str
    version: str
    component: str  # 'system', 'activelog-agent', 'firmware', etc.
    size_bytes: int
    checksum: str
    download_url: str
    release_notes: str
    required_version: Optional[str] = None
    rollback_supported: bool = True
    critical: bool = False

class HealthMonitor:
    """Monitors device health and performance metrics"""
    
    def __init__(self, device_id: str, config: Dict):
        self.device_id = device_id
        self.config = config
        self.metrics_history = []
        self.alert_thresholds = config.get("thresholds", {})
        self.logger = logging.getLogger(__name__)
        
        # Initialize metrics database
        self._init_metrics_db()
    
    def _init_metrics_db(self):
        """Initialize metrics storage database"""
        db_path = self.config.get("metrics_db", f"/var/lib/activelog/metrics_{self.device_id}.db")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        with sqlite3.connect(db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS health_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    device_id TEXT NOT NULL,
                    cpu_percent REAL,
                    memory_percent REAL,
                    disk_percent REAL,
                    temperature REAL,
                    uptime_seconds INTEGER,
                    network_latency REAL,
                    error_count INTEGER,
                    status TEXT,
                    custom_metrics TEXT
                )
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_timestamp ON health_metrics(timestamp)
            ''')
    
    async def collect_metrics(self) -> DeviceHealthMetrics:
        """Collect comprehensive health metrics"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            
            # System temperature
            temperature = await self._get_system_temperature()
            
            # Uptime
            boot_time = psutil.boot_time()
            uptime_seconds = int(time.time() - boot_time)
            
            # Network latency (ping to gateway)
            network_latency = await self._measure_network_latency()
            
            # Error count (from system logs)
            error_count = await self._count_recent_errors()
            
            # Determine status
            status = self._determine_device_status(
                cpu_percent, memory_percent, disk_percent, 
                temperature, network_latency
            )
            
            # Custom metrics
            custom_metrics = await self._collect_custom_metrics()
            
            metrics = DeviceHealthMetrics(
                timestamp=datetime.now().isoformat(),
                device_id=self.device_id,
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                disk_percent=disk_percent,
                temperature=temperature,
                uptime_seconds=uptime_seconds,
                network_latency=network_latency,
                error_count=error_count,
                status=status,
                custom_metrics=custom_metrics
            )
            
            # Store metrics
            await self._store_metrics(metrics)
            
            # Check for alerts
            await self._check_alert_conditions(metrics)
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Failed to collect metrics: {e}")
            return DeviceHealthMetrics(
                timestamp=datetime.now().isoformat(),
                device_id=self.device_id,
                cpu_percent=0,
                memory_percent=0,
                disk_percent=0,
                temperature=None,
                uptime_seconds=0,
                network_latency=None,
                error_count=0,
                status=DeviceStatus.ERROR
            )
    
    async def _get_system_temperature(self) -> Optional[float]:
        """Get system temperature"""
        try:
            # Try multiple sources for temperature
            temp_sources = [
                "/sys/class/thermal/thermal_zone0/temp",
                "/sys/class/hwmon/hwmon0/temp1_input",
                "/sys/devices/virtual/thermal/thermal_zone0/temp"
            ]
            
            for temp_file in temp_sources:
                try:
                    with open(temp_file, 'r') as f:
                        temp_raw = int(f.read().strip())
                        # Convert from millicelsius to celsius
                        return temp_raw / 1000.0
                except:
                    continue
            
            # Try vcgencmd for Raspberry Pi
            try:
                result = subprocess.run(
                    ['vcgencmd', 'measure_temp'], 
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    temp_str = result.stdout.strip()
                    if 'temp=' in temp_str:
                        temp_value = temp_str.split('=')[1].replace("'C", "")
                        return float(temp_value)
            except:
                pass
                
        except Exception as e:
            self.logger.debug(f"Temperature reading failed: {e}")
        
        return None
    
    async def _measure_network_latency(self) -> Optional[float]:
        """Measure network latency to default gateway"""
        try:
            # Get default gateway
            result = subprocess.run(
                ['ip', 'route', 'show', 'default'], 
                capture_output=True, text=True, timeout=5
            )
            
            if result.returncode != 0:
                return None
            
            gateway = None
            for line in result.stdout.split('\n'):
                if 'default via' in line:
                    parts = line.split()
                    if len(parts) >= 3:
                        gateway = parts[2]
                        break
            
            if not gateway:
                return None
            
            # Ping gateway
            ping_result = subprocess.run(
                ['ping', '-c', '1', '-W', '2', gateway],
                capture_output=True, text=True, timeout=10
            )
            
            if ping_result.returncode != 0:
                return None
            
            # Parse latency from ping output
            for line in ping_result.stdout.split('\n'):
                if 'time=' in line:
                    time_part = line.split('time=')[1].split()[0]
                    return float(time_part)
                    
        except Exception as e:
            self.logger.debug(f"Network latency measurement failed: {e}")
        
        return None
    
    async def _count_recent_errors(self) -> int:
        """Count recent errors from system logs"""
        try:
            # Check journalctl for recent errors
            result = subprocess.run([
                'journalctl', '--since', '5 minutes ago', 
                '--priority', 'err', '--no-pager', '-q'
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                return len([line for line in result.stdout.split('\n') if line.strip()])
                
        except Exception as e:
            self.logger.debug(f"Error count failed: {e}")
        
        return 0
    
    def _determine_device_status(self, cpu: float, memory: float, disk: float,
                                temperature: Optional[float], latency: Optional[float]) -> DeviceStatus:
        """Determine overall device status"""
        # Check critical thresholds
        if cpu > 95 or memory > 95 or disk > 95:
            return DeviceStatus.ERROR
        
        if temperature and temperature > 85:  # Critical temperature
            return DeviceStatus.ERROR
        
        # Check degraded thresholds
        degraded_conditions = 0
        
        if cpu > self.alert_thresholds.get("cpu_warning", 80):
            degraded_conditions += 1
        if memory > self.alert_thresholds.get("memory_warning", 85):
            degraded_conditions += 1
        if disk > self.alert_thresholds.get("disk_warning", 90):
            degraded_conditions += 1
        if temperature and temperature > self.alert_thresholds.get("temp_warning", 70):
            degraded_conditions += 1
        if latency and latency > self.alert_thresholds.get("latency_warning", 100):
            degraded_conditions += 1
        
        if degraded_conditions >= 2:
            return DeviceStatus.DEGRADED
        
        return DeviceStatus.ONLINE
    
    async def _collect_custom_metrics(self) -> Dict[str, Any]:
        """Collect custom application-specific metrics"""
        custom_metrics = {}
        
        try:
            # ActiveLog agent metrics
            agent_metrics = await self._get_activelog_agent_metrics()
            if agent_metrics:
                custom_metrics["activelog"] = agent_metrics
            
            # GPU metrics (if available)
            gpu_metrics = await self._get_gpu_metrics()
            if gpu_metrics:
                custom_metrics["gpu"] = gpu_metrics
            
            # Docker metrics (if available)
            docker_metrics = await self._get_docker_metrics()
            if docker_metrics:
                custom_metrics["docker"] = docker_metrics
                
        except Exception as e:
            self.logger.debug(f"Custom metrics collection failed: {e}")
        
        return custom_metrics
    
    async def _get_activelog_agent_metrics(self) -> Optional[Dict]:
        """Get ActiveLog agent specific metrics"""
        try:
            # Check if ActiveLog agent is running
            agent_pid = None
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if any('activelog' in str(cmd).lower() for cmd in proc.info['cmdline'] or []):
                        agent_pid = proc.info['pid']
                        break
                except:
                    continue
            
            if not agent_pid:
                return None
            
            # Get process metrics
            agent_proc = psutil.Process(agent_pid)
            
            return {
                "running": True,
                "cpu_percent": agent_proc.cpu_percent(),
                "memory_mb": agent_proc.memory_info().rss / 1024 / 1024,
                "num_threads": agent_proc.num_threads(),
                "open_files": len(agent_proc.open_files())
            }
            
        except Exception as e:
            self.logger.debug(f"ActiveLog agent metrics failed: {e}")
            return {"running": False}
    
    async def _get_gpu_metrics(self) -> Optional[Dict]:
        """Get GPU metrics (NVIDIA)"""
        try:
            result = subprocess.run([
                'nvidia-smi', '--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu',
                '--format=csv,noheader,nounits'
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                values = result.stdout.strip().split(', ')
                if len(values) >= 4:
                    return {
                        "utilization_percent": float(values[0]),
                        "memory_used_mb": float(values[1]),
                        "memory_total_mb": float(values[2]),
                        "temperature_c": float(values[3])
                    }
                    
        except Exception as e:
            self.logger.debug(f"GPU metrics failed: {e}")
        
        return None
    
    async def _get_docker_metrics(self) -> Optional[Dict]:
        """Get Docker container metrics"""
        try:
            result = subprocess.run([
                'docker', 'stats', '--no-stream', '--format', 
                'table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}'
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')[1:]  # Skip header
                containers = []
                
                for line in lines:
                    if line.strip():
                        parts = line.split('\t')
                        if len(parts) >= 3:
                            containers.append({
                                "name": parts[0],
                                "cpu_percent": parts[1].rstrip('%'),
                                "memory_usage": parts[2]
                            })
                
                return {
                    "running_containers": len(containers),
                    "containers": containers
                }
                
        except Exception as e:
            self.logger.debug(f"Docker metrics failed: {e}")
        
        return None
    
    async def _store_metrics(self, metrics: DeviceHealthMetrics):
        """Store metrics in database"""
        try:
            db_path = self.config.get("metrics_db", f"/var/lib/activelog/metrics_{self.device_id}.db")
            
            with sqlite3.connect(db_path) as conn:
                conn.execute('''
                    INSERT INTO health_metrics 
                    (timestamp, device_id, cpu_percent, memory_percent, disk_percent,
                     temperature, uptime_seconds, network_latency, error_count, status, custom_metrics)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    metrics.timestamp,
                    metrics.device_id,
                    metrics.cpu_percent,
                    metrics.memory_percent,
                    metrics.disk_percent,
                    metrics.temperature,
                    metrics.uptime_seconds,
                    metrics.network_latency,
                    metrics.error_count,
                    metrics.status.value,
                    json.dumps(metrics.custom_metrics)
                ))
            
            # Keep metrics in memory for quick access
            self.metrics_history.append(metrics)
            if len(self.metrics_history) > 100:
                self.metrics_history = self.metrics_history[-50:]  # Keep last 50
                
        except Exception as e:
            self.logger.error(f"Failed to store metrics: {e}")
    
    async def _check_alert_conditions(self, metrics: DeviceHealthMetrics):
        """Check if metrics trigger any alerts"""
        alerts = []
        
        # CPU alert
        if metrics.cpu_percent > self.alert_thresholds.get("cpu_critical", 90):
            alerts.append({
                "type": "cpu_critical",
                "message": f"High CPU usage: {metrics.cpu_percent:.1f}%",
                "severity": "critical"
            })
        elif metrics.cpu_percent > self.alert_thresholds.get("cpu_warning", 80):
            alerts.append({
                "type": "cpu_warning",
                "message": f"Elevated CPU usage: {metrics.cpu_percent:.1f}%",
                "severity": "warning"
            })
        
        # Memory alert
        if metrics.memory_percent > self.alert_thresholds.get("memory_critical", 95):
            alerts.append({
                "type": "memory_critical",
                "message": f"High memory usage: {metrics.memory_percent:.1f}%",
                "severity": "critical"
            })
        elif metrics.memory_percent > self.alert_thresholds.get("memory_warning", 85):
            alerts.append({
                "type": "memory_warning",
                "message": f"Elevated memory usage: {metrics.memory_percent:.1f}%",
                "severity": "warning"
            })
        
        # Temperature alert
        if metrics.temperature:
            if metrics.temperature > self.alert_thresholds.get("temp_critical", 80):
                alerts.append({
                    "type": "temperature_critical",
                    "message": f"High temperature: {metrics.temperature:.1f}°C",
                    "severity": "critical"
                })
            elif metrics.temperature > self.alert_thresholds.get("temp_warning", 70):
                alerts.append({
                    "type": "temperature_warning",
                    "message": f"Elevated temperature: {metrics.temperature:.1f}°C",
                    "severity": "warning"
                })
        
        # Send alerts
        for alert in alerts:
            await self._send_alert(alert, metrics)
    
    async def _send_alert(self, alert: Dict, metrics: DeviceHealthMetrics):
        """Send alert notification"""
        self.logger.warning(f"Alert: {alert['message']} on device {self.device_id}")
        
        # In a real implementation, this would send alerts via:
        # - Email
        # - Slack/Teams webhook
        # - SMS
        # - Push notification
        # - Central monitoring system

class UpdateManager:
    """Manages software updates and OTA deployments"""
    
    def __init__(self, device_id: str, config: Dict):
        self.device_id = device_id
        self.config = config
        self.current_updates = {}
        self.update_history = []
        self.logger = logging.getLogger(__name__)
        
        # Initialize update database
        self._init_update_db()
    
    def _init_update_db(self):
        """Initialize update tracking database"""
        db_path = self.config.get("update_db", f"/var/lib/activelog/updates_{self.device_id}.db")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        with sqlite3.connect(db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS updates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    package_id TEXT NOT NULL,
                    version TEXT NOT NULL,
                    component TEXT NOT NULL,
                    status TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    error_message TEXT,
                    rollback_version TEXT
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS update_packages (
                    package_id TEXT PRIMARY KEY,
                    version TEXT NOT NULL,
                    component TEXT NOT NULL,
                    size_bytes INTEGER,
                    checksum TEXT,
                    download_url TEXT,
                    release_notes TEXT,
                    required_version TEXT,
                    rollback_supported BOOLEAN,
                    critical BOOLEAN,
                    downloaded_at TEXT,
                    file_path TEXT
                )
            ''')
    
    async def check_for_updates(self, server_url: str) -> List[UpdatePackage]:
        """Check for available updates from update server"""
        try:
            # Get current version information
            current_versions = await self._get_current_versions()
            
            # Query update server
            async with aiohttp.ClientSession() as session:
                payload = {
                    "device_id": self.device_id,
                    "current_versions": current_versions,
                    "device_type": self.config.get("device_type", "generic")
                }
                
                async with session.post(f"{server_url}/api/updates/check", 
                                      json=payload, timeout=30) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        available_updates = []
                        for update_info in data.get("updates", []):
                            update_package = UpdatePackage(**update_info)
                            available_updates.append(update_package)
                        
                        self.logger.info(f"Found {len(available_updates)} available updates")
                        return available_updates
                    else:
                        self.logger.error(f"Update check failed: {response.status}")
                        
        except Exception as e:
            self.logger.error(f"Failed to check for updates: {e}")
        
        return []
    
    async def _get_current_versions(self) -> Dict[str, str]:
        """Get current version of all components"""
        versions = {}
        
        try:
            # System version
            with open("/etc/os-release", 'r') as f:
                for line in f:
                    if line.startswith("VERSION_ID="):
                        versions["system"] = line.split("=")[1].strip().strip('"')
                        break
            
            # ActiveLog agent version
            try:
                result = subprocess.run([
                    'python3', '-c', 
                    'import activelog; print(activelog.__version__)'
                ], capture_output=True, text=True, timeout=5)
                
                if result.returncode == 0:
                    versions["activelog-agent"] = result.stdout.strip()
            except:
                pass
            
            # Custom application versions
            version_file = Path("/opt/activelog/VERSION")
            if version_file.exists():
                versions["application"] = version_file.read_text().strip()
                
        except Exception as e:
            self.logger.debug(f"Version detection error: {e}")
        
        return versions
    
    async def download_update(self, package: UpdatePackage) -> bool:
        """Download an update package"""
        try:
            self.current_updates[package.package_id] = UpdateStatus.DOWNLOADING
            
            download_dir = Path(self.config.get("download_dir", "/var/lib/activelog/downloads"))
            download_dir.mkdir(parents=True, exist_ok=True)
            
            file_path = download_dir / f"{package.package_id}_{package.version}.zip"
            
            self.logger.info(f"Downloading update {package.package_id} v{package.version}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(package.download_url) as response:
                    if response.status == 200:
                        total_size = int(response.headers.get('content-length', 0))
                        downloaded = 0
                        
                        with open(file_path, 'wb') as f:
                            async for chunk in response.content.iter_chunked(8192):
                                f.write(chunk)
                                downloaded += len(chunk)
                                
                                # Log progress
                                if total_size > 0:
                                    progress = (downloaded / total_size) * 100
                                    if downloaded % (1024 * 1024) == 0:  # Log every MB
                                        self.logger.info(f"Download progress: {progress:.1f}%")
                        
                        # Verify checksum
                        if await self._verify_checksum(file_path, package.checksum):
                            # Store package info
                            await self._store_package_info(package, str(file_path))
                            
                            self.logger.info(f"Successfully downloaded {package.package_id}")
                            return True
                        else:
                            self.logger.error(f"Checksum verification failed for {package.package_id}")
                            file_path.unlink(missing_ok=True)
                            return False
                    else:
                        self.logger.error(f"Download failed: HTTP {response.status}")
                        return False
                        
        except Exception as e:
            self.logger.error(f"Download error: {e}")
            return False
        finally:
            if package.package_id in self.current_updates:
                del self.current_updates[package.package_id]
    
    async def _verify_checksum(self, file_path: Path, expected_checksum: str) -> bool:
        """Verify file checksum"""
        try:
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
            
            actual_checksum = sha256_hash.hexdigest()
            return actual_checksum == expected_checksum
            
        except Exception as e:
            self.logger.error(f"Checksum verification error: {e}")
            return False
    
    async def _store_package_info(self, package: UpdatePackage, file_path: str):
        """Store downloaded package information"""
        try:
            db_path = self.config.get("update_db", f"/var/lib/activelog/updates_{self.device_id}.db")
            
            with sqlite3.connect(db_path) as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO update_packages 
                    (package_id, version, component, size_bytes, checksum, download_url,
                     release_notes, required_version, rollback_supported, critical, 
                     downloaded_at, file_path)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    package.package_id,
                    package.version,
                    package.component,
                    package.size_bytes,
                    package.checksum,
                    package.download_url,
                    package.release_notes,
                    package.required_version,
                    package.rollback_supported,
                    package.critical,
                    datetime.now().isoformat(),
                    file_path
                ))
                
        except Exception as e:
            self.logger.error(f"Failed to store package info: {e}")
    
    async def install_update(self, package_id: str) -> bool:
        """Install a downloaded update package"""
        try:
            self.current_updates[package_id] = UpdateStatus.INSTALLING
            
            # Get package info
            package_info = await self._get_package_info(package_id)
            if not package_info:
                self.logger.error(f"Package {package_id} not found")
                return False
            
            file_path = Path(package_info["file_path"])
            if not file_path.exists():
                self.logger.error(f"Package file not found: {file_path}")
                return False
            
            self.logger.info(f"Installing update {package_id}")
            
            # Record update start
            await self._record_update_start(package_id, package_info)
            
            # Extract update package
            extract_dir = Path(f"/tmp/activelog_update_{package_id}")
            extract_dir.mkdir(exist_ok=True)
            
            try:
                with zipfile.ZipFile(file_path, 'r') as zip_file:
                    zip_file.extractall(extract_dir)
                
                # Look for install script
                install_script = extract_dir / "install.sh"
                if install_script.exists():
                    # Make script executable
                    install_script.chmod(0o755)
                    
                    # Run install script
                    result = subprocess.run([
                        str(install_script), self.device_id, package_info["component"]
                    ], capture_output=True, text=True, timeout=600)  # 10 minute timeout
                    
                    if result.returncode == 0:
                        await self._record_update_completion(package_id, True)
                        self.logger.info(f"Successfully installed {package_id}")
                        
                        # Clean up
                        shutil.rmtree(extract_dir, ignore_errors=True)
                        file_path.unlink(missing_ok=True)
                        
                        return True
                    else:
                        self.logger.error(f"Install script failed: {result.stderr}")
                        await self._record_update_completion(package_id, False, result.stderr)
                        return False
                else:
                    # Default installation for specific component types
                    success = await self._default_install(extract_dir, package_info)
                    await self._record_update_completion(package_id, success)
                    
                    if success:
                        shutil.rmtree(extract_dir, ignore_errors=True)
                        file_path.unlink(missing_ok=True)
                    
                    return success
                    
            except Exception as e:
                self.logger.error(f"Installation failed: {e}")
                await self._record_update_completion(package_id, False, str(e))
                shutil.rmtree(extract_dir, ignore_errors=True)
                return False
                
        except Exception as e:
            self.logger.error(f"Update installation error: {e}")
            return False
        finally:
            if package_id in self.current_updates:
                del self.current_updates[package_id]
    
    async def _get_package_info(self, package_id: str) -> Optional[Dict]:
        """Get stored package information"""
        try:
            db_path = self.config.get("update_db", f"/var/lib/activelog/updates_{self.device_id}.db")
            
            with sqlite3.connect(db_path) as conn:
                cursor = conn.execute('''
                    SELECT * FROM update_packages WHERE package_id = ?
                ''', (package_id,))
                
                row = cursor.fetchone()
                if row:
                    columns = [description[0] for description in cursor.description]
                    return dict(zip(columns, row))
                    
        except Exception as e:
            self.logger.error(f"Failed to get package info: {e}")
        
        return None
    
    async def _record_update_start(self, package_id: str, package_info: Dict):
        """Record update start in database"""
        try:
            db_path = self.config.get("update_db", f"/var/lib/activelog/updates_{self.device_id}.db")
            
            with sqlite3.connect(db_path) as conn:
                conn.execute('''
                    INSERT INTO updates 
                    (package_id, version, component, status, started_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    package_id,
                    package_info["version"],
                    package_info["component"],
                    UpdateStatus.INSTALLING.value,
                    datetime.now().isoformat()
                ))
                
        except Exception as e:
            self.logger.error(f"Failed to record update start: {e}")
    
    async def _record_update_completion(self, package_id: str, success: bool, 
                                      error_message: str = None):
        """Record update completion in database"""
        try:
            db_path = self.config.get("update_db", f"/var/lib/activelog/updates_{self.device_id}.db")
            
            status = UpdateStatus.COMPLETED if success else UpdateStatus.FAILED
            
            with sqlite3.connect(db_path) as conn:
                conn.execute('''
                    UPDATE updates 
                    SET status = ?, completed_at = ?, error_message = ?
                    WHERE package_id = ? AND completed_at IS NULL
                ''', (
                    status.value,
                    datetime.now().isoformat(),
                    error_message,
                    package_id
                ))
                
        except Exception as e:
            self.logger.error(f"Failed to record update completion: {e}")
    
    async def _default_install(self, extract_dir: Path, package_info: Dict) -> bool:
        """Default installation logic for common component types"""
        component = package_info["component"]
        
        try:
            if component == "activelog-agent":
                # Install ActiveLog agent
                return await self._install_activelog_agent(extract_dir)
            elif component == "system":
                # System update (requires careful handling)
                return await self._install_system_update(extract_dir)
            elif component == "application":
                # Application update
                return await self._install_application_update(extract_dir)
            else:
                self.logger.error(f"Unknown component type: {component}")
                return False
                
        except Exception as e:
            self.logger.error(f"Default installation failed: {e}")
            return False
    
    async def _install_activelog_agent(self, extract_dir: Path) -> bool:
        """Install ActiveLog agent update"""
        try:
            # Stop current agent
            subprocess.run(['systemctl', 'stop', 'activelog-agent'], timeout=30)
            
            # Backup current installation
            backup_dir = Path("/opt/activelog/backup")
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            if Path("/opt/activelog/agent").exists():
                shutil.copytree("/opt/activelog/agent", 
                               backup_dir / f"agent_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            
            # Install new version
            agent_files = extract_dir / "agent"
            if agent_files.exists():
                if Path("/opt/activelog/agent").exists():
                    shutil.rmtree("/opt/activelog/agent")
                
                shutil.copytree(agent_files, "/opt/activelog/agent")
                
                # Set permissions
                for file_path in Path("/opt/activelog/agent").rglob("*.py"):
                    file_path.chmod(0o755)
                
                # Start agent
                subprocess.run(['systemctl', 'start', 'activelog-agent'], timeout=30)
                
                # Verify agent is running
                await asyncio.sleep(5)
                result = subprocess.run(['systemctl', 'is-active', 'activelog-agent'], 
                                      capture_output=True, text=True)
                
                return result.returncode == 0 and result.stdout.strip() == "active"
            
        except Exception as e:
            self.logger.error(f"ActiveLog agent installation failed: {e}")
        
        return False
    
    async def _install_system_update(self, extract_dir: Path) -> bool:
        """Install system update (placeholder)"""
        # System updates require very careful handling and are typically
        # done through package managers. This is a simplified example.
        self.logger.warning("System updates not implemented in this example")
        return False
    
    async def _install_application_update(self, extract_dir: Path) -> bool:
        """Install application update"""
        try:
            app_files = extract_dir / "app"
            if app_files.exists():
                # Stop application
                subprocess.run(['systemctl', 'stop', 'activelog-app'], timeout=30)
                
                # Backup current application
                backup_dir = Path("/opt/activelog/backup")
                backup_dir.mkdir(parents=True, exist_ok=True)
                
                if Path("/opt/activelog/app").exists():
                    shutil.copytree("/opt/activelog/app",
                                   backup_dir / f"app_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
                
                # Install new version
                if Path("/opt/activelog/app").exists():
                    shutil.rmtree("/opt/activelog/app")
                
                shutil.copytree(app_files, "/opt/activelog/app")
                
                # Start application
                subprocess.run(['systemctl', 'start', 'activelog-app'], timeout=30)
                
                return True
                
        except Exception as e:
            self.logger.error(f"Application installation failed: {e}")
        
        return False
    
    async def rollback_update(self, package_id: str) -> bool:
        """Rollback a previously installed update"""
        try:
            self.logger.info(f"Rolling back update {package_id}")
            
            # Get update info
            update_info = await self._get_update_info(package_id)
            if not update_info:
                return False
            
            component = update_info["component"]
            
            # Find most recent backup
            backup_dir = Path("/opt/activelog/backup")
            if not backup_dir.exists():
                self.logger.error("No backup directory found")
                return False
            
            backup_pattern = f"{component}_*"
            backups = list(backup_dir.glob(backup_pattern))
            
            if not backups:
                self.logger.error(f"No backups found for component {component}")
                return False
            
            # Get most recent backup
            latest_backup = max(backups, key=lambda p: p.stat().st_mtime)
            
            # Stop service
            subprocess.run(['systemctl', 'stop', f'activelog-{component}'], timeout=30)
            
            # Restore from backup
            target_dir = Path(f"/opt/activelog/{component}")
            if target_dir.exists():
                shutil.rmtree(target_dir)
            
            shutil.copytree(latest_backup, target_dir)
            
            # Start service
            subprocess.run(['systemctl', 'start', f'activelog-{component}'], timeout=30)
            
            # Record rollback
            await self._record_rollback(package_id)
            
            self.logger.info(f"Successfully rolled back {package_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Rollback failed: {e}")
            return False
    
    async def _get_update_info(self, package_id: str) -> Optional[Dict]:
        """Get update information from database"""
        try:
            db_path = self.config.get("update_db", f"/var/lib/activelog/updates_{self.device_id}.db")
            
            with sqlite3.connect(db_path) as conn:
                cursor = conn.execute('''
                    SELECT * FROM updates WHERE package_id = ? 
                    ORDER BY started_at DESC LIMIT 1
                ''', (package_id,))
                
                row = cursor.fetchone()
                if row:
                    columns = [description[0] for description in cursor.description]
                    return dict(zip(columns, row))
                    
        except Exception as e:
            self.logger.error(f"Failed to get update info: {e}")
        
        return None
    
    async def _record_rollback(self, package_id: str):
        """Record rollback in database"""
        try:
            db_path = self.config.get("update_db", f"/var/lib/activelog/updates_{self.device_id}.db")
            
            with sqlite3.connect(db_path) as conn:
                conn.execute('''
                    UPDATE updates 
                    SET status = ?, completed_at = ?
                    WHERE package_id = ? AND status = ?
                ''', (
                    UpdateStatus.ROLLBACK.value,
                    datetime.now().isoformat(),
                    package_id,
                    UpdateStatus.COMPLETED.value
                ))
                
        except Exception as e:
            self.logger.error(f"Failed to record rollback: {e}")

class RemoteMonitoringAgent:
    """Main remote monitoring and update agent"""
    
    def __init__(self, config_path: str = "/etc/activelog/monitoring.conf"):
        self.config_path = config_path
        self.config = self._load_config()
        self.device_id = self.config.get("device_id", "unknown")
        self.running = False
        
        # Initialize logging
        self.logger = self._setup_logging()
        
        # Initialize managers
        self.health_monitor = HealthMonitor(self.device_id, self.config.get("health", {}))
        self.update_manager = UpdateManager(self.device_id, self.config.get("updates", {}))
        
        self.logger.info(f"Remote Monitoring Agent initialized for device: {self.device_id}")
    
    def _load_config(self) -> Dict:
        """Load monitoring configuration"""
        default_config = {
            "device_id": "edge_device_001",
            "server_url": "https://monitor.activelog.ai",
            "reporting_interval": 300,  # 5 minutes
            "update_check_interval": 3600,  # 1 hour
            "health": {
                "thresholds": {
                    "cpu_warning": 80,
                    "cpu_critical": 90,
                    "memory_warning": 85,
                    "memory_critical": 95,
                    "disk_warning": 90,
                    "disk_critical": 95,
                    "temp_warning": 70,
                    "temp_critical": 80,
                    "latency_warning": 100
                }
            },
            "updates": {
                "auto_download": True,
                "auto_install_critical": True,
                "auto_install_non_critical": False,
                "maintenance_window": {
                    "start": "02:00",
                    "end": "04:00"
                }
            }
        }
        
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    loaded_config = json.load(f)
                    self._merge_config(default_config, loaded_config)
        except Exception as e:
            print(f"Error loading config: {e}")
        
        return default_config
    
    def _merge_config(self, default: Dict, loaded: Dict):
        """Recursively merge configurations"""
        for key, value in loaded.items():
            if key in default and isinstance(default[key], dict) and isinstance(value, dict):
                self._merge_config(default[key], value)
            else:
                default[key] = value
    
    def _setup_logging(self):
        """Setup logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler("/var/log/activelog/monitoring.log"),
                logging.StreamHandler()
            ]
        )
        return logging.getLogger(__name__)
    
    async def start(self):
        """Start the monitoring agent"""
        self.running = True
        self.logger.info("Starting Remote Monitoring Agent")
        
        # Start background tasks
        tasks = [
            asyncio.create_task(self._health_monitoring_loop()),
            asyncio.create_task(self._update_checking_loop()),
            asyncio.create_task(self._reporting_loop())
        ]
        
        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            self.logger.info("Received shutdown signal")
        finally:
            await self.stop()
    
    async def stop(self):
        """Stop the monitoring agent"""
        self.running = False
        self.logger.info("Remote Monitoring Agent stopped")
    
    async def _health_monitoring_loop(self):
        """Continuous health monitoring"""
        while self.running:
            try:
                metrics = await self.health_monitor.collect_metrics()
                
                # Log significant status changes
                if hasattr(self, '_last_status'):
                    if metrics.status != self._last_status:
                        self.logger.info(f"Device status changed: {self._last_status.value} -> {metrics.status.value}")
                
                self._last_status = metrics.status
                
                await asyncio.sleep(60)  # Collect metrics every minute
                
            except Exception as e:
                self.logger.error(f"Health monitoring error: {e}")
                await asyncio.sleep(60)
    
    async def _update_checking_loop(self):
        """Periodic update checking"""
        while self.running:
            try:
                await asyncio.sleep(self.config["update_check_interval"])
                
                if not self.running:
                    break
                
                # Check for available updates
                server_url = self.config["server_url"]
                available_updates = await self.update_manager.check_for_updates(server_url)
                
                if available_updates:
                    self.logger.info(f"Found {len(available_updates)} available updates")
                    
                    for update in available_updates:
                        # Auto-download if enabled
                        if self.config["updates"]["auto_download"]:
                            await self.update_manager.download_update(update)
                        
                        # Auto-install critical updates if enabled
                        if (update.critical and 
                            self.config["updates"]["auto_install_critical"]):
                            await self._schedule_update_installation(update)
                        elif (not update.critical and
                              self.config["updates"]["auto_install_non_critical"]):
                            await self._schedule_update_installation(update)
                
            except Exception as e:
                self.logger.error(f"Update checking error: {e}")
    
    async def _schedule_update_installation(self, update: UpdatePackage):
        """Schedule update installation during maintenance window"""
        try:
            maintenance_config = self.config["updates"]["maintenance_window"]
            
            # Check if we're in maintenance window
            if self._is_maintenance_window(maintenance_config):
                self.logger.info(f"Installing update {update.package_id} during maintenance window")
                await self.update_manager.install_update(update.package_id)
            else:
                # Schedule for next maintenance window
                self.logger.info(f"Scheduling update {update.package_id} for next maintenance window")
                # In a real implementation, this would use a job scheduler
                
        except Exception as e:
            self.logger.error(f"Update scheduling error: {e}")
    
    def _is_maintenance_window(self, maintenance_config: Dict) -> bool:
        """Check if current time is within maintenance window"""
        try:
            now = datetime.now()
            current_time = now.strftime("%H:%M")
            
            start_time = maintenance_config["start"]
            end_time = maintenance_config["end"]
            
            return start_time <= current_time <= end_time
            
        except Exception as e:
            self.logger.debug(f"Maintenance window check error: {e}")
            return False
    
    async def _reporting_loop(self):
        """Periodic reporting to central server"""
        while self.running:
            try:
                await asyncio.sleep(self.config["reporting_interval"])
                
                if not self.running:
                    break
                
                # Collect current metrics
                metrics = await self.health_monitor.collect_metrics()
                
                # Prepare report
                report = {
                    "device_id": self.device_id,
                    "timestamp": datetime.now().isoformat(),
                    "metrics": asdict(metrics),
                    "update_status": self._get_update_status(),
                    "agent_version": "1.0.0"  # Would be dynamic
                }
                
                # Send report to server
                await self._send_report(report)
                
            except Exception as e:
                self.logger.error(f"Reporting error: {e}")
    
    def _get_update_status(self) -> Dict:
        """Get current update status"""
        return {
            "active_updates": len(self.update_manager.current_updates),
            "update_statuses": dict(self.update_manager.current_updates)
        }
    
    async def _send_report(self, report: Dict):
        """Send monitoring report to central server"""
        try:
            server_url = self.config["server_url"]
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{server_url}/api/monitoring/report",
                    json=report,
                    timeout=30
                ) as response:
                    if response.status == 200:
                        self.logger.debug("Report sent successfully")
                    else:
                        self.logger.warning(f"Report failed: HTTP {response.status}")
                        
        except Exception as e:
            self.logger.debug(f"Report sending failed: {e}")

async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="ActiveLog Remote Monitoring Agent")
    parser.add_argument("--config", default="/etc/activelog/monitoring.conf",
                        help="Configuration file path")
    parser.add_argument("--device-id", help="Device ID override")
    
    args = parser.parse_args()
    
    agent = RemoteMonitoringAgent(args.config)
    
    if args.device_id:
        agent.device_id = args.device_id
        agent.config["device_id"] = args.device_id
    
    try:
        await agent.start()
    except KeyboardInterrupt:
        print("Remote monitoring agent stopped")

if __name__ == "__main__":
    asyncio.run(main())