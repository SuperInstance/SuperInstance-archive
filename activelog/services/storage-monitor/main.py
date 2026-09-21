#!/usr/bin/env python3
"""
Automated Storage Monitoring and Remediation System
Prevents storage disasters like the 598GB checkpoint bloat issue

This system monitors for:
- Rapid growth (100MB+ in 5 minutes)  
- Large files (1GB+ single files)
- Directory limits (5GB+ per directory)
- Disk usage warnings (80%+) and critical (95%+)
- Automatic remediation and alerting
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
import os
import json
import time
import logging
import sqlite3
import threading
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import subprocess
import psutil
import hashlib
import shutil
from contextlib import asynccontextmanager

# Configuration
STORAGE_DB = "/home/activeloguser/activelog/services/storage-monitor/data/storage_monitor.db"
LOG_FILE = "/home/activeloguser/activelog/services/storage-monitor/logs/storage_monitor.log"
CONFIG_FILE = "/home/activeloguser/activelog/services/storage-monitor/config/monitor_config.json"

# Global monitoring thread
monitoring_thread = None
monitoring_active = False

class StorageMonitor:
    def __init__(self, config_path: str = CONFIG_FILE):
        self.config_path = config_path
        self.load_config()
        self.setup_logging()
        self.setup_database()
        self.growth_history = {}
        self.last_scan_time = {}
        
    def load_config(self):
        """Load configuration with enhanced thresholds"""
        default_config = {
            "thresholds": {
                "rapid_growth_mb": 100,  # 100MB in scan_interval
                "large_file_gb": 1.0,    # 1GB single file
                "directory_limit_gb": 5.0,  # 5GB per directory
                "disk_usage_warning": 0.8,  # 80% disk usage
                "disk_usage_critical": 0.95,  # 95% disk usage
                "scan_interval_seconds": 60,  # Check every minute
                "growth_window_minutes": 5,  # Growth rate calculation window
                "alert_cooldown_minutes": 15  # Minimum time between alerts
            },
            "paths_to_monitor": [
                "/home/activeloguser/activelog/services",
                "/home/activeloguser/activelog/checkpoints", 
                "/home/activeloguser/activelog/backups",
                "/home/activeloguser/activelog/logs",
                "/home/activeloguser/activelog/pids"
            ],
            "paths_to_exclude": [
                "/home/activeloguser/activelog/services/*/node_modules",
                "/home/activeloguser/activelog/services/*/__pycache__",
                "/home/activeloguser/activelog/services/*/dist",
                "/home/activeloguser/activelog/services/*/build",
                "/home/activeloguser/activelog/services/*/.git"
            ],
            "remediation": {
                "auto_remediate": True,
                "max_file_size_for_auto_delete_mb": 500,  # Only auto-delete files < 500MB
                "backup_before_delete": True,
                "compress_large_files": True,
                "move_to_quarantine": True,
                "quarantine_dir": "/home/activeloguser/activelog/services/storage-monitor/quarantine"
            },
            "alerts": {
                "enabled": True,
                "log_alerts": True,
                "email_alerts": False,
                "webhook_alerts": False,
                "integration_with_improvement_system": True
            }
        }
        
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    loaded_config = json.load(f)
                # Merge with defaults
                self.config = {**default_config, **loaded_config}
            else:
                self.config = default_config
                with open(self.config_path, 'w') as f:
                    json.dump(default_config, f, indent=2)
        except Exception as e:
            print(f"Error loading config: {e}")
            self.config = default_config
    
    def setup_logging(self):
        """Setup comprehensive logging"""
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(LOG_FILE),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('StorageMonitor')
        
    def setup_database(self):
        """Setup SQLite database for tracking"""
        os.makedirs(os.path.dirname(STORAGE_DB), exist_ok=True)
        
        with sqlite3.connect(STORAGE_DB) as conn:
            cursor = conn.cursor()
            
            # Directory size history
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS directory_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    path TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    file_count INTEGER NOT NULL,
                    timestamp DATETIME NOT NULL,
                    scan_duration_ms INTEGER
                )
            ''')
            
            # Large files tracking
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS large_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    path TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    created_time DATETIME,
                    modified_time DATETIME,
                    detected_time DATETIME NOT NULL,
                    file_hash TEXT,
                    remediated BOOLEAN DEFAULT FALSE
                )
            ''')
            
            # Rapid growth alerts
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS growth_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    path TEXT NOT NULL,
                    growth_rate_mb INTEGER NOT NULL,
                    time_window_minutes INTEGER NOT NULL,
                    alert_time DATETIME NOT NULL,
                    remediation_action TEXT,
                    resolved BOOLEAN DEFAULT FALSE
                )
            ''')
            
            # System metrics
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS system_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    disk_total_gb REAL NOT NULL,
                    disk_used_gb REAL NOT NULL,
                    disk_free_gb REAL NOT NULL,
                    disk_usage_percent REAL NOT NULL,
                    cpu_percent REAL,
                    memory_percent REAL
                )
            ''')
            
            # Remediation log
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS remediation_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    action_type TEXT NOT NULL,
                    target_path TEXT NOT NULL,
                    original_size_bytes INTEGER,
                    final_size_bytes INTEGER,
                    success BOOLEAN NOT NULL,
                    details TEXT
                )
            ''')
            
            conn.commit()
    
    def get_directory_size_and_count(self, path: Path) -> Tuple[int, int]:
        """Get directory size and file count efficiently"""
        total_size = 0
        file_count = 0
        
        try:
            for dirpath, dirnames, filenames in os.walk(path):
                # Skip excluded directories
                if self.is_path_excluded(dirpath):
                    continue
                    
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    try:
                        if os.path.exists(filepath) and not os.path.islink(filepath):
                            size = os.path.getsize(filepath)
                            total_size += size
                            file_count += 1
                            
                            # Check for large files while we're scanning
                            if size > self.config['thresholds']['large_file_gb'] * 1_000_000_000:
                                self.handle_large_file(filepath, size)
                                
                    except (OSError, IOError):
                        continue
                        
        except Exception as e:
            self.logger.error(f"Error scanning directory {path}: {e}")
            
        return total_size, file_count
    
    def is_path_excluded(self, path: str) -> bool:
        """Check if path should be excluded from monitoring"""
        for pattern in self.config['paths_to_exclude']:
            if pattern.replace('*', '') in path:
                return True
        return False
    
    def calculate_growth_rate(self, path: str) -> Optional[float]:
        """Calculate growth rate for a directory in MB per time window"""
        try:
            with sqlite3.connect(STORAGE_DB) as conn:
                cursor = conn.cursor()
                
                # Get size history for this path
                window_start = datetime.now() - timedelta(
                    minutes=self.config['thresholds']['growth_window_minutes']
                )
                
                cursor.execute('''
                    SELECT size_bytes, timestamp FROM directory_history 
                    WHERE path = ? AND timestamp >= ? 
                    ORDER BY timestamp DESC LIMIT 2
                ''', (path, window_start))
                
                results = cursor.fetchall()
                
                if len(results) >= 2:
                    current_size, current_time = results[0]
                    previous_size, previous_time = results[1]
                    
                    # Convert to datetime objects for calculation
                    current_dt = datetime.fromisoformat(current_time)
                    previous_dt = datetime.fromisoformat(previous_time)
                    
                    time_diff_minutes = (current_dt - previous_dt).total_seconds() / 60
                    size_diff_bytes = current_size - previous_size
                    
                    if time_diff_minutes > 0 and size_diff_bytes > 0:
                        # Return growth rate in MB per scan interval
                        growth_rate_mb = (size_diff_bytes / 1_000_000) / (time_diff_minutes / self.config['thresholds']['growth_window_minutes'])
                        return growth_rate_mb
                        
        except Exception as e:
            self.logger.error(f"Error calculating growth rate for {path}: {e}")
            
        return None
    
    def handle_large_file(self, filepath: str, size: int):
        """Handle discovery of large file"""
        try:
            with sqlite3.connect(STORAGE_DB) as conn:
                cursor = conn.cursor()
                
                # Check if we've already recorded this file
                cursor.execute('''
                    SELECT id FROM large_files WHERE path = ? AND size_bytes = ?
                ''', (filepath, size))
                
                if cursor.fetchone():
                    return  # Already recorded
                
                # Get file metadata
                stat = os.stat(filepath)
                created_time = datetime.fromtimestamp(stat.st_ctime)
                modified_time = datetime.fromtimestamp(stat.st_mtime)
                
                # Calculate file hash for deduplication
                file_hash = self.calculate_file_hash(filepath) if size < 100_000_000 else None
                
                # Record the large file
                cursor.execute('''
                    INSERT INTO large_files 
                    (path, size_bytes, created_time, modified_time, detected_time, file_hash)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (filepath, size, created_time, modified_time, datetime.now(), file_hash))
                
                conn.commit()
                
                self.logger.warning(f"Large file detected: {filepath} ({size / 1_000_000:.1f} MB)")
                
                # Auto-remediate if configured
                if self.config['remediation']['auto_remediate']:
                    self.auto_remediate_large_file(filepath, size)
                    
        except Exception as e:
            self.logger.error(f"Error handling large file {filepath}: {e}")
    
    def calculate_file_hash(self, filepath: str) -> str:
        """Calculate SHA-256 hash of file for deduplication"""
        try:
            hash_sha256 = hashlib.sha256()
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception:
            return None
    
    def handle_runaway_storage(self, path: str, growth_rate: float):
        """Handle rapid storage growth"""
        self.logger.critical(f"RUNAWAY STORAGE DETECTED: {path} growing at {growth_rate:.1f}MB per scan interval")
        
        # Record the alert
        try:
            with sqlite3.connect(STORAGE_DB) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO growth_alerts 
                    (path, growth_rate_mb, time_window_minutes, alert_time)
                    VALUES (?, ?, ?, ?)
                ''', (path, int(growth_rate), self.config['thresholds']['growth_window_minutes'], datetime.now()))
                conn.commit()
        except Exception as e:
            self.logger.error(f"Error recording growth alert: {e}")
        
        # Emergency remediation
        if self.config['remediation']['auto_remediate']:
            self.emergency_remediation(path, growth_rate)
    
    def emergency_remediation(self, path: str, growth_rate: float):
        """Emergency remediation for runaway storage growth"""
        self.logger.info(f"Starting emergency remediation for {path}")
        
        remediation_actions = []
        
        try:
            path_obj = Path(path)
            
            # 1. Stop any processes that might be writing to this directory
            self.stop_related_processes(path)
            remediation_actions.append("stopped_related_processes")
            
            # 2. Find and quarantine the largest files
            large_files = self.find_largest_files(path, limit=10)
            for file_path, file_size in large_files:
                if file_size > 10_000_000:  # > 10MB
                    if self.quarantine_file(file_path, file_size):
                        remediation_actions.append(f"quarantined_{os.path.basename(file_path)}")
            
            # 3. Compress old log files if this is a log directory
            if 'log' in path.lower():
                self.compress_old_logs(path)
                remediation_actions.append("compressed_old_logs")
            
            # 4. Alert improvement system
            if self.config['alerts']['integration_with_improvement_system']:
                self.alert_improvement_system(path, growth_rate, remediation_actions)
            
            # Log remediation
            self.log_remediation("emergency_remediation", path, remediation_actions)
            
        except Exception as e:
            self.logger.error(f"Emergency remediation failed for {path}: {e}")
    
    def stop_related_processes(self, path: str):
        """Stop processes that might be writing to the problematic directory"""
        try:
            # Find processes with open files in this directory
            for proc in psutil.process_iter(['pid', 'name', 'open_files']):
                try:
                    open_files = proc.info['open_files']
                    if open_files:
                        for file_info in open_files:
                            if path in file_info.path:
                                self.logger.warning(f"Stopping process {proc.info['name']} (PID: {proc.info['pid']}) writing to {path}")
                                # Be careful - only stop specific service processes
                                if 'python' in proc.info['name'].lower() or 'node' in proc.info['name'].lower():
                                    proc.terminate()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            self.logger.error(f"Error stopping related processes: {e}")
    
    def find_largest_files(self, path: str, limit: int = 10) -> List[Tuple[str, int]]:
        """Find the largest files in a directory"""
        files_with_sizes = []
        
        try:
            for root, dirs, files in os.walk(path):
                for file in files:
                    filepath = os.path.join(root, file)
                    try:
                        size = os.path.getsize(filepath)
                        files_with_sizes.append((filepath, size))
                    except (OSError, IOError):
                        continue
            
            # Sort by size (largest first) and return top N
            files_with_sizes.sort(key=lambda x: x[1], reverse=True)
            return files_with_sizes[:limit]
            
        except Exception as e:
            self.logger.error(f"Error finding largest files in {path}: {e}")
            return []
    
    def quarantine_file(self, filepath: str, size: int) -> bool:
        """Move file to quarantine directory"""
        try:
            quarantine_dir = Path(self.config['remediation']['quarantine_dir'])
            quarantine_dir.mkdir(parents=True, exist_ok=True)
            
            # Create unique filename in quarantine
            original_name = os.path.basename(filepath)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            quarantine_name = f"{timestamp}_{original_name}"
            quarantine_path = quarantine_dir / quarantine_name
            
            # Move file to quarantine
            shutil.move(filepath, quarantine_path)
            
            self.logger.info(f"Quarantined file: {filepath} -> {quarantine_path} ({size / 1_000_000:.1f}MB)")
            
            # Create metadata file
            metadata = {
                'original_path': filepath,
                'quarantine_path': str(quarantine_path),
                'size_bytes': size,
                'quarantine_time': datetime.now().isoformat(),
                'reason': 'emergency_remediation'
            }
            
            metadata_path = quarantine_path.with_suffix(quarantine_path.suffix + '.meta.json')
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error quarantining file {filepath}: {e}")
            return False
    
    def compress_old_logs(self, log_dir: str):
        """Compress old log files to save space"""
        try:
            for root, dirs, files in os.walk(log_dir):
                for file in files:
                    if file.endswith('.log') and not file.endswith('.gz'):
                        filepath = os.path.join(root, file)
                        
                        # Only compress files older than 1 day and larger than 1MB
                        stat = os.stat(filepath)
                        age_hours = (time.time() - stat.st_mtime) / 3600
                        size_mb = stat.st_size / 1_000_000
                        
                        if age_hours > 24 and size_mb > 1:
                            compressed_path = f"{filepath}.gz"
                            subprocess.run(['gzip', filepath], check=True)
                            self.logger.info(f"Compressed log file: {filepath} -> {compressed_path}")
                            
        except Exception as e:
            self.logger.error(f"Error compressing logs in {log_dir}: {e}")
    
    def auto_remediate_large_file(self, filepath: str, size: int):
        """Auto-remediate a large file based on configuration"""
        remediation_actions = []
        
        try:
            # Only auto-delete files under the configured threshold
            max_auto_delete_size = self.config['remediation']['max_file_size_for_auto_delete_mb'] * 1_000_000
            
            if size < max_auto_delete_size:
                # Check if it's a temp file, log file, or cache file
                filename = os.path.basename(filepath).lower()
                
                if any(pattern in filename for pattern in ['.tmp', '.temp', '.cache', '.log']):
                    if self.config['remediation']['backup_before_delete']:
                        self.quarantine_file(filepath, size)
                        remediation_actions.append("quarantined")
                    else:
                        os.remove(filepath)
                        remediation_actions.append("deleted")
                        
                elif self.config['remediation']['compress_large_files']:
                    self.compress_file(filepath)
                    remediation_actions.append("compressed")
                    
            elif self.config['remediation']['move_to_quarantine']:
                self.quarantine_file(filepath, size)
                remediation_actions.append("quarantined")
            
            if remediation_actions:
                self.log_remediation("auto_remediate_large_file", filepath, remediation_actions)
                
        except Exception as e:
            self.logger.error(f"Auto-remediation failed for {filepath}: {e}")
    
    def compress_file(self, filepath: str):
        """Compress a file to save space"""
        try:
            subprocess.run(['gzip', filepath], check=True)
            self.logger.info(f"Compressed file: {filepath}")
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to compress {filepath}: {e}")
    
    def log_remediation(self, action_type: str, target_path: str, actions: List[str]):
        """Log remediation actions"""
        try:
            with sqlite3.connect(STORAGE_DB) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO remediation_log 
                    (timestamp, action_type, target_path, success, details)
                    VALUES (?, ?, ?, ?, ?)
                ''', (datetime.now(), action_type, target_path, True, json.dumps(actions)))
                conn.commit()
        except Exception as e:
            self.logger.error(f"Error logging remediation: {e}")
    
    def alert_improvement_system(self, path: str, growth_rate: float, actions: List[str]):
        """Alert the improvement system about storage issues"""
        try:
            # Try to contact the improvement system API
            import requests
            
            alert_data = {
                'type': 'storage_emergency',
                'path': path,
                'growth_rate_mb': growth_rate,
                'remediation_actions': actions,
                'timestamp': datetime.now().isoformat()
            }
            
            # Try improvement system first
            try:
                response = requests.post(
                    'http://localhost:8500/emergency-alert',
                    json=alert_data,
                    timeout=5
                )
                if response.status_code == 200:
                    self.logger.info("Alert sent to improvement system")
            except requests.RequestException:
                self.logger.warning("Could not contact improvement system")
            
        except ImportError:
            self.logger.warning("requests library not available for alerting")
    
    def scan_directories(self) -> List[str]:
        """Get list of directories to scan"""
        directories = []
        
        for path_pattern in self.config['paths_to_monitor']:
            try:
                path = Path(path_pattern)
                if path.exists() and path.is_dir():
                    directories.append(str(path))
                    
                    # Also add immediate subdirectories for services
                    if 'services' in str(path):
                        for subdir in path.iterdir():
                            if subdir.is_dir() and not self.is_path_excluded(str(subdir)):
                                directories.append(str(subdir))
            except Exception as e:
                self.logger.error(f"Error processing path pattern {path_pattern}: {e}")
                
        return directories
    
    def record_system_metrics(self):
        """Record system-wide disk and resource metrics"""
        try:
            disk_usage = psutil.disk_usage('/home/activeloguser/activelog')
            cpu_percent = psutil.cpu_percent()
            memory_percent = psutil.virtual_memory().percent
            
            with sqlite3.connect(STORAGE_DB) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO system_metrics 
                    (timestamp, disk_total_gb, disk_used_gb, disk_free_gb, 
                     disk_usage_percent, cpu_percent, memory_percent)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    datetime.now(),
                    disk_usage.total / 1_000_000_000,
                    disk_usage.used / 1_000_000_000,
                    disk_usage.free / 1_000_000_000,
                    (disk_usage.used / disk_usage.total) * 100,
                    cpu_percent,
                    memory_percent
                ))
                conn.commit()
            
            # Check disk usage thresholds
            usage_percent = (disk_usage.used / disk_usage.total)
            
            if usage_percent > self.config['thresholds']['disk_usage_critical']:
                self.logger.critical(f"CRITICAL: Disk usage at {usage_percent*100:.1f}%")
                # Emergency cleanup
                self.emergency_disk_cleanup()
            elif usage_percent > self.config['thresholds']['disk_usage_warning']:
                self.logger.warning(f"WARNING: Disk usage at {usage_percent*100:.1f}%")
                
        except Exception as e:
            self.logger.error(f"Error recording system metrics: {e}")
    
    def emergency_disk_cleanup(self):
        """Emergency disk cleanup when space is critically low"""
        self.logger.info("Starting emergency disk cleanup")
        
        cleanup_actions = []
        
        try:
            # 1. Clean up quarantine directory (oldest files first)
            quarantine_dir = Path(self.config['remediation']['quarantine_dir'])
            if quarantine_dir.exists():
                quarantine_files = sorted(quarantine_dir.glob("*"), key=lambda p: p.stat().st_mtime)
                for old_file in quarantine_files[:10]:  # Remove 10 oldest
                    try:
                        old_file.unlink()
                        cleanup_actions.append(f"removed_quarantine_{old_file.name}")
                    except Exception:
                        pass
            
            # 2. Trigger improvement system cleanup
            try:
                subprocess.run([
                    '/home/activeloguser/activelog/services/improvement-system/bin/cleanup-checkpoints.sh',
                    'size'
                ], check=True, timeout=60)
                cleanup_actions.append("improvement_system_cleanup")
            except Exception:
                pass
            
            # 3. Compress large log files system-wide
            for log_dir in ['/home/activeloguser/activelog/logs', '/home/activeloguser/activelog/services/*/logs']:
                if os.path.exists(log_dir):
                    self.compress_old_logs(log_dir)
                    cleanup_actions.append(f"compressed_logs_{os.path.basename(log_dir)}")
            
            self.log_remediation("emergency_disk_cleanup", "/", cleanup_actions)
            
        except Exception as e:
            self.logger.error(f"Emergency disk cleanup failed: {e}")
    
    def monitor_loop(self):
        """Main monitoring loop"""
        self.logger.info("Starting storage monitoring loop")
        
        while monitoring_active:
            try:
                scan_start_time = time.time()
                
                # Record system metrics
                self.record_system_metrics()
                
                # Scan all monitored directories
                for dir_path in self.scan_directories():
                    try:
                        # Get current size and file count
                        size_bytes, file_count = self.get_directory_size_and_count(Path(dir_path))
                        scan_duration_ms = int((time.time() - scan_start_time) * 1000)
                        
                        # Record in database
                        with sqlite3.connect(STORAGE_DB) as conn:
                            cursor = conn.cursor()
                            cursor.execute('''
                                INSERT INTO directory_history 
                                (path, size_bytes, file_count, timestamp, scan_duration_ms)
                                VALUES (?, ?, ?, ?, ?)
                            ''', (dir_path, size_bytes, file_count, datetime.now(), scan_duration_ms))
                            conn.commit()
                        
                        # Check for rapid growth
                        growth_rate = self.calculate_growth_rate(dir_path)
                        if growth_rate and growth_rate > self.config['thresholds']['rapid_growth_mb']:
                            self.handle_runaway_storage(dir_path, growth_rate)
                        
                        # Check directory size limit
                        size_gb = size_bytes / 1_000_000_000
                        if size_gb > self.config['thresholds']['directory_limit_gb']:
                            self.logger.warning(f"Directory size limit exceeded: {dir_path} ({size_gb:.1f}GB)")
                            
                            # Auto-remediate if configured
                            if self.config['remediation']['auto_remediate']:
                                self.auto_remediate_large_directory(dir_path, size_gb)
                        
                    except Exception as e:
                        self.logger.error(f"Error monitoring directory {dir_path}: {e}")
                
                # Sleep until next scan
                time.sleep(self.config['thresholds']['scan_interval_seconds'])
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                time.sleep(60)  # Wait before retrying
        
        self.logger.info("Storage monitoring loop stopped")
    
    def auto_remediate_large_directory(self, dir_path: str, size_gb: float):
        """Auto-remediate a directory that's too large"""
        self.logger.info(f"Auto-remediating large directory: {dir_path} ({size_gb:.1f}GB)")
        
        remediation_actions = []
        
        try:
            # Find and handle largest files
            large_files = self.find_largest_files(dir_path, limit=5)
            for file_path, file_size in large_files:
                if file_size > 50_000_000:  # > 50MB
                    self.auto_remediate_large_file(file_path, file_size)
                    remediation_actions.append(f"remediated_{os.path.basename(file_path)}")
            
            # If it's a logs directory, compress old logs
            if 'log' in dir_path.lower():
                self.compress_old_logs(dir_path)
                remediation_actions.append("compressed_logs")
            
            self.log_remediation("auto_remediate_large_directory", dir_path, remediation_actions)
            
        except Exception as e:
            self.logger.error(f"Auto-remediation failed for directory {dir_path}: {e}")

