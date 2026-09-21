"""
Comprehensive Health Check System for ActiveLog Production

Provides detailed health monitoring for all system components:
- Database connectivity and performance
- Redis availability and memory usage
- File system health and disk space
- External service dependencies
- Application metrics and status
- Circuit breaker states
- Cache hit rates
"""

import time
import psutil
import logging
import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta
import json
import redis
import psycopg2
import requests
from pathlib import Path

logger = logging.getLogger(__name__)

class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"

@dataclass
class HealthCheckResult:
    name: str
    status: HealthStatus
    response_time_ms: float
    message: str
    details: Dict[str, Any] = None
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat() + "Z"
        if self.details is None:
            self.details = {}

class BaseHealthCheck:
    """Base class for health checks"""
    
    def __init__(self, name: str, timeout: float = 10.0):
        self.name = name
        self.timeout = timeout
    
    async def check(self) -> HealthCheckResult:
        """Perform health check"""
        start_time = time.time()
        try:
            result = await asyncio.wait_for(self._check(), timeout=self.timeout)
            response_time = (time.time() - start_time) * 1000
            
            return HealthCheckResult(
                name=self.name,
                status=result.get("status", HealthStatus.HEALTHY),
                response_time_ms=response_time,
                message=result.get("message", "Health check passed"),
                details=result.get("details", {})
            )
        except asyncio.TimeoutError:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                response_time_ms=response_time,
                message=f"Health check timed out after {self.timeout}s",
                details={"timeout": self.timeout}
            )
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                response_time_ms=response_time,
                message=f"Health check failed: {str(e)}",
                details={"error": str(e), "error_type": type(e).__name__}
            )
    
    async def _check(self) -> Dict[str, Any]:
        """Override this method in subclasses"""
        raise NotImplementedError

class DatabaseHealthCheck(BaseHealthCheck):
    """PostgreSQL database health check"""
    
    def __init__(self, connection_string: str, **kwargs):
        super().__init__("database", **kwargs)
        self.connection_string = connection_string
    
    async def _check(self) -> Dict[str, Any]:
        conn = None
        try:
            # Test connection
            conn = psycopg2.connect(self.connection_string)
            cursor = conn.cursor()
            
            # Test basic query
            start_query = time.time()
            cursor.execute("SELECT 1")
            query_time = (time.time() - start_query) * 1000
            
            # Get database stats
            cursor.execute("""
                SELECT 
                    pg_database_size(current_database()) as db_size,
                    (SELECT count(*) FROM pg_stat_activity) as connections,
                    (SELECT count(*) FROM pg_stat_activity WHERE state = 'active') as active_connections,
                    (SELECT ROUND(100.0 * sum(heap_blks_hit) / NULLIF(sum(heap_blks_hit + heap_blks_read), 0), 2)) as cache_hit_ratio
                FROM pg_statio_user_tables
            """)
            
            db_size, connections, active_connections, cache_hit_ratio = cursor.fetchone()
            
            # Check for long-running queries
            cursor.execute("""
                SELECT count(*) 
                FROM pg_stat_activity 
                WHERE state = 'active' 
                AND query_start < NOW() - INTERVAL '5 minutes'
                AND query NOT LIKE '%pg_stat_activity%'
            """)
            long_queries = cursor.fetchone()[0]
            
            # Determine status
            status = HealthStatus.HEALTHY
            message = "Database is healthy"
            
            if cache_hit_ratio and cache_hit_ratio < 95:
                status = HealthStatus.DEGRADED
                message = f"Low cache hit ratio: {cache_hit_ratio}%"
            
            if active_connections > 80:  # Assuming max_connections is 100
                status = HealthStatus.DEGRADED
                message = f"High connection count: {active_connections}"
            
            if long_queries > 0:
                status = HealthStatus.DEGRADED
                message = f"Long running queries detected: {long_queries}"
            
            return {
                "status": status,
                "message": message,
                "details": {
                    "database_size_bytes": db_size,
                    "database_size_mb": round(db_size / 1024 / 1024, 2) if db_size else 0,
                    "total_connections": connections,
                    "active_connections": active_connections,
                    "cache_hit_ratio": cache_hit_ratio,
                    "long_running_queries": long_queries,
                    "query_response_time_ms": round(query_time, 2)
                }
            }
            
        finally:
            if conn:
                conn.close()

