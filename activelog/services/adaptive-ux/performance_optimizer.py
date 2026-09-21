#!/usr/bin/env python3
"""
Performance Optimizer for Adaptive UX System

This module provides performance optimizations including caching, batching,
memory management, and intelligent preloading for the adaptive UX system.
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Tuple
from enum import Enum
from dataclasses import dataclass, asdict
from collections import defaultdict, deque, OrderedDict
import hashlib
import pickle
from concurrent.futures import ThreadPoolExecutor
import threading

class CacheStrategy(Enum):
    """Cache strategies for different data types"""
    LRU = "lru"                 # Least Recently Used
    TTL = "ttl"                 # Time To Live
    ADAPTIVE = "adaptive"       # Adaptive based on usage patterns
    WRITE_THROUGH = "write_through"  # Write to cache and storage simultaneously
    WRITE_BEHIND = "write_behind"    # Write to cache immediately, storage later

class MetricType(Enum):
    """Types of performance metrics"""
    RESPONSE_TIME = "response_time"
    CACHE_HIT_RATE = "cache_hit_rate"
    MEMORY_USAGE = "memory_usage"
    REQUEST_RATE = "request_rate"
    ERROR_RATE = "error_rate"
    USER_SATISFACTION = "user_satisfaction"

@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    key: str
    value: Any
    created_at: datetime
    last_accessed: datetime
    access_count: int
    ttl_seconds: Optional[int] = None
    size_bytes: int = 0
    
    def is_expired(self) -> bool:
        """Check if cache entry is expired"""
        if self.ttl_seconds is None:
            return False
        return (datetime.utcnow() - self.created_at).total_seconds() > self.ttl_seconds
    
    def access(self):
        """Mark entry as accessed"""
        self.last_accessed = datetime.utcnow()
        self.access_count += 1

@dataclass
class PerformanceMetric:
    """Performance metric tracking"""
    metric_type: MetricType
    value: float
    timestamp: datetime
    user_id: Optional[str] = None
    endpoint: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class IntelligentCache:
    """
    Intelligent cache with multiple strategies and adaptive behavior
    """
    
    def __init__(self, max_size: int = 10000, default_ttl: int = 3600):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.strategy_map: Dict[str, CacheStrategy] = {}
        self.access_patterns: Dict[str, List[datetime]] = defaultdict(list)
        self.lock = threading.RLock()
        self.stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "writes": 0
        }
        
        # Start background cleanup task
        self._cleanup_task = None
        self._start_cleanup_task()
    
    def _start_cleanup_task(self):
        """Start background cleanup task"""
        async def cleanup_expired():
            while True:
                try:
                    await asyncio.sleep(300)  # Clean every 5 minutes
                    self._cleanup_expired_entries()
                except Exception as e:
                    logging.error(f"Error in cache cleanup: {e}")
        
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(cleanup_expired())
    
    def _generate_key(self, namespace: str, key: str, params: Dict[str, Any] = None) -> str:
        """Generate cache key with namespace and parameters"""
        if params:
            param_str = json.dumps(params, sort_keys=True)
            param_hash = hashlib.md5(param_str.encode()).hexdigest()[:8]
            return f"{namespace}:{key}:{param_hash}"
        return f"{namespace}:{key}"
    
    def get(self, namespace: str, key: str, params: Dict[str, Any] = None) -> Optional[Any]:
        """Get value from cache"""
        cache_key = self._generate_key(namespace, key, params)
        
        with self.lock:
            entry = self.cache.get(cache_key)
            
            if entry is None:
                self.stats["misses"] += 1
                return None
            
            if entry.is_expired():
                del self.cache[cache_key]
                self.stats["misses"] += 1
                return None
            
            # Move to end (LRU)
            self.cache.move_to_end(cache_key)
            entry.access()
            self._track_access_pattern(cache_key)
            self.stats["hits"] += 1
            
            return entry.value
    
    def set(self, namespace: str, key: str, value: Any, 
           ttl: Optional[int] = None, params: Dict[str, Any] = None,
           strategy: CacheStrategy = CacheStrategy.LRU):
        """Set value in cache"""
        cache_key = self._generate_key(namespace, key, params)
        
        with self.lock:
            # Calculate size estimate
            size_bytes = len(pickle.dumps(value)) if value is not None else 0
            
            # Create cache entry
            entry = CacheEntry(
                key=cache_key,
                value=value,
                created_at=datetime.utcnow(),
                last_accessed=datetime.utcnow(),
                access_count=1,
                ttl_seconds=ttl or self.default_ttl,
                size_bytes=size_bytes
            )
            
            # Store strategy mapping
            self.strategy_map[cache_key] = strategy
            
            # Add to cache
            self.cache[cache_key] = entry
            self.cache.move_to_end(cache_key)
            self.stats["writes"] += 1
            
            # Evict if necessary
            self._evict_if_necessary()
    
    def invalidate(self, namespace: str, key: str = None, params: Dict[str, Any] = None):
        """Invalidate cache entries"""
        if key:
            cache_key = self._generate_key(namespace, key, params)
            with self.lock:
                self.cache.pop(cache_key, None)
        else:
            # Invalidate entire namespace
            with self.lock:
                keys_to_remove = [k for k in self.cache.keys() if k.startswith(f"{namespace}:")]
                for k in keys_to_remove:
                    self.cache.pop(k, None)
    
    def _evict_if_necessary(self):
        """Evict entries if cache is full"""
        while len(self.cache) > self.max_size:
            # Find best candidate for eviction
            evict_key = self._select_eviction_candidate()
            if evict_key:
                del self.cache[evict_key]
                self.stats["evictions"] += 1
    
    def _select_eviction_candidate(self) -> Optional[str]:
        """Select the best candidate for eviction using adaptive strategy"""
        if not self.cache:
            return None
        
        # Score entries for eviction (higher score = more likely to evict)
        scores = {}
        now = datetime.utcnow()
        
        for key, entry in self.cache.items():
            score = 0
            
            # Time since last access
            time_since_access = (now - entry.last_accessed).total_seconds()
            score += time_since_access / 3600  # Hours since access
            
            # Inverse of access frequency
            if entry.access_count > 0:
                score += 1 / entry.access_count
            
            # Size penalty for large entries
            score += entry.size_bytes / (1024 * 1024)  # MB
            
            # TTL consideration
            if entry.ttl_seconds:
                time_to_expire = entry.ttl_seconds - (now - entry.created_at).total_seconds()
                if time_to_expire < 300:  # Less than 5 minutes to expire
                    score += 10
            
            scores[key] = score
        
        # Return key with highest eviction score
        return max(scores.items(), key=lambda x: x[1])[0]
    
    def _cleanup_expired_entries(self):
        """Remove expired entries"""
        with self.lock:
            expired_keys = [
                key for key, entry in self.cache.items()
                if entry.is_expired()
            ]
            
            for key in expired_keys:
                del self.cache[key]
    
    def _track_access_pattern(self, key: str):
        """Track access patterns for adaptive caching"""
        now = datetime.utcnow()
        self.access_patterns[key].append(now)
        
        # Keep only recent access history (last 24 hours)
        cutoff = now - timedelta(hours=24)
        self.access_patterns[key] = [
            access_time for access_time in self.access_patterns[key]
            if access_time > cutoff
        ]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = self.stats["hits"] / total_requests if total_requests > 0 else 0
        
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hit_rate": round(hit_rate, 3),
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "evictions": self.stats["evictions"],
            "writes": self.stats["writes"]
        }

class BatchProcessor:
    """
    Batch processor for grouping similar operations
    """
    
    def __init__(self, batch_size: int = 50, flush_interval: float = 1.0):
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.batches: Dict[str, List[Any]] = defaultdict(list)
        self.processors: Dict[str, Callable] = {}
        self.last_flush: Dict[str, datetime] = {}
        self.lock = threading.Lock()
        
        # Start background flush task
        self._flush_task = None
        self._start_flush_task()
    
    def _start_flush_task(self):
        """Start background flush task"""
        async def flush_batches():
            while True:
                try:
                    await asyncio.sleep(self.flush_interval)
                    await self._flush_ready_batches()
                except Exception as e:
                    logging.error(f"Error in batch flush: {e}")
        
        if self._flush_task is None:
            self._flush_task = asyncio.create_task(flush_batches())
    
    def register_processor(self, batch_type: str, processor: Callable):
        """Register a batch processor function"""
        self.processors[batch_type] = processor
    
    def add_to_batch(self, batch_type: str, item: Any):
        """Add item to batch"""
        with self.lock:
            self.batches[batch_type].append(item)
            
            if batch_type not in self.last_flush:
                self.last_flush[batch_type] = datetime.utcnow()
            
            # Flush if batch is full
            if len(self.batches[batch_type]) >= self.batch_size:
                asyncio.create_task(self._flush_batch(batch_type))
    
    async def _flush_ready_batches(self):
        """Flush batches that are ready"""
        now = datetime.utcnow()
        
        with self.lock:
            ready_batches = []
            for batch_type, last_flush in self.last_flush.items():
                if (now - last_flush).total_seconds() >= self.flush_interval:
                    if self.batches[batch_type]:  # Only if there are items
                        ready_batches.append(batch_type)
        
        for batch_type in ready_batches:
            await self._flush_batch(batch_type)
    
    async def _flush_batch(self, batch_type: str):
        """Flush a specific batch"""
        with self.lock:
            items = self.batches[batch_type][:]
            self.batches[batch_type].clear()
            self.last_flush[batch_type] = datetime.utcnow()
        
        if items and batch_type in self.processors:
            try:
                processor = self.processors[batch_type]
                if asyncio.iscoroutinefunction(processor):
                    await processor(items)
                else:
                    processor(items)
            except Exception as e:
                logging.error(f"Error processing batch {batch_type}: {e}")

class PerformanceMonitor:
    """
    Performance monitoring and metrics collection
    """
    
    def __init__(self, max_metrics: int = 10000):
        self.max_metrics = max_metrics
        self.metrics: deque = deque(maxlen=max_metrics)
        self.aggregated_stats: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        self.alert_thresholds: Dict[MetricType, float] = {
            MetricType.RESPONSE_TIME: 5.0,      # 5 seconds
            MetricType.ERROR_RATE: 0.05,        # 5%
            MetricType.MEMORY_USAGE: 0.85,      # 85%
            MetricType.CACHE_HIT_RATE: 0.60     # 60%
        }
        self.lock = threading.Lock()
    
    def record_metric(self, metric_type: MetricType, value: float,
                     user_id: str = None, endpoint: str = None,
                     metadata: Dict[str, Any] = None):
        """Record a performance metric"""
        metric = PerformanceMetric(
            metric_type=metric_type,
            value=value,
            timestamp=datetime.utcnow(),
            user_id=user_id,
            endpoint=endpoint,
            metadata=metadata or {}
        )
        
        with self.lock:
            self.metrics.append(metric)
            self._update_aggregated_stats(metric)
            self._check_alerts(metric)
    
    def _update_aggregated_stats(self, metric: PerformanceMetric):
        """Update aggregated statistics"""
        key = f"{metric.metric_type.value}"
        if metric.endpoint:
            key += f":{metric.endpoint}"
        
        stats = self.aggregated_stats[key]
        stats["count"] += 1
        stats["sum"] += metric.value
        stats["avg"] = stats["sum"] / stats["count"]
        
        if "min" not in stats or metric.value < stats["min"]:
            stats["min"] = metric.value
        if "max" not in stats or metric.value > stats["max"]:
            stats["max"] = metric.value
    
    def _check_alerts(self, metric: PerformanceMetric):
        """Check if metric triggers alerts"""
        threshold = self.alert_thresholds.get(metric.metric_type)
        if threshold and metric.value > threshold:
            self._trigger_alert(metric, threshold)
    
    def _trigger_alert(self, metric: PerformanceMetric, threshold: float):
        """Trigger performance alert"""
        alert_message = (
            f"Performance Alert: {metric.metric_type.value} = {metric.value} "
            f"exceeds threshold {threshold}"
        )
        if metric.endpoint:
            alert_message += f" for endpoint {metric.endpoint}"
        
        logging.warning(alert_message)
    
    def get_stats(self, time_window: timedelta = None) -> Dict[str, Any]:
        """Get performance statistics"""
        cutoff = datetime.utcnow() - time_window if time_window else None
        
        with self.lock:
            relevant_metrics = [
                m for m in self.metrics
                if cutoff is None or m.timestamp > cutoff
            ]
        
        if not relevant_metrics:
            return {"message": "No metrics in specified time window"}
        
        # Group by metric type
        by_type = defaultdict(list)
        for metric in relevant_metrics:
            by_type[metric.metric_type.value].append(metric.value)
        
        stats = {}
        for metric_type, values in by_type.items():
            stats[metric_type] = {
                "count": len(values),
                "avg": sum(values) / len(values),
                "min": min(values),
                "max": max(values),
                "p95": self._percentile(values, 95),
                "p99": self._percentile(values, 99)
            }
        
        return {
            "time_window": str(time_window) if time_window else "all_time",
            "total_metrics": len(relevant_metrics),
            "stats": stats
        }
    
    def _percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile"""
        if not values:
            return 0
        
        sorted_values = sorted(values)
        index = (percentile / 100) * (len(sorted_values) - 1)
        
        if index.is_integer():
            return sorted_values[int(index)]
        else:
            lower = sorted_values[int(index)]
            upper = sorted_values[int(index) + 1]
            return lower + (upper - lower) * (index - int(index))

