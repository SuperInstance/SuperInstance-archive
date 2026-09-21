"""
Memory-Efficient Data Structures and Advanced Caching Systems
World-class implementation with compression, serialization, and intelligent memory management
"""

import asyncio
import array
import bisect
import gc
import gzip
import json
import logging
import mmap
import os
import pickle
import sqlite3
import sys
import tempfile
import threading
import time
import weakref
import zlib
from collections import deque, defaultdict, OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Set, Union, Tuple, Iterator, Generic, TypeVar
import uuid
from functools import lru_cache
import struct
import heapq

logger = logging.getLogger(__name__)

T = TypeVar('T')
K = TypeVar('K')
V = TypeVar('V')


class CompressionAlgorithm(Enum):
    """Available compression algorithms"""
    NONE = "none"
    GZIP = "gzip"
    ZLIB = "zlib"
    LZMA = "lzma"
    BROTLI = "brotli"


class SerializationFormat(Enum):
    """Serialization formats"""
    PICKLE = "pickle"
    JSON = "json"
    MSGPACK = "msgpack"
    PROTOBUF = "protobuf"
    AVRO = "avro"


class EvictionPolicy(Enum):
    """Cache eviction policies"""
    LRU = "lru"
    LFU = "lfu"
    FIFO = "fifo"
    LIFO = "lifo"
    RANDOM = "random"
    TTL = "ttl"
    SIZE_AWARE = "size_aware"
    COST_AWARE = "cost_aware"


@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    key: Any
    value: Any
    size: int
    access_count: int = 0
    access_time: float = field(default_factory=time.time)
    creation_time: float = field(default_factory=time.time)
    ttl: Optional[float] = None
    cost: float = 1.0
    compressed: bool = False
    serialized: bool = False
    
    def is_expired(self) -> bool:
        """Check if entry has expired"""
        if self.ttl is None:
            return False
        return time.time() - self.creation_time > self.ttl
    
    def update_access(self):
        """Update access statistics"""
        self.access_count += 1
        self.access_time = time.time()


class CompactArray(Generic[T]):
    """Memory-efficient array for numeric data"""
    
    def __init__(self, type_code: str = 'i', initial_capacity: int = 1000):
        """
        Initialize compact array
        
        Args:
            type_code: Array type code ('i' for int, 'f' for float, etc.)
            initial_capacity: Initial capacity
        """
        self.type_code = type_code
        self._array = array.array(type_code)
        self._capacity = initial_capacity
        self._size = 0
        
        # Pre-allocate array
        self._array.extend([0] * initial_capacity)
    
    def append(self, value: T):
        """Append value to array"""
        if self._size >= self._capacity:
            self._expand()
        
        self._array[self._size] = value
        self._size += 1
    
    def extend(self, values: List[T]):
        """Extend array with multiple values"""
        needed_capacity = self._size + len(values)
        while self._capacity < needed_capacity:
            self._expand()
        
        for i, value in enumerate(values):
            self._array[self._size + i] = value
        
        self._size += len(values)
    
    def __getitem__(self, index: int) -> T:
        """Get item by index"""
        if index >= self._size:
            raise IndexError("Index out of range")
        return self._array[index]
    
    def __setitem__(self, index: int, value: T):
        """Set item by index"""
        if index >= self._size:
            raise IndexError("Index out of range")
        self._array[index] = value
    
    def __len__(self) -> int:
        """Get array length"""
        return self._size
    
    def __iter__(self) -> Iterator[T]:
        """Iterate over array"""
        for i in range(self._size):
            yield self._array[i]
    
    def _expand(self):
        """Expand array capacity"""
        new_capacity = int(self._capacity * 1.5)
        extension_size = new_capacity - self._capacity
        self._array.extend([0] * extension_size)
        self._capacity = new_capacity
    
    def compact(self):
        """Remove unused capacity"""
        if self._capacity > self._size:
            # Create new array with exact size
            new_array = array.array(self.type_code, self._array[:self._size])
            self._array = new_array
            self._capacity = self._size
    
    def get_memory_usage(self) -> int:
        """Get memory usage in bytes"""
        return self._array.buffer_info()[1] * self._array.itemsize
    
    def to_bytes(self) -> bytes:
        """Convert to bytes for serialization"""
        return self._array[:self._size].tobytes()
    
    @classmethod
    def from_bytes(cls, data: bytes, type_code: str = 'i') -> 'CompactArray':
        """Create array from bytes"""
        arr = cls(type_code, 0)
        arr._array = array.array(type_code)
        arr._array.frombytes(data)
        arr._size = len(arr._array)
        arr._capacity = arr._size
        return arr


