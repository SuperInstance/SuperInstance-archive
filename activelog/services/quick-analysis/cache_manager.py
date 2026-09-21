#!/usr/bin/env python3
"""
Quick Analysis Portal - Intelligent Caching System
"""

import json
import time
import hashlib
import sqlite3
import logging
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from functools import wraps
import threading


@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    key: str
    value: Any
    created_at: datetime
    expires_at: datetime
    hit_count: int = 0
    last_accessed: datetime = None
    size_bytes: int = 0


class IntelligentCache:
    """Intelligent caching system with multiple eviction strategies"""
    
    def __init__(self, max_size_mb: int = 100, default_ttl: int = 300):
        self.max_size_bytes = max_size_mb * 1024 * 1024  # Convert MB to bytes
        self.default_ttl = default_ttl  # Default time-to-live in seconds
        self.cache: Dict[str, CacheEntry] = {}
        self.lock = threading.RLock()
        
        # Statistics
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'total_size_bytes': 0
        }
        
        # Setup logging
        self.logger = logging.getLogger(__name__)

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        with self.lock:
            if key not in self.cache:
                self.stats['misses'] += 1
                return None
            
            entry = self.cache[key]
            
            # Check if expired
            if datetime.now() > entry.expires_at:
                self.logger.debug(f"Cache entry expired: {key}")
                del self.cache[key]
                self.stats['misses'] += 1
                self._update_total_size()
                return None
            
            # Update access statistics
            entry.hit_count += 1
            entry.last_accessed = datetime.now()
            self.stats['hits'] += 1
            
            self.logger.debug(f"Cache hit: {key}")
            return entry.value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache"""
        with self.lock:
            ttl = ttl or self.default_ttl
            now = datetime.now()
            expires_at = now + timedelta(seconds=ttl)
            
            # Calculate size
            value_size = self._calculate_size(value)
            
            # Check if we need to make room
            if not self._make_room(value_size):
                self.logger.warning(f"Failed to make room for cache entry: {key}")
                return False
            
            # Create cache entry
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=now,
                expires_at=expires_at,
                last_accessed=now,
                size_bytes=value_size
            )
            
            self.cache[key] = entry
            self._update_total_size()
            
            self.logger.debug(f"Cache set: {key} (TTL: {ttl}s, Size: {value_size} bytes)")
            return True

    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                self._update_total_size()
                self.logger.debug(f"Cache delete: {key}")
                return True
            return False

    def clear(self):
        """Clear all cache entries"""
        with self.lock:
            self.cache.clear()
            self.stats['total_size_bytes'] = 0
            self.logger.info("Cache cleared")

    def _calculate_size(self, value: Any) -> int:
        """Calculate approximate size of value in bytes"""
        try:
            return len(json.dumps(value, default=str).encode('utf-8'))
        except (TypeError, ValueError):
            return len(str(value).encode('utf-8'))

    def _make_room(self, needed_size: int) -> bool:
        """Make room in cache using LRU eviction"""
        with self.lock:
            # Remove expired entries first
            self._remove_expired()
            
            # Check if we have enough room now
            if self.stats['total_size_bytes'] + needed_size <= self.max_size_bytes:
                return True
            
            # Evict entries using LRU strategy
            entries_by_access = sorted(
                self.cache.values(),
                key=lambda e: e.last_accessed or e.created_at
            )
            
            for entry in entries_by_access:
                del self.cache[entry.key]
                self.stats['evictions'] += 1
                self.logger.debug(f"Evicted cache entry: {entry.key}")
                
                self._update_total_size()
                
                if self.stats['total_size_bytes'] + needed_size <= self.max_size_bytes:
                    return True
            
            return False

    def _remove_expired(self):
        """Remove expired entries"""
        now = datetime.now()
        expired_keys = [
            key for key, entry in self.cache.items()
            if now > entry.expires_at
        ]
        
        for key in expired_keys:
            del self.cache[key]
            self.logger.debug(f"Removed expired cache entry: {key}")
        
        if expired_keys:
            self._update_total_size()

    def _update_total_size(self):
        """Update total cache size"""
        self.stats['total_size_bytes'] = sum(
            entry.size_bytes for entry in self.cache.values()
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self.lock:
            total_requests = self.stats['hits'] + self.stats['misses']
            hit_rate = (self.stats['hits'] / total_requests * 100) if total_requests > 0 else 0
            
            return {
                'hits': self.stats['hits'],
                'misses': self.stats['misses'],
                'hit_rate': round(hit_rate, 2),
                'evictions': self.stats['evictions'],
                'total_entries': len(self.cache),
                'total_size_bytes': self.stats['total_size_bytes'],
                'total_size_mb': round(self.stats['total_size_bytes'] / (1024 * 1024), 2),
                'max_size_mb': round(self.max_size_bytes / (1024 * 1024), 2)
            }

    def get_entries_info(self) -> List[Dict[str, Any]]:
        """Get detailed information about cache entries"""
        with self.lock:
            entries = []
            for entry in self.cache.values():
                entries.append({
                    'key': entry.key,
                    'created_at': entry.created_at.isoformat(),
                    'expires_at': entry.expires_at.isoformat(),
                    'last_accessed': entry.last_accessed.isoformat() if entry.last_accessed else None,
                    'hit_count': entry.hit_count,
                    'size_bytes': entry.size_bytes,
                    'ttl_remaining': max(0, (entry.expires_at - datetime.now()).total_seconds())
                })
            
            return sorted(entries, key=lambda x: x['last_accessed'] or x['created_at'], reverse=True)


class DatabaseCache:
    """Persistent cache using SQLite"""
    
    def __init__(self, db_path: str = "data/cache.db", table_name: str = "cache"):
        self.db_path = db_path
        self.table_name = table_name
        self.logger = logging.getLogger(__name__)
        self._init_db()

    def _init_db(self):
        """Initialize cache database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    hit_count INTEGER DEFAULT 0,
                    last_accessed TEXT
                )
            """)
            
            # Create indexes for better performance
            cursor.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_{self.table_name}_expires_at 
                ON {self.table_name} (expires_at)
            """)
            
            cursor.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_{self.table_name}_last_accessed 
                ON {self.table_name} (last_accessed)
            """)
            
            conn.commit()

    def get(self, key: str) -> Optional[Any]:
        """Get value from database cache"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute(f"""
                    SELECT value, expires_at, hit_count FROM {self.table_name}
                    WHERE key = ?
                """, (key,))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                value_json, expires_at_str, hit_count = row
                expires_at = datetime.fromisoformat(expires_at_str)
                
                # Check if expired
                if datetime.now() > expires_at:
                    self.delete(key)
                    return None
                
                # Update access statistics
                cursor.execute(f"""
                    UPDATE {self.table_name}
                    SET hit_count = hit_count + 1, last_accessed = ?
                    WHERE key = ?
                """, (datetime.now().isoformat(), key))
                
                conn.commit()
                
                return json.loads(value_json)
                
        except Exception as e:
            self.logger.error(f"Database cache get error: {e}")
            return None

    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Set value in database cache"""
        try:
            now = datetime.now()
            expires_at = now + timedelta(seconds=ttl)
            value_json = json.dumps(value, default=str)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute(f"""
                    INSERT OR REPLACE INTO {self.table_name}
                    (key, value, created_at, expires_at, hit_count, last_accessed)
                    VALUES (?, ?, ?, ?, 0, ?)
                """, (key, value_json, now.isoformat(), expires_at.isoformat(), now.isoformat()))
                
                conn.commit()
                return True
                
        except Exception as e:
            self.logger.error(f"Database cache set error: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Delete key from database cache"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(f"DELETE FROM {self.table_name} WHERE key = ?", (key,))
                conn.commit()
                return cursor.rowcount > 0
                
        except Exception as e:
            self.logger.error(f"Database cache delete error: {e}")
            return False

    def cleanup_expired(self) -> int:
        """Remove expired entries and return count of removed entries"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(f"""
                    DELETE FROM {self.table_name}
                    WHERE expires_at < ?
                """, (datetime.now().isoformat(),))
                conn.commit()
                return cursor.rowcount
                
        except Exception as e:
            self.logger.error(f"Database cache cleanup error: {e}")
            return 0


class SmartCacheManager:
    """Unified cache manager with multiple cache layers"""
    
    def __init__(self, config: Dict[str, Any] = None):
        config = config or {}
        
        # Initialize cache layers
        self.memory_cache = IntelligentCache(
            max_size_mb=config.get('memory_cache_size_mb', 50),
            default_ttl=config.get('memory_cache_ttl', 300)
        )
        
        self.db_cache = DatabaseCache(
            db_path=config.get('db_cache_path', 'data/cache.db'),
            table_name=config.get('db_cache_table', 'cache')
        )
        
        self.logger = logging.getLogger(__name__)

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache (memory first, then database)"""
        # Try memory cache first
        value = self.memory_cache.get(key)
        if value is not None:
            return value
        
        # Try database cache
        value = self.db_cache.get(key)
        if value is not None:
            # Promote to memory cache
            self.memory_cache.set(key, value, ttl=300)
            return value
        
        return None

    def set(self, key: str, value: Any, ttl: int = 300, persist: bool = True) -> bool:
        """Set value in cache"""
        # Always set in memory cache
        memory_success = self.memory_cache.set(key, value, ttl)
        
        # Set in database cache if persistence is enabled
        db_success = True
        if persist:
            db_success = self.db_cache.set(key, value, ttl)
        
        return memory_success and db_success

    def delete(self, key: str) -> bool:
        """Delete key from all cache layers"""
        memory_success = self.memory_cache.delete(key)
        db_success = self.db_cache.delete(key)
        return memory_success or db_success

    def clear_memory(self):
        """Clear memory cache only"""
        self.memory_cache.clear()

    def cleanup_expired(self) -> int:
        """Clean up expired entries in database cache"""
        return self.db_cache.cleanup_expired()

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        memory_stats = self.memory_cache.get_stats()
        
        return {
            'memory_cache': memory_stats,
            'database_cache': {
                'cleanup_needed': True  # Could implement DB stats here
            }
        }


def cached(ttl: int = 300, key_prefix: str = "", persist: bool = True):
    """Decorator for caching function results"""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            key_data = {
                'function': func.__name__,
                'args': args,
                'kwargs': kwargs
            }
            key_hash = hashlib.md5(json.dumps(key_data, sort_keys=True, default=str).encode()).hexdigest()
            cache_key = f"{key_prefix}:{func.__name__}:{key_hash}" if key_prefix else f"{func.__name__}:{key_hash}"
            
            # Try to get from cache
            if hasattr(func, '_cache_manager'):
                cached_result = func._cache_manager.get(cache_key)
                if cached_result is not None:
                    return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            
            if hasattr(func, '_cache_manager'):
                func._cache_manager.set(cache_key, result, ttl=ttl, persist=persist)
            
            return result
        
        return wrapper
    return decorator


# Global cache manager instance
cache_manager = SmartCacheManager()


def set_cache_config(config: Dict[str, Any]):
    """Update global cache manager configuration"""
    global cache_manager
    cache_manager = SmartCacheManager(config)


# Add cache manager to functions that need it
def add_cache_to_function(func: Callable, cache_mgr: SmartCacheManager = None):
    """Add cache manager to a function"""
    func._cache_manager = cache_mgr or cache_manager
    return func