import time
import threading
import smtplib
import json
import requests
import sqlite3
import psutil
from typing import Dict, List, Optional, Callable, Any, Set
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta
from collections import deque, defaultdict
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart

from .optimization_strategies import MemoryOptimizer, OptimizationConfig, MemoryThresholds

class AlertSeverity(Enum):
    INFO = "info"
    WARNING = "warning" 
    CRITICAL = "critical"
    EMERGENCY = "emergency"

class AlertChannel(Enum):
    EMAIL = "email"
    WEBHOOK = "webhook"
    LOG = "log"
    CONSOLE = "console"
    DATABASE = "database"

@dataclass
class AlertConfig:
    enabled: bool = True
    channels: List[AlertChannel] = None
    email_config: Dict[str, str] = None
    webhook_urls: List[str] = None
    severity_threshold: AlertSeverity = AlertSeverity.WARNING
    cooldown_minutes: int = 5
    max_alerts_per_hour: int = 10

@dataclass
class MemoryAlert:
    timestamp: datetime
    severity: AlertSeverity
    message: str
    memory_usage: Dict[str, float]
    source: str
    details: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': self.timestamp.isoformat(),
            'severity': self.severity.value,
            'message': self.message,
            'memory_usage': self.memory_usage,
            'source': self.source,
            'details': self.details or {}
        }

