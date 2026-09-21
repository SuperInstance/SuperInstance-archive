"""
Advanced Monitoring and Health Check System

Comprehensive monitoring, alerting, logging, and health checks for the
runtime optimizer with metrics collection and dashboard data.
"""

import asyncio
import logging
import json
import time
import os
import socket
import traceback
from datetime import datetime, timedelta
from collections import deque, defaultdict
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HealthStatus(Enum):
    """Health status levels"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    DOWN = "down"
    UNKNOWN = "unknown"

class AlertLevel(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class MetricType(Enum):
    """Types of metrics"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"

@dataclass
class HealthCheckResult:
    """Result of a health check"""
    check_name: str
    status: HealthStatus
    message: str
    timestamp: datetime
    duration_ms: float
    metadata: Dict[str, Any]
    
    def to_dict(self):
        data = asdict(self)
        data['status'] = self.status.value
        data['timestamp'] = self.timestamp.isoformat()
        return data

@dataclass
class Alert:
    """System alert"""
    alert_id: str
    timestamp: datetime
    level: AlertLevel
    component: str
    message: str
    details: Dict[str, Any]
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    
    def to_dict(self):
        data = asdict(self)
        data['level'] = self.level.value
        data['timestamp'] = self.timestamp.isoformat()
        if self.resolved_at:
            data['resolved_at'] = self.resolved_at.isoformat()
        return data

@dataclass
class Metric:
    """System metric"""
    metric_name: str
    metric_type: MetricType
    value: float
    timestamp: datetime
    tags: Dict[str, str]
    
    def to_dict(self):
        data = asdict(self)
        data['metric_type'] = self.metric_type.value
        data['timestamp'] = self.timestamp.isoformat()
        return data

class MetricsCollector:
    """Collect and aggregate system metrics"""
    
    def __init__(self, max_metrics: int = 10000):
        self.metrics = deque(maxlen=max_metrics)
        self.metric_aggregates = defaultdict(list)
        self.custom_metrics = {}
        
    def record_metric(self, name: str, metric_type: MetricType, value: float, 
                     tags: Dict[str, str] = None):
        """Record a metric"""
        metric = Metric(
            metric_name=name,
            metric_type=metric_type,
            value=value,
            timestamp=datetime.now(),
            tags=tags or {}
        )
        
        self.metrics.append(metric)
        self.metric_aggregates[name].append(value)
        
        # Keep only recent values for aggregation
        if len(self.metric_aggregates[name]) > 1000:
            self.metric_aggregates[name] = self.metric_aggregates[name][-1000:]
    
    def increment_counter(self, name: str, value: float = 1.0, tags: Dict[str, str] = None):
        """Increment a counter metric"""
        current_value = self.custom_metrics.get(name, 0.0)
        new_value = current_value + value
        self.custom_metrics[name] = new_value
        self.record_metric(name, MetricType.COUNTER, new_value, tags)
    
    def set_gauge(self, name: str, value: float, tags: Dict[str, str] = None):
        """Set a gauge metric"""
        self.custom_metrics[name] = value
        self.record_metric(name, MetricType.GAUGE, value, tags)
    
    def record_timer(self, name: str, duration_ms: float, tags: Dict[str, str] = None):
        """Record a timer metric"""
        self.record_metric(name, MetricType.TIMER, duration_ms, tags)
    
    def get_metric_summary(self, name: str, minutes: int = 60) -> Dict[str, float]:
        """Get summary statistics for a metric"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        
        recent_values = []
        for metric in self.metrics:
            if (metric.metric_name == name and 
                metric.timestamp >= cutoff_time):
                recent_values.append(metric.value)
        
        if not recent_values:
            return {}
        
        return {
            'count': len(recent_values),
            'min': min(recent_values),
            'max': max(recent_values),
            'mean': np.mean(recent_values),
            'median': np.median(recent_values),
            'std': np.std(recent_values),
            'p95': np.percentile(recent_values, 95),
            'p99': np.percentile(recent_values, 99)
        }
    
    def get_all_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of all metrics"""
        metric_names = set(m.metric_name for m in self.metrics)
        summaries = {}
        
        for name in metric_names:
            summaries[name] = self.get_metric_summary(name)
        
        return {
            'metric_summaries': summaries,
            'total_metrics': len(self.metrics),
            'unique_metrics': len(metric_names),
            'custom_metrics': self.custom_metrics.copy()
        }

