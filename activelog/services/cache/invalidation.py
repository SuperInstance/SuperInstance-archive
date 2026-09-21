"""
Cache Invalidation Strategies
Implements intelligent cache invalidation patterns and strategies
"""

import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any, Callable
from enum import Enum
from dataclasses import dataclass
from .redis_client import get_redis_client, RedisClient

logger = logging.getLogger(__name__)


class InvalidationType(Enum):
    """Types of cache invalidation"""
    IMMEDIATE = "immediate"
    LAZY = "lazy"
    TIME_BASED = "time_based"
    WRITE_THROUGH = "write_through"
    WRITE_BEHIND = "write_behind"
    DEPENDENCY_BASED = "dependency_based"


@dataclass
class InvalidationRule:
    """Cache invalidation rule configuration"""
    cache_type: str
    invalidation_type: InvalidationType
    ttl_override: Optional[int] = None
    dependencies: List[str] = None
    conditions: Dict[str, Any] = None
    callback: Optional[Callable] = None


class CacheInvalidationManager:
    """Manages cache invalidation strategies and execution"""
    
    def __init__(self, redis_client: Optional[RedisClient] = None):
        self.redis = redis_client or get_redis_client()
        
        # Invalidation rules registry
        self.invalidation_rules: Dict[str, List[InvalidationRule]] = {}
        
        # Dependency tracking
        self.dependency_map: Dict[str, Set[str]] = {}
        
        # Invalidation queue for batch processing
        self.invalidation_queue = []
        
        # Statistics
        self.stats = {
            'immediate_invalidations': 0,
            'lazy_invalidations': 0,
            'dependency_invalidations': 0,
            'batch_invalidations': 0
        }
        
        self._setup_default_rules()
    
    def _setup_default_rules(self):
        """Setup default invalidation rules"""
        
        # File metadata invalidation rules
        self.register_rule('file_update', InvalidationRule(
            cache_type='metadata',
            invalidation_type=InvalidationType.IMMEDIATE,
            dependencies=['file_metadata', 'user_files', 'search_results']
        ))
        
        self.register_rule('file_delete', InvalidationRule(
            cache_type='metadata',
            invalidation_type=InvalidationType.IMMEDIATE,
            dependencies=['file_metadata', 'user_files', 'search_results', 'analytics']
        ))
        
        self.register_rule('user_permission_change', InvalidationRule(
            cache_type='permissions',
            invalidation_type=InvalidationType.IMMEDIATE,
            dependencies=['user_permissions', 'role_permissions', 'session_data']
        ))
        
        self.register_rule('search_index_update', InvalidationRule(
            cache_type='search',
            invalidation_type=InvalidationType.LAZY,
            ttl_override=300  # 5 minutes
        ))
        
        self.register_rule('analytics_update', InvalidationRule(
            cache_type='analytics',
            invalidation_type=InvalidationType.TIME_BASED,
            ttl_override=1800  # 30 minutes
        ))
    
    def register_rule(self, event_type: str, rule: InvalidationRule):
        """Register an invalidation rule for an event type"""
        if event_type not in self.invalidation_rules:
            self.invalidation_rules[event_type] = []
        
        self.invalidation_rules[event_type].append(rule)
        
        # Update dependency map
        if rule.dependencies:
            for dependency in rule.dependencies:
                if dependency not in self.dependency_map:
                    self.dependency_map[dependency] = set()
                self.dependency_map[dependency].add(event_type)
        
        logger.debug(f"Registered invalidation rule for {event_type}: {rule}")
    
    def invalidate(self, event_type: str, context: Dict[str, Any] = None):
        """Execute invalidation based on event type"""
        if event_type not in self.invalidation_rules:
            logger.warning(f"No invalidation rules found for event type: {event_type}")
            return
        
        context = context or {}
        
        for rule in self.invalidation_rules[event_type]:
            try:
                self._execute_invalidation_rule(rule, context)
            except Exception as e:
                logger.error(f"Failed to execute invalidation rule {rule}: {e}")
    
    def _execute_invalidation_rule(self, rule: InvalidationRule, context: Dict[str, Any]):
        """Execute a specific invalidation rule"""
        
        if rule.invalidation_type == InvalidationType.IMMEDIATE:
            self._immediate_invalidation(rule, context)
            self.stats['immediate_invalidations'] += 1
            
        elif rule.invalidation_type == InvalidationType.LAZY:
            self._lazy_invalidation(rule, context)
            self.stats['lazy_invalidations'] += 1
            
        elif rule.invalidation_type == InvalidationType.TIME_BASED:
            self._time_based_invalidation(rule, context)
            
        elif rule.invalidation_type == InvalidationType.DEPENDENCY_BASED:
            self._dependency_based_invalidation(rule, context)
            self.stats['dependency_invalidations'] += 1
            
        elif rule.invalidation_type == InvalidationType.WRITE_THROUGH:
            self._write_through_invalidation(rule, context)
            
        elif rule.invalidation_type == InvalidationType.WRITE_BEHIND:
            self._write_behind_invalidation(rule, context)
        
        # Execute callback if provided
        if rule.callback:
            try:
                rule.callback(rule, context)
            except Exception as e:
                logger.error(f"Invalidation callback failed: {e}")
    
    def _immediate_invalidation(self, rule: InvalidationRule, context: Dict[str, Any]):
        """Immediate cache invalidation"""
        cache_type = rule.cache_type
        
        if 'file_id' in context:
            file_id = context['file_id']
            
            # Invalidate file-specific caches
            self.redis.delete(cache_type, f"file:{file_id}")
            self.redis.delete(cache_type, f"content:{file_id}")
            self.redis.delete(cache_type, f"tags:{file_id}")
            self.redis.delete(cache_type, f"perms:{file_id}")
            
            # Invalidate related user cache
            if 'user_id' in context:
                user_id = context['user_id']
                self.redis.delete(cache_type, f"user_files:{user_id}")
                self.redis.delete(cache_type, f"user_file_data:{user_id}")
        
        elif 'user_id' in context:
            user_id = context['user_id']
            
            # Invalidate user-specific caches
            self.redis.delete_pattern(f"{self.redis.prefixes[cache_type]}*{user_id}*")
        
        elif 'tag_name' in context:
            tag_name = context['tag_name']
            
            # Invalidate tag-related caches
            self.redis.delete(cache_type, f"tag_files:{tag_name.lower()}")
        
        # Invalidate dependencies
        if rule.dependencies:
            for dependency in rule.dependencies:
                if dependency == 'search_results':
                    self.redis.clear_prefix('search')
                elif dependency == 'analytics':
                    self.redis.clear_prefix('analytics')
    
    def _lazy_invalidation(self, rule: InvalidationRule, context: Dict[str, Any]):
        """Lazy invalidation - mark as stale but don't remove immediately"""
        cache_type = rule.cache_type
        
        # Add stale marker with shorter TTL
        stale_ttl = rule.ttl_override or 300  # 5 minutes default
        
        if 'file_id' in context:
            file_id = context['file_id']
            stale_marker = {
                'stale': True,
                'stale_since': datetime.utcnow().isoformat(),
                'context': context
            }
            
            self.redis.set(cache_type, f"stale:file:{file_id}", stale_marker, stale_ttl)
        
        # Add to lazy invalidation queue for batch processing
        self.invalidation_queue.append({
            'rule': rule,
            'context': context,
            'queued_at': datetime.utcnow().isoformat()
        })
    
    def _time_based_invalidation(self, rule: InvalidationRule, context: Dict[str, Any]):
        """Time-based invalidation with TTL updates"""
        cache_type = rule.cache_type
        new_ttl = rule.ttl_override or self.redis.default_ttl.get(cache_type, 3600)
        
        if 'file_id' in context:
            file_id = context['file_id']
            
            # Update TTL for existing cache entries
            self.redis.expire(cache_type, f"file:{file_id}", new_ttl)
            self.redis.expire(cache_type, f"content:{file_id}", new_ttl)
            self.redis.expire(cache_type, f"tags:{file_id}", new_ttl)
        
        elif 'user_id' in context:
            user_id = context['user_id']
            
            # Update TTL for user caches
            self.redis.expire(cache_type, f"user_files:{user_id}", new_ttl)
            self.redis.expire(cache_type, f"user_file_data:{user_id}", new_ttl)
    
    def _dependency_based_invalidation(self, rule: InvalidationRule, context: Dict[str, Any]):
        """Invalidation based on dependency graph"""
        if not rule.dependencies:
            return
        
        # Find all dependent cache entries
        dependent_keys = set()
        
        for dependency in rule.dependencies:
            if dependency in self.dependency_map:
                for dependent_event in self.dependency_map[dependency]:
                    dependent_keys.add(dependent_event)
        
        # Invalidate dependent caches
        for key in dependent_keys:
            cache_pattern = f"{self.redis.prefixes.get(key, key)}*"
            self.redis.delete_pattern(cache_pattern)
    
    def _write_through_invalidation(self, rule: InvalidationRule, context: Dict[str, Any]):
        """Write-through invalidation - update cache immediately"""
        if 'new_data' not in context:
            return
        
        cache_type = rule.cache_type
        new_data = context['new_data']
        
        if 'file_id' in context:
            file_id = context['file_id']
            
            # Update cache with new data
            ttl = rule.ttl_override or self.redis.default_ttl.get(cache_type, 3600)
            self.redis.set(cache_type, f"file:{file_id}", new_data, ttl)
    
    def _write_behind_invalidation(self, rule: InvalidationRule, context: Dict[str, Any]):
        """Write-behind invalidation - queue for background update"""
        # Add to background update queue
        update_item = {
            'rule': rule,
            'context': context,
            'queued_at': datetime.utcnow().isoformat(),
            'type': 'write_behind'
        }
        
        self.redis.lpush('cache', 'update_queue', update_item)
        self.redis.expire('cache', 'update_queue', 3600 * 24)  # 24 hours
    
    def process_lazy_invalidation_queue(self, batch_size: int = 100):
        """Process queued lazy invalidations"""
        if not self.invalidation_queue:
            return 0
        
        processed = 0
        current_time = datetime.utcnow()
        
        # Process items in batches
        while self.invalidation_queue and processed < batch_size:
            item = self.invalidation_queue.pop(0)
            
            # Check if item is still relevant (not too old)
            queued_time = datetime.fromisoformat(item['queued_at'])
            if current_time - queued_time > timedelta(hours=1):
                continue  # Skip old items
            
            # Execute immediate invalidation for queued item
            rule = item['rule']
            context = item['context']
            
            # Convert to immediate invalidation
            immediate_rule = InvalidationRule(
                cache_type=rule.cache_type,
                invalidation_type=InvalidationType.IMMEDIATE,
                dependencies=rule.dependencies
            )
            
            self._immediate_invalidation(immediate_rule, context)
            processed += 1
        
        self.stats['batch_invalidations'] += processed
        logger.debug(f"Processed {processed} lazy invalidations")
        
        return processed
    
    def check_stale_data(self, cache_type: str, cache_key: str) -> bool:
        """Check if cached data is marked as stale"""
        stale_marker = self.redis.get(cache_type, f"stale:{cache_key}")
        return stale_marker is not None
    
    def invalidate_by_pattern(self, cache_type: str, pattern: str) -> int:
        """Invalidate caches matching a pattern"""
        full_pattern = f"{self.redis.prefixes.get(cache_type, cache_type)}{pattern}"
        return self.redis.delete_pattern(full_pattern)
    
    def invalidate_expired_cache(self) -> int:
        """Find and invalidate expired cache entries"""
        invalidated_count = 0
        
        # Get all cache keys and check TTL
        for prefix_name, prefix in self.redis.prefixes.items():
            pattern = f"{prefix}*"
            keys = self.redis.client.keys(pattern)
            
            for key in keys:
                ttl = self.redis.client.ttl(key)
                if ttl == -1:  # Key exists but has no expiration
                    # Set default TTL
                    default_ttl = self.redis.default_ttl.get(prefix_name, 3600)
                    self.redis.client.expire(key, default_ttl)
                elif ttl == -2:  # Key doesn't exist
                    invalidated_count += 1
        
        return invalidated_count
    
    def get_cache_dependencies(self, cache_key: str) -> List[str]:
        """Get dependencies for a cache key"""
        dependencies = []
        
        for dependency, events in self.dependency_map.items():
            if cache_key in events:
                dependencies.append(dependency)
        
        return dependencies
    
    def register_dependency(self, parent: str, child: str):
        """Register a cache dependency relationship"""
        if parent not in self.dependency_map:
            self.dependency_map[parent] = set()
        
        self.dependency_map[parent].add(child)
    
    def get_invalidation_stats(self) -> Dict[str, Any]:
        """Get invalidation statistics"""
        return {
            **self.stats,
            'registered_rules': len(self.invalidation_rules),
            'dependency_mappings': len(self.dependency_map),
            'queue_size': len(self.invalidation_queue),
            'last_updated': datetime.utcnow().isoformat()
        }
    
    def clear_invalidation_stats(self):
        """Clear invalidation statistics"""
        self.stats = {
            'immediate_invalidations': 0,
            'lazy_invalidations': 0,
            'dependency_invalidations': 0,
            'batch_invalidations': 0
        }


