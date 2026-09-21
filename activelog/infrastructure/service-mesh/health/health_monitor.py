import asyncio
import aiohttp
import socket
import time
import threading
import logging
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Tuple, Set
from dataclasses import dataclass, asdict
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, as_completed
import statistics
import subprocess


class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class CheckType(Enum):
    HTTP = "http"
    TCP = "tcp"
    GRPC = "grpc"
    DATABASE = "database"
    REDIS = "redis"
    RABBITMQ = "rabbitmq"
    CUSTOM = "custom"


@dataclass
class HealthCheckConfig:
    check_id: str
    service_name: str
    check_type: CheckType
    target: str  # URL, host:port, connection string
    interval: int  # seconds
    timeout: int  # seconds
    retries: int = 3
    expected_codes: List[int] = None  # For HTTP checks
    expected_response: str = None  # Expected response content
    headers: Dict[str, str] = None  # For HTTP checks
    metadata: Dict[str, Any] = None
    enabled: bool = True


@dataclass
class HealthCheckResult:
    check_id: str
    service_name: str
    status: HealthStatus
    response_time: float  # milliseconds
    message: str
    timestamp: datetime
    details: Dict[str, Any] = None
    error: Optional[str] = None


@dataclass
class ServiceHealth:
    service_name: str
    overall_status: HealthStatus
    checks: List[HealthCheckResult]
    last_updated: datetime
    uptime_percentage: float = 0.0
    avg_response_time: float = 0.0


