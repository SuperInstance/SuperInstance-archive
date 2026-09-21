"""
Resource Usage Tracker
Real-time monitoring and tracking of compute resources for billing
"""

import asyncio
import json
import time
import logging
import psutil
import docker
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import redis
import aiohttp
from collections import defaultdict, deque
import threading
import subprocess

class ResourceType(Enum):
    CPU = "cpu"
    MEMORY = "memory"
    STORAGE = "storage"
    NETWORK = "network"
    GPU = "gpu"
    CONTAINERS = "containers"
    CUSTOM = "custom"

class MonitoringMode(Enum):
    SYSTEM_WIDE = "system_wide"
    PER_SESSION = "per_session"
    PER_USER = "per_user"
    PER_SERVICE = "per_service"

@dataclass
class ResourceMetric:
    """Individual resource measurement"""
    resource_type: ResourceType
    value: float
    unit: str
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class UsageSnapshot:
    """Snapshot of resource usage at a point in time"""
    session_id: str
    user_id: str
    timestamp: datetime
    metrics: Dict[ResourceType, ResourceMetric]
    system_info: Dict[str, Any] = field(default_factory=dict)

@dataclass
class MonitoringTarget:
    """Target for resource monitoring"""
    target_id: str
    target_type: str  # session, user, container, process
    monitoring_mode: MonitoringMode
    resource_types: List[ResourceType]
    sampling_interval: float  # seconds
    retention_period: int  # seconds
    custom_collectors: List[Callable] = field(default_factory=list)

