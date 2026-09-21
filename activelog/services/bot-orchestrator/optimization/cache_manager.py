import asyncio
import logging
import time
import pickle
import json
import hashlib
from typing import Dict, Any, Optional, List, Union, Callable, TypeVar, Generic
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, OrderedDict
from enum import Enum
import threading
import weakref
import redis.asyncio as redis
from functools import wraps
import zlib
import orjson

logger = logging.getLogger(__name__)

T = TypeVar('T')

class CacheLevel(Enum):
    MEMORY = "memory"
    REDIS = "redis"
    DISK = "disk"
    HYBRID = "hybrid"

class EvictionPolicy(Enum):
    LRU = "lru"
    LFU = "lfu"
    TTL = "ttl"
    FIFO = "fifo"
    ADAPTIVE = "adaptive"

@dataclass
class CacheEntry(Generic[T]):
    key: str
    value: T
    timestamp: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    ttl_seconds: Optional[int] = None
    size_bytes: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        if self.ttl_seconds is None:
            return False
        return (datetime.now() - self.timestamp).total_seconds() > self.ttl_seconds
    
    def touch(self):
        self.last_accessed = datetime.now()
        self.access_count += 1

class CacheStats:
    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self.size_bytes = 0
        self.entry_count = 0
        self.average_access_time = 0.0
        self.hit_rate = 0.0
        self.lock = threading.Lock()
    
    def record_hit(self, access_time: float = 0.0):
        with self.lock:
            self.hits += 1
            self._update_hit_rate()
            self._update_average_access_time(access_time)
    
    def record_miss(self, access_time: float = 0.0):
        with self.lock:
            self.misses += 1
            self._update_hit_rate()
            self._update_average_access_time(access_time)
    
    def record_eviction(self):
        with self.lock:
            self.evictions += 1
    
    def update_size(self, size_bytes: int, entry_count: int):
        with self.lock:
            self.size_bytes = size_bytes
            self.entry_count = entry_count
    
    def _update_hit_rate(self):
        total = self.hits + self.misses
        self.hit_rate = (self.hits / total * 100) if total > 0 else 0.0
    
    def _update_average_access_time(self, access_time: float):
        total_ops = self.hits + self.misses
        if total_ops > 1:
            self.average_access_time = (
                (self.average_access_time * (total_ops - 1) + access_time) / total_ops
            )
        else:
            self.average_access_time = access_time
    
    def get_stats(self) -> Dict[str, Any]:
        with self.lock:
            return {
                "hits": self.hits,
                "misses": self.misses,
                "evictions": self.evictions,
                "hit_rate": self.hit_rate,
                "entry_count": self.entry_count,
                "size_bytes": self.size_bytes,
                "average_access_time": self.average_access_time
            }

