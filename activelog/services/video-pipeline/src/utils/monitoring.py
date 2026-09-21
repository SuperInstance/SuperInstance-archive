"""
Monitoring and health check utilities for video pipeline service
"""
import asyncio
import json
import os
import psutil
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from collections import deque, defaultdict

import structlog
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

from config.settings import settings

logger = structlog.get_logger()

# Prometheus metrics
video_uploads_total = Counter('video_uploads_total', 'Total number of video uploads', ['status'])
video_processing_duration = Histogram('video_processing_duration_seconds', 'Video processing duration in seconds', ['operation_type'])
active_jobs_gauge = Gauge('active_jobs', 'Number of active processing jobs', ['job_type'])
system_cpu_usage = Gauge('system_cpu_usage_percent', 'System CPU usage percentage')
system_memory_usage = Gauge('system_memory_usage_percent', 'System memory usage percentage')
system_disk_usage = Gauge('system_disk_usage_percent', 'System disk usage percentage', ['path'])
queue_size_gauge = Gauge('queue_size', 'Size of processing queues', ['queue_name'])
error_rate_counter = Counter('errors_total', 'Total number of errors', ['error_type', 'component'])


class SystemMonitor:
    """
    System resource monitoring and health checks
    """
    
    def __init__(self):
        self.start_time = datetime.utcnow()
        self.metrics_history = defaultdict(lambda: deque(maxlen=100))
        self._monitoring_task: Optional[asyncio.Task] = None
        
    async def start_monitoring(self, interval_seconds: int = 30) -> None:
        """Start system monitoring loop"""
        if self._monitoring_task and not self._monitoring_task.done():
            return
            
        self._monitoring_task = asyncio.create_task(
            self._monitoring_loop(interval_seconds)
        )
        
        logger.info("System monitoring started", interval_seconds=interval_seconds)

    async def stop_monitoring(self) -> None:
        """Stop system monitoring"""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
                
        logger.info("System monitoring stopped")

    async def _monitoring_loop(self, interval_seconds: int) -> None:
        """Main monitoring loop"""
        try:
            while True:
                await self._collect_system_metrics()
                await asyncio.sleep(interval_seconds)
                
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error("Monitoring loop failed", error=str(e))

    async def _collect_system_metrics(self) -> None:
        """Collect system metrics"""
        try:
            timestamp = datetime.utcnow()
            
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            system_cpu_usage.set(cpu_percent)
            self.metrics_history["cpu"].append((timestamp, cpu_percent))
            
            # Memory metrics
            memory = psutil.virtual_memory()
            system_memory_usage.set(memory.percent)
            self.metrics_history["memory"].append((timestamp, memory.percent))
            
            # Disk metrics
            disk_paths = ["/", "/tmp"]
            for path in disk_paths:
                if os.path.exists(path):
                    disk = psutil.disk_usage(path)
                    disk_percent = (disk.used / disk.total) * 100
                    system_disk_usage.labels(path=path).set(disk_percent)
                    self.metrics_history[f"disk_{path}"].append((timestamp, disk_percent))
            
            # Network metrics
            network = psutil.net_io_counters()
            self.metrics_history["network_bytes_sent"].append((timestamp, network.bytes_sent))
            self.metrics_history["network_bytes_recv"].append((timestamp, network.bytes_recv))
            
            # Process-specific metrics
            current_process = psutil.Process()
            process_cpu = current_process.cpu_percent()
            process_memory = current_process.memory_info().rss / 1024 / 1024  # MB
            
            self.metrics_history["process_cpu"].append((timestamp, process_cpu))
            self.metrics_history["process_memory"].append((timestamp, process_memory))
            
        except Exception as e:
            logger.error("Failed to collect system metrics", error=str(e))

    def get_system_health(self) -> Dict[str, Any]:
        """Get current system health status"""
        try:
            # Current metrics
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            
            # Health status
            health_score = 1.0
            issues = []
            warnings = []
            
            # CPU check
            if cpu_percent > 90:
                health_score *= 0.5
                issues.append(f"High CPU usage: {cpu_percent:.1f}%")
            elif cpu_percent > 80:
                health_score *= 0.8
                warnings.append(f"Elevated CPU usage: {cpu_percent:.1f}%")
                
            # Memory check
            if memory.percent > 90:
                health_score *= 0.5
                issues.append(f"High memory usage: {memory.percent:.1f}%")
            elif memory.percent > 80:
                health_score *= 0.8
                warnings.append(f"Elevated memory usage: {memory.percent:.1f}%")
                
            # Disk check
            disk_percent = (disk.used / disk.total) * 100
            if disk_percent > 95:
                health_score *= 0.3
                issues.append(f"Very low disk space: {disk_percent:.1f}% used")
            elif disk_percent > 85:
                health_score *= 0.7
                warnings.append(f"Low disk space: {disk_percent:.1f}% used")
                
            # Determine overall status
            if health_score >= 0.9:
                status = "healthy"
            elif health_score >= 0.7:
                status = "degraded"
            else:
                status = "unhealthy"
                
            return {
                "status": status,
                "health_score": health_score,
                "uptime_seconds": (datetime.utcnow() - self.start_time).total_seconds(),
                "metrics": {
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "disk_percent": disk_percent,
                    "available_memory_mb": memory.available / 1024 / 1024,
                    "free_disk_gb": disk.free / 1024 / 1024 / 1024
                },
                "issues": issues,
                "warnings": warnings,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Failed to get system health", error=str(e))
            return {
                "status": "unknown",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    def get_metrics_history(
        self, 
        metric_name: str, 
        duration_minutes: int = 60
    ) -> List[Dict[str, Any]]:
        """Get historical metrics for a specific metric"""
        if metric_name not in self.metrics_history:
            return []
            
        cutoff_time = datetime.utcnow() - timedelta(minutes=duration_minutes)
        history = self.metrics_history[metric_name]
        
        return [
            {"timestamp": timestamp.isoformat(), "value": value}
            for timestamp, value in history
            if timestamp >= cutoff_time
        ]


class JobMonitor:
    """
    Monitor processing jobs and queues
    """
    
    def __init__(self):
        self.active_jobs = {}
        self.job_history = deque(maxlen=1000)
        self.queue_stats = defaultdict(lambda: {"size": 0, "processed": 0, "failed": 0})

    def start_job(self, job_id: str, job_type: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Record job start"""
        job_info = {
            "job_id": job_id,
            "job_type": job_type,
            "start_time": datetime.utcnow(),
            "metadata": metadata or {}
        }
        
        self.active_jobs[job_id] = job_info
        active_jobs_gauge.labels(job_type=job_type).inc()
        
        logger.info("Job started", job_id=job_id, job_type=job_type)

    def complete_job(
        self, 
        job_id: str, 
        success: bool = True, 
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ) -> None:
        """Record job completion"""
        if job_id not in self.active_jobs:
            logger.warning("Trying to complete unknown job", job_id=job_id)
            return
            
        job_info = self.active_jobs.pop(job_id)
        end_time = datetime.utcnow()
        duration = (end_time - job_info["start_time"]).total_seconds()
        
        # Update metrics
        job_type = job_info["job_type"]
        active_jobs_gauge.labels(job_type=job_type).dec()
        video_processing_duration.labels(operation_type=job_type).observe(duration)
        
        if success:
            self.queue_stats[job_type]["processed"] += 1
        else:
            self.queue_stats[job_type]["failed"] += 1
            error_rate_counter.labels(error_type="job_failed", component=job_type).inc()
        
        # Record in history
        job_record = {
            **job_info,
            "end_time": end_time,
            "duration_seconds": duration,
            "success": success,
            "result": result,
            "error": error
        }
        
        self.job_history.append(job_record)
        
        logger.info("Job completed", 
                   job_id=job_id, 
                   job_type=job_type,
                   success=success,
                   duration_seconds=duration)

    def update_queue_size(self, queue_name: str, size: int) -> None:
        """Update queue size metric"""
        queue_size_gauge.labels(queue_name=queue_name).set(size)
        self.queue_stats[queue_name]["size"] = size

    def get_active_jobs(self) -> List[Dict[str, Any]]:
        """Get list of currently active jobs"""
        current_time = datetime.utcnow()
        
        return [
            {
                **job_info,
                "runtime_seconds": (current_time - job_info["start_time"]).total_seconds(),
                "start_time": job_info["start_time"].isoformat()
            }
            for job_info in self.active_jobs.values()
        ]

    def get_job_statistics(self, duration_hours: int = 24) -> Dict[str, Any]:
        """Get job statistics for specified duration"""
        cutoff_time = datetime.utcnow() - timedelta(hours=duration_hours)
        
        # Filter recent jobs
        recent_jobs = [
            job for job in self.job_history
            if job["start_time"] >= cutoff_time
        ]
        
        if not recent_jobs:
            return {
                "total_jobs": 0,
                "successful_jobs": 0,
                "failed_jobs": 0,
                "success_rate": 0,
                "avg_duration_seconds": 0,
                "job_types": {}
            }
        
        # Calculate statistics
        total_jobs = len(recent_jobs)
        successful_jobs = sum(1 for job in recent_jobs if job["success"])
        failed_jobs = total_jobs - successful_jobs
        success_rate = (successful_jobs / total_jobs) * 100 if total_jobs > 0 else 0
        avg_duration = sum(job["duration_seconds"] for job in recent_jobs) / total_jobs
        
        # Job type breakdown
        job_types = defaultdict(lambda: {"count": 0, "success": 0, "avg_duration": 0})
        
        for job in recent_jobs:
            job_type = job["job_type"]
            job_types[job_type]["count"] += 1
            if job["success"]:
                job_types[job_type]["success"] += 1
            job_types[job_type]["avg_duration"] = (
                job_types[job_type]["avg_duration"] + job["duration_seconds"]
            ) / job_types[job_type]["count"]
        
        return {
            "total_jobs": total_jobs,
            "successful_jobs": successful_jobs,
            "failed_jobs": failed_jobs,
            "success_rate": success_rate,
            "avg_duration_seconds": avg_duration,
            "job_types": dict(job_types),
            "queue_stats": dict(self.queue_stats)
        }


class HealthChecker:
    """
    Comprehensive health checking for the video pipeline service
    """
    
    def __init__(self, system_monitor: SystemMonitor, job_monitor: JobMonitor):
        self.system_monitor = system_monitor
        self.job_monitor = job_monitor

    async def comprehensive_health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check"""
        health_check = {
            "overall_status": "healthy",
            "checks": {},
            "timestamp": datetime.utcnow().isoformat(),
            "service_info": {
                "name": "video-pipeline",
                "version": "1.0.0",
                "uptime_seconds": (datetime.utcnow() - self.system_monitor.start_time).total_seconds()
            }
        }
        
        try:
            # System health
            system_health = self.system_monitor.get_system_health()
            health_check["checks"]["system"] = system_health
            
            # Database connectivity (placeholder for actual DB check)
            health_check["checks"]["database"] = await self._check_database()
            
            # Message queue connectivity
            health_check["checks"]["message_queue"] = await self._check_message_queue()
            
            # Storage service
            health_check["checks"]["storage"] = await self._check_storage()
            
            # External services
            health_check["checks"]["external_services"] = await self._check_external_services()
            
            # Processing capacity
            health_check["checks"]["processing_capacity"] = self._check_processing_capacity()
            
            # Determine overall status
            failed_checks = [
                name for name, check in health_check["checks"].items()
                if check.get("status") not in ["healthy", "degraded"]
            ]
            
            degraded_checks = [
                name for name, check in health_check["checks"].items()
                if check.get("status") == "degraded"
            ]
            
            if failed_checks:
                health_check["overall_status"] = "unhealthy"
                health_check["failed_checks"] = failed_checks
            elif degraded_checks:
                health_check["overall_status"] = "degraded" 
                health_check["degraded_checks"] = degraded_checks
                
            return health_check
            
        except Exception as e:
            logger.error("Health check failed", error=str(e))
            return {
                "overall_status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    async def _check_database(self) -> Dict[str, Any]:
        """Check database connectivity"""
        try:
            # This would be implemented with actual database connection test
            # For now, return a placeholder
            return {
                "status": "healthy",
                "latency_ms": 5.2,
                "connections": 5
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }

    async def _check_message_queue(self) -> Dict[str, Any]:
        """Check message queue connectivity"""
        try:
            from services.message_queue import mq_service
            return await mq_service.health_check()
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }

    async def _check_storage(self) -> Dict[str, Any]:
        """Check storage service connectivity"""
        try:
            from services.storage import storage_service
            
            # Test bucket access
            buckets = ["videos", "thumbnails", "processed"]
            bucket_status = {}
            
            for bucket in buckets:
                try:
                    # Try to list objects (just check connectivity)
                    objects = await storage_service.list_objects(
                        prefix="health_check_", 
                        bucket_type=bucket
                    )
                    bucket_status[bucket] = "accessible"
                except Exception as e:
                    bucket_status[bucket] = f"error: {str(e)}"
                    
            all_accessible = all(status == "accessible" for status in bucket_status.values())
            
            return {
                "status": "healthy" if all_accessible else "degraded",
                "buckets": bucket_status
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }

    async def _check_external_services(self) -> Dict[str, Any]:
        """Check external service connectivity"""
        try:
            from services.external_apis import external_api_service
            return await external_api_service.health_check_all_services()
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }

    def _check_processing_capacity(self) -> Dict[str, Any]:
        """Check current processing capacity"""
        try:
            active_jobs = self.job_monitor.get_active_jobs()
            job_stats = self.job_monitor.get_job_statistics(duration_hours=1)
            
            # Simple capacity check
            max_concurrent_jobs = 10  # This could be configurable
            current_load = len(active_jobs) / max_concurrent_jobs
            
            if current_load < 0.7:
                status = "healthy"
            elif current_load < 0.9:
                status = "degraded"
            else:
                status = "overloaded"
                
            return {
                "status": status,
                "active_jobs": len(active_jobs),
                "max_concurrent_jobs": max_concurrent_jobs,
                "load_percentage": current_load * 100,
                "recent_success_rate": job_stats["success_rate"]
            }
            
        except Exception as e:
            return {
                "status": "unknown",
                "error": str(e)
            }


def get_prometheus_metrics() -> str:
    """Get Prometheus metrics"""
    return generate_latest()


# Global monitoring instances
system_monitor = SystemMonitor()
job_monitor = JobMonitor()
health_checker = HealthChecker(system_monitor, job_monitor)