class RedisHealthCheck(BaseHealthCheck):
    """Redis health check"""
    
    def __init__(self, host: str = "redis-master", port: int = 6379, **kwargs):
        super().__init__("redis", **kwargs)
        self.host = host
        self.port = port
    
    async def _check(self) -> Dict[str, Any]:
        client = redis.Redis(host=self.host, port=self.port, socket_timeout=5)
        
        try:
            # Test basic connectivity
            start_ping = time.time()
            ping_result = client.ping()
            ping_time = (time.time() - start_ping) * 1000
            
            if not ping_result:
                return {
                    "status": HealthStatus.UNHEALTHY,
                    "message": "Redis ping failed"
                }
            
            # Get Redis info
            info = client.info()
            memory_info = client.info('memory')
            
            # Calculate memory usage percentage
            used_memory = memory_info.get('used_memory', 0)
            max_memory = memory_info.get('maxmemory', 0)
            memory_usage_pct = 0
            if max_memory > 0:
                memory_usage_pct = (used_memory / max_memory) * 100
            
            # Test read/write operations
            test_key = "health_check_test"
            client.set(test_key, "test_value", ex=60)
            test_value = client.get(test_key)
            client.delete(test_key)
            
            if test_value != b'test_value':
                return {
                    "status": HealthStatus.UNHEALTHY,
                    "message": "Redis read/write test failed"
                }
            
            # Determine status
            status = HealthStatus.HEALTHY
            message = "Redis is healthy"
            
            if memory_usage_pct > 90:
                status = HealthStatus.UNHEALTHY
                message = f"Redis memory usage critical: {memory_usage_pct:.1f}%"
            elif memory_usage_pct > 80:
                status = HealthStatus.DEGRADED
                message = f"Redis memory usage high: {memory_usage_pct:.1f}%"
            
            if info.get('connected_clients', 0) > 900:  # Assuming max 1000 clients
                status = HealthStatus.DEGRADED
                message = f"High Redis client count: {info.get('connected_clients')}"
            
            return {
                "status": status,
                "message": message,
                "details": {
                    "ping_time_ms": round(ping_time, 2),
                    "connected_clients": info.get('connected_clients', 0),
                    "used_memory_mb": round(used_memory / 1024 / 1024, 2),
                    "memory_usage_percent": round(memory_usage_pct, 2),
                    "total_connections_received": info.get('total_connections_received', 0),
                    "keyspace_hits": info.get('keyspace_hits', 0),
                    "keyspace_misses": info.get('keyspace_misses', 0),
                    "uptime_seconds": info.get('uptime_in_seconds', 0),
                    "redis_version": info.get('redis_version', 'unknown')
                }
            }
            
        finally:
            client.close()

