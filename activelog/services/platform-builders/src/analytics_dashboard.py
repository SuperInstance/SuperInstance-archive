#!/usr/bin/env python3
"""
Advanced Visualization and Analytics Dashboard

Comprehensive real-time dashboard system providing advanced visualizations,
analytics, and insights for the platform builders service.
"""

import asyncio
import time
import threading
import json
import logging
import statistics
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from collections import deque, defaultdict, Counter
import hashlib
import base64

logger = logging.getLogger(__name__)


class ChartType(Enum):
    LINE = "line"
    BAR = "bar"
    PIE = "pie"
    SCATTER = "scatter"
    HEATMAP = "heatmap"
    GAUGE = "gauge"
    TREEMAP = "treemap"
    SANKEY = "sankey"


class MetricType(Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


class AlertLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class DataPoint:
    timestamp: float
    value: Union[float, int, str]
    labels: Dict[str, str] = None
    
    def __post_init__(self):
        if self.labels is None:
            self.labels = {}


@dataclass
class Metric:
    name: str
    type: MetricType
    description: str
    unit: str
    data_points: deque
    aggregation_window: float = 300.0  # 5 minutes default
    
    def __post_init__(self):
        if not isinstance(self.data_points, deque):
            self.data_points = deque(maxlen=10000)


@dataclass
class ChartConfig:
    id: str
    title: str
    type: ChartType
    metrics: List[str]
    width: int = 12
    height: int = 300
    refresh_interval: int = 5000  # milliseconds
    color_scheme: str = "default"
    options: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.options is None:
            self.options = {}


@dataclass
class Dashboard:
    id: str
    name: str
    description: str
    charts: List[ChartConfig]
    layout: Dict[str, Any]
    filters: Dict[str, Any] = None
    auto_refresh: bool = True
    
    def __post_init__(self):
        if self.filters is None:
            self.filters = {}


@dataclass
class Alert:
    id: str
    name: str
    description: str
    level: AlertLevel
    condition: str  # Simple condition expression
    metric: str
    threshold: float
    is_active: bool = False
    triggered_at: Optional[float] = None
    resolved_at: Optional[float] = None


class MetricsCollector:
    """Advanced metrics collection and aggregation system"""
    
    def __init__(self, retention_hours: int = 24):
        self.metrics = {}
        self.retention_seconds = retention_hours * 3600
        self.collection_lock = threading.Lock()
        self.aggregation_cache = {}
        self.collection_start_time = time.time()
        
    def register_metric(self, metric: Metric):
        """Register a new metric"""
        with self.collection_lock:
            self.metrics[metric.name] = metric
            logger.info(f"Registered metric: {metric.name} ({metric.type.value})")
    
    def add_data_point(self, metric_name: str, value: Union[float, int], 
                      labels: Dict[str, str] = None, timestamp: float = None):
        """Add a data point to a metric"""
        if timestamp is None:
            timestamp = time.time()
        
        if metric_name not in self.metrics:
            # Auto-register simple gauge metric
            self.register_metric(Metric(
                name=metric_name,
                type=MetricType.GAUGE,
                description=f"Auto-registered metric: {metric_name}",
                unit="",
                data_points=deque(maxlen=10000)
            ))
        
        data_point = DataPoint(timestamp=timestamp, value=value, labels=labels or {})
        
        with self.collection_lock:
            self.metrics[metric_name].data_points.append(data_point)
            
            # Clear old data points
            cutoff_time = timestamp - self.retention_seconds
            metric = self.metrics[metric_name]
            while metric.data_points and metric.data_points[0].timestamp < cutoff_time:
                metric.data_points.popleft()
    
    def get_metric_data(self, metric_name: str, start_time: float = None, 
                       end_time: float = None, aggregation: str = None) -> List[Dict[str, Any]]:
        """Get metric data with optional time range and aggregation"""
        if metric_name not in self.metrics:
            return []
        
        current_time = time.time()
        if start_time is None:
            start_time = current_time - 3600  # Last hour by default
        if end_time is None:
            end_time = current_time
        
        metric = self.metrics[metric_name]
        
        with self.collection_lock:
            # Filter by time range
            filtered_points = [
                dp for dp in metric.data_points
                if start_time <= dp.timestamp <= end_time
            ]
        
        if not filtered_points:
            return []
        
        # Apply aggregation if specified
        if aggregation:
            return self._apply_aggregation(filtered_points, aggregation, metric.aggregation_window)
        
        # Return raw data points
        return [
            {
                'timestamp': dp.timestamp,
                'value': dp.value,
                'labels': dp.labels
            }
            for dp in filtered_points
        ]
    
    def _apply_aggregation(self, data_points: List[DataPoint], aggregation: str, 
                         window_seconds: float) -> List[Dict[str, Any]]:
        """Apply aggregation to data points"""
        if not data_points:
            return []
        
        # Group data points by time windows
        windows = defaultdict(list)
        start_time = data_points[0].timestamp
        
        for dp in data_points:
            window_key = int((dp.timestamp - start_time) // window_seconds)
            windows[window_key].append(dp.value)
        
        # Apply aggregation function
        aggregated_data = []
        for window_key in sorted(windows.keys()):
            window_timestamp = start_time + (window_key * window_seconds)
            values = windows[window_key]
            
            if aggregation == "avg":
                aggregated_value = statistics.mean(values)
            elif aggregation == "sum":
                aggregated_value = sum(values)
            elif aggregation == "min":
                aggregated_value = min(values)
            elif aggregation == "max":
                aggregated_value = max(values)
            elif aggregation == "count":
                aggregated_value = len(values)
            elif aggregation == "stddev":
                aggregated_value = statistics.stdev(values) if len(values) > 1 else 0
            else:
                aggregated_value = statistics.mean(values)  # Default to average
            
            aggregated_data.append({
                'timestamp': window_timestamp,
                'value': aggregated_value,
                'count': len(values)
            })
        
        return aggregated_data
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of all metrics"""
        summary = {}
        current_time = time.time()
        
        with self.collection_lock:
            for name, metric in self.metrics.items():
                if not metric.data_points:
                    continue
                
                # Recent data points (last 5 minutes)
                recent_points = [
                    dp for dp in metric.data_points
                    if dp.timestamp > current_time - 300
                ]
                
                if recent_points:
                    values = [dp.value for dp in recent_points if isinstance(dp.value, (int, float))]
                    
                    if values:
                        summary[name] = {
                            'type': metric.type.value,
                            'unit': metric.unit,
                            'total_points': len(metric.data_points),
                            'recent_points': len(recent_points),
                            'latest_value': recent_points[-1].value,
                            'latest_timestamp': recent_points[-1].timestamp,
                            'avg_value': statistics.mean(values),
                            'min_value': min(values),
                            'max_value': max(values)
                        }
                    else:
                        summary[name] = {
                            'type': metric.type.value,
                            'unit': metric.unit,
                            'total_points': len(metric.data_points),
                            'recent_points': len(recent_points),
                            'latest_value': recent_points[-1].value,
                            'latest_timestamp': recent_points[-1].timestamp
                        }
        
        return summary


class AlertManager:
    """Advanced alerting system for dashboard metrics"""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector
        self.alerts = {}
        self.alert_history = deque(maxlen=1000)
        self.evaluation_lock = threading.Lock()
        self.notification_callbacks = []
        
    def register_alert(self, alert: Alert):
        """Register a new alert"""
        with self.evaluation_lock:
            self.alerts[alert.id] = alert
            logger.info(f"Registered alert: {alert.name} for metric {alert.metric}")
    
    def add_notification_callback(self, callback: callable):
        """Add callback for alert notifications"""
        self.notification_callbacks.append(callback)
    
    async def evaluate_alerts(self):
        """Evaluate all registered alerts"""
        current_time = time.time()
        
        for alert_id, alert in self.alerts.items():
            try:
                await self._evaluate_single_alert(alert, current_time)
            except Exception as e:
                logger.error(f"Error evaluating alert {alert_id}: {e}")
    
    async def _evaluate_single_alert(self, alert: Alert, current_time: float):
        """Evaluate a single alert"""
        # Get recent metric data
        metric_data = self.metrics_collector.get_metric_data(
            alert.metric,
            start_time=current_time - 300,  # Last 5 minutes
            end_time=current_time
        )
        
        if not metric_data:
            return
        
        # Get latest value
        latest_value = metric_data[-1]['value']
        
        # Evaluate condition
        condition_met = self._evaluate_condition(alert.condition, latest_value, alert.threshold)
        
        # Handle alert state changes
        if condition_met and not alert.is_active:
            # Alert triggered
            alert.is_active = True
            alert.triggered_at = current_time
            alert.resolved_at = None
            
            await self._send_alert_notification(alert, "triggered", latest_value)
            self._add_to_history(alert, "triggered", latest_value)
            
        elif not condition_met and alert.is_active:
            # Alert resolved
            alert.is_active = False
            alert.resolved_at = current_time
            
            await self._send_alert_notification(alert, "resolved", latest_value)
            self._add_to_history(alert, "resolved", latest_value)
    
    def _evaluate_condition(self, condition: str, value: float, threshold: float) -> bool:
        """Evaluate alert condition"""
        conditions = {
            "gt": value > threshold,
            "gte": value >= threshold,
            "lt": value < threshold,
            "lte": value <= threshold,
            "eq": value == threshold,
            "ne": value != threshold
        }
        return conditions.get(condition, False)
    
    async def _send_alert_notification(self, alert: Alert, action: str, value: float):
        """Send alert notification to registered callbacks"""
        notification = {
            'alert_id': alert.id,
            'alert_name': alert.name,
            'action': action,
            'level': alert.level.value,
            'metric': alert.metric,
            'value': value,
            'threshold': alert.threshold,
            'timestamp': time.time()
        }
        
        for callback in self.notification_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(notification)
                else:
                    callback(notification)
            except Exception as e:
                logger.error(f"Error in alert notification callback: {e}")
    
    def _add_to_history(self, alert: Alert, action: str, value: float):
        """Add alert event to history"""
        history_entry = {
            'alert_id': alert.id,
            'alert_name': alert.name,
            'action': action,
            'level': alert.level.value,
            'metric': alert.metric,
            'value': value,
            'threshold': alert.threshold,
            'timestamp': time.time()
        }
        self.alert_history.append(history_entry)
    
    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get all currently active alerts"""
        return [
            {
                'id': alert.id,
                'name': alert.name,
                'level': alert.level.value,
                'metric': alert.metric,
                'triggered_at': alert.triggered_at
            }
            for alert in self.alerts.values()
            if alert.is_active
        ]
    
    def get_alert_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get alert history for specified hours"""
        cutoff_time = time.time() - (hours * 3600)
        return [
            entry for entry in self.alert_history
            if entry['timestamp'] > cutoff_time
        ]


class DashboardRenderer:
    """Dashboard rendering and data preparation system"""
    
    def __init__(self, metrics_collector: MetricsCollector, alert_manager: AlertManager):
        self.metrics_collector = metrics_collector
        self.alert_manager = alert_manager
        self.dashboards = {}
        self.chart_cache = {}
        self.cache_ttl = 30  # 30 seconds cache TTL
        
    def register_dashboard(self, dashboard: Dashboard):
        """Register a new dashboard"""
        self.dashboards[dashboard.id] = dashboard
        logger.info(f"Registered dashboard: {dashboard.name}")
    
    async def render_dashboard(self, dashboard_id: str, filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Render dashboard with all charts and data"""
        if dashboard_id not in self.dashboards:
            raise ValueError(f"Dashboard {dashboard_id} not found")
        
        dashboard = self.dashboards[dashboard_id]
        current_time = time.time()
        
        # Apply filters
        effective_filters = {**(dashboard.filters or {}), **(filters or {})}
        
        # Render all charts
        charts_data = []
        for chart_config in dashboard.charts:
            chart_data = await self._render_chart(chart_config, effective_filters, current_time)
            charts_data.append(chart_data)
        
        # Get alerts
        active_alerts = self.alert_manager.get_active_alerts()
        
        # Get metrics summary
        metrics_summary = self.metrics_collector.get_metrics_summary()
        
        return {
            'dashboard': {
                'id': dashboard.id,
                'name': dashboard.name,
                'description': dashboard.description,
                'layout': dashboard.layout,
                'auto_refresh': dashboard.auto_refresh
            },
            'charts': charts_data,
            'alerts': active_alerts,
            'metrics_summary': metrics_summary,
            'rendered_at': current_time,
            'filters_applied': effective_filters
        }
    
    async def _render_chart(self, chart_config: ChartConfig, filters: Dict[str, Any], 
                           current_time: float) -> Dict[str, Any]:
        """Render individual chart"""
        cache_key = self._get_cache_key(chart_config, filters)
        
        # Check cache
        if cache_key in self.chart_cache:
            cached_data = self.chart_cache[cache_key]
            if current_time - cached_data['cached_at'] < self.cache_ttl:
                return cached_data['data']
        
        # Get time range from filters
        start_time = filters.get('start_time', current_time - 3600)  # Last hour
        end_time = filters.get('end_time', current_time)
        aggregation = filters.get('aggregation', 'avg')
        
        # Collect data for all metrics in chart
        chart_data = {
            'id': chart_config.id,
            'title': chart_config.title,
            'type': chart_config.type.value,
            'width': chart_config.width,
            'height': chart_config.height,
            'refresh_interval': chart_config.refresh_interval,
            'color_scheme': chart_config.color_scheme,
            'options': chart_config.options,
            'datasets': []
        }
        
        for metric_name in chart_config.metrics:
            metric_data = self.metrics_collector.get_metric_data(
                metric_name, start_time, end_time, aggregation
            )
            
            if metric_data:
                dataset = {
                    'label': metric_name,
                    'data': metric_data,
                    'metric_name': metric_name
                }
                chart_data['datasets'].append(dataset)
        
        # Cache the result
        self.chart_cache[cache_key] = {
            'data': chart_data,
            'cached_at': current_time
        }
        
        return chart_data
    
    def _get_cache_key(self, chart_config: ChartConfig, filters: Dict[str, Any]) -> str:
        """Generate cache key for chart"""
        key_data = {
            'chart_id': chart_config.id,
            'metrics': sorted(chart_config.metrics),
            'filters': sorted(filters.items()) if filters else []
        }
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def get_dashboard_list(self) -> List[Dict[str, Any]]:
        """Get list of all dashboards"""
        return [
            {
                'id': dashboard.id,
                'name': dashboard.name,
                'description': dashboard.description,
                'chart_count': len(dashboard.charts)
            }
            for dashboard in self.dashboards.values()
        ]


class AnalyticsDashboard:
    """Main analytics dashboard system"""
    
    def __init__(self):
        self.metrics_collector = MetricsCollector()
        self.alert_manager = AlertManager(self.metrics_collector)
        self.dashboard_renderer = DashboardRenderer(self.metrics_collector, self.alert_manager)
        
        # Monitoring state
        self.is_running = False
        self.monitoring_task = None
        
        # Setup default dashboards and alerts
        self._setup_default_dashboards()
        self._setup_default_alerts()
    
    async def start(self):
        """Start the analytics dashboard"""
        if self.is_running:
            return
        
        self.is_running = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Analytics dashboard started")
    
    async def stop(self):
        """Stop the analytics dashboard"""
        if not self.is_running:
            return
        
        self.is_running = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Analytics dashboard stopped")
    
    async def _monitoring_loop(self):
        """Main monitoring and alert evaluation loop"""
        while self.is_running:
            try:
                # Evaluate alerts
                await self.alert_manager.evaluate_alerts()
                
                # Wait before next evaluation
                await asyncio.sleep(30)  # Evaluate every 30 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in dashboard monitoring loop: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    def _setup_default_dashboards(self):
        """Setup default dashboards"""
        # System Overview Dashboard
        system_dashboard = Dashboard(
            id="system_overview",
            name="System Overview",
            description="Overall system performance metrics",
            charts=[
                ChartConfig(
                    id="cpu_usage",
                    title="CPU Usage",
                    type=ChartType.LINE,
                    metrics=["cpu_percent"],
                    width=6,
                    height=300,
                    options={"yAxis": {"max": 100, "unit": "%"}}
                ),
                ChartConfig(
                    id="memory_usage",
                    title="Memory Usage",
                    type=ChartType.LINE,
                    metrics=["memory_percent"],
                    width=6,
                    height=300,
                    options={"yAxis": {"max": 100, "unit": "%"}}
                ),
                ChartConfig(
                    id="active_builds",
                    title="Active Builds",
                    type=ChartType.BAR,
                    metrics=["active_builds_count"],
                    width=6,
                    height=300
                ),
                ChartConfig(
                    id="build_success_rate",
                    title="Build Success Rate",
                    type=ChartType.GAUGE,
                    metrics=["build_success_rate"],
                    width=6,
                    height=300,
                    options={"gauge": {"max": 100, "unit": "%"}}
                )
            ],
            layout={"columns": 12, "rows": "auto"}
        )
        self.dashboard_renderer.register_dashboard(system_dashboard)
        
        # Build Performance Dashboard
        build_dashboard = Dashboard(
            id="build_performance",
            name="Build Performance",
            description="Build system performance and statistics",
            charts=[
                ChartConfig(
                    id="build_duration",
                    title="Build Duration Trends",
                    type=ChartType.LINE,
                    metrics=["avg_build_duration", "max_build_duration"],
                    width=12,
                    height=300,
                    options={"yAxis": {"unit": "seconds"}}
                ),
                ChartConfig(
                    id="builds_by_platform",
                    title="Builds by Platform",
                    type=ChartType.PIE,
                    metrics=["builds_by_platform"],
                    width=6,
                    height=300
                ),
                ChartConfig(
                    id="error_rate",
                    title="Build Error Rate",
                    type=ChartType.LINE,
                    metrics=["build_error_rate"],
                    width=6,
                    height=300,
                    options={"yAxis": {"max": 100, "unit": "%"}}
                )
            ],
            layout={"columns": 12, "rows": "auto"}
        )
        self.dashboard_renderer.register_dashboard(build_dashboard)
        
        # Performance Bottlenecks Dashboard
        bottlenecks_dashboard = Dashboard(
            id="performance_bottlenecks",
            name="Performance Bottlenecks",
            description="Real-time performance bottleneck analysis",
            charts=[
                ChartConfig(
                    id="bottleneck_count",
                    title="Active Bottlenecks",
                    type=ChartType.BAR,
                    metrics=["bottleneck_count"],
                    width=6,
                    height=300
                ),
                ChartConfig(
                    id="bottleneck_types",
                    title="Bottleneck Types",
                    type=ChartType.PIE,
                    metrics=["bottleneck_types"],
                    width=6,
                    height=300
                ),
                ChartConfig(
                    id="resolution_effectiveness",
                    title="Resolution Effectiveness",
                    type=ChartType.LINE,
                    metrics=["resolution_success_rate"],
                    width=12,
                    height=300,
                    options={"yAxis": {"max": 100, "unit": "%"}}
                )
            ],
            layout={"columns": 12, "rows": "auto"}
        )
        self.dashboard_renderer.register_dashboard(bottlenecks_dashboard)
    
    def _setup_default_alerts(self):
        """Setup default alert rules"""
        alerts = [
            Alert(
                id="high_cpu_usage",
                name="High CPU Usage",
                description="CPU usage is above 80%",
                level=AlertLevel.WARNING,
                condition="gt",
                metric="cpu_percent",
                threshold=80.0
            ),
            Alert(
                id="critical_cpu_usage",
                name="Critical CPU Usage",
                description="CPU usage is above 95%",
                level=AlertLevel.CRITICAL,
                condition="gt",
                metric="cpu_percent",
                threshold=95.0
            ),
            Alert(
                id="high_memory_usage",
                name="High Memory Usage",
                description="Memory usage is above 85%",
                level=AlertLevel.WARNING,
                condition="gt",
                metric="memory_percent",
                threshold=85.0
            ),
            Alert(
                id="build_failure_rate",
                name="High Build Failure Rate",
                description="Build failure rate is above 10%",
                level=AlertLevel.ERROR,
                condition="gt",
                metric="build_error_rate",
                threshold=10.0
            ),
            Alert(
                id="performance_bottlenecks",
                name="Multiple Performance Bottlenecks",
                description="More than 5 active bottlenecks detected",
                level=AlertLevel.WARNING,
                condition="gt",
                metric="bottleneck_count",
                threshold=5.0
            )
        ]
        
        for alert in alerts:
            self.alert_manager.register_alert(alert)
    
    # Public API methods
    
    def add_metric_data(self, metric_name: str, value: Union[float, int], 
                       labels: Dict[str, str] = None):
        """Add data point to a metric"""
        self.metrics_collector.add_data_point(metric_name, value, labels)
    
    def register_metric(self, metric: Metric):
        """Register a new metric"""
        self.metrics_collector.register_metric(metric)
    
    def register_alert(self, alert: Alert):
        """Register a new alert"""
        self.alert_manager.register_alert(alert)
    
    def register_dashboard(self, dashboard: Dashboard):
        """Register a new dashboard"""
        self.dashboard_renderer.register_dashboard(dashboard)
    
    async def get_dashboard(self, dashboard_id: str, filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get rendered dashboard data"""
        return await self.dashboard_renderer.render_dashboard(dashboard_id, filters)
    
    def get_dashboards(self) -> List[Dict[str, Any]]:
        """Get list of available dashboards"""
        return self.dashboard_renderer.get_dashboard_list()
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get metrics summary"""
        return self.metrics_collector.get_metrics_summary()
    
    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get active alerts"""
        return self.alert_manager.get_active_alerts()
    
    def get_alert_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get alert history"""
        return self.alert_manager.get_alert_history(hours)
    
    def add_alert_callback(self, callback: callable):
        """Add alert notification callback"""
        self.alert_manager.add_notification_callback(callback)


# Global dashboard instance
_global_dashboard: Optional[AnalyticsDashboard] = None


def get_dashboard() -> AnalyticsDashboard:
    """Get global analytics dashboard instance"""
    global _global_dashboard
    if _global_dashboard is None:
        _global_dashboard = AnalyticsDashboard()
    return _global_dashboard


async def start_dashboard():
    """Start global analytics dashboard"""
    dashboard = get_dashboard()
    await dashboard.start()


async def stop_dashboard():
    """Stop global analytics dashboard"""
    dashboard = get_dashboard()
    await dashboard.stop()