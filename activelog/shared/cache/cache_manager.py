#!/usr/bin/env python3
"""
High-Performance Multi-Layer Caching System
Provides in-memory, Redis, and application-level caching with smart invalidation
"""

import asyncio
import json
import time
import hashlib
from typing import Any, Optional, Dict, List, Callable, Union
from dataclasses import dataclass, field
from contextlib import asynccontextmanager
from functools import wraps
import redis.asyncio as redis
import logging
from pathlib import Path
import pickle
import zlib
from enum import Enum

logger = logging.getLogger(__name__)

class CacheStrategy(Enum):
    """Cache storage strategies"""
    MEMORY_ONLY = "memory"
    REDIS_ONLY = "redis"
    MULTI_LAYER = "multi_layer"  # Memory -> Redis -> Database
    WRITE_THROUGH = "write_through"
    WRITE_BEHIND = "write_behind"

@dataclass
class CacheConfig:
    """Cache configuration settings"""
    default_ttl: int = 3600  # 1 hour
    memory_max_size: int = 1000  # Maximum items in memory cache
    compression_threshold: int = 1024  # Compress items larger than 1KB
    serialize_complex: bool = True
    health_check_interval: int = 60
    metrics_enabled: bool = True
    
@dataclass
class CacheMetrics:
    """Cache performance metrics"""
    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    memory_usage: int = 0
    redis_usage: int = 0
    compression_saves: int = 0
    
    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return (self.hits / total) if total > 0 else 0.0
    
    @property
    def miss_rate(self) -> float:
        return 1.0 - self.hit_rate

