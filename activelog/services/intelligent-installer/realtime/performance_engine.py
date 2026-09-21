"""
Real-Time Performance Optimization Engine
Advanced real-time monitoring, analysis, and optimization system
"""

import asyncio
import time
import logging
import threading
from typing import Dict, List, Optional, Any, Callable, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import deque, defaultdict
import numpy as np
import json
from pathlib import Path

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

from api.models import HardwareProfile, AdaptiveConfiguration

@dataclass
class PerformanceMetric:
    """Real-time performance metric"""
    name: str
    value: float
    unit: str
    timestamp: datetime
    source: str
    severity: str = 'normal'  # normal, warning, critical
    trend: str = 'stable'  # improving, stable, degrading
    metadata: Dict[str, Any] = None

@dataclass
class OptimizationAction:
    """Real-time optimization action"""
    action_id: str
    action_type: str
    target_component: str
    parameters: Dict[str, Any]
    expected_impact: float
    priority: int  # 1-10, 10 being highest
    requires_user_approval: bool
    estimated_duration: float  # seconds
    rollback_possible: bool

@dataclass
class PerformanceAlert:
    """Performance alert/warning"""
    alert_id: str
    severity: str  # info, warning, error, critical
    component: str
    message: str
    metric_value: float
    threshold: float
    timestamp: datetime
    suggested_actions: List[str]
    auto_resolved: bool = False

