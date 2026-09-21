"""
ActiveLog Project Memory - Performance Monitoring and Auto-Scaling
Real-time performance monitoring with intelligent auto-scaling capabilities
"""

from typing import Dict, List, Any, Optional, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import psutil
import time
import json
import numpy as np
from datetime import datetime, timezone, timedelta
from collections import deque, defaultdict
import threading
import weakref

class MetricType(Enum):
    """Types of metrics being monitored"""
    CPU_USAGE = "cpu_usage"
    MEMORY_USAGE = "memory_usage"
    RESPONSE_TIME = "response_time"
    THROUGHPUT = "throughput"
    ERROR_RATE = "error_rate"
    CACHE_HIT_RATE = "cache_hit_rate"
    ACTIVE_SESSIONS = "active_sessions"
    PREDICTION_ACCURACY = "prediction_accuracy"
    COMPRESSION_RATIO = "compression_ratio"
    SEARCH_LATENCY = "search_latency"

class AlertLevel(Enum):
    """Alert severity levels"""
    CRITICAL = "critical"    # Immediate action required
    WARNING = "warning"      # Attention needed
    INFO = "info"           # Informational
    DEBUG = "debug"         # Debug information

class ScalingAction(Enum):
    """Possible scaling actions"""
    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down" 
    OPTIMIZE_CACHE = "optimize_cache"
    COMPRESS_DATA = "compress_data"
    CLEAR_LOW_PRIORITY = "clear_low_priority"
    INCREASE_WORKERS = "increase_workers"
    DECREASE_WORKERS = "decrease_workers"

@dataclass
class MetricPoint:
    """Single metric measurement point"""
    metric_type: MetricType
    value: float
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Alert:
    """System alert with details"""
    level: AlertLevel
    message: str
    metric_type: MetricType
    current_value: float
    threshold: float
    timestamp: datetime
    suggested_actions: List[ScalingAction] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PerformanceThresholds:
    """Performance thresholds for alerting"""
    cpu_warning: float = 70.0      # CPU usage %
    cpu_critical: float = 90.0
    memory_warning: float = 75.0   # Memory usage %
    memory_critical: float = 90.0
    response_time_warning: float = 1000.0   # ms
    response_time_critical: float = 3000.0
    error_rate_warning: float = 2.0         # %
    error_rate_critical: float = 5.0
    cache_hit_rate_warning: float = 70.0    # %
    throughput_min: float = 10.0            # requests/second