class SparseArray(Generic[T]):
    """Memory-efficient sparse array for data with many empty slots"""
    
    def __init__(self, default_value: Optional[T] = None):
        self.default_value = default_value
        self._data: Dict[int, T] = {}
        self._max_index = -1
    
    def __getitem__(self, index: int) -> T:
        """Get item by index"""
        if index < 0:
            raise IndexError("Negative indices not supported")
        
        return self._data.get(index, self.default_value)
    
    def __setitem__(self, index: int, value: T):
        """Set item by index"""
        if index < 0:
            raise IndexError("Negative indices not supported")
        
        if value != self.default_value:
            self._data[index] = value
            self._max_index = max(self._max_index, index)
        elif index in self._data:
            del self._data[index]
            # Recalculate max_index if necessary
            if index == self._max_index and self._data:
                self._max_index = max(self._data.keys())
            elif not self._data:
                self._max_index = -1
    
    def __len__(self) -> int:
        """Get logical length of array"""
        return self._max_index + 1 if self._max_index >= 0 else 0
    
    def __iter__(self) -> Iterator[T]:
        """Iterate over array"""
        for i in range(len(self)):
            yield self[i]
    
    def get_density(self) -> float:
        """Get density (ratio of non-default values to total length)"""
        if len(self) == 0:
            return 0.0
        return len(self._data) / len(self)
    
    def get_memory_usage(self) -> int:
        """Estimate memory usage"""
        return sys.getsizeof(self._data) + sum(sys.getsizeof(v) for v in self._data.values())
    
    def compact(self):
        """Remove unnecessary internal structures"""
        # Remove entries that equal default value
        to_remove = [k for k, v in self._data.items() if v == self.default_value]
        for k in to_remove:
            del self._data[k]


class RingBuffer(Generic[T]):
    """Memory-efficient circular buffer"""
    
    def __init__(self, capacity: int):
        self.capacity = capacity
        self._buffer: List[Optional[T]] = [None] * capacity
        self._head = 0
        self._tail = 0
        self._size = 0
        self._full = False
    
    def append(self, item: T):
        """Add item to buffer"""
        self._buffer[self._head] = item
        
        if self._full:
            self._tail = (self._tail + 1) % self.capacity
        else:
            self._size += 1
        
        self._head = (self._head + 1) % self.capacity
        
        if self._head == self._tail:
            self._full = True
    
    def popleft(self) -> Optional[T]:
        """Remove and return leftmost item"""
        if self._size == 0:
            return None
        
        item = self._buffer[self._tail]
        self._buffer[self._tail] = None
        self._tail = (self._tail + 1) % self.capacity
        self._size -= 1
        self._full = False
        
        return item
    
    def __len__(self) -> int:
        """Get buffer size"""
        return self._size
    
    def __iter__(self) -> Iterator[T]:
        """Iterate over buffer"""
        idx = self._tail
        for _ in range(self._size):
            yield self._buffer[idx]
            idx = (idx + 1) % self.capacity
    
    def is_full(self) -> bool:
        """Check if buffer is full"""
        return self._full
    
    def get_memory_usage(self) -> int:
        """Get memory usage"""
        return sys.getsizeof(self._buffer) + sum(
            sys.getsizeof(item) for item in self._buffer if item is not None
        )