class RealTimeMonitor:
    """Real-time system monitoring"""
    
    def __init__(self, sampling_interval: float = 1.0):
        self.sampling_interval = sampling_interval
        self.is_monitoring = False
        self.metrics_buffer = deque(maxlen=3600)  # 1 hour at 1Hz
        self.performance_history = defaultdict(lambda: deque(maxlen=300))  # 5 minutes per metric
        self.monitoring_thread = None
        self.callbacks = []
        
    def add_callback(self, callback: Callable[[List[PerformanceMetric]], None]):
        """Add callback for real-time metrics"""
        self.callbacks.append(callback)
    
    async def start_monitoring(self):
        """Start real-time monitoring"""
        if self.is_monitoring:
            return
            
        self.is_monitoring = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        logging.info("📊 Real-time performance monitoring started")
    
    async def stop_monitoring(self):
        """Stop monitoring"""
        self.is_monitoring = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5.0)
        logging.info("📊 Real-time monitoring stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.is_monitoring:
            try:
                metrics = self._collect_metrics()
                timestamp = datetime.now()
                
                # Store metrics
                for metric in metrics:
                    self.metrics_buffer.append(metric)
                    self.performance_history[metric.name].append((timestamp, metric.value))
                
                # Notify callbacks
                for callback in self.callbacks:
                    try:
                        callback(metrics)
                    except Exception as e:
                        logging.error(f"Monitoring callback error: {e}")
                
                time.sleep(self.sampling_interval)
                
            except Exception as e:
                logging.error(f"Monitoring error: {e}")
                time.sleep(5.0)
    
    def _collect_metrics(self) -> List[PerformanceMetric]:
        """Collect current performance metrics"""
        metrics = []
        timestamp = datetime.now()
        
        if not PSUTIL_AVAILABLE:
            # Mock metrics
            return [
                PerformanceMetric("cpu_percent", 45.0, "%", timestamp, "mock"),
                PerformanceMetric("memory_percent", 65.0, "%", timestamp, "mock"),
                PerformanceMetric("disk_usage", 70.0, "%", timestamp, "mock")
            ]
        
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=0.1)
            cpu_freq = psutil.cpu_freq()
            load_avg = psutil.getloadavg() if hasattr(psutil, 'getloadavg') else (0, 0, 0)
            
            metrics.extend([
                PerformanceMetric("cpu_percent", cpu_percent, "%", timestamp, "psutil",
                                severity="critical" if cpu_percent > 90 else "warning" if cpu_percent > 80 else "normal"),
                PerformanceMetric("cpu_frequency", cpu_freq.current if cpu_freq else 0, "MHz", timestamp, "psutil"),
                PerformanceMetric("load_average_1m", load_avg[0], "", timestamp, "psutil"),
                PerformanceMetric("load_average_5m", load_avg[1], "", timestamp, "psutil"),
            ])
            
            # Memory metrics
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            metrics.extend([
                PerformanceMetric("memory_percent", memory.percent, "%", timestamp, "psutil",
                                severity="critical" if memory.percent > 95 else "warning" if memory.percent > 85 else "normal"),
                PerformanceMetric("memory_available_gb", memory.available / (1024**3), "GB", timestamp, "psutil"),
                PerformanceMetric("memory_used_gb", memory.used / (1024**3), "GB", timestamp, "psutil"),
                PerformanceMetric("swap_percent", swap.percent, "%", timestamp, "psutil"),
            ])
            
            # Disk metrics
            disk_usage = psutil.disk_usage('/')
            disk_io = psutil.disk_io_counters()
            
            metrics.extend([
                PerformanceMetric("disk_usage_percent", disk_usage.percent, "%", timestamp, "psutil",
                                severity="warning" if disk_usage.percent > 90 else "normal"),
                PerformanceMetric("disk_free_gb", disk_usage.free / (1024**3), "GB", timestamp, "psutil"),
            ])
            
            if disk_io:
                metrics.extend([
                    PerformanceMetric("disk_read_mb_s", disk_io.read_bytes / (1024**2), "MB/s", timestamp, "psutil"),
                    PerformanceMetric("disk_write_mb_s", disk_io.write_bytes / (1024**2), "MB/s", timestamp, "psutil"),
                ])
            
            # Network metrics
            net_io = psutil.net_io_counters()
            if net_io:
                metrics.extend([
                    PerformanceMetric("network_sent_mb_s", net_io.bytes_sent / (1024**2), "MB/s", timestamp, "psutil"),
                    PerformanceMetric("network_recv_mb_s", net_io.bytes_recv / (1024**2), "MB/s", timestamp, "psutil"),
                ])
            
            # Process metrics
            processes = len(psutil.pids())
            metrics.append(PerformanceMetric("process_count", processes, "", timestamp, "psutil"))
            
            # Temperature metrics (if available)
            try:
                temps = psutil.sensors_temperatures()
                if temps:
                    for name, entries in temps.items():
                        for i, entry in enumerate(entries):
                            metric_name = f"temperature_{name}_{i}" if len(entries) > 1 else f"temperature_{name}"
                            severity = "critical" if entry.current > 85 else "warning" if entry.current > 75 else "normal"
                            metrics.append(PerformanceMetric(metric_name, entry.current, "°C", timestamp, "psutil", severity=severity))
            except:
                pass
            
            # Battery metrics (if available)
            try:
                battery = psutil.sensors_battery()
                if battery:
                    metrics.extend([
                        PerformanceMetric("battery_percent", battery.percent, "%", timestamp, "psutil"),
                        PerformanceMetric("battery_time_left", battery.secsleft / 3600 if battery.secsleft != psutil.POWER_TIME_UNLIMITED else -1, "hours", timestamp, "psutil"),
                        PerformanceMetric("battery_plugged", 1.0 if battery.power_plugged else 0.0, "", timestamp, "psutil"),
                    ])
            except:
                pass
                
        except Exception as e:
            logging.error(f"Metrics collection error: {e}")
        
        return metrics
    
    def get_recent_metrics(self, metric_name: str, duration_seconds: int = 300) -> List[Tuple[datetime, float]]:
        """Get recent values for a specific metric"""
        cutoff_time = datetime.now() - timedelta(seconds=duration_seconds)
        
        if metric_name in self.performance_history:
            return [(ts, value) for ts, value in self.performance_history[metric_name] 
                   if ts >= cutoff_time]
        return []
    
    def get_metric_statistics(self, metric_name: str, duration_seconds: int = 300) -> Dict[str, float]:
        """Get statistics for a metric"""
        recent_values = self.get_recent_metrics(metric_name, duration_seconds)
        
        if not recent_values:
            return {}
        
        values = [v for _, v in recent_values]
        
        return {
            'current': values[-1] if values else 0,
            'average': np.mean(values),
            'min': np.min(values),
            'max': np.max(values),
            'std': np.std(values),
            'trend': self._calculate_trend(values)
        }
    
    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend direction"""
        if len(values) < 3:
            return 'stable'
        
        # Use linear regression to determine trend
        x = np.arange(len(values))
        slope = np.polyfit(x, values, 1)[0]
        
        if slope > 0.1:
            return 'increasing'
        elif slope < -0.1:
            return 'decreasing'
        else:
            return 'stable'

class IntelligentOptimizer:
    """Intelligent real-time optimizer"""
    
    def __init__(self):
        self.optimization_rules = []
        self.active_optimizations = {}
        self.optimization_history = deque(maxlen=1000)
        self.user_approval_queue = deque()
        
    def add_optimization_rule(self, rule: Dict[str, Any]):
        """Add optimization rule"""
        self.optimization_rules.append(rule)
    
    def initialize_default_rules(self):
        """Initialize default optimization rules"""
        
        # CPU optimization rules
        self.add_optimization_rule({
            'name': 'high_cpu_usage',
            'trigger': {'metric': 'cpu_percent', 'condition': '>', 'threshold': 85, 'duration': 30},
            'actions': [
                {
                    'type': 'reduce_background_tasks',
                    'parameters': {'priority_threshold': 'low'},
                    'impact': 0.15,
                    'requires_approval': False
                },
                {
                    'type': 'enable_cpu_governor',
                    'parameters': {'mode': 'performance'},
                    'impact': 0.10,
                    'requires_approval': True
                }
            ]
        })
        
        # Memory optimization rules
        self.add_optimization_rule({
            'name': 'high_memory_usage',
            'trigger': {'metric': 'memory_percent', 'condition': '>', 'threshold': 90, 'duration': 10},
            'actions': [
                {
                    'type': 'clear_system_cache',
                    'parameters': {},
                    'impact': 0.05,
                    'requires_approval': False
                },
                {
                    'type': 'reduce_cache_size',
                    'parameters': {'reduction_factor': 0.5},
                    'impact': 0.20,
                    'requires_approval': False
                }
            ]
        })
        
        # Disk space optimization
        self.add_optimization_rule({
            'name': 'low_disk_space',
            'trigger': {'metric': 'disk_usage_percent', 'condition': '>', 'threshold': 95, 'duration': 5},
            'actions': [
                {
                    'type': 'cleanup_temp_files',
                    'parameters': {},
                    'impact': 0.02,
                    'requires_approval': False
                }
            ]
        })
        
        # Temperature optimization
        self.add_optimization_rule({
            'name': 'high_temperature',
            'trigger': {'metric': 'temperature_coretemp_0', 'condition': '>', 'threshold': 80, 'duration': 60},
            'actions': [
                {
                    'type': 'reduce_performance',
                    'parameters': {'cpu_limit': 0.8},
                    'impact': 0.25,
                    'requires_approval': True
                }
            ]
        })
        
        # Battery optimization
        self.add_optimization_rule({
            'name': 'low_battery',
            'trigger': {'metric': 'battery_percent', 'condition': '<', 'threshold': 20, 'duration': 5},
            'actions': [
                {
                    'type': 'enable_power_saving',
                    'parameters': {'profile': 'aggressive'},
                    'impact': 0.40,
                    'requires_approval': False
                }
            ]
        })
    
    async def evaluate_optimizations(self, metrics: List[PerformanceMetric]) -> List[OptimizationAction]:
        """Evaluate and generate optimization actions"""
        
        actions = []
        
        for rule in self.optimization_rules:
            if await self._check_rule_trigger(rule, metrics):
                rule_actions = await self._generate_rule_actions(rule, metrics)
                actions.extend(rule_actions)
        
        # Priority-based filtering
        actions.sort(key=lambda a: a.priority, reverse=True)
        
        return actions[:5]  # Top 5 actions
    
    async def _check_rule_trigger(self, rule: Dict[str, Any], metrics: List[PerformanceMetric]) -> bool:
        """Check if rule trigger conditions are met"""
        
        trigger = rule['trigger']
        metric_name = trigger['metric']
        condition = trigger['condition']
        threshold = trigger['threshold']
        required_duration = trigger.get('duration', 0)
        
        # Find current metric value
        current_value = None
        for metric in metrics:
            if metric.name == metric_name:
                current_value = metric.value
                break
        
        if current_value is None:
            return False
        
        # Check condition
        condition_met = False
        if condition == '>':
            condition_met = current_value > threshold
        elif condition == '<':
            condition_met = current_value < threshold
        elif condition == '==':
            condition_met = abs(current_value - threshold) < 0.01
        elif condition == '>=':
            condition_met = current_value >= threshold
        elif condition == '<=':
            condition_met = current_value <= threshold
        
        if not condition_met:
            return False
        
        # Check duration if required
        if required_duration > 0:
            # This would require checking historical data
            # Simplified for now
            return True
        
        return True
    
    async def _generate_rule_actions(self, rule: Dict[str, Any], metrics: List[PerformanceMetric]) -> List[OptimizationAction]:
        """Generate optimization actions from rule"""
        
        actions = []
        
        for action_def in rule['actions']:
            action = OptimizationAction(
                action_id=f"{rule['name']}_{int(time.time())}",
                action_type=action_def['type'],
                target_component=rule['name'],
                parameters=action_def['parameters'],
                expected_impact=action_def['impact'],
                priority=self._calculate_action_priority(action_def, metrics),
                requires_user_approval=action_def.get('requires_approval', False),
                estimated_duration=action_def.get('duration', 5.0),
                rollback_possible=action_def.get('rollback_possible', True)
            )
            actions.append(action)
        
        return actions
    
    def _calculate_action_priority(self, action_def: Dict[str, Any], metrics: List[PerformanceMetric]) -> int:
        """Calculate action priority"""
        
        base_priority = 5
        
        # Increase priority based on impact
        impact_boost = int(action_def['impact'] * 10)
        base_priority += impact_boost
        
        # Increase priority for critical system states
        for metric in metrics:
            if metric.severity == 'critical':
                base_priority += 3
            elif metric.severity == 'warning':
                base_priority += 1
        
        return min(10, max(1, base_priority))

class AlertManager:
    """Manages performance alerts and notifications"""
    
    def __init__(self):
        self.active_alerts = {}
        self.alert_history = deque(maxlen=1000)
        self.alert_callbacks = []
        self.thresholds = self._initialize_thresholds()
    
    def _initialize_thresholds(self) -> Dict[str, Dict[str, float]]:
        """Initialize alert thresholds"""
        return {
            'cpu_percent': {'warning': 80, 'critical': 95},
            'memory_percent': {'warning': 85, 'critical': 95},
            'disk_usage_percent': {'warning': 85, 'critical': 95},
            'temperature_coretemp_0': {'warning': 75, 'critical': 85},
            'battery_percent': {'warning': 15, 'critical': 5}
        }
    
    def add_alert_callback(self, callback: Callable[[PerformanceAlert], None]):
        """Add alert callback"""
        self.alert_callbacks.append(callback)
    
    def process_metrics(self, metrics: List[PerformanceMetric]) -> List[PerformanceAlert]:
        """Process metrics and generate alerts"""
        
        new_alerts = []
        
        for metric in metrics:
            alert = self._check_metric_thresholds(metric)
            if alert:
                # Check if this is a new alert or update to existing
                alert_key = f"{metric.name}_{alert.severity}"
                
                if alert_key not in self.active_alerts:
                    # New alert
                    self.active_alerts[alert_key] = alert
                    new_alerts.append(alert)
                    
                    # Notify callbacks
                    for callback in self.alert_callbacks:
                        try:
                            callback(alert)
                        except Exception as e:
                            logging.error(f"Alert callback error: {e}")
                else:
                    # Update existing alert
                    self.active_alerts[alert_key].metric_value = metric.value
                    self.active_alerts[alert_key].timestamp = metric.timestamp
        
        # Check for resolved alerts
        self._check_resolved_alerts(metrics)
        
        return new_alerts
    
    def _check_metric_thresholds(self, metric: PerformanceMetric) -> Optional[PerformanceAlert]:
        """Check if metric exceeds thresholds"""
        
        if metric.name not in self.thresholds:
            return None
        
        thresholds = self.thresholds[metric.name]
        
        if metric.value >= thresholds.get('critical', float('inf')):
            severity = 'critical'
            threshold = thresholds['critical']
        elif metric.value >= thresholds.get('warning', float('inf')):
            severity = 'warning'
            threshold = thresholds['warning']
        else:
            return None
        
        suggested_actions = self._get_suggested_actions(metric.name, severity)
        
        return PerformanceAlert(
            alert_id=f"alert_{metric.name}_{int(time.time())}",
            severity=severity,
            component=metric.name,
            message=f"{metric.name} is {severity}: {metric.value}{metric.unit} (threshold: {threshold}{metric.unit})",
            metric_value=metric.value,
            threshold=threshold,
            timestamp=metric.timestamp,
            suggested_actions=suggested_actions
        )
    
    def _get_suggested_actions(self, metric_name: str, severity: str) -> List[str]:
        """Get suggested actions for alert"""
        
        actions = {
            'cpu_percent': {
                'warning': ["Close unnecessary applications", "Check for resource-heavy processes"],
                'critical': ["Force-kill non-essential processes", "Enable performance mode", "Consider hardware upgrade"]
            },
            'memory_percent': {
                'warning': ["Clear system cache", "Close browser tabs"],
                'critical': ["Force garbage collection", "Kill memory-intensive processes", "Add more RAM"]
            },
            'disk_usage_percent': {
                'warning': ["Clean temporary files", "Empty trash"],
                'critical': ["Delete large files", "Move files to external storage", "Uninstall unused programs"]
            },
            'temperature_coretemp_0': {
                'warning': ["Check system ventilation", "Reduce CPU load"],
                'critical': ["Enable thermal throttling", "Shut down system if overheating continues"]
            },
            'battery_percent': {
                'warning': ["Enable power saving mode", "Reduce screen brightness"],
                'critical': ["Save work and connect charger immediately", "Emergency shutdown if no power available"]
            }
        }
        
        return actions.get(metric_name, {}).get(severity, ["Monitor situation closely"])
    
    def _check_resolved_alerts(self, metrics: List[PerformanceMetric]):
        """Check for resolved alerts"""
        
        metric_values = {m.name: m.value for m in metrics}
        resolved_alerts = []
        
        for alert_key, alert in self.active_alerts.items():
            metric_name = alert.component
            
            if metric_name in metric_values:
                current_value = metric_values[metric_name]
                
                # Check if alert condition is no longer met
                if alert.severity == 'critical':
                    threshold = self.thresholds[metric_name]['critical']
                    if current_value < threshold * 0.9:  # 10% hysteresis
                        resolved_alerts.append(alert_key)
                elif alert.severity == 'warning':
                    threshold = self.thresholds[metric_name]['warning']
                    if current_value < threshold * 0.95:  # 5% hysteresis
                        resolved_alerts.append(alert_key)
        
        # Remove resolved alerts
        for alert_key in resolved_alerts:
            resolved_alert = self.active_alerts.pop(alert_key)
            resolved_alert.auto_resolved = True
            self.alert_history.append(resolved_alert)
            logging.info(f"Alert resolved: {resolved_alert.message}")

class RealTimePerformanceEngine:
    """Main real-time performance optimization engine"""
    
    def __init__(self, hardware_profile: HardwareProfile):
        self.hardware_profile = hardware_profile
        self.monitor = RealTimeMonitor(sampling_interval=1.0)
        self.optimizer = IntelligentOptimizer()
        self.alert_manager = AlertManager()
        self.is_running = False
        
        # Connect components
        self.monitor.add_callback(self._process_metrics)
        self.alert_manager.add_alert_callback(self._handle_alert)
    
    async def start(self):
        """Start real-time optimization engine"""
        if self.is_running:
            return
        
        self.is_running = True
        
        # Initialize optimizer rules
        self.optimizer.initialize_default_rules()
        
        # Start monitoring
        await self.monitor.start_monitoring()
        
        # Start optimization loop
        asyncio.create_task(self._optimization_loop())
        
        logging.info("🚀 Real-time performance engine started")
    
    async def stop(self):
        """Stop the engine"""
        self.is_running = False
        await self.monitor.stop_monitoring()
        logging.info("🚀 Real-time performance engine stopped")
    
    def _process_metrics(self, metrics: List[PerformanceMetric]):
        """Process new metrics"""
        try:
            # Generate alerts
            alerts = self.alert_manager.process_metrics(metrics)
            
            # Log critical alerts
            for alert in alerts:
                if alert.severity == 'critical':
                    logging.warning(f"CRITICAL ALERT: {alert.message}")
        
        except Exception as e:
            logging.error(f"Metrics processing error: {e}")
    
    def _handle_alert(self, alert: PerformanceAlert):
        """Handle performance alert"""
        logging.info(f"Performance alert: {alert.message}")
        
        # Add alert-triggered optimization logic here
        if alert.severity == 'critical':
            # Trigger emergency optimizations
            pass
    
    async def _optimization_loop(self):
        """Main optimization loop"""
        while self.is_running:
            try:
                # Get recent metrics
                recent_metrics = list(self.monitor.metrics_buffer)[-10:] if self.monitor.metrics_buffer else []
                
                if recent_metrics:
                    # Generate optimization actions
                    actions = await self.optimizer.evaluate_optimizations(recent_metrics)
                    
                    # Execute non-approval-required actions
                    for action in actions:
                        if not action.requires_user_approval:
                            await self._execute_optimization_action(action)
                        else:
                            # Queue for user approval
                            self.optimizer.user_approval_queue.append(action)
                
                await asyncio.sleep(10.0)  # Optimize every 10 seconds
                
            except Exception as e:
                logging.error(f"Optimization loop error: {e}")
                await asyncio.sleep(30.0)
    
    async def _execute_optimization_action(self, action: OptimizationAction) -> bool:
        """Execute an optimization action"""
        
        try:
            logging.info(f"Executing optimization: {action.action_type}")
            
            if action.action_type == 'reduce_background_tasks':
                return await self._reduce_background_tasks(action.parameters)
            elif action.action_type == 'clear_system_cache':
                return await self._clear_system_cache(action.parameters)
            elif action.action_type == 'reduce_cache_size':
                return await self._reduce_cache_size(action.parameters)
            elif action.action_type == 'cleanup_temp_files':
                return await self._cleanup_temp_files(action.parameters)
            elif action.action_type == 'enable_power_saving':
                return await self._enable_power_saving(action.parameters)
            else:
                logging.warning(f"Unknown optimization action: {action.action_type}")
                return False
                
        except Exception as e:
            logging.error(f"Optimization execution error: {e}")
            return False
    
    async def _reduce_background_tasks(self, parameters: Dict[str, Any]) -> bool:
        """Reduce background task priority"""
        # Placeholder implementation
        logging.info("Reducing background task priorities")
        return True
    
    async def _clear_system_cache(self, parameters: Dict[str, Any]) -> bool:
        """Clear system cache"""
        try:
            if PSUTIL_AVAILABLE:
                # This would implement actual cache clearing
                logging.info("Clearing system cache")
                return True
        except Exception as e:
            logging.error(f"Cache clearing failed: {e}")
        return False
    
    async def _reduce_cache_size(self, parameters: Dict[str, Any]) -> bool:
        """Reduce application cache size"""
        reduction_factor = parameters.get('reduction_factor', 0.5)
        logging.info(f"Reducing cache size by factor {reduction_factor}")
        return True
    
    async def _cleanup_temp_files(self, parameters: Dict[str, Any]) -> bool:
        """Clean up temporary files"""
        try:
            import tempfile
            import shutil
            
            temp_dir = tempfile.gettempdir()
            # This would implement safe temp file cleanup
            logging.info(f"Cleaning up temporary files in {temp_dir}")
            return True
        except Exception as e:
            logging.error(f"Temp cleanup failed: {e}")
        return False
    
    async def _enable_power_saving(self, parameters: Dict[str, Any]) -> bool:
        """Enable power saving mode"""
        profile = parameters.get('profile', 'standard')
        logging.info(f"Enabling power saving profile: {profile}")
        return True
    
    def get_current_status(self) -> Dict[str, Any]:
        """Get current engine status"""
        
        # Get recent metrics statistics
        metrics_stats = {}
        key_metrics = ['cpu_percent', 'memory_percent', 'disk_usage_percent']
        
        for metric_name in key_metrics:
            stats = self.monitor.get_metric_statistics(metric_name)
            if stats:
                metrics_stats[metric_name] = stats
        
        return {
            'engine_running': self.is_running,
            'monitoring_active': self.monitor.is_monitoring,
            'active_alerts': len(self.alert_manager.active_alerts),
            'pending_approvals': len(self.optimizer.user_approval_queue),
            'metrics_collected': len(self.monitor.metrics_buffer),
            'optimization_rules': len(self.optimizer.optimization_rules),
            'metrics_statistics': metrics_stats,
            'recent_optimizations': len(self.optimizer.optimization_history)
        }
    
    def get_performance_dashboard_data(self) -> Dict[str, Any]:
        """Get data for performance dashboard"""
        
        dashboard_data = {
            'timestamp': datetime.now().isoformat(),
            'system_health': 'good',  # good, warning, critical
            'metrics': {},
            'alerts': [],
            'optimizations': [],
            'trends': {}
        }
        
        # Current metrics
        if self.monitor.metrics_buffer:
            recent_metrics = list(self.monitor.metrics_buffer)[-1:]
            for metric in recent_metrics:
                dashboard_data['metrics'][metric.name] = {
                    'value': metric.value,
                    'unit': metric.unit,
                    'severity': metric.severity,
                    'trend': metric.trend
                }
        
        # Active alerts
        dashboard_data['alerts'] = [
            {
                'severity': alert.severity,
                'component': alert.component,
                'message': alert.message,
                'timestamp': alert.timestamp.isoformat()
            }
            for alert in self.alert_manager.active_alerts.values()
        ]
        
        # Recent optimizations
        dashboard_data['optimizations'] = [
            {
                'action_type': opt.action_type,
                'target_component': opt.target_component,
                'impact': opt.expected_impact
            }
            for opt in list(self.optimizer.optimization_history)[-5:]
        ]
        
        # System health assessment
        critical_alerts = [a for a in self.alert_manager.active_alerts.values() if a.severity == 'critical']
        warning_alerts = [a for a in self.alert_manager.active_alerts.values() if a.severity == 'warning']
        
        if critical_alerts:
            dashboard_data['system_health'] = 'critical'
        elif warning_alerts:
            dashboard_data['system_health'] = 'warning'
        
        return dashboard_data