class MemoryCache:
    """High-performance in-memory LRU cache"""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.access_order: List[str] = []
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get item from memory cache"""
        async with self._lock:
            if key in self.cache:
                # Move to end (most recently used)
                self.access_order.remove(key)
                self.access_order.append(key)
                
                entry = self.cache[key]
                if entry['expires_at'] > time.time():
                    return entry['value']
                else:
                    # Expired, remove
                    del self.cache[key]
                    self.access_order.remove(key)
        
        return None
    
    async def set(self, key: str, value: Any, ttl: int = 3600):
        """Set item in memory cache with TTL"""
        async with self._lock:
            # Remove if already exists
            if key in self.cache:
                self.access_order.remove(key)
            
            # Add new entry
            self.cache[key] = {
                'value': value,
                'expires_at': time.time() + ttl,
                'created_at': time.time()
            }
            self.access_order.append(key)
            
            # Enforce size limit (LRU eviction)
            while len(self.cache) > self.max_size:
                oldest_key = self.access_order.pop(0)
                del self.cache[oldest_key]
    
    async def delete(self, key: str):
        """Delete item from memory cache"""
        async with self._lock:
            if key in self.cache:
                del self.cache[key]
                self.access_order.remove(key)
    
    async def clear(self):
        """Clear all items from memory cache"""
        async with self._lock:
            self.cache.clear()
            self.access_order.clear()
    
    async def size(self) -> int:
        """Get current cache size"""
        return len(self.cache)
    
    async def memory_usage(self) -> int:
        """Estimate memory usage in bytes"""
        try:
            import sys
            total = 0
            for key, entry in self.cache.items():
                total += sys.getsizeof(key)
                total += sys.getsizeof(entry['value'])
                total += sys.getsizeof(entry)
            return total
        except:
            return len(self.cache) * 1024  # Rough estimate

class CacheManager:
    """Advanced multi-layer cache manager"""
    
    def __init__(self, config: CacheConfig = None):
        self.config = config or CacheConfig()
        self.memory_cache = MemoryCache(self.config.memory_max_size)
        self.redis_client: Optional[redis.Redis] = None
        self.metrics = CacheMetrics()
        self._initialized = False
        self._health_task: Optional[asyncio.Task] = None
    
    async def initialize(self, redis_url: str = "redis://localhost:6379/1"):
        """Initialize cache manager with Redis connection"""
        if self._initialized:
            return
        
        try:
            # Initialize Redis connection
            self.redis_client = redis.from_url(
                redis_url,
                decode_responses=False,  # Handle binary data
                socket_keepalive=True,
                health_check_interval=30,
                retry_on_timeout=True
            )
            
            # Test Redis connection
            await self.redis_client.ping()
            logger.info("Cache manager initialized with Redis")
            
            # Start health check task
            if self.config.health_check_interval > 0:
                self._health_task = asyncio.create_task(self._health_check_loop())
            
            self._initialized = True
            
        except Exception as e:
            logger.warning(f"Failed to connect to Redis, using memory-only cache: {e}")
            self.redis_client = None
            self._initialized = True
    
    def _make_key(self, key: str, namespace: str = "default") -> str:
        """Generate namespaced cache key"""
        return f"activelog:cache:{namespace}:{key}"
    
    def _serialize(self, value: Any) -> bytes:
        """Serialize value for storage"""
        try:
            if isinstance(value, (str, int, float, bool)):
                data = json.dumps(value).encode('utf-8')
            else:
                data = pickle.dumps(value)
            
            # Compress if above threshold
            if len(data) > self.config.compression_threshold:
                compressed = zlib.compress(data)
                if len(compressed) < len(data):
                    self.metrics.compression_saves += len(data) - len(compressed)
                    return b'COMPRESSED:' + compressed
            
            return data
            
        except Exception as e:
            logger.error(f"Serialization error: {e}")
            raise
    
    def _deserialize(self, data: bytes) -> Any:
        """Deserialize value from storage"""
        try:
            if data.startswith(b'COMPRESSED:'):
                data = zlib.decompress(data[11:])
            
            # Try JSON first for simple types
            try:
                return json.loads(data.decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError):
                # Fall back to pickle for complex types
                return pickle.loads(data)
                
        except Exception as e:
            logger.error(f"Deserialization error: {e}")
            raise
    
    async def get(self, key: str, namespace: str = "default") -> Optional[Any]:
        """Get item from cache with multi-layer fallback"""
        if not self._initialized:
            await self.initialize()
        
        cache_key = self._make_key(key, namespace)
        
        # Try memory cache first
        try:
            value = await self.memory_cache.get(cache_key)
            if value is not None:
                self.metrics.hits += 1
                return value
        except Exception as e:
            logger.warning(f"Memory cache get error: {e}")
        
        # Try Redis cache
        if self.redis_client:
            try:
                data = await self.redis_client.get(cache_key)
                if data is not None:
                    value = self._deserialize(data)
                    
                    # Populate memory cache for next time
                    try:
                        await self.memory_cache.set(cache_key, value, self.config.default_ttl)
                    except:
                        pass  # Don't fail if memory cache fails
                    
                    self.metrics.hits += 1
                    return value
            except Exception as e:
                logger.warning(f"Redis cache get error: {e}")
        
        self.metrics.misses += 1
        return None
    
    async def set(self, key: str, value: Any, ttl: int = None, namespace: str = "default"):
        """Set item in cache with multi-layer storage"""
        if not self._initialized:
            await self.initialize()
        
        if ttl is None:
            ttl = self.config.default_ttl
        
        cache_key = self._make_key(key, namespace)
        
        # Set in memory cache
        try:
            await self.memory_cache.set(cache_key, value, ttl)
        except Exception as e:
            logger.warning(f"Memory cache set error: {e}")
        
        # Set in Redis cache
        if self.redis_client:
            try:
                data = self._serialize(value)
                await self.redis_client.setex(cache_key, ttl, data)
            except Exception as e:
                logger.warning(f"Redis cache set error: {e}")
        
        self.metrics.sets += 1
    
    async def delete(self, key: str, namespace: str = "default"):
        """Delete item from all cache layers"""
        cache_key = self._make_key(key, namespace)
        
        # Delete from memory cache
        try:
            await self.memory_cache.delete(cache_key)
        except Exception as e:
            logger.warning(f"Memory cache delete error: {e}")
        
        # Delete from Redis cache
        if self.redis_client:
            try:
                await self.redis_client.delete(cache_key)
            except Exception as e:
                logger.warning(f"Redis cache delete error: {e}")
        
        self.metrics.deletes += 1
    
    async def exists(self, key: str, namespace: str = "default") -> bool:
        """Check if key exists in cache"""
        value = await self.get(key, namespace)
        return value is not None
    
    async def clear_namespace(self, namespace: str = "default"):
        """Clear all items in a namespace"""
        if self.redis_client:
            pattern = self._make_key("*", namespace)
            try:
                keys = await self.redis_client.keys(pattern)
                if keys:
                    await self.redis_client.delete(*keys)
            except Exception as e:
                logger.warning(f"Redis namespace clear error: {e}")
        
        # For memory cache, we need to iterate and remove
        try:
            cache_prefix = self._make_key("", namespace)
            keys_to_remove = []
            
            for key in self.memory_cache.cache.keys():
                if key.startswith(cache_prefix):
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                await self.memory_cache.delete(key)
                
        except Exception as e:
            logger.warning(f"Memory cache namespace clear error: {e}")
    
    async def clear_all(self):
        """Clear all cache data"""
        try:
            await self.memory_cache.clear()
        except Exception as e:
            logger.warning(f"Memory cache clear error: {e}")
        
        if self.redis_client:
            try:
                pattern = "activelog:cache:*"
                keys = await self.redis_client.keys(pattern)
                if keys:
                    await self.redis_client.delete(*keys)
            except Exception as e:
                logger.warning(f"Redis cache clear error: {e}")
    
    def cached(self, ttl: int = None, namespace: str = "default", key_func: Callable = None):
        """Decorator for caching function results"""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Generate cache key
                if key_func:
                    cache_key = key_func(*args, **kwargs)
                else:
                    # Default key generation
                    key_parts = [func.__name__]
                    key_parts.extend(str(arg) for arg in args)
                    key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                    key_string = ":".join(key_parts)
                    cache_key = hashlib.md5(key_string.encode()).hexdigest()
                
                # Try to get from cache
                cached_result = await self.get(cache_key, namespace)
                if cached_result is not None:
                    return cached_result
                
                # Execute function and cache result
                result = await func(*args, **kwargs)
                await self.set(cache_key, result, ttl, namespace)
                
                return result
            return wrapper
        return decorator
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get cache performance metrics"""
        memory_usage = await self.memory_cache.memory_usage()
        memory_size = await self.memory_cache.size()
        
        redis_info = {}
        if self.redis_client:
            try:
                info = await self.redis_client.info("memory")
                redis_info = {
                    'used_memory': info.get('used_memory', 0),
                    'used_memory_human': info.get('used_memory_human', '0B'),
                    'connected_clients': info.get('connected_clients', 0)
                }
            except:
                pass
        
        return {
            'hits': self.metrics.hits,
            'misses': self.metrics.misses,
            'hit_rate': self.metrics.hit_rate,
            'miss_rate': self.metrics.miss_rate,
            'sets': self.metrics.sets,
            'deletes': self.metrics.deletes,
            'memory_cache_size': memory_size,
            'memory_cache_usage': memory_usage,
            'compression_saves': self.metrics.compression_saves,
            'redis_info': redis_info
        }
    
    async def health_check(self) -> Dict[str, bool]:
        """Check cache system health"""
        health = {}
        
        # Test memory cache
        try:
            test_key = f"health_check_{time.time()}"
            await self.memory_cache.set(test_key, "ok", 60)
            result = await self.memory_cache.get(test_key)
            health['memory_cache'] = result == "ok"
            await self.memory_cache.delete(test_key)
        except Exception as e:
            logger.error(f"Memory cache health check failed: {e}")
            health['memory_cache'] = False
        
        # Test Redis cache
        if self.redis_client:
            try:
                await self.redis_client.ping()
                health['redis_cache'] = True
            except Exception as e:
                logger.error(f"Redis cache health check failed: {e}")
                health['redis_cache'] = False
        else:
            health['redis_cache'] = False
        
        return health
    
    async def _health_check_loop(self):
        """Periodic health check background task"""
        while True:
            try:
                await asyncio.sleep(self.config.health_check_interval)
                health = await self.health_check()
                
                if not all(health.values()):
                    logger.warning(f"Cache health check failed: {health}")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check loop error: {e}")
    
    async def close(self):
        """Close cache manager and cleanup resources"""
        if self._health_task:
            self._health_task.cancel()
            try:
                await self._health_task
            except asyncio.CancelledError:
                pass
        
        if self.redis_client:
            await self.redis_client.close()
        
        await self.memory_cache.clear()
        self._initialized = False

# Global cache manager instance
cache_manager = CacheManager()

# Convenience functions
async def init_cache(redis_url: str = "redis://localhost:6379/1"):
    """Initialize global cache manager"""
    await cache_manager.initialize(redis_url)

async def cache_get(key: str, namespace: str = "default"):
    """Get item from cache"""
    return await cache_manager.get(key, namespace)

async def cache_set(key: str, value: Any, ttl: int = None, namespace: str = "default"):
    """Set item in cache"""
    await cache_manager.set(key, value, ttl, namespace)

async def cache_delete(key: str, namespace: str = "default"):
    """Delete item from cache"""
    await cache_manager.delete(key, namespace)

def cached(ttl: int = None, namespace: str = "default", key_func: Callable = None):
    """Decorator for caching function results"""
    return cache_manager.cached(ttl, namespace, key_func)

async def cache_metrics():
    """Get cache performance metrics"""
    return await cache_manager.get_metrics()

async def cache_health():
    """Check cache system health"""
    return await cache_manager.health_check()

async def close_cache():
    """Close cache manager"""
    await cache_manager.close()