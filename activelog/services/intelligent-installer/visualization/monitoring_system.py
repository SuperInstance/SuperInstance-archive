"""
Advanced Monitoring System
Comprehensive system monitoring, alerting, and performance analysis
"""

import asyncio
import json
import logging
import os
import uuid
import time
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional, Any, Set, Tuple, Callable
from enum import Enum
from pathlib import Path
import statistics
import heapq

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

try:
    from scipy import stats
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

logger = logging.getLogger(__name__)

class MetricType(Enum):
    GAUGE = "gauge"          # Point-in-time value
    COUNTER = "counter"      # Monotonically increasing
    HISTOGRAM = "histogram"  # Distribution of values
    SUMMARY = "summary"      # Summary statistics
    RATE = "rate"           # Rate of change

class AlertSeverity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

class AlertStatus(Enum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"

class MonitoringScope(Enum):
    SYSTEM = "system"
    APPLICATION = "application"
    NETWORK = "network"
    DATABASE = "database"
    CUSTOM = "custom"

@dataclass
class Metric:
    name: str
    value: float
    metric_type: MetricType
    timestamp: datetime
    tags: Dict[str, str]
    scope: MonitoringScope
    unit: Optional[str] = None
    description: Optional[str] = None

@dataclass
class AlertRule:
    rule_id: str
    name: str
    description: str
    metric_name: str
    condition: str  # e.g., "> 90", "< 10", "== 0"
    threshold: float
    severity: AlertSeverity
    duration: timedelta  # How long condition must be true
    enabled: bool = True
    tags: Dict[str, str] = field(default_factory=dict)
    notification_channels: List[str] = field(default_factory=list)

@dataclass
class Alert:
    alert_id: str
    rule_id: str
    metric_name: str
    current_value: float
    threshold: float
    severity: AlertSeverity
    status: AlertStatus
    message: str
    started_at: datetime
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    tags: Dict[str, str] = field(default_factory=dict)

@dataclass
class PerformanceBaseline:
    metric_name: str
    baseline_value: float
    standard_deviation: float
    confidence_interval: Tuple[float, float]
    sample_size: int
    calculated_at: datetime
    valid_until: datetime

@dataclass
class TrendAnalysis:
    metric_name: str
    trend_direction: str  # "increasing", "decreasing", "stable"
    trend_strength: float  # 0-1
    correlation_coefficient: float
    forecast_values: List[float]
    forecast_timestamps: List[datetime]
    analysis_period: timedelta
    calculated_at: datetime

class MetricsCollector:
    """Advanced metrics collection system"""
    
    def __init__(self, storage_path: str):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.metrics_buffer: List[Metric] = []
        self.buffer_size = 1000
        self.flush_interval = 30  # seconds
        
        self.custom_collectors: Dict[str, Callable] = {}
        self.collection_tasks: Dict[str, asyncio.Task] = {}
        
        self.logger = logging.getLogger(__name__)
        
        # Start background tasks
        asyncio.create_task(self._start_collection_tasks())
    
    async def collect_system_metrics(self) -> List[Metric]:
        """Collect comprehensive system metrics"""
        metrics = []
        timestamp = datetime.utcnow()
        
        try:
            if PSUTIL_AVAILABLE:
                # CPU metrics
                cpu_percent = psutil.cpu_percent(interval=1)
                cpu_count = psutil.cpu_count()
                load_avg = psutil.getloadavg() if hasattr(psutil, 'getloadavg') else (0, 0, 0)
                
                metrics.extend([
                    Metric("cpu_usage_percent", cpu_percent, MetricType.GAUGE, timestamp, 
                          {"scope": "system"}, MonitoringScope.SYSTEM, "%"),
                    Metric("cpu_count", cpu_count, MetricType.GAUGE, timestamp,
                          {"scope": "system"}, MonitoringScope.SYSTEM, "cores"),
                    Metric("load_average_1m", load_avg[0], MetricType.GAUGE, timestamp,
                          {"scope": "system"}, MonitoringScope.SYSTEM)
                ])
                
                # Memory metrics
                memory = psutil.virtual_memory()
                metrics.extend([
                    Metric("memory_total", memory.total, MetricType.GAUGE, timestamp,
                          {"scope": "system"}, MonitoringScope.SYSTEM, "bytes"),
                    Metric("memory_available", memory.available, MetricType.GAUGE, timestamp,
                          {"scope": "system"}, MonitoringScope.SYSTEM, "bytes"),
                    Metric("memory_percent", memory.percent, MetricType.GAUGE, timestamp,
                          {"scope": "system"}, MonitoringScope.SYSTEM, "%"),
                    Metric("memory_used", memory.used, MetricType.GAUGE, timestamp,
                          {"scope": "system"}, MonitoringScope.SYSTEM, "bytes")
                ])
                
                # Disk metrics
                disk_usage = psutil.disk_usage('/')
                disk_io = psutil.disk_io_counters()
                
                metrics.extend([
                    Metric("disk_total", disk_usage.total, MetricType.GAUGE, timestamp,
                          {"scope": "system", "mount": "/"}, MonitoringScope.SYSTEM, "bytes"),
                    Metric("disk_free", disk_usage.free, MetricType.GAUGE, timestamp,
                          {"scope": "system", "mount": "/"}, MonitoringScope.SYSTEM, "bytes"),
                    Metric("disk_percent", (disk_usage.used / disk_usage.total) * 100, MetricType.GAUGE, timestamp,
                          {"scope": "system", "mount": "/"}, MonitoringScope.SYSTEM, "%")
                ])
                
                if disk_io:
                    metrics.extend([
                        Metric("disk_read_bytes", disk_io.read_bytes, MetricType.COUNTER, timestamp,
                              {"scope": "system"}, MonitoringScope.SYSTEM, "bytes"),
                        Metric("disk_write_bytes", disk_io.write_bytes, MetricType.COUNTER, timestamp,
                              {"scope": "system"}, MonitoringScope.SYSTEM, "bytes")
                    ])
                
                # Network metrics
                network_io = psutil.net_io_counters()
                if network_io:
                    metrics.extend([
                        Metric("network_bytes_sent", network_io.bytes_sent, MetricType.COUNTER, timestamp,
                              {"scope": "system"}, MonitoringScope.NETWORK, "bytes"),
                        Metric("network_bytes_recv", network_io.bytes_recv, MetricType.COUNTER, timestamp,
                              {"scope": "system"}, MonitoringScope.NETWORK, "bytes"),
                        Metric("network_packets_sent", network_io.packets_sent, MetricType.COUNTER, timestamp,
                              {"scope": "system"}, MonitoringScope.NETWORK),
                        Metric("network_packets_recv", network_io.packets_recv, MetricType.COUNTER, timestamp,
                              {"scope": "system"}, MonitoringScope.NETWORK)
                    ])
                
                # Process metrics
                process_count = len(psutil.pids())
                metrics.append(
                    Metric("process_count", process_count, MetricType.GAUGE, timestamp,
                          {"scope": "system"}, MonitoringScope.SYSTEM)
                )
                
            else:
                # Fallback metrics without psutil
                import os
                load_avg = os.getloadavg() if hasattr(os, 'getloadavg') else (0, 0, 0)
                metrics.append(
                    Metric("load_average_1m", load_avg[0], MetricType.GAUGE, timestamp,
                          {"scope": "system"}, MonitoringScope.SYSTEM)
                )
                
        except Exception as e:
            self.logger.error(f"System metrics collection failed: {e}")
            # Add error metric
            metrics.append(
                Metric("metrics_collection_error", 1, MetricType.COUNTER, timestamp,
                      {"error": str(e)}, MonitoringScope.SYSTEM)
            )
        
        return metrics
    
    async def collect_application_metrics(self) -> List[Metric]:
        """Collect application-specific metrics"""
        metrics = []
        timestamp = datetime.utcnow()
        
        try:
            # Current process metrics
            if PSUTIL_AVAILABLE:
                current_process = psutil.Process()
                
                # Process CPU and memory
                cpu_percent = current_process.cpu_percent()
                memory_info = current_process.memory_info()
                
                metrics.extend([
                    Metric("app_cpu_percent", cpu_percent, MetricType.GAUGE, timestamp,
                          {"scope": "application", "process": "current"}, MonitoringScope.APPLICATION, "%"),
                    Metric("app_memory_rss", memory_info.rss, MetricType.GAUGE, timestamp,
                          {"scope": "application", "process": "current"}, MonitoringScope.APPLICATION, "bytes"),
                    Metric("app_memory_vms", memory_info.vms, MetricType.GAUGE, timestamp,
                          {"scope": "application", "process": "current"}, MonitoringScope.APPLICATION, "bytes"),
                ])
                
                # Thread and file descriptor counts
                num_threads = current_process.num_threads()
                try:
                    num_fds = current_process.num_fds()
                    metrics.append(
                        Metric("app_file_descriptors", num_fds, MetricType.GAUGE, timestamp,
                              {"scope": "application", "process": "current"}, MonitoringScope.APPLICATION)
                    )
                except:
                    pass  # Not available on all platforms
                
                metrics.append(
                    Metric("app_thread_count", num_threads, MetricType.GAUGE, timestamp,
                          {"scope": "application", "process": "current"}, MonitoringScope.APPLICATION)
                )
            
            # Python-specific metrics
            import gc
            import sys
            
            # Garbage collection stats
            gc_stats = gc.get_stats()
            if gc_stats:
                for i, gen_stats in enumerate(gc_stats):
                    metrics.extend([
                        Metric(f"gc_gen{i}_collections", gen_stats['collections'], MetricType.COUNTER, timestamp,
                              {"scope": "application", "generation": str(i)}, MonitoringScope.APPLICATION),
                        Metric(f"gc_gen{i}_collected", gen_stats['collected'], MetricType.COUNTER, timestamp,
                              {"scope": "application", "generation": str(i)}, MonitoringScope.APPLICATION),
                        Metric(f"gc_gen{i}_uncollectable", gen_stats['uncollectable'], MetricType.COUNTER, timestamp,
                              {"scope": "application", "generation": str(i)}, MonitoringScope.APPLICATION)
                    ])
            
            # Object counts
            metrics.append(
                Metric("python_objects_count", len(gc.get_objects()), MetricType.GAUGE, timestamp,
                      {"scope": "application"}, MonitoringScope.APPLICATION)
            )
            
        except Exception as e:
            self.logger.error(f"Application metrics collection failed: {e}")
            metrics.append(
                Metric("app_metrics_collection_error", 1, MetricType.COUNTER, timestamp,
                      {"error": str(e)}, MonitoringScope.APPLICATION)
            )
        
        return metrics
    
    async def register_custom_collector(self, name: str, collector_func: Callable) -> bool:
        """Register custom metrics collector"""
        try:
            self.custom_collectors[name] = collector_func
            
            # Start collection task
            task = asyncio.create_task(self._custom_collection_loop(name, collector_func))
            self.collection_tasks[name] = task
            
            self.logger.info(f"Custom collector registered: {name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to register custom collector: {e}")
            return False
    
    async def store_metric(self, metric: Metric):
        """Store metric in buffer"""
        self.metrics_buffer.append(metric)
        
        if len(self.metrics_buffer) >= self.buffer_size:
            await self._flush_metrics()
    
    async def _start_collection_tasks(self):
        """Start system and application metrics collection"""
        # System metrics collection
        asyncio.create_task(self._system_metrics_loop())
        asyncio.create_task(self._application_metrics_loop())
        asyncio.create_task(self._metrics_flush_loop())
    
    async def _system_metrics_loop(self):
        """System metrics collection loop"""
        while True:
            try:
                metrics = await self.collect_system_metrics()
                for metric in metrics:
                    await self.store_metric(metric)
                
                await asyncio.sleep(30)  # Collect every 30 seconds
                
            except Exception as e:
                self.logger.error(f"System metrics collection loop error: {e}")
                await asyncio.sleep(60)
    
    async def _application_metrics_loop(self):
        """Application metrics collection loop"""
        while True:
            try:
                metrics = await self.collect_application_metrics()
                for metric in metrics:
                    await self.store_metric(metric)
                
                await asyncio.sleep(15)  # Collect every 15 seconds
                
            except Exception as e:
                self.logger.error(f"Application metrics collection loop error: {e}")
                await asyncio.sleep(30)
    
    async def _custom_collection_loop(self, name: str, collector_func: Callable):
        """Custom collector loop"""
        while True:
            try:
                metrics = await collector_func()
                if metrics:
                    for metric in metrics:
                        await self.store_metric(metric)
                
                await asyncio.sleep(60)  # Collect every minute
                
            except Exception as e:
                self.logger.error(f"Custom collector {name} error: {e}")
                await asyncio.sleep(120)
    
    async def _metrics_flush_loop(self):
        """Periodic metrics flush to storage"""
        while True:
            try:
                await asyncio.sleep(self.flush_interval)
                await self._flush_metrics()
                
            except Exception as e:
                self.logger.error(f"Metrics flush loop error: {e}")
    
    async def _flush_metrics(self):
        """Flush metrics buffer to persistent storage"""
        try:
            if not self.metrics_buffer:
                return
            
            # Create timestamped file
            timestamp = datetime.utcnow()
            filename = f"metrics_{timestamp.strftime('%Y%m%d_%H%M%S')}.json"
            filepath = self.storage_path / filename
            
            # Serialize metrics
            metrics_data = [asdict(metric) for metric in self.metrics_buffer]
            for data in metrics_data:
                data['timestamp'] = data['timestamp'].isoformat()
            
            # Write to file
            with open(filepath, 'w') as f:
                json.dump(metrics_data, f, indent=2, default=str)
            
            # Clear buffer
            self.metrics_buffer.clear()
            
            self.logger.debug(f"Flushed {len(metrics_data)} metrics to {filename}")
            
        except Exception as e:
            self.logger.error(f"Metrics flush failed: {e}")

class AlertManager:
    """Advanced alerting system"""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector
        self.alert_rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        
        self.notification_channels: Dict[str, Callable] = {}
        self.evaluation_interval = 30  # seconds
        
        self.logger = logging.getLogger(__name__)
        
        # Start alert evaluation
        asyncio.create_task(self._start_alert_evaluation())
    
    async def add_alert_rule(self, rule: AlertRule) -> bool:
        """Add new alert rule"""
        try:
            # Validate rule
            if not self._validate_alert_rule(rule):
                return False
            
            self.alert_rules[rule.rule_id] = rule
            self.logger.info(f"Alert rule added: {rule.name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add alert rule: {e}")
            return False
    
    async def evaluate_alerts(self) -> List[Alert]:
        """Evaluate all alert rules against current metrics"""
        new_alerts = []
        
        try:
            # Get recent metrics for evaluation
            recent_metrics = await self._get_recent_metrics()
            
            for rule in self.alert_rules.values():
                if not rule.enabled:
                    continue
                
                # Find metrics matching this rule
                matching_metrics = [m for m in recent_metrics if m.name == rule.metric_name]
                
                if not matching_metrics:
                    continue
                
                # Evaluate condition
                alert = await self._evaluate_rule_condition(rule, matching_metrics)
                
                if alert:
                    new_alerts.append(alert)
                    await self._handle_new_alert(alert)
            
            return new_alerts
            
        except Exception as e:
            self.logger.error(f"Alert evaluation failed: {e}")
            return []
    
    async def _evaluate_rule_condition(self, rule: AlertRule, metrics: List[Metric]) -> Optional[Alert]:
        """Evaluate specific alert rule condition"""
        try:
            if not metrics:
                return None
            
            # Get latest metric value
            latest_metric = max(metrics, key=lambda m: m.timestamp)
            current_value = latest_metric.value
            
            # Parse and evaluate condition
            condition_met = self._evaluate_condition(rule.condition, current_value, rule.threshold)
            
            if condition_met:
                # Check if alert already exists
                existing_alert_key = f"{rule.rule_id}_{rule.metric_name}"
                
                if existing_alert_key not in self.active_alerts:
                    # Create new alert
                    alert = Alert(
                        alert_id=str(uuid.uuid4()),
                        rule_id=rule.rule_id,
                        metric_name=rule.metric_name,
                        current_value=current_value,
                        threshold=rule.threshold,
                        severity=rule.severity,
                        status=AlertStatus.OPEN,
                        message=f"{rule.name}: {rule.metric_name} {rule.condition} {rule.threshold} (current: {current_value})",
                        started_at=datetime.utcnow(),
                        tags=rule.tags.copy()
                    )
                    
                    self.active_alerts[existing_alert_key] = alert
                    return alert
            else:
                # Check if we should resolve existing alert
                existing_alert_key = f"{rule.rule_id}_{rule.metric_name}"
                if existing_alert_key in self.active_alerts:
                    alert = self.active_alerts[existing_alert_key]
                    alert.status = AlertStatus.RESOLVED
                    alert.resolved_at = datetime.utcnow()
                    
                    # Move to history
                    self.alert_history.append(alert)
                    del self.active_alerts[existing_alert_key]
                    
                    await self._handle_resolved_alert(alert)
            
            return None
            
        except Exception as e:
            self.logger.error(f"Rule condition evaluation failed: {e}")
            return None
    
    def _evaluate_condition(self, condition: str, current_value: float, threshold: float) -> bool:
        """Evaluate alert condition"""
        try:
            condition = condition.strip()
            
            if condition.startswith('>'):
                if condition.startswith('>='):
                    return current_value >= threshold
                else:
                    return current_value > threshold
            elif condition.startswith('<'):
                if condition.startswith('<='):
                    return current_value <= threshold
                else:
                    return current_value < threshold
            elif condition.startswith('=='):
                return abs(current_value - threshold) < 0.001  # Floating point comparison
            elif condition.startswith('!='):
                return abs(current_value - threshold) >= 0.001
            else:
                # Default to greater than
                return current_value > threshold
                
        except Exception as e:
            self.logger.error(f"Condition evaluation failed: {e}")
            return False
    
    async def _handle_new_alert(self, alert: Alert):
        """Handle new alert"""
        try:
            self.logger.warning(f"New alert: {alert.message}")
            
            # Send notifications
            rule = self.alert_rules.get(alert.rule_id)
            if rule and rule.notification_channels:
                for channel in rule.notification_channels:
                    await self._send_notification(channel, alert, 'new')
            
        except Exception as e:
            self.logger.error(f"New alert handling failed: {e}")
    
    async def _handle_resolved_alert(self, alert: Alert):
        """Handle resolved alert"""
        try:
            self.logger.info(f"Alert resolved: {alert.message}")
            
            # Send resolution notifications
            rule = self.alert_rules.get(alert.rule_id)
            if rule and rule.notification_channels:
                for channel in rule.notification_channels:
                    await self._send_notification(channel, alert, 'resolved')
            
        except Exception as e:
            self.logger.error(f"Resolved alert handling failed: {e}")
    
    async def _send_notification(self, channel: str, alert: Alert, event_type: str):
        """Send alert notification"""
        try:
            if channel in self.notification_channels:
                await self.notification_channels[channel](alert, event_type)
            else:
                self.logger.warning(f"Unknown notification channel: {channel}")
                
        except Exception as e:
            self.logger.error(f"Notification send failed: {e}")
    
    async def _get_recent_metrics(self, window_minutes: int = 5) -> List[Metric]:
        """Get recent metrics for alert evaluation"""
        # This would query the metrics storage
        # For now, return empty list as metrics are in buffer
        return []
    
    def _validate_alert_rule(self, rule: AlertRule) -> bool:
        """Validate alert rule"""
        if not rule.rule_id or not rule.name or not rule.metric_name:
            return False
        
        if not rule.condition or rule.threshold is None:
            return False
        
        return True
    
    async def _start_alert_evaluation(self):
        """Start alert evaluation loop"""
        while True:
            try:
                await self.evaluate_alerts()
                await asyncio.sleep(self.evaluation_interval)
                
            except Exception as e:
                self.logger.error(f"Alert evaluation loop error: {e}")
                await asyncio.sleep(self.evaluation_interval * 2)

class PerformanceAnalyzer:
    """Performance analysis and baseline calculation"""
    
    def __init__(self):
        self.baselines: Dict[str, PerformanceBaseline] = {}
        self.metric_history: Dict[str, List[Tuple[datetime, float]]] = {}
        self.logger = logging.getLogger(__name__)
    
    async def calculate_baseline(self, metric_name: str, 
                               historical_data: List[Tuple[datetime, float]],
                               confidence_level: float = 0.95) -> Optional[PerformanceBaseline]:
        """Calculate performance baseline for metric"""
        try:
            if len(historical_data) < 30:  # Need minimum data points
                return None
            
            values = [value for _, value in historical_data]
            
            if NUMPY_AVAILABLE and SCIPY_AVAILABLE:
                # Statistical analysis with numpy/scipy
                values_array = np.array(values)
                
                mean_value = np.mean(values_array)
                std_dev = np.std(values_array)
                
                # Calculate confidence interval
                confidence_interval = stats.t.interval(
                    confidence_level, 
                    len(values) - 1,
                    loc=mean_value, 
                    scale=stats.sem(values_array)
                )
            else:
                # Fallback statistical calculations
                mean_value = sum(values) / len(values)
                variance = sum((x - mean_value) ** 2 for x in values) / len(values)
                std_dev = variance ** 0.5
                
                # Approximate confidence interval
                margin = 1.96 * (std_dev / (len(values) ** 0.5))  # 95% CI approximation
                confidence_interval = (mean_value - margin, mean_value + margin)
            
            baseline = PerformanceBaseline(
                metric_name=metric_name,
                baseline_value=mean_value,
                standard_deviation=std_dev,
                confidence_interval=confidence_interval,
                sample_size=len(values),
                calculated_at=datetime.utcnow(),
                valid_until=datetime.utcnow() + timedelta(days=7)
            )
            
            self.baselines[metric_name] = baseline
            self.logger.info(f"Baseline calculated for {metric_name}: {mean_value:.2f} ± {std_dev:.2f}")
            
            return baseline
            
        except Exception as e:
            self.logger.error(f"Baseline calculation failed: {e}")
            return None
    
    async def detect_anomalies(self, metric_name: str, 
                              current_value: float,
                              sensitivity: float = 2.0) -> bool:
        """Detect anomalies using baseline comparison"""
        try:
            baseline = self.baselines.get(metric_name)
            if not baseline or baseline.valid_until < datetime.utcnow():
                return False
            
            # Calculate z-score
            z_score = abs(current_value - baseline.baseline_value) / baseline.standard_deviation
            
            # Anomaly if z-score exceeds sensitivity threshold
            is_anomaly = z_score > sensitivity
            
            if is_anomaly:
                self.logger.warning(f"Anomaly detected in {metric_name}: {current_value} (z-score: {z_score:.2f})")
            
            return is_anomaly
            
        except Exception as e:
            self.logger.error(f"Anomaly detection failed: {e}")
            return False

class TrendAnalyzer:
    """Trend analysis and forecasting"""
    
    def __init__(self):
        self.trend_cache: Dict[str, TrendAnalysis] = {}
        self.logger = logging.getLogger(__name__)
    
    async def analyze_trend(self, metric_name: str,
                           time_series_data: List[Tuple[datetime, float]],
                           forecast_periods: int = 10) -> Optional[TrendAnalysis]:
        """Analyze trend and generate forecast"""
        try:
            if len(time_series_data) < 10:
                return None
            
            # Extract values and convert timestamps to numeric
            timestamps = [ts.timestamp() for ts, _ in time_series_data]
            values = [value for _, value in time_series_data]
            
            # Simple linear regression for trend analysis
            if NUMPY_AVAILABLE:
                x = np.array(timestamps)
                y = np.array(values)
                
                # Calculate correlation coefficient
                correlation = np.corrcoef(x, y)[0, 1] if len(x) > 1 else 0
                
                # Linear regression
                slope, intercept = np.polyfit(x, y, 1)
                
                # Determine trend direction
                if abs(correlation) < 0.1:
                    trend_direction = "stable"
                elif slope > 0:
                    trend_direction = "increasing"
                else:
                    trend_direction = "decreasing"
                
                # Generate forecast
                last_timestamp = timestamps[-1]
                forecast_timestamps = []
                forecast_values = []
                
                for i in range(1, forecast_periods + 1):
                    future_timestamp = last_timestamp + (i * 300)  # 5-minute intervals
                    future_value = slope * future_timestamp + intercept
                    
                    forecast_timestamps.append(datetime.fromtimestamp(future_timestamp))
                    forecast_values.append(future_value)
                    
            else:
                # Fallback simple trend analysis
                if len(values) < 2:
                    return None
                
                # Calculate simple trend
                first_half = values[:len(values)//2]
                second_half = values[len(values)//2:]
                
                first_avg = sum(first_half) / len(first_half)
                second_avg = sum(second_half) / len(second_half)
                
                if abs(second_avg - first_avg) < (first_avg * 0.05):  # 5% threshold
                    trend_direction = "stable"
                elif second_avg > first_avg:
                    trend_direction = "increasing"
                else:
                    trend_direction = "decreasing"
                
                correlation = 0.5 if trend_direction != "stable" else 0.1
                
                # Simple forecast (last value)
                last_value = values[-1]
                forecast_timestamps = [datetime.utcnow() + timedelta(minutes=5*i) for i in range(1, forecast_periods + 1)]
                forecast_values = [last_value] * forecast_periods
            
            analysis = TrendAnalysis(
                metric_name=metric_name,
                trend_direction=trend_direction,
                trend_strength=abs(correlation),
                correlation_coefficient=correlation,
                forecast_values=forecast_values,
                forecast_timestamps=forecast_timestamps,
                analysis_period=time_series_data[-1][0] - time_series_data[0][0],
                calculated_at=datetime.utcnow()
            )
            
            self.trend_cache[metric_name] = analysis
            self.logger.info(f"Trend analysis completed for {metric_name}: {trend_direction} trend")
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Trend analysis failed: {e}")
            return None

class MonitoringSystem:
    """Main monitoring system orchestrator"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        storage_path = config.get('storage_path', './monitoring_data')
        self.metrics_collector = MetricsCollector(storage_path)
        self.alert_manager = AlertManager(self.metrics_collector)
        self.performance_analyzer = PerformanceAnalyzer()
        self.trend_analyzer = TrendAnalyzer()
        
        self.logger = logging.getLogger(__name__)
    
    async def initialize(self) -> bool:
        """Initialize monitoring system"""
        try:
            self.logger.info("Initializing advanced monitoring system...")
            
            # Setup default alert rules
            await self._setup_default_alert_rules()
            
            # Setup notification channels
            await self._setup_notification_channels()
            
            # Start monitoring tasks
            await self._start_monitoring_tasks()
            
            self.logger.info("Monitoring system initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Monitoring system initialization failed: {e}")
            return False
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        try:
            # Collect current metrics
            system_metrics = await self.metrics_collector.collect_system_metrics()
            app_metrics = await self.metrics_collector.collect_application_metrics()
            
            # Get active alerts
            active_alerts = list(self.alert_manager.active_alerts.values())
            
            # Calculate health score
            health_score = self._calculate_health_score(system_metrics, active_alerts)
            
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'health_score': health_score,
                'status': self._determine_overall_status(health_score, active_alerts),
                'system_metrics': [asdict(m) for m in system_metrics],
                'application_metrics': [asdict(m) for m in app_metrics],
                'active_alerts': [asdict(a) for a in active_alerts],
                'alert_summary': {
                    'total': len(active_alerts),
                    'critical': len([a for a in active_alerts if a.severity == AlertSeverity.CRITICAL]),
                    'high': len([a for a in active_alerts if a.severity == AlertSeverity.HIGH]),
                    'medium': len([a for a in active_alerts if a.severity == AlertSeverity.MEDIUM])
                }
            }
            
        except Exception as e:
            self.logger.error(f"System status retrieval failed: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def _calculate_health_score(self, metrics: List[Metric], alerts: List[Alert]) -> float:
        """Calculate overall system health score (0-100)"""
        try:
            base_score = 100.0
            
            # Deduct points for alerts
            for alert in alerts:
                if alert.severity == AlertSeverity.CRITICAL:
                    base_score -= 25
                elif alert.severity == AlertSeverity.HIGH:
                    base_score -= 15
                elif alert.severity == AlertSeverity.MEDIUM:
                    base_score -= 5
            
            # Deduct points for high resource utilization
            for metric in metrics:
                if metric.name == 'cpu_usage_percent' and metric.value > 90:
                    base_score -= 10
                elif metric.name == 'memory_percent' and metric.value > 90:
                    base_score -= 10
                elif metric.name == 'disk_percent' and metric.value > 95:
                    base_score -= 15
            
            return max(0.0, min(100.0, base_score))
            
        except Exception as e:
            self.logger.error(f"Health score calculation failed: {e}")
            return 50.0  # Default to average health
    
    def _determine_overall_status(self, health_score: float, alerts: List[Alert]) -> str:
        """Determine overall system status"""
        critical_alerts = [a for a in alerts if a.severity == AlertSeverity.CRITICAL]
        
        if critical_alerts or health_score < 50:
            return "critical"
        elif health_score < 70:
            return "warning"
        elif health_score < 90:
            return "good"
        else:
            return "excellent"
    
    async def _setup_default_alert_rules(self):
        """Setup default alert rules"""
        default_rules = [
            AlertRule(
                rule_id="high_cpu_usage",
                name="High CPU Usage",
                description="CPU usage is above 90%",
                metric_name="cpu_usage_percent",
                condition="> 90",
                threshold=90.0,
                severity=AlertSeverity.HIGH,
                duration=timedelta(minutes=2)
            ),
            AlertRule(
                rule_id="high_memory_usage", 
                name="High Memory Usage",
                description="Memory usage is above 90%",
                metric_name="memory_percent",
                condition="> 90",
                threshold=90.0,
                severity=AlertSeverity.HIGH,
                duration=timedelta(minutes=5)
            ),
            AlertRule(
                rule_id="disk_space_low",
                name="Low Disk Space",
                description="Disk space is above 95%",
                metric_name="disk_percent",
                condition="> 95",
                threshold=95.0,
                severity=AlertSeverity.CRITICAL,
                duration=timedelta(minutes=1)
            )
        ]
        
        for rule in default_rules:
            await self.alert_manager.add_alert_rule(rule)
    
    async def _setup_notification_channels(self):
        """Setup notification channels"""
        # Console notification channel
        async def console_notification(alert: Alert, event_type: str):
            severity_emoji = {
                AlertSeverity.CRITICAL: "🚨",
                AlertSeverity.HIGH: "⚠️",
                AlertSeverity.MEDIUM: "📋",
                AlertSeverity.LOW: "ℹ️"
            }
            
            emoji = severity_emoji.get(alert.severity, "📊")
            print(f"{emoji} {event_type.upper()}: {alert.message}")
        
        self.alert_manager.notification_channels['console'] = console_notification