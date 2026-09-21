#!/usr/bin/env python3
"""
Advanced Caching System with Intelligent Eviction

Implements sophisticated multi-tier caching with predictive warming,
distributed coherency, and adaptive eviction algorithms.
"""

import asyncio
import threading
import time
import json
import hashlib
import weakref
import struct
from typing import Dict, List, Any, Optional, Union, Callable, Set, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from collections import OrderedDict, defaultdict
import heapq
from concurrent.futures import ThreadPoolExecutor
import logging
import pickle
import gzip
import sqlite3
import aiofiles
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class CacheType(Enum):
    """Cache types for different use cases"""
    MEMORY = "memory"
    DISK = "disk"
    DISTRIBUTED = "distributed"
    HYBRID = "hybrid"


class EvictionPolicy(Enum):
    """Cache eviction algorithms"""
    LRU = "lru"          # Least Recently Used
    LFU = "lfu"          # Least Frequently Used
    ARC = "arc"          # Adaptive Replacement Cache
    CLOCK = "clock"      # Clock algorithm
    PREDICTIVE = "predictive"  # ML-based prediction
    TTL = "ttl"          # Time to Live
    SLRU = "slru"        # Segmented LRU
    W_TINYLFU = "w_tinylfu"  # Window TinyLFU


class CompressionType(Enum):
    """Compression algorithms for cache storage"""
    NONE = "none"
    GZIP = "gzip"
    LZ4 = "lz4"
    ZSTD = "zstd"


@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    key: str
    value: Any
    size: int
    created_at: float
    last_accessed: float
    access_count: int
    ttl: Optional[float] = None
    priority: int = 0
    compressed: bool = False
    encoding: str = 'utf-8'
    version: int = 1
    
    def is_expired(self) -> bool:
        """Check if entry is expired"""
        if self.ttl is None:
            return False
        return time.time() - self.created_at > self.ttl
    
    def serialize(self) -> bytes:
        """Serialize entry for storage"""
        data = asdict(self)
        data['value'] = pickle.dumps(self.value)
        return json.dumps(data).encode(self.encoding)
    
    @classmethod
    def deserialize(cls, data: bytes) -> 'CacheEntry':
        """Deserialize entry from storage"""
        json_data = json.loads(data.decode('utf-8'))
        json_data['value'] = pickle.loads(json_data['value'])
        return cls(**json_data)


class CacheStats:
    """Cache statistics tracking"""
    
    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self.insertions = 0
        self.updates = 0
        self.size_bytes = 0
        self.avg_access_time = 0.0
        self.hit_rate_history = []
        self._lock = threading.Lock()
    
    def record_hit(self, access_time: float = 0.0):
        with self._lock:
            self.hits += 1
            if access_time > 0:
                self.avg_access_time = (self.avg_access_time + access_time) / 2
    
    def record_miss(self):
        with self._lock:
            self.misses += 1
    
    def record_eviction(self):
        with self._lock:
            self.evictions += 1
    
    def record_insertion(self, size: int):
        with self._lock:
            self.insertions += 1
            self.size_bytes += size
    
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0
    
    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                'hits': self.hits,
                'misses': self.misses,
                'evictions': self.evictions,
                'insertions': self.insertions,
                'updates': self.updates,
                'size_bytes': self.size_bytes,
                'hit_rate': self.hit_rate(),
                'avg_access_time_ms': self.avg_access_time * 1000
            }


