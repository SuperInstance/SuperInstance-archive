"""
Adaptive Resource Manager

Real-time system monitoring and dynamic resource allocation with intelligent
optimization strategies for CPU, memory, GPU, network, and thermal management.
"""

import asyncio
import psutil
import time
import logging
import threading
import subprocess
import os
import json
from collections import deque, defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import numpy as np
from concurrent.futures import ThreadPoolExecutor
import multiprocessing
import socket

from config.settings import config, ResourceTier, PowerProfile

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ResourceType(Enum):
    """Types of system resources"""
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"
    GPU = "gpu"
    THERMAL = "thermal"
    POWER = "power"

class TaskPriority(Enum):
    """Task priority levels"""
    CRITICAL = 0    # System critical
    HIGH = 1        # User interface
    NORMAL = 2      # Background processing
    LOW = 3         # Maintenance tasks
    IDLE = 4        # Only when idle

@dataclass
class SystemMetrics:
    """System performance metrics snapshot"""
    timestamp: float
    cpu_percent: float
    cpu_per_core: List[float]
    cpu_frequency: float
    cpu_temperature: Optional[float]
    memory_percent: float
    memory_available: int
    memory_used: int
    disk_percent: float
    disk_read_speed: float
    disk_write_speed: float
    network_sent: int
    network_recv: int
    network_bandwidth_mbps: float
    gpu_utilization: Optional[float]
    gpu_memory_used: Optional[float]
    gpu_temperature: Optional[float]
    battery_percent: Optional[float]
    power_plugged: bool
    load_average: List[float]
    process_count: int
    thread_count: int
    
    def to_dict(self):
        return asdict(self)

@dataclass
class ResourceAllocation:
    """Resource allocation configuration"""
    max_cpu_percent: float
    max_memory_percent: float
    max_threads: int
    max_processes: int
    io_priority: int  # 0-7, lower is higher priority
    cpu_affinity: Optional[List[int]]
    nice_value: int  # -20 to 19, lower is higher priority
    gpu_enabled: bool
    network_throttle_mbps: Optional[float]

@dataclass
class ScheduledTask:
    """Scheduled task representation"""
    task_id: str
    priority: TaskPriority
    function: Callable
    args: Tuple
    kwargs: Dict[str, Any]
    resource_requirements: Dict[ResourceType, float]
    estimated_duration: float
    deadline: Optional[datetime]
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    cancelled: bool = False
    result: Any = None
    error: Optional[Exception] = None
    
    def to_dict(self):
        data = asdict(self)
        # Convert non-serializable fields
        data['function'] = getattr(self.function, '__name__', str(self.function))
        data['priority'] = self.priority.value
        data['resource_requirements'] = {k.value: v for k, v in self.resource_requirements.items()}
        data['created_at'] = self.created_at.isoformat()
        if self.started_at:
            data['started_at'] = self.started_at.isoformat()
        if self.completed_at:
            data['completed_at'] = self.completed_at.isoformat()
        if self.deadline:
            data['deadline'] = self.deadline.isoformat()
        if self.error:
            data['error'] = str(self.error)
        return data

