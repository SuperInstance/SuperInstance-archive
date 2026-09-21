"""
Intelligent Memory Management System for Multi-Bot Environment
Advanced memory optimization with profiling, caching, and automatic cleanup
"""

import asyncio
import gc
import logging
import psutil
import sys
import threading
import time
import weakref
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Set, Callable, Union
import json
import sqlite3
import uuid
from functools import lru_cache, wraps
import tracemalloc
import resource
import mmap
import pickle
import os
import tempfile

logger = logging.getLogger(__name__)


class MemoryPriority(Enum):
    """Memory priority levels for data retention"""
    CRITICAL = "critical"      # Never evict
    HIGH = "high"             # Evict only under pressure
    MEDIUM = "medium"         # Regular eviction candidate
    LOW = "low"              # First to evict
    TEMPORARY = "temporary"   # Short-lived data


class MemoryStrategy(Enum):
    """Memory optimization strategies"""
    CONSERVATIVE = "conservative"  # Keep more data in memory
    BALANCED = "balanced"         # Balance between memory and performance
    AGGRESSIVE = "aggressive"     # Minimize memory usage
    ADAPTIVE = "adaptive"         # Adapt based on system conditions


class CachePolicy(Enum):
    """Cache eviction policies"""
    LRU = "lru"                  # Least Recently Used
    LFU = "lfu"                  # Least Frequently Used
    FIFO = "fifo"               # First In First Out
    TTL = "ttl"                 # Time To Live
    SIZE_AWARE = "size_aware"   # Consider object size
    PRIORITY_BASED = "priority_based"  # Based on priority


@dataclass
class MemoryProfile:
    """Memory profile for a bot or system component"""
    entity_id: str
    entity_type: str  # "bot", "system", "task", "collaboration"
    
    # Current memory usage
    rss_memory: int  # Resident Set Size in bytes
    vms_memory: int  # Virtual Memory Size in bytes
    heap_memory: int # Heap memory usage
    
    # Memory breakdown
    cache_memory: int = 0
    buffer_memory: int = 0
    temp_data_memory: int = 0
    persistent_data_memory: int = 0
    
    # Memory statistics
    peak_memory: int = 0
    average_memory: float = 0.0
    memory_growth_rate: float = 0.0  # bytes per second
    
    # Memory events
    gc_count: int = 0
    oom_events: int = 0  # Out of memory events
    cache_hits: int = 0
    cache_misses: int = 0
    
    # Timestamps
    last_updated: datetime = field(default_factory=datetime.now)
    profile_start: datetime = field(default_factory=datetime.now)
    
    # Optimization metrics
    compression_ratio: float = 1.0
    serialization_efficiency: float = 1.0


@dataclass
class MemoryObject:
    """Tracked memory object with metadata"""
    object_id: str
    object_type: str
    size_bytes: int
    priority: MemoryPriority
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    ttl: Optional[timedelta] = None
    owner_id: Optional[str] = None
    serializable: bool = True
    compressed: bool = False
    
    def is_expired(self) -> bool:
        """Check if object has expired based on TTL"""
        if self.ttl is None:
            return False
        return datetime.now() - self.created_at > self.ttl


@dataclass
class MemoryAlert:
    """Memory-related alert"""
    alert_id: str
    alert_type: str
    severity: str
    entity_id: str
    message: str
    memory_usage: int
    threshold: int
    timestamp: datetime
    resolved: bool = False


