"""
ActiveLog Integration Hub - Health Monitoring Dashboard
Real-time monitoring of all 70+ services with comprehensive health checks
"""

import asyncio
import aiohttp
import json
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict, field
from enum import Enum
from datetime import datetime, timedelta
from service_discovery import ServiceDiscovery, ServiceInfo, ServiceStatus
import statistics
import psutil

class HealthCheckType(Enum):
    HTTP = "http"
    TCP = "tcp"
    PROCESS = "process"
    DATABASE = "database"
    CUSTOM = "custom"

class AlertSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class HealthMetrics:
    response_time_ms: float = 0
    cpu_usage_percent: float = 0
    memory_usage_mb: float = 0
    disk_usage_percent: float = 0
    error_rate_percent: float = 0
    uptime_seconds: float = 0
    request_count: int = 0
    last_error: Optional[str] = None
    custom_metrics: Dict[str, Any] = field(default_factory=dict)

@dataclass
class HealthCheckResult:
    service_name: str
    check_type: HealthCheckType
    status: ServiceStatus
    timestamp: datetime
    metrics: HealthMetrics
    message: str = ""
    error: Optional[str] = None
    duration_ms: float = 0

@dataclass
class ServiceAlert:
    service_name: str
    severity: AlertSeverity
    message: str
    timestamp: datetime
    resolved: bool = False
    resolved_at: Optional[datetime] = None

