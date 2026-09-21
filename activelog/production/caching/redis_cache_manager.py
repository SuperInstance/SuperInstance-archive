"""
Redis Cache Manager for ActiveLog Production

Comprehensive caching strategies including:
- Application-level caching
- Session management
- Rate limiting
- Distributed locking
- Cache invalidation patterns
"""

import json
import time
import hashlib
import logging
from typing import Any, Optional, Dict, List, Union, Callable
from contextlib import contextmanager
from functools import wraps
from dataclasses import dataclass
from enum import Enum
import redis
import redis.sentinel
from redis.exceptions import RedisError, LockError
import pickle

logger = logging.getLogger(__name__)

class CacheStrategy(Enum):
    """Cache eviction strategies"""
    LRU = "allkeys-lru"
    LFU = "allkeys-lfu" 
    RANDOM = "allkeys-random"
    TTL = "volatile-ttl"
    NONE = "noeviction"

@dataclass
class CacheConfig:
    """Cache configuration"""
    host: str = "redis-master"
    port: int = 6379
    password: Optional[str] = None
    db: int = 0
    max_connections: int = 50
    socket_timeout: int = 5
    socket_connect_timeout: int = 5
    retry_on_timeout: bool = True
    decode_responses: bool = True
    default_ttl: int = 3600  # 1 hour
    max_ttl: int = 86400     # 24 hours
    key_prefix: str = "activelog"
    use_sentinel: bool = True
    sentinel_hosts: List[tuple] = None
    sentinel_service: str = "mymaster"

class RedisConnectionManager:
    """Manages Redis connections with sentinel support and failover"""
    
    def __init__(self, config: CacheConfig):
        self.config = config
        self._redis_client = None
        self._sentinel = None
        self._connection_pool = None
        
    def _create_sentinel_connection(self) -> redis.Redis:
        """Create Redis connection through Sentinel"""
        try:
            self._sentinel = redis.sentinel.Sentinel(
                self.config.sentinel_hosts or [('redis-sentinel', 26379)],
                socket_timeout=self.config.socket_timeout,
                socket_connect_timeout=self.config.socket_connect_timeout,
            )
            
            master = self._sentinel.master_for(
                self.config.sentinel_service,
                socket_timeout=self.config.socket_timeout,
                socket_connect_timeout=self.config.socket_connect_timeout,
                password=self.config.password,
                db=self.config.db,
                decode_responses=self.config.decode_responses,
                max_connections=self.config.max_connections,
                retry_on_timeout=self.config.retry_on_timeout,
            )
            
            logger.info("Connected to Redis via Sentinel")
            return master
            
        except Exception as e:
            logger.error(f"Failed to connect via Sentinel: {e}")
            raise
    
    def _create_direct_connection(self) -> redis.Redis:
        """Create direct Redis connection"""
        try:
            return redis.Redis(
                host=self.config.host,
                port=self.config.port,
                password=self.config.password,
                db=self.config.db,
                socket_timeout=self.config.socket_timeout,
                socket_connect_timeout=self.config.socket_connect_timeout,
                decode_responses=self.config.decode_responses,
                max_connections=self.config.max_connections,
                retry_on_timeout=self.config.retry_on_timeout,
            )
        except Exception as e:
            logger.error(f"Failed to create direct Redis connection: {e}")
            raise
    
    def get_connection(self) -> redis.Redis:
        """Get Redis connection with automatic failover"""
        if self._redis_client is None:
            if self.config.use_sentinel:
                try:
                    self._redis_client = self._create_sentinel_connection()
                except Exception:
                    logger.warning("Sentinel connection failed, falling back to direct connection")
                    self._redis_client = self._create_direct_connection()
            else:
                self._redis_client = self._create_direct_connection()
        
        # Test connection
        try:
            self._redis_client.ping()
        except Exception:
            logger.warning("Redis connection lost, reconnecting...")
            self._redis_client = None
            return self.get_connection()
        
        return self._redis_client
    
    def close(self):
        """Close Redis connections"""
        if self._redis_client:
            self._redis_client.close()
        if self._sentinel:
            for sentinel in self._sentinel.sentinels:
                sentinel.close()