class FileSystemHealthCheck(BaseHealthCheck):
    """File system health check"""
    
    def __init__(self, paths: List[str], **kwargs):
        super().__init__("filesystem", **kwargs)
        self.paths = paths
    
    async def _check(self) -> Dict[str, Any]:
        path_details = {}
        overall_status = HealthStatus.HEALTHY
        messages = []
        
        for path in self.paths:
            try:
                path_obj = Path(path)
                
                # Check if path exists
                if not path_obj.exists():
                    path_details[path] = {
                        "exists": False,
                        "error": "Path does not exist"
                    }
                    overall_status = HealthStatus.UNHEALTHY
                    messages.append(f"Path {path} does not exist")
                    continue
                
                # Get disk usage
                usage = psutil.disk_usage(path)
                free_percent = (usage.free / usage.total) * 100
                used_percent = (usage.used / usage.total) * 100
                
                # Check permissions
                readable = path_obj.is_dir() and access(path, os.R_OK) if path_obj.is_dir() else path_obj.is_file() and access(path, os.R_OK)
                writable = access(path, os.W_OK)
                
                path_details[path] = {
                    "exists": True,
                    "is_directory": path_obj.is_dir(),
                    "readable": readable,
                    "writable": writable,
                    "total_gb": round(usage.total / 1024**3, 2),
                    "used_gb": round(usage.used / 1024**3, 2),
                    "free_gb": round(usage.free / 1024**3, 2),
                    "used_percent": round(used_percent, 2),
                    "free_percent": round(free_percent, 2)
                }
                
                # Check disk space
                if free_percent < 5:
                    overall_status = HealthStatus.UNHEALTHY
                    messages.append(f"Critical disk space on {path}: {free_percent:.1f}% free")
                elif free_percent < 15:
                    if overall_status == HealthStatus.HEALTHY:
                        overall_status = HealthStatus.DEGRADED
                    messages.append(f"Low disk space on {path}: {free_percent:.1f}% free")
                
                # Check permissions
                if not readable or not writable:
                    overall_status = HealthStatus.UNHEALTHY
                    messages.append(f"Permission issues on {path}: readable={readable}, writable={writable}")
                
            except Exception as e:
                path_details[path] = {
                    "error": str(e)
                }
                overall_status = HealthStatus.UNHEALTHY
                messages.append(f"Error checking {path}: {str(e)}")
        
        message = "File system is healthy"
        if messages:
            message = "; ".join(messages)
        
        return {
            "status": overall_status,
            "message": message,
            "details": {
                "paths": path_details,
                "system_disk_io": self._get_disk_io_stats()
            }
        }
    
    def _get_disk_io_stats(self) -> Dict[str, Any]:
        """Get system disk I/O statistics"""
        try:
            disk_io = psutil.disk_io_counters()
            if disk_io:
                return {
                    "read_bytes": disk_io.read_bytes,
                    "write_bytes": disk_io.write_bytes,
                    "read_count": disk_io.read_count,
                    "write_count": disk_io.write_count,
                    "read_time": disk_io.read_time,
                    "write_time": disk_io.write_time
                }
        except:
            pass
        return {}

class ExternalServiceHealthCheck(BaseHealthCheck):
    """External service health check via HTTP"""
    
    def __init__(self, name: str, url: str, expected_status: int = 200, **kwargs):
        super().__init__(name, **kwargs)
        self.url = url
        self.expected_status = expected_status
    
    async def _check(self) -> Dict[str, Any]:
        try:
            start_time = time.time()
            response = requests.get(self.url, timeout=self.timeout)
            response_time = (time.time() - start_time) * 1000
            
            status = HealthStatus.HEALTHY
            message = f"Service responded with {response.status_code}"
            
            if response.status_code != self.expected_status:
                status = HealthStatus.UNHEALTHY
                message = f"Unexpected status code: {response.status_code} (expected {self.expected_status})"
            
            # Parse response if JSON
            response_data = {}
            try:
                response_data = response.json()
            except:
                pass
            
            return {
                "status": status,
                "message": message,
                "details": {
                    "url": self.url,
                    "status_code": response.status_code,
                    "response_time_ms": round(response_time, 2),
                    "response_size_bytes": len(response.content),
                    "response_data": response_data
                }
            }
            
        except requests.exceptions.Timeout:
            return {
                "status": HealthStatus.UNHEALTHY,
                "message": f"Request timeout after {self.timeout}s",
                "details": {"url": self.url, "timeout": self.timeout}
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": HealthStatus.UNHEALTHY,
                "message": "Connection error",
                "details": {"url": self.url}
            }