class HealthMonitor:
    def __init__(self, discovery: ServiceDiscovery, check_interval: int = 30):
        self.discovery = discovery
        self.check_interval = check_interval
        self.health_history: Dict[str, List[HealthCheckResult]] = {}
        self.active_alerts: Dict[str, List[ServiceAlert]] = {}
        self.custom_checks: Dict[str, Callable] = {}
        self.running = False
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Health check configurations
        self.timeout = 10
        self.max_history_size = 1000
        self.alert_thresholds = {
            'response_time_ms': 5000,
            'error_rate_percent': 5.0,
            'cpu_usage_percent': 80.0,
            'memory_usage_mb': 1000,
            'disk_usage_percent': 90.0
        }
    
    async def start_monitoring(self):
        """Start the health monitoring system"""
        self.running = True
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        )
        
        print(f"Starting health monitoring with {self.check_interval}s intervals...")
        
        while self.running:
            try:
                await self.run_health_checks()
                await self.process_alerts()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logging.error(f"Health monitoring error: {e}")
                await asyncio.sleep(5)
    
    async def stop_monitoring(self):
        """Stop the health monitoring system"""
        self.running = False
        if self.session:
            await self.session.close()
    
    async def run_health_checks(self):
        """Run health checks for all discovered services"""
        # Refresh service discovery
        await self.discovery.discover_all_services()
        
        # Run health checks concurrently
        tasks = []
        for service_name, service_info in self.discovery.services.items():
            task = asyncio.create_task(self.check_service_health(service_info))
            tasks.append(task)
        
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, HealthCheckResult):
                    await self.record_health_result(result)
                elif isinstance(result, Exception):
                    logging.error(f"Health check failed: {result}")
    
    async def check_service_health(self, service: ServiceInfo) -> HealthCheckResult:
        """Perform comprehensive health check for a service"""
        start_time = time.time()
        metrics = HealthMetrics()
        status = ServiceStatus.UNKNOWN
        message = "Health check completed"
        error = None
        
        try:
            # HTTP health check
            if service.port > 0:
                http_result = await self.http_health_check(service)
                status = http_result.status
                metrics.response_time_ms = http_result.metrics.response_time_ms
                if http_result.error:
                    error = http_result.error
            
            # Process health check
            if service.metadata and 'pid' in service.metadata:
                process_result = await self.process_health_check(service)
                metrics.cpu_usage_percent = process_result.metrics.cpu_usage_percent
                metrics.memory_usage_mb = process_result.metrics.memory_usage_mb
                metrics.uptime_seconds = process_result.metrics.uptime_seconds
                
                # If HTTP check failed but process is running, mark as degraded
                if status == ServiceStatus.UNKNOWN and process_result.status == ServiceStatus.HEALTHY:
                    status = ServiceStatus.UNHEALTHY
                    message = "Service process running but HTTP endpoint unreachable"
            
            # TCP connectivity check for non-HTTP services
            if service.port > 0 and status == ServiceStatus.UNKNOWN:
                tcp_result = await self.tcp_health_check(service)
                if tcp_result.status == ServiceStatus.HEALTHY:
                    status = ServiceStatus.HEALTHY
                    message = "TCP port accessible"
            
            # Custom health checks
            if service.name in self.custom_checks:
                custom_result = await self.custom_checks[service.name](service)
                if custom_result:
                    metrics.custom_metrics.update(custom_result.metrics.custom_metrics)
                    if custom_result.status != ServiceStatus.HEALTHY:
                        status = custom_result.status
                        error = custom_result.error
            
            # If still unknown, check if it's a file-based service
            if status == ServiceStatus.UNKNOWN:
                status = ServiceStatus.STOPPED
                message = "Service not running or unreachable"
        
        except Exception as e:
            status = ServiceStatus.UNHEALTHY
            error = str(e)
            message = f"Health check failed: {e}"
        
        duration_ms = (time.time() - start_time) * 1000
        
        return HealthCheckResult(
            service_name=service.name,
            check_type=HealthCheckType.HTTP,
            status=status,
            timestamp=datetime.now(),
            metrics=metrics,
            message=message,
            error=error,
            duration_ms=duration_ms
        )
    
    async def http_health_check(self, service: ServiceInfo) -> HealthCheckResult:
        """Perform HTTP health check"""
        start_time = time.time()
        metrics = HealthMetrics()
        
        try:
            url = f"http://{service.host}:{service.port}{service.health_endpoint}"
            
            async with self.session.get(url) as response:
                response_time = (time.time() - start_time) * 1000
                metrics.response_time_ms = response_time
                
                if response.status == 200:
                    # Try to parse response for additional metrics
                    try:
                        data = await response.json()
                        if isinstance(data, dict):
                            metrics.custom_metrics.update(data)
                    except:
                        pass
                    
                    return HealthCheckResult(
                        service_name=service.name,
                        check_type=HealthCheckType.HTTP,
                        status=ServiceStatus.HEALTHY,
                        timestamp=datetime.now(),
                        metrics=metrics,
                        message=f"HTTP {response.status}",
                        duration_ms=response_time
                    )
                else:
                    return HealthCheckResult(
                        service_name=service.name,
                        check_type=HealthCheckType.HTTP,
                        status=ServiceStatus.UNHEALTHY,
                        timestamp=datetime.now(),
                        metrics=metrics,
                        error=f"HTTP {response.status}",
                        duration_ms=response_time
                    )
        
        except asyncio.TimeoutError:
            return HealthCheckResult(
                service_name=service.name,
                check_type=HealthCheckType.HTTP,
                status=ServiceStatus.UNHEALTHY,
                timestamp=datetime.now(),
                metrics=metrics,
                error="HTTP timeout",
                duration_ms=(time.time() - start_time) * 1000
            )
        except Exception as e:
            return HealthCheckResult(
                service_name=service.name,
                check_type=HealthCheckType.HTTP,
                status=ServiceStatus.UNHEALTHY,
                timestamp=datetime.now(),
                metrics=metrics,
                error=str(e),
                duration_ms=(time.time() - start_time) * 1000
            )
    
    async def tcp_health_check(self, service: ServiceInfo) -> HealthCheckResult:
        """Perform TCP connectivity check"""
        start_time = time.time()
        metrics = HealthMetrics()
        
        try:
            # Try to connect to the TCP port
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(service.host, service.port),
                timeout=5
            )
            writer.close()
            await writer.wait_closed()
            
            response_time = (time.time() - start_time) * 1000
            metrics.response_time_ms = response_time
            
            return HealthCheckResult(
                service_name=service.name,
                check_type=HealthCheckType.TCP,
                status=ServiceStatus.HEALTHY,
                timestamp=datetime.now(),
                metrics=metrics,
                message="TCP port accessible",
                duration_ms=response_time
            )
        
        except Exception as e:
            return HealthCheckResult(
                service_name=service.name,
                check_type=HealthCheckType.TCP,
                status=ServiceStatus.UNHEALTHY,
                timestamp=datetime.now(),
                metrics=metrics,
                error=f"TCP connection failed: {e}",
                duration_ms=(time.time() - start_time) * 1000
            )
    
    async def process_health_check(self, service: ServiceInfo) -> HealthCheckResult:
        """Check process-level health metrics"""
        metrics = HealthMetrics()
        
        try:
            pid = service.metadata.get('pid')
            if pid:
                process = psutil.Process(pid)
                
                # CPU usage
                metrics.cpu_usage_percent = process.cpu_percent()
                
                # Memory usage
                memory_info = process.memory_info()
                metrics.memory_usage_mb = memory_info.rss / 1024 / 1024
                
                # Uptime
                metrics.uptime_seconds = time.time() - process.create_time()
                
                return HealthCheckResult(
                    service_name=service.name,
                    check_type=HealthCheckType.PROCESS,
                    status=ServiceStatus.HEALTHY,
                    timestamp=datetime.now(),
                    metrics=metrics,
                    message="Process metrics collected"
                )
        
        except psutil.NoSuchProcess:
            return HealthCheckResult(
                service_name=service.name,
                check_type=HealthCheckType.PROCESS,
                status=ServiceStatus.STOPPED,
                timestamp=datetime.now(),
                metrics=metrics,
                error="Process not found"
            )
        except Exception as e:
            return HealthCheckResult(
                service_name=service.name,
                check_type=HealthCheckType.PROCESS,
                status=ServiceStatus.UNHEALTHY,
                timestamp=datetime.now(),
                metrics=metrics,
                error=str(e)
            )
    
    async def record_health_result(self, result: HealthCheckResult):
        """Record health check result and maintain history"""
        service_name = result.service_name
        
        # Initialize history if needed
        if service_name not in self.health_history:
            self.health_history[service_name] = []
        
        # Add result to history
        self.health_history[service_name].append(result)
        
        # Trim history if too large
        if len(self.health_history[service_name]) > self.max_history_size:
            self.health_history[service_name] = self.health_history[service_name][-self.max_history_size:]
        
        # Update service status in discovery
        if service_name in self.discovery.services:
            self.discovery.services[service_name].status = result.status
            self.discovery.services[service_name].last_health_check = result.timestamp
            self.discovery.services[service_name].response_time_ms = result.metrics.response_time_ms
            if result.error:
                self.discovery.services[service_name].error_count += 1
    
    async def process_alerts(self):
        """Process health results and generate alerts"""
        current_time = datetime.now()
        
        for service_name, history in self.health_history.items():
            if not history:
                continue
            
            latest_result = history[-1]
            
            # Check for service down
            if latest_result.status in [ServiceStatus.UNHEALTHY, ServiceStatus.STOPPED]:
                await self.create_alert(
                    service_name,
                    AlertSeverity.ERROR,
                    f"Service {service_name} is {latest_result.status.value}: {latest_result.error or latest_result.message}"
                )
            
            # Check threshold violations
            metrics = latest_result.metrics
            
            if metrics.response_time_ms > self.alert_thresholds['response_time_ms']:
                await self.create_alert(
                    service_name,
                    AlertSeverity.WARNING,
                    f"High response time: {metrics.response_time_ms:.0f}ms"
                )
            
            if metrics.cpu_usage_percent > self.alert_thresholds['cpu_usage_percent']:
                await self.create_alert(
                    service_name,
                    AlertSeverity.WARNING,
                    f"High CPU usage: {metrics.cpu_usage_percent:.1f}%"
                )
            
            if metrics.memory_usage_mb > self.alert_thresholds['memory_usage_mb']:
                await self.create_alert(
                    service_name,
                    AlertSeverity.WARNING,
                    f"High memory usage: {metrics.memory_usage_mb:.0f}MB"
                )
            
            # Check error rate over last 10 checks
            if len(history) >= 10:
                recent_errors = sum(1 for r in history[-10:] if r.error)
                error_rate = (recent_errors / 10) * 100
                
                if error_rate > self.alert_thresholds['error_rate_percent']:
                    await self.create_alert(
                        service_name,
                        AlertSeverity.ERROR,
                        f"High error rate: {error_rate:.1f}% over last 10 checks"
                    )
            
            # Auto-resolve alerts if service is healthy
            if latest_result.status == ServiceStatus.HEALTHY:
                await self.resolve_alerts(service_name)
    
    async def create_alert(self, service_name: str, severity: AlertSeverity, message: str):
        """Create a new alert"""
        # Check if similar alert already exists
        if service_name in self.active_alerts:
            for alert in self.active_alerts[service_name]:
                if not alert.resolved and alert.message == message:
                    return  # Don't duplicate alerts
        
        alert = ServiceAlert(
            service_name=service_name,
            severity=severity,
            message=message,
            timestamp=datetime.now()
        )
        
        if service_name not in self.active_alerts:
            self.active_alerts[service_name] = []
        
        self.active_alerts[service_name].append(alert)
        
        # Log alert
        severity_emoji = {
            AlertSeverity.INFO: "ℹ️",
            AlertSeverity.WARNING: "⚠️",
            AlertSeverity.ERROR: "❌",
            AlertSeverity.CRITICAL: "🔥"
        }
        
        print(f"{severity_emoji[severity]} ALERT [{severity.value.upper()}] {service_name}: {message}")
    
    async def resolve_alerts(self, service_name: str):
        """Resolve active alerts for a service"""
        if service_name in self.active_alerts:
            current_time = datetime.now()
            for alert in self.active_alerts[service_name]:
                if not alert.resolved:
                    alert.resolved = True
                    alert.resolved_at = current_time
    
    def get_service_health_summary(self, service_name: str) -> Dict[str, Any]:
        """Get health summary for a specific service"""
        if service_name not in self.health_history:
            return {"error": "No health data available"}
        
        history = self.health_history[service_name]
        if not history:
            return {"error": "No health checks recorded"}
        
        latest = history[-1]
        
        # Calculate statistics from recent history (last 100 checks)
        recent_history = history[-100:]
        response_times = [r.metrics.response_time_ms for r in recent_history if r.metrics.response_time_ms > 0]
        
        summary = {
            "service_name": service_name,
            "current_status": latest.status.value,
            "last_check": latest.timestamp.isoformat(),
            "message": latest.message,
            "error": latest.error,
            "metrics": {
                "response_time_ms": latest.metrics.response_time_ms,
                "cpu_usage_percent": latest.metrics.cpu_usage_percent,
                "memory_usage_mb": latest.metrics.memory_usage_mb,
                "uptime_seconds": latest.metrics.uptime_seconds,
                "custom_metrics": latest.metrics.custom_metrics
            },
            "statistics": {
                "total_checks": len(history),
                "recent_checks": len(recent_history),
                "avg_response_time_ms": statistics.mean(response_times) if response_times else 0,
                "max_response_time_ms": max(response_times) if response_times else 0,
                "min_response_time_ms": min(response_times) if response_times else 0,
                "success_rate_percent": (len([r for r in recent_history if r.status == ServiceStatus.HEALTHY]) / len(recent_history)) * 100
            },
            "active_alerts": len([a for a in self.active_alerts.get(service_name, []) if not a.resolved])
        }
        
        return summary
    
    def get_overall_health_dashboard(self) -> Dict[str, Any]:
        """Get overall health dashboard data"""
        total_services = len(self.discovery.services)
        healthy_services = len([s for s in self.discovery.services.values() if s.status == ServiceStatus.HEALTHY])
        unhealthy_services = len([s for s in self.discovery.services.values() if s.status == ServiceStatus.UNHEALTHY])
        stopped_services = len([s for s in self.discovery.services.values() if s.status == ServiceStatus.STOPPED])
        
        # Count alerts by severity
        alert_counts = {severity.value: 0 for severity in AlertSeverity}
        for alerts in self.active_alerts.values():
            for alert in alerts:
                if not alert.resolved:
                    alert_counts[alert.severity.value] += 1
        
        # Service type breakdown
        service_type_health = {}
        for service in self.discovery.services.values():
            stype = service.service_type.value
            if stype not in service_type_health:
                service_type_health[stype] = {"healthy": 0, "unhealthy": 0, "stopped": 0, "unknown": 0}
            service_type_health[stype][service.status.value] += 1
        
        dashboard = {
            "overview": {
                "total_services": total_services,
                "healthy_services": healthy_services,
                "unhealthy_services": unhealthy_services,
                "stopped_services": stopped_services,
                "health_percentage": (healthy_services / total_services * 100) if total_services > 0 else 0
            },
            "alerts": {
                "total_active": sum(alert_counts.values()),
                "by_severity": alert_counts
            },
            "service_types": service_type_health,
            "recent_activity": self.get_recent_activity(),
            "last_updated": datetime.now().isoformat()
        }
        
        return dashboard
    
    def get_recent_activity(self) -> List[Dict[str, Any]]:
        """Get recent health check activity"""
        all_recent = []
        
        for service_name, history in self.health_history.items():
            if history:
                latest = history[-1]
                all_recent.append({
                    "service_name": service_name,
                    "status": latest.status.value,
                    "timestamp": latest.timestamp.isoformat(),
                    "message": latest.message,
                    "response_time_ms": latest.metrics.response_time_ms
                })
        
        # Sort by timestamp descending
        all_recent.sort(key=lambda x: x["timestamp"], reverse=True)
        return all_recent[:50]  # Return last 50 activities
    
    def register_custom_health_check(self, service_name: str, check_func: Callable):
        """Register a custom health check function for a service"""
        self.custom_checks[service_name] = check_func
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert monitor state to dictionary"""
        return {
            "monitoring": self.running,
            "check_interval": self.check_interval,
            "total_services_monitored": len(self.health_history),
            "alert_thresholds": self.alert_thresholds,
            "dashboard": self.get_overall_health_dashboard(),
            "services": {
                name: self.get_service_health_summary(name)
                for name in self.health_history.keys()
            }
        }

# Example usage and dashboard web interface
class HealthDashboardAPI:
    def __init__(self, monitor: HealthMonitor):
        self.monitor = monitor
    
    async def get_dashboard(self) -> Dict[str, Any]:
        """Get the main dashboard data"""
        return self.monitor.get_overall_health_dashboard()
    
    async def get_service_details(self, service_name: str) -> Dict[str, Any]:
        """Get detailed health info for a service"""
        return self.monitor.get_service_health_summary(service_name)
    
    async def get_alerts(self) -> Dict[str, Any]:
        """Get all active alerts"""
        all_alerts = []
        for service_name, alerts in self.monitor.active_alerts.items():
            for alert in alerts:
                if not alert.resolved:
                    all_alerts.append({
                        "service_name": service_name,
                        "severity": alert.severity.value,
                        "message": alert.message,
                        "timestamp": alert.timestamp.isoformat()
                    })
        
        # Sort by severity and timestamp
        severity_order = {"critical": 0, "error": 1, "warning": 2, "info": 3}
        all_alerts.sort(key=lambda x: (severity_order.get(x["severity"], 4), x["timestamp"]), reverse=True)
        
        return {"alerts": all_alerts, "count": len(all_alerts)}

# Example usage
async def main():
    discovery = ServiceDiscovery()
    monitor = HealthMonitor(discovery, check_interval=30)
    
    # Register custom health checks
    async def custom_db_check(service: ServiceInfo):
        # Custom database health check logic
        metrics = HealthMetrics()
        metrics.custom_metrics["connection_pool_size"] = 10
        metrics.custom_metrics["query_latency_ms"] = 25
        
        return HealthCheckResult(
            service_name=service.name,
            check_type=HealthCheckType.CUSTOM,
            status=ServiceStatus.HEALTHY,
            timestamp=datetime.now(),
            metrics=metrics
        )
    
    monitor.register_custom_health_check("database-service", custom_db_check)
    
    # Start monitoring
    print("Starting health monitoring system...")
    await monitor.start_monitoring()

if __name__ == "__main__":
    asyncio.run(main())