class MemoryAlertSystem:
    """Advanced memory alerting and notification system"""
    
    def __init__(self, config: AlertConfig = None, db_path: str = "memory_alerts.db"):
        self.config = config or AlertConfig()
        if self.config.channels is None:
            self.config.channels = [AlertChannel.LOG, AlertChannel.CONSOLE]
            
        self.db_path = db_path
        self.alert_history = deque(maxlen=1000)
        self.alert_cooldowns = {}
        self.hourly_alert_counts = defaultdict(int)
        
        # Initialize database
        self._init_database()
        
        # Alert processors
        self.alert_processors = {
            AlertChannel.EMAIL: self._send_email_alert,
            AlertChannel.WEBHOOK: self._send_webhook_alert,
            AlertChannel.LOG: self._log_alert,
            AlertChannel.CONSOLE: self._console_alert,
            AlertChannel.DATABASE: self._database_alert
        }
        
        self.running = False
        self.monitor_thread = None
        
    def _init_database(self):
        """Initialize SQLite database for alert storage"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    message TEXT NOT NULL,
                    memory_usage TEXT NOT NULL,
                    source TEXT NOT NULL,
                    details TEXT,
                    acknowledged BOOLEAN DEFAULT FALSE,
                    resolved BOOLEAN DEFAULT FALSE
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_alerts_timestamp 
                ON memory_alerts(timestamp)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_alerts_severity 
                ON memory_alerts(severity)
            """)
            
    def start_monitoring(self, check_interval: int = 30):
        """Start continuous memory monitoring and alerting"""
        if self.running:
            return
            
        self.running = True
        self.monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            args=(check_interval,),
            daemon=True
        )
        self.monitor_thread.start()
        
    def stop_monitoring(self):
        """Stop memory monitoring"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=10)
            
    def _monitoring_loop(self, check_interval: int):
        """Main monitoring loop"""
        while self.running:
            try:
                self._check_memory_conditions()
                self._cleanup_old_data()
                time.sleep(check_interval)
            except Exception as e:
                print(f"Error in memory monitoring loop: {e}")
                time.sleep(60)  # Wait longer on error
                
    def _check_memory_conditions(self):
        """Check current memory conditions and trigger alerts if needed"""
        memory_usage = self._get_memory_usage()
        
        # Check system memory
        if memory_usage['system_percent'] >= 0.95:
            self.trigger_alert(
                AlertSeverity.EMERGENCY,
                f"System memory critically low: {memory_usage['system_percent']:.1%}",
                memory_usage,
                "system_monitor"
            )
        elif memory_usage['system_percent'] >= 0.85:
            self.trigger_alert(
                AlertSeverity.CRITICAL,
                f"System memory very high: {memory_usage['system_percent']:.1%}",
                memory_usage,
                "system_monitor"
            )
        elif memory_usage['system_percent'] >= 0.75:
            self.trigger_alert(
                AlertSeverity.WARNING,
                f"System memory elevated: {memory_usage['system_percent']:.1%}",
                memory_usage,
                "system_monitor"
            )
            
        # Check process memory
        if memory_usage['rss_mb'] > 2048:  # 2GB
            self.trigger_alert(
                AlertSeverity.WARNING,
                f"Process memory high: {memory_usage['rss_mb']:.1f}MB",
                memory_usage,
                "process_monitor"
            )
            
        # Check memory leaks (growth trend)
        self._check_memory_leaks(memory_usage)
        
    def _check_memory_leaks(self, current_usage: Dict[str, float]):
        """Detect potential memory leaks based on growth trends"""
        if len(self.alert_history) < 10:
            return
            
        # Analyze memory growth over last 10 measurements
        recent_alerts = [alert for alert in self.alert_history 
                        if alert.timestamp > datetime.now() - timedelta(minutes=30)]
        
        if len(recent_alerts) < 5:
            return
            
        memory_values = [alert.memory_usage.get('rss_mb', 0) for alert in recent_alerts]
        
        # Calculate growth trend
        if len(memory_values) >= 5:
            growth_rate = (memory_values[-1] - memory_values[0]) / len(memory_values)
            
            if growth_rate > 10:  # Growing by more than 10MB per measurement
                self.trigger_alert(
                    AlertSeverity.WARNING,
                    f"Potential memory leak detected: growing at {growth_rate:.1f}MB per check",
                    current_usage,
                    "leak_detector",
                    {'growth_rate_mb': growth_rate, 'measurements': len(memory_values)}
                )
                
    def trigger_alert(self, severity: AlertSeverity, message: str, 
                     memory_usage: Dict[str, float], source: str, 
                     details: Dict[str, Any] = None):
        """Trigger a memory alert"""
        if not self.config.enabled:
            return
            
        # Check severity threshold
        if severity.value not in ['emergency', 'critical', 'warning', 'info']:
            return
            
        severity_levels = {
            'info': 0,
            'warning': 1, 
            'critical': 2,
            'emergency': 3
        }
        
        if severity_levels[severity.value] < severity_levels[self.config.severity_threshold.value]:
            return
            
        # Check cooldown
        alert_key = f"{source}_{severity.value}"
        if self._is_in_cooldown(alert_key):
            return
            
        # Check rate limit
        current_hour = datetime.now().replace(minute=0, second=0, microsecond=0)
        if self.hourly_alert_counts[current_hour] >= self.config.max_alerts_per_hour:
            return
            
        # Create alert
        alert = MemoryAlert(
            timestamp=datetime.now(),
            severity=severity,
            message=message,
            memory_usage=memory_usage,
            source=source,
            details=details
        )
        
        # Process alert through all configured channels
        self._process_alert(alert)
        
        # Record alert
        self.alert_history.append(alert)
        self.alert_cooldowns[alert_key] = datetime.now()
        self.hourly_alert_counts[current_hour] += 1
        
    def _is_in_cooldown(self, alert_key: str) -> bool:
        """Check if alert is in cooldown period"""
        if alert_key not in self.alert_cooldowns:
            return False
            
        last_alert_time = self.alert_cooldowns[alert_key]
        cooldown_period = timedelta(minutes=self.config.cooldown_minutes)
        
        return datetime.now() - last_alert_time < cooldown_period
        
    def _process_alert(self, alert: MemoryAlert):
        """Process alert through all configured channels"""
        for channel in self.config.channels:
            try:
                processor = self.alert_processors.get(channel)
                if processor:
                    processor(alert)
            except Exception as e:
                print(f"Error processing alert through {channel.value}: {e}")
                
    def _send_email_alert(self, alert: MemoryAlert):
        """Send alert via email"""
        if not self.config.email_config:
            return
            
        try:
            smtp_server = self.config.email_config.get('smtp_server')
            smtp_port = self.config.email_config.get('smtp_port', 587)
            username = self.config.email_config.get('username')
            password = self.config.email_config.get('password')
            from_email = self.config.email_config.get('from_email')
            to_emails = self.config.email_config.get('to_emails', [])
            
            if not all([smtp_server, username, password, from_email, to_emails]):
                return
                
            msg = MimeMultipart()
            msg['From'] = from_email
            msg['To'] = ', '.join(to_emails)
            msg['Subject'] = f"Memory Alert - {alert.severity.value.upper()}: {alert.message}"
            
            body = f"""
Memory Alert Details:

Timestamp: {alert.timestamp}
Severity: {alert.severity.value.upper()}
Source: {alert.source}
Message: {alert.message}

Memory Usage:
{json.dumps(alert.memory_usage, indent=2)}