class MemoryMappedDict:
    """Dictionary backed by memory-mapped file for large datasets"""
    
    def __init__(self, filepath: str, max_size: int = 1024 * 1024 * 1024):  # 1GB default
        self.filepath = filepath
        self.max_size = max_size
        self._index: Dict[str, Tuple[int, int]] = {}  # key -> (offset, size)
        self._file = None
        self._mmap = None
        self._current_offset = 0
        self._lock = threading.RLock()
        
        self._ensure_file_exists()
        self._load_index()
    
    def _ensure_file_exists(self):
        """Ensure the backing file exists"""
        if not os.path.exists(self.filepath):
            with open(self.filepath, 'wb') as f:
                f.write(b'\x00' * min(1024 * 1024, self.max_size))  # 1MB initial
    
    def _load_index(self):
        """Load index from file metadata"""
        index_path = self.filepath + '.idx'
        if os.path.exists(index_path):
            try:
                with open(index_path, 'rb') as f:
                    self._index = pickle.load(f)
                    self._current_offset = max(
                        (offset + size for offset, size in self._index.values()),
                        default=0
                    )
            except Exception as e:
                logger.warning(f"Failed to load index: {e}")
                self._index = {}
                self._current_offset = 0
    
    def _save_index(self):
        """Save index to file"""
        index_path = self.filepath + '.idx'
        try:
            with open(index_path, 'wb') as f:
                pickle.dump(self._index, f)
        except Exception as e:
            logger.error(f"Failed to save index: {e}")
    
    def _open_mmap(self):
        """Open memory-mapped file"""
        if self._file is None:
            self._file = open(self.filepath, 'r+b')
            self._mmap = mmap.mmap(self._file.fileno(), 0)
    
    def _close_mmap(self):
        """Close memory-mapped file"""
        if self._mmap:
            self._mmap.close()
            self._mmap = None
        if self._file:
            self._file.close()
            self._file = None
    
    def __enter__(self):
        self._open_mmap()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self._save_index()
        self._close_mmap()
    
    def put(self, key: str, value: Any):
        """Store value in memory-mapped dict"""
        with self._lock:
            self._open_mmap()
            
            # Serialize value
            data = pickle.dumps(value)
            size = len(data)
            
            # Check if we have space
            if self._current_offset + size > self.max_size:
                raise MemoryError("Memory-mapped dict is full")
            
            # Write data
            self._mmap.seek(self._current_offset)
            self._mmap.write(data)
            
            # Update index
            self._index[key] = (self._current_offset, size)
            self._current_offset += size
    
    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve value from memory-mapped dict"""
        with self._lock:
            if key not in self._index:
                return default
            
            self._open_mmap()
            
            offset, size = self._index[key]
            self._mmap.seek(offset)
            data = self._mmap.read(size)
            
            try:
                return pickle.loads(data)
            except Exception as e:
                logger.error(f"Failed to deserialize data for key {key}: {e}")
                return default
    
    def delete(self, key: str) -> bool:
        """Delete key from dict"""
        with self._lock:
            if key in self._index:
                del self._index[key]
                return True
            return False
    
    def keys(self) -> List[str]:
        """Get all keys"""
        return list(self._index.keys())
    
    def __len__(self) -> int:
        """Get number of items"""
        return len(self._index)
    
    def get_memory_usage(self) -> int:
        """Get memory usage"""
        return self._current_offset


class MultiLevelCache:
    """Multi-level cache with different storage tiers"""
    
    def __init__(
        self,
        l1_size: int = 1000,      # In-memory cache
        l2_size: int = 10000,     # Compressed cache
        l3_path: Optional[str] = None,  # Disk cache
        compression: CompressionAlgorithm = CompressionAlgorithm.ZLIB,
        serialization: SerializationFormat = SerializationFormat.PICKLE
    ):
        # Level 1: Fast in-memory cache
        self.l1_cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.l1_size = l1_size
        
        # Level 2: Compressed in-memory cache
        self.l2_cache: Dict[str, bytes] = {}
        self.l2_size = l2_size
        self.l2_metadata: Dict[str, Dict[str, Any]] = {}
        
        # Level 3: Disk cache
        self.l3_path = l3_path
        self.l3_cache: Optional[MemoryMappedDict] = None
        
        self.compression = compression
        self.serialization = serialization
        
        # Statistics
        self.l1_hits = 0
        self.l2_hits = 0
        self.l3_hits = 0
        self.misses = 0
        
        # Thread safety
        self.lock = threading.RLock()
        
        # Initialize L3 cache if path provided
        if self.l3_path:
            self.l3_cache = MemoryMappedDict(self.l3_path)
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache (check all levels)"""
        with self.lock:
            # Check L1 cache
            if key in self.l1_cache:
                entry = self.l1_cache[key]
                if not entry.is_expired():
                    entry.update_access()
                    # Move to end (most recently used)
                    self.l1_cache.move_to_end(key)
                    self.l1_hits += 1
                    return entry.value
                else:
                    del self.l1_cache[key]
            
            # Check L2 cache
            if key in self.l2_cache:
                try:
                    compressed_data = self.l2_cache[key]
                    metadata = self.l2_metadata[key]
                    
                    # Check expiration
                    if metadata.get('ttl') and time.time() - metadata['creation_time'] > metadata['ttl']:
                        del self.l2_cache[key]
                        del self.l2_metadata[key]
                    else:
                        # Decompress and deserialize
                        value = self._decompress_deserialize(compressed_data)
                        
                        # Promote to L1
                        self._promote_to_l1(key, value, metadata)
                        
                        self.l2_hits += 1
                        return value
                
                except Exception as e:
                    logger.error(f"Error retrieving from L2 cache: {e}")
                    # Remove corrupted entry
                    self.l2_cache.pop(key, None)
                    self.l2_metadata.pop(key, None)
            
            # Check L3 cache
            if self.l3_cache:
                try:
                    with self.l3_cache:
                        value = self.l3_cache.get(key)
                        if value is not None:
                            # Promote to L2 and L1
                            self._promote_to_l2(key, value)
                            self._promote_to_l1(key, value)
                            
                            self.l3_hits += 1
                            return value
                
                except Exception as e:
                    logger.error(f"Error retrieving from L3 cache: {e}")
            
            # Cache miss
            self.misses += 1
            return None
    
    def put(self, key: str, value: Any, ttl: Optional[float] = None, cost: float = 1.0):
        """Put value in cache"""
        with self.lock:
            # Always try to put in L1 first
            entry = CacheEntry(
                key=key,
                value=value,
                size=sys.getsizeof(value),
                ttl=ttl,
                cost=cost
            )
            
            # Check if L1 has space
            if len(self.l1_cache) >= self.l1_size:
                self._evict_l1()
            
            self.l1_cache[key] = entry
            
            # Also store in L2 (compressed)
            try:
                compressed_data = self._compress_serialize(value)
                
                if len(self.l2_cache) >= self.l2_size:
                    self._evict_l2()
                
                self.l2_cache[key] = compressed_data
                self.l2_metadata[key] = {
                    'creation_time': time.time(),
                    'ttl': ttl,
                    'size': len(compressed_data),
                    'cost': cost
                }
            
            except Exception as e:
                logger.error(f"Error storing in L2 cache: {e}")
            
            # Store in L3 if available
            if self.l3_cache:
                try:
                    with self.l3_cache:
                        self.l3_cache.put(key, value)
                except Exception as e:
                    logger.error(f"Error storing in L3 cache: {e}")
    
    def remove(self, key: str) -> bool:
        """Remove key from all cache levels"""
        with self.lock:
            removed = False
            
            if key in self.l1_cache:
                del self.l1_cache[key]
                removed = True
            
            if key in self.l2_cache:
                del self.l2_cache[key]
                self.l2_metadata.pop(key, None)
                removed = True
            
            if self.l3_cache:
                try:
                    with self.l3_cache:
                        if self.l3_cache.delete(key):
                            removed = True
                except Exception as e:
                    logger.error(f"Error removing from L3 cache: {e}")
            
            return removed
    
    def clear(self):
        """Clear all cache levels"""
        with self.lock:
            self.l1_cache.clear()
            self.l2_cache.clear()
            self.l2_metadata.clear()
            
            if self.l3_cache:
                try:
                    # Clear L3 cache by recreating the file
                    self.l3_cache._close_mmap()
                    if os.path.exists(self.l3_path):
                        os.remove(self.l3_path)
                    if os.path.exists(self.l3_path + '.idx'):
                        os.remove(self.l3_path + '.idx')
                    self.l3_cache = MemoryMappedDict(self.l3_path)
                except Exception as e:
                    logger.error(f"Error clearing L3 cache: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self.l1_hits + self.l2_hits + self.l3_hits + self.misses
        
        return {
            "l1_cache": {
                "size": len(self.l1_cache),
                "max_size": self.l1_size,
                "hits": self.l1_hits,
                "hit_rate": self.l1_hits / max(1, total_requests)
            },
            "l2_cache": {
                "size": len(self.l2_cache),
                "max_size": self.l2_size,
                "hits": self.l2_hits,
                "hit_rate": self.l2_hits / max(1, total_requests),
                "compression_ratio": self._get_l2_compression_ratio()
            },
            "l3_cache": {
                "size": len(self.l3_cache) if self.l3_cache else 0,
                "hits": self.l3_hits,
                "hit_rate": self.l3_hits / max(1, total_requests),
                "memory_usage": self.l3_cache.get_memory_usage() if self.l3_cache else 0
            },
            "overall": {
                "total_hits": self.l1_hits + self.l2_hits + self.l3_hits,
                "total_misses": self.misses,
                "hit_rate": (self.l1_hits + self.l2_hits + self.l3_hits) / max(1, total_requests)
            }
        }
    
    def _promote_to_l1(self, key: str, value: Any, metadata: Optional[Dict[str, Any]] = None):
        """Promote item to L1 cache"""
        if len(self.l1_cache) >= self.l1_size:
            self._evict_l1()
        
        entry = CacheEntry(
            key=key,
            value=value,
            size=sys.getsizeof(value),
            ttl=metadata.get('ttl') if metadata else None,
            cost=metadata.get('cost', 1.0) if metadata else 1.0
        )
        
        self.l1_cache[key] = entry
    
    def _promote_to_l2(self, key: str, value: Any):
        """Promote item to L2 cache"""
        try:
            compressed_data = self._compress_serialize(value)
            
            if len(self.l2_cache) >= self.l2_size:
                self._evict_l2()
            
            self.l2_cache[key] = compressed_data
            self.l2_metadata[key] = {
                'creation_time': time.time(),
                'ttl': None,
                'size': len(compressed_data),
                'cost': 1.0
            }
        except Exception as e:
            logger.error(f"Error promoting to L2 cache: {e}")
    
    def _evict_l1(self):
        """Evict item from L1 cache (LRU)"""
        if self.l1_cache:
            # Remove least recently used item (first in OrderedDict)
            key, entry = self.l1_cache.popitem(last=False)
            
            # Demote to L2 if not already there
            if key not in self.l2_cache:
                try:
                    compressed_data = self._compress_serialize(entry.value)
                    if len(self.l2_cache) < self.l2_size:
                        self.l2_cache[key] = compressed_data
                        self.l2_metadata[key] = {
                            'creation_time': entry.creation_time,
                            'ttl': entry.ttl,
                            'size': len(compressed_data),
                            'cost': entry.cost
                        }
                except Exception as e:
                    logger.error(f"Error demoting to L2 cache: {e}")
    
    def _evict_l2(self):
        """Evict item from L2 cache (cost-aware LRU)"""
        if not self.l2_cache:
            return
        
        # Find item with lowest cost-to-size ratio among oldest items
        candidates = list(self.l2_cache.items())[:max(1, len(self.l2_cache) // 4)]  # Consider oldest 25%
        
        if candidates:
            def cost_ratio(item):
                key, _ = item
                metadata = self.l2_metadata.get(key, {})
                size = metadata.get('size', 1)
                cost = metadata.get('cost', 1.0)
                return cost / size
            
            victim_key, _ = min(candidates, key=cost_ratio)
            
            # Demote to L3 if available
            if self.l3_cache and victim_key not in self.l3_cache.keys():
                try:
                    compressed_data = self.l2_cache[victim_key]
                    value = self._decompress_deserialize(compressed_data)
                    with self.l3_cache:
                        self.l3_cache.put(victim_key, value)
                except Exception as e:
                    logger.error(f"Error demoting to L3 cache: {e}")
            
            # Remove from L2
            del self.l2_cache[victim_key]
            self.l2_metadata.pop(victim_key, None)
    
    def _compress_serialize(self, value: Any) -> bytes:
        """Serialize and compress value"""
        # Serialize
        if self.serialization == SerializationFormat.PICKLE:
            data = pickle.dumps(value)
        elif self.serialization == SerializationFormat.JSON:
            data = json.dumps(value).encode('utf-8')
        else:
            data = pickle.dumps(value)  # Fallback to pickle
        
        # Compress
        if self.compression == CompressionAlgorithm.ZLIB:
            return zlib.compress(data)
        elif self.compression == CompressionAlgorithm.GZIP:
            return gzip.compress(data)
        elif self.compression == CompressionAlgorithm.LZMA:
            import lzma
            return lzma.compress(data)
        else:
            return data  # No compression
    
    def _decompress_deserialize(self, data: bytes) -> Any:
        """Decompress and deserialize data"""
        # Decompress
        if self.compression == CompressionAlgorithm.ZLIB:
            decompressed = zlib.decompress(data)
        elif self.compression == CompressionAlgorithm.GZIP:
            decompressed = gzip.decompress(data)
        elif self.compression == CompressionAlgorithm.LZMA:
            import lzma
            decompressed = lzma.decompress(data)
        else:
            decompressed = data  # No compression
        
        # Deserialize
        if self.serialization == SerializationFormat.PICKLE:
            return pickle.loads(decompressed)
        elif self.serialization == SerializationFormat.JSON:
            return json.loads(decompressed.decode('utf-8'))
        else:
            return pickle.loads(decompressed)  # Fallback to pickle
    
    def _get_l2_compression_ratio(self) -> float:
        """Calculate average compression ratio for L2 cache"""
        if not self.l2_metadata:
            return 1.0
        
        total_original = 0
        total_compressed = 0
        
        for key, metadata in self.l2_metadata.items():
            if key in self.l1_cache:
                original_size = self.l1_cache[key].size
            else:
                original_size = metadata.get('size', 0) * 2  # Estimate
            
            compressed_size = metadata.get('size', 0)
            
            total_original += original_size
            total_compressed += compressed_size
        
        return total_original / max(1, total_compressed)


class BloomFilter:
    """Memory-efficient probabilistic data structure for set membership testing"""
    
    def __init__(self, expected_items: int, false_positive_rate: float = 0.01):
        import math
        
        self.expected_items = expected_items
        self.false_positive_rate = false_positive_rate
        
        # Calculate optimal bit array size and number of hash functions
        self.bit_array_size = int(-expected_items * math.log(false_positive_rate) / (math.log(2) ** 2))
        self.hash_functions = int(self.bit_array_size * math.log(2) / expected_items)
        
        # Use compact bit array
        self.bit_array = CompactArray('B')  # Unsigned char array
        # Initialize with zeros
        self.bit_array.extend([0] * ((self.bit_array_size + 7) // 8))  # Ceil division for bytes
        
        self.items_added = 0
    
    def add(self, item: Any):
        """Add item to bloom filter"""
        item_hash = hash(str(item))
        
        for i in range(self.hash_functions):
            # Generate different hash values using the original hash
            bit_index = (item_hash + i * 31) % self.bit_array_size
            byte_index = bit_index // 8
            bit_offset = bit_index % 8
            
            # Set bit
            self.bit_array[byte_index] |= (1 << bit_offset)
        
        self.items_added += 1
    
    def contains(self, item: Any) -> bool:
        """Check if item might be in the set (no false negatives, possible false positives)"""
        item_hash = hash(str(item))
        
        for i in range(self.hash_functions):
            bit_index = (item_hash + i * 31) % self.bit_array_size
            byte_index = bit_index // 8
            bit_offset = bit_index % 8
            
            # Check bit
            if not (self.bit_array[byte_index] & (1 << bit_offset)):
                return False
        
        return True
    
    def get_memory_usage(self) -> int:
        """Get memory usage in bytes"""
        return self.bit_array.get_memory_usage()
    
    def get_current_false_positive_rate(self) -> float:
        """Calculate current false positive rate"""
        import math
        
        if self.items_added == 0:
            return 0.0
        
        # Calculate actual false positive rate based on items added
        return (1 - math.exp(-self.hash_functions * self.items_added / self.bit_array_size)) ** self.hash_functions


class AdaptiveCache:
    """Cache that adapts its behavior based on access patterns and memory pressure"""
    
    def __init__(
        self,
        initial_size: int = 1000,
        max_size: int = 10000,
        adaptation_interval: int = 100  # Adapt every N operations
    ):
        self.initial_size = initial_size
        self.max_size = max_size
        self.current_size = initial_size
        self.adaptation_interval = adaptation_interval
        
        # Multiple eviction strategies
        self.strategies = {
            EvictionPolicy.LRU: OrderedDict(),
            EvictionPolicy.LFU: {},
            EvictionPolicy.COST_AWARE: {}
        }
        
        # Current active strategy
        self.active_strategy = EvictionPolicy.LRU
        self.strategy_cache = self.strategies[self.active_strategy]
        
        # Access patterns tracking
        self.access_frequency: Dict[str, int] = defaultdict(int)
        self.access_times: Dict[str, float] = {}
        self.costs: Dict[str, float] = defaultdict(lambda: 1.0)
        
        # Performance metrics for each strategy
        self.strategy_performance = {
            strategy: {'hits': 0, 'misses': 0} 
            for strategy in EvictionPolicy
        }
        
        # Adaptation state
        self.operations_count = 0
        self.last_adaptation = 0
        
        # Thread safety
        self.lock = threading.RLock()
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        with self.lock:
            self.operations_count += 1
            
            # Update access patterns
            self.access_frequency[key] += 1
            self.access_times[key] = time.time()
            
            # Check current strategy cache
            if self.active_strategy == EvictionPolicy.LRU:
                if key in self.strategy_cache:
                    value = self.strategy_cache[key]
                    self.strategy_cache.move_to_end(key)  # Move to end (most recent)
                    self.strategy_performance[self.active_strategy]['hits'] += 1
                    self._maybe_adapt()
                    return value
            elif self.active_strategy == EvictionPolicy.LFU:
                if key in self.strategy_cache:
                    value = self.strategy_cache[key]
                    self.strategy_performance[self.active_strategy]['hits'] += 1
                    self._maybe_adapt()
                    return value
            elif self.active_strategy == EvictionPolicy.COST_AWARE:
                if key in self.strategy_cache:
                    value = self.strategy_cache[key]
                    self.strategy_performance[self.active_strategy]['hits'] += 1
                    self._maybe_adapt()
                    return value
            
            # Cache miss
            self.strategy_performance[self.active_strategy]['misses'] += 1
            self._maybe_adapt()
            return None
    
    def put(self, key: str, value: Any, cost: float = 1.0):
        """Put value in cache"""
        with self.lock:
            self.operations_count += 1
            self.costs[key] = cost
            
            # Check if eviction is needed
            if len(self.strategy_cache) >= self.current_size:
                self._evict()
            
            # Add to current strategy cache
            if self.active_strategy == EvictionPolicy.LRU:
                self.strategy_cache[key] = value
            elif self.active_strategy == EvictionPolicy.LFU:
                self.strategy_cache[key] = value
            elif self.active_strategy == EvictionPolicy.COST_AWARE:
                self.strategy_cache[key] = value
            
            self._maybe_adapt()
    
    def _evict(self):
        """Evict item based on current strategy"""
        if not self.strategy_cache:
            return
        
        if self.active_strategy == EvictionPolicy.LRU:
            # Remove least recently used (first in OrderedDict)
            self.strategy_cache.popitem(last=False)
        
        elif self.active_strategy == EvictionPolicy.LFU:
            # Remove least frequently used
            lfu_key = min(self.strategy_cache.keys(), 
                         key=lambda k: self.access_frequency[k])
            del self.strategy_cache[lfu_key]
        
        elif self.active_strategy == EvictionPolicy.COST_AWARE:
            # Remove item with lowest cost
            low_cost_key = min(self.strategy_cache.keys(),
                              key=lambda k: self.costs[k])
            del self.strategy_cache[low_cost_key]
    
    def _maybe_adapt(self):
        """Adapt cache strategy if needed"""
        if self.operations_count - self.last_adaptation >= self.adaptation_interval:
            self._adapt_strategy()
            self._adapt_size()
            self.last_adaptation = self.operations_count
    
    def _adapt_strategy(self):
        """Adapt cache eviction strategy based on performance"""
        # Calculate hit rates for each strategy
        hit_rates = {}
        for strategy, perf in self.strategy_performance.items():
            total = perf['hits'] + perf['misses']
            hit_rates[strategy] = perf['hits'] / max(1, total)
        
        # Find best performing strategy
        best_strategy = max(hit_rates.keys(), key=lambda k: hit_rates[k])
        
        # Switch if significantly better
        current_hit_rate = hit_rates[self.active_strategy]
        best_hit_rate = hit_rates[best_strategy]
        
        if best_hit_rate > current_hit_rate * 1.1:  # 10% improvement threshold
            logger.info(f"Switching cache strategy from {self.active_strategy} to {best_strategy} "
                       f"(hit rate: {current_hit_rate:.3f} -> {best_hit_rate:.3f})")
            
            # Migrate current cache content to new strategy
            old_cache = self.strategy_cache
            self.active_strategy = best_strategy
            
            # Initialize new strategy cache
            if best_strategy == EvictionPolicy.LRU:
                self.strategies[best_strategy] = OrderedDict()
            else:
                self.strategies[best_strategy] = {}
            
            self.strategy_cache = self.strategies[best_strategy]
            
            # Migrate content (up to current size limit)
            migrated = 0
            for key, value in old_cache.items():
                if migrated >= self.current_size:
                    break
                self.strategy_cache[key] = value
                migrated += 1
    
    def _adapt_size(self):
        """Adapt cache size based on memory pressure and hit rate"""
        # Simple adaptation: increase size if hit rate is good and memory allows
        current_perf = self.strategy_performance[self.active_strategy]
        total_ops = current_perf['hits'] + current_perf['misses']
        hit_rate = current_perf['hits'] / max(1, total_ops)
        
        # Get memory pressure (simplified)
        try:
            process = __import__('psutil').Process()
            memory_percent = process.memory_percent()
            
            if hit_rate > 0.8 and memory_percent < 70 and self.current_size < self.max_size:
                # Increase cache size
                self.current_size = min(self.max_size, int(self.current_size * 1.2))
                logger.debug(f"Increased cache size to {self.current_size}")
            
            elif hit_rate < 0.5 or memory_percent > 85:
                # Decrease cache size
                self.current_size = max(self.initial_size, int(self.current_size * 0.8))
                logger.debug(f"Decreased cache size to {self.current_size}")
                
                # Evict excess items
                while len(self.strategy_cache) > self.current_size:
                    self._evict()
        
        except ImportError:
            pass  # psutil not available
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self.lock:
            total_ops = sum(
                perf['hits'] + perf['misses'] 
                for perf in self.strategy_performance.values()
            )
            
            return {
                "active_strategy": self.active_strategy.value,
                "current_size": len(self.strategy_cache),
                "max_capacity": self.current_size,
                "operations": self.operations_count,
                "strategy_performance": {
                    strategy.value: {
                        "hits": perf["hits"],
                        "misses": perf["misses"],
                        "hit_rate": perf["hits"] / max(1, perf["hits"] + perf["misses"])
                    }
                    for strategy, perf in self.strategy_performance.items()
                },
                "overall_hit_rate": sum(perf["hits"] for perf in self.strategy_performance.values()) / max(1, total_ops)
            }


# Factory functions for easy creation
def create_compact_int_array(initial_capacity: int = 1000) -> CompactArray[int]:
    """Create compact integer array"""
    return CompactArray('i', initial_capacity)

def create_compact_float_array(initial_capacity: int = 1000) -> CompactArray[float]:
    """Create compact float array"""
    return CompactArray('f', initial_capacity)

def create_sparse_array(default_value: Any = None) -> SparseArray:
    """Create sparse array"""
    return SparseArray(default_value)

def create_ring_buffer(capacity: int) -> RingBuffer:
    """Create ring buffer"""
    return RingBuffer(capacity)

def create_multi_level_cache(
    l1_size: int = 1000,
    l2_size: int = 10000,
    l3_path: Optional[str] = None,
    compression: str = "zlib"
) -> MultiLevelCache:
    """Create multi-level cache"""
    compression_algo = CompressionAlgorithm(compression)
    return MultiLevelCache(l1_size, l2_size, l3_path, compression_algo)

def create_bloom_filter(expected_items: int, false_positive_rate: float = 0.01) -> BloomFilter:
    """Create bloom filter"""
    return BloomFilter(expected_items, false_positive_rate)

def create_adaptive_cache(
    initial_size: int = 1000,
    max_size: int = 10000,
    adaptation_interval: int = 100
) -> AdaptiveCache:
    """Create adaptive cache"""
    return AdaptiveCache(initial_size, max_size, adaptation_interval)

def create_memory_mapped_dict(filepath: str, max_size: int = 1024*1024*1024) -> MemoryMappedDict:
    """Create memory-mapped dictionary"""
    return MemoryMappedDict(filepath, max_size)