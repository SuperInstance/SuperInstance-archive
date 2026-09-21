"""
ActiveLog Project Memory - Redis Integration for Distributed Caching
High-performance distributed caching with Redis backend
"""

from typing import Dict, List, Any, Optional, Union, Tuple
import asyncio
import json
import pickle
import zlib
import hashlib
import time
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from enum import Enum
import redis.asyncio as redis
from redis.asyncio import Redis
import logging

class SerializationFormat(Enum):
    """Serialization formats for Redis storage"""
    JSON = "json"
    PICKLE = "pickle" 
    COMPRESSED_PICKLE = "compressed_pickle"
    STRING = "string"

class CacheNamespace(Enum):
    """Cache namespaces for organization"""
    CONCEPTS = "concepts"
    CONTEXTS = "contexts"
    BOT_SESSIONS = "bot_sessions"
    SEARCH_RESULTS = "search_results"
    PREDICTIONS = "predictions"
    DOCUMENTATION = "documentation"
    METRICS = "metrics"

@dataclass
class RedisConfig:
    """Redis connection configuration"""
    host: str = "localhost"
    port: int = 6379
    password: Optional[str] = None
    db: int = 0
    max_connections: int = 100
    socket_timeout: float = 5.0
    socket_connect_timeout: float = 5.0
    retry_on_timeout: bool = True
    health_check_interval: int = 30

@dataclass
class CacheEntry:
    """Enhanced cache entry for Redis"""
    key: str
    value: Any
    namespace: CacheNamespace
    ttl_seconds: Optional[int] = None
    compression_enabled: bool = True
    serialization_format: SerializationFormat = SerializationFormat.COMPRESSED_PICKLE
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    access_count: int = 0
    last_accessed: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)

