#!/usr/bin/env python3
"""
Real-time Performance Profiler and Bottleneck Detection

Advanced performance monitoring system that identifies, analyzes, and resolves
performance issues in real-time across the platform builders service.
"""

import asyncio
import time
import threading
import psutil
import statistics
import json
import logging
import traceback
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from collections import deque, defaultdict
import sys
import inspect
import functools
import cProfile
import pstats
import io
from concurrent.futures import ThreadPoolExecutor
from queue import Queue, Empty
import gc
import memory_profiler

logger = logging.getLogger(__name__)


class BottleneckType(Enum):
    CPU = "cpu"
    MEMORY = "memory"
    IO = "io"
    NETWORK = "network"
    DATABASE = "database"
    LOCK_CONTENTION = "lock_contention"
    ASYNC_BLOCKING = "async_blocking"
    GC_PRESSURE = "gc_pressure"
    RESOURCE_LEAK = "resource_leak"


class SeverityLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class PerformanceMetric:
    timestamp: float
    metric_name: str
    value: float
    unit: str
    labels: Dict[str, str] = None
    
    def __post_init__(self):
        if self.labels is None:
            self.labels = {}


@dataclass
class Bottleneck:
    id: str
    type: BottleneckType
    severity: SeverityLevel
    description: str
    location: str
    metrics: Dict[str, float]
    stack_trace: Optional[str]
    suggestions: List[str]
    timestamp: float
    duration: Optional[float] = None


@dataclass
class ProfileSnapshot:
    timestamp: float
    function_stats: Dict[str, Dict[str, Any]]
    memory_usage: Dict[str, float]
    cpu_usage: float
    io_stats: Dict[str, float]
    thread_info: Dict[str, Any]
    gc_stats: Dict[str, int]


class FunctionProfiler:
    """Decorator and context manager for function profiling"""
    
    def __init__(self, profiler_manager, function_name: str = None):
        self.profiler_manager = profiler_manager
        self.function_name = function_name
        self.start_time = None
        
    def __enter__(self):
        self.start_time = time.perf_counter()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = time.perf_counter() - self.start_time
            self.profiler_manager.record_function_call(
                self.function_name or "anonymous",
                duration,
                exc_type is not None
            )
    
    def __call__(self, func):
        function_name = f"{func.__module__}.{func.__qualname__}"
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                self.profiler_manager.record_function_call(
                    function_name,
                    time.perf_counter() - start_time,
                    False
                )
                return result
            except Exception as e:
                self.profiler_manager.record_function_call(
                    function_name,
                    time.perf_counter() - start_time,
                    True
                )
                raise
                
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                self.profiler_manager.record_function_call(
                    function_name,
                    time.perf_counter() - start_time,
                    False
                )
                return result
            except Exception as e:
                self.profiler_manager.record_function_call(
                    function_name,
                    time.perf_counter() - start_time,
                    True
                )
                raise
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper


class MemoryTracker:
    """Advanced memory usage tracking and leak detection"""
    
    def __init__(self, profiler_manager):
        self.profiler_manager = profiler_manager
        self.memory_snapshots = deque(maxlen=100)
        self.object_counts = defaultdict(int)
        self.large_objects = []
        
    def track_allocation(self, obj_type: str, size: int):
        """Track memory allocation"""
        self.object_counts[obj_type] += 1
        if size > 1024 * 1024:  # Track objects > 1MB
            self.large_objects.append({
                'type': obj_type,
                'size': size,
                'timestamp': time.time(),
                'stack': traceback.format_stack()[-5:]
            })
    
    def take_snapshot(self) -> Dict[str, Any]:
        """Take memory usage snapshot"""
        process = psutil.Process()
        memory_info = process.memory_info()
        
        snapshot = {
            'timestamp': time.time(),
            'rss': memory_info.rss,
            'vms': memory_info.vms,
            'percent': process.memory_percent(),
            'object_counts': dict(self.object_counts),
            'gc_counts': {
                str(i): gc.get_count()[i] for i in range(3)
            },
            'large_objects_count': len(self.large_objects)
        }
        
        self.memory_snapshots.append(snapshot)
        return snapshot
    
    def detect_leaks(self) -> List[Dict[str, Any]]:
        """Detect potential memory leaks"""
        leaks = []
        
        if len(self.memory_snapshots) < 10:
            return leaks
        
        recent_snapshots = list(self.memory_snapshots)[-10:]
        memory_growth = []
        
        for i in range(1, len(recent_snapshots)):
            growth = recent_snapshots[i]['rss'] - recent_snapshots[i-1]['rss']
            memory_growth.append(growth)
        
        # Check for consistent memory growth
        if len(memory_growth) > 5:
            avg_growth = statistics.mean(memory_growth[-5:])
            if avg_growth > 1024 * 1024:  # > 1MB growth per snapshot
                leaks.append({
                    'type': 'consistent_growth',
                    'growth_rate': avg_growth,
                    'severity': 'high' if avg_growth > 10 * 1024 * 1024 else 'medium'
                })
        
        # Check for object count anomalies
        for obj_type, count in self.object_counts.items():
            if count > 10000:  # Arbitrary threshold
                leaks.append({
                    'type': 'object_accumulation',
                    'object_type': obj_type,
                    'count': count,
                    'severity': 'medium'
                })
        
        return leaks