class SmartCache:
    """Intelligent cache with multiple eviction policies and compression"""
    
    def __init__(
        self,
        max_size: int = 100 * 1024 * 1024,  # 100MB default
        policy: CachePolicy = CachePolicy.PRIORITY_BASED,
        enable_compression: bool = True,
        enable_serialization: bool = True
    ):
        self.max_size = max_size
        self.policy = policy
        self.enable_compression = enable_compression
        self.enable_serialization = enable_serialization
        
        # Storage
        self.cache: Dict[str, MemoryObject] = {}
        self.data_store: Dict[str, Any] = {}
        self.access_times: Dict[str, datetime] = {}
        self.access_counts: Dict[str, int] = defaultdict(int)
        
        # Statistics
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self.current_size = 0
        
        # Thread safety
        self.lock = threading.RLock()
    
    def get(self, key: str) -> Optional[Any]:
        """Get item from cache"""
        with self.lock:
            if key not in self.cache:
                self.misses += 1
                return None
            
            # Update access information
            self.hits += 1
            self.access_times[key] = datetime.now()
            self.access_counts[key] += 1
            self.cache[key].last_accessed = datetime.now()
            self.cache[key].access_count += 1
            
            # Return data (decompress if needed)
            data = self.data_store[key]
            if self.cache[key].compressed:
                data = self._decompress(data)
            
            return data
    
    def put(self, key: str, value: Any, priority: MemoryPriority = MemoryPriority.MEDIUM, ttl: Optional[timedelta] = None):
        """Put item in cache"""
        with self.lock:
            # Calculate object size
            size = self._calculate_size(value)
            
            # Compress if beneficial
            compressed = False
            if self.enable_compression and size > 1024:  # Compress objects > 1KB
                compressed_value = self._compress(value)
                if len(compressed_value) < size * 0.8:  # 20% compression benefit
                    value = compressed_value
                    size = len(compressed_value)
                    compressed = True
            
            # Create memory object
            mem_obj = MemoryObject(
                object_id=key,
                object_type=type(value).__name__,
                size_bytes=size,
                priority=priority,
                created_at=datetime.now(),
                last_accessed=datetime.now(),
                ttl=ttl,
                compressed=compressed
            )
            
            # Check if we need to evict
            while self.current_size + size > self.max_size and self.cache:
                self._evict_item()
            
            # Store the item
            self.cache[key] = mem_obj
            self.data_store[key] = value
            self.access_times[key] = datetime.now()
            self.access_counts[key] = 1
            self.current_size += size
    
    def remove(self, key: str) -> bool:
        """Remove item from cache"""
        with self.lock:
            if key not in self.cache:
                return False
            
            self.current_size -= self.cache[key].size_bytes
            del self.cache[key]
            del self.data_store[key]
            self.access_times.pop(key, None)
            self.access_counts.pop(key, None)
            return True
    
    def clear(self):
        """Clear all cache entries"""
        with self.lock:
            self.cache.clear()
            self.data_store.clear()
            self.access_times.clear()
            self.access_counts.clear()
            self.current_size = 0
    
    def cleanup_expired(self) -> int:
        """Remove expired items from cache"""
        with self.lock:
            expired_keys = [
                key for key, obj in self.cache.items()
                if obj.is_expired()
            ]
            
            for key in expired_keys:
                self.remove(key)
            
            return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests) if total_requests > 0 else 0
        
        return {
            "size": len(self.cache),
            "current_size_bytes": self.current_size,
            "max_size_bytes": self.max_size,
            "utilization": (self.current_size / self.max_size) if self.max_size > 0 else 0,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": hit_rate,
            "evictions": self.evictions
        }
    
    def _evict_item(self):
        """Evict an item based on the configured policy"""
        if not self.cache:
            return
        
        if self.policy == CachePolicy.LRU:
            # Evict least recently used
            lru_key = min(self.access_times.keys(), key=lambda k: self.access_times[k])
            self.remove(lru_key)
        
        elif self.policy == CachePolicy.LFU:
            # Evict least frequently used
            lfu_key = min(self.access_counts.keys(), key=lambda k: self.access_counts[k])
            self.remove(lfu_key)
        
        elif self.policy == CachePolicy.PRIORITY_BASED:
            # Evict based on priority (lowest first)
            priority_order = [MemoryPriority.TEMPORARY, MemoryPriority.LOW, MemoryPriority.MEDIUM, MemoryPriority.HIGH]
            
            for priority in priority_order:
                candidates = [key for key, obj in self.cache.items() if obj.priority == priority]
                if candidates:
                    # Among same priority, use LRU
                    victim_key = min(candidates, key=lambda k: self.access_times[k])
                    self.remove(victim_key)
                    break
        
        elif self.policy == CachePolicy.SIZE_AWARE:
            # Evict largest items first
            largest_key = max(self.cache.keys(), key=lambda k: self.cache[k].size_bytes)
            self.remove(largest_key)
        
        self.evictions += 1
    
    def _calculate_size(self, obj: Any) -> int:
        """Calculate memory size of object"""
        try:
            if hasattr(obj, '__sizeof__'):
                return sys.getsizeof(obj)
            return len(pickle.dumps(obj))
        except:
            return 1024  # Default estimate
    
    def _compress(self, obj: Any) -> bytes:
        """Compress object using gzip"""
        import gzip
        import pickle
        
        try:
            serialized = pickle.dumps(obj)
            return gzip.compress(serialized)
        except:
            return pickle.dumps(obj)
    
    def _decompress(self, compressed_data: bytes) -> Any:
        """Decompress object"""
        import gzip
        import pickle
        
        try:
            decompressed = gzip.decompress(compressed_data)
            return pickle.loads(decompressed)
        except:
            return pickle.loads(compressed_data)