class RedisDistributedCache:
    """
    High-performance distributed caching with Redis backend
    Supports compression, serialization, and intelligent key management
    """
    
    def __init__(self, config: RedisConfig):
        self.config = config
        self.redis_client: Optional[Redis] = None
        self.connection_pool = None
        self.is_connected = False
        
        # Performance tracking
        self.operation_stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "errors": 0
        }
        
        # Compression settings
        self.compression_threshold = 1024  # Compress if > 1KB
        self.compression_level = 6
        
        # Key expiration defaults
        self.default_ttl = {
            CacheNamespace.CONCEPTS: 3600,      # 1 hour
            CacheNamespace.CONTEXTS: 1800,      # 30 minutes
            CacheNamespace.BOT_SESSIONS: 7200,  # 2 hours
            CacheNamespace.SEARCH_RESULTS: 900, # 15 minutes
            CacheNamespace.PREDICTIONS: 600,    # 10 minutes
            CacheNamespace.DOCUMENTATION: 86400, # 24 hours
            CacheNamespace.METRICS: 300         # 5 minutes
        }
        
        # Batch operation settings
        self.batch_size = 100
        self.pipeline_threshold = 5
        
        self.logger = logging.getLogger(__name__)
    
    async def connect(self) -> bool:
        """Connect to Redis server"""
        try:
            # Create connection pool
            self.connection_pool = redis.ConnectionPool(
                host=self.config.host,
                port=self.config.port,
                password=self.config.password,
                db=self.config.db,
                max_connections=self.config.max_connections,
                socket_timeout=self.config.socket_timeout,
                socket_connect_timeout=self.config.socket_connect_timeout,
                retry_on_timeout=self.config.retry_on_timeout,
                health_check_interval=self.config.health_check_interval
            )
            
            # Create Redis client
            self.redis_client = Redis(connection_pool=self.connection_pool)
            
            # Test connection
            await self.redis_client.ping()
            
            self.is_connected = True
            self.logger.info(f"Connected to Redis at {self.config.host}:{self.config.port}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to Redis: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis_client:
            await self.redis_client.close()
            self.is_connected = False
            self.logger.info("Disconnected from Redis")
    
    def _build_key(self, namespace: CacheNamespace, key: str) -> str:
        """Build namespaced Redis key"""
        return f"activelog:memory:{namespace.value}:{key}"
    
    def _serialize_value(self, value: Any, format: SerializationFormat, 
                        compress: bool = True) -> bytes:
        """Serialize value for Redis storage"""
        
        if format == SerializationFormat.STRING:
            serialized = str(value).encode('utf-8')
        
        elif format == SerializationFormat.JSON:
            serialized = json.dumps(value, default=str).encode('utf-8')
        
        elif format == SerializationFormat.PICKLE:
            serialized = pickle.dumps(value)
        
        elif format == SerializationFormat.COMPRESSED_PICKLE:
            pickled = pickle.dumps(value)
            if compress and len(pickled) > self.compression_threshold:
                serialized = zlib.compress(pickled, self.compression_level)
            else:
                serialized = pickled
        
        else:
            raise ValueError(f"Unsupported serialization format: {format}")
        
        return serialized
    
    def _deserialize_value(self, data: bytes, format: SerializationFormat,
                          was_compressed: bool = True) -> Any:
        """Deserialize value from Redis storage"""
        
        if format == SerializationFormat.STRING:
            return data.decode('utf-8')
        
        elif format == SerializationFormat.JSON:
            return json.loads(data.decode('utf-8'))
        
        elif format == SerializationFormat.PICKLE:
            return pickle.loads(data)
        
        elif format == SerializationFormat.COMPRESSED_PICKLE:
            if was_compressed and len(data) > 0:
                try:
                    decompressed = zlib.decompress(data)
                    return pickle.loads(decompressed)
                except zlib.error:
                    # Not compressed, try direct pickle
                    return pickle.loads(data)
            else:
                return pickle.loads(data)
        
        else:
            raise ValueError(f"Unsupported serialization format: {format}")
    
    async def get(self, namespace: CacheNamespace, key: str,
                 default: Any = None) -> Any:
        """Get value from cache"""
        
        if not self.is_connected or not self.redis_client:
            return default
        
        try:
            redis_key = self._build_key(namespace, key)
            
            # Get value and metadata
            pipe = self.redis_client.pipeline()
            pipe.hgetall(redis_key)
            pipe.expire(redis_key, self.default_ttl.get(namespace, 3600))  # Refresh TTL
            
            results = await pipe.execute()
            entry_data = results[0]
            
            if not entry_data:
                self.operation_stats["misses"] += 1
                return default
            
            # Deserialize value
            value_data = entry_data.get(b'value')
            if not value_data:
                self.operation_stats["misses"] += 1
                return default
            
            # Get metadata
            format_str = entry_data.get(b'format', b'compressed_pickle').decode('utf-8')
            was_compressed = entry_data.get(b'compressed', b'true').decode('utf-8') == 'true'
            
            serialization_format = SerializationFormat(format_str)
            value = self._deserialize_value(value_data, serialization_format, was_compressed)
            
            # Update access statistics
            await self._update_access_stats(redis_key)
            
            self.operation_stats["hits"] += 1
            return value
            
        except Exception as e:
            self.logger.error(f"Redis get error for {namespace.value}:{key}: {e}")
            self.operation_stats["errors"] += 1
            return default
    
    async def set(self, namespace: CacheNamespace, key: str, value: Any,
                 ttl: Optional[int] = None, 
                 format: SerializationFormat = SerializationFormat.COMPRESSED_PICKLE) -> bool:
        """Set value in cache"""
        
        if not self.is_connected or not self.redis_client:
            return False
        
        try:
            redis_key = self._build_key(namespace, key)
            
            # Determine TTL
            effective_ttl = ttl or self.default_ttl.get(namespace, 3600)
            
            # Serialize value
            compress = format == SerializationFormat.COMPRESSED_PICKLE
            serialized_value = self._serialize_value(value, format, compress)
            
            # Prepare entry data
            entry_data = {
                'value': serialized_value,
                'format': format.value,
                'compressed': str(compress).lower(),
                'created_at': datetime.now(timezone.utc).isoformat(),
                'access_count': '0',
                'last_accessed': datetime.now(timezone.utc).isoformat(),
                'size_bytes': str(len(serialized_value))
            }
            
            # Set in Redis with TTL
            await self.redis_client.hset(redis_key, mapping=entry_data)
            await self.redis_client.expire(redis_key, effective_ttl)
            
            self.operation_stats["sets"] += 1
            return True
            
        except Exception as e:
            self.logger.error(f"Redis set error for {namespace.value}:{key}: {e}")
            self.operation_stats["errors"] += 1
            return False
    
    async def delete(self, namespace: CacheNamespace, key: str) -> bool:
        """Delete value from cache"""
        
        if not self.is_connected or not self.redis_client:
            return False
        
        try:
            redis_key = self._build_key(namespace, key)
            result = await self.redis_client.delete(redis_key)
            
            self.operation_stats["deletes"] += 1
            return result > 0
            
        except Exception as e:
            self.logger.error(f"Redis delete error for {namespace.value}:{key}: {e}")
            self.operation_stats["errors"] += 1
            return False
    
    async def exists(self, namespace: CacheNamespace, key: str) -> bool:
        """Check if key exists in cache"""
        
        if not self.is_connected or not self.redis_client:
            return False
        
        try:
            redis_key = self._build_key(namespace, key)
            result = await self.redis_client.exists(redis_key)
            return result > 0
            
        except Exception as e:
            self.logger.error(f"Redis exists error for {namespace.value}:{key}: {e}")
            return False
    
    async def get_multi(self, namespace: CacheNamespace, 
                       keys: List[str]) -> Dict[str, Any]:
        """Get multiple values efficiently using pipeline"""
        
        if not self.is_connected or not self.redis_client or not keys:
            return {}
        
        try:
            results = {}
            
            # Process in batches
            for i in range(0, len(keys), self.batch_size):
                batch_keys = keys[i:i + self.batch_size]
                batch_results = await self._get_batch(namespace, batch_keys)
                results.update(batch_results)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Redis get_multi error for {namespace.value}: {e}")
            return {}
    
    async def _get_batch(self, namespace: CacheNamespace, 
                        keys: List[str]) -> Dict[str, Any]:
        """Get a batch of keys using pipeline"""
        
        pipe = self.redis_client.pipeline()
        redis_keys = [self._build_key(namespace, key) for key in keys]
        
        # Queue all gets
        for redis_key in redis_keys:
            pipe.hgetall(redis_key)
        
        # Execute pipeline
        pipeline_results = await pipe.execute()
        
        # Process results
        results = {}
        for i, (original_key, entry_data) in enumerate(zip(keys, pipeline_results)):
            if entry_data and entry_data.get(b'value'):
                try:
                    # Deserialize
                    value_data = entry_data[b'value']
                    format_str = entry_data.get(b'format', b'compressed_pickle').decode('utf-8')
                    was_compressed = entry_data.get(b'compressed', b'true').decode('utf-8') == 'true'
                    
                    serialization_format = SerializationFormat(format_str)
                    value = self._deserialize_value(value_data, serialization_format, was_compressed)
                    results[original_key] = value
                    
                except Exception as e:
                    self.logger.error(f"Error deserializing {original_key}: {e}")
        
        return results
    
    async def set_multi(self, namespace: CacheNamespace, 
                       items: Dict[str, Any], ttl: Optional[int] = None) -> Dict[str, bool]:
        """Set multiple values efficiently using pipeline"""
        
        if not self.is_connected or not self.redis_client or not items:
            return {}
        
        try:
            results = {}
            effective_ttl = ttl or self.default_ttl.get(namespace, 3600)
            
            # Process in batches
            item_keys = list(items.keys())
            for i in range(0, len(item_keys), self.batch_size):
                batch_keys = item_keys[i:i + self.batch_size]
                batch_items = {k: items[k] for k in batch_keys}
                batch_results = await self._set_batch(namespace, batch_items, effective_ttl)
                results.update(batch_results)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Redis set_multi error for {namespace.value}: {e}")
            return {k: False for k in items.keys()}
    
    async def _set_batch(self, namespace: CacheNamespace, 
                        items: Dict[str, Any], ttl: int) -> Dict[str, bool]:
        """Set a batch of items using pipeline"""
        
        pipe = self.redis_client.pipeline()
        serialized_items = {}
        
        # Prepare all items for serialization
        for key, value in items.items():
            try:
                redis_key = self._build_key(namespace, key)
                serialized_value = self._serialize_value(
                    value, SerializationFormat.COMPRESSED_PICKLE, True
                )
                
                entry_data = {
                    'value': serialized_value,
                    'format': SerializationFormat.COMPRESSED_PICKLE.value,
                    'compressed': 'true',
                    'created_at': datetime.now(timezone.utc).isoformat(),
                    'access_count': '0',
                    'last_accessed': datetime.now(timezone.utc).isoformat(),
                    'size_bytes': str(len(serialized_value))
                }
                
                # Queue operations
                pipe.hset(redis_key, mapping=entry_data)
                pipe.expire(redis_key, ttl)
                
                serialized_items[key] = True
                
            except Exception as e:
                self.logger.error(f"Error preparing {key} for batch set: {e}")
                serialized_items[key] = False
        
        # Execute pipeline
        try:
            await pipe.execute()
            self.operation_stats["sets"] += len(serialized_items)
            return serialized_items
            
        except Exception as e:
            self.logger.error(f"Pipeline execution error: {e}")
            return {k: False for k in items.keys()}
    
    async def delete_multi(self, namespace: CacheNamespace, keys: List[str]) -> int:
        """Delete multiple keys efficiently"""
        
        if not self.is_connected or not self.redis_client or not keys:
            return 0
        
        try:
            redis_keys = [self._build_key(namespace, key) for key in keys]
            deleted_count = await self.redis_client.delete(*redis_keys)
            
            self.operation_stats["deletes"] += deleted_count
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"Redis delete_multi error for {namespace.value}: {e}")
            return 0
    
    async def clear_namespace(self, namespace: CacheNamespace) -> int:
        """Clear all keys in a namespace"""
        
        if not self.is_connected or not self.redis_client:
            return 0
        
        try:
            pattern = f"activelog:memory:{namespace.value}:*"
            keys = []
            
            # Scan for keys (memory-efficient for large datasets)
            async for key in self.redis_client.scan_iter(match=pattern, count=1000):
                keys.append(key)
                
                # Delete in batches
                if len(keys) >= 1000:
                    deleted = await self.redis_client.delete(*keys)
                    keys.clear()
            
            # Delete remaining keys
            if keys:
                deleted = await self.redis_client.delete(*keys)
            
            return len(keys)
            
        except Exception as e:
            self.logger.error(f"Redis clear_namespace error for {namespace.value}: {e}")
            return 0
    
    async def get_namespace_info(self, namespace: CacheNamespace) -> Dict[str, Any]:
        """Get information about a namespace"""
        
        if not self.is_connected or not self.redis_client:
            return {}
        
        try:
            pattern = f"activelog:memory:{namespace.value}:*"
            
            key_count = 0
            total_memory = 0
            total_access_count = 0
            oldest_created = None
            newest_created = None
            
            # Scan keys and collect info
            async for key in self.redis_client.scan_iter(match=pattern, count=100):
                key_count += 1
                
                # Get key info
                entry_data = await self.redis_client.hgetall(key)
                if entry_data:
                    # Memory usage
                    size_bytes = int(entry_data.get(b'size_bytes', b'0'))
                    total_memory += size_bytes
                    
                    # Access count
                    access_count = int(entry_data.get(b'access_count', b'0'))
                    total_access_count += access_count
                    
                    # Creation time
                    created_at_str = entry_data.get(b'created_at', b'').decode('utf-8')
                    if created_at_str:
                        created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                        if oldest_created is None or created_at < oldest_created:
                            oldest_created = created_at
                        if newest_created is None or created_at > newest_created:
                            newest_created = created_at
            
            return {
                "namespace": namespace.value,
                "key_count": key_count,
                "total_memory_bytes": total_memory,
                "total_memory_mb": total_memory / (1024 * 1024),
                "total_access_count": total_access_count,
                "average_accesses_per_key": total_access_count / max(1, key_count),
                "oldest_entry": oldest_created.isoformat() if oldest_created else None,
                "newest_entry": newest_created.isoformat() if newest_created else None
            }
            
        except Exception as e:
            self.logger.error(f"Error getting namespace info for {namespace.value}: {e}")
            return {"error": str(e)}
    
    async def _update_access_stats(self, redis_key: str):
        """Update access statistics for a key"""
        try:
            pipe = self.redis_client.pipeline()
            pipe.hincrby(redis_key, 'access_count', 1)
            pipe.hset(redis_key, 'last_accessed', datetime.now(timezone.utc).isoformat())
            await pipe.execute()
        except Exception:
            pass  # Non-critical operation
    
    async def optimize_memory(self, namespace: Optional[CacheNamespace] = None) -> Dict[str, Any]:
        """Optimize memory usage by removing expired/least accessed entries"""
        
        if not self.is_connected or not self.redis_client:
            return {"error": "Not connected to Redis"}
        
        try:
            optimization_results = {
                "expired_keys_removed": 0,
                "low_access_keys_removed": 0,
                "memory_freed_bytes": 0,
                "total_keys_processed": 0
            }
            
            # Determine namespaces to optimize
            namespaces_to_optimize = [namespace] if namespace else list(CacheNamespace)
            
            for ns in namespaces_to_optimize:
                pattern = f"activelog:memory:{ns.value}:*"
                keys_to_remove = []
                
                # Scan keys in namespace
                async for key in self.redis_client.scan_iter(match=pattern, count=100):
                    optimization_results["total_keys_processed"] += 1
                    
                    entry_data = await self.redis_client.hgetall(key)
                    if not entry_data:
                        continue
                    
                    # Check if key is expired or rarely accessed
                    access_count = int(entry_data.get(b'access_count', b'0'))
                    created_at_str = entry_data.get(b'created_at', b'').decode('utf-8')
                    
                    if created_at_str:
                        created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                        age_hours = (datetime.now(timezone.utc) - created_at).total_seconds() / 3600
                        
                        # Remove if very old with no recent access
                        if age_hours > 24 and access_count == 0:
                            keys_to_remove.append(key)
                            size_bytes = int(entry_data.get(b'size_bytes', b'0'))
                            optimization_results["memory_freed_bytes"] += size_bytes
                            optimization_results["low_access_keys_removed"] += 1
                
                # Remove identified keys in batches
                if keys_to_remove:
                    for i in range(0, len(keys_to_remove), self.batch_size):
                        batch = keys_to_remove[i:i + self.batch_size]
                        await self.redis_client.delete(*batch)
            
            return optimization_results
            
        except Exception as e:
            self.logger.error(f"Memory optimization error: {e}")
            return {"error": str(e)}
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        
        stats = {
            "connection": {
                "is_connected": self.is_connected,
                "host": self.config.host,
                "port": self.config.port,
                "db": self.config.db
            },
            "operations": self.operation_stats.copy(),
            "namespaces": {}
        }
        
        # Calculate hit rate
        total_operations = self.operation_stats["hits"] + self.operation_stats["misses"]
        if total_operations > 0:
            stats["hit_rate"] = self.operation_stats["hits"] / total_operations
        else:
            stats["hit_rate"] = 0.0
        
        # Get namespace info
        if self.is_connected:
            for namespace in CacheNamespace:
                try:
                    namespace_info = await self.get_namespace_info(namespace)
                    stats["namespaces"][namespace.value] = namespace_info
                except Exception as e:
                    stats["namespaces"][namespace.value] = {"error": str(e)}
        
        return stats
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on Redis connection"""
        
        health_status = {
            "healthy": False,
            "response_time_ms": None,
            "error": None,
            "redis_info": {}
        }
        
        if not self.is_connected or not self.redis_client:
            health_status["error"] = "Not connected to Redis"
            return health_status
        
        try:
            start_time = time.time()
            
            # Test basic operations
            test_key = "activelog:memory:health_check:test"
            await self.redis_client.set(test_key, "test_value", ex=60)
            result = await self.redis_client.get(test_key)
            await self.redis_client.delete(test_key)
            
            response_time = (time.time() - start_time) * 1000  # ms
            
            if result == b"test_value":
                health_status["healthy"] = True
                health_status["response_time_ms"] = response_time
                
                # Get Redis info
                redis_info = await self.redis_client.info()
                health_status["redis_info"] = {
                    "redis_version": redis_info.get("redis_version"),
                    "used_memory": redis_info.get("used_memory"),
                    "used_memory_human": redis_info.get("used_memory_human"),
                    "connected_clients": redis_info.get("connected_clients"),
                    "keyspace_hits": redis_info.get("keyspace_hits"),
                    "keyspace_misses": redis_info.get("keyspace_misses")
                }
            else:
                health_status["error"] = "Test operation failed"
                
        except Exception as e:
            health_status["error"] = str(e)
            self.logger.error(f"Redis health check failed: {e}")
        
        return health_status