class HealthChecker:
    """Perform comprehensive health checks"""
    
    def __init__(self):
        self.health_checks = {}
        self.check_results = deque(maxlen=1000)
        self.last_check_time = {}
        
    def register_health_check(self, name: str, check_func: Callable, 
                            interval_seconds: int = 60):
        """Register a health check function"""
        self.health_checks[name] = {
            'function': check_func,
            'interval': interval_seconds,
            'last_run': 0
        }
        logger.info(f"Registered health check: {name}")
    
    async def run_health_check(self, name: str) -> HealthCheckResult:
        """Run a specific health check"""
        if name not in self.health_checks:
            return HealthCheckResult(
                check_name=name,
                status=HealthStatus.UNKNOWN,
                message=f"Health check '{name}' not found",
                timestamp=datetime.now(),
                duration_ms=0.0,
                metadata={}
            )
        
        check_info = self.health_checks[name]
        start_time = time.time()
        
        try:
            result = await check_info['function']()
            duration_ms = (time.time() - start_time) * 1000
            
            if isinstance(result, dict):
                status = HealthStatus(result.get('status', 'healthy'))
                message = result.get('message', 'Check passed')
                metadata = result.get('metadata', {})
            else:
                status = HealthStatus.HEALTHY if result else HealthStatus.CRITICAL
                message = "Check passed" if result else "Check failed"
                metadata = {}
            
            check_result = HealthCheckResult(
                check_name=name,
                status=status,
                message=message,
                timestamp=datetime.now(),
                duration_ms=duration_ms,
                metadata=metadata
            )
            
            self.check_results.append(check_result)
            self.last_check_time[name] = time.time()
            
            return check_result
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            error_result = HealthCheckResult(
                check_name=name,
                status=HealthStatus.CRITICAL,
                message=f"Health check failed: {str(e)}",
                timestamp=datetime.now(),
                duration_ms=duration_ms,
                metadata={'error': str(e), 'traceback': traceback.format_exc()}
            )
            
            self.check_results.append(error_result)
            logger.error(f"Health check {name} failed: {e}")
            
            return error_result
    
    async def run_all_health_checks(self, force: bool = False) -> Dict[str, HealthCheckResult]:
        """Run all registered health checks"""
        current_time = time.time()
        results = {}
        
        for name, check_info in self.health_checks.items():
            # Check if it's time to run this check
            last_run = check_info.get('last_run', 0)
            if force or (current_time - last_run) >= check_info['interval']:
                result = await self.run_health_check(name)
                results[name] = result
        
        return results
    
    def get_overall_health(self) -> HealthStatus:
        """Get overall system health status"""
        # Get latest result for each check
        latest_results = {}
        for result in reversed(self.check_results):
            if result.check_name not in latest_results:
                latest_results[result.check_name] = result
        
        if not latest_results:
            return HealthStatus.UNKNOWN
        
        # Determine overall status based on worst individual status
        statuses = [result.status for result in latest_results.values()]
        
        if HealthStatus.DOWN in statuses:
            return HealthStatus.DOWN
        elif HealthStatus.CRITICAL in statuses:
            return HealthStatus.CRITICAL
        elif HealthStatus.WARNING in statuses:
            return HealthStatus.WARNING
        elif all(status == HealthStatus.HEALTHY for status in statuses):
            return HealthStatus.HEALTHY
        else:
            return HealthStatus.UNKNOWN
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get comprehensive health summary"""
        # Latest results by check name
        latest_results = {}
        for result in reversed(self.check_results):
            if result.check_name not in latest_results:
                latest_results[result.check_name] = result.to_dict()
        
        overall_status = self.get_overall_health()
        
        return {
            'overall_status': overall_status.value,
            'individual_checks': latest_results,
            'total_checks': len(self.health_checks),
            'last_check_time': max(self.last_check_time.values()) if self.last_check_time else 0
        }

class AlertManager:
    """Manage system alerts and notifications"""
    
    def __init__(self, max_alerts: int = 1000):
        self.alerts = deque(maxlen=max_alerts)
        self.alert_callbacks = []
        self.alert_rules = {}
        
    def add_alert_callback(self, callback: Callable):
        """Add callback for alert notifications"""
        self.alert_callbacks.append(callback)
    
    def add_alert_rule(self, rule_name: str, condition: Callable, 
                      level: AlertLevel, message_template: str):
        """Add automatic alert rule"""
        self.alert_rules[rule_name] = {
            'condition': condition,
            'level': level,
            'message_template': message_template,
            'last_triggered': 0,
            'cooldown_seconds': 300  # 5 minutes
        }
    
    async def create_alert(self, component: str, level: AlertLevel, 
                          message: str, details: Dict[str, Any] = None) -> str:
        """Create a new alert"""
        alert_id = f"alert_{int(time.time() * 1000)}_{len(self.alerts)}"
        
        alert = Alert(
            alert_id=alert_id,
            timestamp=datetime.now(),
            level=level,
            component=component,
            message=message,
            details=details or {}
        )
        
        self.alerts.append(alert)
        
        # Notify callbacks
        for callback in self.alert_callbacks:
            try:
                await callback(alert)
            except Exception as e:
                logger.error(f"Alert callback error: {e}")
        
        logger.warning(f"Alert created: [{level.value}] {component}: {message}")
        
        return alert_id
    
    async def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert"""
        for alert in self.alerts:
            if alert.alert_id == alert_id:
                alert.resolved = True
                alert.resolved_at = datetime.now()
                logger.info(f"Alert resolved: {alert_id}")
                return True
        
        return False
    
    async def check_alert_rules(self, context: Dict[str, Any]):
        """Check all alert rules against current context"""
        current_time = time.time()
        
        for rule_name, rule in self.alert_rules.items():
            try:
                # Check cooldown
                if (current_time - rule['last_triggered']) < rule['cooldown_seconds']:
                    continue
                
                # Evaluate condition
                if rule['condition'](context):
                    message = rule['message_template'].format(**context)
                    await self.create_alert('system', rule['level'], message, context)
                    rule['last_triggered'] = current_time
                    
            except Exception as e:
                logger.error(f"Error checking alert rule {rule_name}: {e}")
    
    def get_active_alerts(self, level: AlertLevel = None) -> List[Dict[str, Any]]:
        """Get active (unresolved) alerts"""
        active_alerts = [alert for alert in self.alerts if not alert.resolved]
        
        if level:
            active_alerts = [alert for alert in active_alerts if alert.level == level]
        
        return [alert.to_dict() for alert in active_alerts]
    
    def get_alert_statistics(self) -> Dict[str, Any]:
        """Get alert statistics"""
        total_alerts = len(self.alerts)
        active_alerts = len([a for a in self.alerts if not a.resolved])
        
        # Count by level
        by_level = defaultdict(int)
        by_component = defaultdict(int)
        
        for alert in self.alerts:
            by_level[alert.level.value] += 1
            by_component[alert.component] += 1
        
        return {
            'total_alerts': total_alerts,
            'active_alerts': active_alerts,
            'resolved_alerts': total_alerts - active_alerts,
            'by_level': dict(by_level),
            'by_component': dict(by_component),
            'alert_rules_count': len(self.alert_rules)
        }

