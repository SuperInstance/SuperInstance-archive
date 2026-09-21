"""
ActiveLog Audit Tools - Service Health Checker
Comprehensive health monitoring for all ActiveLog services
"""

import asyncio
import aiohttp
import json
import time
import subprocess
import psutil
import socket
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import logging
import sqlite3
import os
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded" 
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"

class ServiceType(Enum):
    WEB_SERVICE = "web_service"
    API_SERVICE = "api_service"
    DATABASE = "database"
    MICROSERVICE = "microservice"

@dataclass
class ServiceCheck:
    service_name: str
    service_type: ServiceType
    host: str
    port: int
    health_endpoint: Optional[str]
    expected_response_time: float  # seconds
    critical_endpoints: List[str]
    dependencies: List[str]
    process_name: Optional[str]
    config_file: Optional[str]

@dataclass
class HealthResult:
    service_name: str
    status: HealthStatus
    response_time: Optional[float]
    last_check: datetime
    error_message: Optional[str]
    details: Dict[str, Any]
    uptime: Optional[float]
    memory_usage: Optional[float]
    cpu_usage: Optional[float]

@dataclass
class SystemHealth:
    overall_status: HealthStatus
    services: Dict[str, HealthResult]
    system_metrics: Dict[str, float]
    alerts: List[str]
    recommendations: List[str]
    last_updated: datetime