class AsyncProfiler:
    """Profiler for async operations and coroutines"""
    
    def __init__(self, profiler_manager):
        self.profiler_manager = profiler_manager
        self.active_tasks = {}
        self.task_metrics = defaultdict(list)
        
    def track_task_start(self, task_id: str, task_name: str):
        """Track async task start"""
        self.active_tasks[task_id] = {
            'name': task_name,
            'start_time': time.perf_counter(),
            'create_time': time.time()
        }
    
    def track_task_end(self, task_id: str, success: bool = True):
        """Track async task completion"""
        if task_id not in self.active_tasks:
            return
        
        task_info = self.active_tasks.pop(task_id)
        duration = time.perf_counter() - task_info['start_time']
        
        self.task_metrics[task_info['name']].append({
            'duration': duration,
            'success': success,
            'timestamp': time.time()
        })
    
    def detect_blocking_operations(self) -> List[Dict[str, Any]]:
        """Detect potentially blocking async operations"""
        blocking_ops = []
        
        # Check for long-running tasks
        current_time = time.perf_counter()
        for task_id, task_info in self.active_tasks.items():
            duration = current_time - task_info['start_time']
            if duration > 5.0:  # Tasks running > 5 seconds
                blocking_ops.append({
                    'type': 'long_running_task',
                    'task_id': task_id,
                    'task_name': task_info['name'],
                    'duration': duration,
                    'severity': 'high' if duration > 30 else 'medium'
                })
        
        # Check task metrics for patterns
        for task_name, metrics in self.task_metrics.items():
            if len(metrics) >= 10:
                recent_metrics = metrics[-10:]
                avg_duration = statistics.mean([m['duration'] for m in recent_metrics])
                
                if avg_duration > 1.0:  # Average > 1 second
                    blocking_ops.append({
                        'type': 'slow_task_pattern',
                        'task_name': task_name,
                        'avg_duration': avg_duration,
                        'severity': 'medium'
                    })
        
        return blocking_ops


class IOProfiler:
    """I/O operations profiler"""
    
    def __init__(self, profiler_manager):
        self.profiler_manager = profiler_manager
        self.io_operations = deque(maxlen=1000)
        self.file_operations = defaultdict(list)
        
    def track_io_operation(self, operation: str, path: str, duration: float, bytes_transferred: int = 0):
        """Track I/O operation"""
        io_op = {
            'operation': operation,
            'path': path,
            'duration': duration,
            'bytes': bytes_transferred,
            'timestamp': time.time(),
            'throughput': bytes_transferred / duration if duration > 0 else 0
        }
        
        self.io_operations.append(io_op)
        self.file_operations[path].append(io_op)
    
    def detect_io_bottlenecks(self) -> List[Dict[str, Any]]:
        """Detect I/O bottlenecks"""
        bottlenecks = []
        
        if not self.io_operations:
            return bottlenecks
        
        # Check for slow I/O operations
        slow_ops = [op for op in self.io_operations if op['duration'] > 0.1]
        if len(slow_ops) > len(self.io_operations) * 0.1:  # > 10% slow ops
            bottlenecks.append({
                'type': 'slow_io_operations',
                'slow_ops_count': len(slow_ops),
                'total_ops': len(self.io_operations),
                'severity': 'medium'
            })
        
        # Check for files with many operations
        for path, ops in self.file_operations.items():
            if len(ops) > 100:  # Many operations on same file
                avg_duration = statistics.mean([op['duration'] for op in ops])
                if avg_duration > 0.05:  # Average > 50ms
                    bottlenecks.append({
                        'type': 'high_frequency_slow_file',
                        'path': path,
                        'operations_count': len(ops),
                        'avg_duration': avg_duration,
                        'severity': 'medium'
                    })
        
        return bottlenecks