class LogAnalyzer:
    """Analyze logs for patterns and issues"""
    
    def __init__(self, log_file_path: str = None):
        self.log_file_path = log_file_path
        self.error_patterns = deque(maxlen=1000)
        self.warning_patterns = deque(maxlen=1000)
        self.performance_metrics = deque(maxlen=1000)
        
    def analyze_log_entry(self, log_entry: str, timestamp: datetime):
        """Analyze a single log entry"""
        entry_lower = log_entry.lower()
        
        # Detect errors
        if any(keyword in entry_lower for keyword in ['error', 'exception', 'failed', 'critical']):
            self.error_patterns.append({
                'timestamp': timestamp,
                'message': log_entry,
                'severity': 'error'
            })
        
        # Detect warnings
        elif any(keyword in entry_lower for keyword in ['warning', 'warn', 'deprecated']):
            self.warning_patterns.append({
                'timestamp': timestamp,
                'message': log_entry,
                'severity': 'warning'
            })
        
        # Detect performance issues
        if any(keyword in entry_lower for keyword in ['slow', 'timeout', 'high cpu', 'memory']):
            self.performance_metrics.append({
                'timestamp': timestamp,
                'message': log_entry,
                'type': 'performance'
            })
    
    def get_error_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get summary of recent errors"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        recent_errors = [e for e in self.error_patterns 
                        if e['timestamp'] >= cutoff_time]
        
        # Group by similar messages
        error_groups = defaultdict(int)
        for error in recent_errors:
            # Simple grouping by first few words
            key = ' '.join(error['message'].split()[:5])
            error_groups[key] += 1
        
        return {
            'total_errors': len(recent_errors),
            'unique_error_types': len(error_groups),
            'most_common_errors': dict(sorted(error_groups.items(), 
                                           key=lambda x: x[1], reverse=True)[:10])
        }