class ServiceHealthChecker:
    def __init__(self, config_file: str = "health_config.json"):
        self.config_file = config_file
        self.services: Dict[str, ServiceCheck] = {}
        self.health_history: Dict[str, List[HealthResult]] = {}
        self.db_path = "audit_health.db"
        
        # Initialize database
        self._init_database()
        
        # Load service configurations
        self._load_service_configs()
    
    def _init_database(self):
        """Initialize SQLite database for health tracking"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS health_checks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service_name TEXT NOT NULL,
                status TEXT NOT NULL,
                response_time REAL,
                error_message TEXT,
                details TEXT,
                uptime REAL,
                memory_usage REAL,
                cpu_usage REAL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_name TEXT NOT NULL,
                metric_value REAL NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service_name TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                message TEXT NOT NULL,
                severity TEXT NOT NULL,
                resolved BOOLEAN DEFAULT FALSE,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create indexes for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_health_service_time ON health_checks(service_name, timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_metrics_name_time ON system_metrics(metric_name, timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_alerts_service ON alerts(service_name)')
        
        conn.commit()
        conn.close()
    
    def _load_service_configs(self):
        """Load service configurations"""
        # ActiveLog services configuration
        services_config = [
            {
                "service_name": "permissions",
                "service_type": "microservice",
                "host": "localhost",
                "port": 8000,
                "health_endpoint": "/health",
                "expected_response_time": 0.5,
                "critical_endpoints": ["/api/permissions", "/api/users"],
                "dependencies": ["database"],
                "process_name": "python3",
                "config_file": None
            },
            {
                "service_name": "voice-excellence",
                "service_type": "api_service", 
                "host": "localhost",
                "port": 8380,
                "health_endpoint": "/health",
                "expected_response_time": 1.0,
                "critical_endpoints": ["/api/voice/process", "/api/hands-free/start"],
                "dependencies": [],
                "process_name": "python3",
                "config_file": None
            },
            {
                "service_name": "dream-mode-v2",
                "service_type": "api_service",
                "host": "localhost", 
                "port": 8388,
                "health_endpoint": "/health",
                "expected_response_time": 1.0,
                "critical_endpoints": ["/api/status", "/api/industry/simulations"],
                "dependencies": [],
                "process_name": "python3",
                "config_file": None
            },
            {
                "service_name": "marketplace-v2",
                "service_type": "api_service",
                "host": "localhost",
                "port": 8390,
                "health_endpoint": "/health", 
                "expected_response_time": 1.0,
                "critical_endpoints": ["/api/analytics/overview", "/api/products/search"],
                "dependencies": [],
                "process_name": "python3",
                "config_file": None
            }
        ]
        
        # Convert to ServiceCheck objects
        for config in services_config:
            service_check = ServiceCheck(
                service_name=config["service_name"],
                service_type=ServiceType(config["service_type"]),
                host=config["host"],
                port=config["port"],
                health_endpoint=config["health_endpoint"],
                expected_response_time=config["expected_response_time"],
                critical_endpoints=config["critical_endpoints"],
                dependencies=config["dependencies"],
                process_name=config["process_name"],
                config_file=config["config_file"]
            )
            self.services[config["service_name"]] = service_check
    
    async def check_service_health(self, service: ServiceCheck) -> HealthResult:
        """Check health of a single service"""
        start_time = time.time()
        
        try:
            # Check if port is open
            if not self._is_port_open(service.host, service.port):
                return HealthResult(
                    service_name=service.service_name,
                    status=HealthStatus.UNHEALTHY,
                    response_time=None,
                    last_check=datetime.now(),
                    error_message=f"Port {service.port} is not accessible",
                    details={"port_status": "closed"},
                    uptime=None,
                    memory_usage=None,
                    cpu_usage=None
                )
            
            # Check HTTP health endpoint
            health_status = HealthStatus.UNKNOWN
            error_message = None
            details = {}
            response_time = None
            
            if service.health_endpoint:
                health_status, response_time, error_message, endpoint_details = await self._check_http_endpoint(
                    service.host, service.port, service.health_endpoint, service.expected_response_time
                )
                details.update(endpoint_details)
            
            # Check critical endpoints
            critical_status = await self._check_critical_endpoints(service)
            details["critical_endpoints"] = critical_status
            
            # Get process metrics
            uptime, memory_usage, cpu_usage = self._get_process_metrics(service)
            details["process_metrics"] = {
                "uptime": uptime,
                "memory_mb": memory_usage,
                "cpu_percent": cpu_usage
            }
            
            # Determine overall health status
            if health_status == HealthStatus.HEALTHY and all(critical_status.values()):
                final_status = HealthStatus.HEALTHY
            elif health_status == HealthStatus.DEGRADED or not all(critical_status.values()):
                final_status = HealthStatus.DEGRADED
            else:
                final_status = HealthStatus.UNHEALTHY
                
        except Exception as e:
            logger.error(f"Error checking {service.service_name}: {e}")
            final_status = HealthStatus.UNHEALTHY
            error_message = str(e)
            response_time = None
            uptime = None
            memory_usage = None
            cpu_usage = None
            details = {"error": str(e)}
        
        result = HealthResult(
            service_name=service.service_name,
            status=final_status,
            response_time=response_time,
            last_check=datetime.now(),
            error_message=error_message,
            details=details,
            uptime=uptime,
            memory_usage=memory_usage,
            cpu_usage=cpu_usage
        )
        
        # Store result in database
        self._store_health_result(result)
        
        return result
    
    def _is_port_open(self, host: str, port: int) -> bool:
        """Check if a port is open"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except Exception:
            return False
    
    async def _check_http_endpoint(self, host: str, port: int, endpoint: str, 
                                 expected_response_time: float) -> Tuple[HealthStatus, Optional[float], Optional[str], Dict[str, Any]]:
        """Check HTTP endpoint health"""
        url = f"http://{host}:{port}{endpoint}"
        start_time = time.time()
        
        try:
            timeout = aiohttp.ClientTimeout(total=expected_response_time * 2)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    response_time = time.time() - start_time
                    response_data = await response.text()
                    
                    details = {
                        "status_code": response.status,
                        "response_time": response_time,
                        "content_length": len(response_data)
                    }
                    
                    # Parse JSON response if possible
                    try:
                        json_data = json.loads(response_data)
                        details["response_data"] = json_data
                    except:
                        pass
                    
                    # Determine health status
                    if response.status == 200:
                        if response_time <= expected_response_time:
                            status = HealthStatus.HEALTHY
                        else:
                            status = HealthStatus.DEGRADED
                        error_message = None
                    elif 200 <= response.status < 500:
                        status = HealthStatus.DEGRADED
                        error_message = f"HTTP {response.status}"
                    else:
                        status = HealthStatus.UNHEALTHY
                        error_message = f"HTTP {response.status}"
                    
                    return status, response_time, error_message, details
                    
        except asyncio.TimeoutError:
            return HealthStatus.UNHEALTHY, None, "Timeout", {"error": "timeout"}
        except Exception as e:
            return HealthStatus.UNHEALTHY, None, str(e), {"error": str(e)}
    
    async def _check_critical_endpoints(self, service: ServiceCheck) -> Dict[str, bool]:
        """Check critical endpoints for a service"""
        results = {}
        
        for endpoint in service.critical_endpoints:
            try:
                url = f"http://{service.host}:{service.port}{endpoint}"
                timeout = aiohttp.ClientTimeout(total=10)
                
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(url) as response:
                        # Consider 2xx and 3xx as success
                        results[endpoint] = 200 <= response.status < 400
            except Exception as e:
                logger.debug(f"Critical endpoint {endpoint} failed: {e}")
                results[endpoint] = False
        
        return results
    
    def _get_process_metrics(self, service: ServiceCheck) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """Get process metrics for a service"""
        try:
            # Find processes by port
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
                try:
                    # Check if process is listening on the service port
                    connections = proc.connections()
                    for conn in connections:
                        if conn.laddr.port == service.port and conn.status == psutil.CONN_LISTEN:
                            processes.append(proc)
                            break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            if not processes:
                return None, None, None
            
            # Use the first matching process
            process = processes[0]
            
            # Calculate uptime
            create_time = process.create_time()
            uptime = time.time() - create_time
            
            # Get memory usage in MB
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            
            # Get CPU usage percentage
            cpu_percent = process.cpu_percent()
            
            return uptime, memory_mb, cpu_percent
            
        except Exception as e:
            logger.debug(f"Failed to get process metrics for {service.service_name}: {e}")
            return None, None, None
    
    def _store_health_result(self, result: HealthResult):
        """Store health check result in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO health_checks 
            (service_name, status, response_time, error_message, details, uptime, memory_usage, cpu_usage)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            result.service_name,
            result.status.value,
            result.response_time,
            result.error_message,
            json.dumps(result.details),
            result.uptime,
            result.memory_usage,
            result.cpu_usage
        ))
        
        conn.commit()
        conn.close()
    
    async def check_all_services(self) -> SystemHealth:
        """Check health of all configured services"""
        logger.info("Starting comprehensive health check of all services")
        
        # Check each service concurrently
        tasks = [self.check_service_health(service) for service in self.services.values()]
        service_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        health_results = {}
        healthy_count = 0
        degraded_count = 0
        unhealthy_count = 0
        
        for i, result in enumerate(service_results):
            if isinstance(result, Exception):
                service_name = list(self.services.keys())[i]
                result = HealthResult(
                    service_name=service_name,
                    status=HealthStatus.UNHEALTHY,
                    response_time=None,
                    last_check=datetime.now(),
                    error_message=str(result),
                    details={"exception": str(result)},
                    uptime=None,
                    memory_usage=None,
                    cpu_usage=None
                )
            
            health_results[result.service_name] = result
            
            if result.status == HealthStatus.HEALTHY:
                healthy_count += 1
            elif result.status == HealthStatus.DEGRADED:
                degraded_count += 1
            else:
                unhealthy_count += 1
        
        # Determine overall system health
        if unhealthy_count > 0:
            overall_status = HealthStatus.UNHEALTHY
        elif degraded_count > 0:
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.HEALTHY
        
        # Get system metrics
        system_metrics = self._get_system_metrics()
        
        # Generate alerts and recommendations
        alerts = self._generate_alerts(health_results, system_metrics)
        recommendations = self._generate_recommendations(health_results, system_metrics)
        
        system_health = SystemHealth(
            overall_status=overall_status,
            services=health_results,
            system_metrics=system_metrics,
            alerts=alerts,
            recommendations=recommendations,
            last_updated=datetime.now()
        )
        
        logger.info(f"Health check completed. Status: {overall_status.value}")
        logger.info(f"Services - Healthy: {healthy_count}, Degraded: {degraded_count}, Unhealthy: {unhealthy_count}")
        
        return system_health
    
    def _get_system_metrics(self) -> Dict[str, float]:
        """Get overall system metrics"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_available_gb = memory.available / 1024**3
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            disk_free_gb = disk.free / 1024**3
            
            # Network stats
            network = psutil.net_io_counters()
            
            # Load average (Linux/Mac)
            try:
                load_avg = os.getloadavg()[0]  # 1-minute load average
            except OSError:
                load_avg = 0.0
            
            metrics = {
                "cpu_usage_percent": cpu_percent,
                "memory_usage_percent": memory_percent,
                "memory_available_gb": memory_available_gb,
                "disk_usage_percent": disk_percent,
                "disk_free_gb": disk_free_gb,
                "network_bytes_sent": network.bytes_sent,
                "network_bytes_recv": network.bytes_recv,
                "load_average": load_avg,
                "active_connections": len(psutil.net_connections())
            }
            
            # Store metrics in database
            self._store_system_metrics(metrics)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to get system metrics: {e}")
            return {}
    
    def _store_system_metrics(self, metrics: Dict[str, float]):
        """Store system metrics in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for metric_name, metric_value in metrics.items():
            cursor.execute('''
                INSERT INTO system_metrics (metric_name, metric_value)
                VALUES (?, ?)
            ''', (metric_name, metric_value))
        
        conn.commit()
        conn.close()
    
    def _generate_alerts(self, health_results: Dict[str, HealthResult], 
                        system_metrics: Dict[str, float]) -> List[str]:
        """Generate alerts based on health check results"""
        alerts = []
        
        # Service-level alerts
        for service_name, result in health_results.items():
            if result.status == HealthStatus.UNHEALTHY:
                alerts.append(f"🔴 CRITICAL: {service_name} is unhealthy - {result.error_message or 'Unknown error'}")
            elif result.status == HealthStatus.DEGRADED:
                alerts.append(f"🟡 WARNING: {service_name} is degraded - Performance issues detected")
            
            # Response time alerts
            if result.response_time and result.response_time > self.services[service_name].expected_response_time * 2:
                alerts.append(f"⚠️  SLOW RESPONSE: {service_name} response time is {result.response_time:.2f}s")
            
            # Memory alerts
            if result.memory_usage and result.memory_usage > 1000:  # Over 1GB
                alerts.append(f"💾 HIGH MEMORY: {service_name} using {result.memory_usage:.1f}MB")
        
        # System-level alerts
        if system_metrics.get("cpu_usage_percent", 0) > 80:
            alerts.append(f"🔥 HIGH CPU: System CPU usage is {system_metrics['cpu_usage_percent']:.1f}%")
        
        if system_metrics.get("memory_usage_percent", 0) > 85:
            alerts.append(f"💾 HIGH MEMORY: System memory usage is {system_metrics['memory_usage_percent']:.1f}%")
        
        if system_metrics.get("disk_usage_percent", 0) > 90:
            alerts.append(f"💿 LOW DISK SPACE: Disk usage is {system_metrics['disk_usage_percent']:.1f}%")
        
        return alerts
    
    def _generate_recommendations(self, health_results: Dict[str, HealthResult],
                                system_metrics: Dict[str, float]) -> List[str]:
        """Generate recommendations based on health check results"""
        recommendations = []
        
        unhealthy_services = [name for name, result in health_results.items() 
                            if result.status == HealthStatus.UNHEALTHY]
        
        if unhealthy_services:
            recommendations.append(f"Investigate and restart unhealthy services: {', '.join(unhealthy_services)}")
        
        slow_services = [name for name, result in health_results.items()
                        if result.response_time and result.response_time > self.services[name].expected_response_time * 1.5]
        
        if slow_services:
            recommendations.append(f"Optimize performance for slow services: {', '.join(slow_services)}")
        
        # System recommendations
        if system_metrics.get("cpu_usage_percent", 0) > 70:
            recommendations.append("Consider CPU optimization or scaling up resources")
        
        if system_metrics.get("memory_usage_percent", 0) > 80:
            recommendations.append("Monitor memory usage and consider adding more RAM")
        
        if system_metrics.get("disk_usage_percent", 0) > 80:
            recommendations.append("Clean up disk space or add more storage")
        
        # Service-specific recommendations
        high_memory_services = [name for name, result in health_results.items()
                              if result.memory_usage and result.memory_usage > 500]
        
        if high_memory_services:
            recommendations.append(f"Review memory usage for: {', '.join(high_memory_services)}")
        
        return recommendations
    
    def get_health_history(self, service_name: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Get health check history for a service"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        cursor.execute('''
            SELECT service_name, status, response_time, error_message, uptime, 
                   memory_usage, cpu_usage, timestamp
            FROM health_checks 
            WHERE service_name = ? AND timestamp >= ?
            ORDER BY timestamp DESC
        ''', (service_name, cutoff_time))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                "service_name": row[0],
                "status": row[1],
                "response_time": row[2],
                "error_message": row[3],
                "uptime": row[4],
                "memory_usage": row[5],
                "cpu_usage": row[6],
                "timestamp": row[7]
            })
        
        conn.close()
        return results
    
    def generate_health_report(self, system_health: SystemHealth) -> str:
        """Generate a comprehensive health report"""
        report = [
            "=" * 60,
            "ACTIVELOG SYSTEM HEALTH REPORT",
            "=" * 60,
            f"Generated: {system_health.last_updated.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Overall Status: {system_health.overall_status.value.upper()}",
            "",
            "SERVICE STATUS:",
            "-" * 40
        ]
        
        for service_name, result in system_health.services.items():
            status_icon = {
                HealthStatus.HEALTHY: "✅",
                HealthStatus.DEGRADED: "⚠️ ",
                HealthStatus.UNHEALTHY: "❌",
                HealthStatus.UNKNOWN: "❓"
            }[result.status]
            
            report.append(f"{status_icon} {service_name.ljust(20)} {result.status.value.upper()}")
            
            if result.response_time:
                report.append(f"   Response Time: {result.response_time:.3f}s")
            
            if result.memory_usage:
                report.append(f"   Memory: {result.memory_usage:.1f}MB")
            
            if result.error_message:
                report.append(f"   Error: {result.error_message}")
            
            report.append("")
        
        # System metrics
        report.extend([
            "SYSTEM METRICS:",
            "-" * 40,
            f"CPU Usage: {system_health.system_metrics.get('cpu_usage_percent', 0):.1f}%",
            f"Memory Usage: {system_health.system_metrics.get('memory_usage_percent', 0):.1f}%",
            f"Disk Usage: {system_health.system_metrics.get('disk_usage_percent', 0):.1f}%",
            f"Load Average: {system_health.system_metrics.get('load_average', 0):.2f}",
            ""
        ])
        
        # Alerts
        if system_health.alerts:
            report.extend([
                "ALERTS:",
                "-" * 40
            ])
            for alert in system_health.alerts:
                report.append(f"• {alert}")
            report.append("")
        
        # Recommendations
        if system_health.recommendations:
            report.extend([
                "RECOMMENDATIONS:",
                "-" * 40
            ])
            for rec in system_health.recommendations:
                report.append(f"• {rec}")
        
        report.append("=" * 60)
        
        return "\n".join(report)

async def main():
    """Run comprehensive health check"""
    checker = ServiceHealthChecker()
    
    print("🏥 ActiveLog System Health Checker")
    print("=" * 50)
    
    # Run health check
    system_health = await checker.check_all_services()
    
    # Generate and display report
    report = checker.generate_health_report(system_health)
    print(report)
    
    # Save report to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"health_report_{timestamp}.txt"
    
    with open(report_file, 'w') as f:
        f.write(report)
    
    print(f"\n📄 Full report saved to: {report_file}")
    
    return system_health

if __name__ == "__main__":
    result = asyncio.run(main())