Additional Details:
{json.dumps(alert.details or {}, indent=2)}
            """
            
            msg.attach(MimeText(body, 'plain'))
            
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(username, password)
                server.send_message(msg)
                
        except Exception as e:
            print(f"Failed to send email alert: {e}")
            
    def _send_webhook_alert(self, alert: MemoryAlert):
        """Send alert via webhook"""
        if not self.config.webhook_urls:
            return
            
        payload = alert.to_dict()
        
        for webhook_url in self.config.webhook_urls:
            try:
                response = requests.post(
                    webhook_url,
                    json=payload,
                    headers={'Content-Type': 'application/json'},
                    timeout=10
                )
                response.raise_for_status()
            except Exception as e:
                print(f"Failed to send webhook alert to {webhook_url}: {e}")
                
    def _log_alert(self, alert: MemoryAlert):
        """Log alert to file"""
        import logging
        
        # Configure logger if not already done
        if not hasattr(self, 'logger'):
            self.logger = logging.getLogger('memory_alerts')
            if not self.logger.handlers:
                handler = logging.FileHandler('memory_alerts.log')
                formatter = logging.Formatter(
                    '%(asctime)s - %(levelname)s - %(message)s'
                )
                handler.setFormatter(formatter)
                self.logger.addHandler(handler)
                self.logger.setLevel(logging.INFO)
                
        log_message = f"[{alert.source}] {alert.message} | Usage: {alert.memory_usage}"
        
        if alert.severity == AlertSeverity.EMERGENCY:
            self.logger.critical(log_message)
        elif alert.severity == AlertSeverity.CRITICAL:
            self.logger.error(log_message)
        elif alert.severity == AlertSeverity.WARNING:
            self.logger.warning(log_message)
        else:
            self.logger.info(log_message)
            
    def _console_alert(self, alert: MemoryAlert):
        """Print alert to console"""
        severity_colors = {
            AlertSeverity.INFO: '\033[94m',      # Blue
            AlertSeverity.WARNING: '\033[93m',   # Yellow
            AlertSeverity.CRITICAL: '\033[91m',  # Red
            AlertSeverity.EMERGENCY: '\033[95m'  # Magenta
        }
        
        color = severity_colors.get(alert.severity, '')
        reset = '\033[0m'
        
        print(f"{color}[{alert.severity.value.upper()}] {alert.timestamp.strftime('%H:%M:%S')} - "
              f"{alert.source}: {alert.message}{reset}")
              
    def _database_alert(self, alert: MemoryAlert):
        """Store alert in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO memory_alerts 
                    (timestamp, severity, message, memory_usage, source, details)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    alert.timestamp.isoformat(),
                    alert.severity.value,
                    alert.message,
                    json.dumps(alert.memory_usage),
                    alert.source,
                    json.dumps(alert.details) if alert.details else None
                ))
        except Exception as e:
            print(f"Failed to store alert in database: {e}")
            
    def _get_memory_usage(self) -> Dict[str, float]:
        """Get current memory usage"""
        process = psutil.Process()
        memory_info = process.memory_info()
        system_memory = psutil.virtual_memory()
        
        return {
            'rss_mb': memory_info.rss / 1024 / 1024,
            'vms_mb': memory_info.vms / 1024 / 1024,
            'percent': process.memory_percent(),
            'system_percent': system_memory.percent / 100,
            'available_mb': system_memory.available / 1024 / 1024
        }
        
    def _cleanup_old_data(self):
        """Clean up old alert data"""
        cutoff_date = datetime.now() - timedelta(days=7)
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    DELETE FROM memory_alerts 
                    WHERE timestamp < ? AND resolved = TRUE
                """, (cutoff_date.isoformat(),))
        except Exception as e:
            print(f"Failed to cleanup old alert data: {e}")
            
    def get_alert_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get alert summary for the last N hours"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_alerts = [
            alert for alert in self.alert_history 
            if alert.timestamp > cutoff_time
        ]
        
        severity_counts = defaultdict(int)
        source_counts = defaultdict(int)
        
        for alert in recent_alerts:
            severity_counts[alert.severity.value] += 1
            source_counts[alert.source] += 1
            
        return {
            'time_period_hours': hours,
            'total_alerts': len(recent_alerts),
            'severity_breakdown': dict(severity_counts),
            'source_breakdown': dict(source_counts),
            'recent_alerts': [alert.to_dict() for alert in recent_alerts[-10:]]
        }
        
    def acknowledge_alert(self, alert_id: int):
        """Acknowledge an alert in the database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE memory_alerts 
                    SET acknowledged = TRUE 
                    WHERE id = ?
                """, (alert_id,))
        except Exception as e:
            print(f"Failed to acknowledge alert: {e}")
            
    def resolve_alert(self, alert_id: int):
        """Mark an alert as resolved"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE memory_alerts 
                    SET resolved = TRUE 
                    WHERE id = ?
                """, (alert_id,))
        except Exception as e:
            print(f"Failed to resolve alert: {e}")

class AutomaticCleanupSystem:
    """Automatic cleanup system for memory management"""
    
    def __init__(self, memory_optimizer: MemoryOptimizer, alert_system: MemoryAlertSystem):
        self.optimizer = memory_optimizer
        self.alert_system = alert_system
        
        self.cleanup_rules = []
        self.running = False
        self.cleanup_thread = None
        
    def add_cleanup_rule(self, name: str, condition: Callable[[], bool], 
                        action: Callable[[], Dict[str, Any]], 
                        cooldown_minutes: int = 30):
        """Add an automatic cleanup rule"""
        rule = {
            'name': name,
            'condition': condition,
            'action': action,
            'cooldown_minutes': cooldown_minutes,
            'last_executed': None
        }
        self.cleanup_rules.append(rule)
        
    def start_automatic_cleanup(self, check_interval: int = 60):
        """Start automatic cleanup system"""
        if self.running:
            return
            
        self.running = True
        self.cleanup_thread = threading.Thread(
            target=self._cleanup_loop,
            args=(check_interval,),
            daemon=True
        )
        self.cleanup_thread.start()
        
    def stop_automatic_cleanup(self):
        """Stop automatic cleanup"""
        self.running = False
        if self.cleanup_thread:
            self.cleanup_thread.join(timeout=10)
            
    def _cleanup_loop(self, check_interval: int):
        """Main cleanup loop"""
        while self.running:
            try:
                self._execute_cleanup_rules()
                time.sleep(check_interval)
            except Exception as e:
                print(f"Error in cleanup loop: {e}")
                time.sleep(300)  # Wait 5 minutes on error
                
    def _execute_cleanup_rules(self):
        """Execute applicable cleanup rules"""
        for rule in self.cleanup_rules:
            try:
                # Check cooldown
                if rule['last_executed']:
                    cooldown = timedelta(minutes=rule['cooldown_minutes'])
                    if datetime.now() - rule['last_executed'] < cooldown:
                        continue
                        
                # Check condition
                if rule['condition']():
                    # Execute action
                    result = rule['action']()
                    rule['last_executed'] = datetime.now()
                    
                    # Log cleanup action
                    self.alert_system.trigger_alert(
                        AlertSeverity.INFO,
                        f"Automatic cleanup executed: {rule['name']}",
                        self.optimizer.get_memory_usage(),
                        "auto_cleanup",
                        {'rule': rule['name'], 'result': result}
                    )
                    
            except Exception as e:
                print(f"Error executing cleanup rule {rule['name']}: {e}")

def setup_default_cleanup_rules(cleanup_system: AutomaticCleanupSystem):
    """Set up default cleanup rules"""
    
    # High memory usage cleanup
    cleanup_system.add_cleanup_rule(
        name="high_memory_cleanup",
        condition=lambda: psutil.virtual_memory().percent > 85,
        action=lambda: cleanup_system.optimizer.optimize_memory(),
        cooldown_minutes=15
    )
    
    # Process memory cleanup
    cleanup_system.add_cleanup_rule(
        name="process_memory_cleanup", 
        condition=lambda: psutil.Process().memory_percent() > 20,
        action=lambda: cleanup_system.optimizer.cleanup_temporary_objects(),
        cooldown_minutes=10
    )
    
    # Garbage collection cleanup
    cleanup_system.add_cleanup_rule(
        name="garbage_collection",
        condition=lambda: len(__import__('gc').get_objects()) > 50000,
        action=lambda: cleanup_system.optimizer.force_garbage_collection(),
        cooldown_minutes=5
    )

# Global instances
global_alert_system = None
global_cleanup_system = None

def get_alert_system(config: AlertConfig = None) -> MemoryAlertSystem:
    """Get or create global alert system"""
    global global_alert_system
    if global_alert_system is None:
        global_alert_system = MemoryAlertSystem(config)
        global_alert_system.start_monitoring()
    return global_alert_system

def get_cleanup_system(optimizer: MemoryOptimizer = None, 
                      alert_system: MemoryAlertSystem = None) -> AutomaticCleanupSystem:
    """Get or create global cleanup system"""
    global global_cleanup_system
    if global_cleanup_system is None:
        if optimizer is None:
            from .optimization_strategies import get_memory_optimizer
            optimizer = get_memory_optimizer()
        if alert_system is None:
            alert_system = get_alert_system()
            
        global_cleanup_system = AutomaticCleanupSystem(optimizer, alert_system)
        setup_default_cleanup_rules(global_cleanup_system)
        global_cleanup_system.start_automatic_cleanup()
        
    return global_cleanup_system

if __name__ == "__main__":
    # Example usage
    alert_config = AlertConfig(
        channels=[AlertChannel.CONSOLE, AlertChannel.LOG],
        severity_threshold=AlertSeverity.WARNING,
        cooldown_minutes=2
    )
    
    alert_system = MemoryAlertSystem(alert_config)
    alert_system.start_monitoring(check_interval=10)
    
    # Simulate some activity
    try:
        time.sleep(30)
        summary = alert_system.get_alert_summary()
        print(json.dumps(summary, indent=2))
    finally:
        alert_system.stop_monitoring()