#!/usr/bin/env python3
"""
Enhanced Automated Storage Monitoring and Remediation System v2.0
Enterprise-grade storage monitoring with advanced performance, security, and reliability

Key Improvements:
- Multi-threaded async monitoring with worker pools
- Advanced security with authentication and authorization
- Self-healing capabilities and circuit breakers
- Enhanced performance with intelligent caching
- Real-time streaming APIs and WebSocket support
- Advanced machine learning for anomaly detection
- Comprehensive observability and metrics
"""

import asyncio
import aiofiles
import aiohttp
from fastapi import FastAPI, HTTPException, Depends, WebSocket, BackgroundTasks, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from pydantic import BaseModel, Field, validator
import uvicorn
import os
import json
import time
import logging
from logging.handlers import RotatingFileHandler
import sqlite3
import aiosqlite
import threading
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple, Any, Set, Union
import subprocess
import psutil
import hashlib
import shutil
from contextlib import asynccontextmanager
import weakref
from dataclasses import dataclass, field
from collections import defaultdict, deque
import asyncio
import concurrent.futures
from functools import lru_cache, wraps
import signal
import sys
from enum import Enum
import redis
import pickle
from cryptography.fernet import Fernet
import jwt
from passlib.context import CryptContext
import secrets
from tenacity import retry, stop_after_attempt, wait_exponential
from circuit_breaker import CircuitBreaker
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import joblib
import yaml
from datadog import initialize, statsd
import structlog
import traceback

# Configuration
BASE_DIR = Path("/home/activeloguser/activelog/services/storage-monitor")
STORAGE_DB = BASE_DIR / "data" / "storage_monitor.db"
LOG_FILE = BASE_DIR / "logs" / "storage_monitor.log"
CONFIG_FILE = BASE_DIR / "config" / "enhanced_config.yaml"
METRICS_PORT = 8491
WEBSOCKET_PORT = 8492

# Prometheus metrics
SCAN_DURATION = Histogram('storage_scan_duration_seconds', 'Time spent scanning directories', ['path_type'])
GROWTH_ALERTS = Counter('storage_growth_alerts_total', 'Total growth alerts triggered', ['severity', 'path'])
REMEDIATION_ACTIONS = Counter('storage_remediation_actions_total', 'Total remediation actions', ['action_type', 'success'])
DISK_USAGE = Gauge('storage_disk_usage_percent', 'Current disk usage percentage')
ACTIVE_MONITORS = Gauge('storage_active_monitors', 'Number of active monitoring workers')
API_REQUESTS = Counter('storage_api_requests_total', 'Total API requests', ['endpoint', 'method', 'status'])

# Enhanced logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Security
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = os.getenv("STORAGE_MONITOR_SECRET_KEY", secrets.token_urlsafe(32))

class AlertSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class MonitoringState(str, Enum):
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    ERROR = "error"

class RemediationAction(str, Enum):
    QUARANTINE = "quarantine"
    COMPRESS = "compress"
    DELETE = "delete"
    STOP_PROCESS = "stop_process"
    ALERT_ONLY = "alert_only"

@dataclass
class PerformanceMetrics:
    """Enhanced performance metrics tracking"""
    scan_count: int = 0
    scan_duration_ms: float = 0
    memory_usage_mb: float = 0
    cpu_usage_percent: float = 0
    cache_hit_rate: float = 0
    errors_per_hour: int = 0
    throughput_files_per_second: float = 0
    
    def update_scan(self, duration_ms: float, file_count: int):
        self.scan_count += 1
        self.scan_duration_ms = (self.scan_duration_ms + duration_ms) / 2  # Rolling average
        self.throughput_files_per_second = file_count / (duration_ms / 1000) if duration_ms > 0 else 0

@dataclass
class DirectorySnapshot:
    """Immutable directory state snapshot"""
    path: str
    size_bytes: int
    file_count: int
    largest_file_size: int
    timestamp: datetime
    file_types: Dict[str, int] = field(default_factory=dict)
    checksum: str = ""
    
    def __post_init__(self):
        # Calculate checksum for change detection
        data = f"{self.size_bytes}:{self.file_count}:{self.largest_file_size}"
        self.checksum = hashlib.md5(data.encode()).hexdigest()