class ResourceMonitor:
    """Real-time system resource monitoring"""
    
    def __init__(self, history_size: int = 300):
        self.history_size = history_size
        self.metrics_history = deque(maxlen=history_size)
        self.monitoring = False
        self.callbacks = defaultdict(list)
        self._monitor_task = None
        self._last_network_io = None
        self._last_disk_io = None
        
    def add_callback(self, resource_type: ResourceType, callback: Callable):
        """Add callback for resource threshold events"""
        self.callbacks[resource_type].append(callback)
    
    async def start_monitoring(self, interval: float = 1.0):
        """Start continuous resource monitoring"""
        self.monitoring = True
        self._monitor_task = asyncio.create_task(self._monitor_loop(interval))
    
    async def stop_monitoring(self):
        """Stop resource monitoring"""
        self.monitoring = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
    
    async def _monitor_loop(self, interval: float):
        """Main monitoring loop"""
        while self.monitoring:
            try:
                metrics = await self._collect_metrics()
                self.metrics_history.append(metrics)
                await self._check_thresholds(metrics)
                await asyncio.sleep(interval)
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(interval)
    
    async def _collect_metrics(self) -> SystemMetrics:
        """Collect current system metrics"""
        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=0.1)
        cpu_per_core = psutil.cpu_percent(percpu=True)
        cpu_freq = psutil.cpu_freq()
        cpu_frequency = cpu_freq.current if cpu_freq else 0.0
        
        # CPU temperature (if available)
        cpu_temperature = None
        try:
            sensors = psutil.sensors_temperatures()
            if 'coretemp' in sensors:
                cpu_temperature = sensors['coretemp'][0].current
            elif 'cpu_thermal' in sensors:
                cpu_temperature = sensors['cpu_thermal'][0].current
        except (AttributeError, KeyError):
            pass
        
        # Memory metrics
        memory = psutil.virtual_memory()
        
        # Disk metrics
        disk = psutil.disk_usage('/')
        disk_io = psutil.disk_io_counters()
        
        # Calculate disk speeds
        disk_read_speed = 0.0
        disk_write_speed = 0.0
        if self._last_disk_io and disk_io:
            time_delta = 1.0  # Approximate 1 second
            disk_read_speed = (disk_io.read_bytes - self._last_disk_io.read_bytes) / time_delta / 1024 / 1024  # MB/s
            disk_write_speed = (disk_io.write_bytes - self._last_disk_io.write_bytes) / time_delta / 1024 / 1024  # MB/s
        self._last_disk_io = disk_io
        
        # Network metrics
        network_io = psutil.net_io_counters()
        network_bandwidth_mbps = 0.0
        if self._last_network_io and network_io:
            time_delta = 1.0
            bytes_sent = network_io.bytes_sent - self._last_network_io.bytes_sent
            bytes_recv = network_io.bytes_recv - self._last_network_io.bytes_recv
            total_bytes = bytes_sent + bytes_recv
            network_bandwidth_mbps = (total_bytes * 8) / (time_delta * 1024 * 1024)  # Mbps
        self._last_network_io = network_io
        
        # GPU metrics (if available)
        gpu_utilization = None
        gpu_memory_used = None
        gpu_temperature = None
        try:
            import pynvml
            pynvml.nvmlInit()
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            gpu_util = pynvml.nvmlDeviceGetUtilizationRates(handle)
            gpu_utilization = gpu_util.gpu
            
            gpu_mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
            gpu_memory_used = (gpu_mem.used / gpu_mem.total) * 100
            
            gpu_temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
            gpu_temperature = gpu_temp
        except (ImportError, Exception):
            pass
        
        # Battery metrics
        battery = psutil.sensors_battery()
        battery_percent = battery.percent if battery else None
        power_plugged = battery.power_plugged if battery else True
        
        # System load
        load_avg = os.getloadavg() if hasattr(os, 'getloadavg') else [0.0, 0.0, 0.0]
        
        # Process metrics
        process_count = len(psutil.pids())
        thread_count = sum(p.num_threads() for p in psutil.process_iter(['pid', 'num_threads']) 
                          if p.info['num_threads'] is not None)
        
        return SystemMetrics(
            timestamp=time.time(),
            cpu_percent=cpu_percent,
            cpu_per_core=cpu_per_core,
            cpu_frequency=cpu_frequency,
            cpu_temperature=cpu_temperature,
            memory_percent=memory.percent,
            memory_available=memory.available,
            memory_used=memory.used,
            disk_percent=disk.percent,
            disk_read_speed=disk_read_speed,
            disk_write_speed=disk_write_speed,
            network_sent=network_io.bytes_sent,
            network_recv=network_io.bytes_recv,
            network_bandwidth_mbps=network_bandwidth_mbps,
            gpu_utilization=gpu_utilization,
            gpu_memory_used=gpu_memory_used,
            gpu_temperature=gpu_temperature,
            battery_percent=battery_percent,
            power_plugged=power_plugged,
            load_average=list(load_avg),
            process_count=process_count,
            thread_count=thread_count
        )
    
    async def _check_thresholds(self, metrics: SystemMetrics):
        """Check thresholds and trigger callbacks"""
        # CPU threshold checks
        if metrics.cpu_percent > config.thresholds.cpu_critical:
            for callback in self.callbacks[ResourceType.CPU]:
                try:
                    await callback(ResourceType.CPU, metrics.cpu_percent, 'critical')
                except Exception as e:
                    logger.error(f"CPU callback error: {e}")
        
        # Memory threshold checks
        if metrics.memory_percent > config.thresholds.memory_critical:
            for callback in self.callbacks[ResourceType.MEMORY]:
                try:
                    await callback(ResourceType.MEMORY, metrics.memory_percent, 'critical')
                except Exception as e:
                    logger.error(f"Memory callback error: {e}")
        
        # Thermal threshold checks
        if metrics.cpu_temperature and metrics.cpu_temperature > config.thresholds.temperature_critical:
            for callback in self.callbacks[ResourceType.THERMAL]:
                try:
                    await callback(ResourceType.THERMAL, metrics.cpu_temperature, 'critical')
                except Exception as e:
                    logger.error(f"Thermal callback error: {e}")
    
    def get_current_metrics(self) -> Optional[SystemMetrics]:
        """Get most recent metrics"""
        return self.metrics_history[-1] if self.metrics_history else None
    
    def get_average_metrics(self, window_seconds: int = 60) -> Optional[Dict[str, float]]:
        """Get average metrics over time window"""
        if not self.metrics_history:
            return None
        
        current_time = time.time()
        window_metrics = [m for m in self.metrics_history 
                         if current_time - m.timestamp <= window_seconds]
        
        if not window_metrics:
            return None
        
        return {
            'cpu_percent': np.mean([m.cpu_percent for m in window_metrics]),
            'memory_percent': np.mean([m.memory_percent for m in window_metrics]),
            'disk_percent': np.mean([m.disk_percent for m in window_metrics]),
            'network_bandwidth_mbps': np.mean([m.network_bandwidth_mbps for m in window_metrics]),
            'gpu_utilization': np.mean([m.gpu_utilization for m in window_metrics if m.gpu_utilization]),
            'temperature': np.mean([m.cpu_temperature for m in window_metrics if m.cpu_temperature])
        }
    
    def predict_resource_usage(self, seconds_ahead: int = 60) -> Dict[str, float]:
        """Predict future resource usage using linear regression"""
        if len(self.metrics_history) < 10:
            return {}
        
        # Use last 10 minutes of data for prediction
        recent_metrics = list(self.metrics_history)[-600:]  # Last 600 samples
        
        predictions = {}
        
        # CPU prediction
        cpu_values = [m.cpu_percent for m in recent_metrics]
        if len(cpu_values) >= 5:
            x = np.arange(len(cpu_values))
            coeffs = np.polyfit(x, cpu_values, 1)  # Linear fit
            future_x = len(cpu_values) + seconds_ahead
            predictions['cpu_percent'] = max(0, min(100, coeffs[0] * future_x + coeffs[1]))
        
        # Memory prediction
        memory_values = [m.memory_percent for m in recent_metrics]
        if len(memory_values) >= 5:
            x = np.arange(len(memory_values))
            coeffs = np.polyfit(x, memory_values, 1)
            future_x = len(memory_values) + seconds_ahead
            predictions['memory_percent'] = max(0, min(100, coeffs[0] * future_x + coeffs[1]))
        
        return predictions