class PerformanceProfiler:
    """Main performance profiler and bottleneck detector"""
    
    def __init__(self, enable_detailed_profiling: bool = True):
        self.enable_detailed_profiling = enable_detailed_profiling
        self.metrics = deque(maxlen=10000)
        self.bottlenecks = []
        self.function_calls = defaultdict(list)
        self.profiling_overhead = deque(maxlen=100)
        
        # Specialized profilers
        self.memory_tracker = MemoryTracker(self)
        self.async_profiler = AsyncProfiler(self)
        self.io_profiler = IOProfiler(self)
        
        # System monitoring
        self.system_metrics = {
            'cpu_percent': deque(maxlen=100),
            'memory_percent': deque(maxlen=100),
            'disk_io': deque(maxlen=100),
            'network_io': deque(maxlen=100)
        }
        
        # Profiling state
        self.is_profiling = False
        self.profiling_lock = threading.Lock()
        self.monitoring_task = None
        
    async def start_profiling(self):
        """Start performance profiling"""
        if self.is_profiling:
            return
        
        self.is_profiling = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Performance profiling started")
    
    async def stop_profiling(self):
        """Stop performance profiling"""
        if not self.is_profiling:
            return
        
        self.is_profiling = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Performance profiling stopped")
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.is_profiling:
            try:
                await self._collect_system_metrics()
                await self._analyze_performance()
                await asyncio.sleep(1.0)  # Collect metrics every second
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(5.0)
    
    async def _collect_system_metrics(self):
        """Collect system performance metrics"""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=None)
            self.system_metrics['cpu_percent'].append(cpu_percent)
            
            # Memory metrics
            memory = psutil.virtual_memory()
            self.system_metrics['memory_percent'].append(memory.percent)
            
            # Disk I/O metrics
            disk_io = psutil.disk_io_counters()
            if disk_io:
                self.system_metrics['disk_io'].append({
                    'read_bytes': disk_io.read_bytes,
                    'write_bytes': disk_io.write_bytes,
                    'timestamp': time.time()
                })
            
            # Network I/O metrics
            network_io = psutil.net_io_counters()
            if network_io:
                self.system_metrics['network_io'].append({
                    'bytes_sent': network_io.bytes_sent,
                    'bytes_recv': network_io.bytes_recv,
                    'timestamp': time.time()
                })
            
            # Memory snapshot
            self.memory_tracker.take_snapshot()
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
    
    async def _analyze_performance(self):
        """Analyze performance and detect bottlenecks"""
        try:
            # Analyze CPU bottlenecks
            await self._analyze_cpu_bottlenecks()
            
            # Analyze memory bottlenecks
            await self._analyze_memory_bottlenecks()
            
            # Analyze I/O bottlenecks
            await self._analyze_io_bottlenecks()
            
            # Analyze async bottlenecks
            await self._analyze_async_bottlenecks()
            
            # Analyze function performance
            await self._analyze_function_performance()
            
        except Exception as e:
            logger.error(f"Error analyzing performance: {e}")
    
    async def _analyze_cpu_bottlenecks(self):
        """Analyze CPU usage bottlenecks"""
        if len(self.system_metrics['cpu_percent']) < 10:
            return
        
        recent_cpu = list(self.system_metrics['cpu_percent'])[-10:]
        avg_cpu = statistics.mean(recent_cpu)
        
        if avg_cpu > 80:
            bottleneck = Bottleneck(
                id=f"cpu_high_{int(time.time())}",
                type=BottleneckType.CPU,
                severity=SeverityLevel.HIGH if avg_cpu > 90 else SeverityLevel.MEDIUM,
                description=f"High CPU usage detected: {avg_cpu:.1f}%",
                location="system",
                metrics={"cpu_percent": avg_cpu},
                stack_trace=None,
                suggestions=[
                    "Consider optimizing CPU-intensive operations",
                    "Use async/await for I/O operations",
                    "Implement caching for expensive computations",
                    "Consider load balancing or horizontal scaling"
                ],
                timestamp=time.time()
            )
            self._add_bottleneck(bottleneck)
    
    async def _analyze_memory_bottlenecks(self):
        """Analyze memory usage bottlenecks"""
        if len(self.system_metrics['memory_percent']) < 10:
            return
        
        recent_memory = list(self.system_metrics['memory_percent'])[-10:]
        avg_memory = statistics.mean(recent_memory)
        
        if avg_memory > 80:
            bottleneck = Bottleneck(
                id=f"memory_high_{int(time.time())}",
                type=BottleneckType.MEMORY,
                severity=SeverityLevel.HIGH if avg_memory > 90 else SeverityLevel.MEDIUM,
                description=f"High memory usage detected: {avg_memory:.1f}%",
                location="system",
                metrics={"memory_percent": avg_memory},
                stack_trace=None,
                suggestions=[
                    "Check for memory leaks",
                    "Implement object pooling",
                    "Use generators for large datasets",
                    "Consider increasing available memory"
                ],
                timestamp=time.time()
            )
            self._add_bottleneck(bottleneck)
        
        # Check for memory leaks
        leaks = self.memory_tracker.detect_leaks()
        for leak in leaks:
            bottleneck = Bottleneck(
                id=f"memory_leak_{int(time.time())}_{leak['type']}",
                type=BottleneckType.MEMORY,
                severity=SeverityLevel.HIGH if leak['severity'] == 'high' else SeverityLevel.MEDIUM,
                description=f"Memory leak detected: {leak['type']}",
                location="memory_tracker",
                metrics=leak,
                stack_trace=None,
                suggestions=[
                    "Review object lifecycle management",
                    "Check for circular references",
                    "Use weak references where appropriate",
                    "Implement proper cleanup in destructors"
                ],
                timestamp=time.time()
            )
            self._add_bottleneck(bottleneck)
    
    async def _analyze_io_bottlenecks(self):
        """Analyze I/O bottlenecks"""
        io_bottlenecks = self.io_profiler.detect_io_bottlenecks()
        
        for bottleneck_data in io_bottlenecks:
            bottleneck = Bottleneck(
                id=f"io_{bottleneck_data['type']}_{int(time.time())}",
                type=BottleneckType.IO,
                severity=SeverityLevel.HIGH if bottleneck_data['severity'] == 'high' else SeverityLevel.MEDIUM,
                description=f"I/O bottleneck: {bottleneck_data['type']}",
                location="io_operations",
                metrics=bottleneck_data,
                stack_trace=None,
                suggestions=[
                    "Use asynchronous I/O operations",
                    "Implement I/O batching",
                    "Consider using faster storage",
                    "Optimize file access patterns"
                ],
                timestamp=time.time()
            )
            self._add_bottleneck(bottleneck)
    
    async def _analyze_async_bottlenecks(self):
        """Analyze async operation bottlenecks"""
        blocking_ops = self.async_profiler.detect_blocking_operations()
        
        for op_data in blocking_ops:
            bottleneck = Bottleneck(
                id=f"async_{op_data['type']}_{int(time.time())}",
                type=BottleneckType.ASYNC_BLOCKING,
                severity=SeverityLevel.HIGH if op_data['severity'] == 'high' else SeverityLevel.MEDIUM,
                description=f"Async bottleneck: {op_data['type']}",
                location="async_operations",
                metrics=op_data,
                stack_trace=None,
                suggestions=[
                    "Review async/await usage",
                    "Avoid blocking calls in async functions",
                    "Use asyncio.create_task() for concurrent operations",
                    "Consider task timeouts"
                ],
                timestamp=time.time()
            )
            self._add_bottleneck(bottleneck)
    
    async def _analyze_function_performance(self):
        """Analyze function call performance"""
        for func_name, calls in self.function_calls.items():
            if len(calls) < 10:
                continue
            
            recent_calls = calls[-10:]
            durations = [call['duration'] for call in recent_calls]
            avg_duration = statistics.mean(durations)
            
            if avg_duration > 1.0:  # Functions taking > 1 second on average
                bottleneck = Bottleneck(
                    id=f"slow_function_{func_name}_{int(time.time())}",
                    type=BottleneckType.CPU,
                    severity=SeverityLevel.MEDIUM,
                    description=f"Slow function detected: {func_name}",
                    location=func_name,
                    metrics={
                        "avg_duration": avg_duration,
                        "call_count": len(recent_calls),
                        "error_rate": sum(1 for call in recent_calls if call['error']) / len(recent_calls)
                    },
                    stack_trace=None,
                    suggestions=[
                        "Profile function for optimization opportunities",
                        "Consider caching results",
                        "Break down into smaller functions",
                        "Use async/await if doing I/O"
                    ],
                    timestamp=time.time()
                )
                self._add_bottleneck(bottleneck)
    
    def _add_bottleneck(self, bottleneck: Bottleneck):
        """Add bottleneck to the list"""
        # Avoid duplicate bottlenecks
        for existing in self.bottlenecks:
            if (existing.type == bottleneck.type and 
                existing.location == bottleneck.location and
                time.time() - existing.timestamp < 60):  # Within 1 minute
                return
        
        self.bottlenecks.append(bottleneck)
        
        # Keep only recent bottlenecks
        cutoff_time = time.time() - 3600  # 1 hour
        self.bottlenecks = [b for b in self.bottlenecks if b.timestamp > cutoff_time]
        
        logger.warning(f"Performance bottleneck detected: {bottleneck.description}")
    
    def record_function_call(self, function_name: str, duration: float, error: bool = False):
        """Record function call metrics"""
        call_data = {
            'duration': duration,
            'error': error,
            'timestamp': time.time()
        }
        
        self.function_calls[function_name].append(call_data)
        
        # Keep only recent calls
        if len(self.function_calls[function_name]) > 100:
            self.function_calls[function_name] = self.function_calls[function_name][-50:]
    
    def get_profile_decorator(self) -> FunctionProfiler:
        """Get function profiler decorator"""
        return FunctionProfiler(self)
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        return {
            'timestamp': time.time(),
            'system_metrics': {
                'cpu_avg': statistics.mean(list(self.system_metrics['cpu_percent'])[-10:]) if self.system_metrics['cpu_percent'] else 0,
                'memory_avg': statistics.mean(list(self.system_metrics['memory_percent'])[-10:]) if self.system_metrics['memory_percent'] else 0,
                'active_threads': threading.active_count(),
                'gc_counts': dict(enumerate(gc.get_count()))
            },
            'bottlenecks': [asdict(b) for b in self.bottlenecks[-20:]],  # Last 20 bottlenecks
            'function_performance': {
                name: {
                    'call_count': len(calls),
                    'avg_duration': statistics.mean([c['duration'] for c in calls[-10:]]) if calls else 0,
                    'error_rate': sum(1 for c in calls[-10:] if c['error']) / min(len(calls), 10) if calls else 0
                }
                for name, calls in list(self.function_calls.items())[:10]  # Top 10 functions
            },
            'memory_info': self.memory_tracker.memory_snapshots[-1] if self.memory_tracker.memory_snapshots else None,
            'is_profiling': self.is_profiling
        }
    
    def get_optimization_recommendations(self) -> List[Dict[str, Any]]:
        """Get optimization recommendations based on detected bottlenecks"""
        recommendations = []
        
        # Group bottlenecks by type
        bottleneck_types = defaultdict(list)
        for bottleneck in self.bottlenecks[-50:]:  # Recent bottlenecks
            bottleneck_types[bottleneck.type].append(bottleneck)
        
        for bottleneck_type, bottlenecks in bottleneck_types.items():
            if len(bottlenecks) >= 3:  # Multiple instances of same type
                recommendations.append({
                    'type': f'{bottleneck_type.value}_optimization',
                    'priority': 'high' if any(b.severity == SeverityLevel.HIGH for b in bottlenecks) else 'medium',
                    'description': f'Multiple {bottleneck_type.value} bottlenecks detected',
                    'count': len(bottlenecks),
                    'suggestions': bottlenecks[0].suggestions,  # Use suggestions from first bottleneck
                    'affected_locations': list(set(b.location for b in bottlenecks))
                })
        
        return recommendations


# Global profiler instance
_global_profiler: Optional[PerformanceProfiler] = None


def get_profiler() -> PerformanceProfiler:
    """Get global profiler instance"""
    global _global_profiler
    if _global_profiler is None:
        _global_profiler = PerformanceProfiler()
    return _global_profiler


def profile_function(func_name: str = None):
    """Decorator for profiling functions"""
    profiler = get_profiler()
    return profiler.get_profile_decorator()(func_name)


async def start_profiling():
    """Start global performance profiling"""
    profiler = get_profiler()
    await profiler.start_profiling()


async def stop_profiling():
    """Stop global performance profiling"""
    profiler = get_profiler()
    await profiler.stop_profiling()


def get_performance_summary() -> Dict[str, Any]:
    """Get global performance summary"""
    profiler = get_profiler()
    return profiler.get_performance_summary()


def get_optimization_recommendations() -> List[Dict[str, Any]]:
    """Get optimization recommendations"""
    profiler = get_profiler()
    return profiler.get_optimization_recommendations()