class SystemResourcesHealthCheck(BaseHealthCheck):
    """System resources health check"""
    
    def __init__(self, **kwargs):
        super().__init__("system_resources", **kwargs)
    
    async def _check(self) -> Dict[str, Any]:
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        
        # Memory usage
        memory = psutil.virtual_memory()
        
        # Load average (Unix only)
        load_avg = None
        try:
            load_avg = psutil.getloadavg()
        except:
            pass
        
        # Network I/O
        network_io = psutil.net_io_counters()
        
        # Determine status
        status = HealthStatus.HEALTHY
        messages = []
        
        if cpu_percent > 90:
            status = HealthStatus.UNHEALTHY
            messages.append(f"Critical CPU usage: {cpu_percent}%")
        elif cpu_percent > 80:
            status = HealthStatus.DEGRADED
            messages.append(f"High CPU usage: {cpu_percent}%")
        
        if memory.percent > 95:
            status = HealthStatus.UNHEALTHY
            messages.append(f"Critical memory usage: {memory.percent}%")
        elif memory.percent > 85:
            if status == HealthStatus.HEALTHY:
                status = HealthStatus.DEGRADED
            messages.append(f"High memory usage: {memory.percent}%")
        
        message = "System resources are healthy"
        if messages:
            message = "; ".join(messages)
        
        details = {
            "cpu": {
                "usage_percent": round(cpu_percent, 2),
                "count": cpu_count
            },
            "memory": {
                "total_gb": round(memory.total / 1024**3, 2),
                "available_gb": round(memory.available / 1024**3, 2),
                "used_gb": round(memory.used / 1024**3, 2),
                "usage_percent": round(memory.percent, 2),
                "free_gb": round(memory.free / 1024**3, 2)
            },
            "network": {
                "bytes_sent": network_io.bytes_sent,
                "bytes_recv": network_io.bytes_recv,
                "packets_sent": network_io.packets_sent,
                "packets_recv": network_io.packets_recv
            }
        }
        
        if load_avg:
            details["load_average"] = {
                "1min": round(load_avg[0], 2),
                "5min": round(load_avg[1], 2), 
                "15min": round(load_avg[2], 2)
            }
        
        return {
            "status": status,
            "message": message,
            "details": details
        }

class HealthCheckManager:
    """Manages and orchestrates health checks"""
    
    def __init__(self):
        self.checks: List[BaseHealthCheck] = []
        self.last_results: Dict[str, HealthCheckResult] = {}
    
    def add_check(self, health_check: BaseHealthCheck):
        """Add a health check"""
        self.checks.append(health_check)
    
    async def run_all_checks(self) -> Dict[str, Any]:
        """Run all health checks"""
        start_time = time.time()
        
        # Run all checks concurrently
        tasks = [check.check() for check in self.checks]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        check_results = {}
        overall_status = HealthStatus.HEALTHY
        
        for i, result in enumerate(results):
            check_name = self.checks[i].name
            
            if isinstance(result, Exception):
                # Handle exceptions from health checks
                result = HealthCheckResult(
                    name=check_name,
                    status=HealthStatus.UNHEALTHY,
                    response_time_ms=0,
                    message=f"Health check exception: {str(result)}",
                    details={"error": str(result)}
                )
            
            check_results[check_name] = asdict(result)
            self.last_results[check_name] = result
            
            # Update overall status
            if result.status == HealthStatus.UNHEALTHY:
                overall_status = HealthStatus.UNHEALTHY
            elif result.status == HealthStatus.DEGRADED and overall_status == HealthStatus.HEALTHY:
                overall_status = HealthStatus.DEGRADED
        
        total_time = (time.time() - start_time) * 1000
        
        return {
            "status": overall_status.value,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "total_check_time_ms": round(total_time, 2),
            "checks": check_results,
            "summary": {
                "total_checks": len(self.checks),
                "healthy_checks": len([r for r in check_results.values() if r["status"] == "healthy"]),
                "degraded_checks": len([r for r in check_results.values() if r["status"] == "degraded"]),
                "unhealthy_checks": len([r for r in check_results.values() if r["status"] == "unhealthy"])
            }
        }
    
    async def run_single_check(self, check_name: str) -> Optional[Dict[str, Any]]:
        """Run a single health check by name"""
        for check in self.checks:
            if check.name == check_name:
                result = await check.check()
                self.last_results[check_name] = result
                return asdict(result)
        return None
    
    def get_last_results(self) -> Dict[str, Any]:
        """Get the last health check results"""
        return {name: asdict(result) for name, result in self.last_results.items()}