class TaskScheduler:
    """Intelligent task scheduler with priority and resource management"""
    
    def __init__(self, resource_monitor: ResourceMonitor):
        self.resource_monitor = resource_monitor
        self.task_queue = []  # Priority queue
        self.running_tasks: Dict[str, ScheduledTask] = {}
        self.completed_tasks = deque(maxlen=1000)
        self.executor = ThreadPoolExecutor(max_workers=multiprocessing.cpu_count())
        self.scheduler_running = False
        self._scheduler_task = None
        
    async def start_scheduler(self):
        """Start task scheduler"""
        self.scheduler_running = True
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())
    
    async def stop_scheduler(self):
        """Stop task scheduler"""
        self.scheduler_running = False
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
        
        # Cancel running tasks
        for task in self.running_tasks.values():
            task.cancelled = True
        
        self.executor.shutdown(wait=True)
    
    def schedule_task(self, task: ScheduledTask) -> str:
        """Schedule a new task"""
        # Insert task in priority order
        inserted = False
        for i, existing_task in enumerate(self.task_queue):
            if task.priority.value < existing_task.priority.value:
                self.task_queue.insert(i, task)
                inserted = True
                break
            elif (task.priority.value == existing_task.priority.value and 
                  task.deadline and existing_task.deadline and 
                  task.deadline < existing_task.deadline):
                self.task_queue.insert(i, task)
                inserted = True
                break
        
        if not inserted:
            self.task_queue.append(task)
        
        logger.info(f"Scheduled task {task.task_id} with priority {task.priority.value}")
        return task.task_id
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a scheduled or running task"""
        # Check running tasks
        if task_id in self.running_tasks:
            self.running_tasks[task_id].cancelled = True
            logger.info(f"Cancelled running task {task_id}")
            return True
        
        # Check queue
        for i, task in enumerate(self.task_queue):
            if task.task_id == task_id:
                task.cancelled = True
                self.task_queue.pop(i)
                logger.info(f"Cancelled queued task {task_id}")
                return True
        
        return False
    
    async def _scheduler_loop(self):
        """Main scheduler loop"""
        while self.scheduler_running:
            try:
                await self._process_task_queue()
                await self._cleanup_completed_tasks()
                await asyncio.sleep(0.1)  # Check every 100ms
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(1.0)
    
    async def _process_task_queue(self):
        """Process tasks from queue based on available resources"""
        if not self.task_queue:
            return
        
        current_metrics = self.resource_monitor.get_current_metrics()
        if not current_metrics:
            return
        
        # Calculate available resources
        available_cpu = max(0, 100 - current_metrics.cpu_percent)
        available_memory = max(0, 100 - current_metrics.memory_percent)
        
        # Find tasks that can run with available resources
        tasks_to_run = []
        for task in self.task_queue[:]:  # Copy list to avoid modification during iteration
            if task.cancelled:
                self.task_queue.remove(task)
                continue
            
            # Check if task deadline has passed
            if task.deadline and datetime.now() > task.deadline:
                task.cancelled = True
                task.error = Exception("Task deadline exceeded")
                self.completed_tasks.append(task)
                self.task_queue.remove(task)
                continue
            
            # Check resource requirements
            cpu_required = task.resource_requirements.get(ResourceType.CPU, 10.0)
            memory_required = task.resource_requirements.get(ResourceType.MEMORY, 5.0)
            
            if (cpu_required <= available_cpu and 
                memory_required <= available_memory and
                len(self.running_tasks) < config.optimization.max_threads or multiprocessing.cpu_count()):
                
                tasks_to_run.append(task)
                available_cpu -= cpu_required
                available_memory -= memory_required
                
                # Don't overload system
                if available_cpu < 20 or available_memory < 20:
                    break
        
        # Execute selected tasks
        for task in tasks_to_run:
            await self._execute_task(task)
            self.task_queue.remove(task)
    
    async def _execute_task(self, task: ScheduledTask):
        """Execute a task"""
        task.started_at = datetime.now()
        self.running_tasks[task.task_id] = task
        
        logger.info(f"Executing task {task.task_id}")
        
        # Create resource allocation for task
        allocation = self._create_resource_allocation(task)
        
        try:
            # Submit task to thread pool
            loop = asyncio.get_event_loop()
            future = loop.run_in_executor(
                self.executor,
                self._run_task_with_allocation,
                task,
                allocation
            )
            
            # Don't await here - let it run in background
            asyncio.create_task(self._handle_task_completion(task, future))
            
        except Exception as e:
            task.error = e
            task.completed_at = datetime.now()
            self.completed_tasks.append(task)
            if task.task_id in self.running_tasks:
                del self.running_tasks[task.task_id]
            logger.error(f"Error executing task {task.task_id}: {e}")
    
    async def _handle_task_completion(self, task: ScheduledTask, future):
        """Handle task completion"""
        try:
            result = await future
            task.result = result
            task.completed_at = datetime.now()
            logger.info(f"Task {task.task_id} completed successfully")
        except Exception as e:
            task.error = e
            task.completed_at = datetime.now()
            logger.error(f"Task {task.task_id} failed: {e}")
        finally:
            self.completed_tasks.append(task)
            if task.task_id in self.running_tasks:
                del self.running_tasks[task.task_id]
    
    def _run_task_with_allocation(self, task: ScheduledTask, allocation: ResourceAllocation):
        """Run task with specific resource allocation"""
        try:
            # Set process priority if available
            current_process = psutil.Process()
            if hasattr(current_process, 'nice'):
                current_process.nice(allocation.nice_value)
            
            # Set CPU affinity if specified
            if allocation.cpu_affinity and hasattr(current_process, 'cpu_affinity'):
                current_process.cpu_affinity(allocation.cpu_affinity)
            
            # Execute the task function
            if task.kwargs:
                result = task.function(*task.args, **task.kwargs)
            else:
                result = task.function(*task.args)
            
            return result
            
        except Exception as e:
            logger.error(f"Error in task execution {task.task_id}: {e}")
            raise e
    
    def _create_resource_allocation(self, task: ScheduledTask) -> ResourceAllocation:
        """Create resource allocation based on task priority and system state"""
        current_metrics = self.resource_monitor.get_current_metrics()
        resource_tier = config.get_resource_tier(
            current_metrics.cpu_percent if current_metrics else 50.0,
            current_metrics.memory_percent if current_metrics else 50.0,
            current_metrics.cpu_temperature
        )
        
        # Base allocation
        if task.priority == TaskPriority.CRITICAL:
            return ResourceAllocation(
                max_cpu_percent=80.0,
                max_memory_percent=70.0,
                max_threads=multiprocessing.cpu_count(),
                max_processes=4,
                io_priority=0,
                cpu_affinity=None,
                nice_value=-10,
                gpu_enabled=True,
                network_throttle_mbps=None
            )
        elif task.priority == TaskPriority.HIGH:
            return ResourceAllocation(
                max_cpu_percent=60.0,
                max_memory_percent=50.0,
                max_threads=max(2, multiprocessing.cpu_count() // 2),
                max_processes=2,
                io_priority=1,
                cpu_affinity=None,
                nice_value=-5,
                gpu_enabled=True,
                network_throttle_mbps=None
            )
        elif task.priority == TaskPriority.NORMAL:
            return ResourceAllocation(
                max_cpu_percent=40.0,
                max_memory_percent=30.0,
                max_threads=max(1, multiprocessing.cpu_count() // 4),
                max_processes=1,
                io_priority=3,
                cpu_affinity=None,
                nice_value=0,
                gpu_enabled=resource_tier in [ResourceTier.HIGH, ResourceTier.ABUNDANT],
                network_throttle_mbps=50.0 if resource_tier == ResourceTier.LOW else None
            )
        else:  # LOW or IDLE
            return ResourceAllocation(
                max_cpu_percent=20.0,
                max_memory_percent=15.0,
                max_threads=1,
                max_processes=1,
                io_priority=6,
                cpu_affinity=[0],  # Use only first core
                nice_value=10,
                gpu_enabled=False,
                network_throttle_mbps=10.0
            )
    
    async def _cleanup_completed_tasks(self):
        """Clean up old completed tasks"""
        current_time = datetime.now()
        cutoff_time = current_time - timedelta(hours=1)
        
        # Remove old completed tasks
        while (self.completed_tasks and 
               self.completed_tasks[0].completed_at and
               self.completed_tasks[0].completed_at < cutoff_time):
            self.completed_tasks.popleft()
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific task"""
        # Check running tasks
        if task_id in self.running_tasks:
            return self.running_tasks[task_id].to_dict()
        
        # Check completed tasks
        for task in self.completed_tasks:
            if task.task_id == task_id:
                return task.to_dict()
        
        # Check queue
        for task in self.task_queue:
            if task.task_id == task_id:
                return task.to_dict()
        
        return None
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get overall queue status"""
        return {
            'queued_tasks': len(self.task_queue),
            'running_tasks': len(self.running_tasks),
            'completed_tasks': len(self.completed_tasks),
            'queue_by_priority': {
                priority.name: sum(1 for t in self.task_queue if t.priority == priority)
                for priority in TaskPriority
            },
            'running_by_priority': {
                priority.name: sum(1 for t in self.running_tasks.values() if t.priority == priority)
                for priority in TaskPriority
            }
        }

class AdaptiveResourceManager:
    """Main adaptive resource management system"""
    
    def __init__(self):
        self.monitor = ResourceMonitor()
        self.scheduler = TaskScheduler(self.monitor)
        self.current_resource_tier = ResourceTier.MODERATE
        self.current_power_profile = PowerProfile.BALANCED
        self.optimization_callbacks = []
        self.running = False
        
        # Set up resource threshold callbacks
        self.monitor.add_callback(ResourceType.CPU, self._handle_cpu_pressure)
        self.monitor.add_callback(ResourceType.MEMORY, self._handle_memory_pressure)
        self.monitor.add_callback(ResourceType.THERMAL, self._handle_thermal_pressure)
        
    async def start(self):
        """Start the adaptive resource manager"""
        self.running = True
        await self.monitor.start_monitoring(config.optimization.monitoring_interval)
        await self.scheduler.start_scheduler()
        logger.info("Adaptive Resource Manager started")
    
    async def stop(self):
        """Stop the adaptive resource manager"""
        self.running = False
        await self.scheduler.stop_scheduler()
        await self.monitor.stop_monitoring()
        logger.info("Adaptive Resource Manager stopped")
    
    def add_optimization_callback(self, callback: Callable):
        """Add callback for optimization events"""
        self.optimization_callbacks.append(callback)
    
    async def _handle_cpu_pressure(self, resource_type: ResourceType, value: float, severity: str):
        """Handle high CPU usage"""
        logger.warning(f"CPU pressure detected: {value}% ({severity})")
        
        if severity == 'critical':
            # Emergency CPU pressure relief
            await self._emergency_resource_relief(ResourceType.CPU)
    
    async def _handle_memory_pressure(self, resource_type: ResourceType, value: float, severity: str):
        """Handle high memory usage"""
        logger.warning(f"Memory pressure detected: {value}% ({severity})")
        
        if severity == 'critical':
            # Emergency memory pressure relief
            await self._emergency_resource_relief(ResourceType.MEMORY)
    
    async def _handle_thermal_pressure(self, resource_type: ResourceType, value: float, severity: str):
        """Handle high temperature"""
        logger.warning(f"Thermal pressure detected: {value}°C ({severity})")
        
        if severity == 'critical':
            # Emergency thermal throttling
            await self._emergency_thermal_throttling()
    
    async def _emergency_resource_relief(self, resource_type: ResourceType):
        """Emergency resource pressure relief"""
        # Cancel low priority tasks
        cancelled_count = 0
        for task_id, task in list(self.scheduler.running_tasks.items()):
            if task.priority in [TaskPriority.LOW, TaskPriority.IDLE]:
                self.scheduler.cancel_task(task_id)
                cancelled_count += 1
        
        # Clear low priority queue items
        self.scheduler.task_queue = [t for t in self.scheduler.task_queue 
                                   if t.priority not in [TaskPriority.LOW, TaskPriority.IDLE]]
        
        logger.info(f"Emergency relief: cancelled {cancelled_count} low priority tasks")
        
        # Trigger optimization callbacks
        for callback in self.optimization_callbacks:
            try:
                await callback('emergency_relief', resource_type, cancelled_count)
            except Exception as e:
                logger.error(f"Optimization callback error: {e}")
    
    async def _emergency_thermal_throttling(self):
        """Emergency thermal throttling"""
        # Reduce CPU frequency if possible
        try:
            subprocess.run(['cpufreq-set', '-u', '1GHz'], check=False)
        except FileNotFoundError:
            pass
        
        # Cancel all but critical tasks
        cancelled_count = 0
        for task_id, task in list(self.scheduler.running_tasks.items()):
            if task.priority != TaskPriority.CRITICAL:
                self.scheduler.cancel_task(task_id)
                cancelled_count += 1
        
        logger.warning(f"Emergency thermal throttling: cancelled {cancelled_count} tasks")
    
    def update_resource_tier(self) -> ResourceTier:
        """Update current resource tier based on system state"""
        metrics = self.monitor.get_current_metrics()
        if not metrics:
            return self.current_resource_tier
        
        new_tier = config.get_resource_tier(
            metrics.cpu_percent,
            metrics.memory_percent,
            metrics.cpu_temperature
        )
        
        # Apply hysteresis to prevent oscillation
        if new_tier != self.current_resource_tier:
            # Require tier change to be sustained
            recent_avg = self.monitor.get_average_metrics(30)  # 30 second window
            if recent_avg:
                sustained_tier = config.get_resource_tier(
                    recent_avg['cpu_percent'],
                    recent_avg['memory_percent'],
                    recent_avg.get('temperature')
                )
                
                if sustained_tier == new_tier:
                    old_tier = self.current_resource_tier
                    self.current_resource_tier = new_tier
                    logger.info(f"Resource tier changed: {old_tier.value} -> {new_tier.value}")
                    
                    # Notify optimization callbacks
                    asyncio.create_task(self._notify_tier_change(old_tier, new_tier))
        
        return self.current_resource_tier
    
    async def _notify_tier_change(self, old_tier: ResourceTier, new_tier: ResourceTier):
        """Notify callbacks of tier change"""
        for callback in self.optimization_callbacks:
            try:
                await callback('tier_change', old_tier, new_tier)
            except Exception as e:
                logger.error(f"Tier change callback error: {e}")
    
    def schedule_task(self, task_id: str, function: Callable, args: Tuple = (), 
                     kwargs: Dict[str, Any] = None, priority: TaskPriority = TaskPriority.NORMAL,
                     resource_requirements: Dict[ResourceType, float] = None,
                     estimated_duration: float = 60.0, deadline: Optional[datetime] = None) -> str:
        """Schedule a task for execution"""
        task = ScheduledTask(
            task_id=task_id,
            priority=priority,
            function=function,
            args=args,
            kwargs=kwargs or {},
            resource_requirements=resource_requirements or {},
            estimated_duration=estimated_duration,
            deadline=deadline,
            created_at=datetime.now()
        )
        
        return self.scheduler.schedule_task(task)
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        metrics = self.monitor.get_current_metrics()
        predictions = self.monitor.predict_resource_usage()
        queue_status = self.scheduler.get_queue_status()
        
        return {
            'resource_manager': {
                'running': self.running,
                'current_tier': self.current_resource_tier.value,
                'power_profile': self.current_power_profile.value,
                'monitoring_active': self.monitor.monitoring
            },
            'current_metrics': metrics.to_dict() if metrics else None,
            'predictions': predictions,
            'task_scheduler': queue_status,
            'optimization_callbacks': len(self.optimization_callbacks),
            'system_info': {
                'cpu_count': multiprocessing.cpu_count(),
                'available_memory_gb': psutil.virtual_memory().available / (1024**3),
                'disk_free_gb': psutil.disk_usage('/').free / (1024**3),
                'platform': os.name
            }
        }

# Global resource manager instance
resource_manager = AdaptiveResourceManager()

# Utility functions for easy task scheduling
async def schedule_background_task(task_id: str, function: Callable, *args, **kwargs):
    """Schedule a background task"""
    return resource_manager.schedule_task(
        task_id=task_id,
        function=function,
        args=args,
        kwargs=kwargs,
        priority=TaskPriority.NORMAL,
        resource_requirements={ResourceType.CPU: 20.0, ResourceType.MEMORY: 10.0}
    )

async def schedule_critical_task(task_id: str, function: Callable, *args, **kwargs):
    """Schedule a critical task"""
    return resource_manager.schedule_task(
        task_id=task_id,
        function=function,
        args=args,
        kwargs=kwargs,
        priority=TaskPriority.CRITICAL,
        resource_requirements={ResourceType.CPU: 50.0, ResourceType.MEMORY: 30.0}
    )

if __name__ == "__main__":
    # Demo usage
    async def demo_task(name: str, duration: int = 5):
        """Demo task that simulates work"""
        import time
        print(f"Starting task {name}")
        time.sleep(duration)
        print(f"Completed task {name}")
        return f"Result from {name}"
    
    async def main():
        # Start resource manager
        await resource_manager.start()
        
        # Schedule some demo tasks
        await schedule_background_task("demo_1", demo_task, "Background Task 1", 3)
        await schedule_critical_task("demo_2", demo_task, "Critical Task", 2)
        await schedule_background_task("demo_3", demo_task, "Background Task 2", 4)
        
        # Run for a while
        await asyncio.sleep(15)
        
        # Print status
        status = resource_manager.get_system_status()
        print(json.dumps(status, indent=2, default=str))
        
        # Stop resource manager
        await resource_manager.stop()
    
    asyncio.run(main())