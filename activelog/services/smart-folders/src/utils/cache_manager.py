"""Cache management utilities"""

import asyncio
import json
import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class CacheManager:
    """Simple in-memory cache manager"""
    
    def __init__(self):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "evictions": 0
        }
        self.default_ttl = 3600  # 1 hour
    
    async def initialize(self):
        """Initialize cache manager"""
        logger.info("Cache manager initialized")
    
    def _is_expired(self, item: Dict[str, Any]) -> bool:
        """Check if cache item is expired"""
        if "expires_at" not in item:
            return False
        return datetime.utcnow() > datetime.fromisoformat(item["expires_at"])
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if key in self.cache:
            item = self.cache[key]
            
            if self._is_expired(item):
                del self.cache[key]
                self.stats["evictions"] += 1
                self.stats["misses"] += 1
                return None
            
            item["accessed_at"] = datetime.utcnow().isoformat()
            item["access_count"] = item.get("access_count", 0) + 1
            self.stats["hits"] += 1
            return item["value"]
        
        self.stats["misses"] += 1
        return None
    
    def set(self, key: str, value: Any, ttl: int = None) -> None:
        """Set value in cache"""
        ttl = ttl or self.default_ttl
        expires_at = datetime.utcnow() + timedelta(seconds=ttl)
        
        self.cache[key] = {
            "value": value,
            "created_at": datetime.utcnow().isoformat(),
            "accessed_at": datetime.utcnow().isoformat(),
            "expires_at": expires_at.isoformat(),
            "access_count": 0,
            "ttl": ttl
        }
        
        self.stats["sets"] += 1
    
    def delete(self, key: str) -> bool:
        """Delete value from cache"""
        if key in self.cache:
            del self.cache[key]
            self.stats["deletes"] += 1
            return True
        return False
    
    def clear(self) -> None:
        """Clear all cache entries"""
        cleared_count = len(self.cache)
        self.cache.clear()
        self.stats["evictions"] += cleared_count
        logger.info(f"Cleared {cleared_count} cache entries")
    
    def cleanup_expired(self) -> int:
        """Remove expired cache entries"""
        expired_keys = []
        
        for key, item in self.cache.items():
            if self._is_expired(item):
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.cache[key]
        
        self.stats["evictions"] += len(expired_keys)
        return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        stats = self.stats.copy()
        stats.update({
            "cache_size": len(self.cache),
            "hit_rate": self.stats["hits"] / max(1, self.stats["hits"] + self.stats["misses"]),
            "memory_usage": sum(
                len(str(item)) for item in self.cache.values()
            )  # Rough estimate
        })
        return stats