# Global health check manager
health_manager = HealthCheckManager()

def init_health_checks(config: Dict[str, Any]):
    """Initialize health checks based on configuration"""
    
    # Database health check
    if "database" in config:
        db_config = config["database"]
        health_manager.add_check(DatabaseHealthCheck(
            connection_string=db_config.get("connection_string"),
            timeout=db_config.get("timeout", 10)
        ))
    
    # Redis health check
    if "redis" in config:
        redis_config = config["redis"]
        health_manager.add_check(RedisHealthCheck(
            host=redis_config.get("host", "redis-master"),
            port=redis_config.get("port", 6379),
            timeout=redis_config.get("timeout", 5)
        ))
    
    # File system health checks
    if "filesystem" in config:
        fs_config = config["filesystem"]
        health_manager.add_check(FileSystemHealthCheck(
            paths=fs_config.get("paths", ["/opt/activelog"]),
            timeout=fs_config.get("timeout", 5)
        ))
    
    # External service health checks
    if "external_services" in config:
        for service_name, service_config in config["external_services"].items():
            health_manager.add_check(ExternalServiceHealthCheck(
                name=f"external_{service_name}",
                url=service_config["url"],
                expected_status=service_config.get("expected_status", 200),
                timeout=service_config.get("timeout", 10)
            ))
    
    # System resources health check
    health_manager.add_check(SystemResourcesHealthCheck(timeout=5))

# Flask integration
def create_health_endpoints(app):
    """Create health check endpoints for Flask app"""
    
    @app.route('/health')
    async def health_check():
        """Basic health check endpoint"""
        try:
            results = await health_manager.run_all_checks()
            status_code = 200 if results["status"] == "healthy" else 503
            return results, status_code
        except Exception as e:
            return {
                "status": "unhealthy",
                "message": f"Health check error: {str(e)}",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }, 503
    
    @app.route('/health/<check_name>')
    async def individual_health_check(check_name):
        """Individual health check endpoint"""
        try:
            result = await health_manager.run_single_check(check_name)
            if result is None:
                return {"error": f"Health check '{check_name}' not found"}, 404
            
            status_code = 200 if result["status"] == "healthy" else 503
            return result, status_code
        except Exception as e:
            return {
                "status": "unhealthy",
                "message": f"Health check error: {str(e)}",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }, 503
    
    @app.route('/health/status')
    def health_status():
        """Quick health status without running checks"""
        results = health_manager.get_last_results()
        if not results:
            return {"status": "unknown", "message": "No health checks have been run"}, 503
        
        # Determine overall status from last results
        statuses = [result["status"] for result in results.values()]
        if "unhealthy" in statuses:
            overall_status = "unhealthy"
        elif "degraded" in statuses:
            overall_status = "degraded"
        else:
            overall_status = "healthy"
        
        return {
            "status": overall_status,
            "last_check_time": max(result["timestamp"] for result in results.values()),
            "summary": {
                "total_checks": len(results),
                "healthy": len([s for s in statuses if s == "healthy"]),
                "degraded": len([s for s in statuses if s == "degraded"]),
                "unhealthy": len([s for s in statuses if s == "unhealthy"])
            }
        }

# Example configuration
HEALTH_CHECK_CONFIG = {
    "database": {
        "connection_string": "postgresql://activelog_admin@postgres:5432/activelog_prod",
        "timeout": 10
    },
    "redis": {
        "host": "redis-master",
        "port": 6379,
        "timeout": 5
    },
    "filesystem": {
        "paths": ["/opt/activelog", "/opt/activelog/data", "/opt/activelog/logs"],
        "timeout": 5
    },
    "external_services": {
        "auth_service": {
            "url": "http://auth:8001/health",
            "timeout": 5
        },
        "file_processor": {
            "url": "http://file-processor:8003/health",
            "timeout": 10
        }
    }
}