class MonitoringSystem:
    """Main monitoring system orchestrator"""
    
    def __init__(self):
        self.metrics_collector = MetricsCollector()
        self.health_checker = HealthChecker()
        self.alert_manager = AlertManager()
        self.log_analyzer = LogAnalyzer()
        
        self.monitoring_active = False
        self._monitoring_task = None
        self.start_time = datetime.now()
        
        # Register default health checks
        self._register_default_health_checks()
        self._register_default_alert_rules()
        
    def _register_default_health_checks(self):
        """Register default health checks"""
        
        async def check_service_availability():
            """Check if service is responding"""
            try:
                # Try to bind to service port to check availability
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                result = sock.connect_ex(('localhost', 8431))
                sock.close()
                
                if result == 0:
                    return {'status': 'healthy', 'message': 'Service port is accessible'}
                else:
                    return {'status': 'critical', 'message': 'Service port is not accessible'}
            except Exception as e:
                return {'status': 'critical', 'message': f'Port check failed: {e}'}
        
        async def check_disk_space():
            """Check available disk space"""
            try:
                import shutil
                total, used, free = shutil.disk_usage('/')
                free_percent = (free / total) * 100
                
                if free_percent > 20:
                    status = 'healthy'
                elif free_percent > 10:
                    status = 'warning'
                else:
                    status = 'critical'
                
                return {
                    'status': status,
                    'message': f'Disk space: {free_percent:.1f}% free',
                    'metadata': {
                        'free_gb': free / (1024**3),
                        'used_gb': used / (1024**3),
                        'total_gb': total / (1024**3),
                        'free_percent': free_percent
                    }
                }
            except Exception as e:
                return {'status': 'critical', 'message': f'Disk check failed: {e}'}
        
        async def check_memory_usage():
            """Check memory usage"""
            try:
                import psutil
                memory = psutil.virtual_memory()
                
                if memory.percent < 80:
                    status = 'healthy'
                elif memory.percent < 90:
                    status = 'warning'
                else:
                    status = 'critical'
                
                return {
                    'status': status,
                    'message': f'Memory usage: {memory.percent:.1f}%',
                    'metadata': {
                        'used_gb': memory.used / (1024**3),
                        'available_gb': memory.available / (1024**3),
                        'percent': memory.percent
                    }
                }
            except Exception as e:
                return {'status': 'critical', 'message': f'Memory check failed: {e}'}
        
        async def check_cpu_usage():
            """Check CPU usage"""
            try:
                import psutil
                cpu_percent = psutil.cpu_percent(interval=1)
                
                if cpu_percent < 70:
                    status = 'healthy'
                elif cpu_percent < 85:
                    status = 'warning'
                else:
                    status = 'critical'
                
                return {
                    'status': status,
                    'message': f'CPU usage: {cpu_percent:.1f}%',
                    'metadata': {'cpu_percent': cpu_percent}
                }
            except Exception as e:
                return {'status': 'critical', 'message': f'CPU check failed: {e}'}
        
        # Register health checks
        self.health_checker.register_health_check('service_availability', check_service_availability, 30)
        self.health_checker.register_health_check('disk_space', check_disk_space, 120)
        self.health_checker.register_health_check('memory_usage', check_memory_usage, 60)
        self.health_checker.register_health_check('cpu_usage', check_cpu_usage, 60)
    
    def _register_default_alert_rules(self):
        """Register default alert rules"""
        
        # High CPU usage alert
        def high_cpu_condition(context):
            return context.get('cpu_percent', 0) > 90
        
        self.alert_manager.add_alert_rule(
            'high_cpu',
            high_cpu_condition,
            AlertLevel.CRITICAL,
            'High CPU usage detected: {cpu_percent:.1f}%'
        )
        
        # High memory usage alert
        def high_memory_condition(context):
            return context.get('memory_percent', 0) > 90
        
        self.alert_manager.add_alert_rule(
            'high_memory',
            high_memory_condition,
            AlertLevel.CRITICAL,
            'High memory usage detected: {memory_percent:.1f}%'
        )
        
        # Low disk space alert
        def low_disk_condition(context):
            return context.get('disk_free_percent', 100) < 15
        
        self.alert_manager.add_alert_rule(
            'low_disk_space',
            low_disk_condition,
            AlertLevel.WARNING,
            'Low disk space: {disk_free_percent:.1f}% free'
        )
    
    async def start_monitoring(self):
        """Start the monitoring system"""
        self.monitoring_active = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Monitoring system started")
    
    async def stop_monitoring(self):
        """Stop the monitoring system"""
        self.monitoring_active = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        logger.info("Monitoring system stopped")
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.monitoring_active:
            try:
                # Run health checks
                health_results = await self.health_checker.run_all_health_checks()
                
                # Collect system metrics
                await self._collect_system_metrics()
                
                # Check alert rules with current system context
                system_context = await self._get_system_context()
                await self.alert_manager.check_alert_rules(system_context)
                
                # Record monitoring metrics
                self.metrics_collector.increment_counter('monitoring.health_checks_run', len(health_results))
                self.metrics_collector.set_gauge('monitoring.active_alerts', 
                                                len(self.alert_manager.get_active_alerts()))
                
                await asyncio.sleep(30)  # Run every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def _collect_system_metrics(self):
        """Collect current system metrics"""
        try:
            import psutil
            
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=0.1)
            self.metrics_collector.set_gauge('system.cpu_percent', cpu_percent)
            
            # Memory metrics
            memory = psutil.virtual_memory()
            self.metrics_collector.set_gauge('system.memory_percent', memory.percent)
            self.metrics_collector.set_gauge('system.memory_used_gb', memory.used / (1024**3))
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            self.metrics_collector.set_gauge('system.disk_percent', disk_percent)
            
            # Network metrics
            network = psutil.net_io_counters()
            self.metrics_collector.set_gauge('system.network_bytes_sent', network.bytes_sent)
            self.metrics_collector.set_gauge('system.network_bytes_recv', network.bytes_recv)
            
            # Process metrics
            process_count = len(psutil.pids())
            self.metrics_collector.set_gauge('system.process_count', process_count)
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
    
    async def _get_system_context(self) -> Dict[str, Any]:
        """Get current system context for alert rules"""
        try:
            import psutil
            
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                'cpu_percent': psutil.cpu_percent(interval=0.1),
                'memory_percent': memory.percent,
                'disk_free_percent': ((disk.total - disk.used) / disk.total) * 100,
                'uptime_seconds': (datetime.now() - self.start_time).total_seconds(),
                'active_alerts': len(self.alert_manager.get_active_alerts()),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting system context: {e}")
            return {}
    
    def get_monitoring_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive dashboard data"""
        health_summary = self.health_checker.get_health_summary()
        metrics_summary = self.metrics_collector.get_all_metrics_summary()
        alert_stats = self.alert_manager.get_alert_statistics()
        error_summary = self.log_analyzer.get_error_summary()
        
        # Calculate uptime
        uptime = datetime.now() - self.start_time
        uptime_seconds = uptime.total_seconds()
        
        return {
            'monitoring_info': {
                'system_start_time': self.start_time.isoformat(),
                'uptime_seconds': uptime_seconds,
                'uptime_human': str(uptime).split('.')[0],  # Remove microseconds
                'monitoring_active': self.monitoring_active
            },
            'health': health_summary,
            'metrics': metrics_summary,
            'alerts': alert_stats,
            'errors': error_summary,
            'performance': {
                'health_checks_registered': len(self.health_checker.health_checks),
                'metrics_collected': len(self.metrics_collector.metrics),
                'alert_rules': len(self.alert_manager.alert_rules)
            }
        }
    
    async def create_manual_alert(self, component: str, level: str, message: str, 
                                details: Dict[str, Any] = None) -> str:
        """Create a manual alert"""
        try:
            alert_level = AlertLevel(level)
            return await self.alert_manager.create_alert(component, alert_level, message, details)
        except ValueError:
            raise ValueError(f"Invalid alert level: {level}")
    
    def get_system_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive system performance report"""
        # Get metrics for key performance indicators
        cpu_summary = self.metrics_collector.get_metric_summary('system.cpu_percent', 60)
        memory_summary = self.metrics_collector.get_metric_summary('system.memory_percent', 60)
        
        # Health check performance
        health_results = list(self.health_checker.check_results)[-10:]  # Last 10 results
        avg_check_duration = np.mean([r.duration_ms for r in health_results]) if health_results else 0
        
        # Recent alerts
        recent_alerts = self.alert_manager.get_active_alerts()
        critical_alerts = [a for a in recent_alerts if a['level'] == 'critical']
        
        return {
            'performance_summary': {
                'cpu_usage': cpu_summary,
                'memory_usage': memory_summary,
                'health_check_avg_duration_ms': avg_check_duration,
                'total_active_alerts': len(recent_alerts),
                'critical_alerts': len(critical_alerts)
            },
            'recommendations': self._generate_performance_recommendations(
                cpu_summary, memory_summary, len(critical_alerts)
            ),
            'generated_at': datetime.now().isoformat()
        }
    
    def _generate_performance_recommendations(self, cpu_summary: Dict[str, float], 
                                           memory_summary: Dict[str, float], 
                                           critical_alerts_count: int) -> List[str]:
        """Generate performance recommendations"""
        recommendations = []
        
        if cpu_summary and cpu_summary.get('mean', 0) > 80:
            recommendations.append("Consider reducing CPU-intensive operations or scaling resources")
        
        if memory_summary and memory_summary.get('mean', 0) > 85:
            recommendations.append("Memory usage is high - consider optimizing memory allocation")
        
        if critical_alerts_count > 0:
            recommendations.append(f"Address {critical_alerts_count} critical alerts immediately")
        
        if not recommendations:
            recommendations.append("System is performing well - no immediate action required")
        
        return recommendations