# Initialize the monitor
storage_monitor = StorageMonitor()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    global monitoring_thread, monitoring_active
    
    # Startup
    monitoring_active = True
    monitoring_thread = threading.Thread(target=storage_monitor.monitor_loop, daemon=True)
    monitoring_thread.start()
    storage_monitor.logger.info("Storage monitoring started")
    
    yield
    
    # Shutdown
    monitoring_active = False
    if monitoring_thread and monitoring_thread.is_alive():
        monitoring_thread.join(timeout=10)
    storage_monitor.logger.info("Storage monitoring stopped")

# FastAPI app
app = FastAPI(
    title="Automated Storage Monitoring System",
    description="Prevents storage disasters like the 598GB checkpoint bloat",
    version="1.0.0",
    lifespan=lifespan
)

# Pydantic models
class MonitoringStatus(BaseModel):
    active: bool
    last_scan: Optional[str]
    directories_monitored: int
    alerts_active: int
    disk_usage_percent: float
    total_size_monitored_gb: float

class StorageAlert(BaseModel):
    path: str
    alert_type: str
    severity: str
    message: str
    timestamp: str

class RemediationRequest(BaseModel):
    path: str
    action: str
    confirm: bool = False

# API Routes
@app.get("/")
async def root():
    return {
        "message": "Automated Storage Monitoring and Remediation System",
        "version": "1.0.0",
        "status": "active" if monitoring_active else "inactive"
    }