class CacheMetrics:
    """Tracks cache performance metrics"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.metrics_key = "cache:metrics"
    
    def record_hit(self, cache_type: str, key: str):
        """Record cache hit"""
        timestamp = int(time.time())
        pipe = self.redis.pipeline()
        pipe.hincrby(f"{self.metrics_key}:hits", cache_type, 1)
        pipe.hincrby(f"{self.metrics_key}:hits:daily", f"{cache_type}:{timestamp//86400}", 1)
        pipe.expire(f"{self.metrics_key}:hits:daily", 86400 * 7)  # Keep 7 days
        pipe.execute()
    
    def record_miss(self, cache_type: str, key: str):
        """Record cache miss"""
        timestamp = int(time.time())
        pipe = self.redis.pipeline()
        pipe.hincrby(f"{self.metrics_key}:misses", cache_type, 1)
        pipe.hincrby(f"{self.metrics_key}:misses:daily", f"{cache_type}:{timestamp//86400}", 1)
        pipe.expire(f"{self.metrics_key}:misses:daily", 86400 * 7)
        pipe.execute()
    
    def record_set(self, cache_type: str, key: str, size: int = 0):
        """Record cache set operation"""
        pipe = self.redis.pipeline()
        pipe.hincrby(f"{self.metrics_key}:sets", cache_type, 1)
        if size > 0:
            pipe.hincrby(f"{self.metrics_key}:size", cache_type, size)
        pipe.execute()
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get cache metrics"""
        try:
            pipe = self.redis.pipeline()
            pipe.hgetall(f"{self.metrics_key}:hits")
            pipe.hgetall(f"{self.metrics_key}:misses")
            pipe.hgetall(f"{self.metrics_key}:sets")
            pipe.hgetall(f"{self.metrics_key}:size")
            
            hits, misses, sets, sizes = pipe.execute()
            
            metrics = {}
            for cache_type in set(list(hits.keys()) + list(misses.keys())):
                hit_count = int(hits.get(cache_type, 0))
                miss_count = int(misses.get(cache_type, 0))
                total = hit_count + miss_count
                
                metrics[cache_type] = {
                    "hits": hit_count,
                    "misses": miss_count,
                    "hit_rate": hit_count / total if total > 0 else 0,
                    "total_requests": total,
                    "sets": int(sets.get(cache_type, 0)),
                    "size_bytes": int(sizes.get(cache_type, 0))
                }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to get cache metrics: {e}")
            return {}