# Global monitoring system instance
monitoring_system = MonitoringSystem()

if __name__ == "__main__":
    # Demo monitoring
    async def demo_alert_callback(alert):
        print(f"ALERT: [{alert.level.value}] {alert.component}: {alert.message}")
    
    async def main():
        # Add alert callback
        monitoring_system.alert_manager.add_alert_callback(demo_alert_callback)
        
        # Start monitoring
        await monitoring_system.start_monitoring()
        
        # Record some demo metrics
        monitoring_system.metrics_collector.increment_counter('demo.requests', 10)
        monitoring_system.metrics_collector.set_gauge('demo.active_users', 25)
        monitoring_system.metrics_collector.record_timer('demo.response_time', 150.5)
        
        # Create a test alert
        await monitoring_system.create_manual_alert(
            'demo_component', 'warning', 'This is a test alert', 
            {'test_data': 'example'}
        )
        
        # Run for a bit
        await asyncio.sleep(10)
        
        # Get dashboard data
        dashboard = monitoring_system.get_monitoring_dashboard_data()
        print("\nDashboard Data:")
        print(json.dumps(dashboard, indent=2, default=str))
        
        # Get performance report
        report = monitoring_system.get_system_performance_report()
        print("\nPerformance Report:")
        print(json.dumps(report, indent=2, default=str))
        
        # Stop monitoring
        await monitoring_system.stop_monitoring()
    
    asyncio.run(main())