@app.get("/status", response_model=MonitoringStatus)
async def get_monitoring_status():
    """Get current monitoring status"""
    try:
        with sqlite3.connect(STORAGE_DB) as conn:
            cursor = conn.cursor()
            
            # Get latest system metrics
            cursor.execute('''
                SELECT disk_usage_percent FROM system_metrics 
                ORDER BY timestamp DESC LIMIT 1
            ''')
            disk_result = cursor.fetchone()
            disk_usage_percent = disk_result[0] if disk_result else 0
            
            # Count active alerts
            cursor.execute('''
                SELECT COUNT(*) FROM growth_alerts WHERE resolved = FALSE
            ''')
            alerts_active = cursor.fetchone()[0]
            
            # Calculate total size being monitored
            cursor.execute('''
                SELECT SUM(size_bytes) FROM directory_history 
                WHERE timestamp > datetime('now', '-1 hour')
                GROUP BY path
            ''')
            size_results = cursor.fetchall()
            total_size_gb = sum(result[0] for result in size_results) / 1_000_000_000 if size_results else 0
        
        directories_monitored = len(storage_monitor.scan_directories())
        
        return MonitoringStatus(
            active=monitoring_active,
            last_scan=datetime.now().isoformat() if monitoring_active else None,
            directories_monitored=directories_monitored,
            alerts_active=alerts_active,
            disk_usage_percent=disk_usage_percent,
            total_size_monitored_gb=total_size_gb
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")

@app.get("/alerts")
async def get_recent_alerts():
    """Get recent storage alerts"""
    try:
        with sqlite3.connect(STORAGE_DB) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT path, growth_rate_mb, alert_time, resolved
                FROM growth_alerts 
                ORDER BY alert_time DESC LIMIT 20
            ''')
            
            alerts = []
            for row in cursor.fetchall():
                path, growth_rate, alert_time, resolved = row
                alerts.append({
                    "path": path,
                    "alert_type": "rapid_growth",
                    "severity": "critical" if growth_rate > 500 else "warning",
                    "message": f"Rapid growth: {growth_rate}MB per scan interval",
                    "timestamp": alert_time,
                    "resolved": bool(resolved)
                })
            
            return {"alerts": alerts}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get alerts: {str(e)}")

@app.get("/large-files")
async def get_large_files():
    """Get list of detected large files"""
    try:
        with sqlite3.connect(STORAGE_DB) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT path, size_bytes, detected_time, remediated
                FROM large_files 
                ORDER BY size_bytes DESC LIMIT 50
            ''')
            
            files = []
            for row in cursor.fetchall():
                path, size_bytes, detected_time, remediated = row
                files.append({
                    "path": path,
                    "size_mb": size_bytes / 1_000_000,
                    "size_gb": size_bytes / 1_000_000_000,
                    "detected_time": detected_time,
                    "remediated": bool(remediated)
                })
            
            return {"large_files": files}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get large files: {str(e)}")

