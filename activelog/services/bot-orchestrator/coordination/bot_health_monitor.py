import asyncio
import logging
import time
import psutil
import aiohttp
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from collections import defaultdict, deque
import statistics
import threading

logger = logging.getLogger(__name__)

class HealthStatus(Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    FAILED = "failed"
    MAINTENANCE = "maintenance"

class AlertLevel(Enum):
    INFO = 1
    WARNING = 2
    CRITICAL = 3
    EMERGENCY = 4

@dataclass
class HealthMetric:
    name: str
    value: float
    timestamp: datetime
    unit: str = ""
    threshold_warning: Optional[float] = None
    threshold_critical: Optional[float] = None

@dataclass
class HealthAlert:
    id: str
    bot_id: str
    level: AlertLevel
    message: str
    metric_name: str
    current_value: float
    threshold_value: float
    created_at: datetime = field(default_factory=datetime.now)
    resolved_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None

class BotHealthChecker:
    def __init__(self, bot_id: str, check_interval: int = 30):
        self.bot_id = bot_id
        self.check_interval = check_interval
        self.health_status = HealthStatus.HEALTHY
        self.last_check = datetime.now()
        self.consecutive_failures = 0
        self.max_consecutive_failures = 3
        
        # Health metrics history
        self.metrics_history = defaultdict(lambda: deque(maxlen=100))
        
        # Configurable thresholds
        self.thresholds = {
            "cpu_usage": {"warning": 80.0, "critical": 95.0},
            "memory_usage": {"warning": 85.0, "critical": 95.0},
            "response_time": {"warning": 2.0, "critical": 5.0},
            "error_rate": {"warning": 5.0, "critical": 15.0},
            "token_usage_rate": {"warning": 80.0, "critical": 95.0},
            "concurrent_tasks": {"warning": 8, "critical": 12}
        }
        
        # Bot-specific configuration
        self.bot_config = {
            "api_endpoint": f"http://localhost:8000/bots/{bot_id}",
            "timeout": 10,
            "max_retries": 3
        }
        
        self.is_running = False
        self.health_check_task = None
    
    async def start_monitoring(self):
        """Start continuous health monitoring"""
        self.is_running = True
        self.health_check_task = asyncio.create_task(self._health_check_loop())
        logger.info(f"Started health monitoring for bot {self.bot_id}")
    
    async def stop_monitoring(self):
        """Stop health monitoring"""
        self.is_running = False
        if self.health_check_task:
            self.health_check_task.cancel()
            try:
                await self.health_check_task
            except asyncio.CancelledError:
                pass
        logger.info(f"Stopped health monitoring for bot {self.bot_id}")
    
    async def _health_check_loop(self):
        """Main health check loop"""
        while self.is_running:
            try:
                await self.perform_health_check()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error for bot {self.bot_id}: {e}")
                await asyncio.sleep(min(self.check_interval * 2, 300))
    
    async def perform_health_check(self) -> Dict[str, HealthMetric]:
        """Perform comprehensive health check"""
        self.last_check = datetime.now()
        metrics = {}
        
        try:
            # System metrics
            system_metrics = await self._collect_system_metrics()
            metrics.update(system_metrics)
            
            # Bot-specific metrics
            bot_metrics = await self._collect_bot_metrics()
            metrics.update(bot_metrics)
            
            # API health check
            api_metrics = await self._check_api_health()
            metrics.update(api_metrics)
            
            # Store metrics history
            for metric_name, metric in metrics.items():
                self.metrics_history[metric_name].append(metric)
            
            # Evaluate overall health status
            self._evaluate_health_status(metrics)
            
            # Reset consecutive failures on successful check
            self.consecutive_failures = 0
            
            return metrics
            
        except Exception as e:
            self.consecutive_failures += 1
            logger.error(f"Health check failed for bot {self.bot_id}: {e}")
            
            if self.consecutive_failures >= self.max_consecutive_failures:
                self.health_status = HealthStatus.FAILED
            
            raise e
    
    async def _collect_system_metrics(self) -> Dict[str, HealthMetric]:
        """Collect system-level metrics"""
        metrics = {}
        
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            metrics["cpu_usage"] = HealthMetric(
                name="cpu_usage",
                value=cpu_percent,
                timestamp=datetime.now(),
                unit="%",
                threshold_warning=self.thresholds["cpu_usage"]["warning"],
                threshold_critical=self.thresholds["cpu_usage"]["critical"]
            )
            
            # Memory usage
            memory = psutil.virtual_memory()
            metrics["memory_usage"] = HealthMetric(
                name="memory_usage",
                value=memory.percent,
                timestamp=datetime.now(),
                unit="%",
                threshold_warning=self.thresholds["memory_usage"]["warning"],
                threshold_critical=self.thresholds["memory_usage"]["critical"]
            )
            
            # Disk I/O
            disk_io = psutil.disk_io_counters()
            if disk_io:
                metrics["disk_read_rate"] = HealthMetric(
                    name="disk_read_rate",
                    value=disk_io.read_bytes / (1024 * 1024),  # MB
                    timestamp=datetime.now(),
                    unit="MB"
                )
                metrics["disk_write_rate"] = HealthMetric(
                    name="disk_write_rate",
                    value=disk_io.write_bytes / (1024 * 1024),  # MB
                    timestamp=datetime.now(),
                    unit="MB"
                )
            
            # Network I/O
            network_io = psutil.net_io_counters()
            if network_io:
                metrics["network_sent_rate"] = HealthMetric(
                    name="network_sent_rate",
                    value=network_io.bytes_sent / (1024 * 1024),  # MB
                    timestamp=datetime.now(),
                    unit="MB"
                )
                metrics["network_recv_rate"] = HealthMetric(
                    name="network_recv_rate",
                    value=network_io.bytes_recv / (1024 * 1024),  # MB
                    timestamp=datetime.now(),
                    unit="MB"
                )
            
        except Exception as e:
            logger.error(f"Failed to collect system metrics for {self.bot_id}: {e}")
        
        return metrics
    
    async def _collect_bot_metrics(self) -> Dict[str, HealthMetric]:
        """Collect bot-specific metrics from internal APIs"""
        metrics = {}
        
        try:
            # This would typically query the bot's internal metrics API
            # For now, we'll simulate some metrics
            
            # Task completion metrics (simulated)
            task_metrics = {
                "completed_tasks": 45,
                "failed_tasks": 2,
                "pending_tasks": 3,
                "concurrent_tasks": 5
            }
            
            error_rate = (task_metrics["failed_tasks"] / 
                         max(task_metrics["completed_tasks"] + task_metrics["failed_tasks"], 1)) * 100
            
            metrics["error_rate"] = HealthMetric(
                name="error_rate",
                value=error_rate,
                timestamp=datetime.now(),
                unit="%",
                threshold_warning=self.thresholds["error_rate"]["warning"],
                threshold_critical=self.thresholds["error_rate"]["critical"]
            )
            
            metrics["concurrent_tasks"] = HealthMetric(
                name="concurrent_tasks",
                value=task_metrics["concurrent_tasks"],
                timestamp=datetime.now(),
                unit="tasks",
                threshold_warning=self.thresholds["concurrent_tasks"]["warning"],
                threshold_critical=self.thresholds["concurrent_tasks"]["critical"]
            )
            
            # Token usage metrics (simulated)
            token_usage_rate = 65.0  # Percentage of quota used
            metrics["token_usage_rate"] = HealthMetric(
                name="token_usage_rate",
                value=token_usage_rate,
                timestamp=datetime.now(),
                unit="%",
                threshold_warning=self.thresholds["token_usage_rate"]["warning"],
                threshold_critical=self.thresholds["token_usage_rate"]["critical"]
            )
            
        except Exception as e:
            logger.error(f"Failed to collect bot metrics for {self.bot_id}: {e}")
        
        return metrics
    
    async def _check_api_health(self) -> Dict[str, HealthMetric]:
        """Check API endpoint health and response time"""
        metrics = {}
        
        try:
            start_time = time.time()
            timeout = aiohttp.ClientTimeout(total=self.bot_config["timeout"])
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(
                    f"{self.bot_config['api_endpoint']}/health",
                    headers={'Accept': 'application/json'}
                ) as response:
                    response_time = time.time() - start_time
                    
                    metrics["api_response_time"] = HealthMetric(
                        name="api_response_time",
                        value=response_time,
                        timestamp=datetime.now(),
                        unit="seconds",
                        threshold_warning=self.thresholds["response_time"]["warning"],
                        threshold_critical=self.thresholds["response_time"]["critical"]
                    )
                    
                    metrics["api_status_code"] = HealthMetric(
                        name="api_status_code",
                        value=response.status,
                        timestamp=datetime.now(),
                        unit="code"
                    )
                    
                    # Check if response is successful
                    if response.status == 200:
                        try:
                            data = await response.json()
                            metrics["api_health_score"] = HealthMetric(
                                name="api_health_score",
                                value=data.get("health_score", 100),
                                timestamp=datetime.now(),
                                unit="score"
                            )
                        except:
                            pass
            
        except asyncio.TimeoutError:
            metrics["api_response_time"] = HealthMetric(
                name="api_response_time",
                value=self.bot_config["timeout"],
                timestamp=datetime.now(),
                unit="seconds",
                threshold_warning=self.thresholds["response_time"]["warning"],
                threshold_critical=self.thresholds["response_time"]["critical"]
            )
            logger.warning(f"API health check timeout for bot {self.bot_id}")
            
        except Exception as e:
            logger.error(f"API health check failed for bot {self.bot_id}: {e}")
        
        return metrics
    
    def _evaluate_health_status(self, metrics: Dict[str, HealthMetric]):
        """Evaluate overall health status based on metrics"""
        critical_violations = 0
        warning_violations = 0
        
        for metric in metrics.values():
            if metric.threshold_critical and metric.value >= metric.threshold_critical:
                critical_violations += 1
            elif metric.threshold_warning and metric.value >= metric.threshold_warning:
                warning_violations += 1
        
        if critical_violations > 0:
            self.health_status = HealthStatus.CRITICAL
        elif warning_violations > 2:  # Multiple warnings
            self.health_status = HealthStatus.CRITICAL
        elif warning_violations > 0:
            self.health_status = HealthStatus.WARNING
        else:
            self.health_status = HealthStatus.HEALTHY
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get comprehensive health summary"""
        recent_metrics = {}
        for metric_name, history in self.metrics_history.items():
            if history:
                recent_metric = history[-1]
                recent_metrics[metric_name] = {
                    "current_value": recent_metric.value,
                    "unit": recent_metric.unit,
                    "threshold_warning": recent_metric.threshold_warning,
                    "threshold_critical": recent_metric.threshold_critical,
                    "timestamp": recent_metric.timestamp.isoformat()
                }
        
        return {
            "bot_id": self.bot_id,
            "health_status": self.health_status.value,
            "last_check": self.last_check.isoformat(),
            "consecutive_failures": self.consecutive_failures,
            "metrics": recent_metrics
        }
    
    def get_metric_trend(self, metric_name: str, duration_minutes: int = 30) -> Dict[str, Any]:
        """Get trend analysis for a specific metric"""
        if metric_name not in self.metrics_history:
            return {"error": f"Metric {metric_name} not found"}
        
        cutoff_time = datetime.now() - timedelta(minutes=duration_minutes)
        recent_data = [
            m for m in self.metrics_history[metric_name]
            if m.timestamp >= cutoff_time
        ]
        
        if not recent_data:
            return {"error": "No recent data available"}
        
        values = [m.value for m in recent_data]
        
        trend_analysis = {
            "metric_name": metric_name,
            "data_points": len(values),
            "current_value": values[-1] if values else 0,
            "min_value": min(values) if values else 0,
            "max_value": max(values) if values else 0,
            "average_value": statistics.mean(values) if values else 0,
            "median_value": statistics.median(values) if values else 0,
            "trend_direction": "stable"
        }
        
        # Calculate trend direction
        if len(values) >= 3:
            recent_third = values[-len(values)//3:]
            earlier_third = values[:len(values)//3]
            
            recent_avg = statistics.mean(recent_third)
            earlier_avg = statistics.mean(earlier_third)
            
            change_percent = ((recent_avg - earlier_avg) / max(earlier_avg, 0.01)) * 100
            
            if change_percent > 10:
                trend_analysis["trend_direction"] = "increasing"
            elif change_percent < -10:
                trend_analysis["trend_direction"] = "decreasing"
        
        return trend_analysis

class DeadlockDetector:
    def __init__(self):
        self.task_dependencies = defaultdict(set)  # task -> set of dependencies
        self.task_owners = {}  # task -> bot_id
        self.resource_locks = defaultdict(set)  # resource -> set of bot_ids holding locks
        self.resource_waiters = defaultdict(set)  # resource -> set of bot_ids waiting
        self.circular_wait_timeout = 300  # 5 minutes
        
        self.detected_deadlocks = []
        self.lock = threading.Lock()
    
    def add_task_dependency(self, task_id: str, depends_on: str, bot_id: str):
        """Add a task dependency"""
        with self.lock:
            self.task_dependencies[task_id].add(depends_on)
            self.task_owners[task_id] = bot_id
    
    def remove_task_dependency(self, task_id: str, depends_on: str):
        """Remove a task dependency"""
        with self.lock:
            self.task_dependencies[task_id].discard(depends_on)
            if not self.task_dependencies[task_id]:
                del self.task_dependencies[task_id]
                self.task_owners.pop(task_id, None)
    
    def acquire_resource_lock(self, resource_id: str, bot_id: str):
        """Record resource lock acquisition"""
        with self.lock:
            self.resource_locks[resource_id].add(bot_id)
            self.resource_waiters[resource_id].discard(bot_id)
    
    def wait_for_resource(self, resource_id: str, bot_id: str):
        """Record that a bot is waiting for a resource"""
        with self.lock:
            if bot_id not in self.resource_locks[resource_id]:
                self.resource_waiters[resource_id].add(bot_id)
    
    def release_resource_lock(self, resource_id: str, bot_id: str):
        """Record resource lock release"""
        with self.lock:
            self.resource_locks[resource_id].discard(bot_id)
            self.resource_waiters[resource_id].discard(bot_id)
    
    def detect_deadlocks(self) -> List[Dict[str, Any]]:
        """Detect various types of deadlocks"""
        with self.lock:
            deadlocks = []
            
            # Detect circular wait deadlocks
            circular_deadlocks = self._detect_circular_waits()
            deadlocks.extend(circular_deadlocks)
            
            # Detect resource deadlocks
            resource_deadlocks = self._detect_resource_deadlocks()
            deadlocks.extend(resource_deadlocks)
            
            # Detect task dependency cycles
            dependency_deadlocks = self._detect_dependency_cycles()
            deadlocks.extend(dependency_deadlocks)
            
            # Update detected deadlocks list
            self.detected_deadlocks = deadlocks
            
            return deadlocks
    
    def _detect_circular_waits(self) -> List[Dict[str, Any]]:
        """Detect circular wait conditions"""
        deadlocks = []
        
        # Build wait-for graph
        wait_graph = defaultdict(set)
        
        for resource_id, waiters in self.resource_waiters.items():
            holders = self.resource_locks[resource_id]
            for waiter in waiters:
                for holder in holders:
                    if waiter != holder:
                        wait_graph[waiter].add(holder)
        
        # Detect cycles in wait-for graph
        visited = set()
        rec_stack = set()
        
        def dfs(node, path):
            if node in rec_stack:
                # Found cycle
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                return [cycle]
            
            if node in visited:
                return []
            
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            cycles = []
            for neighbor in wait_graph[node]:
                cycles.extend(dfs(neighbor, path.copy()))
            
            rec_stack.remove(node)
            return cycles
        
        for bot_id in wait_graph:
            if bot_id not in visited:
                cycles = dfs(bot_id, [])
                for cycle in cycles:
                    deadlocks.append({
                        "type": "circular_wait",
                        "bots_involved": cycle,
                        "description": f"Circular wait detected: {' -> '.join(cycle)}",
                        "detected_at": datetime.now(),
                        "severity": "high"
                    })
        
        return deadlocks
    
    def _detect_resource_deadlocks(self) -> List[Dict[str, Any]]:
        """Detect resource-based deadlocks"""
        deadlocks = []
        
        # Look for situations where multiple bots are waiting for resources
        # held by each other
        for resource1, waiters1 in self.resource_waiters.items():
            if not waiters1:
                continue
            
            holders1 = self.resource_locks[resource1]
            
            for resource2, waiters2 in self.resource_waiters.items():
                if resource1 >= resource2 or not waiters2:  # Avoid duplicates
                    continue
                
                holders2 = self.resource_locks[resource2]
                
                # Check if any bot holding resource1 is waiting for resource2
                # and any bot holding resource2 is waiting for resource1
                deadlock_bots = set()
                
                for holder1 in holders1:
                    if holder1 in waiters2:
                        for holder2 in holders2:
                            if holder2 in waiters1:
                                deadlock_bots.add(holder1)
                                deadlock_bots.add(holder2)
                
                if len(deadlock_bots) >= 2:
                    deadlocks.append({
                        "type": "resource_deadlock",
                        "resources_involved": [resource1, resource2],
                        "bots_involved": list(deadlock_bots),
                        "description": f"Resource deadlock between {resource1} and {resource2}",
                        "detected_at": datetime.now(),
                        "severity": "high"
                    })
        
        return deadlocks
    
    def _detect_dependency_cycles(self) -> List[Dict[str, Any]]:
        """Detect cycles in task dependencies"""
        deadlocks = []
        
        # Build dependency graph by bot
        bot_dependencies = defaultdict(set)
        for task_id, deps in self.task_dependencies.items():
            bot_id = self.task_owners.get(task_id)
            if bot_id:
                for dep_task in deps:
                    dep_bot = self.task_owners.get(dep_task)
                    if dep_bot and dep_bot != bot_id:
                        bot_dependencies[bot_id].add(dep_bot)
        
        # Detect cycles
        visited = set()
        rec_stack = set()
        
        def find_cycle(node, path):
            if node in rec_stack:
                cycle_start = path.index(node)
                return path[cycle_start:] + [node]
            
            if node in visited:
                return None
            
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for neighbor in bot_dependencies[node]:
                cycle = find_cycle(neighbor, path.copy())
                if cycle:
                    return cycle
            
            rec_stack.remove(node)
            return None
        
        for bot_id in bot_dependencies:
            if bot_id not in visited:
                cycle = find_cycle(bot_id, [])
                if cycle:
                    deadlocks.append({
                        "type": "dependency_cycle",
                        "bots_involved": cycle[:-1],  # Remove duplicate last element
                        "description": f"Task dependency cycle: {' -> '.join(cycle)}",
                        "detected_at": datetime.now(),
                        "severity": "medium"
                    })
        
        return deadlocks
    
    def resolve_deadlock(self, deadlock: Dict[str, Any]) -> bool:
        """Attempt to resolve a detected deadlock"""
        try:
            if deadlock["type"] == "circular_wait":
                return self._resolve_circular_wait(deadlock)
            elif deadlock["type"] == "resource_deadlock":
                return self._resolve_resource_deadlock(deadlock)
            elif deadlock["type"] == "dependency_cycle":
                return self._resolve_dependency_cycle(deadlock)
            else:
                logger.warning(f"Unknown deadlock type: {deadlock['type']}")
                return False
        except Exception as e:
            logger.error(f"Failed to resolve deadlock: {e}")
            return False
    
    def _resolve_circular_wait(self, deadlock: Dict[str, Any]) -> bool:
        """Resolve circular wait by forcing one bot to release resources"""
        bots_involved = deadlock["bots_involved"]
        if not bots_involved:
            return False
        
        # Choose victim bot (lowest priority or most resources)
        victim_bot = bots_involved[0]  # Simple strategy
        
        logger.info(f"Resolving circular wait deadlock by preempting bot {victim_bot}")
        
        # Force release all resources held by victim bot
        with self.lock:
            for resource_id, holders in list(self.resource_locks.items()):
                if victim_bot in holders:
                    holders.discard(victim_bot)
                    logger.info(f"Released resource {resource_id} from bot {victim_bot}")
        
        return True
    
    def _resolve_resource_deadlock(self, deadlock: Dict[str, Any]) -> bool:
        """Resolve resource deadlock by resource preemption"""
        resources_involved = deadlock["resources_involved"]
        bots_involved = deadlock["bots_involved"]
        
        if not resources_involved or not bots_involved:
            return False
        
        # Release one of the resources from one of the bots
        resource_to_release = resources_involved[0]
        bot_to_preempt = bots_involved[0]
        
        logger.info(f"Resolving resource deadlock by releasing {resource_to_release} from {bot_to_preempt}")
        
        with self.lock:
            self.resource_locks[resource_to_release].discard(bot_to_preempt)
        
        return True
    
    def _resolve_dependency_cycle(self, deadlock: Dict[str, Any]) -> bool:
        """Resolve dependency cycle by breaking one dependency"""
        bots_involved = deadlock["bots_involved"]
        
        if len(bots_involved) < 2:
            return False
        
        # Find tasks that create the cycle and break one dependency
        tasks_to_break = []
        
        with self.lock:
            for task_id, deps in self.task_dependencies.items():
                task_bot = self.task_owners.get(task_id)
                if task_bot in bots_involved:
                    for dep_task in deps:
                        dep_bot = self.task_owners.get(dep_task)
                        if dep_bot in bots_involved and dep_bot != task_bot:
                            tasks_to_break.append((task_id, dep_task))
        
        if tasks_to_break:
            task_id, dep_task = tasks_to_break[0]
            self.task_dependencies[task_id].discard(dep_task)
            logger.info(f"Resolved dependency cycle by breaking dependency: {task_id} -> {dep_task}")
            return True
        
        return False

class BotHealthMonitor:
    def __init__(self):
        self.bot_checkers = {}
        self.deadlock_detector = DeadlockDetector()
        self.alerts = {}
        self.alert_handlers = []
        
        # Global monitoring settings
        self.monitoring_interval = 60  # seconds
        self.deadlock_check_interval = 120  # seconds
        
        self.is_running = False
        self.monitoring_task = None
        self.deadlock_task = None
    
    async def start(self):
        """Start the health monitoring system"""
        self.is_running = True
        
        # Start monitoring tasks
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        self.deadlock_task = asyncio.create_task(self._deadlock_detection_loop())
        
        logger.info("Bot Health Monitor started")
    
    async def stop(self):
        """Stop the health monitoring system"""
        self.is_running = False
        
        # Stop all bot checkers
        for checker in self.bot_checkers.values():
            await checker.stop_monitoring()
        
        # Cancel monitoring tasks
        if self.monitoring_task:
            self.monitoring_task.cancel()
        if self.deadlock_task:
            self.deadlock_task.cancel()
        
        await asyncio.gather(
            self.monitoring_task, self.deadlock_task, 
            return_exceptions=True
        )
        
        logger.info("Bot Health Monitor stopped")
    
    def register_bot(self, bot_id: str, check_interval: int = 30):
        """Register a bot for health monitoring"""
        if bot_id not in self.bot_checkers:
            checker = BotHealthChecker(bot_id, check_interval)
            self.bot_checkers[bot_id] = checker
            
            # Start monitoring if system is running
            if self.is_running:
                asyncio.create_task(checker.start_monitoring())
            
            logger.info(f"Registered bot {bot_id} for health monitoring")
    
    def unregister_bot(self, bot_id: str):
        """Unregister a bot from health monitoring"""
        if bot_id in self.bot_checkers:
            checker = self.bot_checkers[bot_id]
            asyncio.create_task(checker.stop_monitoring())
            del self.bot_checkers[bot_id]
            logger.info(f"Unregistered bot {bot_id} from health monitoring")
    
    def add_alert_handler(self, handler_func):
        """Add an alert handler function"""
        self.alert_handlers.append(handler_func)
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.is_running:
            try:
                # Check all registered bots
                for bot_id, checker in self.bot_checkers.items():
                    try:
                        await self._check_bot_and_generate_alerts(bot_id, checker)
                    except Exception as e:
                        logger.error(f"Error checking bot {bot_id}: {e}")
                
                await asyncio.sleep(self.monitoring_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(60)
    
    async def _deadlock_detection_loop(self):
        """Deadlock detection loop"""
        while self.is_running:
            try:
                deadlocks = self.deadlock_detector.detect_deadlocks()
                
                for deadlock in deadlocks:
                    alert = HealthAlert(
                        id=f"deadlock_{int(time.time() * 1000)}",
                        bot_id="system",
                        level=AlertLevel.CRITICAL,
                        message=deadlock["description"],
                        metric_name="deadlock_detection",
                        current_value=len(deadlock["bots_involved"]),
                        threshold_value=0
                    )
                    
                    await self._handle_alert(alert)
                    
                    # Attempt to resolve deadlock
                    if self.deadlock_detector.resolve_deadlock(deadlock):
                        logger.info(f"Successfully resolved deadlock: {deadlock['description']}")
                    else:
                        logger.error(f"Failed to resolve deadlock: {deadlock['description']}")
                
                await asyncio.sleep(self.deadlock_check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Deadlock detection loop error: {e}")
                await asyncio.sleep(120)
    
    async def _check_bot_and_generate_alerts(self, bot_id: str, checker: BotHealthChecker):
        """Check bot health and generate alerts"""
        try:
            metrics = await checker.perform_health_check()
            
            # Generate alerts for threshold violations
            for metric_name, metric in metrics.items():
                if metric.threshold_critical and metric.value >= metric.threshold_critical:
                    alert = HealthAlert(
                        id=f"{bot_id}_{metric_name}_critical_{int(time.time() * 1000)}",
                        bot_id=bot_id,
                        level=AlertLevel.CRITICAL,
                        message=f"Critical threshold exceeded for {metric_name}: {metric.value}{metric.unit}",
                        metric_name=metric_name,
                        current_value=metric.value,
                        threshold_value=metric.threshold_critical
                    )
                    await self._handle_alert(alert)
                
                elif metric.threshold_warning and metric.value >= metric.threshold_warning:
                    alert = HealthAlert(
                        id=f"{bot_id}_{metric_name}_warning_{int(time.time() * 1000)}",
                        bot_id=bot_id,
                        level=AlertLevel.WARNING,
                        message=f"Warning threshold exceeded for {metric_name}: {metric.value}{metric.unit}",
                        metric_name=metric_name,
                        current_value=metric.value,
                        threshold_value=metric.threshold_warning
                    )
                    await self._handle_alert(alert)
            
        except Exception as e:
            # Generate alert for health check failure
            alert = HealthAlert(
                id=f"{bot_id}_health_check_failed_{int(time.time() * 1000)}",
                bot_id=bot_id,
                level=AlertLevel.CRITICAL,
                message=f"Health check failed: {str(e)}",
                metric_name="health_check_status",
                current_value=0,
                threshold_value=1
            )
            await self._handle_alert(alert)
    
    async def _handle_alert(self, alert: HealthAlert):
        """Handle a generated alert"""
        # Store alert
        self.alerts[alert.id] = alert
        
        # Call all alert handlers
        for handler in self.alert_handlers:
            try:
                await handler(alert)
            except Exception as e:
                logger.error(f"Alert handler failed: {e}")
        
        logger.info(f"Generated alert {alert.level.name}: {alert.message}")
    
    def get_system_health_overview(self) -> Dict[str, Any]:
        """Get comprehensive system health overview"""
        overview = {
            "total_bots": len(self.bot_checkers),
            "healthy_bots": 0,
            "warning_bots": 0,
            "critical_bots": 0,
            "failed_bots": 0,
            "active_alerts": len([a for a in self.alerts.values() if not a.resolved_at]),
            "recent_deadlocks": len(self.deadlock_detector.detected_deadlocks),
            "bot_summaries": {}
        }
        
        for bot_id, checker in self.bot_checkers.items():
            summary = checker.get_health_summary()
            overview["bot_summaries"][bot_id] = summary
            
            status = summary["health_status"]
            if status == "healthy":
                overview["healthy_bots"] += 1
            elif status == "warning":
                overview["warning_bots"] += 1
            elif status == "critical":
                overview["critical_bots"] += 1
            elif status == "failed":
                overview["failed_bots"] += 1
        
        return overview
    
    def get_bot_health(self, bot_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed health information for a specific bot"""
        if bot_id not in self.bot_checkers:
            return None
        
        checker = self.bot_checkers[bot_id]
        summary = checker.get_health_summary()
        
        # Add recent alerts for this bot
        bot_alerts = [
            {
                "id": alert.id,
                "level": alert.level.name,
                "message": alert.message,
                "created_at": alert.created_at.isoformat(),
                "resolved": alert.resolved_at is not None
            }
            for alert in self.alerts.values()
            if alert.bot_id == bot_id and 
               (datetime.now() - alert.created_at).total_seconds() < 3600  # Last hour
        ]
        
        summary["recent_alerts"] = bot_alerts
        return summary
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert"""
        if alert_id in self.alerts:
            self.alerts[alert_id].acknowledged_at = datetime.now()
            return True
        return False
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Mark an alert as resolved"""
        if alert_id in self.alerts:
            self.alerts[alert_id].resolved_at = datetime.now()
            return True
        return False