class MetricCollector:
    """Collects system and application metrics"""
    
    def __init__(self, collection_interval: float = 5.0):
        self.collection_interval = collection_interval
        self.metrics_history: Dict[MetricType, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.custom_collectors: Dict[str, Callable] = {}
        self.is_collecting = False
        
    def register_custom_collector(self, name: str, collector_func: Callable):
        """Register custom metric collector function"""
        self.custom_collectors[name] = collector_func
    
    async def start_collection(self):
        """Start metric collection"""
        self.is_collecting = True
        await self._collection_loop()
    
    def stop_collection(self):
        """Stop metric collection"""
        self.is_collecting = False
    
    async def _collection_loop(self):
        """Main collection loop"""
        while self.is_collecting:
            try:
                # Collect system metrics
                await self._collect_system_metrics()
                
                # Collect custom metrics
                await self._collect_custom_metrics()
                
                await asyncio.sleep(self.collection_interval)
                
            except Exception as e:
                print(f"Metric collection error: {e}")
                await asyncio.sleep(self.collection_interval)
    
    async def _collect_system_metrics(self):
        """Collect system-level metrics"""
        timestamp = datetime.now(timezone.utc)
        
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=None)
        self.metrics_history[MetricType.CPU_USAGE].append(
            MetricPoint(MetricType.CPU_USAGE, cpu_percent, timestamp)
        )
        
        # Memory usage
        memory = psutil.virtual_memory()
        self.metrics_history[MetricType.MEMORY_USAGE].append(
            MetricPoint(MetricType.MEMORY_USAGE, memory.percent, timestamp)
        )
    
    async def _collect_custom_metrics(self):
        """Collect custom application metrics"""
        timestamp = datetime.now(timezone.utc)
        
        for name, collector in self.custom_collectors.items():
            try:
                result = collector()
                if isinstance(result, dict):
                    for metric_name, value in result.items():
                        if hasattr(MetricType, metric_name.upper()):
                            metric_type = MetricType(metric_name.lower())
                            self.metrics_history[metric_type].append(
                                MetricPoint(metric_type, value, timestamp, {"collector": name})
                            )
            except Exception as e:
                print(f"Custom collector {name} error: {e}")
    
    def add_metric_point(self, metric_type: MetricType, value: float, 
                        metadata: Optional[Dict[str, Any]] = None):
        """Add a metric point manually"""
        timestamp = datetime.now(timezone.utc)
        point = MetricPoint(metric_type, value, timestamp, metadata or {})
        self.metrics_history[metric_type].append(point)
    
    def get_recent_metrics(self, metric_type: MetricType, 
                          minutes: int = 5) -> List[MetricPoint]:
        """Get recent metrics for a specific type"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        
        if metric_type not in self.metrics_history:
            return []
        
        return [
            point for point in self.metrics_history[metric_type]
            if point.timestamp > cutoff_time
        ]
    
    def calculate_average(self, metric_type: MetricType, minutes: int = 5) -> float:
        """Calculate average value for a metric over time period"""
        recent_metrics = self.get_recent_metrics(metric_type, minutes)
        
        if not recent_metrics:
            return 0.0
        
        return sum(point.value for point in recent_metrics) / len(recent_metrics)
    
    def calculate_percentile(self, metric_type: MetricType, percentile: float, 
                           minutes: int = 5) -> float:
        """Calculate percentile for a metric"""
        recent_metrics = self.get_recent_metrics(metric_type, minutes)
        
        if not recent_metrics:
            return 0.0
        
        values = [point.value for point in recent_metrics]
        return np.percentile(values, percentile)

class AlertManager:
    """Manages alerts and notifications"""
    
    def __init__(self, max_alerts: int = 1000):
        self.max_alerts = max_alerts
        self.active_alerts: List[Alert] = []
        self.alert_history: deque = deque(maxlen=max_alerts)
        self.alert_callbacks: Dict[AlertLevel, List[Callable]] = defaultdict(list)
        self.suppression_rules: Dict[str, Dict[str, Any]] = {}
        
    def register_alert_callback(self, level: AlertLevel, callback: Callable):
        """Register callback for specific alert level"""
        self.alert_callbacks[level].append(callback)
    
    def add_suppression_rule(self, rule_name: str, metric_type: MetricType,
                           duration_minutes: int = 10):
        """Add alert suppression rule to prevent spam"""
        self.suppression_rules[rule_name] = {
            "metric_type": metric_type,
            "duration": timedelta(minutes=duration_minutes),
            "last_triggered": None
        }
    
    async def trigger_alert(self, alert: Alert) -> bool:
        """Trigger an alert if not suppressed"""
        
        # Check suppression rules
        rule_key = f"{alert.metric_type.value}_{alert.level.value}"
        if rule_key in self.suppression_rules:
            rule = self.suppression_rules[rule_key]
            if (rule["last_triggered"] and 
                datetime.now(timezone.utc) - rule["last_triggered"] < rule["duration"]):
                return False  # Suppressed
            
            rule["last_triggered"] = datetime.now(timezone.utc)
        
        # Add to active alerts
        self.active_alerts.append(alert)
        self.alert_history.append(alert)
        
        # Trigger callbacks
        for callback in self.alert_callbacks[alert.level]:
            try:
                await callback(alert)
            except Exception as e:
                print(f"Alert callback error: {e}")
        
        return True
    
    def resolve_alert(self, metric_type: MetricType, level: AlertLevel) -> bool:
        """Resolve active alerts for specific metric and level"""
        
        resolved_count = 0
        self.active_alerts = [
            alert for alert in self.active_alerts
            if not (alert.metric_type == metric_type and alert.level == level)
        ]
        
        return resolved_count > 0
    
    def get_active_alerts(self, level: Optional[AlertLevel] = None) -> List[Alert]:
        """Get active alerts, optionally filtered by level"""
        if level:
            return [alert for alert in self.active_alerts if alert.level == level]
        return self.active_alerts.copy()
    
    def get_alert_stats(self) -> Dict[str, Any]:
        """Get alert statistics"""
        level_counts = defaultdict(int)
        metric_counts = defaultdict(int)
        
        for alert in self.alert_history:
            level_counts[alert.level.value] += 1
            metric_counts[alert.metric_type.value] += 1
        
        return {
            "active_alerts": len(self.active_alerts),
            "total_alerts_24h": len(self.alert_history),
            "alerts_by_level": dict(level_counts),
            "alerts_by_metric": dict(metric_counts)
        }

class AutoScaler:
    """Intelligent auto-scaling based on metrics and predictions"""
    
    def __init__(self, metric_collector: MetricCollector):
        self.metric_collector = metric_collector
        self.scaling_history: List[Dict[str, Any]] = []
        self.scaling_callbacks: Dict[ScalingAction, List[Callable]] = defaultdict(list)
        self.cooldown_periods: Dict[ScalingAction, timedelta] = {
            ScalingAction.SCALE_UP: timedelta(minutes=10),
            ScalingAction.SCALE_DOWN: timedelta(minutes=15),
            ScalingAction.OPTIMIZE_CACHE: timedelta(minutes=5),
            ScalingAction.COMPRESS_DATA: timedelta(minutes=30)
        }
        self.last_scaling_actions: Dict[ScalingAction, datetime] = {}
        
    def register_scaling_callback(self, action: ScalingAction, callback: Callable):
        """Register callback for scaling action"""
        self.scaling_callbacks[action].append(callback)
    
    async def evaluate_scaling_needs(self) -> List[ScalingAction]:
        """Evaluate if scaling is needed and return recommended actions"""
        
        recommended_actions = []
        
        # Check CPU usage
        cpu_avg = self.metric_collector.calculate_average(MetricType.CPU_USAGE, 5)
        cpu_p95 = self.metric_collector.calculate_percentile(MetricType.CPU_USAGE, 95, 5)
        
        if cpu_p95 > 85:
            recommended_actions.append(ScalingAction.SCALE_UP)
        elif cpu_avg < 30 and cpu_p95 < 50:
            recommended_actions.append(ScalingAction.SCALE_DOWN)
        
        # Check memory usage
        memory_avg = self.metric_collector.calculate_average(MetricType.MEMORY_USAGE, 5)
        
        if memory_avg > 80:
            recommended_actions.extend([
                ScalingAction.OPTIMIZE_CACHE,
                ScalingAction.COMPRESS_DATA,
                ScalingAction.CLEAR_LOW_PRIORITY
            ])
        
        # Check response time
        response_time_p95 = self.metric_collector.calculate_percentile(
            MetricType.RESPONSE_TIME, 95, 5
        )
        
        if response_time_p95 > 2000:  # 2 seconds
            recommended_actions.extend([
                ScalingAction.INCREASE_WORKERS,
                ScalingAction.OPTIMIZE_CACHE
            ])
        
        # Check cache hit rate
        cache_hit_rate = self.metric_collector.calculate_average(MetricType.CACHE_HIT_RATE, 10)
        
        if cache_hit_rate < 60:  # Below 60%
            recommended_actions.append(ScalingAction.OPTIMIZE_CACHE)
        
        # Remove actions that are in cooldown
        filtered_actions = []
        for action in recommended_actions:
            if self._can_execute_action(action):
                filtered_actions.append(action)
        
        return filtered_actions
    
    def _can_execute_action(self, action: ScalingAction) -> bool:
        """Check if action can be executed (not in cooldown)"""
        
        if action not in self.last_scaling_actions:
            return True
        
        cooldown = self.cooldown_periods.get(action, timedelta(minutes=5))
        last_executed = self.last_scaling_actions[action]
        
        return datetime.now(timezone.utc) - last_executed > cooldown
    
    async def execute_scaling_action(self, action: ScalingAction,
                                   metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Execute a scaling action"""
        
        if not self._can_execute_action(action):
            return False
        
        success = False
        
        # Execute callbacks for the action
        for callback in self.scaling_callbacks[action]:
            try:
                result = await callback(metadata or {})
                if result:
                    success = True
            except Exception as e:
                print(f"Scaling callback error for {action}: {e}")
        
        if success:
            # Record the action
            self.last_scaling_actions[action] = datetime.now(timezone.utc)
            
            scaling_record = {
                "action": action.value,
                "timestamp": datetime.now(timezone.utc),
                "metadata": metadata or {},
                "trigger_metrics": {
                    "cpu_usage": self.metric_collector.calculate_average(MetricType.CPU_USAGE, 1),
                    "memory_usage": self.metric_collector.calculate_average(MetricType.MEMORY_USAGE, 1),
                    "response_time": self.metric_collector.calculate_average(MetricType.RESPONSE_TIME, 1)
                }
            }
            
            self.scaling_history.append(scaling_record)
            
            # Keep only recent history
            if len(self.scaling_history) > 100:
                self.scaling_history.pop(0)
        
        return success
    
    def get_scaling_stats(self) -> Dict[str, Any]:
        """Get scaling statistics"""
        
        action_counts = defaultdict(int)
        recent_actions = []
        
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
        
        for record in self.scaling_history:
            action_counts[record["action"]] += 1
            if record["timestamp"] > cutoff_time:
                recent_actions.append(record)
        
        return {
            "total_scaling_actions": len(self.scaling_history),
            "actions_24h": len(recent_actions),
            "actions_by_type": dict(action_counts),
            "recent_actions": recent_actions[-10:],  # Last 10 actions
            "cooldown_status": {
                action.value: self._can_execute_action(action)
                for action in ScalingAction
            }
        }