@app.post("/emergency-alert")
async def receive_emergency_alert(alert_data: dict):
    """Receive emergency alerts from other systems"""
    storage_monitor.logger.critical(f"External emergency alert received: {alert_data}")
    return {"message": "Alert received", "status": "processing"}

@app.post("/remediate")
async def manual_remediation(request: RemediationRequest):
    """Manually trigger remediation actions"""
    if not request.confirm:
        return {"message": "Remediation requires confirmation", "action": "none"}
    
    try:
        if request.action == "emergency_cleanup":
            storage_monitor.emergency_disk_cleanup()
            return {"message": "Emergency cleanup initiated", "action": "emergency_cleanup"}
        
        elif request.action == "quarantine_large_files":
            large_files = storage_monitor.find_largest_files(request.path, limit=5)
            quarantined = []
            for file_path, file_size in large_files:
                if storage_monitor.quarantine_file(file_path, file_size):
                    quarantined.append(file_path)
            
            return {"message": f"Quarantined {len(quarantined)} files", "files": quarantined}
        
        else:
            raise HTTPException(status_code=400, detail="Unknown remediation action")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Remediation failed: {str(e)}")

@app.get("/config")
async def get_config():
    """Get current monitoring configuration"""
    return storage_monitor.config

@app.post("/config")
async def update_config(new_config: dict):
    """Update monitoring configuration"""
    try:
        # Merge with existing config
        storage_monitor.config = {**storage_monitor.config, **new_config}
        
        # Save to file
        with open(storage_monitor.config_path, 'w') as f:
            json.dump(storage_monitor.config, f, indent=2)
        
        return {"message": "Configuration updated", "config": storage_monitor.config}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Config update failed: {str(e)}")

@app.get("/metrics")
async def get_system_metrics():
    """Get system resource metrics"""
    try:
        with sqlite3.connect(STORAGE_DB) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT timestamp, disk_usage_percent, cpu_percent, memory_percent
                FROM system_metrics 
                ORDER BY timestamp DESC LIMIT 100
            ''')
            
            metrics = []
            for row in cursor.fetchall():
                timestamp, disk_usage, cpu_usage, memory_usage = row
                metrics.append({
                    "timestamp": timestamp,
                    "disk_usage_percent": disk_usage,
                    "cpu_percent": cpu_usage,
                    "memory_percent": memory_usage
                })
            
            return {"metrics": metrics}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8490)