class SmartCacheInvalidator:
    """Advanced cache invalidation with machine learning-based patterns"""
    
    def __init__(self, invalidation_manager: CacheInvalidationManager):
        self.invalidation_manager = invalidation_manager
        self.redis = invalidation_manager.redis
        
        # Pattern tracking
        self.access_patterns = {}
        self.invalidation_patterns = {}
    
    def track_cache_access(self, cache_type: str, cache_key: str, hit: bool):
        """Track cache access patterns"""
        pattern_key = f"{cache_type}:{cache_key}"
        
        if pattern_key not in self.access_patterns:
            self.access_patterns[pattern_key] = {
                'hits': 0,
                'misses': 0,
                'last_access': None,
                'access_frequency': []
            }
        
        pattern = self.access_patterns[pattern_key]
        current_time = datetime.utcnow()
        
        if hit:
            pattern['hits'] += 1
        else:
            pattern['misses'] += 1
        
        # Track access frequency
        if pattern['last_access']:
            time_diff = (current_time - pattern['last_access']).total_seconds()
            pattern['access_frequency'].append(time_diff)
            
            # Keep only recent frequency data
            if len(pattern['access_frequency']) > 100:
                pattern['access_frequency'] = pattern['access_frequency'][-50:]
        
        pattern['last_access'] = current_time
    
    def predict_optimal_ttl(self, cache_type: str, cache_key: str) -> Optional[int]:
        """Predict optimal TTL based on access patterns"""
        pattern_key = f"{cache_type}:{cache_key}"
        
        if pattern_key not in self.access_patterns:
            return None
        
        pattern = self.access_patterns[pattern_key]
        
        # Calculate hit rate
        total_accesses = pattern['hits'] + pattern['misses']
        if total_accesses == 0:
            return None
        
        hit_rate = pattern['hits'] / total_accesses
        
        # Calculate average access frequency
        if not pattern['access_frequency']:
            return None
        
        avg_frequency = sum(pattern['access_frequency']) / len(pattern['access_frequency'])
        
        # Predict optimal TTL based on patterns
        if hit_rate > 0.8 and avg_frequency < 300:  # High hit rate, frequent access
            return int(avg_frequency * 3)  # Cache for 3x average access interval
        elif hit_rate > 0.5:  # Moderate hit rate
            return int(avg_frequency * 2)
        else:  # Low hit rate
            return int(avg_frequency * 0.5)
    
    def suggest_invalidation_strategy(self, cache_type: str, 
                                    context: Dict[str, Any]) -> InvalidationType:
        """Suggest optimal invalidation strategy based on patterns"""
        
        # Analyze historical patterns
        if cache_type == 'metadata':
            if context.get('file_type') in ['image', 'video']:
                return InvalidationType.LAZY  # Large files benefit from lazy invalidation
            else:
                return InvalidationType.IMMEDIATE
        
        elif cache_type == 'search':
            return InvalidationType.TIME_BASED  # Search results can be time-based
        
        elif cache_type == 'analytics':
            return InvalidationType.WRITE_BEHIND  # Analytics can be updated in background
        
        else:
            return InvalidationType.IMMEDIATE  # Default to immediate


# Global invalidation manager
invalidation_manager = None


def get_invalidation_manager() -> CacheInvalidationManager:
    """Get global cache invalidation manager"""
    global invalidation_manager
    if invalidation_manager is None:
        invalidation_manager = CacheInvalidationManager()
    return invalidation_manager


def invalidate_cache(event_type: str, **context):
    """Convenience function for cache invalidation"""
    manager = get_invalidation_manager()
    manager.invalidate(event_type, context)


def register_invalidation_rule(event_type: str, rule: InvalidationRule):
    """Convenience function for registering invalidation rules"""
    manager = get_invalidation_manager()
    manager.register_rule(event_type, rule)