class AdaptiveReplacementCache:
    """
    ARC (Adaptive Replacement Cache) implementation
    Balances between recency and frequency
    """
    
    def __init__(self, capacity: int):
        self.capacity = capacity
        self.p = 0  # Target size for T1
        
        # Four lists: T1, T2, B1, B2
        self.t1 = OrderedDict()  # Recent entries
        self.t2 = OrderedDict()  # Frequent entries
        self.b1 = OrderedDict()  # Ghost entries from T1
        self.b2 = OrderedDict()  # Ghost entries from T2
        
        self._lock = threading.RLock()
    
    def _replace(self) -> str:
        """Replace algorithm - returns key to evict"""
        if self.t1 and (len(self.t1) > self.p or (self.t1 and len(self.b2) > 0)):
            # Remove from T1
            key = next(iter(self.t1))
            return key
        else:
            # Remove from T2
            key = next(iter(self.t2))
            return key
    
    def get(self, key: str) -> Optional[CacheEntry]:
        """Get item from cache"""
        with self._lock:
            # Check T1
            if key in self.t1:
                entry = self.t1.pop(key)
                self.t2[key] = entry
                return entry
            
            # Check T2
            if key in self.t2:
                entry = self.t2.pop(key)
                self.t2[key] = entry  # Move to end (most recent)
                return entry
            
            return None
    
    def put(self, key: str, entry: CacheEntry) -> Optional[str]:
        """Put item in cache, returns evicted key if any"""
        with self._lock:
            evicted_key = None
            
            # Case 1: x in T1 ∪ T2
            if key in self.t1 or key in self.t2:
                if key in self.t1:
                    self.t1.pop(key)
                    self.t2[key] = entry
                else:
                    self.t2[key] = entry
                return None
            
            # Case 2: x in B1
            if key in self.b1:
                self.p = min(self.capacity, self.p + max(1, len(self.b2) // len(self.b1)))
                self.b1.pop(key)
                
                if len(self.t1) + len(self.t2) >= self.capacity:
                    evicted_key = self._replace()
                    if evicted_key in self.t1:
                        removed = self.t1.pop(evicted_key)
                        self.b1[evicted_key] = None
                    else:
                        removed = self.t2.pop(evicted_key)
                        self.b2[evicted_key] = None
                
                self.t2[key] = entry
                return evicted_key
            
            # Case 3: x in B2
            if key in self.b2:
                self.p = max(0, self.p - max(1, len(self.b1) // len(self.b2)))
                self.b2.pop(key)
                
                if len(self.t1) + len(self.t2) >= self.capacity:
                    evicted_key = self._replace()
                    if evicted_key in self.t1:
                        removed = self.t1.pop(evicted_key)
                        self.b1[evicted_key] = None
                    else:
                        removed = self.t2.pop(evicted_key)
                        self.b2[evicted_key] = None
                
                self.t2[key] = entry
                return evicted_key
            
            # Case 4: x not in cache
            if len(self.t1) + len(self.b1) == self.capacity:
                if len(self.t1) < self.capacity:
                    self.b1.popitem(last=False)  # Remove LRU from B1
                else:
                    evicted_key = self.t1.popitem(last=False)[0]  # Remove LRU from T1
            
            elif len(self.t1) + len(self.b1) < self.capacity:
                total = len(self.t1) + len(self.t2) + len(self.b1) + len(self.b2)
                if total >= self.capacity:
                    if total >= 2 * self.capacity:
                        self.b2.popitem(last=False)  # Remove LRU from B2
                    
                    if len(self.t1) + len(self.t2) >= self.capacity:
                        evicted_key = self._replace()
                        if evicted_key in self.t1:
                            removed = self.t1.pop(evicted_key)
                            self.b1[evicted_key] = None
                        else:
                            removed = self.t2.pop(evicted_key)
                            self.b2[evicted_key] = None
            
            self.t1[key] = entry
            return evicted_key


class PredictiveEvictionPolicy:
    """
    ML-based predictive eviction using access patterns
    """
    
    def __init__(self, window_size: int = 1000):
        self.window_size = window_size
        self.access_patterns = defaultdict(list)
        self.model = None
        self.features_cache = {}
        self._lock = threading.Lock()
    
    def record_access(self, key: str, timestamp: float):
        """Record access pattern"""
        with self._lock:
            self.access_patterns[key].append(timestamp)
            if len(self.access_patterns[key]) > self.window_size:
                self.access_patterns[key].pop(0)
    
    def predict_next_access(self, key: str, current_time: float) -> float:
        """Predict when key will be accessed next"""
        with self._lock:
            if key not in self.access_patterns or len(self.access_patterns[key]) < 2:
                return float('inf')  # Unknown pattern
            
            accesses = self.access_patterns[key]
            
            # Simple linear prediction based on access intervals
            intervals = [accesses[i] - accesses[i-1] for i in range(1, len(accesses))]
            if not intervals:
                return float('inf')
            
            avg_interval = sum(intervals) / len(intervals)
            last_access = accesses[-1]
            
            predicted_next = last_access + avg_interval
            return max(0, predicted_next - current_time)
    
    def should_evict(self, key: str, current_time: float, threshold: float = 300.0) -> bool:
        """Determine if key should be evicted based on prediction"""
        next_access_time = self.predict_next_access(key, current_time)
        return next_access_time > threshold


class DistributedCacheCoordinator:
    """
    Coordinates distributed caching across multiple nodes
    """
    
    def __init__(self, node_id: str, cluster_nodes: List[str]):
        self.node_id = node_id
        self.cluster_nodes = cluster_nodes
        self.consistent_hash_ring = {}
        self.local_keys = set()
        self._setup_hash_ring()
    
    def _setup_hash_ring(self):
        """Setup consistent hashing ring"""
        virtual_nodes = 150  # Virtual nodes per physical node
        
        for node in self.cluster_nodes:
            for i in range(virtual_nodes):
                key = f"{node}:{i}"
                hash_val = int(hashlib.sha256(key.encode()).hexdigest()[:16], 16)
                self.consistent_hash_ring[hash_val] = node
    
    def get_node_for_key(self, key: str) -> str:
        """Get responsible node for a key"""
        if not self.consistent_hash_ring:
            return self.node_id
        
        key_hash = int(hashlib.sha256(key.encode()).hexdigest()[:16], 16)
        
        # Find first node with hash >= key_hash
        for hash_val in sorted(self.consistent_hash_ring.keys()):
            if hash_val >= key_hash:
                return self.consistent_hash_ring[hash_val]
        
        # Wrap around to first node
        return self.consistent_hash_ring[min(self.consistent_hash_ring.keys())]
    
    def is_local_key(self, key: str) -> bool:
        """Check if key should be stored locally"""
        return self.get_node_for_key(key) == self.node_id


class SmartCacheLayer:
    """
    Intelligent multi-tier cache with advanced eviction policies
    """
    
    def __init__(self, 
                 capacity: int = 10000,
                 eviction_policy: EvictionPolicy = EvictionPolicy.ARC,
                 cache_type: CacheType = CacheType.HYBRID,
                 compression: CompressionType = CompressionType.GZIP,
                 enable_predictive: bool = True,
                 disk_cache_path: Optional[str] = None):
        
        self.capacity = capacity
        self.eviction_policy = eviction_policy
        self.cache_type = cache_type
        self.compression = compression
        self.enable_predictive = enable_predictive
        
        # Initialize storage backends
        self.memory_cache: Dict[str, CacheEntry] = {}
        self.access_order = OrderedDict()
        self.frequency_counter = defaultdict(int)
        
        # ARC cache for advanced replacement
        if eviction_policy == EvictionPolicy.ARC:
            self.arc_cache = AdaptiveReplacementCache(capacity)
        
        # Predictive eviction
        if enable_predictive:
            self.predictive_policy = PredictiveEvictionPolicy()
        
        # Disk cache
        if disk_cache_path and cache_type in [CacheType.DISK, CacheType.HYBRID]:
            self.disk_cache_path = disk_cache_path
            self._setup_disk_cache()
        
        # Statistics and monitoring
        self.stats = CacheStats()
        self._lock = threading.RLock()
        
        # Background maintenance
        self._maintenance_task = None
        self._running = False
        
        # Cache warming predictions
        self.warming_predictions = defaultdict(float)
        
        logger.info(f"Initialized SmartCacheLayer: {eviction_policy.value}, "
                   f"capacity={capacity}, type={cache_type.value}")
    
    def _setup_disk_cache(self):
        """Setup SQLite disk cache"""
        self.disk_db = sqlite3.connect(
            f"{self.disk_cache_path}/cache.db", 
            check_same_thread=False
        )
        
        cursor = self.disk_db.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cache_entries (
                key TEXT PRIMARY KEY,
                value BLOB,
                size INTEGER,
                created_at REAL,
                last_accessed REAL,
                access_count INTEGER,
                ttl REAL,
                priority INTEGER
            )
        ''')
        self.disk_db.commit()
    
    async def start(self):
        """Start background maintenance tasks"""
        self._running = True
        self._maintenance_task = asyncio.create_task(self._maintenance_loop())
        logger.info("SmartCacheLayer started")
    
    async def stop(self):
        """Stop background tasks and cleanup"""
        self._running = False
        if self._maintenance_task:
            self._maintenance_task.cancel()
            try:
                await self._maintenance_task
            except asyncio.CancelledError:
                pass
        
        if hasattr(self, 'disk_db'):
            self.disk_db.close()
        
        logger.info("SmartCacheLayer stopped")
    
    async def _maintenance_loop(self):
        """Background maintenance loop"""
        while self._running:
            try:
                await asyncio.sleep(60)  # Run every minute
                await self._perform_maintenance()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cache maintenance error: {e}")
    
    async def _perform_maintenance(self):
        """Perform cache maintenance tasks"""
        current_time = time.time()
        
        with self._lock:
            # Remove expired entries
            expired_keys = []
            for key, entry in self.memory_cache.items():
                if entry.is_expired():
                    expired_keys.append(key)
            
            for key in expired_keys:
                await self._evict_entry(key)
            
            # Update hit rate history
            self.stats.hit_rate_history.append(self.stats.hit_rate())
            if len(self.stats.hit_rate_history) > 1000:
                self.stats.hit_rate_history.pop(0)
            
            # Predictive cache warming
            if self.enable_predictive:
                await self._perform_predictive_warming()
            
            logger.debug(f"Cache maintenance completed. Stats: {self.stats.get_stats()}")
    
    async def _perform_predictive_warming(self):
        """Perform predictive cache warming based on patterns"""
        current_time = time.time()
        
        # Analyze access patterns and predict future needs
        for key in list(self.predictive_policy.access_patterns.keys()):
            if key not in self.memory_cache:
                # Predict if this key might be needed soon
                next_access = self.predictive_policy.predict_next_access(key, current_time)
                if next_access < 60.0:  # Expected access within 1 minute
                    # Try to warm cache from disk or generate prediction
                    await self._warm_cache_entry(key)
    
    async def _warm_cache_entry(self, key: str):
        """Warm cache entry predictively"""
        try:
            # Try to load from disk cache first
            if hasattr(self, 'disk_db'):
                cursor = self.disk_db.cursor()
                cursor.execute('SELECT * FROM cache_entries WHERE key = ?', (key,))
                row = cursor.fetchone()
                
                if row:
                    entry = CacheEntry(
                        key=row[0],
                        value=pickle.loads(row[1]),
                        size=row[2],
                        created_at=row[3],
                        last_accessed=time.time(),
                        access_count=row[5] + 1,
                        ttl=row[6],
                        priority=row[7]
                    )
                    
                    with self._lock:
                        self.memory_cache[key] = entry
                        self._update_access_structures(key, entry)
                    
                    logger.debug(f"Warmed cache entry from disk: {key}")
        
        except Exception as e:
            logger.error(f"Error warming cache entry {key}: {e}")
    
    def _compress_value(self, value: Any) -> bytes:
        """Compress value for storage"""
        serialized = pickle.dumps(value)
        
        if self.compression == CompressionType.GZIP:
            return gzip.compress(serialized)
        elif self.compression == CompressionType.NONE:
            return serialized
        else:
            # Default to gzip
            return gzip.compress(serialized)
    
    def _decompress_value(self, compressed_data: bytes) -> Any:
        """Decompress value from storage"""
        if self.compression == CompressionType.GZIP:
            decompressed = gzip.decompress(compressed_data)
        else:
            decompressed = compressed_data
        
        return pickle.loads(decompressed)
    
    def _calculate_size(self, value: Any) -> int:
        """Calculate approximate size of value"""
        try:
            return len(pickle.dumps(value))
        except:
            return 1024  # Default estimate
    
    def _update_access_structures(self, key: str, entry: CacheEntry):
        """Update internal access tracking structures"""
        # Update access order for LRU
        if key in self.access_order:
            del self.access_order[key]
        self.access_order[key] = entry
        
        # Update frequency for LFU
        self.frequency_counter[key] += 1
        
        # Update predictive model
        if self.enable_predictive:
            self.predictive_policy.record_access(key, time.time())
    
    async def _evict_entry(self, key: str) -> bool:
        """Evict entry from cache"""
        if key not in self.memory_cache:
            return False
        
        entry = self.memory_cache.pop(key)
        
        # Remove from access structures
        if key in self.access_order:
            del self.access_order[key]
        
        # Store to disk if hybrid cache
        if (self.cache_type in [CacheType.DISK, CacheType.HYBRID] and 
            hasattr(self, 'disk_db')):
            await self._store_to_disk(key, entry)
        
        self.stats.record_eviction()
        self.stats.size_bytes -= entry.size
        
        logger.debug(f"Evicted cache entry: {key}")
        return True
    
    async def _store_to_disk(self, key: str, entry: CacheEntry):
        """Store entry to disk cache"""
        try:
            compressed_value = self._compress_value(entry.value)
            
            cursor = self.disk_db.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO cache_entries 
                (key, value, size, created_at, last_accessed, access_count, ttl, priority)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                key, compressed_value, entry.size, entry.created_at,
                entry.last_accessed, entry.access_count, entry.ttl, entry.priority
            ))
            self.disk_db.commit()
            
        except Exception as e:
            logger.error(f"Error storing to disk cache: {e}")
    
    def _select_victim_for_eviction(self) -> Optional[str]:
        """Select victim for eviction based on policy"""
        if not self.memory_cache:
            return None
        
        if self.eviction_policy == EvictionPolicy.LRU:
            return next(iter(self.access_order))
        
        elif self.eviction_policy == EvictionPolicy.LFU:
            return min(self.frequency_counter.keys(), 
                      key=lambda k: self.frequency_counter[k])
        
        elif self.eviction_policy == EvictionPolicy.ARC:
            if hasattr(self, 'arc_cache'):
                # ARC handles its own eviction logic
                return None
            else:
                return next(iter(self.access_order))
        
        elif self.eviction_policy == EvictionPolicy.PREDICTIVE:
            if self.enable_predictive:
                current_time = time.time()
                candidates = []
                
                for key in self.memory_cache.keys():
                    if self.predictive_policy.should_evict(key, current_time):
                        next_access = self.predictive_policy.predict_next_access(key, current_time)
                        candidates.append((key, next_access))
                
                if candidates:
                    # Evict the one with longest predicted next access time
                    return max(candidates, key=lambda x: x[1])[0]
            
            # Fallback to LRU
            return next(iter(self.access_order))
        
        else:
            # Default to LRU
            return next(iter(self.access_order))
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        start_time = time.time()
        
        with self._lock:
            # Check memory cache first
            if key in self.memory_cache:
                entry = self.memory_cache[key]
                
                if entry.is_expired():
                    await self._evict_entry(key)
                    self.stats.record_miss()
                    return None
                
                # Update access metadata
                entry.last_accessed = time.time()
                entry.access_count += 1
                self._update_access_structures(key, entry)
                
                access_time = time.time() - start_time
                self.stats.record_hit(access_time)
                
                return entry.value
            
            # Try disk cache if hybrid
            if (self.cache_type in [CacheType.DISK, CacheType.HYBRID] and 
                hasattr(self, 'disk_db')):
                
                try:
                    cursor = self.disk_db.cursor()
                    cursor.execute('SELECT * FROM cache_entries WHERE key = ?', (key,))
                    row = cursor.fetchone()
                    
                    if row:
                        # Load from disk to memory
                        entry = CacheEntry(
                            key=row[0],
                            value=self._decompress_value(row[1]),
                            size=row[2],
                            created_at=row[3],
                            last_accessed=time.time(),
                            access_count=row[5] + 1,
                            ttl=row[6],
                            priority=row[7]
                        )
                        
                        if not entry.is_expired():
                            # Add back to memory cache
                            await self._make_room_if_needed(entry.size)
                            self.memory_cache[key] = entry
                            self._update_access_structures(key, entry)
                            
                            access_time = time.time() - start_time
                            self.stats.record_hit(access_time)
                            
                            return entry.value
                        else:
                            # Remove expired entry from disk
                            cursor.execute('DELETE FROM cache_entries WHERE key = ?', (key,))
                            self.disk_db.commit()
                
                except Exception as e:
                    logger.error(f"Error reading from disk cache: {e}")
            
            self.stats.record_miss()
            return None
    
    async def put(self, key: str, value: Any, ttl: Optional[float] = None, 
                  priority: int = 0) -> bool:
        """Put value in cache"""
        size = self._calculate_size(value)
        current_time = time.time()
        
        entry = CacheEntry(
            key=key,
            value=value,
            size=size,
            created_at=current_time,
            last_accessed=current_time,
            access_count=1,
            ttl=ttl,
            priority=priority
        )
        
        with self._lock:
            # Make room if needed
            await self._make_room_if_needed(size)
            
            # Handle ARC cache
            if self.eviction_policy == EvictionPolicy.ARC and hasattr(self, 'arc_cache'):
                evicted_key = self.arc_cache.put(key, entry)
                if evicted_key and evicted_key in self.memory_cache:
                    await self._evict_entry(evicted_key)
            
            # Update memory cache
            if key in self.memory_cache:
                old_entry = self.memory_cache[key]
                self.stats.size_bytes -= old_entry.size
                self.stats.updates += 1
            else:
                self.stats.record_insertion(size)
            
            self.memory_cache[key] = entry
            self._update_access_structures(key, entry)
            
            return True
    
    async def _make_room_if_needed(self, required_size: int):
        """Make room in cache if needed"""
        while (len(self.memory_cache) >= self.capacity or 
               self.stats.size_bytes + required_size > self.capacity * 1000):  # Assume avg 1KB per item
            
            victim_key = self._select_victim_for_eviction()
            if not victim_key:
                break
                
            await self._evict_entry(victim_key)
    
    async def delete(self, key: str) -> bool:
        """Delete entry from cache"""
        with self._lock:
            if key in self.memory_cache:
                await self._evict_entry(key)
                return True
            
            # Also try disk cache
            if (self.cache_type in [CacheType.DISK, CacheType.HYBRID] and 
                hasattr(self, 'disk_db')):
                
                cursor = self.disk_db.cursor()
                cursor.execute('DELETE FROM cache_entries WHERE key = ?', (key,))
                deleted = cursor.rowcount > 0
                self.disk_db.commit()
                return deleted
            
            return False
    
    async def clear(self):
        """Clear all cache entries"""
        with self._lock:
            self.memory_cache.clear()
            self.access_order.clear()
            self.frequency_counter.clear()
            
            if hasattr(self, 'arc_cache'):
                self.arc_cache = AdaptiveReplacementCache(self.capacity)
            
            if (self.cache_type in [CacheType.DISK, CacheType.HYBRID] and 
                hasattr(self, 'disk_db')):
                
                cursor = self.disk_db.cursor()
                cursor.execute('DELETE FROM cache_entries')
                self.disk_db.commit()
            
            # Reset stats
            self.stats = CacheStats()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return self.stats.get_stats()
    
    def get_detailed_status(self) -> Dict[str, Any]:
        """Get detailed cache status"""
        with self._lock:
            return {
                'memory_entries': len(self.memory_cache),
                'capacity': self.capacity,
                'eviction_policy': self.eviction_policy.value,
                'cache_type': self.cache_type.value,
                'compression': self.compression.value,
                'predictive_enabled': self.enable_predictive,
                'stats': self.get_stats(),
                'access_patterns': len(self.predictive_policy.access_patterns) if self.enable_predictive else 0,
                'memory_usage_mb': self.stats.size_bytes / (1024 * 1024),
            }


class MultiTierCacheManager:
    """
    Manages multiple cache layers with intelligent routing
    """
    
    def __init__(self):
        self.cache_layers: Dict[str, SmartCacheLayer] = {}
        self.routing_rules: Dict[str, List[str]] = {}
        self.global_stats = CacheStats()
        self._lock = threading.Lock()
    
    def add_cache_layer(self, name: str, cache_layer: SmartCacheLayer, 
                       route_patterns: List[str] = None):
        """Add a cache layer with optional routing patterns"""
        with self._lock:
            self.cache_layers[name] = cache_layer
            
            if route_patterns:
                for pattern in route_patterns:
                    if pattern not in self.routing_rules:
                        self.routing_rules[pattern] = []
                    self.routing_rules[pattern].append(name)
    
    def _select_cache_layers(self, key: str) -> List[SmartCacheLayer]:
        """Select appropriate cache layers for a key"""
        selected_layers = []
        
        # Check routing rules
        for pattern, layer_names in self.routing_rules.items():
            if pattern in key:  # Simple pattern matching
                for layer_name in layer_names:
                    if layer_name in self.cache_layers:
                        selected_layers.append(self.cache_layers[layer_name])
                        break  # Use first matching layer
        
        # Default to all layers if no specific routing
        if not selected_layers:
            selected_layers = list(self.cache_layers.values())
        
        return selected_layers
    
    async def get(self, key: str) -> Optional[Any]:
        """Get from appropriate cache layers"""
        cache_layers = self._select_cache_layers(key)
        
        for cache_layer in cache_layers:
            try:
                value = await cache_layer.get(key)
                if value is not None:
                    self.global_stats.record_hit()
                    return value
            except Exception as e:
                logger.error(f"Error getting from cache layer: {e}")
                continue
        
        self.global_stats.record_miss()
        return None
    
    async def put(self, key: str, value: Any, **kwargs) -> bool:
        """Put in appropriate cache layers"""
        cache_layers = self._select_cache_layers(key)
        success = False
        
        for cache_layer in cache_layers:
            try:
                if await cache_layer.put(key, value, **kwargs):
                    success = True
            except Exception as e:
                logger.error(f"Error putting to cache layer: {e}")
                continue
        
        if success:
            self.global_stats.record_insertion(len(str(value)))
        
        return success
    
    async def start_all(self):
        """Start all cache layers"""
        for cache_layer in self.cache_layers.values():
            await cache_layer.start()
    
    async def stop_all(self):
        """Stop all cache layers"""
        for cache_layer in self.cache_layers.values():
            await cache_layer.stop()
    
    def get_global_stats(self) -> Dict[str, Any]:
        """Get aggregated statistics from all layers"""
        layer_stats = {}
        for name, layer in self.cache_layers.items():
            layer_stats[name] = layer.get_detailed_status()
        
        return {
            'global_stats': self.global_stats.get_stats(),
            'layer_stats': layer_stats,
            'total_layers': len(self.cache_layers),
            'routing_rules': len(self.routing_rules)
        }


# Factory function for easy cache creation
def create_smart_cache(cache_config: Dict[str, Any]) -> SmartCacheLayer:
    """Create a smart cache layer from configuration"""
    return SmartCacheLayer(
        capacity=cache_config.get('capacity', 10000),
        eviction_policy=EvictionPolicy(cache_config.get('eviction_policy', 'arc')),
        cache_type=CacheType(cache_config.get('cache_type', 'hybrid')),
        compression=CompressionType(cache_config.get('compression', 'gzip')),
        enable_predictive=cache_config.get('enable_predictive', True),
        disk_cache_path=cache_config.get('disk_cache_path', '/tmp/cache')
    )