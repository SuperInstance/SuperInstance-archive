import asyncio
import logging
import time
import statistics
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
from enum import Enum
import threading
import psutil
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
import weakref

logger = logging.getLogger(__name__)

class MetricType(Enum):
    LATENCY = "latency"
    THROUGHPUT = "throughput" 
    CPU_USAGE = "cpu_usage"
    MEMORY_USAGE = "memory_usage"
    ERROR_RATE = "error_rate"
    QUEUE_DEPTH = "queue_depth"
    RESPONSE_SIZE = "response_size"

class OptimizationStrategy(Enum):
    LOAD_SHEDDING = "load_shedding"
    CIRCUIT_BREAKER = "circuit_breaker"
    ADAPTIVE_TIMEOUT = "adaptive_timeout"
    BATCH_OPTIMIZATION = "batch_optimization"
    PREFETCHING = "prefetching"
    CONNECTION_POOLING = "connection_pooling"
    COMPRESSION = "compression"

@dataclass
class MetricData:
    timestamp: datetime
    value: float
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PerformanceAlert:
    metric_type: MetricType
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    message: str
    current_value: float
    threshold: float
    timestamp: datetime = field(default_factory=datetime.now)
    resolved: bool = False

class MetricsCollector:
    def __init__(self):
        self.metrics = defaultdict(lambda: deque(maxlen=1000))  # Keep last 1000 samples
        self.thresholds = {
            MetricType.LATENCY: {"warning": 1000, "critical": 5000},  # ms
            MetricType.CPU_USAGE: {"warning": 80, "critical": 95},    # %
            MetricType.MEMORY_USAGE: {"warning": 85, "critical": 95}, # %
            MetricType.ERROR_RATE: {"warning": 5, "critical": 15},    # %
            MetricType.QUEUE_DEPTH: {"warning": 100, "critical": 500}
        }
        self.alerts = []
        self.collection_interval = 10  # seconds
        self.collection_task = None
        self.running = False
        self.lock = threading.Lock()
    
    async def start(self):
        self.running = True
        self.collection_task = asyncio.create_task(self._collection_loop())
        logger.info("Metrics collector started")
    
    async def stop(self):
        self.running = False
        if self.collection_task:
            self.collection_task.cancel()
            try:
                await self.collection_task
            except asyncio.CancelledError:
                pass
        logger.info("Metrics collector stopped")
    
    def record_metric(self, metric_type: MetricType, value: float, metadata: Dict[str, Any] = None):
        """Record a metric value"""
        with self.lock:
            metric_data = MetricData(
                timestamp=datetime.now(),
                value=value,
                metadata=metadata or {}
            )
            self.metrics[metric_type].append(metric_data)
            
            # Check for threshold violations
            self._check_thresholds(metric_type, value)
    
    def get_recent_metrics(self, metric_type: MetricType, 
                          duration_minutes: int = 10) -> List[MetricData]:
        """Get recent metrics within duration"""
        with self.lock:
            cutoff_time = datetime.now() - timedelta(minutes=duration_minutes)
            return [
                metric for metric in self.metrics[metric_type]
                if metric.timestamp > cutoff_time
            ]
    
    def get_metric_stats(self, metric_type: MetricType, 
                        duration_minutes: int = 10) -> Dict[str, float]:
        """Get statistical summary of metrics"""
        recent_metrics = self.get_recent_metrics(metric_type, duration_minutes)
        
        if not recent_metrics:
            return {}
        
        values = [metric.value for metric in recent_metrics]
        
        return {
            "count": len(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "min": min(values),
            "max": max(values),
            "std_dev": statistics.stdev(values) if len(values) > 1 else 0,
            "p95": np.percentile(values, 95),
            "p99": np.percentile(values, 99)
        }
    
    def _check_thresholds(self, metric_type: MetricType, value: float):
        """Check if metric violates thresholds and create alerts"""
        if metric_type not in self.thresholds:
            return
        
        thresholds = self.thresholds[metric_type]
        severity = None
        
        if value >= thresholds.get("critical", float('inf')):
            severity = "CRITICAL"
        elif value >= thresholds.get("warning", float('inf')):
            severity = "HIGH"
        
        if severity:
            alert = PerformanceAlert(
                metric_type=metric_type,
                severity=severity,
                message=f"{metric_type.value} exceeded threshold: {value}",
                current_value=value,
                threshold=thresholds.get("critical" if severity == "CRITICAL" else "warning")
            )
            self.alerts.append(alert)
            logger.warning(f"Performance alert: {alert.message}")
    
    async def _collection_loop(self):
        """Background system metrics collection"""
        while self.running:
            try:
                await self._collect_system_metrics()
                await asyncio.sleep(self.collection_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Metrics collection error: {e}")
                await asyncio.sleep(30)
    
    async def _collect_system_metrics(self):
        """Collect system-level metrics"""
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        self.record_metric(MetricType.CPU_USAGE, cpu_percent)
        
        # Memory usage
        memory = psutil.virtual_memory()
        self.record_metric(MetricType.MEMORY_USAGE, memory.percent)
        
        # Additional system metrics could be added here

class AdaptiveThrottler:
    def __init__(self, initial_rate_limit: int = 100):
        self.rate_limit = initial_rate_limit
        self.request_count = 0
        self.window_start = time.time()
        self.window_duration = 60  # 1 minute windows
        
        self.success_rate_threshold = 0.95
        self.latency_threshold = 2.0  # seconds
        self.adjustment_factor = 0.1
        
        self.recent_requests = deque(maxlen=1000)
        self.lock = threading.Lock()
    
    async def should_allow_request(self) -> bool:
        """Check if request should be allowed based on current rate"""
        with self.lock:
            current_time = time.time()
            
            # Reset window if needed
            if current_time - self.window_start > self.window_duration:
                self.request_count = 0
                self.window_start = current_time
            
            if self.request_count >= self.rate_limit:
                return False
            
            self.request_count += 1
            return True
    
    def record_request_result(self, latency: float, success: bool):
        """Record request result for adaptive adjustment"""
        with self.lock:
            self.recent_requests.append({
                "timestamp": time.time(),
                "latency": latency,
                "success": success
            })
            
            # Adjust rate limit based on performance
            self._adjust_rate_limit()
    
    def _adjust_rate_limit(self):
        """Adjust rate limit based on recent performance"""
        if len(self.recent_requests) < 10:
            return
        
        # Calculate recent metrics
        recent_window = [req for req in self.recent_requests 
                        if time.time() - req["timestamp"] < 300]  # Last 5 minutes
        
        if not recent_window:
            return
        
        success_rate = sum(1 for req in recent_window if req["success"]) / len(recent_window)
        avg_latency = sum(req["latency"] for req in recent_window) / len(recent_window)
        
        # Adjust rate limit
        if success_rate < self.success_rate_threshold or avg_latency > self.latency_threshold:
            # Decrease rate limit
            self.rate_limit = max(10, int(self.rate_limit * (1 - self.adjustment_factor)))
            logger.info(f"Decreased rate limit to {self.rate_limit}")
        elif success_rate > 0.98 and avg_latency < self.latency_threshold * 0.5:
            # Increase rate limit
            self.rate_limit = int(self.rate_limit * (1 + self.adjustment_factor))
            logger.info(f"Increased rate limit to {self.rate_limit}")
    
    def get_current_rate_limit(self) -> int:
        return self.rate_limit

class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, timeout: float = 60.0, 
                 expected_exception: type = Exception):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.lock = threading.Lock()
    
    async def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        with self.lock:
            if self.state == "OPEN":
                if self._should_attempt_reset():
                    self.state = "HALF_OPEN"
                    logger.info("Circuit breaker transitioning to HALF_OPEN")
                else:
                    raise Exception("Circuit breaker is OPEN")
        
        try:
            result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        if self.last_failure_time is None:
            return False
        return time.time() - self.last_failure_time >= self.timeout
    
    def _on_success(self):
        """Handle successful call"""
        with self.lock:
            self.failure_count = 0
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                logger.info("Circuit breaker reset to CLOSED")
    
    def _on_failure(self):
        """Handle failed call"""
        with self.lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
                logger.warning(f"Circuit breaker tripped to OPEN after {self.failure_count} failures")

class BatchProcessor:
    def __init__(self, batch_size: int = 10, max_wait_time: float = 1.0):
        self.batch_size = batch_size
        self.max_wait_time = max_wait_time
        self.pending_requests = []
        self.batch_start_time = None
        self.lock = threading.Lock()
        self.condition = threading.Condition(self.lock)
        self.processor_task = None
        self.running = False
    
    async def start(self):
        self.running = True
        self.processor_task = asyncio.create_task(self._batch_processor_loop())
        logger.info("Batch processor started")
    
    async def stop(self):
        self.running = False
        if self.processor_task:
            self.processor_task.cancel()
            try:
                await self.processor_task
            except asyncio.CancelledError:
                pass
        logger.info("Batch processor stopped")
    
    async def submit_request(self, request_data: Any, callback: Callable) -> Any:
        """Submit request for batch processing"""
        future = asyncio.Future()
        
        with self.condition:
            self.pending_requests.append({
                "data": request_data,
                "callback": callback,
                "future": future,
                "timestamp": time.time()
            })
            
            if self.batch_start_time is None:
                self.batch_start_time = time.time()
            
            self.condition.notify()
        
        return await future
    
    async def _batch_processor_loop(self):
        """Main batch processing loop"""
        while self.running:
            try:
                batch = await self._get_next_batch()
                if batch:
                    await self._process_batch(batch)
                else:
                    await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Batch processing error: {e}")
                await asyncio.sleep(1)
    
    async def _get_next_batch(self) -> Optional[List[Dict[str, Any]]]:
        """Get next batch of requests to process"""
        with self.condition:
            if not self.pending_requests:
                return None
            
            # Check if we should process batch
            should_process = (
                len(self.pending_requests) >= self.batch_size or
                (self.batch_start_time and 
                 time.time() - self.batch_start_time >= self.max_wait_time)
            )
            
            if should_process:
                batch = self.pending_requests[:]
                self.pending_requests.clear()
                self.batch_start_time = None
                return batch
        
        return None
    
    async def _process_batch(self, batch: List[Dict[str, Any]]):
        """Process a batch of requests"""
        try:
            # Group by callback type for efficient processing
            callback_groups = defaultdict(list)
            for request in batch:
                callback_groups[request["callback"]].append(request)
            
            # Process each group
            for callback, requests in callback_groups.items():
                try:
                    batch_data = [req["data"] for req in requests]
                    
                    # Execute batch callback
                    if asyncio.iscoroutinefunction(callback):
                        results = await callback(batch_data)
                    else:
                        results = callback(batch_data)
                    
                    # Set results for individual futures
                    if isinstance(results, list) and len(results) == len(requests):
                        for request, result in zip(requests, results):
                            if not request["future"].done():
                                request["future"].set_result(result)
                    else:
                        # Single result for all requests
                        for request in requests:
                            if not request["future"].done():
                                request["future"].set_result(results)
                
                except Exception as e:
                    # Set exception for all requests in group
                    for request in requests:
                        if not request["future"].done():
                            request["future"].set_exception(e)
        
        except Exception as e:
            logger.error(f"Batch processing failed: {e}")
            # Set exception for all requests
            for request in batch:
                if not request["future"].done():
                    request["future"].set_exception(e)

class ConnectionPool:
    def __init__(self, create_connection: Callable, max_connections: int = 10,
                 min_connections: int = 2, connection_timeout: float = 30.0):
        self.create_connection = create_connection
        self.max_connections = max_connections
        self.min_connections = min_connections
        self.connection_timeout = connection_timeout
        
        self.pool = asyncio.Queue(maxsize=max_connections)
        self.active_connections = set()
        self.connection_stats = {
            "created": 0,
            "destroyed": 0,
            "in_use": 0,
            "idle": 0
        }
        self.lock = threading.Lock()
        self.maintenance_task = None
        self.running = False
    
    async def start(self):
        """Initialize connection pool"""
        self.running = True
        
        # Create minimum connections
        for _ in range(self.min_connections):
            try:
                connection = await self.create_connection()
                await self.pool.put(connection)
                self.connection_stats["created"] += 1
            except Exception as e:
                logger.error(f"Failed to create initial connection: {e}")
        
        # Start maintenance task
        self.maintenance_task = asyncio.create_task(self._maintenance_loop())
        logger.info(f"Connection pool started with {self.pool.qsize()} connections")
    
    async def stop(self):
        """Stop connection pool"""
        self.running = False
        
        if self.maintenance_task:
            self.maintenance_task.cancel()
            try:
                await self.maintenance_task
            except asyncio.CancelledError:
                pass
        
        # Close all connections
        while not self.pool.empty():
            try:
                connection = self.pool.get_nowait()
                await self._close_connection(connection)
            except asyncio.QueueEmpty:
                break
        
        logger.info("Connection pool stopped")
    
    async def get_connection(self):
        """Get connection from pool"""
        try:
            # Try to get existing connection
            connection = self.pool.get_nowait()
        except asyncio.QueueEmpty:
            # Create new connection if under limit
            if len(self.active_connections) < self.max_connections:
                try:
                    connection = await self.create_connection()
                    self.connection_stats["created"] += 1
                except Exception as e:
                    logger.error(f"Failed to create connection: {e}")
                    raise
            else:
                # Wait for available connection
                connection = await asyncio.wait_for(
                    self.pool.get(), 
                    timeout=self.connection_timeout
                )
        
        self.active_connections.add(connection)
        with self.lock:
            self.connection_stats["in_use"] = len(self.active_connections)
            self.connection_stats["idle"] = self.pool.qsize()
        
        return connection
    
    async def return_connection(self, connection):
        """Return connection to pool"""
        if connection in self.active_connections:
            self.active_connections.remove(connection)
            
            # Check if connection is still valid
            if await self._is_connection_valid(connection):
                try:
                    self.pool.put_nowait(connection)
                except asyncio.QueueFull:
                    # Pool is full, close connection
                    await self._close_connection(connection)
            else:
                # Connection is invalid, close it
                await self._close_connection(connection)
            
            with self.lock:
                self.connection_stats["in_use"] = len(self.active_connections)
                self.connection_stats["idle"] = self.pool.qsize()
    
    async def _is_connection_valid(self, connection) -> bool:
        """Check if connection is still valid"""
        # This should be implemented based on connection type
        # For now, assume all connections are valid
        return True
    
    async def _close_connection(self, connection):
        """Close a connection"""
        try:
            if hasattr(connection, 'close'):
                await connection.close()
            elif hasattr(connection, '__aexit__'):
                await connection.__aexit__(None, None, None)
            
            self.connection_stats["destroyed"] += 1
        except Exception as e:
            logger.error(f"Error closing connection: {e}")
    
    async def _maintenance_loop(self):
        """Maintain optimal pool size"""
        while self.running:
            try:
                await self._maintain_pool()
                await asyncio.sleep(60)  # Check every minute
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Connection pool maintenance error: {e}")
                await asyncio.sleep(30)
    
    async def _maintain_pool(self):
        """Maintain minimum number of connections"""
        current_total = self.pool.qsize() + len(self.active_connections)
        
        if current_total < self.min_connections:
            needed = self.min_connections - current_total
            for _ in range(needed):
                try:
                    connection = await self.create_connection()
                    await self.pool.put(connection)
                    self.connection_stats["created"] += 1
                except Exception as e:
                    logger.error(f"Failed to create maintenance connection: {e}")
                    break
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics"""
        with self.lock:
            return {
                **self.connection_stats,
                "pool_size": self.pool.qsize(),
                "active_connections": len(self.active_connections),
                "max_connections": self.max_connections,
                "min_connections": self.min_connections
            }

class PerformanceOptimizer:
    def __init__(self):
        self.metrics_collector = MetricsCollector()
        self.throttler = AdaptiveThrottler()
        self.circuit_breakers = {}
        self.batch_processors = {}
        self.connection_pools = {}
        
        self.optimization_strategies = {
            OptimizationStrategy.LOAD_SHEDDING: self._load_shedding_optimizer,
            OptimizationStrategy.CIRCUIT_BREAKER: self._circuit_breaker_optimizer,
            OptimizationStrategy.ADAPTIVE_TIMEOUT: self._adaptive_timeout_optimizer,
            OptimizationStrategy.BATCH_OPTIMIZATION: self._batch_optimization_optimizer
        }
        
        self.active_optimizations = set()
        self.optimization_history = []
        
        self.optimization_task = None
        self.running = False
    
    async def start(self):
        """Start performance optimizer"""
        self.running = True
        
        await self.metrics_collector.start()
        
        # Start batch processors
        for processor in self.batch_processors.values():
            await processor.start()
        
        # Start connection pools
        for pool in self.connection_pools.values():
            await pool.start()
        
        # Start optimization loop
        self.optimization_task = asyncio.create_task(self._optimization_loop())
        
        logger.info("Performance optimizer started")
    
    async def stop(self):
        """Stop performance optimizer"""
        self.running = False
        
        if self.optimization_task:
            self.optimization_task.cancel()
            try:
                await self.optimization_task
            except asyncio.CancelledError:
                pass
        
        # Stop components
        for pool in self.connection_pools.values():
            await pool.stop()
        
        for processor in self.batch_processors.values():
            await processor.stop()
        
        await self.metrics_collector.stop()
        
        logger.info("Performance optimizer stopped")
    
    def add_circuit_breaker(self, name: str, failure_threshold: int = 5, 
                           timeout: float = 60.0) -> CircuitBreaker:
        """Add circuit breaker for a service"""
        circuit_breaker = CircuitBreaker(failure_threshold, timeout)
        self.circuit_breakers[name] = circuit_breaker
        return circuit_breaker
    
    def add_batch_processor(self, name: str, batch_size: int = 10, 
                           max_wait_time: float = 1.0) -> BatchProcessor:
        """Add batch processor"""
        processor = BatchProcessor(batch_size, max_wait_time)
        self.batch_processors[name] = processor
        return processor
    
    def add_connection_pool(self, name: str, create_connection: Callable,
                           max_connections: int = 10) -> ConnectionPool:
        """Add connection pool"""
        pool = ConnectionPool(create_connection, max_connections)
        self.connection_pools[name] = pool
        return pool
    
    async def should_allow_request(self) -> bool:
        """Check if request should be allowed (throttling)"""
        return await self.throttler.should_allow_request()
    
    def record_request(self, latency: float, success: bool):
        """Record request performance"""
        self.throttler.record_request_result(latency, success)
        self.metrics_collector.record_metric(MetricType.LATENCY, latency * 1000)  # Convert to ms
        
        if not success:
            error_rate = self._calculate_error_rate()
            self.metrics_collector.record_metric(MetricType.ERROR_RATE, error_rate)
    
    def _calculate_error_rate(self) -> float:
        """Calculate current error rate"""
        recent_requests = getattr(self.throttler, 'recent_requests', [])
        if len(recent_requests) < 10:
            return 0.0
        
        recent_window = [req for req in recent_requests 
                        if time.time() - req["timestamp"] < 300]  # Last 5 minutes
        
        if not recent_window:
            return 0.0
        
        error_count = sum(1 for req in recent_window if not req["success"])
        return (error_count / len(recent_window)) * 100
    
    async def _optimization_loop(self):
        """Main optimization loop"""
        while self.running:
            try:
                await self._analyze_and_optimize()
                await asyncio.sleep(30)  # Analyze every 30 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Optimization loop error: {e}")
                await asyncio.sleep(60)
    
    async def _analyze_and_optimize(self):
        """Analyze performance and apply optimizations"""
        # Get current metrics
        cpu_stats = self.metrics_collector.get_metric_stats(MetricType.CPU_USAGE, 5)
        memory_stats = self.metrics_collector.get_metric_stats(MetricType.MEMORY_USAGE, 5)
        latency_stats = self.metrics_collector.get_metric_stats(MetricType.LATENCY, 5)
        error_stats = self.metrics_collector.get_metric_stats(MetricType.ERROR_RATE, 5)
        
        # Determine needed optimizations
        needed_optimizations = set()
        
        # High CPU usage
        if cpu_stats.get("mean", 0) > 80:
            needed_optimizations.add(OptimizationStrategy.LOAD_SHEDDING)
            needed_optimizations.add(OptimizationStrategy.BATCH_OPTIMIZATION)
        
        # High error rate
        if error_stats.get("mean", 0) > 10:
            needed_optimizations.add(OptimizationStrategy.CIRCUIT_BREAKER)
        
        # High latency
        if latency_stats.get("p95", 0) > 2000:  # > 2 seconds
            needed_optimizations.add(OptimizationStrategy.ADAPTIVE_TIMEOUT)
            needed_optimizations.add(OptimizationStrategy.CONNECTION_POOLING)
        
        # Apply new optimizations
        for strategy in needed_optimizations:
            if strategy not in self.active_optimizations:
                await self._apply_optimization(strategy)
        
        # Remove optimizations that are no longer needed
        for strategy in list(self.active_optimizations):
            if strategy not in needed_optimizations:
                await self._remove_optimization(strategy)
    
    async def _apply_optimization(self, strategy: OptimizationStrategy):
        """Apply an optimization strategy"""
        try:
            if strategy in self.optimization_strategies:
                await self.optimization_strategies[strategy](True)
                self.active_optimizations.add(strategy)
                
                self.optimization_history.append({
                    "strategy": strategy.value,
                    "action": "applied",
                    "timestamp": datetime.now()
                })
                
                logger.info(f"Applied optimization strategy: {strategy.value}")
        
        except Exception as e:
            logger.error(f"Failed to apply optimization {strategy.value}: {e}")
    
    async def _remove_optimization(self, strategy: OptimizationStrategy):
        """Remove an optimization strategy"""
        try:
            if strategy in self.optimization_strategies:
                await self.optimization_strategies[strategy](False)
                self.active_optimizations.discard(strategy)
                
                self.optimization_history.append({
                    "strategy": strategy.value,
                    "action": "removed",
                    "timestamp": datetime.now()
                })
                
                logger.info(f"Removed optimization strategy: {strategy.value}")
        
        except Exception as e:
            logger.error(f"Failed to remove optimization {strategy.value}: {e}")
    
    async def _load_shedding_optimizer(self, enable: bool):
        """Load shedding optimization"""
        if enable:
            # Increase throttling aggressiveness
            self.throttler.adjustment_factor = 0.2
            self.throttler.success_rate_threshold = 0.98
        else:
            # Reset to normal values
            self.throttler.adjustment_factor = 0.1
            self.throttler.success_rate_threshold = 0.95
    
    async def _circuit_breaker_optimizer(self, enable: bool):
        """Circuit breaker optimization"""
        if enable:
            # Make circuit breakers more aggressive
            for breaker in self.circuit_breakers.values():
                breaker.failure_threshold = max(3, breaker.failure_threshold - 2)
        else:
            # Reset to normal values
            for breaker in self.circuit_breakers.values():
                breaker.failure_threshold = min(5, breaker.failure_threshold + 2)
    
    async def _adaptive_timeout_optimizer(self, enable: bool):
        """Adaptive timeout optimization"""
        # This would integrate with request handlers to adjust timeouts
        # Implementation depends on specific use cases
        pass
    
    async def _batch_optimization_optimizer(self, enable: bool):
        """Batch processing optimization"""
        if enable:
            # Reduce batch sizes for faster processing
            for processor in self.batch_processors.values():
                processor.batch_size = max(5, processor.batch_size // 2)
                processor.max_wait_time = min(0.5, processor.max_wait_time)
        else:
            # Reset to normal batch sizes
            for processor in self.batch_processors.values():
                processor.batch_size = min(20, processor.batch_size * 2)
                processor.max_wait_time = max(1.0, processor.max_wait_time)
    
    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics"""
        stats = {
            "metrics": {},
            "throttling": {
                "current_rate_limit": self.throttler.get_current_rate_limit(),
                "request_count": self.throttler.request_count,
                "window_start": self.throttler.window_start
            },
            "circuit_breakers": {
                name: {
                    "state": breaker.state,
                    "failure_count": breaker.failure_count,
                    "failure_threshold": breaker.failure_threshold
                }
                for name, breaker in self.circuit_breakers.items()
            },
            "connection_pools": {
                name: pool.get_stats()
                for name, pool in self.connection_pools.items()
            },
            "active_optimizations": [strategy.value for strategy in self.active_optimizations],
            "recent_alerts": [
                {
                    "metric_type": alert.metric_type.value,
                    "severity": alert.severity,
                    "message": alert.message,
                    "timestamp": alert.timestamp.isoformat()
                }
                for alert in self.metrics_collector.alerts[-10:]  # Last 10 alerts
            ]
        }
        
        # Add metric statistics
        for metric_type in MetricType:
            metric_stats = self.metrics_collector.get_metric_stats(metric_type, 10)
            if metric_stats:
                stats["metrics"][metric_type.value] = metric_stats
        
        return stats