class MemoryCache:
    def __init__(self, max_size: int = 1000, max_memory_mb: int = 100, 
                 eviction_policy: EvictionPolicy = EvictionPolicy.LRU):
        self.max_size = max_size
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.eviction_policy = eviction_policy
        self.cache = OrderedDict()
        self.stats = CacheStats()
        self.lock = threading.RLock()
        
        # For LFU
        self.frequency_tracker = defaultdict(int)
        
        # Background cleanup
        self.cleanup_interval = 300  # 5 minutes
        self.cleanup_task = None
        self.running = False
    
    async def start(self):
        self.running = True
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("Memory cache started")
    
    async def stop(self):
        self.running = False
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
        logger.info("Memory cache stopped")
    
    async def get(self, key: str) -> Optional[Any]:
        start_time = time.time()
        
        with self.lock:
            if key in self.cache:
                entry = self.cache[key]
                
                if entry.is_expired():
                    del self.cache[key]
                    self.frequency_tracker.pop(key, None)
                    access_time = time.time() - start_time
                    self.stats.record_miss(access_time)
                    return None
                
                # Update access pattern
                entry.touch()
                self.frequency_tracker[key] += 1
                
                # Move to end for LRU
                if self.eviction_policy == EvictionPolicy.LRU:
                    self.cache.move_to_end(key)
                
                access_time = time.time() - start_time
                self.stats.record_hit(access_time)
                return entry.value
            else:
                access_time = time.time() - start_time
                self.stats.record_miss(access_time)
                return None
    
    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None, 
                  metadata: Dict[str, Any] = None) -> bool:
        try:
            # Calculate size
            serialized = self._serialize_value(value)
            size_bytes = len(serialized)
            
            with self.lock:
                # Create entry
                entry = CacheEntry(
                    key=key,
                    value=value,
                    ttl_seconds=ttl_seconds,
                    size_bytes=size_bytes,
                    metadata=metadata or {}
                )
                
                # Check if we need to evict
                await self._ensure_space(size_bytes)
                
                # Store entry
                self.cache[key] = entry
                self.frequency_tracker[key] = 1
                
                # Move to end for LRU
                if self.eviction_policy == EvictionPolicy.LRU:
                    self.cache.move_to_end(key)
                
                self._update_stats()
                return True
                
        except Exception as e:
            logger.error(f"Failed to cache key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                self.frequency_tracker.pop(key, None)
                self._update_stats()
                return True
            return False
    
    async def clear(self):
        with self.lock:
            self.cache.clear()
            self.frequency_tracker.clear()
            self._update_stats()
    
    async def _ensure_space(self, needed_bytes: int):
        """Ensure there's enough space by evicting entries if necessary"""
        current_size = sum(entry.size_bytes for entry in self.cache.values())
        
        # Check size limits
        while (len(self.cache) >= self.max_size or 
               current_size + needed_bytes > self.max_memory_bytes) and self.cache:
            
            evicted_key = self._select_eviction_candidate()
            if evicted_key:
                evicted_entry = self.cache.pop(evicted_key)
                self.frequency_tracker.pop(evicted_key, None)
                current_size -= evicted_entry.size_bytes
                self.stats.record_eviction()
            else:
                break
    
    def _select_eviction_candidate(self) -> Optional[str]:
        """Select a candidate for eviction based on policy"""
        if not self.cache:
            return None
        
        if self.eviction_policy == EvictionPolicy.LRU:
            # First item in OrderedDict is least recently used
            return next(iter(self.cache))
        
        elif self.eviction_policy == EvictionPolicy.LFU:
            # Find least frequently used
            min_frequency = min(self.frequency_tracker.values())
            for key, freq in self.frequency_tracker.items():
                if freq == min_frequency and key in self.cache:
                    return key
        
        elif self.eviction_policy == EvictionPolicy.TTL:
            # Find earliest expiring item
            earliest_key = None
            earliest_time = None
            
            for key, entry in self.cache.items():
                if entry.ttl_seconds is not None:
                    expire_time = entry.timestamp + timedelta(seconds=entry.ttl_seconds)
                    if earliest_time is None or expire_time < earliest_time:
                        earliest_time = expire_time
                        earliest_key = key
            
            return earliest_key or next(iter(self.cache))
        
        elif self.eviction_policy == EvictionPolicy.FIFO:
            # First inserted (oldest timestamp)
            oldest_key = None
            oldest_time = None
            
            for key, entry in self.cache.items():
                if oldest_time is None or entry.timestamp < oldest_time:
                    oldest_time = entry.timestamp
                    oldest_key = key
            
            return oldest_key
        
        elif self.eviction_policy == EvictionPolicy.ADAPTIVE:
            # Adaptive algorithm considering age, frequency, and size
            best_candidate = None
            best_score = float('-inf')
            
            now = datetime.now()
            for key, entry in self.cache.items():
                age_hours = (now - entry.timestamp).total_seconds() / 3600
                frequency = self.frequency_tracker.get(key, 1)
                size_kb = entry.size_bytes / 1024
                
                # Higher score = better candidate for eviction
                score = (age_hours * 2) + (size_kb / 10) - (frequency * 5)
                
                if score > best_score:
                    best_score = score
                    best_candidate = key
            
            return best_candidate
        
        return next(iter(self.cache))
    
    def _serialize_value(self, value: Any) -> bytes:
        """Serialize value for size calculation"""
        try:
            return orjson.dumps(value)
        except Exception:
            return pickle.dumps(value)
    
    def _update_stats(self):
        """Update cache statistics"""
        total_size = sum(entry.size_bytes for entry in self.cache.values())
        self.stats.update_size(total_size, len(self.cache))
    
    async def _cleanup_loop(self):
        """Background cleanup of expired entries"""
        while self.running:
            try:
                await self._cleanup_expired()
                await asyncio.sleep(self.cleanup_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cache cleanup error: {e}")
                await asyncio.sleep(60)
    
    async def _cleanup_expired(self):
        """Remove expired entries"""
        with self.lock:
            expired_keys = [
                key for key, entry in self.cache.items() 
                if entry.is_expired()
            ]
            
            for key in expired_keys:
                del self.cache[key]
                self.frequency_tracker.pop(key, None)
            
            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
                self._update_stats()

class RedisCache:
    def __init__(self, redis_url: str = "redis://localhost:6379", 
                 key_prefix: str = "bot_orchestrator:"):
        self.redis_url = redis_url
        self.key_prefix = key_prefix
        self.redis_client = None
        self.stats = CacheStats()
        self.compression_threshold = 1024  # Compress values larger than 1KB
    
    async def start(self):
        try:
            self.redis_client = redis.from_url(self.redis_url)
            await self.redis_client.ping()
            logger.info("Redis cache connected")
        except Exception as e:
            logger.warning(f"Redis cache connection failed: {e}")
            self.redis_client = None
    
    async def stop(self):
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Redis cache disconnected")
    
    def _make_key(self, key: str) -> str:
        return f"{self.key_prefix}{key}"
    
    async def get(self, key: str) -> Optional[Any]:
        if not self.redis_client:
            return None
        
        start_time = time.time()
        
        try:
            redis_key = self._make_key(key)
            data = await self.redis_client.get(redis_key)
            
            if data is None:
                access_time = time.time() - start_time
                self.stats.record_miss(access_time)
                return None
            
            # Deserialize
            value = self._deserialize_value(data)
            
            access_time = time.time() - start_time
            self.stats.record_hit(access_time)
            return value
            
        except Exception as e:
            logger.error(f"Redis get error for key {key}: {e}")
            access_time = time.time() - start_time
            self.stats.record_miss(access_time)
            return None
    
    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        if not self.redis_client:
            return False
        
        try:
            redis_key = self._make_key(key)
            serialized_data = self._serialize_value(value)
            
            if ttl_seconds:
                await self.redis_client.setex(redis_key, ttl_seconds, serialized_data)
            else:
                await self.redis_client.set(redis_key, serialized_data)
            
            return True
            
        except Exception as e:
            logger.error(f"Redis set error for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        if not self.redis_client:
            return False
        
        try:
            redis_key = self._make_key(key)
            result = await self.redis_client.delete(redis_key)
            return result > 0
        except Exception as e:
            logger.error(f"Redis delete error for key {key}: {e}")
            return False
    
    async def clear(self, pattern: str = "*"):
        if not self.redis_client:
            return
        
        try:
            pattern_key = self._make_key(pattern)
            keys = await self.redis_client.keys(pattern_key)
            if keys:
                await self.redis_client.delete(*keys)
        except Exception as e:
            logger.error(f"Redis clear error: {e}")
    
    def _serialize_value(self, value: Any) -> bytes:
        """Serialize and optionally compress value"""
        try:
            data = orjson.dumps(value)
        except Exception:
            data = pickle.dumps(value)
        
        # Compress if above threshold
        if len(data) > self.compression_threshold:
            compressed = zlib.compress(data)
            # Only use compression if it actually reduces size
            if len(compressed) < len(data):
                return b"COMPRESSED:" + compressed
        
        return data
    
    def _deserialize_value(self, data: bytes) -> Any:
        """Deserialize and optionally decompress value"""
        # Check if compressed
        if data.startswith(b"COMPRESSED:"):
            data = zlib.decompress(data[11:])
        
        try:
            return orjson.loads(data)
        except Exception:
            return pickle.loads(data)

class HybridCache:
    def __init__(self, memory_cache: MemoryCache, redis_cache: Optional[RedisCache] = None):
        self.memory_cache = memory_cache
        self.redis_cache = redis_cache
        self.stats = CacheStats()
        self.promotion_threshold = 3  # Promote to memory after 3 hits in Redis
        self.hit_counters = defaultdict(int)
        self.lock = threading.Lock()
    
    async def start(self):
        await self.memory_cache.start()
        if self.redis_cache:
            await self.redis_cache.start()
        logger.info("Hybrid cache started")
    
    async def stop(self):
        await self.memory_cache.stop()
        if self.redis_cache:
            await self.redis_cache.stop()
        logger.info("Hybrid cache stopped")
    
    async def get(self, key: str) -> Optional[Any]:
        start_time = time.time()
        
        # Try memory cache first
        value = await self.memory_cache.get(key)
        if value is not None:
            access_time = time.time() - start_time
            self.stats.record_hit(access_time)
            return value
        
        # Try Redis cache
        if self.redis_cache:
            value = await self.redis_cache.get(key)
            if value is not None:
                # Track hits for potential promotion
                with self.lock:
                    self.hit_counters[key] += 1
                    
                    # Promote to memory if hit enough times
                    if self.hit_counters[key] >= self.promotion_threshold:
                        await self.memory_cache.set(key, value, ttl_seconds=3600)  # 1 hour in memory
                        del self.hit_counters[key]
                
                access_time = time.time() - start_time
                self.stats.record_hit(access_time)
                return value
        
        access_time = time.time() - start_time
        self.stats.record_miss(access_time)
        return None
    
    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None,
                  force_memory: bool = False, force_redis: bool = False) -> bool:
        success = True
        
        # Determine where to store based on value characteristics
        serialized_size = len(self._estimate_size(value))
        
        # Store in memory if small, frequently accessed, or forced
        if force_memory or (not force_redis and serialized_size < 10240):  # < 10KB
            success &= await self.memory_cache.set(key, value, ttl_seconds)
        
        # Store in Redis if available and not forcing memory-only
        if self.redis_cache and (force_redis or not force_memory):
            success &= await self.redis_cache.set(key, value, ttl_seconds)
        
        return success
    
    async def delete(self, key: str) -> bool:
        success = True
        
        success &= await self.memory_cache.delete(key)
        if self.redis_cache:
            success &= await self.redis_cache.delete(key)
        
        with self.lock:
            self.hit_counters.pop(key, None)
        
        return success
    
    async def clear(self):
        await self.memory_cache.clear()
        if self.redis_cache:
            await self.redis_cache.clear()
        
        with self.lock:
            self.hit_counters.clear()
    
    def _estimate_size(self, value: Any) -> bytes:
        """Quick size estimation"""
        try:
            return orjson.dumps(value)
        except Exception:
            return pickle.dumps(value)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get combined statistics"""
        return {
            "hybrid_stats": self.stats.get_stats(),
            "memory_stats": self.memory_cache.stats.get_stats(),
            "redis_stats": self.redis_cache.stats.get_stats() if self.redis_cache else None,
            "promotion_candidates": len(self.hit_counters)
        }

class SmartCacheDecorator:
    def __init__(self, cache_manager: 'CacheManager', 
                 cache_level: CacheLevel = CacheLevel.HYBRID,
                 ttl_seconds: Optional[int] = None,
                 key_prefix: str = ""):
        self.cache_manager = cache_manager
        self.cache_level = cache_level
        self.ttl_seconds = ttl_seconds
        self.key_prefix = key_prefix
    
    def __call__(self, func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = self._generate_key(func, args, kwargs)
            
            # Try to get from cache
            cached_result = await self.cache_manager.get(cache_key, self.cache_level)
            if cached_result is not None:
                return cached_result
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Cache result
            await self.cache_manager.set(
                cache_key, result, 
                cache_level=self.cache_level,
                ttl_seconds=self.ttl_seconds
            )
            
            return result
        
        return wrapper
    
    def _generate_key(self, func: Callable, args: tuple, kwargs: dict) -> str:
        """Generate a unique cache key for the function call"""
        func_name = f"{func.__module__}.{func.__name__}"
        
        # Create a hash of arguments
        arg_str = str(args) + str(sorted(kwargs.items()))
        arg_hash = hashlib.md5(arg_str.encode()).hexdigest()[:8]
        
        return f"{self.key_prefix}{func_name}:{arg_hash}"

class CacheManager:
    def __init__(self, config: Dict[str, Any] = None):
        config = config or {}
        
        # Initialize caches
        self.memory_cache = MemoryCache(
            max_size=config.get("memory_max_size", 1000),
            max_memory_mb=config.get("memory_max_mb", 100),
            eviction_policy=EvictionPolicy(config.get("memory_eviction", "lru"))
        )
        
        redis_config = config.get("redis", {})
        self.redis_cache = None
        if redis_config.get("enabled", False):
            self.redis_cache = RedisCache(
                redis_url=redis_config.get("url", "redis://localhost:6379"),
                key_prefix=redis_config.get("key_prefix", "bot_orchestrator:")
            )
        
        self.hybrid_cache = HybridCache(self.memory_cache, self.redis_cache)
        
        # Performance monitoring
        self.performance_monitor = CachePerformanceMonitor()
        
        # Cache warming
        self.cache_warmer = CacheWarmer(self)
        
        self.running = False
    
    async def start(self):
        """Start all cache components"""
        self.running = True
        
        await self.memory_cache.start()
        if self.redis_cache:
            await self.redis_cache.start()
        await self.hybrid_cache.start()
        
        await self.performance_monitor.start()
        await self.cache_warmer.start()
        
        logger.info("Cache Manager started")
    
    async def stop(self):
        """Stop all cache components"""
        self.running = False
        
        await self.cache_warmer.stop()
        await self.performance_monitor.stop()
        await self.hybrid_cache.stop()
        
        logger.info("Cache Manager stopped")
    
    async def get(self, key: str, cache_level: CacheLevel = CacheLevel.HYBRID) -> Optional[Any]:
        """Get value from specified cache level"""
        start_time = time.time()
        
        try:
            if cache_level == CacheLevel.MEMORY:
                result = await self.memory_cache.get(key)
            elif cache_level == CacheLevel.REDIS and self.redis_cache:
                result = await self.redis_cache.get(key)
            elif cache_level == CacheLevel.HYBRID:
                result = await self.hybrid_cache.get(key)
            else:
                result = await self.hybrid_cache.get(key)
            
            access_time = time.time() - start_time
            await self.performance_monitor.record_access(key, access_time, result is not None)
            
            return result
            
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return None
    
    async def set(self, key: str, value: Any, cache_level: CacheLevel = CacheLevel.HYBRID,
                  ttl_seconds: Optional[int] = None, **kwargs) -> bool:
        """Set value in specified cache level"""
        try:
            if cache_level == CacheLevel.MEMORY:
                return await self.memory_cache.set(key, value, ttl_seconds)
            elif cache_level == CacheLevel.REDIS and self.redis_cache:
                return await self.redis_cache.set(key, value, ttl_seconds)
            elif cache_level == CacheLevel.HYBRID:
                return await self.hybrid_cache.set(key, value, ttl_seconds, **kwargs)
            else:
                return await self.hybrid_cache.set(key, value, ttl_seconds, **kwargs)
                
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False
    
    async def delete(self, key: str, cache_level: CacheLevel = CacheLevel.HYBRID) -> bool:
        """Delete value from specified cache level"""
        try:
            if cache_level == CacheLevel.MEMORY:
                return await self.memory_cache.delete(key)
            elif cache_level == CacheLevel.REDIS and self.redis_cache:
                return await self.redis_cache.delete(key)
            elif cache_level == CacheLevel.HYBRID:
                return await self.hybrid_cache.delete(key)
            else:
                return await self.hybrid_cache.delete(key)
                
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False
    
    async def clear(self, cache_level: CacheLevel = CacheLevel.HYBRID):
        """Clear specified cache level"""
        try:
            if cache_level == CacheLevel.MEMORY:
                await self.memory_cache.clear()
            elif cache_level == CacheLevel.REDIS and self.redis_cache:
                await self.redis_cache.clear()
            elif cache_level == CacheLevel.HYBRID:
                await self.hybrid_cache.clear()
            else:
                await self.hybrid_cache.clear()
                
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
    
    def cache_decorator(self, cache_level: CacheLevel = CacheLevel.HYBRID,
                       ttl_seconds: Optional[int] = None, key_prefix: str = ""):
        """Create a cache decorator"""
        return SmartCacheDecorator(self, cache_level, ttl_seconds, key_prefix)
    
    async def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        stats = {}
        
        # Individual cache stats
        stats["memory"] = self.memory_cache.stats.get_stats()
        if self.redis_cache:
            stats["redis"] = self.redis_cache.stats.get_stats()
        stats["hybrid"] = self.hybrid_cache.get_stats()
        
        # Performance monitoring stats
        stats["performance"] = await self.performance_monitor.get_stats()
        
        # Cache warmer stats
        stats["cache_warmer"] = self.cache_warmer.get_stats()
        
        return stats

class CachePerformanceMonitor:
    def __init__(self):
        self.access_patterns = defaultdict(list)
        self.hot_keys = defaultdict(int)
        self.slow_operations = []
        self.lock = threading.Lock()
        self.monitoring_interval = 300  # 5 minutes
        self.monitoring_task = None
        self.running = False
    
    async def start(self):
        self.running = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Cache performance monitor started")
    
    async def stop(self):
        self.running = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        logger.info("Cache performance monitor stopped")
    
    async def record_access(self, key: str, access_time: float, hit: bool):
        """Record cache access for monitoring"""
        with self.lock:
            self.access_patterns[key].append({
                "timestamp": datetime.now(),
                "access_time": access_time,
                "hit": hit
            })
            
            # Track hot keys
            self.hot_keys[key] += 1
            
            # Track slow operations
            if access_time > 0.1:  # 100ms threshold
                self.slow_operations.append({
                    "key": key,
                    "access_time": access_time,
                    "timestamp": datetime.now()
                })
                
                # Keep only recent slow operations
                cutoff_time = datetime.now() - timedelta(hours=1)
                self.slow_operations = [
                    op for op in self.slow_operations 
                    if op["timestamp"] > cutoff_time
                ]
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get performance monitoring statistics"""
        with self.lock:
            # Calculate hot keys (top 10)
            hot_keys = sorted(self.hot_keys.items(), key=lambda x: x[1], reverse=True)[:10]
            
            # Calculate average access times
            total_accesses = sum(len(accesses) for accesses in self.access_patterns.values())
            if total_accesses > 0:
                total_time = sum(
                    sum(access["access_time"] for access in accesses)
                    for accesses in self.access_patterns.values()
                )
                avg_access_time = total_time / total_accesses
            else:
                avg_access_time = 0.0
            
            return {
                "hot_keys": hot_keys,
                "total_unique_keys": len(self.access_patterns),
                "total_accesses": total_accesses,
                "average_access_time": avg_access_time,
                "slow_operations_count": len(self.slow_operations),
                "slow_operations": self.slow_operations[-5:]  # Last 5
            }
    
    async def _monitoring_loop(self):
        """Background monitoring and analysis"""
        while self.running:
            try:
                await self._analyze_patterns()
                await asyncio.sleep(self.monitoring_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Performance monitoring error: {e}")
                await asyncio.sleep(60)
    
    async def _analyze_patterns(self):
        """Analyze access patterns and provide insights"""
        with self.lock:
            # Clean old access patterns
            cutoff_time = datetime.now() - timedelta(hours=24)
            
            for key in list(self.access_patterns.keys()):
                self.access_patterns[key] = [
                    access for access in self.access_patterns[key]
                    if access["timestamp"] > cutoff_time
                ]
                
                if not self.access_patterns[key]:
                    del self.access_patterns[key]
            
            # Log insights
            if self.slow_operations:
                logger.warning(f"Found {len(self.slow_operations)} slow cache operations in the last hour")
            
            # Suggest optimizations
            hot_key_threshold = 100
            very_hot_keys = [key for key, count in self.hot_keys.items() if count > hot_key_threshold]
            if very_hot_keys:
                logger.info(f"Hot keys detected (consider memory caching): {very_hot_keys[:5]}")

class CacheWarmer:
    def __init__(self, cache_manager: CacheManager):
        self.cache_manager = cache_manager
        self.warming_strategies = []
        self.warming_schedule = {}
        self.stats = {
            "keys_warmed": 0,
            "warming_time_total": 0.0,
            "last_warming": None
        }
        self.warming_task = None
        self.running = False
    
    async def start(self):
        self.running = True
        self.warming_task = asyncio.create_task(self._warming_loop())
        logger.info("Cache warmer started")
    
    async def stop(self):
        self.running = False
        if self.warming_task:
            self.warming_task.cancel()
            try:
                await self.warming_task
            except asyncio.CancelledError:
                pass
        logger.info("Cache warmer stopped")
    
    def add_warming_strategy(self, strategy_func: Callable, 
                           schedule_minutes: int = 60, enabled: bool = True):
        """Add a cache warming strategy"""
        strategy = {
            "func": strategy_func,
            "schedule_minutes": schedule_minutes,
            "enabled": enabled,
            "last_run": None,
            "run_count": 0
        }
        self.warming_strategies.append(strategy)
    
    async def warm_cache(self, keys_and_values: List[Tuple[str, Any]], 
                        cache_level: CacheLevel = CacheLevel.MEMORY,
                        ttl_seconds: Optional[int] = 3600):
        """Warm cache with specific key-value pairs"""
        start_time = time.time()
        warmed_count = 0
        
        for key, value in keys_and_values:
            try:
                success = await self.cache_manager.set(key, value, cache_level, ttl_seconds)
                if success:
                    warmed_count += 1
            except Exception as e:
                logger.error(f"Failed to warm cache key {key}: {e}")
        
        warming_time = time.time() - start_time
        self.stats["keys_warmed"] += warmed_count
        self.stats["warming_time_total"] += warming_time
        self.stats["last_warming"] = datetime.now()
        
        logger.info(f"Cache warming completed: {warmed_count} keys in {warming_time:.2f}s")
    
    async def _warming_loop(self):
        """Background cache warming"""
        while self.running:
            try:
                await self._execute_warming_strategies()
                await asyncio.sleep(60)  # Check every minute
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cache warming error: {e}")
                await asyncio.sleep(300)
    
    async def _execute_warming_strategies(self):
        """Execute scheduled warming strategies"""
        now = datetime.now()
        
        for strategy in self.warming_strategies:
            if not strategy["enabled"]:
                continue
            
            # Check if it's time to run
            if strategy["last_run"] is None:
                should_run = True
            else:
                minutes_since_last = (now - strategy["last_run"]).total_seconds() / 60
                should_run = minutes_since_last >= strategy["schedule_minutes"]
            
            if should_run:
                try:
                    # Execute strategy
                    warming_data = await strategy["func"]()
                    if warming_data:
                        await self.warm_cache(warming_data)
                    
                    strategy["last_run"] = now
                    strategy["run_count"] += 1
                    
                except Exception as e:
                    logger.error(f"Cache warming strategy failed: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache warmer statistics"""
        return {
            **self.stats,
            "active_strategies": len([s for s in self.warming_strategies if s["enabled"]]),
            "total_strategies": len(self.warming_strategies)
        }