class HealthChecker:
    """Individual health check implementations"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def check_http(self, config: HealthCheckConfig) -> HealthCheckResult:
        """Perform HTTP health check"""
        start_time = time.time()
        
        try:
            headers = config.headers or {}
            timeout = aiohttp.ClientTimeout(total=config.timeout)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(config.target, headers=headers) as response:
                    response_time = (time.time() - start_time) * 1000
                    response_text = await response.text()
                    
                    # Check response code
                    expected_codes = config.expected_codes or [200]
                    if response.status not in expected_codes:
                        return HealthCheckResult(
                            check_id=config.check_id,
                            service_name=config.service_name,
                            status=HealthStatus.UNHEALTHY,
                            response_time=response_time,
                            message=f"HTTP {response.status}: {response.reason}",
                            timestamp=datetime.now(),
                            details={"status_code": response.status, "response": response_text[:500]},
                            error=f"Unexpected status code: {response.status}"
                        )
                    
                    # Check response content if specified
                    if config.expected_response and config.expected_response not in response_text:
                        return HealthCheckResult(
                            check_id=config.check_id,
                            service_name=config.service_name,
                            status=HealthStatus.DEGRADED,
                            response_time=response_time,
                            message="Response content mismatch",
                            timestamp=datetime.now(),
                            details={"expected": config.expected_response, "actual": response_text[:500]},
                            error="Response content does not match expected pattern"
                        )
                    
                    # Determine status based on response time
                    if response_time > config.timeout * 1000 * 0.8:  # 80% of timeout
                        status = HealthStatus.DEGRADED
                        message = f"Slow response: {response_time:.2f}ms"
                    else:
                        status = HealthStatus.HEALTHY
                        message = f"OK: {response_time:.2f}ms"
                    
                    return HealthCheckResult(
                        check_id=config.check_id,
                        service_name=config.service_name,
                        status=status,
                        response_time=response_time,
                        message=message,
                        timestamp=datetime.now(),
                        details={"status_code": response.status, "content_length": len(response_text)}
                    )
                    
        except asyncio.TimeoutError:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                check_id=config.check_id,
                service_name=config.service_name,
                status=HealthStatus.CRITICAL,
                response_time=response_time,
                message=f"Timeout after {config.timeout}s",
                timestamp=datetime.now(),
                error="Request timeout"
            )
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                check_id=config.check_id,
                service_name=config.service_name,
                status=HealthStatus.CRITICAL,
                response_time=response_time,
                message=f"Connection failed: {str(e)}",
                timestamp=datetime.now(),
                error=str(e)
            )
    
    def check_tcp(self, config: HealthCheckConfig) -> HealthCheckResult:
        """Perform TCP port check"""
        start_time = time.time()
        
        try:
            # Parse host:port
            if ":" not in config.target:
                raise ValueError("TCP target must be in format host:port")
            
            host, port = config.target.rsplit(":", 1)
            port = int(port)
            
            # Create socket connection
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(config.timeout)
            
            result = sock.connect_ex((host, port))
            response_time = (time.time() - start_time) * 1000
            sock.close()
            
            if result == 0:
                status = HealthStatus.HEALTHY if response_time < 1000 else HealthStatus.DEGRADED
                message = f"TCP connection OK: {response_time:.2f}ms"
            else:
                status = HealthStatus.CRITICAL
                message = f"TCP connection failed: error {result}"
            
            return HealthCheckResult(
                check_id=config.check_id,
                service_name=config.service_name,
                status=status,
                response_time=response_time,
                message=message,
                timestamp=datetime.now(),
                details={"host": host, "port": port, "error_code": result}
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                check_id=config.check_id,
                service_name=config.service_name,
                status=HealthStatus.CRITICAL,
                response_time=response_time,
                message=f"TCP check failed: {str(e)}",
                timestamp=datetime.now(),
                error=str(e)
            )
    
    def check_database(self, config: HealthCheckConfig) -> HealthCheckResult:
        """Perform database connectivity check"""
        start_time = time.time()
        
        try:
            # Simple SQLite check for demonstration
            if config.target.startswith("sqlite:"):
                db_path = config.target.replace("sqlite:", "")
                conn = sqlite3.connect(db_path, timeout=config.timeout)
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                conn.close()
                
                response_time = (time.time() - start_time) * 1000
                
                if result and result[0] == 1:
                    return HealthCheckResult(
                        check_id=config.check_id,
                        service_name=config.service_name,
                        status=HealthStatus.HEALTHY,
                        response_time=response_time,
                        message=f"Database OK: {response_time:.2f}ms",
                        timestamp=datetime.now(),
                        details={"db_type": "sqlite", "query": "SELECT 1"}
                    )
            
            # For other databases, you would implement specific connection logic
            return HealthCheckResult(
                check_id=config.check_id,
                service_name=config.service_name,
                status=HealthStatus.UNKNOWN,
                response_time=0,
                message="Database type not implemented",
                timestamp=datetime.now(),
                error="Unsupported database type"
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                check_id=config.check_id,
                service_name=config.service_name,
                status=HealthStatus.CRITICAL,
                response_time=response_time,
                message=f"Database check failed: {str(e)}",
                timestamp=datetime.now(),
                error=str(e)
            )
    
    def check_custom(self, config: HealthCheckConfig) -> HealthCheckResult:
        """Perform custom script-based health check"""
        start_time = time.time()
        
        try:
            # Execute custom script/command
            result = subprocess.run(
                config.target.split(),
                capture_output=True,
                text=True,
                timeout=config.timeout
            )
            
            response_time = (time.time() - start_time) * 1000
            
            # Check exit code
            if result.returncode == 0:
                status = HealthStatus.HEALTHY
                message = f"Custom check passed: {response_time:.2f}ms"
            else:
                status = HealthStatus.UNHEALTHY
                message = f"Custom check failed (exit {result.returncode}): {result.stderr[:100]}"
            
            return HealthCheckResult(
                check_id=config.check_id,
                service_name=config.service_name,
                status=status,
                response_time=response_time,
                message=message,
                timestamp=datetime.now(),
                details={
                    "exit_code": result.returncode,
                    "stdout": result.stdout[:500],
                    "stderr": result.stderr[:500]
                }
            )
            
        except subprocess.TimeoutExpired:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                check_id=config.check_id,
                service_name=config.service_name,
                status=HealthStatus.CRITICAL,
                response_time=response_time,
                message=f"Custom check timeout after {config.timeout}s",
                timestamp=datetime.now(),
                error="Command timeout"
            )
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                check_id=config.check_id,
                service_name=config.service_name,
                status=HealthStatus.CRITICAL,
                response_time=response_time,
                message=f"Custom check error: {str(e)}",
                timestamp=datetime.now(),
                error=str(e)
            )


class HealthMonitor:
    """Main health monitoring system"""
    
    def __init__(self, db_path: str = "health_monitor.db", max_workers: int = 20):
        self.db_path = db_path
        self.max_workers = max_workers
        self.checks: Dict[str, HealthCheckConfig] = {}
        self.results: Dict[str, List[HealthCheckResult]] = {}
        self.running = False
        self.check_threads: Dict[str, threading.Thread] = {}
        self.callbacks: Dict[str, List[Callable[[HealthCheckResult], None]]] = {}
        self.checker = HealthChecker()
        self.logger = logging.getLogger(__name__)
        
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database for storing health check results"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS health_checks (
                check_id TEXT PRIMARY KEY,
                service_name TEXT NOT NULL,
                check_type TEXT NOT NULL,
                target TEXT NOT NULL,
                config TEXT NOT NULL,
                enabled BOOLEAN DEFAULT TRUE,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS health_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                check_id TEXT NOT NULL,
                service_name TEXT NOT NULL,
                status TEXT NOT NULL,
                response_time REAL NOT NULL,
                message TEXT,
                timestamp TEXT NOT NULL,
                details TEXT,
                error TEXT,
                INDEX (check_id, timestamp),
                INDEX (service_name, timestamp)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_health_check(self, config: HealthCheckConfig) -> bool:
        """Add a new health check"""
        try:
            # Store in memory
            self.checks[config.check_id] = config
            self.results[config.check_id] = []
            self.callbacks[config.check_id] = []
            
            # Store in database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO health_checks 
                (check_id, service_name, check_type, target, config, enabled, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                config.check_id,
                config.service_name,
                config.check_type.value,
                config.target,
                json.dumps(asdict(config)),
                config.enabled,
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            # Start monitoring if running
            if self.running and config.enabled:
                self._start_check_thread(config)
            
            self.logger.info(f"Added health check: {config.check_id} for {config.service_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add health check {config.check_id}: {e}")
            return False
    
    def remove_health_check(self, check_id: str) -> bool:
        """Remove a health check"""
        try:
            if check_id in self.checks:
                # Stop monitoring thread
                self._stop_check_thread(check_id)
                
                # Remove from memory
                del self.checks[check_id]
                del self.results[check_id]
                del self.callbacks[check_id]
                
                # Remove from database
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("DELETE FROM health_checks WHERE check_id = ?", (check_id,))
                conn.commit()
                conn.close()
                
                self.logger.info(f"Removed health check: {check_id}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to remove health check {check_id}: {e}")
            return False
    
    def _start_check_thread(self, config: HealthCheckConfig):
        """Start monitoring thread for a health check"""
        def monitor_loop():
            while self.running and config.check_id in self.checks:
                try:
                    # Perform health check with retries
                    result = None
                    for attempt in range(config.retries + 1):
                        result = self._perform_health_check(config)
                        
                        # If check passed or it's the last attempt, break
                        if result.status != HealthStatus.CRITICAL or attempt == config.retries:
                            break
                        
                        # Wait a bit before retry
                        time.sleep(1)
                    
                    if result:
                        # Store result
                        self._store_result(result)
                        
                        # Trigger callbacks
                        for callback in self.callbacks.get(config.check_id, []):
                            try:
                                callback(result)
                            except Exception as e:
                                self.logger.error(f"Callback error for {config.check_id}: {e}")
                    
                    # Wait for next check
                    time.sleep(config.interval)
                    
                except Exception as e:
                    self.logger.error(f"Error in health check thread {config.check_id}: {e}")
                    time.sleep(config.interval)
        
        thread = threading.Thread(target=monitor_loop, daemon=True, name=f"health-{config.check_id}")
        self.check_threads[config.check_id] = thread
        thread.start()
    
    def _stop_check_thread(self, check_id: str):
        """Stop monitoring thread for a health check"""
        if check_id in self.check_threads:
            del self.check_threads[check_id]
    
    def _perform_health_check(self, config: HealthCheckConfig) -> HealthCheckResult:
        """Perform a single health check"""
        try:
            if config.check_type == CheckType.HTTP:
                # Run async HTTP check
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(self.checker.check_http(config))
                finally:
                    loop.close()
                return result
            elif config.check_type == CheckType.TCP:
                return self.checker.check_tcp(config)
            elif config.check_type == CheckType.DATABASE:
                return self.checker.check_database(config)
            elif config.check_type == CheckType.CUSTOM:
                return self.checker.check_custom(config)
            else:
                return HealthCheckResult(
                    check_id=config.check_id,
                    service_name=config.service_name,
                    status=HealthStatus.UNKNOWN,
                    response_time=0,
                    message=f"Unsupported check type: {config.check_type.value}",
                    timestamp=datetime.now(),
                    error="Unsupported check type"
                )
                
        except Exception as e:
            return HealthCheckResult(
                check_id=config.check_id,
                service_name=config.service_name,
                status=HealthStatus.CRITICAL,
                response_time=0,
                message=f"Health check error: {str(e)}",
                timestamp=datetime.now(),
                error=str(e)
            )
    
    def _store_result(self, result: HealthCheckResult):
        """Store health check result"""
        try:
            # Store in memory (keep last 100 results)
            if result.check_id not in self.results:
                self.results[result.check_id] = []
            
            self.results[result.check_id].append(result)
            if len(self.results[result.check_id]) > 100:
                self.results[result.check_id] = self.results[result.check_id][-100:]
            
            # Store in database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO health_results 
                (check_id, service_name, status, response_time, message, timestamp, details, error)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                result.check_id,
                result.service_name,
                result.status.value,
                result.response_time,
                result.message,
                result.timestamp.isoformat(),
                json.dumps(result.details) if result.details else None,
                result.error
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Failed to store health result for {result.check_id}: {e}")
    
    def get_service_health(self, service_name: str) -> ServiceHealth:
        """Get current health status for a service"""
        service_checks = [check for check in self.checks.values() if check.service_name == service_name]
        
        if not service_checks:
            return ServiceHealth(
                service_name=service_name,
                overall_status=HealthStatus.UNKNOWN,
                checks=[],
                last_updated=datetime.now()
            )
        
        # Get latest results for each check
        latest_results = []
        for check in service_checks:
            if check.check_id in self.results and self.results[check.check_id]:
                latest_results.append(self.results[check.check_id][-1])
        
        if not latest_results:
            return ServiceHealth(
                service_name=service_name,
                overall_status=HealthStatus.UNKNOWN,
                checks=[],
                last_updated=datetime.now()
            )
        
        # Determine overall status
        statuses = [result.status for result in latest_results]
        if HealthStatus.CRITICAL in statuses:
            overall_status = HealthStatus.CRITICAL
        elif HealthStatus.UNHEALTHY in statuses:
            overall_status = HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            overall_status = HealthStatus.DEGRADED
        elif all(status == HealthStatus.HEALTHY for status in statuses):
            overall_status = HealthStatus.HEALTHY
        else:
            overall_status = HealthStatus.UNKNOWN
        
        # Calculate metrics
        response_times = [result.response_time for result in latest_results if result.response_time > 0]
        avg_response_time = statistics.mean(response_times) if response_times else 0
        
        # Calculate uptime percentage (last 24 hours)
        uptime_percentage = self._calculate_uptime(service_name, hours=24)
        
        return ServiceHealth(
            service_name=service_name,
            overall_status=overall_status,
            checks=latest_results,
            last_updated=max(result.timestamp for result in latest_results),
            uptime_percentage=uptime_percentage,
            avg_response_time=avg_response_time
        )
    
    def _calculate_uptime(self, service_name: str, hours: int = 24) -> float:
        """Calculate uptime percentage for a service"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            since = datetime.now() - timedelta(hours=hours)
            
            cursor.execute('''
                SELECT COUNT(*) as total_checks,
                       SUM(CASE WHEN status IN ('healthy', 'degraded') THEN 1 ELSE 0 END) as healthy_checks
                FROM health_results 
                WHERE service_name = ? AND timestamp >= ?
            ''', (service_name, since.isoformat()))
            
            row = cursor.fetchone()
            conn.close()
            
            if row and row[0] > 0:
                return (row[1] / row[0]) * 100.0
            
            return 0.0
            
        except Exception as e:
            self.logger.error(f"Failed to calculate uptime for {service_name}: {e}")
            return 0.0
    
    def get_all_service_health(self) -> Dict[str, ServiceHealth]:
        """Get health status for all monitored services"""
        services = set(check.service_name for check in self.checks.values())
        return {service: self.get_service_health(service) for service in services}
    
    def add_health_callback(self, check_id: str, callback: Callable[[HealthCheckResult], None]):
        """Add callback for health check results"""
        if check_id not in self.callbacks:
            self.callbacks[check_id] = []
        self.callbacks[check_id].append(callback)
    
    def get_health_history(self, service_name: str = None, check_id: str = None, 
                          hours: int = 24) -> List[HealthCheckResult]:
        """Get health check history"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            since = datetime.now() - timedelta(hours=hours)
            
            query = "SELECT * FROM health_results WHERE timestamp >= ?"
            params = [since.isoformat()]
            
            if service_name:
                query += " AND service_name = ?"
                params.append(service_name)
            
            if check_id:
                query += " AND check_id = ?"
                params.append(check_id)
            
            query += " ORDER BY timestamp DESC LIMIT 1000"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()
            
            results = []
            for row in rows:
                result = HealthCheckResult(
                    check_id=row[1],
                    service_name=row[2],
                    status=HealthStatus(row[3]),
                    response_time=row[4],
                    message=row[5],
                    timestamp=datetime.fromisoformat(row[6]),
                    details=json.loads(row[7]) if row[7] else None,
                    error=row[8]
                )
                results.append(result)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to get health history: {e}")
            return []
    
    def start(self):
        """Start health monitoring"""
        self.running = True
        
        # Load existing checks from database
        self._load_checks_from_db()
        
        # Start monitoring threads
        for config in self.checks.values():
            if config.enabled:
                self._start_check_thread(config)
        
        self.logger.info(f"Health monitor started with {len(self.checks)} checks")
    
    def stop(self):
        """Stop health monitoring"""
        self.running = False
        
        # Stop all monitoring threads
        for check_id in list(self.check_threads.keys()):
            self._stop_check_thread(check_id)
        
        self.logger.info("Health monitor stopped")
    
    def _load_checks_from_db(self):
        """Load health checks from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT config FROM health_checks WHERE enabled = TRUE")
            rows = cursor.fetchall()
            conn.close()
            
            for row in rows:
                config_data = json.loads(row[0])
                config = HealthCheckConfig(
                    check_id=config_data["check_id"],
                    service_name=config_data["service_name"],
                    check_type=CheckType(config_data["check_type"]),
                    target=config_data["target"],
                    interval=config_data["interval"],
                    timeout=config_data["timeout"],
                    retries=config_data.get("retries", 3),
                    expected_codes=config_data.get("expected_codes"),
                    expected_response=config_data.get("expected_response"),
                    headers=config_data.get("headers"),
                    metadata=config_data.get("metadata"),
                    enabled=config_data.get("enabled", True)
                )
                
                self.checks[config.check_id] = config
                self.results[config.check_id] = []
                self.callbacks[config.check_id] = []
            
            self.logger.info(f"Loaded {len(self.checks)} health checks from database")
            
        except Exception as e:
            self.logger.error(f"Failed to load checks from database: {e}")