class RedisCacheManager:
    """Main Redis cache manager with comprehensive caching strategies"""
    
    def __init__(self, config: CacheConfig):
        self.config = config
        self.connection_manager = RedisConnectionManager(config)
        self._redis = None
        self._metrics = None
    
    @property
    def redis(self) -> redis.Redis:
        """Get Redis connection"""
        if self._redis is None:
            self._redis = self.connection_manager.get_connection()
            self._metrics = CacheMetrics(self._redis)
        return self._redis
    
    @property
    def metrics(self) -> CacheMetrics:
        """Get cache metrics tracker"""
        if self._metrics is None:
            _ = self.redis  # Initialize connection and metrics
        return self._metrics
    
    def _make_key(self, key: str, namespace: str = "default") -> str:
        """Create namespaced cache key"""
        return f"{self.config.key_prefix}:{namespace}:{key}"
    
    def _serialize_value(self, value: Any) -> bytes:
        """Serialize value for storage"""
        try:
            # Try JSON first (human readable)
            return json.dumps(value).encode('utf-8')
        except (TypeError, ValueError):
            # Fall back to pickle for complex objects
            return b'pickle:' + pickle.dumps(value)
    
    def _deserialize_value(self, data: Union[str, bytes]) -> Any:
        """Deserialize value from storage"""
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        if data.startswith(b'pickle:'):
            return pickle.loads(data[7:])  # Remove 'pickle:' prefix
        else:
            return json.loads(data.decode('utf-8'))
    
    def get(self, key: str, namespace: str = "default") -> Optional[Any]:
        """Get value from cache"""
        cache_key = self._make_key(key, namespace)
        try:
            data = self.redis.get(cache_key)
            if data is not None:
                self.metrics.record_hit(namespace, key)
                return self._deserialize_value(data)
            else:
                self.metrics.record_miss(namespace, key)
                return None
        except Exception as e:
            logger.error(f"Cache get error for key {cache_key}: {e}")
            self.metrics.record_miss(namespace, key)
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None, 
            namespace: str = "default") -> bool:
        """Set value in cache"""
        cache_key = self._make_key(key, namespace)
        try:
            serialized = self._serialize_value(value)
            ttl = ttl or self.config.default_ttl
            ttl = min(ttl, self.config.max_ttl)  # Enforce max TTL
            
            result = self.redis.setex(cache_key, ttl, serialized)
            if result:
                self.metrics.record_set(namespace, key, len(serialized))
            return result
        except Exception as e:
            logger.error(f"Cache set error for key {cache_key}: {e}")
            return False
    
    def delete(self, key: str, namespace: str = "default") -> bool:
        """Delete value from cache"""
        cache_key = self._make_key(key, namespace)
        try:
            return self.redis.delete(cache_key) > 0
        except Exception as e:
            logger.error(f"Cache delete error for key {cache_key}: {e}")
            return False
    
    def exists(self, key: str, namespace: str = "default") -> bool:
        """Check if key exists in cache"""
        cache_key = self._make_key(key, namespace)
        try:
            return self.redis.exists(cache_key) > 0
        except Exception as e:
            logger.error(f"Cache exists error for key {cache_key}: {e}")
            return False
    
    def expire(self, key: str, ttl: int, namespace: str = "default") -> bool:
        """Set expiration on existing key"""
        cache_key = self._make_key(key, namespace)
        try:
            return self.redis.expire(cache_key, ttl)
        except Exception as e:
            logger.error(f"Cache expire error for key {cache_key}: {e}")
            return False
    
    def ttl(self, key: str, namespace: str = "default") -> int:
        """Get TTL for key"""
        cache_key = self._make_key(key, namespace)
        try:
            return self.redis.ttl(cache_key)
        except Exception as e:
            logger.error(f"Cache TTL error for key {cache_key}: {e}")
            return -1
    
    def mget(self, keys: List[str], namespace: str = "default") -> Dict[str, Any]:
        """Get multiple values from cache"""
        if not keys:
            return {}
        
        cache_keys = [self._make_key(key, namespace) for key in keys]
        try:
            values = self.redis.mget(cache_keys)
            result = {}
            
            for i, (key, value) in enumerate(zip(keys, values)):
                if value is not None:
                    result[key] = self._deserialize_value(value)
                    self.metrics.record_hit(namespace, key)
                else:
                    self.metrics.record_miss(namespace, key)
            
            return result
        except Exception as e:
            logger.error(f"Cache mget error: {e}")
            for key in keys:
                self.metrics.record_miss(namespace, key)
            return {}
    
    def mset(self, data: Dict[str, Any], ttl: Optional[int] = None, 
             namespace: str = "default") -> bool:
        """Set multiple values in cache"""
        if not data:
            return True
        
        ttl = ttl or self.config.default_ttl
        try:
            pipe = self.redis.pipeline()
            for key, value in data.items():
                cache_key = self._make_key(key, namespace)
                serialized = self._serialize_value(value)
                pipe.setex(cache_key, ttl, serialized)
                self.metrics.record_set(namespace, key, len(serialized))
            
            results = pipe.execute()
            return all(results)
        except Exception as e:
            logger.error(f"Cache mset error: {e}")
            return False
    
    def invalidate_pattern(self, pattern: str, namespace: str = "default") -> int:
        """Invalidate cache keys matching pattern"""
        cache_pattern = self._make_key(pattern, namespace)
        try:
            keys = self.redis.keys(cache_pattern)
            if keys:
                return self.redis.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Cache invalidate pattern error: {e}")
            return 0
    
    def increment(self, key: str, amount: int = 1, namespace: str = "counters") -> int:
        """Increment counter"""
        cache_key = self._make_key(key, namespace)
        try:
            return self.redis.incrby(cache_key, amount)
        except Exception as e:
            logger.error(f"Cache increment error for key {cache_key}: {e}")
            return 0
    
    def decrement(self, key: str, amount: int = 1, namespace: str = "counters") -> int:
        """Decrement counter"""
        return self.increment(key, -amount, namespace)
    
    @contextmanager
    def lock(self, key: str, timeout: int = 10, blocking_timeout: int = 5, 
             namespace: str = "locks"):
        """Distributed lock context manager"""
        cache_key = self._make_key(key, namespace)
        lock = self.redis.lock(cache_key, timeout=timeout, blocking_timeout=blocking_timeout)
        
        try:
            acquired = lock.acquire()
            if not acquired:
                raise LockError(f"Could not acquire lock for key: {key}")
            yield lock
        finally:
            try:
                lock.release()
            except LockError:
                pass  # Lock may have already expired
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """Get Redis memory usage information"""
        try:
            info = self.redis.info('memory')
            return {
                "used_memory": info.get('used_memory', 0),
                "used_memory_human": info.get('used_memory_human', '0B'),
                "used_memory_peak": info.get('used_memory_peak', 0),
                "used_memory_peak_human": info.get('used_memory_peak_human', '0B'),
                "maxmemory": info.get('maxmemory', 0),
                "maxmemory_human": info.get('maxmemory_human', '0B'),
                "memory_fragmentation_ratio": info.get('mem_fragmentation_ratio', 0),
            }
        except Exception as e:
            logger.error(f"Failed to get memory usage: {e}")
            return {}
    
    def flush_namespace(self, namespace: str) -> int:
        """Flush all keys in a namespace"""
        pattern = self._make_key("*", namespace)
        try:
            keys = self.redis.keys(pattern)
            if keys:
                return self.redis.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Failed to flush namespace {namespace}: {e}")
            return 0
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check on cache"""
        try:
            start_time = time.time()
            self.redis.ping()
            ping_time = time.time() - start_time
            
            info = self.redis.info()
            
            return {
                "status": "healthy",
                "ping_time_ms": round(ping_time * 1000, 2),
                "connected_clients": info.get('connected_clients', 0),
                "total_connections_received": info.get('total_connections_received', 0),
                "keyspace_hits": info.get('keyspace_hits', 0),
                "keyspace_misses": info.get('keyspace_misses', 0),
                "hit_rate": (info.get('keyspace_hits', 0) / 
                           max(info.get('keyspace_hits', 0) + info.get('keyspace_misses', 0), 1)),
                "uptime_seconds": info.get('uptime_in_seconds', 0),
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }

# Decorator for caching function results
def cached(ttl: int = 3600, namespace: str = "functions", 
           key_func: Optional[Callable] = None, cache_manager: Optional[RedisCacheManager] = None):
    """Decorator to cache function results"""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Default key generation
                args_str = str(args) + str(sorted(kwargs.items()))
                cache_key = f"{func.__name__}:{hashlib.md5(args_str.encode()).hexdigest()}"
            
            # Get cache manager
            if cache_manager is None:
                # Use global cache manager (should be initialized elsewhere)
                from .cache_config import get_cache_manager
                cm = get_cache_manager()
            else:
                cm = cache_manager
            
            # Try to get from cache
            result = cm.get(cache_key, namespace)
            if result is not None:
                return result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cm.set(cache_key, result, ttl, namespace)
            
            return result
        return wrapper
    return decorator

# Session management
class SessionManager:
    """Redis-based session management"""
    
    def __init__(self, cache_manager: RedisCacheManager, session_ttl: int = 3600):
        self.cache = cache_manager
        self.session_ttl = session_ttl
        self.namespace = "sessions"
    
    def create_session(self, user_id: str, session_data: Dict[str, Any]) -> str:
        """Create new session"""
        import uuid
        session_id = str(uuid.uuid4())
        
        session_info = {
            "user_id": user_id,
            "created_at": time.time(),
            "last_accessed": time.time(),
            "data": session_data
        }
        
        self.cache.set(session_id, session_info, self.session_ttl, self.namespace)
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data"""
        session_info = self.cache.get(session_id, self.namespace)
        if session_info:
            # Update last accessed time
            session_info["last_accessed"] = time.time()
            self.cache.set(session_id, session_info, self.session_ttl, self.namespace)
            return session_info
        return None
    
    def update_session(self, session_id: str, session_data: Dict[str, Any]) -> bool:
        """Update session data"""
        session_info = self.cache.get(session_id, self.namespace)
        if session_info:
            session_info["data"].update(session_data)
            session_info["last_accessed"] = time.time()
            return self.cache.set(session_id, session_info, self.session_ttl, self.namespace)
        return False
    
    def delete_session(self, session_id: str) -> bool:
        """Delete session"""
        return self.cache.delete(session_id, self.namespace)
    
    def extend_session(self, session_id: str, additional_ttl: int = None) -> bool:
        """Extend session TTL"""
        ttl = additional_ttl or self.session_ttl
        return self.cache.expire(session_id, ttl, self.namespace)