class ResourceUsageTracker:
    """
    Advanced resource usage tracker that monitors compute resources
    in real-time for precise billing calculations
    """
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis_client = redis_client
        self.logger = logging.getLogger(__name__)
        
        # Monitoring state
        self.monitoring_active = False
        self.monitoring_targets: Dict[str, MonitoringTarget] = {}
        
        # Usage data storage
        self.usage_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.current_snapshots: Dict[str, UsageSnapshot] = {}
        
        # Resource collectors
        self.resource_collectors: Dict[ResourceType, Callable] = {
            ResourceType.CPU: self._collect_cpu_usage,
            ResourceType.MEMORY: self._collect_memory_usage,
            ResourceType.STORAGE: self._collect_storage_usage,
            ResourceType.NETWORK: self._collect_network_usage,
            ResourceType.GPU: self._collect_gpu_usage,
            ResourceType.CONTAINERS: self._collect_container_usage
        }
        
        # Docker client
        try:
            self.docker_client = docker.from_env()
        except Exception as e:
            self.logger.warning(f"Docker client not available: {e}")
            self.docker_client = None
        
        # System monitoring
        self.system_baseline = self._establish_system_baseline()
        
        # Performance metrics
        self.metrics = {
            "snapshots_collected": 0,
            "collection_errors": 0,
            "average_collection_time": 0.0,
            "data_points_stored": 0
        }

    def _establish_system_baseline(self) -> Dict[str, Any]:
        """Establish baseline system resource usage"""
        try:
            return {
                "cpu_count": psutil.cpu_count(),
                "memory_total": psutil.virtual_memory().total,
                "disk_usage": {
                    path: psutil.disk_usage(path).total
                    for path in ['/'] if psutil.disk_usage(path)
                },
                "network_interfaces": list(psutil.net_io_counters(pernic=True).keys()),
                "boot_time": psutil.boot_time(),
                "established_at": time.time()
            }
        except Exception as e:
            self.logger.error(f"Failed to establish system baseline: {e}")
            return {}

    async def add_monitoring_target(
        self,
        target_id: str,
        target_type: str,
        resource_types: List[ResourceType],
        sampling_interval: float = 30.0,
        retention_period: int = 86400,  # 24 hours
        monitoring_mode: MonitoringMode = MonitoringMode.PER_SESSION
    ):
        """Add a target for resource monitoring"""
        try:
            target = MonitoringTarget(
                target_id=target_id,
                target_type=target_type,
                monitoring_mode=monitoring_mode,
                resource_types=resource_types,
                sampling_interval=sampling_interval,
                retention_period=retention_period
            )
            
            self.monitoring_targets[target_id] = target
            
            # Initialize usage history for target
            self.usage_history[target_id] = deque(maxlen=int(retention_period / sampling_interval))
            
            self.logger.info(f"Added monitoring target: {target_id} ({target_type})")
            
        except Exception as e:
            self.logger.error(f"Failed to add monitoring target {target_id}: {e}")
            raise

    async def remove_monitoring_target(self, target_id: str):
        """Remove monitoring target"""
        try:
            if target_id in self.monitoring_targets:
                del self.monitoring_targets[target_id]
                
                # Clean up history
                if target_id in self.usage_history:
                    del self.usage_history[target_id]
                
                if target_id in self.current_snapshots:
                    del self.current_snapshots[target_id]
                
                self.logger.info(f"Removed monitoring target: {target_id}")
                
        except Exception as e:
            self.logger.error(f"Failed to remove monitoring target {target_id}: {e}")

    async def start_continuous_monitoring(self):
        """Start continuous monitoring of all targets"""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.logger.info("Starting continuous resource monitoring")
        
        try:
            # Start monitoring tasks for each target
            monitoring_tasks = []
            
            for target_id, target in self.monitoring_targets.items():
                task = asyncio.create_task(self._monitor_target(target))
                monitoring_tasks.append(task)
            
            # Start cleanup task
            cleanup_task = asyncio.create_task(self._cleanup_old_data())
            monitoring_tasks.append(cleanup_task)
            
            # Start storage task
            storage_task = asyncio.create_task(self._store_usage_data())
            monitoring_tasks.append(storage_task)
            
            # Wait for all tasks
            await asyncio.gather(*monitoring_tasks, return_exceptions=True)
            
        except asyncio.CancelledError:
            self.logger.info("Continuous monitoring cancelled")
        except Exception as e:
            self.logger.error(f"Continuous monitoring error: {e}")
        finally:
            self.monitoring_active = False

    async def _monitor_target(self, target: MonitoringTarget):
        """Monitor a specific target continuously"""
        self.logger.info(f"Starting monitoring for target {target.target_id}")
        
        try:
            while self.monitoring_active:
                start_time = time.time()
                
                try:
                    # Collect usage snapshot
                    snapshot = await self._collect_usage_snapshot(target)
                    
                    if snapshot:
                        # Store snapshot
                        self.usage_history[target.target_id].append(snapshot)
                        self.current_snapshots[target.target_id] = snapshot
                        
                        # Store in Redis if available
                        if self.redis_client:
                            await self._store_snapshot_in_redis(snapshot)
                        
                        self.metrics["snapshots_collected"] += 1
                        
                        # Calculate collection time
                        collection_time = time.time() - start_time
                        self.metrics["average_collection_time"] = (
                            self.metrics["average_collection_time"] * 0.9 + collection_time * 0.1
                        )
                    
                except Exception as e:
                    self.logger.error(f"Error collecting snapshot for {target.target_id}: {e}")
                    self.metrics["collection_errors"] += 1
                
                # Wait for next collection
                await asyncio.sleep(target.sampling_interval)
                
        except asyncio.CancelledError:
            self.logger.info(f"Monitoring cancelled for target {target.target_id}")
        except Exception as e:
            self.logger.error(f"Monitoring error for target {target.target_id}: {e}")

    async def _collect_usage_snapshot(self, target: MonitoringTarget) -> Optional[UsageSnapshot]:
        """Collect resource usage snapshot for target"""
        try:
            timestamp = datetime.now(timezone.utc)
            metrics = {}
            
            # Collect metrics for each resource type
            for resource_type in target.resource_types:
                if resource_type in self.resource_collectors:
                    try:
                        metric = await self.resource_collectors[resource_type](target)
                        if metric:
                            metrics[resource_type] = metric
                    except Exception as e:
                        self.logger.warning(f"Failed to collect {resource_type} for {target.target_id}: {e}")
            
            # Collect custom metrics
            for collector in target.custom_collectors:
                try:
                    custom_metrics = await collector(target)
                    if custom_metrics:
                        metrics.update(custom_metrics)
                except Exception as e:
                    self.logger.warning(f"Custom collector failed for {target.target_id}: {e}")
            
            if not metrics:
                return None
            
            # Extract user_id from target (assume format includes user info)
            user_id = target.target_id.split('_')[1] if '_' in target.target_id else "unknown"
            
            snapshot = UsageSnapshot(
                session_id=target.target_id,
                user_id=user_id,
                timestamp=timestamp,
                metrics=metrics,
                system_info={
                    "hostname": psutil.Process().name(),
                    "load_average": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None,
                    "cpu_percent": psutil.cpu_percent(),
                    "memory_percent": psutil.virtual_memory().percent
                }
            )
            
            return snapshot
            
        except Exception as e:
            self.logger.error(f"Failed to collect usage snapshot for {target.target_id}: {e}")
            return None

    async def _collect_cpu_usage(self, target: MonitoringTarget) -> Optional[ResourceMetric]:
        """Collect CPU usage metrics"""
        try:
            # Get system-wide CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            
            # Calculate CPU seconds based on usage and time
            cpu_seconds = (cpu_percent / 100.0) * cpu_count * target.sampling_interval
            
            if target.target_type == "container" and self.docker_client:
                # Get container-specific CPU usage
                try:
                    container = self.docker_client.containers.get(target.target_id)
                    stats = container.stats(stream=False)
                    
                    # Calculate container CPU usage
                    cpu_usage = stats['cpu_stats']['cpu_usage']['total_usage']
                    system_cpu_usage = stats['cpu_stats']['system_cpu_usage']
                    
                    # Calculate CPU percentage for container
                    if 'precpu_stats' in stats:
                        cpu_delta = cpu_usage - stats['precpu_stats']['cpu_usage']['total_usage']
                        system_delta = system_cpu_usage - stats['precpu_stats']['system_cpu_usage']
                        
                        if system_delta > 0:
                            container_cpu_percent = (cpu_delta / system_delta) * len(stats['cpu_stats']['cpu_usage']['percpu_usage']) * 100.0
                            cpu_seconds = (container_cpu_percent / 100.0) * target.sampling_interval
                
                except Exception as e:
                    self.logger.debug(f"Container CPU collection failed: {e}")
            
            return ResourceMetric(
                resource_type=ResourceType.CPU,
                value=cpu_seconds,
                unit="cpu_seconds",
                timestamp=datetime.now(timezone.utc),
                metadata={
                    "cpu_count": cpu_count,
                    "cpu_percent": cpu_percent,
                    "sampling_interval": target.sampling_interval
                }
            )
            
        except Exception as e:
            self.logger.error(f"CPU collection failed: {e}")
            return None

    async def _collect_memory_usage(self, target: MonitoringTarget) -> Optional[ResourceMetric]:
        """Collect memory usage metrics"""
        try:
            # Get system memory info
            memory = psutil.virtual_memory()
            memory_used_mb = memory.used / (1024 * 1024)
            
            if target.target_type == "container" and self.docker_client:
                # Get container-specific memory usage
                try:
                    container = self.docker_client.containers.get(target.target_id)
                    stats = container.stats(stream=False)
                    
                    memory_usage = stats['memory_stats']['usage']
                    memory_used_mb = memory_usage / (1024 * 1024)
                
                except Exception as e:
                    self.logger.debug(f"Container memory collection failed: {e}")
            
            # Calculate memory-seconds (MB * seconds)
            memory_mb_seconds = memory_used_mb * target.sampling_interval
            
            return ResourceMetric(
                resource_type=ResourceType.MEMORY,
                value=memory_mb_seconds,
                unit="mb_seconds",
                timestamp=datetime.now(timezone.utc),
                metadata={
                    "memory_used_mb": memory_used_mb,
                    "memory_total_mb": memory.total / (1024 * 1024),
                    "memory_percent": memory.percent,
                    "sampling_interval": target.sampling_interval
                }
            )
            
        except Exception as e:
            self.logger.error(f"Memory collection failed: {e}")
            return None

    async def _collect_storage_usage(self, target: MonitoringTarget) -> Optional[ResourceMetric]:
        """Collect storage usage metrics"""
        try:
            # Get disk usage for root partition
            disk_usage = psutil.disk_usage('/')
            storage_used_gb = disk_usage.used / (1024 ** 3)
            
            if target.target_type == "container" and self.docker_client:
                # Get container-specific storage usage
                try:
                    container = self.docker_client.containers.get(target.target_id)
                    
                    # Get container filesystem size
                    exec_result = container.exec_run("df -BG /")
                    if exec_result.exit_code == 0:
                        output = exec_result.output.decode()
                        lines = output.strip().split('\n')
                        if len(lines) > 1:
                            fields = lines[1].split()
                            if len(fields) >= 3:
                                used_str = fields[2].replace('G', '')
                                storage_used_gb = float(used_str)
                
                except Exception as e:
                    self.logger.debug(f"Container storage collection failed: {e}")
            
            # Calculate storage-seconds (GB * seconds)
            storage_gb_seconds = storage_used_gb * target.sampling_interval
            
            return ResourceMetric(
                resource_type=ResourceType.STORAGE,
                value=storage_gb_seconds,
                unit="gb_seconds",
                timestamp=datetime.now(timezone.utc),
                metadata={
                    "storage_used_gb": storage_used_gb,
                    "storage_total_gb": disk_usage.total / (1024 ** 3),
                    "storage_percent": (disk_usage.used / disk_usage.total) * 100,
                    "sampling_interval": target.sampling_interval
                }
            )
            
        except Exception as e:
            self.logger.error(f"Storage collection failed: {e}")
            return None

    async def _collect_network_usage(self, target: MonitoringTarget) -> Optional[ResourceMetric]:
        """Collect network usage metrics"""
        try:
            # Get network I/O counters
            network_io = psutil.net_io_counters()
            
            # Calculate network usage since last measurement
            network_gb = 0.0
            
            if hasattr(self, '_last_network_bytes'):
                bytes_sent_delta = network_io.bytes_sent - self._last_network_bytes['sent']
                bytes_recv_delta = network_io.bytes_recv - self._last_network_bytes['recv']
                total_bytes_delta = bytes_sent_delta + bytes_recv_delta
                network_gb = total_bytes_delta / (1024 ** 3)
            
            # Store current values for next calculation
            self._last_network_bytes = {
                'sent': network_io.bytes_sent,
                'recv': network_io.bytes_recv
            }
            
            if target.target_type == "container" and self.docker_client:
                # Get container-specific network usage
                try:
                    container = self.docker_client.containers.get(target.target_id)
                    stats = container.stats(stream=False)
                    
                    if 'networks' in stats:
                        total_bytes = 0
                        for interface, net_stats in stats['networks'].items():
                            total_bytes += net_stats['rx_bytes'] + net_stats['tx_bytes']
                        
                        # Calculate network usage for this interval
                        if hasattr(self, f'_last_container_bytes_{target.target_id}'):
                            last_bytes = getattr(self, f'_last_container_bytes_{target.target_id}')
                            bytes_delta = total_bytes - last_bytes
                            network_gb = max(0, bytes_delta) / (1024 ** 3)
                        
                        setattr(self, f'_last_container_bytes_{target.target_id}', total_bytes)
                
                except Exception as e:
                    self.logger.debug(f"Container network collection failed: {e}")
            
            return ResourceMetric(
                resource_type=ResourceType.NETWORK,
                value=network_gb,
                unit="gb",
                timestamp=datetime.now(timezone.utc),
                metadata={
                    "bytes_sent": network_io.bytes_sent,
                    "bytes_recv": network_io.bytes_recv,
                    "packets_sent": network_io.packets_sent,
                    "packets_recv": network_io.packets_recv,
                    "sampling_interval": target.sampling_interval
                }
            )
            
        except Exception as e:
            self.logger.error(f"Network collection failed: {e}")
            return None

    async def _collect_gpu_usage(self, target: MonitoringTarget) -> Optional[ResourceMetric]:
        """Collect GPU usage metrics"""
        try:
            # Check if nvidia-smi is available
            result = subprocess.run([
                'nvidia-smi', '--query-gpu=utilization.gpu,memory.used', 
                '--format=csv,noheader,nounits'
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                total_gpu_seconds = 0.0
                
                for line in lines:
                    if line.strip():
                        parts = line.split(',')
                        if len(parts) >= 2:
                            gpu_utilization = float(parts[0].strip())
                            # Calculate GPU seconds based on utilization
                            gpu_seconds = (gpu_utilization / 100.0) * target.sampling_interval
                            total_gpu_seconds += gpu_seconds
                
                return ResourceMetric(
                    resource_type=ResourceType.GPU,
                    value=total_gpu_seconds,
                    unit="gpu_seconds",
                    timestamp=datetime.now(timezone.utc),
                    metadata={
                        "gpu_count": len(lines),
                        "sampling_interval": target.sampling_interval
                    }
                )
            
        except Exception as e:
            self.logger.debug(f"GPU collection failed (normal if no GPU): {e}")
        
        return None

    async def _collect_container_usage(self, target: MonitoringTarget) -> Optional[ResourceMetric]:
        """Collect container-specific usage metrics"""
        try:
            if not self.docker_client:
                return None
            
            containers = self.docker_client.containers.list()
            container_count = len(containers)
            
            # Count running containers
            running_containers = len([c for c in containers if c.status == 'running'])
            
            return ResourceMetric(
                resource_type=ResourceType.CONTAINERS,
                value=float(container_count),
                unit="containers",
                timestamp=datetime.now(timezone.utc),
                metadata={
                    "total_containers": container_count,
                    "running_containers": running_containers,
                    "sampling_interval": target.sampling_interval
                }
            )
            
        except Exception as e:
            self.logger.error(f"Container collection failed: {e}")
            return None

    async def record_usage(self, usage_data: Dict[str, Any]):
        """Record custom usage data"""
        try:
            session_id = usage_data.get("session_id")
            if not session_id:
                raise ValueError("session_id required")
            
            timestamp = datetime.now(timezone.utc)
            
            # Create metrics from usage data
            metrics = {}
            
            if "cpu_seconds" in usage_data:
                metrics[ResourceType.CPU] = ResourceMetric(
                    resource_type=ResourceType.CPU,
                    value=float(usage_data["cpu_seconds"]),
                    unit="cpu_seconds",
                    timestamp=timestamp
                )
            
            if "memory_mb_seconds" in usage_data:
                metrics[ResourceType.MEMORY] = ResourceMetric(
                    resource_type=ResourceType.MEMORY,
                    value=float(usage_data["memory_mb_seconds"]),
                    unit="mb_seconds",
                    timestamp=timestamp
                )
            
            if "storage_gb_seconds" in usage_data:
                metrics[ResourceType.STORAGE] = ResourceMetric(
                    resource_type=ResourceType.STORAGE,
                    value=float(usage_data["storage_gb_seconds"]),
                    unit="gb_seconds",
                    timestamp=timestamp
                )
            
            if "network_gb" in usage_data:
                metrics[ResourceType.NETWORK] = ResourceMetric(
                    resource_type=ResourceType.NETWORK,
                    value=float(usage_data["network_gb"]),
                    unit="gb",
                    timestamp=timestamp
                )
            
            if "gpu_seconds" in usage_data:
                metrics[ResourceType.GPU] = ResourceMetric(
                    resource_type=ResourceType.GPU,
                    value=float(usage_data["gpu_seconds"]),
                    unit="gpu_seconds",
                    timestamp=timestamp
                )
            
            if "requests_count" in usage_data:
                metrics[ResourceType.CUSTOM] = ResourceMetric(
                    resource_type=ResourceType.CUSTOM,
                    value=float(usage_data["requests_count"]),
                    unit="requests",
                    timestamp=timestamp,
                    metadata={"metric_name": "requests_count"}
                )
            
            # Create usage snapshot
            user_id = usage_data.get("user_id", "unknown")
            snapshot = UsageSnapshot(
                session_id=session_id,
                user_id=user_id,
                timestamp=timestamp,
                metrics=metrics
            )
            
            # Store snapshot
            self.usage_history[session_id].append(snapshot)
            self.current_snapshots[session_id] = snapshot
            
            # Store in Redis if available
            if self.redis_client:
                await self._store_snapshot_in_redis(snapshot)
            
            self.metrics["data_points_stored"] += len(metrics)
            
        except Exception as e:
            self.logger.error(f"Failed to record usage: {e}")
            raise

    async def get_session_usage(self, session_id: str) -> Dict[str, Any]:
        """Get usage statistics for a session"""
        try:
            if session_id not in self.usage_history:
                return {"error": "Session not found"}
            
            history = list(self.usage_history[session_id])
            
            if not history:
                return {"session_id": session_id, "usage": {}, "snapshots": 0}
            
            # Aggregate usage across all snapshots
            aggregated_usage = defaultdict(float)
            
            for snapshot in history:
                for resource_type, metric in snapshot.metrics.items():
                    aggregated_usage[f"{resource_type.value}_{metric.unit}"] += metric.value
            
            # Calculate time range
            start_time = history[0].timestamp
            end_time = history[-1].timestamp
            duration = (end_time - start_time).total_seconds()
            
            return {
                "session_id": session_id,
                "user_id": history[0].user_id,
                "time_range": {
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat(),
                    "duration_seconds": duration
                },
                "aggregated_usage": dict(aggregated_usage),
                "snapshots_count": len(history),
                "latest_snapshot": history[-1].timestamp.isoformat() if history else None
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get session usage for {session_id}: {e}")
            return {"error": str(e)}

    async def get_user_usage_summary(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Get usage summary for user over specified period"""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=days)
            
            # Find all sessions for user
            user_sessions = []
            total_usage = defaultdict(float)
            
            for session_id, history in self.usage_history.items():
                for snapshot in history:
                    if snapshot.user_id == user_id and snapshot.timestamp >= cutoff_time:
                        if session_id not in [s["session_id"] for s in user_sessions]:
                            user_sessions.append({
                                "session_id": session_id,
                                "start_time": snapshot.timestamp.isoformat(),
                                "usage": defaultdict(float)
                            })
                        
                        # Aggregate usage
                        for resource_type, metric in snapshot.metrics.items():
                            key = f"{resource_type.value}_{metric.unit}"
                            total_usage[key] += metric.value
                            
                            # Add to session usage
                            for session in user_sessions:
                                if session["session_id"] == session_id:
                                    session["usage"][key] += metric.value
                                    break
            
            return {
                "user_id": user_id,
                "period_days": days,
                "total_usage": dict(total_usage),
                "sessions": user_sessions,
                "summary": {
                    "total_sessions": len(user_sessions),
                    "total_cpu_hours": total_usage.get("cpu_cpu_seconds", 0) / 3600,
                    "total_memory_gb_hours": total_usage.get("memory_mb_seconds", 0) / (1024 * 3600),
                    "total_storage_gb_hours": total_usage.get("storage_gb_seconds", 0) / 3600,
                    "total_network_gb": total_usage.get("network_gb", 0),
                    "total_requests": total_usage.get("custom_requests", 0)
                }
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get user usage summary for {user_id}: {e}")
            return {"error": str(e)}

    async def _store_snapshot_in_redis(self, snapshot: UsageSnapshot):
        """Store usage snapshot in Redis"""
        try:
            if not self.redis_client:
                return
            
            # Store snapshot data
            snapshot_data = {
                "session_id": snapshot.session_id,
                "user_id": snapshot.user_id,
                "timestamp": snapshot.timestamp.isoformat(),
                "metrics": json.dumps({
                    rt.value: {
                        "value": metric.value,
                        "unit": metric.unit,
                        "metadata": metric.metadata
                    }
                    for rt, metric in snapshot.metrics.items()
                })
            }
            
            # Store in sorted set with timestamp as score
            key = f"usage_snapshots:{snapshot.session_id}"
            await self.redis_client.zadd(
                key,
                {json.dumps(snapshot_data): snapshot.timestamp.timestamp()}
            )
            
            # Set expiration (7 days)
            await self.redis_client.expire(key, 604800)
            
            # Store user index
            user_key = f"user_sessions:{snapshot.user_id}"
            await self.redis_client.sadd(user_key, snapshot.session_id)
            await self.redis_client.expire(user_key, 2592000)  # 30 days
            
        except Exception as e:
            self.logger.error(f"Failed to store snapshot in Redis: {e}")

    async def _cleanup_old_data(self):
        """Clean up old usage data periodically"""
        try:
            while self.monitoring_active:
                current_time = datetime.now(timezone.utc)
                cleaned_count = 0
                
                # Clean up in-memory data
                for session_id, history in list(self.usage_history.items()):
                    # Remove old snapshots (older than retention period)
                    cutoff_time = current_time - timedelta(seconds=86400)  # 24 hours default
                    
                    original_length = len(history)
                    
                    # Filter out old snapshots
                    while history and history[0].timestamp < cutoff_time:
                        history.popleft()
                        cleaned_count += 1
                    
                    # Remove empty sessions
                    if not history:
                        del self.usage_history[session_id]
                        if session_id in self.current_snapshots:
                            del self.current_snapshots[session_id]
                
                # Clean up Redis data
                if self.redis_client and cleaned_count > 0:
                    try:
                        # Clean old snapshots from Redis
                        cutoff_timestamp = (current_time - timedelta(days=7)).timestamp()
                        
                        # Find all usage snapshot keys
                        cursor = 0
                        while True:
                            cursor, keys = await self.redis_client.scan(
                                cursor=cursor,
                                match="usage_snapshots:*",
                                count=100
                            )
                            
                            for key in keys:
                                # Remove old entries from sorted set
                                await self.redis_client.zremrangebyscore(key, 0, cutoff_timestamp)
                            
                            if cursor == 0:
                                break
                    
                    except Exception as e:
                        self.logger.error(f"Redis cleanup failed: {e}")
                
                if cleaned_count > 0:
                    self.logger.info(f"Cleaned up {cleaned_count} old usage records")
                
                # Wait 1 hour before next cleanup
                await asyncio.sleep(3600)
                
        except asyncio.CancelledError:
            self.logger.info("Usage data cleanup cancelled")
        except Exception as e:
            self.logger.error(f"Usage data cleanup error: {e}")

    async def _store_usage_data(self):
        """Periodically store usage data to persistent storage"""
        try:
            while self.monitoring_active:
                # Store current snapshots to Redis
                for session_id, snapshot in list(self.current_snapshots.items()):
                    if self.redis_client:
                        await self._store_snapshot_in_redis(snapshot)
                
                # Wait 5 minutes before next storage
                await asyncio.sleep(300)
                
        except asyncio.CancelledError:
            self.logger.info("Usage data storage cancelled")
        except Exception as e:
            self.logger.error(f"Usage data storage error: {e}")

    async def optimize_storage(self) -> Dict[str, Any]:
        """Optimize storage usage and clean up redundant data"""
        try:
            optimized_sessions = 0
            reclaimed_space = 0
            
            # Optimize in-memory storage
            for session_id, history in list(self.usage_history.items()):
                original_size = len(history)
                
                # Remove duplicate snapshots
                unique_snapshots = []
                last_timestamp = None
                
                for snapshot in history:
                    # Only keep snapshots that are significantly different
                    if (last_timestamp is None or 
                        (snapshot.timestamp - last_timestamp).total_seconds() >= 30):
                        unique_snapshots.append(snapshot)
                        last_timestamp = snapshot.timestamp
                
                if len(unique_snapshots) < original_size:
                    self.usage_history[session_id] = deque(unique_snapshots, maxlen=1000)
                    reclaimed_space += original_size - len(unique_snapshots)
                    optimized_sessions += 1
            
            # Optimize Redis storage
            if self.redis_client:
                # Compress old data
                try:
                    cursor = 0
                    redis_optimized = 0
                    
                    while True:
                        cursor, keys = await self.redis_client.scan(
                            cursor=cursor,
                            match="usage_snapshots:*",
                            count=50
                        )
                        
                        for key in keys:
                            # Get all entries
                            entries = await self.redis_client.zrange(key, 0, -1, withscores=True)
                            
                            if len(entries) > 100:  # Optimize if many entries
                                # Keep only every 5th entry for old data
                                cutoff_time = time.time() - 3600  # 1 hour ago
                                
                                optimized_entries = []
                                count = 0
                                
                                for entry, score in entries:
                                    if score > cutoff_time or count % 5 == 0:
                                        optimized_entries.append({entry: score})
                                    count += 1
                                
                                if len(optimized_entries) < len(entries):
                                    # Replace with optimized data
                                    await self.redis_client.delete(key)
                                    if optimized_entries:
                                        for entry_dict in optimized_entries:
                                            await self.redis_client.zadd(key, entry_dict)
                                    
                                    redis_optimized += 1
                        
                        if cursor == 0:
                            break
                    
                except Exception as e:
                    self.logger.error(f"Redis optimization failed: {e}")
            
            return {
                "optimized_sessions": optimized_sessions,
                "reclaimed_space": reclaimed_space,
                "redis_keys_optimized": redis_optimized,
                "optimized_at": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Storage optimization failed: {e}")
            return {"error": str(e)}

    async def get_status(self) -> Dict[str, Any]:
        """Get usage tracker status"""
        return {
            "monitoring_active": self.monitoring_active,
            "monitoring_targets": len(self.monitoring_targets),
            "active_sessions": len(self.current_snapshots),
            "total_snapshots": sum(len(history) for history in self.usage_history.values()),
            "metrics": self.metrics,
            "docker_available": self.docker_client is not None,
            "redis_connected": self.redis_client is not None,
            "system_baseline": self.system_baseline
        }

    async def shutdown(self):
        """Shutdown usage tracker gracefully"""
        try:
            self.logger.info("Shutting down usage tracker...")
            
            # Stop monitoring
            self.monitoring_active = False
            
            # Store final snapshots
            for session_id, snapshot in self.current_snapshots.items():
                if self.redis_client:
                    await self._store_snapshot_in_redis(snapshot)
            
            self.logger.info("Usage tracker shutdown complete")
            
        except Exception as e:
            self.logger.error(f"Error during usage tracker shutdown: {e}")