class PerformanceOptimizer:
    """
    Main performance optimizer that coordinates caching, batching, and monitoring
    """
    
    def __init__(self):
        self.cache = IntelligentCache(max_size=50000, default_ttl=3600)
        self.batch_processor = BatchProcessor(batch_size=100, flush_interval=2.0)
        self.monitor = PerformanceMonitor(max_metrics=50000)
        self.thread_pool = ThreadPoolExecutor(max_workers=4)
        
        self.logger = logging.getLogger(__name__)
        
        # Register batch processors
        self._register_batch_processors()
    
    def _register_batch_processors(self):
        """Register batch processors for common operations"""
        self.batch_processor.register_processor("interactions", self._process_interaction_batch)
        self.batch_processor.register_processor("analytics", self._process_analytics_batch)
        self.batch_processor.register_processor("metrics", self._process_metrics_batch)
    
    async def _process_interaction_batch(self, interactions: List[Dict[str, Any]]):
        """Process batch of interactions"""
        try:
            # Group by user for efficient processing
            by_user = defaultdict(list)
            for interaction in interactions:
                by_user[interaction.get("user_id", "unknown")].append(interaction)
            
            # Process each user's interactions
            for user_id, user_interactions in by_user.items():
                await self._process_user_interactions(user_id, user_interactions)
                
        except Exception as e:
            self.logger.error(f"Error processing interaction batch: {e}")
    
    async def _process_user_interactions(self, user_id: str, interactions: List[Dict[str, Any]]):
        """Process interactions for a specific user"""
        # Update user statistics
        total_interactions = len(interactions)
        successful_interactions = sum(1 for i in interactions if i.get("success", True))
        success_rate = successful_interactions / total_interactions if total_interactions > 0 else 0
        
        # Cache updated statistics
        stats_key = f"user_stats:{user_id}"
        cached_stats = self.cache.get("analytics", stats_key) or {}
        
        cached_stats.update({
            "last_batch_size": total_interactions,
            "last_success_rate": success_rate,
            "last_updated": datetime.utcnow().isoformat(),
            "total_batches": cached_stats.get("total_batches", 0) + 1
        })
        
        self.cache.set("analytics", stats_key, cached_stats, ttl=7200)  # 2 hours
    
    async def _process_analytics_batch(self, analytics: List[Dict[str, Any]]):
        """Process batch of analytics events"""
        try:
            # Aggregate analytics by type
            by_type = defaultdict(list)
            for event in analytics:
                event_type = event.get("type", "unknown")
                by_type[event_type].append(event)
            
            # Process each type
            for event_type, events in by_type.items():
                await self._process_analytics_type(event_type, events)
                
        except Exception as e:
            self.logger.error(f"Error processing analytics batch: {e}")
    
    async def _process_analytics_type(self, event_type: str, events: List[Dict[str, Any]]):
        """Process analytics events of a specific type"""
        aggregated = {
            "event_type": event_type,
            "count": len(events),
            "timestamp": datetime.utcnow().isoformat(),
            "sample_events": events[:5]  # Keep sample for debugging
        }
        
        # Cache aggregated analytics
        cache_key = f"analytics_agg:{event_type}:{datetime.utcnow().strftime('%Y%m%d_%H')}"
        self.cache.set("analytics", cache_key, aggregated, ttl=86400)  # 24 hours
    
    async def _process_metrics_batch(self, metrics: List[Dict[str, Any]]):
        """Process batch of metrics"""
        try:
            for metric_data in metrics:
                metric_type = MetricType(metric_data.get("type", "response_time"))
                value = metric_data.get("value", 0)
                
                self.monitor.record_metric(
                    metric_type=metric_type,
                    value=value,
                    user_id=metric_data.get("user_id"),
                    endpoint=metric_data.get("endpoint"),
                    metadata=metric_data.get("metadata", {})
                )
        except Exception as e:
            self.logger.error(f"Error processing metrics batch: {e}")
    
    def cache_with_warming(self, namespace: str, key: str, 
                          fetch_func: Callable, ttl: int = 3600,
                          params: Dict[str, Any] = None) -> Any:
        """Cache with intelligent warming"""
        # Try to get from cache first
        cached_value = self.cache.get(namespace, key, params)
        
        if cached_value is not None:
            # Record cache hit
            self.monitor.record_metric(MetricType.CACHE_HIT_RATE, 1.0)
            return cached_value
        
        # Cache miss - fetch value
        start_time = time.time()
        try:
            if asyncio.iscoroutinefunction(fetch_func):
                # Handle async functions
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Create task for async execution
                    future = asyncio.ensure_future(fetch_func())
                    value = None  # Will be set asynchronously
                else:
                    value = loop.run_until_complete(fetch_func())
            else:
                value = fetch_func()
            
            # Record fetch time
            fetch_time = time.time() - start_time
            self.monitor.record_metric(MetricType.RESPONSE_TIME, fetch_time)
            
            # Cache the value
            if value is not None:
                self.cache.set(namespace, key, value, ttl=ttl, params=params)
            
            # Record cache miss
            self.monitor.record_metric(MetricType.CACHE_HIT_RATE, 0.0)
            
            return value
            
        except Exception as e:
            self.logger.error(f"Error fetching data for cache: {e}")
            self.monitor.record_metric(MetricType.ERROR_RATE, 1.0)
            return None
    
    def batch_operation(self, batch_type: str, item: Any):
        """Add item to batch for processing"""
        self.batch_processor.add_to_batch(batch_type, item)
    
    def record_performance_metric(self, metric_type: MetricType, value: float,
                                user_id: str = None, endpoint: str = None,
                                metadata: Dict[str, Any] = None):
        """Record a performance metric"""
        self.monitor.record_metric(metric_type, value, user_id, endpoint, metadata)
    
    async def optimize_memory(self):
        """Perform memory optimization"""
        try:
            # Clean expired cache entries
            self.cache._cleanup_expired_entries()
            
            # Force garbage collection for expired metrics
            import gc
            collected = gc.collect()
            
            self.logger.info(f"Memory optimization completed. Collected {collected} objects.")
            
        except Exception as e:
            self.logger.error(f"Error during memory optimization: {e}")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        return {
            "cache": self.cache.get_stats(),
            "monitoring": self.monitor.get_stats(timedelta(hours=1)),  # Last hour
            "batch_processing": {
                "active_batches": len(self.batch_processor.batches),
                "total_processors": len(self.batch_processor.processors)
            },
            "system": {
                "thread_pool_active": self.thread_pool._threads,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    
    async def preload_user_data(self, user_id: str):
        """Preload commonly accessed user data"""
        try:
            # Preload user profile
            profile_key = f"profile:{user_id}"
            if not self.cache.get("users", profile_key):
                # Would fetch from database/service
                self.logger.info(f"Preloading profile for user {user_id}")
            
            # Preload recent interactions
            interactions_key = f"recent_interactions:{user_id}"
            if not self.cache.get("interactions", interactions_key):
                self.logger.info(f"Preloading interactions for user {user_id}")
            
            # Preload interface configuration
            config_key = f"interface_config:{user_id}"
            if not self.cache.get("configs", config_key):
                self.logger.info(f"Preloading interface config for user {user_id}")
                
        except Exception as e:
            self.logger.error(f"Error preloading user data: {e}")
    
    def cleanup(self):
        """Cleanup resources"""
        try:
            if hasattr(self.cache, '_cleanup_task') and self.cache._cleanup_task:
                self.cache._cleanup_task.cancel()
            
            if hasattr(self.batch_processor, '_flush_task') and self.batch_processor._flush_task:
                self.batch_processor._flush_task.cancel()
            
            self.thread_pool.shutdown(wait=True)
            
            self.logger.info("Performance optimizer cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")