#!/usr/bin/env python3
"""
System Monitoring and Alerting for Adaptive UX System

This module provides comprehensive system monitoring, health checks, alerting,
and observability for the adaptive UX system components.
"""

import asyncio
import json
import logging
import psutil
import time
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union
from enum import Enum
from dataclasses import dataclass, asdict, field
from collections import defaultdict, deque
import threading
from concurrent.futures import ThreadPoolExecutor

class AlertLevel(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class MetricType(Enum):
    """Types of system metrics"""
    SYSTEM_HEALTH = "system_health"
    PERFORMANCE = "performance"
    USER_ACTIVITY = "user_activity"
    ERROR_RATE = "error_rate"
    RESPONSE_TIME = "response_time"
    MEMORY_USAGE = "memory_usage"
    CPU_USAGE = "cpu_usage"
    DISK_USAGE = "disk_usage"
    NETWORK_IO = "network_io"
    DATABASE_HEALTH = "database_health"
    CACHE_PERFORMANCE = "cache_performance"

class ComponentStatus(Enum):
    """Status of system components"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    OFFLINE = "offline"
    UNKNOWN = "unknown"

@dataclass
class SystemMetric:
    """System metric data point"""
    metric_type: MetricType
    component: str
    value: float
    unit: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
@dataclass  
class HealthCheck:
    """Health check definition"""
    check_id: str
    name: str
    description: str
    component: str
    check_function: Callable[[], bool]
    interval_seconds: int = 60
    timeout_seconds: int = 30
    enabled: bool = True
    last_run: Optional[datetime] = None
    last_status: ComponentStatus = ComponentStatus.UNKNOWN
    consecutive_failures: int = 0
    max_failures: int = 3

@dataclass
class Alert:
    """System alert"""
    alert_id: str
    level: AlertLevel
    title: str
    description: str
    component: str
    metric_type: Optional[MetricType] = None
    value: Optional[float] = None
    threshold: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ComponentHealth:
    """Health status of a system component"""
    component: str
    status: ComponentStatus
    last_checked: datetime
    health_score: float  # 0.0 to 1.0
    issues: List[str] = field(default_factory=list)
    metrics: Dict[str, float] = field(default_factory=dict)
    uptime_percentage: float = 100.0

class SystemMonitor:
    """Core system monitoring functionality"""
    
    def __init__(self):
        self.metrics: deque = deque(maxlen=10000)
        self.health_checks: Dict[str, HealthCheck] = {}
        self.component_health: Dict[str, ComponentHealth] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: deque = deque(maxlen=1000)
        
        self.monitoring_active = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        self.logger = logging.getLogger(__name__)
        self._initialize_default_health_checks()
    
    def _initialize_default_health_checks(self):
        """Initialize default system health checks"""
        checks = [
            HealthCheck(
                "system_cpu",
                "CPU Usage",
                "Monitor system CPU utilization",
                "system",
                self._check_cpu_usage,
                interval_seconds=30
            ),
            HealthCheck(
                "system_memory",
                "Memory Usage", 
                "Monitor system memory utilization",
                "system",
                self._check_memory_usage,
                interval_seconds=30
            ),
            HealthCheck(
                "system_disk",
                "Disk Usage",
                "Monitor disk space utilization",
                "system",
                self._check_disk_usage,
                interval_seconds=300  # 5 minutes
            ),
            HealthCheck(
                "adaptive_ux_api",
                "Adaptive UX API",
                "Check if Adaptive UX API is responding",
                "adaptive_ux",
                self._check_api_health,
                interval_seconds=60
            ),
            HealthCheck(
                "interface_intelligence",
                "Interface Intelligence",
                "Check Interface Intelligence component",
                "adaptive_ux",
                self._check_interface_intelligence,
                interval_seconds=120
            ),
            HealthCheck(
                "progressive_disclosure",
                "Progressive Disclosure",
                "Check Progressive Disclosure engine",
                "adaptive_ux",
                self._check_progressive_disclosure,
                interval_seconds=120
            )
        ]
        
        for check in checks:
            self.health_checks[check.check_id] = check
    
    def start_monitoring(self):
        """Start system monitoring"""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        self.logger.info("System monitoring started")
    
    def stop_monitoring(self):
        """Stop system monitoring"""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        self.executor.shutdown(wait=False)
        self.logger.info("System monitoring stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.monitoring_active:
            try:
                # Run health checks
                self._run_scheduled_health_checks()
                
                # Collect system metrics
                self._collect_system_metrics()
                
                # Update component health
                self._update_component_health()
                
                # Check alert conditions
                self._check_alert_conditions()
                
                # Sleep before next iteration
                time.sleep(10)  # Run every 10 seconds
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                time.sleep(30)  # Wait longer on error
    
    def _run_scheduled_health_checks(self):
        """Run health checks that are due"""
        now = datetime.utcnow()
        
        for check in self.health_checks.values():
            if not check.enabled:
                continue
            
            # Check if it's time to run this check
            if (check.last_run is None or 
                (now - check.last_run).total_seconds() >= check.interval_seconds):
                
                self._run_health_check(check)
    
    def _run_health_check(self, check: HealthCheck):
        """Run a single health check"""
        try:
            start_time = time.time()
            
            # Run the check function with timeout
            future = self.executor.submit(check.check_function)
            success = future.result(timeout=check.timeout_seconds)
            
            execution_time = time.time() - start_time
            
            # Update check status
            check.last_run = datetime.utcnow()
            
            if success:
                check.last_status = ComponentStatus.HEALTHY
                check.consecutive_failures = 0
            else:
                check.consecutive_failures += 1
                if check.consecutive_failures >= check.max_failures:
                    check.last_status = ComponentStatus.UNHEALTHY
                else:
                    check.last_status = ComponentStatus.DEGRADED
            
            # Record metric
            self._record_metric(
                MetricType.SYSTEM_HEALTH,
                check.component,
                1.0 if success else 0.0,
                "boolean",
                {"check_id": check.check_id, "execution_time": execution_time}
            )
            
            self.logger.debug(f"Health check {check.check_id}: {'PASS' if success else 'FAIL'}")
            
        except Exception as e:
            self.logger.error(f"Health check {check.check_id} failed: {e}")
            check.consecutive_failures += 1
            check.last_status = ComponentStatus.UNHEALTHY
            check.last_run = datetime.utcnow()
    
    def _collect_system_metrics(self):
        """Collect system-level metrics"""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            self._record_metric(MetricType.CPU_USAGE, "system", cpu_percent, "%")
            
            # Memory metrics
            memory = psutil.virtual_memory()
            self._record_metric(MetricType.MEMORY_USAGE, "system", memory.percent, "%")
            self._record_metric(MetricType.MEMORY_USAGE, "system", memory.used / (1024**3), "GB", {"type": "used"})
            self._record_metric(MetricType.MEMORY_USAGE, "system", memory.available / (1024**3), "GB", {"type": "available"})
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            self._record_metric(MetricType.DISK_USAGE, "system", disk_percent, "%")
            self._record_metric(MetricType.DISK_USAGE, "system", disk.free / (1024**3), "GB", {"type": "free"})
            
            # Network I/O metrics
            network = psutil.net_io_counters()
            self._record_metric(MetricType.NETWORK_IO, "system", network.bytes_sent / (1024**2), "MB", {"type": "sent"})
            self._record_metric(MetricType.NETWORK_IO, "system", network.bytes_recv / (1024**2), "MB", {"type": "received"})
            
        except Exception as e:
            self.logger.error(f"Error collecting system metrics: {e}")
    
    def _record_metric(self, metric_type: MetricType, component: str, 
                      value: float, unit: str, metadata: Dict[str, Any] = None):
        """Record a system metric"""
        metric = SystemMetric(
            metric_type=metric_type,
            component=component,
            value=value,
            unit=unit,
            metadata=metadata or {}
        )
        
        self.metrics.append(metric)
    
    def _update_component_health(self):
        """Update health status for all components"""
        component_checks = defaultdict(list)
        
        # Group checks by component
        for check in self.health_checks.values():
            component_checks[check.component].append(check)
        
        # Calculate health for each component
        for component, checks in component_checks.items():
            healthy_checks = sum(1 for check in checks if check.last_status == ComponentStatus.HEALTHY)
            total_checks = len(checks)
            
            if total_checks == 0:
                continue
            
            health_score = healthy_checks / total_checks
            
            # Determine overall status
            if health_score >= 0.8:
                status = ComponentStatus.HEALTHY
            elif health_score >= 0.6:
                status = ComponentStatus.DEGRADED
            else:
                status = ComponentStatus.UNHEALTHY
            
            # Collect issues
            issues = []
            for check in checks:
                if check.last_status != ComponentStatus.HEALTHY:
                    issues.append(f"{check.name}: {check.last_status.value}")
            
            # Update component health
            self.component_health[component] = ComponentHealth(
                component=component,
                status=status,
                last_checked=datetime.utcnow(),
                health_score=health_score,
                issues=issues,
                metrics=self._get_recent_component_metrics(component),
                uptime_percentage=self._calculate_uptime(component)
            )
    
    def _get_recent_component_metrics(self, component: str) -> Dict[str, float]:
        """Get recent metrics for a component"""
        cutoff = datetime.utcnow() - timedelta(minutes=5)
        recent_metrics = [
            m for m in self.metrics 
            if m.component == component and m.timestamp > cutoff
        ]
        
        metrics_summary = {}
        if recent_metrics:
            for metric in recent_metrics:
                key = f"{metric.metric_type.value}"
                if metric.metadata:
                    key += f"_{metric.metadata.get('type', '')}"
                
                if key not in metrics_summary:
                    metrics_summary[key] = []
                metrics_summary[key].append(metric.value)
            
            # Calculate averages
            for key, values in metrics_summary.items():
                metrics_summary[key] = sum(values) / len(values)
        
        return metrics_summary
    
    def _calculate_uptime(self, component: str) -> float:
        """Calculate component uptime percentage"""
        # Look at health check history for the last 24 hours
        cutoff = datetime.utcnow() - timedelta(hours=24)
        
        component_checks = [
            check for check in self.health_checks.values()
            if check.component == component and check.last_run and check.last_run > cutoff
        ]
        
        if not component_checks:
            return 100.0
        
        # Count healthy vs total checks
        total_runs = 0
        healthy_runs = 0
        
        for check in component_checks:
            # Estimate number of runs based on interval
            hours_active = min(24, (datetime.utcnow() - cutoff).total_seconds() / 3600)
            estimated_runs = int(hours_active * 3600 / check.interval_seconds)
            
            total_runs += estimated_runs
            
            # Assume healthy if last status is healthy
            if check.last_status == ComponentStatus.HEALTHY:
                healthy_runs += estimated_runs - check.consecutive_failures
            else:
                healthy_runs += max(0, estimated_runs - check.consecutive_failures * 2)
        
        return (healthy_runs / total_runs * 100) if total_runs > 0 else 100.0
    
    def _check_alert_conditions(self):
        """Check for conditions that should trigger alerts"""
        # CPU usage alerts
        cpu_metrics = [
            m for m in list(self.metrics)[-20:]  # Last 20 metrics
            if m.metric_type == MetricType.CPU_USAGE and m.component == "system"
        ]
        
        if cpu_metrics:
            avg_cpu = sum(m.value for m in cpu_metrics) / len(cpu_metrics)
            if avg_cpu > 80:
                self._create_alert(
                    AlertLevel.WARNING,
                    "High CPU Usage",
                    f"Average CPU usage is {avg_cpu:.1f}%",
                    "system",
                    MetricType.CPU_USAGE,
                    avg_cpu,
                    80.0
                )
        
        # Memory usage alerts
        memory_metrics = [
            m for m in list(self.metrics)[-20:]
            if m.metric_type == MetricType.MEMORY_USAGE and m.component == "system" and m.unit == "%"
        ]
        
        if memory_metrics:
            avg_memory = sum(m.value for m in memory_metrics) / len(memory_metrics)
            if avg_memory > 85:
                self._create_alert(
                    AlertLevel.WARNING,
                    "High Memory Usage", 
                    f"Average memory usage is {avg_memory:.1f}%",
                    "system",
                    MetricType.MEMORY_USAGE,
                    avg_memory,
                    85.0
                )
        
        # Component health alerts
        for component, health in self.component_health.items():
            if health.status == ComponentStatus.UNHEALTHY:
                self._create_alert(
                    AlertLevel.ERROR,
                    f"Component Unhealthy: {component}",
                    f"Component {component} is unhealthy. Issues: {', '.join(health.issues)}",
                    component,
                    MetricType.SYSTEM_HEALTH,
                    health.health_score,
                    0.8
                )
    
    def _create_alert(self, level: AlertLevel, title: str, description: str,
                     component: str, metric_type: MetricType = None,
                     value: float = None, threshold: float = None):
        """Create a new alert"""
        # Create unique alert ID based on content
        import hashlib
        alert_content = f"{title}:{component}:{metric_type}"
        alert_id = hashlib.md5(alert_content.encode()).hexdigest()[:8]
        
        # Check if similar alert already exists and is not resolved
        if alert_id in self.active_alerts and not self.active_alerts[alert_id].resolved:
            return  # Don't create duplicate alert
        
        alert = Alert(
            alert_id=alert_id,
            level=level,
            title=title,
            description=description,
            component=component,
            metric_type=metric_type,
            value=value,
            threshold=threshold
        )
        
        self.active_alerts[alert_id] = alert
        self.alert_history.append(alert)
        
        self.logger.warning(f"Alert created: {level.value.upper()} - {title}")
    
    # Health check functions
    def _check_cpu_usage(self) -> bool:
        """Check if CPU usage is within acceptable limits"""
        cpu_percent = psutil.cpu_percent(interval=1)
        return cpu_percent < 90  # Alert if CPU > 90%
    
    def _check_memory_usage(self) -> bool:
        """Check if memory usage is within acceptable limits"""
        memory = psutil.virtual_memory()
        return memory.percent < 90  # Alert if memory > 90%
    
    def _check_disk_usage(self) -> bool:
        """Check if disk usage is within acceptable limits"""
        disk = psutil.disk_usage('/')
        disk_percent = (disk.used / disk.total) * 100
        return disk_percent < 85  # Alert if disk > 85%
    
    def _check_api_health(self) -> bool:
        """Check if the main API is responding"""
        try:
            import requests
            response = requests.get("http://localhost:8433/health", timeout=10)
            return response.status_code == 200
        except:
            return False
    
    def _check_interface_intelligence(self) -> bool:
        """Check Interface Intelligence component health"""
        # This would check if the interface intelligence module is working
        # For now, just return True as a placeholder
        return True
    
    def _check_progressive_disclosure(self) -> bool:
        """Check Progressive Disclosure component health"""
        # This would check if the progressive disclosure engine is working  
        # For now, just return True as a placeholder
        return True
    
    # Public API methods
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        overall_status = ComponentStatus.HEALTHY
        
        # Determine overall system status
        if self.component_health:
            unhealthy_count = sum(
                1 for health in self.component_health.values() 
                if health.status == ComponentStatus.UNHEALTHY
            )
            degraded_count = sum(
                1 for health in self.component_health.values()
                if health.status == ComponentStatus.DEGRADED  
            )
            
            if unhealthy_count > 0:
                overall_status = ComponentStatus.UNHEALTHY
            elif degraded_count > 0:
                overall_status = ComponentStatus.DEGRADED
        
        # Count active alerts by level
        alert_counts = defaultdict(int)
        for alert in self.active_alerts.values():
            if not alert.resolved:
                alert_counts[alert.level.value] += 1
        
        return {
            "overall_status": overall_status.value,
            "timestamp": datetime.utcnow().isoformat(),
            "uptime": self._get_system_uptime(),
            "components": {
                component: asdict(health) 
                for component, health in self.component_health.items()
            },
            "active_alerts": dict(alert_counts),
            "system_metrics": self._get_current_system_metrics(),
            "monitoring_active": self.monitoring_active
        }
    
    def get_alerts(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """Get system alerts"""
        if active_only:
            alerts = [alert for alert in self.active_alerts.values() if not alert.resolved]
        else:
            alerts = list(self.alert_history)
        
        return [asdict(alert) for alert in sorted(alerts, key=lambda a: a.timestamp, reverse=True)]
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an active alert"""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.resolved = True
            alert.resolved_at = datetime.utcnow()
            self.logger.info(f"Alert resolved: {alert.title}")
            return True
        return False
    
    def get_metrics(self, component: str = None, metric_type: MetricType = None,
                   time_range: timedelta = None) -> List[Dict[str, Any]]:
        """Get system metrics with optional filtering"""
        cutoff = datetime.utcnow() - time_range if time_range else None
        
        filtered_metrics = []
        for metric in self.metrics:
            if cutoff and metric.timestamp < cutoff:
                continue
            if component and metric.component != component:
                continue
            if metric_type and metric.metric_type != metric_type:
                continue
            
            filtered_metrics.append(asdict(metric))
        
        return filtered_metrics
    
    def _get_system_uptime(self) -> str:
        """Get system uptime"""
        try:
            boot_time = psutil.boot_time()
            uptime_seconds = time.time() - boot_time
            uptime_timedelta = timedelta(seconds=uptime_seconds)
            
            days = uptime_timedelta.days
            hours, remainder = divmod(uptime_timedelta.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            
            return f"{days}d {hours}h {minutes}m"
        except:
            return "unknown"
    
    def _get_current_system_metrics(self) -> Dict[str, Any]:
        """Get current system metrics"""
        try:
            return {
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": (psutil.disk_usage('/').used / psutil.disk_usage('/').total) * 100,
                "load_average": psutil.getloadavg()[0] if hasattr(psutil, 'getloadavg') else 0
            }
        except:
            return {}

class AlertManager:
    """Manages alert notifications and escalations"""
    
    def __init__(self):
        self.notification_handlers: Dict[str, Callable] = {}
        self.escalation_rules: List[Dict[str, Any]] = []
        self.alert_cooldowns: Dict[str, datetime] = {}
        self.logger = logging.getLogger(__name__)
    
    def register_notification_handler(self, name: str, handler: Callable):
        """Register an alert notification handler"""
        self.notification_handlers[name] = handler
        self.logger.info(f"Registered notification handler: {name}")
    
    def add_escalation_rule(self, rule: Dict[str, Any]):
        """Add an alert escalation rule"""
        self.escalation_rules.append(rule)
        self.logger.info(f"Added escalation rule: {rule}")
    
    def process_alert(self, alert: Alert):
        """Process an alert and send notifications"""
        alert_key = f"{alert.component}:{alert.title}"
        
        # Check cooldown period
        if alert_key in self.alert_cooldowns:
            last_sent = self.alert_cooldowns[alert_key]
            if datetime.utcnow() - last_sent < timedelta(minutes=15):
                return  # Skip to avoid spam
        
        # Send notifications
        self._send_notifications(alert)
        
        # Update cooldown
        self.alert_cooldowns[alert_key] = datetime.utcnow()
        
        # Check for escalation
        self._check_escalation(alert)
    
    def _send_notifications(self, alert: Alert):
        """Send alert notifications"""
        for handler_name, handler in self.notification_handlers.items():
            try:
                handler(alert)
            except Exception as e:
                self.logger.error(f"Error in notification handler {handler_name}: {e}")
    
    def _check_escalation(self, alert: Alert):
        """Check if alert meets escalation criteria"""
        for rule in self.escalation_rules:
            if self._matches_escalation_rule(alert, rule):
                self._escalate_alert(alert, rule)
    
    def _matches_escalation_rule(self, alert: Alert, rule: Dict[str, Any]) -> bool:
        """Check if alert matches escalation rule"""
        if rule.get("level") and alert.level.value != rule["level"]:
            return False
        
        if rule.get("component") and alert.component != rule["component"]:
            return False
        
        return True
    
    def _escalate_alert(self, alert: Alert, rule: Dict[str, Any]):
        """Escalate alert according to rule"""
        escalation_handler = rule.get("handler")
        if escalation_handler and escalation_handler in self.notification_handlers:
            self.notification_handlers[escalation_handler](alert)
            self.logger.warning(f"Alert escalated: {alert.title}")

class HealthDashboard:
    """Health dashboard for visualizing system status"""
    
    def __init__(self, system_monitor: SystemMonitor):
        self.system_monitor = system_monitor
        self.logger = logging.getLogger(__name__)
    
    def generate_dashboard_data(self) -> Dict[str, Any]:
        """Generate data for health dashboard"""
        status = self.system_monitor.get_system_status()
        alerts = self.system_monitor.get_alerts(active_only=True)
        
        # Recent metrics for charts
        recent_metrics = self.system_monitor.get_metrics(
            time_range=timedelta(hours=1)
        )
        
        # Group metrics by type for charting
        metrics_by_type = defaultdict(list)
        for metric in recent_metrics:
            key = f"{metric['metric_type']}_{metric['component']}"
            metrics_by_type[key].append({
                "timestamp": metric["timestamp"],
                "value": metric["value"],
                "unit": metric["unit"]
            })
        
        return {
            "system_status": status,
            "alerts": alerts,
            "metrics_chart_data": dict(metrics_by_type),
            "summary": {
                "total_components": len(status["components"]),
                "healthy_components": len([
                    c for c in status["components"].values() 
                    if c["status"] == "healthy"
                ]),
                "total_alerts": len(alerts),
                "critical_alerts": len([
                    a for a in alerts if a["level"] == "critical"
                ])
            },
            "generated_at": datetime.utcnow().isoformat()
        }
    
    def export_health_report(self, time_range: timedelta = None) -> Dict[str, Any]:
        """Export comprehensive health report"""
        time_range = time_range or timedelta(hours=24)
        
        status = self.system_monitor.get_system_status()
        all_alerts = self.system_monitor.get_alerts(active_only=False)
        all_metrics = self.system_monitor.get_metrics(time_range=time_range)
        
        # Calculate statistics
        alert_stats = defaultdict(int)
        for alert in all_alerts:
            alert_stats[alert["level"]] += 1
        
        metric_stats = defaultdict(list)
        for metric in all_metrics:
            key = f"{metric['metric_type']}_{metric['component']}"
            metric_stats[key].append(metric["value"])
        
        # Calculate averages and ranges
        metric_summary = {}
        for key, values in metric_stats.items():
            if values:
                metric_summary[key] = {
                    "count": len(values),
                    "average": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values)
                }
        
        return {
            "report_period": str(time_range),
            "generated_at": datetime.utcnow().isoformat(),
            "system_status": status,
            "alert_summary": dict(alert_stats),
            "metric_summary": metric_summary,
            "component_health": status["components"],
            "recommendations": self._generate_health_recommendations(status, all_alerts)
        }
    
    def _generate_health_recommendations(self, status: Dict[str, Any], 
                                       alerts: List[Dict[str, Any]]) -> List[str]:
        """Generate health improvement recommendations"""
        recommendations = []
        
        # Check for high resource usage
        if status["system_metrics"].get("cpu_percent", 0) > 70:
            recommendations.append("Consider scaling up CPU resources or optimizing high-CPU processes")
        
        if status["system_metrics"].get("memory_percent", 0) > 80:
            recommendations.append("Monitor memory usage and consider increasing available memory")
        
        if status["system_metrics"].get("disk_percent", 0) > 80:
            recommendations.append("Clean up disk space or expand storage capacity")
        
        # Check for unhealthy components
        unhealthy_components = [
            name for name, health in status["components"].items()
            if health["status"] != "healthy"
        ]
        
        if unhealthy_components:
            recommendations.append(f"Investigate issues with components: {', '.join(unhealthy_components)}")
        
        # Check for frequent alerts
        frequent_alerts = defaultdict(int)
        for alert in alerts[-50:]:  # Last 50 alerts
            frequent_alerts[alert["component"]] += 1
        
        for component, count in frequent_alerts.items():
            if count > 10:
                recommendations.append(f"Component {component} is generating frequent alerts - investigate root cause")
        
        if not recommendations:
            recommendations.append("System is healthy - no immediate actions required")
        
        return recommendations

class MonitoringSystem:
    """
    Main monitoring system that coordinates all monitoring components
    """
    
    def __init__(self):
        self.system_monitor = SystemMonitor()
        self.alert_manager = AlertManager()
        self.dashboard = HealthDashboard(self.system_monitor)
        
        self.logger = logging.getLogger(__name__)
        
        # Set up default notification handlers
        self._setup_default_notifications()
    
    def _setup_default_notifications(self):
        """Set up default notification handlers"""
        def log_notification_handler(alert: Alert):
            """Log alert notifications"""
            self.logger.warning(f"ALERT: {alert.level.value.upper()} - {alert.title} - {alert.description}")
        
        self.alert_manager.register_notification_handler("log", log_notification_handler)
        
        # Add escalation rule for critical alerts
        self.alert_manager.add_escalation_rule({
            "level": "critical",
            "handler": "log"
        })
    
    def start(self):
        """Start the monitoring system"""
        self.system_monitor.start_monitoring()
        self.logger.info("Monitoring system started")
    
    def stop(self):
        """Stop the monitoring system"""
        self.system_monitor.stop_monitoring()
        self.logger.info("Monitoring system stopped")
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        return self.system_monitor.get_system_status()
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get dashboard data"""
        return self.dashboard.generate_dashboard_data()
    
    def get_health_report(self, hours: int = 24) -> Dict[str, Any]:
        """Get health report for specified time period"""
        time_range = timedelta(hours=hours)
        return self.dashboard.export_health_report(time_range)
    
    def add_custom_health_check(self, check: HealthCheck):
        """Add a custom health check"""
        self.system_monitor.health_checks[check.check_id] = check
        self.logger.info(f"Added custom health check: {check.check_id}")
    
    def add_notification_handler(self, name: str, handler: Callable):
        """Add a custom notification handler"""
        self.alert_manager.register_notification_handler(name, handler)
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert"""
        return self.system_monitor.resolve_alert(alert_id)
    
    def get_metrics(self, component: str = None, hours: int = 1) -> List[Dict[str, Any]]:
        """Get metrics with optional filtering"""
        time_range = timedelta(hours=hours)
        return self.system_monitor.get_metrics(component=component, time_range=time_range)