# Usage example
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    monitor = HealthMonitor()
    
    # Add HTTP health check
    http_check = HealthCheckConfig(
        check_id="api-service-http",
        service_name="api-service",
        check_type=CheckType.HTTP,
        target="http://localhost:8080/health",
        interval=30,
        timeout=10,
        expected_codes=[200],
        headers={"User-Agent": "HealthMonitor/1.0"}
    )
    
    # Add TCP health check
    tcp_check = HealthCheckConfig(
        check_id="db-service-tcp",
        service_name="database",
        check_type=CheckType.TCP,
        target="localhost:5432",
        interval=60,
        timeout=5
    )
    
    # Add health checks
    monitor.add_health_check(http_check)
    monitor.add_health_check(tcp_check)
    
    # Add callback for critical status
    def on_critical_status(result: HealthCheckResult):
        if result.status == HealthStatus.CRITICAL:
            print(f"CRITICAL: {result.service_name} - {result.message}")
    
    monitor.add_health_callback("api-service-http", on_critical_status)
    
    # Start monitoring
    monitor.start()
    
    try:
        # Run for 2 minutes
        time.sleep(120)
        
        # Check service health
        health = monitor.get_service_health("api-service")
        print(f"API Service Health: {health.overall_status.value}")
        print(f"Uptime: {health.uptime_percentage:.2f}%")
        print(f"Avg Response Time: {health.avg_response_time:.2f}ms")
        
    finally:
        monitor.stop()