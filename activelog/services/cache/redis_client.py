"""
Redis Client for ActiveLog
Provides centralized Redis connection management and caching utilities
"""

import redis
import json
import pickle
import hashlib
import time
import logging
from typing import Any, Optional, Dict, List, Union
from datetime import datetime, timedelta
from functools import wraps
import asyncio
import aioredis
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class RedisClient:
    """Centralized Redis client with connection pooling and utility methods"""
    
    def __init__(self, 
                 host: str = 'localhost',
                 port: int = 6379,
                 db: int = 0,
                 password: Optional[str] = None,
                 max_connections: int = 20,
                 decode_responses: bool = True):
        
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        
        # Create connection pool
        self.pool = redis.ConnectionPool(
            host=host,
            port=port,
            db=db,
            password=password,
            max_connections=max_connections,
            decode_responses=decode_responses,
            retry_on_timeout=True,
            socket_connect_timeout=5,
            socket_timeout=5
        )
        
        # Sync client
        self.client = redis.Redis(connection_pool=self.pool)
        
        # Async client (will be initialized when needed)
        self._async_client = None
        
        # Cache key prefixes
        self.prefixes = {
            'session': 'session:',
            'user': 'user:',
            'permissions': 'perms:',
            'metadata': 'meta:',
            'file': 'file:',
            'search': 'search:',
            'api_response': 'api:',
            'lock': 'lock:',
            'rate_limit': 'rate:',
            'analytics': 'analytics:',
            'embedding': 'embed:'
        }
        
        # Default TTL values (in seconds)
        self.default_ttl = {
            'session': 3600 * 24,  # 24 hours
            'user': 3600 * 2,      # 2 hours
            'permissions': 3600,    # 1 hour
            'metadata': 3600 * 6,   # 6 hours
            'file': 3600 * 12,     # 12 hours
            'search': 1800,        # 30 minutes
            'api_response': 300,    # 5 minutes
            'analytics': 3600,      # 1 hour
            'embedding': 3600 * 24  # 24 hours
        }
    
    async def get_async_client(self):
        """Get async Redis client"""
        if self._async_client is None:
            self._async_client = await aioredis.from_url(
                f"redis://{self.host}:{self.port}/{self.db}",
                password=self.password,
                encoding="utf-8",
                decode_responses=True,
                max_connections=20
            )
        return self._async_client
    
    def health_check(self) -> bool:
        """Check Redis connection health"""
        try:
            return self.client.ping()
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False
    
    def _make_key(self, prefix: str, key: str) -> str:
        """Create prefixed cache key"""
        return f"{self.prefixes.get(prefix, prefix)}{key}"
    
    def _serialize(self, value: Any) -> str:
        """Serialize value for Redis storage"""
        if isinstance(value, (str, int, float)):
            return str(value)
        elif isinstance(value, dict):
            return json.dumps(value)
        else:
            # Use pickle for complex objects
            return pickle.dumps(value).hex()
    
    def _deserialize(self, value: str, data_type: str = 'auto') -> Any:
        """Deserialize value from Redis"""
        if not value:
            return None
            
        if data_type == 'json':
            return json.loads(value)
        elif data_type == 'pickle':
            return pickle.loads(bytes.fromhex(value))
        elif data_type == 'auto':
            # Try to detect format
            try:
                return json.loads(value)
            except (json.JSONDecodeError, ValueError):
                try:
                    return pickle.loads(bytes.fromhex(value))
                except (ValueError, pickle.UnpicklingError):
                    return value
        return value
    
    # Basic cache operations
    def get(self, prefix: str, key: str, data_type: str = 'auto') -> Any:
        """Get value from cache"""
        try:
            cache_key = self._make_key(prefix, key)
            value = self.client.get(cache_key)
            return self._deserialize(value, data_type) if value else None
        except Exception as e:
            logger.error(f"Cache get error for {prefix}:{key}: {e}")
            return None
    
    def set(self, prefix: str, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache"""
        try:
            cache_key = self._make_key(prefix, key)
            serialized_value = self._serialize(value)
            
            if ttl is None:
                ttl = self.default_ttl.get(prefix, 3600)
            
            return self.client.setex(cache_key, ttl, serialized_value)
        except Exception as e:
            logger.error(f"Cache set error for {prefix}:{key}: {e}")
            return False
    
    def delete(self, prefix: str, key: str) -> bool:
        """Delete value from cache"""
        try:
            cache_key = self._make_key(prefix, key)
            return bool(self.client.delete(cache_key))
        except Exception as e:
            logger.error(f"Cache delete error for {prefix}:{key}: {e}")
            return False
    
    def exists(self, prefix: str, key: str) -> bool:
        """Check if key exists in cache"""
        try:
            cache_key = self._make_key(prefix, key)
            return bool(self.client.exists(cache_key))
        except Exception as e:
            logger.error(f"Cache exists error for {prefix}:{key}: {e}")
            return False
    
    def expire(self, prefix: str, key: str, ttl: int) -> bool:
        """Set expiration for existing key"""
        try:
            cache_key = self._make_key(prefix, key)
            return bool(self.client.expire(cache_key, ttl))
        except Exception as e:
            logger.error(f"Cache expire error for {prefix}:{key}: {e}")
            return False
    
    def ttl(self, prefix: str, key: str) -> int:
        """Get TTL for key"""
        try:
            cache_key = self._make_key(prefix, key)
            return self.client.ttl(cache_key)
        except Exception as e:
            logger.error(f"Cache TTL error for {prefix}:{key}: {e}")
            return -1
    
    # Bulk operations
    def mget(self, prefix: str, keys: List[str], data_type: str = 'auto') -> Dict[str, Any]:
        """Get multiple values from cache"""
        try:
            cache_keys = [self._make_key(prefix, key) for key in keys]
            values = self.client.mget(cache_keys)
            
            result = {}
            for i, key in enumerate(keys):
                value = values[i]
                result[key] = self._deserialize(value, data_type) if value else None
            
            return result
        except Exception as e:
            logger.error(f"Cache mget error for {prefix}: {e}")
            return {}
    
    def mset(self, prefix: str, mapping: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Set multiple values in cache"""
        try:
            cache_mapping = {}
            for key, value in mapping.items():
                cache_key = self._make_key(prefix, key)
                cache_mapping[cache_key] = self._serialize(value)
            
            # Use pipeline for atomic operation
            pipe = self.client.pipeline()
            pipe.mset(cache_mapping)
            
            if ttl is None:
                ttl = self.default_ttl.get(prefix, 3600)
            
            # Set expiration for each key
            for cache_key in cache_mapping.keys():
                pipe.expire(cache_key, ttl)
            
            pipe.execute()
            return True
        except Exception as e:
            logger.error(f"Cache mset error for {prefix}: {e}")
            return False
    
    def delete_pattern(self, pattern: str) -> int:
        """Delete keys matching pattern"""
        try:
            keys = self.client.keys(pattern)
            if keys:
                return self.client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Cache delete pattern error for {pattern}: {e}")
            return 0
    
    # Hash operations (for structured data)
    def hget(self, prefix: str, key: str, field: str) -> Any:
        """Get hash field value"""
        try:
            cache_key = self._make_key(prefix, key)
            value = self.client.hget(cache_key, field)
            return self._deserialize(value) if value else None
        except Exception as e:
            logger.error(f"Cache hget error for {prefix}:{key}.{field}: {e}")
            return None
    
    def hset(self, prefix: str, key: str, field: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set hash field value"""
        try:
            cache_key = self._make_key(prefix, key)
            serialized_value = self._serialize(value)
            
            result = self.client.hset(cache_key, field, serialized_value)
            
            if ttl is None:
                ttl = self.default_ttl.get(prefix, 3600)
            
            self.client.expire(cache_key, ttl)
            return bool(result)
        except Exception as e:
            logger.error(f"Cache hset error for {prefix}:{key}.{field}: {e}")
            return False
    
    def hgetall(self, prefix: str, key: str) -> Dict[str, Any]:
        """Get all hash fields"""
        try:
            cache_key = self._make_key(prefix, key)
            hash_data = self.client.hgetall(cache_key)
            
            result = {}
            for field, value in hash_data.items():
                result[field] = self._deserialize(value)
            
            return result
        except Exception as e:
            logger.error(f"Cache hgetall error for {prefix}:{key}: {e}")
            return {}
    
    def hmset(self, prefix: str, key: str, mapping: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Set multiple hash fields"""
        try:
            cache_key = self._make_key(prefix, key)
            
            serialized_mapping = {}
            for field, value in mapping.items():
                serialized_mapping[field] = self._serialize(value)
            
            result = self.client.hmset(cache_key, serialized_mapping)
            
            if ttl is None:
                ttl = self.default_ttl.get(prefix, 3600)
            
            self.client.expire(cache_key, ttl)
            return result
        except Exception as e:
            logger.error(f"Cache hmset error for {prefix}:{key}: {e}")
            return False
    
    # List operations
    def lpush(self, prefix: str, key: str, *values) -> int:
        """Push values to left of list"""
        try:
            cache_key = self._make_key(prefix, key)
            serialized_values = [self._serialize(v) for v in values]
            return self.client.lpush(cache_key, *serialized_values)
        except Exception as e:
            logger.error(f"Cache lpush error for {prefix}:{key}: {e}")
            return 0
    
    def rpush(self, prefix: str, key: str, *values) -> int:
        """Push values to right of list"""
        try:
            cache_key = self._make_key(prefix, key)
            serialized_values = [self._serialize(v) for v in values]
            return self.client.rpush(cache_key, *serialized_values)
        except Exception as e:
            logger.error(f"Cache rpush error for {prefix}:{key}: {e}")
            return 0
    
    def lrange(self, prefix: str, key: str, start: int = 0, end: int = -1) -> List[Any]:
        """Get list range"""
        try:
            cache_key = self._make_key(prefix, key)
            values = self.client.lrange(cache_key, start, end)
            return [self._deserialize(v) for v in values]
        except Exception as e:
            logger.error(f"Cache lrange error for {prefix}:{key}: {e}")
            return []
    
    def ltrim(self, prefix: str, key: str, start: int, end: int) -> bool:
        """Trim list to range"""
        try:
            cache_key = self._make_key(prefix, key)
            return self.client.ltrim(cache_key, start, end)
        except Exception as e:
            logger.error(f"Cache ltrim error for {prefix}:{key}: {e}")
            return False
    
    # Set operations
    def sadd(self, prefix: str, key: str, *values) -> int:
        """Add values to set"""
        try:
            cache_key = self._make_key(prefix, key)
            serialized_values = [self._serialize(v) for v in values]
            return self.client.sadd(cache_key, *serialized_values)
        except Exception as e:
            logger.error(f"Cache sadd error for {prefix}:{key}: {e}")
            return 0
    
    def smembers(self, prefix: str, key: str) -> set:
        """Get all set members"""
        try:
            cache_key = self._make_key(prefix, key)
            values = self.client.smembers(cache_key)
            return {self._deserialize(v) for v in values}
        except Exception as e:
            logger.error(f"Cache smembers error for {prefix}:{key}: {e}")
            return set()
    
    def sismember(self, prefix: str, key: str, value: Any) -> bool:
        """Check if value is in set"""
        try:
            cache_key = self._make_key(prefix, key)
            serialized_value = self._serialize(value)
            return bool(self.client.sismember(cache_key, serialized_value))
        except Exception as e:
            logger.error(f"Cache sismember error for {prefix}:{key}: {e}")
            return False
    
    # Utility methods
    def clear_prefix(self, prefix: str) -> int:
        """Clear all keys with given prefix"""
        pattern = f"{self.prefixes.get(prefix, prefix)}*"
        return self.delete_pattern(pattern)
    
    def get_info(self) -> Dict[str, Any]:
        """Get Redis server info"""
        try:
            return self.client.info()
        except Exception as e:
            logger.error(f"Failed to get Redis info: {e}")
            return {}
    
    def get_memory_usage(self, prefix: str, key: str) -> int:
        """Get memory usage of key"""
        try:
            cache_key = self._make_key(prefix, key)
            return self.client.memory_usage(cache_key) or 0
        except Exception as e:
            logger.error(f"Memory usage error for {prefix}:{key}: {e}")
            return 0


# Global Redis client instance
redis_client = None


def get_redis_client() -> RedisClient:
    """Get global Redis client instance"""
    global redis_client
    if redis_client is None:
        redis_client = RedisClient()
    return redis_client


def cache_result(prefix: str, key_func=None, ttl: Optional[int] = None):
    """Decorator for caching function results"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            client = get_redis_client()
            
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Default key generation
                key_parts = [func.__name__]
                key_parts.extend(str(arg) for arg in args)
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                cache_key = hashlib.md5(":".join(key_parts).encode()).hexdigest()
            
            # Try to get from cache
            cached_result = client.get(prefix, cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            client.set(prefix, cache_key, result, ttl)
            
            return result
        
        return wrapper
    return decorator


async def async_cache_result(prefix: str, key_func=None, ttl: Optional[int] = None):
    """Async decorator for caching function results"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            client = get_redis_client()
            async_client = await client.get_async_client()
            
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                key_parts = [func.__name__]
                key_parts.extend(str(arg) for arg in args)
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                cache_key = hashlib.md5(":".join(key_parts).encode()).hexdigest()
            
            # Try to get from cache
            full_key = client._make_key(prefix, cache_key)
            cached_value = await async_client.get(full_key)
            
            if cached_value:
                return client._deserialize(cached_value)
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            
            if ttl is None:
                ttl = client.default_ttl.get(prefix, 3600)
            
            serialized_result = client._serialize(result)
            await async_client.setex(full_key, ttl, serialized_result)
            
            return result
        
        return wrapper
    return decorator