# Rate limiting
class RateLimiter:
    """Redis-based rate limiter"""
    
    def __init__(self, cache_manager: RedisCacheManager):
        self.cache = cache_manager
        self.namespace = "rate_limits"
    
    def is_allowed(self, key: str, limit: int, window: int) -> tuple[bool, Dict[str, Any]]:
        """Check if request is allowed under rate limit"""
        cache_key = f"{key}:{window}"
        
        try:
            with self.cache.redis.pipeline() as pipe:
                now = int(time.time())
                window_start = now - window
                
                # Clean old entries and count current requests
                pipe.multi()
                pipe.zremrangebyscore(self._make_key(cache_key), 0, window_start)
                pipe.zcard(self._make_key(cache_key))
                pipe.zadd(self._make_key(cache_key), {str(now): now})
                pipe.expire(self._make_key(cache_key), window + 1)
                
                results = pipe.execute()
                current_requests = results[1]
                
                allowed = current_requests < limit
                
                return allowed, {
                    "allowed": allowed,
                    "limit": limit,
                    "remaining": max(0, limit - current_requests - 1),
                    "reset_time": now + window,
                    "retry_after": window if not allowed else 0
                }
                
        except Exception as e:
            logger.error(f"Rate limit error for key {key}: {e}")
            # Fail open - allow request on error
            return True, {
                "allowed": True,
                "limit": limit,
                "remaining": limit - 1,
                "reset_time": int(time.time()) + window,
                "retry_after": 0,
                "error": str(e)
            }
    
    def _make_key(self, key: str) -> str:
        """Make rate limit key"""
        return self.cache._make_key(key, self.namespace)

# Global cache manager instance
_cache_manager = None

def init_cache_manager(config: CacheConfig) -> RedisCacheManager:
    """Initialize global cache manager"""
    global _cache_manager
    _cache_manager = RedisCacheManager(config)
    return _cache_manager

def get_cache_manager() -> RedisCacheManager:
    """Get global cache manager"""
    if _cache_manager is None:
        raise RuntimeError("Cache manager not initialized. Call init_cache_manager first.")
    return _cache_manager