class PerformanceMonitor:
    """
    Main performance monitoring system with auto-scaling capabilities
    """
    
    def __init__(self, collection_interval: float = 5.0):
        self.collection_interval = collection_interval
        
        # Core components
        self.metric_collector = MetricCollector(collection_interval)
        self.alert_manager = AlertManager()
        self.auto_scaler = AutoScaler(self.metric_collector)
        self.thresholds = PerformanceThresholds()
        
        # Monitoring state
        self.is_running = False
        self.monitoring_tasks: List[asyncio.Task] = []
        
        # Performance baselines
        self.baseline_metrics = {}
        self.anomaly_detection_enabled = True
        
    async def start_monitoring(self):
        """Start the performance monitoring system"""
        
        if self.is_running:
            return
        
        self.is_running = True
        
        # Start metric collection
        collection_task = asyncio.create_task(self.metric_collector.start_collection())
        self.monitoring_tasks.append(collection_task)
        
        # Start alert evaluation
        alert_task = asyncio.create_task(self._alert_evaluation_loop())
        self.monitoring_tasks.append(alert_task)
        
        # Start auto-scaling evaluation
        scaling_task = asyncio.create_task(self._scaling_evaluation_loop())
        self.monitoring_tasks.append(scaling_task)
        
        # Start anomaly detection
        if self.anomaly_detection_enabled:
            anomaly_task = asyncio.create_task(self._anomaly_detection_loop())
            self.monitoring_tasks.append(anomaly_task)
        
        print("Performance monitoring system started")
    
    async def stop_monitoring(self):
        """Stop the performance monitoring system"""
        
        self.is_running = False
        self.metric_collector.stop_collection()
        
        # Cancel all monitoring tasks
        for task in self.monitoring_tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        self.monitoring_tasks.clear()
        print("Performance monitoring system stopped")
    
    async def _alert_evaluation_loop(self):
        """Main alert evaluation loop"""
        
        while self.is_running:
            try:
                await self._evaluate_alerts()
                await asyncio.sleep(self.collection_interval)
            except Exception as e:
                print(f"Alert evaluation error: {e}")
                await asyncio.sleep(self.collection_interval)
    
    async def _evaluate_alerts(self):
        """Evaluate metrics against thresholds and trigger alerts"""
        
        # CPU alerts
        cpu_avg = self.metric_collector.calculate_average(MetricType.CPU_USAGE, 2)
        
        if cpu_avg > self.thresholds.cpu_critical:
            alert = Alert(
                level=AlertLevel.CRITICAL,
                message=f"CPU usage critical: {cpu_avg:.1f}%",
                metric_type=MetricType.CPU_USAGE,
                current_value=cpu_avg,
                threshold=self.thresholds.cpu_critical,
                timestamp=datetime.now(timezone.utc),
                suggested_actions=[ScalingAction.SCALE_UP, ScalingAction.INCREASE_WORKERS]
            )
            await self.alert_manager.trigger_alert(alert)
        
        elif cpu_avg > self.thresholds.cpu_warning:
            alert = Alert(
                level=AlertLevel.WARNING,
                message=f"CPU usage high: {cpu_avg:.1f}%",
                metric_type=MetricType.CPU_USAGE,
                current_value=cpu_avg,
                threshold=self.thresholds.cpu_warning,
                timestamp=datetime.now(timezone.utc),
                suggested_actions=[ScalingAction.OPTIMIZE_CACHE]
            )
            await self.alert_manager.trigger_alert(alert)
        
        # Memory alerts
        memory_avg = self.metric_collector.calculate_average(MetricType.MEMORY_USAGE, 2)
        
        if memory_avg > self.thresholds.memory_critical:
            alert = Alert(
                level=AlertLevel.CRITICAL,
                message=f"Memory usage critical: {memory_avg:.1f}%",
                metric_type=MetricType.MEMORY_USAGE,
                current_value=memory_avg,
                threshold=self.thresholds.memory_critical,
                timestamp=datetime.now(timezone.utc),
                suggested_actions=[
                    ScalingAction.CLEAR_LOW_PRIORITY,
                    ScalingAction.COMPRESS_DATA,
                    ScalingAction.OPTIMIZE_CACHE
                ]
            )
            await self.alert_manager.trigger_alert(alert)
        
        # Response time alerts
        response_time_p95 = self.metric_collector.calculate_percentile(
            MetricType.RESPONSE_TIME, 95, 2
        )
        
        if response_time_p95 > self.thresholds.response_time_critical:
            alert = Alert(
                level=AlertLevel.CRITICAL,
                message=f"Response time critical: {response_time_p95:.0f}ms",
                metric_type=MetricType.RESPONSE_TIME,
                current_value=response_time_p95,
                threshold=self.thresholds.response_time_critical,
                timestamp=datetime.now(timezone.utc),
                suggested_actions=[ScalingAction.INCREASE_WORKERS, ScalingAction.OPTIMIZE_CACHE]
            )
            await self.alert_manager.trigger_alert(alert)
    
    async def _scaling_evaluation_loop(self):
        """Main auto-scaling evaluation loop"""
        
        while self.is_running:
            try:
                # Wait longer between scaling evaluations
                await asyncio.sleep(30)
                
                # Evaluate scaling needs
                recommended_actions = await self.auto_scaler.evaluate_scaling_needs()
                
                # Execute high-priority actions automatically
                for action in recommended_actions:
                    if action in [ScalingAction.OPTIMIZE_CACHE, ScalingAction.CLEAR_LOW_PRIORITY]:
                        success = await self.auto_scaler.execute_scaling_action(action)
                        if success:
                            print(f"Auto-executed scaling action: {action.value}")
                
            except Exception as e:
                print(f"Scaling evaluation error: {e}")
                await asyncio.sleep(30)
    
    async def _anomaly_detection_loop(self):
        """Detect anomalies in metrics"""
        
        while self.is_running:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                await self._detect_anomalies()
                
            except Exception as e:
                print(f"Anomaly detection error: {e}")
                await asyncio.sleep(60)
    
    async def _detect_anomalies(self):
        """Simple anomaly detection based on statistical methods"""
        
        for metric_type in [MetricType.CPU_USAGE, MetricType.MEMORY_USAGE, MetricType.RESPONSE_TIME]:
            recent_values = [
                point.value for point in 
                self.metric_collector.get_recent_metrics(metric_type, 30)
            ]
            
            if len(recent_values) < 10:
                continue
            
            # Calculate z-score for recent values
            mean_val = np.mean(recent_values)
            std_val = np.std(recent_values)
            
            if std_val == 0:
                continue
            
            # Check last few values for anomalies
            recent_few = recent_values[-3:]
            for value in recent_few:
                z_score = abs((value - mean_val) / std_val)
                
                if z_score > 3:  # 3-sigma rule
                    alert = Alert(
                        level=AlertLevel.WARNING,
                        message=f"Anomaly detected in {metric_type.value}: {value:.2f} (z-score: {z_score:.2f})",
                        metric_type=metric_type,
                        current_value=value,
                        threshold=mean_val + 3 * std_val,
                        timestamp=datetime.now(timezone.utc),
                        metadata={"z_score": z_score, "mean": mean_val, "std": std_val}
                    )
                    await self.alert_manager.trigger_alert(alert)
    
    def register_metric_collector(self, name: str, collector_func: Callable):
        """Register custom metric collector"""
        self.metric_collector.register_custom_collector(name, collector_func)
    
    def add_metric(self, metric_type: MetricType, value: float,
                  metadata: Optional[Dict[str, Any]] = None):
        """Add a metric point manually"""
        self.metric_collector.add_metric_point(metric_type, value, metadata)
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "is_running": self.is_running,
            "current_metrics": {
                "cpu_usage": self.metric_collector.calculate_average(MetricType.CPU_USAGE, 1),
                "memory_usage": self.metric_collector.calculate_average(MetricType.MEMORY_USAGE, 1),
                "response_time_p95": self.metric_collector.calculate_percentile(MetricType.RESPONSE_TIME, 95, 5),
                "cache_hit_rate": self.metric_collector.calculate_average(MetricType.CACHE_HIT_RATE, 5),
                "active_sessions": self.metric_collector.calculate_average(MetricType.ACTIVE_SESSIONS, 1)
            },
            "alerts": self.alert_manager.get_alert_stats(),
            "scaling": self.auto_scaler.get_scaling_stats(),
            "thresholds": {
                "cpu_warning": self.thresholds.cpu_warning,
                "cpu_critical": self.thresholds.cpu_critical,
                "memory_warning": self.thresholds.memory_warning,
                "memory_critical": self.thresholds.memory_critical,
                "response_time_warning": self.thresholds.response_time_warning,
                "response_time_critical": self.thresholds.response_time_critical
            }
        }
    
    def get_metrics_summary(self, hours: int = 1) -> Dict[str, Any]:
        """Get metrics summary for specified time period"""
        
        summary = {}
        
        for metric_type in MetricType:
            recent_metrics = self.metric_collector.get_recent_metrics(metric_type, hours * 60)
            
            if recent_metrics:
                values = [point.value for point in recent_metrics]
                summary[metric_type.value] = {
                    "count": len(values),
                    "average": np.mean(values),
                    "min": np.min(values),
                    "max": np.max(values),
                    "p50": np.percentile(values, 50),
                    "p95": np.percentile(values, 95),
                    "p99": np.percentile(values, 99)
                }
        
        return summary