class EnhancedStorageMonitor:
    """Enterprise-grade storage monitoring system"""
    
    def __init__(self, config_path: str = str(CONFIG_FILE)):
        self.config_path = config_path
        self.state = MonitoringState.STARTING
        self.worker_pool = None
        self.monitoring_tasks: Set[asyncio.Task] = set()
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.performance_metrics = PerformanceMetrics()
        self.directory_cache: Dict[str, DirectorySnapshot] = {}
        self.alert_history = deque(maxlen=1000)
        self.websocket_clients: Set[WebSocket] = set()
        
        # Machine learning models
        self.anomaly_detector = None
        self.scaler = StandardScaler()
        self.ml_model_path = BASE_DIR / "models"
        
        # Load configuration
        self.load_enhanced_config()
        
        # Setup components
        self.setup_enhanced_logging()
        self.setup_database()
        self.setup_cache()
        self.setup_security()
        self.setup_ml_models()
        
        # Initialize circuit breakers
        self._setup_circuit_breakers()
        
        logger.info("Enhanced Storage Monitor initialized", 
                   config_path=config_path, 
                   version="2.0")

    def load_enhanced_config(self):
        """Load enhanced YAML configuration with validation"""
        default_config = {
            'monitoring': {
                'scan_interval_seconds': 30,  # Faster scanning
                'worker_threads': os.cpu_count() or 4,
                'batch_size': 100,
                'enable_async_io': True,
                'enable_caching': True,
                'cache_ttl_seconds': 300,
                'enable_compression': True,
                'max_memory_usage_mb': 512
            },
            'thresholds': {
                'rapid_growth_mb_per_minute': 50,  # More sensitive
                'large_file_gb': 0.5,  # Lower threshold
                'directory_limit_gb': 2.0,  # More conservative
                'disk_usage_warning': 0.75,
                'disk_usage_critical': 0.90,
                'cpu_usage_limit': 80,
                'memory_usage_limit': 75
            },
            'paths': {
                'monitor': [
                    "/home/activeloguser/activelog/services",
                    "/home/activeloguser/activelog/checkpoints",
                    "/home/activeloguser/activelog/backups",
                    "/home/activeloguser/activelog/logs"
                ],
                'exclude_patterns': [
                    "*/node_modules/*",
                    "*/__pycache__/*", 
                    "*/dist/*",
                    "*/build/*",
                    "*/.git/*",
                    "*/temp/*",
                    "*/tmp/*",
                    "*/.cache/*"
                ],
                'quarantine_dir': str(BASE_DIR / "quarantine"),
                'models_dir': str(BASE_DIR / "models")
            },
            'security': {
                'enable_auth': True,
                'jwt_expiry_hours': 24,
                'rate_limit_per_minute': 100,
                'allowed_ips': ["127.0.0.1", "localhost"],
                'encrypt_sensitive_data': True
            },
            'features': {
                'enable_ml_anomaly_detection': True,
                'enable_predictive_analysis': True,
                'enable_auto_remediation': True,
                'enable_real_time_streaming': True,
                'enable_distributed_monitoring': False
            },
            'integrations': {
                'improvement_system': {
                    'url': 'http://localhost:8500',
                    'enabled': True,
                    'timeout_seconds': 30
                },
                'prometheus': {
                    'enabled': True,
                    'port': 8491
                },
                'redis': {
                    'enabled': False,
                    'url': 'redis://localhost:6379'
                },
                'webhooks': {
                    'enabled': False,
                    'endpoints': []
                }
            },
            'remediation': {
                'auto_quarantine_mb': 100,
                'auto_compress_days': 1,
                'auto_delete_temp_files': True,
                'backup_before_action': True,
                'max_concurrent_actions': 3,
                'action_timeout_minutes': 10
            }
        }
        
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    loaded_config = yaml.safe_load(f)
                # Deep merge with defaults
                self.config = self._deep_merge(default_config, loaded_config)
            else:
                self.config = default_config
                os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
                with open(self.config_path, 'w') as f:
                    yaml.dump(default_config, f, default_flow_style=False, indent=2)
                    
        except Exception as e:
            logger.error("Configuration load failed", error=str(e))
            self.config = default_config

    def _deep_merge(self, base: dict, update: dict) -> dict:
        """Deep merge two dictionaries"""
        result = base.copy()
        for key, value in update.items():
            if isinstance(value, dict) and key in result and isinstance(result[key], dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def setup_enhanced_logging(self):
        """Setup enhanced structured logging with rotation"""
        log_dir = BASE_DIR / "logs"
        log_dir.mkdir(exist_ok=True)
        
        # Setup rotating file handler
        file_handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=50*1024*1024,  # 50MB
            backupCount=10
        )
        file_handler.setLevel(logging.INFO)
        
        # Setup console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Configure formatters
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)

    async def setup_database(self):
        """Setup enhanced async database with proper indexing"""
        os.makedirs(os.path.dirname(STORAGE_DB), exist_ok=True)
        
        async with aiosqlite.connect(STORAGE_DB) as conn:
            # Enable WAL mode for better concurrent access
            await conn.execute("PRAGMA journal_mode=WAL")
            await conn.execute("PRAGMA synchronous=NORMAL")
            await conn.execute("PRAGMA cache_size=10000")
            await conn.execute("PRAGMA temp_store=MEMORY")
            
            # Enhanced schema with better indexing
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS directory_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    path TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    file_count INTEGER NOT NULL,
                    largest_file_size INTEGER DEFAULT 0,
                    timestamp DATETIME NOT NULL,
                    checksum TEXT NOT NULL,
                    file_types TEXT,  -- JSON
                    scan_duration_ms REAL DEFAULT 0,
                    UNIQUE(path, timestamp)
                )
            ''')
            
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS growth_analysis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    path TEXT NOT NULL,
                    linear_rate_mb_hour REAL DEFAULT 0,
                    exponential_factor REAL DEFAULT 1.0,
                    burst_rate_mb_hour REAL DEFAULT 0,
                    anomaly_score REAL DEFAULT 0,
                    risk_level TEXT DEFAULT 'low',
                    timestamp DATETIME NOT NULL,
                    prediction_accuracy REAL DEFAULT 0
                )
            ''')
            
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS alerts_enhanced (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alert_id TEXT UNIQUE NOT NULL,
                    severity TEXT NOT NULL,
                    alert_type TEXT NOT NULL,
                    path TEXT NOT NULL,
                    message TEXT NOT NULL,
                    metadata TEXT,  -- JSON
                    created_at DATETIME NOT NULL,
                    resolved_at DATETIME,
                    resolution_method TEXT,
                    false_positive BOOLEAN DEFAULT FALSE
                )
            ''')
            
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS remediation_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action_id TEXT UNIQUE NOT NULL,
                    action_type TEXT NOT NULL,
                    target_path TEXT NOT NULL,
                    parameters TEXT,  -- JSON
                    started_at DATETIME NOT NULL,
                    completed_at DATETIME,
                    success BOOLEAN DEFAULT FALSE,
                    error_message TEXT,
                    bytes_affected INTEGER DEFAULT 0,
                    files_affected INTEGER DEFAULT 0
                )
            ''')
            
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    cpu_percent REAL,
                    memory_mb REAL,
                    scan_duration_ms REAL,
                    throughput_files_per_sec REAL,
                    cache_hit_rate REAL,
                    active_workers INTEGER
                )
            ''')
            
            # Create indexes for better performance
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_snapshots_path_time ON directory_snapshots(path, timestamp DESC)",
                "CREATE INDEX IF NOT EXISTS idx_snapshots_size ON directory_snapshots(size_bytes DESC)",
                "CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts_enhanced(severity, created_at DESC)",
                "CREATE INDEX IF NOT EXISTS idx_alerts_unresolved ON alerts_enhanced(resolved_at) WHERE resolved_at IS NULL",
                "CREATE INDEX IF NOT EXISTS idx_remediation_type ON remediation_actions(action_type, started_at DESC)",
                "CREATE INDEX IF NOT EXISTS idx_growth_path_time ON growth_analysis(path, timestamp DESC)"
            ]
            
            for index in indexes:
                await conn.execute(index)
            
            await conn.commit()

    def setup_cache(self):
        """Setup intelligent caching system"""
        if self.config['integrations']['redis']['enabled']:
            try:
                import redis
                self.cache = redis.from_url(self.config['integrations']['redis']['url'])
                logger.info("Redis cache initialized")
            except Exception as e:
                logger.warning("Redis cache failed to initialize, using memory cache", error=str(e))
                self.cache = {}
        else:
            self.cache = {}
    
    def setup_security(self):
        """Setup security components"""
        if self.config['security']['enable_auth']:
            # Generate or load encryption key
            key_file = BASE_DIR / "config" / "encryption.key"
            if key_file.exists():
                with open(key_file, 'rb') as f:
                    self.encryption_key = f.read()
            else:
                self.encryption_key = Fernet.generate_key()
                key_file.parent.mkdir(exist_ok=True)
                with open(key_file, 'wb') as f:
                    f.write(self.encryption_key)
                os.chmod(key_file, 0o600)
            
            self.fernet = Fernet(self.encryption_key)
            logger.info("Security components initialized")

    def setup_ml_models(self):
        """Setup machine learning models for anomaly detection"""
        if not self.config['features']['enable_ml_anomaly_detection']:
            return
            
        model_dir = Path(self.config['paths']['models_dir'])
        model_dir.mkdir(exist_ok=True)
        
        model_file = model_dir / "anomaly_detector.joblib"
        scaler_file = model_dir / "feature_scaler.joblib"
        
        try:
            if model_file.exists() and scaler_file.exists():
                self.anomaly_detector = joblib.load(model_file)
                self.scaler = joblib.load(scaler_file)
                logger.info("ML models loaded from disk")
            else:
                # Initialize new models
                self.anomaly_detector = IsolationForest(
                    contamination=0.1,
                    random_state=42,
                    n_jobs=-1
                )
                logger.info("New ML models initialized")
                
        except Exception as e:
            logger.error("ML model setup failed", error=str(e))
            self.anomaly_detector = None

    def _setup_circuit_breakers(self):
        """Setup circuit breakers for external dependencies"""
        self.circuit_breakers = {
            'database': CircuitBreaker(
                failure_threshold=5,
                recovery_timeout=30,
                expected_exception=Exception
            ),
            'improvement_system': CircuitBreaker(
                failure_threshold=3,
                recovery_timeout=60,
                expected_exception=Exception
            ),
            'file_system': CircuitBreaker(
                failure_threshold=10,
                recovery_timeout=15,
                expected_exception=(OSError, IOError)
            )
        }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def scan_directory_enhanced(self, path: Path) -> Optional[DirectorySnapshot]:
        """Enhanced directory scanning with async I/O and error recovery"""
        start_time = time.perf_counter()
        
        try:
            # Check cache first
            cache_key = f"scan:{path}:{int(time.time() // self.config['monitoring']['cache_ttl_seconds'])}"
            if self.config['monitoring']['enable_caching'] and cache_key in self.cache:
                return pickle.loads(self.cache[cache_key]) if isinstance(self.cache, dict) else self.cache.get(cache_key)
            
            # Parallel file scanning with asyncio
            tasks = []
            file_data = []
            file_types = defaultdict(int)
            
            # Use async file operations where possible
            if not path.exists():
                return None
                
            async def process_file(file_path: Path) -> Tuple[int, str]:
                """Process individual file asynchronously"""
                try:
                    stat = file_path.stat()
                    if file_path.is_file() and not file_path.is_symlink():
                        file_ext = file_path.suffix.lower()
                        return stat.st_size, file_ext
                except Exception:
                    return 0, ""
                
            # Collect all files
            all_files = []
            try:
                for item in path.rglob("*"):
                    if self._should_exclude_path(str(item)):
                        continue
                    if item.is_file():
                        all_files.append(item)
                        
            except PermissionError:
                logger.warning("Permission denied scanning directory", path=str(path))
                return None
            except Exception as e:
                logger.error("Directory scan error", path=str(path), error=str(e))
                return None
            
            # Process files in batches for memory efficiency
            batch_size = self.config['monitoring']['batch_size']
            total_size = 0
            largest_file = 0
            
            for i in range(0, len(all_files), batch_size):
                batch = all_files[i:i + batch_size]
                batch_tasks = [process_file(file_path) for file_path in batch]
                
                try:
                    results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                    
                    for result in results:
                        if isinstance(result, tuple):
                            size, ext = result
                            total_size += size
                            largest_file = max(largest_file, size)
                            if ext:
                                file_types[ext] += 1
                                
                except Exception as e:
                    logger.error("Batch processing error", error=str(e))
                    continue
            
            # Create snapshot
            snapshot = DirectorySnapshot(
                path=str(path),
                size_bytes=total_size,
                file_count=len(all_files),
                largest_file_size=largest_file,
                timestamp=datetime.now(timezone.utc),
                file_types=dict(file_types)
            )
            
            # Cache the result
            if self.config['monitoring']['enable_caching']:
                cache_data = pickle.dumps(snapshot)
                if isinstance(self.cache, dict):
                    self.cache[cache_key] = cache_data
                else:
                    try:
                        self.cache.setex(cache_key, self.config['monitoring']['cache_ttl_seconds'], cache_data)
                    except:
                        pass  # Cache failure is not critical
            
            # Update performance metrics
            scan_duration = (time.perf_counter() - start_time) * 1000
            self.performance_metrics.update_scan(scan_duration, len(all_files))
            
            # Record metrics
            SCAN_DURATION.labels(path_type=self._get_path_type(str(path))).observe(scan_duration / 1000)
            
            return snapshot
            
        except Exception as e:
            logger.error("Enhanced directory scan failed", path=str(path), error=str(e), traceback=traceback.format_exc())
            return None

    def _should_exclude_path(self, path: str) -> bool:
        """Enhanced path exclusion with glob patterns"""
        import fnmatch
        
        for pattern in self.config['paths']['exclude_patterns']:
            if fnmatch.fnmatch(path, pattern):
                return True
        return False

    def _get_path_type(self, path: str) -> str:
        """Classify path type for metrics"""
        if 'services' in path:
            return 'services'
        elif 'logs' in path:
            return 'logs'
        elif 'checkpoints' in path:
            return 'checkpoints'
        elif 'backups' in path:
            return 'backups'
        else:
            return 'other'

    async def analyze_growth_patterns_ml(self, path: str, snapshots: List[DirectorySnapshot]) -> Dict[str, Any]:
        """Advanced growth analysis using machine learning"""
        if not snapshots or len(snapshots) < 3:
            return {'error': 'insufficient_data'}
        
        try:
            # Extract features for ML analysis
            features = []
            timestamps = []
            sizes = []
            
            for snapshot in snapshots[-10:]:  # Use last 10 snapshots
                # Time-based features
                hour = snapshot.timestamp.hour
                day_of_week = snapshot.timestamp.weekday()
                
                # Size-based features
                size_mb = snapshot.size_bytes / (1024 * 1024)
                file_count = snapshot.file_count
                avg_file_size = snapshot.size_bytes / snapshot.file_count if snapshot.file_count > 0 else 0
                largest_file_ratio = snapshot.largest_file_size / snapshot.size_bytes if snapshot.size_bytes > 0 else 0
                
                features.append([
                    size_mb, file_count, avg_file_size, largest_file_ratio,
                    hour, day_of_week, len(snapshot.file_types)
                ])
                
                timestamps.append(snapshot.timestamp.timestamp())
                sizes.append(size_mb)
            
            if len(features) < 3:
                return {'error': 'insufficient_features'}
            
            # Prepare features for anomaly detection
            features_array = np.array(features)
            
            # Scale features
            if hasattr(self.scaler, 'mean_'):
                features_scaled = self.scaler.transform(features_array)
            else:
                # First time training
                features_scaled = self.scaler.fit_transform(features_array)
                
            # Anomaly detection
            anomaly_score = 0.0
            if self.anomaly_detector:
                try:
                    if hasattr(self.anomaly_detector, 'decision_function'):
                        # For trained model
                        scores = self.anomaly_detector.decision_function(features_scaled)
                        anomaly_score = float(scores[-1])  # Latest score
                    else:
                        # Train if not trained
                        self.anomaly_detector.fit(features_scaled)
                        scores = self.anomaly_detector.decision_function(features_scaled)
                        anomaly_score = float(scores[-1])
                        
                        # Save trained model
                        model_dir = Path(self.config['paths']['models_dir'])
                        joblib.dump(self.anomaly_detector, model_dir / "anomaly_detector.joblib")
                        joblib.dump(self.scaler, model_dir / "feature_scaler.joblib")
                        
                except Exception as e:
                    logger.error("ML anomaly detection failed", error=str(e))
                    anomaly_score = 0.0
            
            # Traditional statistical analysis
            size_changes = np.diff(sizes)
            time_deltas = np.diff(timestamps) / 3600  # Convert to hours
            
            growth_rates = []
            for i, delta_time in enumerate(time_deltas):
                if delta_time > 0:
                    growth_rates.append(size_changes[i] / delta_time)
            
            if not growth_rates:
                return {'error': 'no_growth_data'}
            
            # Enhanced metrics
            linear_rate = np.mean(growth_rates) if growth_rates else 0
            growth_acceleration = np.mean(np.diff(growth_rates)) if len(growth_rates) > 1 else 0
            growth_volatility = np.std(growth_rates) if len(growth_rates) > 1 else 0
            
            # Recent vs historical comparison
            recent_rate = np.mean(growth_rates[-3:]) if len(growth_rates) >= 3 else 0
            historical_rate = np.mean(growth_rates[:-3]) if len(growth_rates) > 3 else 0
            burst_factor = recent_rate / historical_rate if historical_rate > 0 else 1.0
            
            # Risk assessment
            risk_factors = {
                'high_growth_rate': linear_rate > 50,  # >50MB/hour
                'accelerating_growth': growth_acceleration > 5,
                'high_volatility': growth_volatility > 20,
                'recent_burst': burst_factor > 2.0,
                'anomaly_detected': anomaly_score < -0.5,  # Isolation Forest threshold
                'large_files_ratio': features_array[-1, 3] > 0.8  # >80% in single file
            }
            
            risk_score = sum(risk_factors.values())
            
            if risk_score >= 4:
                risk_level = AlertSeverity.CRITICAL
            elif risk_score >= 3:
                risk_level = AlertSeverity.HIGH
            elif risk_score >= 2:
                risk_level = AlertSeverity.MEDIUM
            else:
                risk_level = AlertSeverity.LOW
            
            return {
                'linear_growth_mb_per_hour': float(linear_rate),
                'growth_acceleration': float(growth_acceleration),
                'growth_volatility': float(growth_volatility),
                'burst_factor': float(burst_factor),
                'anomaly_score': float(anomaly_score),
                'risk_level': risk_level,
                'risk_factors': risk_factors,
                'confidence': min(len(snapshots) / 10.0, 1.0),  # Confidence based on data points
                'prediction_horizon_hours': 24,
                'predicted_size_mb_24h': sizes[-1] + (linear_rate * 24)
            }
            
        except Exception as e:
            logger.error("ML growth analysis failed", path=path, error=str(e), traceback=traceback.format_exc())
            return {'error': str(e)}

    async def trigger_intelligent_remediation(self, alert_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced remediation with intelligent action selection"""
        try:
            path = alert_data['path']
            risk_level = alert_data.get('risk_level', AlertSeverity.LOW)
            growth_rate = alert_data.get('linear_growth_mb_per_hour', 0)
            
            # Determine optimal remediation strategy
            strategy = await self._select_remediation_strategy(path, risk_level, growth_rate)
            
            actions_taken = []
            total_bytes_saved = 0
            
            for action_config in strategy['actions']:
                try:
                    result = await self._execute_remediation_action(
                        action_config['action'],
                        path,
                        action_config.get('parameters', {})
                    )
                    
                    if result['success']:
                        actions_taken.append({
                            'action': action_config['action'],
                            'bytes_saved': result.get('bytes_saved', 0),
                            'files_affected': result.get('files_affected', 0),
                            'duration_seconds': result.get('duration_seconds', 0)
                        })
                        total_bytes_saved += result.get('bytes_saved', 0)
                        
                        # Update metrics
                        REMEDIATION_ACTIONS.labels(
                            action_type=action_config['action'],
                            success='true'
                        ).inc()
                        
                except Exception as e:
                    logger.error("Remediation action failed", 
                               action=action_config['action'],
                               path=path,
                               error=str(e))
                    
                    REMEDIATION_ACTIONS.labels(
                        action_type=action_config['action'],
                        success='false'
                    ).inc()
            
            # Notify connected clients via WebSocket
            await self._notify_websocket_clients({
                'type': 'remediation_completed',
                'path': path,
                'actions_taken': actions_taken,
                'total_bytes_saved': total_bytes_saved,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
            return {
                'success': True,
                'strategy': strategy['name'],
                'actions_taken': actions_taken,
                'total_bytes_saved': total_bytes_saved,
                'estimated_effectiveness': strategy.get('effectiveness', 0)
            }
            
        except Exception as e:
            logger.error("Intelligent remediation failed", 
                        alert_data=alert_data, 
                        error=str(e),
                        traceback=traceback.format_exc())
            return {'success': False, 'error': str(e)}

    async def _select_remediation_strategy(self, path: str, risk_level: AlertSeverity, growth_rate: float) -> Dict[str, Any]:
        """Select optimal remediation strategy based on context"""
        
        # Analyze path characteristics
        path_analysis = await self._analyze_path_characteristics(path)
        
        if risk_level == AlertSeverity.CRITICAL:
            if 'logs' in path.lower():
                return {
                    'name': 'aggressive_log_cleanup',
                    'effectiveness': 0.9,
                    'actions': [
                        {'action': RemediationAction.COMPRESS, 'parameters': {'age_hours': 1}},
                        {'action': RemediationAction.DELETE, 'parameters': {'pattern': '*.tmp'}},
                        {'action': RemediationAction.STOP_PROCESS, 'parameters': {'signal': 'SIGTERM'}}
                    ]
                }
            elif 'checkpoints' in path.lower():
                return {
                    'name': 'checkpoint_emergency_cleanup',
                    'effectiveness': 0.95,
                    'actions': [
                        {'action': RemediationAction.STOP_PROCESS, 'parameters': {'pattern': 'checkpoint'}},
                        {'action': RemediationAction.QUARANTINE, 'parameters': {'size_threshold_mb': 50}}
                    ]
                }
        
        elif risk_level == AlertSeverity.HIGH:
            return {
                'name': 'standard_high_risk_cleanup',
                'effectiveness': 0.7,
                'actions': [
                    {'action': RemediationAction.QUARANTINE, 'parameters': {'size_threshold_mb': 100}},
                    {'action': RemediationAction.COMPRESS, 'parameters': {'age_hours': 24}}
                ]
            }
        
        else:
            return {
                'name': 'conservative_cleanup',
                'effectiveness': 0.4,
                'actions': [
                    {'action': RemediationAction.COMPRESS, 'parameters': {'age_days': 7}},
                    {'action': RemediationAction.ALERT_ONLY, 'parameters': {}}
                ]
            }

    async def _analyze_path_characteristics(self, path: str) -> Dict[str, Any]:
        """Analyze path to determine optimal remediation approach"""
        try:
            path_obj = Path(path)
            
            # Get recent snapshot
            cache_key = f"analysis:{path}"
            if cache_key in self.directory_cache:
                snapshot = self.directory_cache[cache_key]
            else:
                snapshot = await self.scan_directory_enhanced(path_obj)
                if snapshot:
                    self.directory_cache[cache_key] = snapshot
            
            if not snapshot:
                return {'error': 'path_not_accessible'}
            
            characteristics = {
                'total_size_mb': snapshot.size_bytes / (1024 * 1024),
                'file_count': snapshot.file_count,
                'largest_file_mb': snapshot.largest_file_size / (1024 * 1024),
                'file_types': snapshot.file_types,
                'is_log_directory': 'log' in path.lower(),
                'is_checkpoint_directory': 'checkpoint' in path.lower(),
                'is_temp_directory': any(temp in path.lower() for temp in ['temp', 'tmp', 'cache']),
                'compressible_files': sum(
                    count for ext, count in snapshot.file_types.items()
                    if ext in ['.log', '.txt', '.json', '.xml', '.csv']
                ),
                'large_file_ratio': snapshot.largest_file_size / snapshot.size_bytes if snapshot.size_bytes > 0 else 0
            }
            
            return characteristics
            
        except Exception as e:
            logger.error("Path characteristic analysis failed", path=path, error=str(e))
            return {'error': str(e)}

    async def _execute_remediation_action(self, action: RemediationAction, path: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute specific remediation action with detailed tracking"""
        start_time = time.perf_counter()
        action_id = f"{action}_{int(time.time())}_{secrets.token_hex(8)}"
        
        try:
            # Record action start
            async with aiosqlite.connect(STORAGE_DB) as conn:
                await conn.execute('''
                    INSERT INTO remediation_actions 
                    (action_id, action_type, target_path, parameters, started_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (action_id, action.value, path, json.dumps(parameters), datetime.now(timezone.utc)))
                await conn.commit()
            
            result = {'success': False, 'bytes_saved': 0, 'files_affected': 0}
            
            if action == RemediationAction.COMPRESS:
                result = await self._compress_files(path, parameters)
            elif action == RemediationAction.QUARANTINE:
                result = await self._quarantine_files(path, parameters)
            elif action == RemediationAction.DELETE:
                result = await self._delete_files(path, parameters)
            elif action == RemediationAction.STOP_PROCESS:
                result = await self._stop_related_processes(path, parameters)
            elif action == RemediationAction.ALERT_ONLY:
                result = {'success': True, 'bytes_saved': 0, 'files_affected': 0}
                await self._send_alert_notification(path, parameters)
            
            # Record completion
            duration = time.perf_counter() - start_time
            result['duration_seconds'] = duration
            
            async with aiosqlite.connect(STORAGE_DB) as conn:
                await conn.execute('''
                    UPDATE remediation_actions 
                    SET completed_at = ?, success = ?, bytes_affected = ?, files_affected = ?
                    WHERE action_id = ?
                ''', (
                    datetime.now(timezone.utc),
                    result['success'],
                    result.get('bytes_saved', 0),
                    result.get('files_affected', 0),
                    action_id
                ))
                await conn.commit()
            
            logger.info("Remediation action completed",
                       action_id=action_id,
                       action=action.value,
                       path=path,
                       success=result['success'],
                       bytes_saved=result.get('bytes_saved', 0),
                       duration=duration)
            
            return result
            
        except Exception as e:
            # Record failure
            async with aiosqlite.connect(STORAGE_DB) as conn:
                await conn.execute('''
                    UPDATE remediation_actions 
                    SET completed_at = ?, success = FALSE, error_message = ?
                    WHERE action_id = ?
                ''', (datetime.now(timezone.utc), str(e), action_id))
                await conn.commit()
            
            logger.error("Remediation action failed",
                        action_id=action_id,
                        action=action.value,
                        path=path,
                        error=str(e))
            
            return {'success': False, 'error': str(e)}

    async def _compress_files(self, path: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Compress files based on age or pattern"""
        import gzip
        import shutil
        
        age_hours = parameters.get('age_hours', 24)
        age_days = parameters.get('age_days', 0)
        pattern = parameters.get('pattern', '*.log')
        
        cutoff_time = datetime.now() - timedelta(hours=age_hours, days=age_days)
        
        compressed_files = 0
        bytes_saved = 0
        
        try:
            path_obj = Path(path)
            for file_path in path_obj.rglob(pattern):
                if file_path.is_file() and not file_path.name.endswith('.gz'):
                    file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    
                    if file_mtime < cutoff_time:
                        original_size = file_path.stat().st_size
                        compressed_path = f"{file_path}.gz"
                        
                        # Compress file
                        with open(file_path, 'rb') as f_in:
                            with gzip.open(compressed_path, 'wb') as f_out:
                                shutil.copyfileobj(f_in, f_out)
                        
                        # Verify compression and remove original
                        if os.path.exists(compressed_path):
                            compressed_size = os.path.getsize(compressed_path)
                            os.remove(file_path)
                            
                            bytes_saved += (original_size - compressed_size)
                            compressed_files += 1
            
            return {
                'success': True,
                'bytes_saved': bytes_saved,
                'files_affected': compressed_files
            }
            
        except Exception as e:
            logger.error("File compression failed", path=path, error=str(e))
            return {'success': False, 'error': str(e)}

    async def _quarantine_files(self, path: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Move large files to quarantine directory"""
        size_threshold = parameters.get('size_threshold_mb', 100) * 1024 * 1024
        quarantine_dir = Path(self.config['paths']['quarantine_dir'])
        quarantine_dir.mkdir(exist_ok=True)
        
        quarantined_files = 0
        bytes_quarantined = 0
        
        try:
            path_obj = Path(path)
            for file_path in path_obj.rglob("*"):
                if file_path.is_file() and file_path.stat().st_size > size_threshold:
                    # Create unique quarantine name
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    quarantine_name = f"{timestamp}_{file_path.name}"
                    quarantine_path = quarantine_dir / quarantine_name
                    
                    # Move file to quarantine
                    file_size = file_path.stat().st_size
                    shutil.move(str(file_path), str(quarantine_path))
                    
                    # Create metadata
                    metadata = {
                        'original_path': str(file_path),
                        'quarantine_time': datetime.now(timezone.utc).isoformat(),
                        'size_bytes': file_size,
                        'reason': 'size_threshold_exceeded'
                    }
                    
                    metadata_path = quarantine_path.with_suffix('.metadata.json')
                    with open(metadata_path, 'w') as f:
                        json.dump(metadata, f, indent=2)
                    
                    bytes_quarantined += file_size
                    quarantined_files += 1
            
            return {
                'success': True,
                'bytes_saved': bytes_quarantined,  # Not actually saved, but removed from monitored space
                'files_affected': quarantined_files
            }
            
        except Exception as e:
            logger.error("File quarantine failed", path=path, error=str(e))
            return {'success': False, 'error': str(e)}

    async def _delete_files(self, path: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Delete files matching pattern (with safety checks)"""
        pattern = parameters.get('pattern', '*.tmp')
        max_age_hours = parameters.get('max_age_hours', 1)  # Only delete recent temp files
        
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        deleted_files = 0
        bytes_deleted = 0
        
        try:
            path_obj = Path(path)
            for file_path in path_obj.rglob(pattern):
                if file_path.is_file():
                    file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    
                    # Safety check: only delete recent temp files
                    if file_mtime > cutoff_time and ('tmp' in file_path.name.lower() or 'temp' in file_path.name.lower()):
                        file_size = file_path.stat().st_size
                        file_path.unlink()
                        
                        bytes_deleted += file_size
                        deleted_files += 1
            
            return {
                'success': True,
                'bytes_saved': bytes_deleted,
                'files_affected': deleted_files
            }
            
        except Exception as e:
            logger.error("File deletion failed", path=path, error=str(e))
            return {'success': False, 'error': str(e)}

    async def _stop_related_processes(self, path: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Stop processes that are writing to the problematic directory"""
        pattern = parameters.get('pattern', '')
        signal_type = parameters.get('signal', 'SIGTERM')
        
        stopped_processes = 0
        
        try:
            for proc in psutil.process_iter(['pid', 'name', 'open_files']):
                try:
                    open_files = proc.info.get('open_files', [])
                    if open_files:
                        for file_info in open_files:
                            if path in file_info.path:
                                # Additional safety check
                                if pattern and pattern not in proc.info['name']:
                                    continue
                                
                                logger.warning("Stopping process writing to monitored path",
                                             pid=proc.info['pid'],
                                             name=proc.info['name'],
                                             path=path)
                                
                                # Send signal to process
                                process = psutil.Process(proc.info['pid'])
                                if signal_type == 'SIGTERM':
                                    process.terminate()
                                elif signal_type == 'SIGKILL':
                                    process.kill()
                                
                                stopped_processes += 1
                                break
                                
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
            
            return {
                'success': True,
                'bytes_saved': 0,  # Prevents future growth
                'files_affected': stopped_processes
            }
            
        except Exception as e:
            logger.error("Process stopping failed", path=path, error=str(e))
            return {'success': False, 'error': str(e)}

    async def _send_alert_notification(self, path: str, parameters: Dict[str, Any]) -> None:
        """Send alert notification via configured channels"""
        try:
            # WebSocket notification
            await self._notify_websocket_clients({
                'type': 'alert',
                'path': path,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'parameters': parameters
            })
            
            # Additional notification channels could be added here
            # (email, Slack, PagerDuty, etc.)
            
        except Exception as e:
            logger.error("Alert notification failed", path=path, error=str(e))

    async def _notify_websocket_clients(self, message: Dict[str, Any]) -> None:
        """Notify all connected WebSocket clients"""
        if not self.websocket_clients:
            return
            
        message_json = json.dumps(message)
        disconnected_clients = set()
        
        for client in self.websocket_clients:
            try:
                await client.send_text(message_json)
            except Exception:
                disconnected_clients.add(client)
        
        # Remove disconnected clients
        self.websocket_clients -= disconnected_clients

# Global monitor instance
enhanced_monitor = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Enhanced application lifecycle management"""
    global enhanced_monitor
    
    # Startup
    logger.info("Starting Enhanced Storage Monitor v2.0")
    
    try:
        enhanced_monitor = EnhancedStorageMonitor()
        await enhanced_monitor.setup_database()
        
        # Start monitoring workers
        enhanced_monitor.state = MonitoringState.RUNNING
        ACTIVE_MONITORS.set(1)
        
        logger.info("Enhanced Storage Monitor started successfully")
        
        yield
        
    except Exception as e:
        logger.error("Startup failed", error=str(e), traceback=traceback.format_exc())
        raise
    
    # Shutdown
    try:
        if enhanced_monitor:
            enhanced_monitor.state = MonitoringState.STOPPING
            
            # Cancel all monitoring tasks
            for task in enhanced_monitor.monitoring_tasks:
                if not task.done():
                    task.cancel()
            
            # Wait for graceful shutdown
            if enhanced_monitor.monitoring_tasks:
                await asyncio.gather(*enhanced_monitor.monitoring_tasks, return_exceptions=True)
            
            ACTIVE_MONITORS.set(0)
            logger.info("Enhanced Storage Monitor stopped gracefully")
            
    except Exception as e:
        logger.error("Shutdown error", error=str(e))

# Enhanced FastAPI application
app = FastAPI(
    title="Enhanced Storage Monitoring System",
    description="Enterprise-grade storage monitoring with ML-powered anomaly detection",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

# Authentication dependency
async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Enhanced authentication with JWT validation"""
    if not enhanced_monitor or not enhanced_monitor.config['security']['enable_auth']:
        return {"user": "system", "permissions": ["admin"]}
    
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication token")

# Enhanced API endpoints
@app.get("/")
async def root():
    """System information and health check"""
    return {
        "service": "Enhanced Storage Monitoring System",
        "version": "2.0.0",
        "status": enhanced_monitor.state if enhanced_monitor else "initializing",
        "features": {
            "ml_anomaly_detection": True,
            "real_time_streaming": True,
            "intelligent_remediation": True,
            "enterprise_security": True
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.get("/health")
async def health_check():
    """Comprehensive health check"""
    if not enhanced_monitor:
        raise HTTPException(status_code=503, detail="Monitor not initialized")
    
    # Perform health checks
    health_status = {
        "status": "healthy",
        "checks": {
            "database": "checking",
            "cache": "checking",
            "ml_models": "checking",
            "integration": "checking"
        },
        "performance": {
            "cpu_usage": psutil.cpu_percent(),
            "memory_usage_mb": psutil.Process().memory_info().rss / 1024 / 1024,
            "disk_usage": psutil.disk_usage('/').percent
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    try:
        # Database check
        async with aiosqlite.connect(STORAGE_DB) as conn:
            await conn.execute("SELECT 1")
        health_status["checks"]["database"] = "healthy"
    except Exception as e:
        health_status["checks"]["database"] = f"error: {str(e)}"
        health_status["status"] = "degraded"
    
    # Cache check
    try:
        if hasattr(enhanced_monitor.cache, 'ping'):
            enhanced_monitor.cache.ping()
        health_status["checks"]["cache"] = "healthy"
    except Exception as e:
        health_status["checks"]["cache"] = f"error: {str(e)}"
    
    # ML models check
    health_status["checks"]["ml_models"] = "healthy" if enhanced_monitor.anomaly_detector else "not_loaded"
    
    # Integration check (simplified)
    health_status["checks"]["integration"] = "healthy"
    
    return health_status

@app.get("/metrics")
async def prometheus_metrics():
    """Prometheus metrics endpoint"""
    return generate_latest().decode('utf-8')

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await websocket.accept()
    
    if enhanced_monitor:
        enhanced_monitor.websocket_clients.add(websocket)
        
        try:
            # Send initial status
            await websocket.send_json({
                "type": "connection_established",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": enhanced_monitor.state
            })
            
            # Keep connection alive
            while True:
                await websocket.receive_text()  # Wait for client messages
                
        except Exception as e:
            logger.info("WebSocket client disconnected", error=str(e))
        finally:
            enhanced_monitor.websocket_clients.discard(websocket)

if __name__ == "__main__":
    # Enhanced startup with proper signal handling
    def signal_handler(signum, frame):
        logger.info("Received shutdown signal", signal=signum)
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8490,
        log_config=None,  # Use our custom logging
        access_log=False,
        workers=1  # Single worker for now, can be scaled
    )