class MemoryPool:
    """Memory pool for efficient allocation and reuse"""
    
    def __init__(self, object_type: type, initial_size: int = 100):
        self.object_type = object_type
        self.available: deque = deque()
        self.in_use: Set[id] = set()
        self.lock = threading.Lock()
        
        # Pre-allocate initial objects
        for _ in range(initial_size):
            obj = self._create_object()
            self.available.append(obj)
    
    def acquire(self) -> Any:
        """Acquire object from pool"""
        with self.lock:
            if self.available:
                obj = self.available.popleft()
                self.in_use.add(id(obj))
                return obj
            else:
                # Create new object if pool is empty
                obj = self._create_object()
                self.in_use.add(id(obj))
                return obj
    
    def release(self, obj: Any):
        """Release object back to pool"""
        with self.lock:
            obj_id = id(obj)
            if obj_id in self.in_use:
                self.in_use.remove(obj_id)
                # Reset object state if needed
                self._reset_object(obj)
                self.available.append(obj)
    
    def _create_object(self) -> Any:
        """Create new object instance"""
        return self.object_type()
    
    def _reset_object(self, obj: Any):
        """Reset object to initial state"""
        # Override in subclasses for specific reset logic
        pass
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics"""
        return {
            "available": len(self.available),
            "in_use": len(self.in_use),
            "total": len(self.available) + len(self.in_use)
        }


class MemoryManager:
    """Comprehensive memory management system for multi-bot environment"""
    
    def __init__(
        self,
        strategy: MemoryStrategy = MemoryStrategy.ADAPTIVE,
        memory_limit_mb: int = 2048,  # 2GB default
        gc_threshold: float = 0.8,    # Trigger GC at 80% memory usage
        alert_threshold: float = 0.9, # Alert at 90% memory usage
        db_path: str = "/home/activeloguser/activelog/data/memory_manager.db"
    ):
        self.strategy = strategy
        self.memory_limit_bytes = memory_limit_mb * 1024 * 1024
        self.gc_threshold = gc_threshold
        self.alert_threshold = alert_threshold
        self.db_path = db_path
        
        # Memory tracking
        self.memory_profiles: Dict[str, MemoryProfile] = {}
        self.memory_alerts: Dict[str, MemoryAlert] = {}
        self.tracked_objects: Dict[str, MemoryObject] = {}
        
        # Caches and pools
        self.caches: Dict[str, SmartCache] = {}
        self.memory_pools: Dict[type, MemoryPool] = {}
        
        # Background tasks
        self.running = False
        self.monitor_task = None
        self.gc_task = None
        self.cleanup_task = None
        
        # Statistics
        self.gc_collections = 0
        self.cache_compressions = 0
        self.memory_optimizations = 0
        
        # Thread safety
        self.lock = threading.RLock()
        
        # Initialize system
        self._init_database()
        self._setup_memory_tracing()
        self.start_memory_management()
    
    def _init_database(self):
        """Initialize memory management database"""
        with sqlite3.connect(self.db_path) as conn:
            # Memory profiles table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_profiles (
                    entity_id TEXT PRIMARY KEY,
                    entity_type TEXT NOT NULL,
                    profile_data TEXT NOT NULL,
                    last_updated TEXT NOT NULL
                )
            """)
            
            # Memory alerts table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_alerts (
                    alert_id TEXT PRIMARY KEY,
                    alert_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    message TEXT NOT NULL,
                    memory_usage INTEGER NOT NULL,
                    threshold_value INTEGER NOT NULL,
                    timestamp TEXT NOT NULL,
                    resolved BOOLEAN DEFAULT FALSE
                )
            """)
            
            # Memory events table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    entity_id TEXT,
                    memory_before INTEGER,
                    memory_after INTEGER,
                    event_data TEXT,
                    timestamp TEXT NOT NULL
                )
            """)
            
            # Create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_profiles_updated ON memory_profiles(last_updated)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON memory_alerts(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_timestamp ON memory_events(timestamp)")
    
    def _setup_memory_tracing(self):
        """Setup memory tracing for detailed profiling"""
        if not tracemalloc.is_tracing():
            tracemalloc.start(10)  # Store up to 10 frames
    
    def start_memory_management(self):
        """Start background memory management tasks"""
        if not self.running:
            self.running = True
            self.monitor_task = threading.Thread(target=self._memory_monitor, daemon=True)
            self.gc_task = threading.Thread(target=self._garbage_collector, daemon=True)
            self.cleanup_task = threading.Thread(target=self._cleanup_manager, daemon=True)
            
            self.monitor_task.start()
            self.gc_task.start()
            self.cleanup_task.start()
    
    def stop_memory_management(self):
        """Stop background tasks"""
        self.running = False
        if self.monitor_task:
            self.monitor_task.join(timeout=5)
        if self.gc_task:
            self.gc_task.join(timeout=5)
        if self.cleanup_task:
            self.cleanup_task.join(timeout=5)
    
    def register_entity(self, entity_id: str, entity_type: str) -> bool:
        """Register an entity for memory tracking"""
        try:
            profile = MemoryProfile(
                entity_id=entity_id,
                entity_type=entity_type,
                rss_memory=0,
                vms_memory=0,
                heap_memory=0
            )
            
            with self.lock:
                self.memory_profiles[entity_id] = profile
            
            self._persist_profile(profile)
            return True
            
        except Exception as e:
            logger.error(f"Error registering entity {entity_id}: {e}")
            return False
    
    def create_cache(
        self,
        cache_id: str,
        max_size: int = 50 * 1024 * 1024,  # 50MB default
        policy: CachePolicy = CachePolicy.PRIORITY_BASED
    ) -> SmartCache:
        """Create a new smart cache"""
        cache = SmartCache(
            max_size=max_size,
            policy=policy,
            enable_compression=True,
            enable_serialization=True
        )
        
        self.caches[cache_id] = cache
        return cache
    
    def get_cache(self, cache_id: str) -> Optional[SmartCache]:
        """Get existing cache by ID"""
        return self.caches.get(cache_id)
    
    def create_memory_pool(self, object_type: type, initial_size: int = 100) -> MemoryPool:
        """Create memory pool for object reuse"""
        pool = MemoryPool(object_type, initial_size)
        self.memory_pools[object_type] = pool
        return pool
    
    def get_memory_pool(self, object_type: type) -> Optional[MemoryPool]:
        """Get existing memory pool"""
        return self.memory_pools.get(object_type)
    
    def track_object(
        self,
        obj: Any,
        object_id: str,
        priority: MemoryPriority = MemoryPriority.MEDIUM,
        ttl: Optional[timedelta] = None,
        owner_id: Optional[str] = None
    ):
        """Track a memory object"""
        mem_obj = MemoryObject(
            object_id=object_id,
            object_type=type(obj).__name__,
            size_bytes=sys.getsizeof(obj),
            priority=priority,
            created_at=datetime.now(),
            last_accessed=datetime.now(),
            ttl=ttl,
            owner_id=owner_id
        )
        
        self.tracked_objects[object_id] = mem_obj
    
    def update_memory_profile(self, entity_id: str) -> Optional[MemoryProfile]:
        """Update memory profile for an entity"""
        if entity_id not in self.memory_profiles:
            return None
        
        try:
            # Get current process memory info
            process = psutil.Process()
            memory_info = process.memory_info()
            
            profile = self.memory_profiles[entity_id]
            old_rss = profile.rss_memory
            
            # Update memory statistics
            profile.rss_memory = memory_info.rss
            profile.vms_memory = memory_info.vms
            
            # Calculate growth rate
            time_diff = (datetime.now() - profile.last_updated).total_seconds()
            if time_diff > 0:
                profile.memory_growth_rate = (profile.rss_memory - old_rss) / time_diff
            
            # Update peak memory
            profile.peak_memory = max(profile.peak_memory, profile.rss_memory)
            
            # Calculate average memory
            total_time = (datetime.now() - profile.profile_start).total_seconds()
            if total_time > 0:
                profile.average_memory = (profile.average_memory * (total_time - time_diff) + profile.rss_memory * time_diff) / total_time
            
            profile.last_updated = datetime.now()
            self._persist_profile(profile)
            
            # Check for alerts
            self._check_memory_alerts(entity_id, profile)
            
            return profile
            
        except Exception as e:
            logger.error(f"Error updating memory profile for {entity_id}: {e}")
            return None
    
    def optimize_memory(self, entity_id: str) -> Dict[str, Any]:
        """Optimize memory usage for an entity"""
        optimization_results = {
            "entity_id": entity_id,
            "actions_taken": [],
            "memory_before": 0,
            "memory_after": 0,
            "savings": 0
        }
        
        try:
            # Get current memory usage
            profile = self.update_memory_profile(entity_id)
            if not profile:
                return optimization_results
            
            optimization_results["memory_before"] = profile.rss_memory
            
            # Apply optimization strategies based on current strategy
            if self.strategy in [MemoryStrategy.AGGRESSIVE, MemoryStrategy.ADAPTIVE]:
                # Aggressive cache cleanup
                for cache_id, cache in self.caches.items():
                    before_size = cache.current_size
                    expired_count = cache.cleanup_expired()
                    
                    if expired_count > 0:
                        optimization_results["actions_taken"].append(f"Cleaned {expired_count} expired items from {cache_id}")
                
                # Force garbage collection
                collected = self._force_garbage_collection()
                if collected > 0:
                    optimization_results["actions_taken"].append(f"Garbage collected {collected} objects")
            
            if self.strategy == MemoryStrategy.ADAPTIVE:
                # Adaptive optimizations based on memory pressure
                memory_pressure = profile.rss_memory / self.memory_limit_bytes
                
                if memory_pressure > 0.8:
                    # High memory pressure - aggressive cleanup
                    self._aggressive_cleanup()
                    optimization_results["actions_taken"].append("Applied aggressive cleanup")
                elif memory_pressure > 0.6:
                    # Medium pressure - moderate cleanup
                    self._moderate_cleanup()
                    optimization_results["actions_taken"].append("Applied moderate cleanup")
            
            # Update profile after optimization
            profile_after = self.update_memory_profile(entity_id)
            if profile_after:
                optimization_results["memory_after"] = profile_after.rss_memory
                optimization_results["savings"] = optimization_results["memory_before"] - optimization_results["memory_after"]
            
            self.memory_optimizations += 1
            
            # Record optimization event
            self._record_memory_event("optimization", entity_id, profile.rss_memory, profile_after.rss_memory if profile_after else 0, optimization_results)
            
        except Exception as e:
            logger.error(f"Error optimizing memory for {entity_id}: {e}")
            optimization_results["actions_taken"].append(f"Error: {str(e)}")
        
        return optimization_results
    
    def get_memory_statistics(self) -> Dict[str, Any]:
        """Get comprehensive memory statistics"""
        try:
            # System memory info
            system_memory = psutil.virtual_memory()
            process = psutil.Process()
            process_memory = process.memory_info()
            
            # Cache statistics
            cache_stats = {}
            total_cache_size = 0
            for cache_id, cache in self.caches.items():
                stats = cache.get_stats()
                cache_stats[cache_id] = stats
                total_cache_size += stats["current_size_bytes"]
            
            # Pool statistics
            pool_stats = {}
            for obj_type, pool in self.memory_pools.items():
                pool_stats[obj_type.__name__] = pool.get_stats()
            
            # Tracked objects summary
            tracked_summary = {
                "total_objects": len(self.tracked_objects),
                "total_size": sum(obj.size_bytes for obj in self.tracked_objects.values()),
                "by_priority": {}
            }
            
            for priority in MemoryPriority:
                priority_objects = [obj for obj in self.tracked_objects.values() if obj.priority == priority]
                tracked_summary["by_priority"][priority.value] = {
                    "count": len(priority_objects),
                    "size": sum(obj.size_bytes for obj in priority_objects)
                }
            
            return {
                "timestamp": datetime.now().isoformat(),
                "system_memory": {
                    "total": system_memory.total,
                    "available": system_memory.available,
                    "used": system_memory.used,
                    "percentage": system_memory.percent
                },
                "process_memory": {
                    "rss": process_memory.rss,
                    "vms": process_memory.vms,
                    "percentage": (process_memory.rss / system_memory.total) * 100
                },
                "memory_limit": self.memory_limit_bytes,
                "memory_usage_percentage": (process_memory.rss / self.memory_limit_bytes) * 100,
                "caches": cache_stats,
                "total_cache_size": total_cache_size,
                "memory_pools": pool_stats,
                "tracked_objects": tracked_summary,
                "profiles_count": len(self.memory_profiles),
                "active_alerts": len([a for a in self.memory_alerts.values() if not a.resolved]),
                "statistics": {
                    "gc_collections": self.gc_collections,
                    "cache_compressions": self.cache_compressions,
                    "memory_optimizations": self.memory_optimizations
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting memory statistics: {e}")
            return {"error": str(e)}
    
    def get_memory_profile(self, entity_id: str) -> Optional[MemoryProfile]:
        """Get memory profile for an entity"""
        self.update_memory_profile(entity_id)
        return self.memory_profiles.get(entity_id)
    
    def get_memory_alerts(self, entity_id: Optional[str] = None, resolved: Optional[bool] = None) -> List[MemoryAlert]:
        """Get memory alerts with optional filtering"""
        alerts = list(self.memory_alerts.values())
        
        if entity_id:
            alerts = [a for a in alerts if a.entity_id == entity_id]
        
        if resolved is not None:
            alerts = [a for a in alerts if a.resolved == resolved]
        
        # Sort by timestamp (newest first)
        alerts.sort(key=lambda a: a.timestamp, reverse=True)
        
        return alerts
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve a memory alert"""
        if alert_id in self.memory_alerts:
            self.memory_alerts[alert_id].resolved = True
            self._persist_alert(self.memory_alerts[alert_id])
            return True
        return False
    
    def _memory_monitor(self):
        """Background memory monitoring task"""
        while self.running:
            try:
                # Update all entity profiles
                for entity_id in list(self.memory_profiles.keys()):
                    self.update_memory_profile(entity_id)
                
                # Check for memory pressure and trigger optimizations
                system_memory = psutil.virtual_memory()
                if system_memory.percent > 85:  # High system memory usage
                    self._handle_memory_pressure()
                
                # Sleep for monitoring interval
                time.sleep(30)  # Monitor every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in memory monitor: {e}")
                time.sleep(60)
    
    def _garbage_collector(self):
        """Background garbage collection task"""
        while self.running:
            try:
                # Check if GC should be triggered
                process = psutil.Process()
                memory_usage = process.memory_info().rss / self.memory_limit_bytes
                
                if memory_usage > self.gc_threshold:
                    collected = self._force_garbage_collection()
                    if collected > 0:
                        logger.info(f"Garbage collection freed {collected} objects")
                
                # Sleep between GC cycles
                time.sleep(120)  # Run GC every 2 minutes
                
            except Exception as e:
                logger.error(f"Error in garbage collector: {e}")
                time.sleep(300)
    
    def _cleanup_manager(self):
        """Background cleanup task"""
        while self.running:
            try:
                # Clean up expired cached objects
                for cache in self.caches.values():
                    cache.cleanup_expired()
                
                # Clean up expired tracked objects
                expired_objects = [
                    obj_id for obj_id, obj in self.tracked_objects.items()
                    if obj.is_expired()
                ]
                
                for obj_id in expired_objects:
                    del self.tracked_objects[obj_id]
                
                # Clean up old memory events
                self._cleanup_old_data()
                
                # Sleep between cleanup cycles
                time.sleep(600)  # Cleanup every 10 minutes
                
            except Exception as e:
                logger.error(f"Error in cleanup manager: {e}")
                time.sleep(600)
    
    def _check_memory_alerts(self, entity_id: str, profile: MemoryProfile):
        """Check for memory alerts and create them if needed"""
        memory_percentage = profile.rss_memory / self.memory_limit_bytes
        
        # High memory usage alert
        if memory_percentage > self.alert_threshold and not self._has_active_alert(entity_id, "high_memory"):
            alert = MemoryAlert(
                alert_id=str(uuid.uuid4()),
                alert_type="high_memory",
                severity="high",
                entity_id=entity_id,
                message=f"High memory usage: {memory_percentage:.1%} of limit",
                memory_usage=profile.rss_memory,
                threshold=int(self.memory_limit_bytes * self.alert_threshold),
                timestamp=datetime.now()
            )
            
            self.memory_alerts[alert.alert_id] = alert
            self._persist_alert(alert)
            logger.warning(f"Memory alert: {alert.message}")
        
        # Memory leak detection
        if profile.memory_growth_rate > 1024 * 1024:  # Growing > 1MB/sec
            if not self._has_active_alert(entity_id, "memory_leak"):
                alert = MemoryAlert(
                    alert_id=str(uuid.uuid4()),
                    alert_type="memory_leak",
                    severity="critical",
                    entity_id=entity_id,
                    message=f"Possible memory leak: growing at {profile.memory_growth_rate / 1024 / 1024:.2f} MB/s",
                    memory_usage=profile.rss_memory,
                    threshold=0,
                    timestamp=datetime.now()
                )
                
                self.memory_alerts[alert.alert_id] = alert
                self._persist_alert(alert)
                logger.critical(f"Memory leak alert: {alert.message}")
    
    def _has_active_alert(self, entity_id: str, alert_type: str) -> bool:
        """Check if entity has an active alert of given type"""
        return any(
            alert.entity_id == entity_id and alert.alert_type == alert_type and not alert.resolved
            for alert in self.memory_alerts.values()
        )
    
    def _handle_memory_pressure(self):
        """Handle high system memory pressure"""
        logger.warning("High memory pressure detected, applying optimizations")
        
        # Optimize all tracked entities
        for entity_id in self.memory_profiles.keys():
            self.optimize_memory(entity_id)
        
        # Force aggressive cleanup
        self._aggressive_cleanup()
        
        # Force garbage collection
        self._force_garbage_collection()
    
    def _aggressive_cleanup(self):
        """Perform aggressive memory cleanup"""
        # Clear low priority objects from caches
        for cache in self.caches.values():
            with cache.lock:
                low_priority_keys = [
                    key for key, obj in cache.cache.items()
                    if obj.priority in [MemoryPriority.LOW, MemoryPriority.TEMPORARY]
                ]
                
                for key in low_priority_keys:
                    cache.remove(key)
        
        # Remove expired tracked objects
        expired_objects = [
            obj_id for obj_id, obj in self.tracked_objects.items()
            if obj.is_expired() or obj.priority == MemoryPriority.TEMPORARY
        ]
        
        for obj_id in expired_objects:
            del self.tracked_objects[obj_id]
    
    def _moderate_cleanup(self):
        """Perform moderate memory cleanup"""
        # Clean up expired items
        for cache in self.caches.values():
            cache.cleanup_expired()
        
        # Remove temporary objects
        temp_objects = [
            obj_id for obj_id, obj in self.tracked_objects.items()
            if obj.priority == MemoryPriority.TEMPORARY
        ]
        
        for obj_id in temp_objects:
            del self.tracked_objects[obj_id]
    
    def _force_garbage_collection(self) -> int:
        """Force garbage collection and return number of collected objects"""
        before_count = len(gc.get_objects())
        collected = gc.collect()
        after_count = len(gc.get_objects())
        
        self.gc_collections += 1
        
        return before_count - after_count
    
    def _cleanup_old_data(self):
        """Clean up old database records"""
        cutoff_date = datetime.now() - timedelta(days=30)
        
        with sqlite3.connect(self.db_path) as conn:
            # Clean up old memory events
            conn.execute("DELETE FROM memory_events WHERE timestamp < ?", (cutoff_date.isoformat(),))
            
            # Clean up resolved alerts older than 7 days
            alert_cutoff = datetime.now() - timedelta(days=7)
            conn.execute("DELETE FROM memory_alerts WHERE resolved = TRUE AND timestamp < ?", (alert_cutoff.isoformat(),))
    
    def _record_memory_event(self, event_type: str, entity_id: str, memory_before: int, memory_after: int, event_data: Dict[str, Any]):
        """Record a memory management event"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO memory_events (event_type, entity_id, memory_before, memory_after, event_data, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                event_type,
                entity_id,
                memory_before,
                memory_after,
                json.dumps(event_data),
                datetime.now().isoformat()
            ))
    
    def _persist_profile(self, profile: MemoryProfile):
        """Persist memory profile to database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO memory_profiles (entity_id, entity_type, profile_data, last_updated)
                VALUES (?, ?, ?, ?)
            """, (
                profile.entity_id,
                profile.entity_type,
                json.dumps({
                    "rss_memory": profile.rss_memory,
                    "vms_memory": profile.vms_memory,
                    "heap_memory": profile.heap_memory,
                    "cache_memory": profile.cache_memory,
                    "buffer_memory": profile.buffer_memory,
                    "temp_data_memory": profile.temp_data_memory,
                    "persistent_data_memory": profile.persistent_data_memory,
                    "peak_memory": profile.peak_memory,
                    "average_memory": profile.average_memory,
                    "memory_growth_rate": profile.memory_growth_rate,
                    "gc_count": profile.gc_count,
                    "oom_events": profile.oom_events,
                    "cache_hits": profile.cache_hits,
                    "cache_misses": profile.cache_misses,
                    "profile_start": profile.profile_start.isoformat(),
                    "compression_ratio": profile.compression_ratio,
                    "serialization_efficiency": profile.serialization_efficiency
                }),
                profile.last_updated.isoformat()
            ))
    
    def _persist_alert(self, alert: MemoryAlert):
        """Persist memory alert to database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO memory_alerts 
                (alert_id, alert_type, severity, entity_id, message, memory_usage, threshold_value, timestamp, resolved)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                alert.alert_id,
                alert.alert_type,
                alert.severity,
                alert.entity_id,
                alert.message,
                alert.memory_usage,
                alert.threshold,
                alert.timestamp.isoformat(),
                alert.resolved
            ))


# Decorator for memory-efficient function caching
def memory_efficient_cache(maxsize: int = 128, ttl_seconds: Optional[int] = None):
    """Decorator for memory-efficient caching with TTL support"""
    def decorator(func):
        cache = SmartCache(
            max_size=maxsize * 1024,  # Approximate size
            policy=CachePolicy.LRU,
            enable_compression=True
        )
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key
            key = str(hash((args, tuple(sorted(kwargs.items())))))
            
            # Try to get from cache
            result = cache.get(key)
            if result is not None:
                return result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            ttl = timedelta(seconds=ttl_seconds) if ttl_seconds else None
            cache.put(key, result, ttl=ttl)
            
            return result
        
        # Attach cache for inspection
        wrapper._cache = cache
        return wrapper
    
    return decorator


# Context manager for memory tracking
class MemoryTracker:
    """Context manager for tracking memory usage of code blocks"""
    
    def __init__(self, description: str = "Memory tracking"):
        self.description = description
        self.start_memory = 0
        self.end_memory = 0
        self.peak_memory = 0
    
    def __enter__(self):
        if tracemalloc.is_tracing():
            current, peak = tracemalloc.get_traced_memory()
            self.start_memory = current
        else:
            process = psutil.Process()
            self.start_memory = process.memory_info().rss
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if tracemalloc.is_tracing():
            current, peak = tracemalloc.get_traced_memory()
            self.end_memory = current
            self.peak_memory = peak
        else:
            process = psutil.Process()
            self.end_memory = process.memory_info().rss
        
        memory_diff = self.end_memory - self.start_memory
        logger.info(f"{self.description}: Memory delta: {memory_diff:,} bytes, Peak: {self.peak_memory:,} bytes")
    
    def get_memory_usage(self) -> Dict[str, int]:
        """Get memory usage statistics"""
        return {
            "start_memory": self.start_memory,
            "end_memory": self.end_memory,
            "peak_memory": self.peak_memory,
            "memory_delta": self.end_memory - self.start_memory
        }


# Utility functions
def optimize_data_structure(data: Any) -> Any:
    """Optimize data structure for memory efficiency"""
    if isinstance(data, dict):
        # Use more memory-efficient dict implementation for large dicts
        if len(data) > 1000:
            # Could implement custom dict with better memory layout
            pass
        return {k: optimize_data_structure(v) for k, v in data.items()}
    
    elif isinstance(data, list):
        # Use array.array for numeric data
        if data and all(isinstance(x, (int, float)) for x in data):
            import array
            if all(isinstance(x, int) for x in data):
                return array.array('i', data)  # Integer array
            else:
                return array.array('f', data)  # Float array
        return [optimize_data_structure(item) for item in data]
    
    return data


def create_memory_manager(config: Optional[Dict[str, Any]] = None) -> MemoryManager:
    """Create memory manager with configuration"""
    if config is None:
        config = {}
    
    return MemoryManager(
        strategy=MemoryStrategy(config.get('strategy', 'adaptive')),
        memory_limit_mb=config.get('memory_limit_mb', 2048),
        gc_threshold=config.get('gc_threshold', 0.8),
        alert_threshold=config.get('alert_threshold', 0.9)
    )