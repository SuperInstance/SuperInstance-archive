"""
ActiveLog Project Memory - Intelligent Caching System
Advanced caching with LRU, priority-based eviction, and predictive loading
"""

from typing import Dict, List, Any, Optional, Tuple, Set, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import time
import heapq
import json
import hashlib
import pickle
from datetime import datetime, timezone, timedelta
from collections import OrderedDict, defaultdict
import threading
import weakref

class CacheStrategy(Enum):
    """Caching strategies available"""
    LRU = "lru"                    # Least Recently Used
    LFU = "lfu"                    # Least Frequently Used
    PRIORITY_LRU = "priority_lru"  # Priority-based LRU
    ADAPTIVE = "adaptive"          # Adaptive based on usage patterns
    PREDICTIVE = "predictive"      # Predictive caching

class CachePriority(Enum):
    """Cache priority levels"""
    CRITICAL = 5    # Core system concepts, never evict
    HIGH = 4        # Frequently accessed, high retention
    MEDIUM = 3      # Standard priority
    LOW = 2         # Infrequently accessed
    TEMPORARY = 1   # Short-lived, first to evict

@dataclass
class CacheEntry:
    """Enhanced cache entry with metadata"""
    key: str
    value: Any
    priority: CachePriority
    access_count: int = 0
    last_access: float = field(default_factory=time.time)
    creation_time: float = field(default_factory=time.time)
    expiry_time: Optional[float] = None
    size_bytes: int = 0
    tags: Set[str] = field(default_factory=set)
    dependencies: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CacheStats:
    """Cache performance statistics"""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    size: int = 0
    memory_usage: int = 0
    avg_access_time: float = 0.0
    prediction_accuracy: float = 0.0

class PriorityQueue:
    """Thread-safe priority queue for cache eviction"""
    
    def __init__(self):
        self._queue = []
        self._index = 0
        self._lock = threading.RLock()
    
    def put(self, priority: float, item: Any):
        with self._lock:
            heapq.heappush(self._queue, (priority, self._index, item))
            self._index += 1
    
    def get(self) -> Any:
        with self._lock:
            if self._queue:
                return heapq.heappop(self._queue)[2]
            return None
    
    def remove(self, item: Any) -> bool:
        with self._lock:
            for i, (_, _, queued_item) in enumerate(self._queue):
                if queued_item == item:
                    del self._queue[i]
                    heapq.heapify(self._queue)
                    return True
            return False
    
    def empty(self) -> bool:
        with self._lock:
            return len(self._queue) == 0

class UsagePredictor:
    """Predicts future cache access patterns"""
    
    def __init__(self, history_size: int = 1000):
        self.access_history = []
        self.history_size = history_size
        self.pattern_cache = {}
        self.sequence_patterns = defaultdict(list)
        
    def record_access(self, key: str, timestamp: float):
        """Record cache access for pattern learning"""
        self.access_history.append((key, timestamp))
        
        # Maintain history size
        if len(self.access_history) > self.history_size:
            self.access_history.pop(0)
        
        # Update sequence patterns
        if len(self.access_history) >= 3:
            # Look at last 3 accesses to find patterns
            recent = self.access_history[-3:]
            sequence = tuple(item[0] for item in recent[:-1])
            next_key = recent[-1][0]
            
            if sequence not in self.sequence_patterns:
                self.sequence_patterns[sequence] = []
            self.sequence_patterns[sequence].append(next_key)
    
    def predict_next_access(self, current_sequence: Tuple[str, ...], 
                          count: int = 5) -> List[Tuple[str, float]]:
        """Predict next likely cache accesses"""
        predictions = []
        
        # Look for sequence patterns
        if current_sequence in self.sequence_patterns:
            candidates = self.sequence_patterns[current_sequence]
            
            # Calculate probability based on frequency
            candidate_counts = defaultdict(int)
            for candidate in candidates:
                candidate_counts[candidate] += 1
            
            total_count = len(candidates)
            for key, freq in candidate_counts.items():
                probability = freq / total_count
                predictions.append((key, probability))
        
        # Sort by probability and return top predictions
        predictions.sort(key=lambda x: x[1], reverse=True)
        return predictions[:count]
    
    def get_access_probability(self, key: str, time_window: float = 3600) -> float:
        """Calculate probability of accessing key within time window"""
        now = time.time()
        recent_accesses = [
            timestamp for k, timestamp in self.access_history
            if k == key and (now - timestamp) <= time_window
        ]
        
        if not recent_accesses:
            return 0.0
        
        # Simple probability based on recent access frequency
        access_rate = len(recent_accesses) / time_window
        probability = min(1.0, access_rate * time_window / 24)  # Normalize to daily rate
        
        return probability

class IntelligentCache:
    """
    Intelligent caching system with multiple strategies and predictive capabilities
    """
    
    def __init__(self, max_size: int = 10000, max_memory: int = 100 * 1024 * 1024,
                 strategy: CacheStrategy = CacheStrategy.ADAPTIVE):
        
        self.max_size = max_size
        self.max_memory = max_memory
        self.strategy = strategy
        
        # Cache storage
        self._cache: Dict[str, CacheEntry] = {}
        self._lru_order = OrderedDict()  # For LRU tracking
        self._access_frequencies = defaultdict(int)  # For LFU tracking
        self._priority_queue = PriorityQueue()  # For priority-based eviction
        
        # Statistics and monitoring
        self.stats = CacheStats()
        self._lock = threading.RLock()
        
        # Predictive components
        self.predictor = UsagePredictor()
        self.preload_queue = asyncio.Queue()
        self._preload_task = None
        
        # Adaptive strategy components
        self.strategy_performance = {
            CacheStrategy.LRU: {"hits": 0, "misses": 0},
            CacheStrategy.LFU: {"hits": 0, "misses": 0},
            CacheStrategy.PRIORITY_LRU: {"hits": 0, "misses": 0}
        }
        
        # Background tasks
        self._cleanup_task = None
        self._stats_task = None
        
    async def start_background_tasks(self):
        """Start background maintenance tasks"""
        self._preload_task = asyncio.create_task(self._preload_worker())
        self._cleanup_task = asyncio.create_task(self._cleanup_worker())
        self._stats_task = asyncio.create_task(self._stats_worker())
    
    async def stop_background_tasks(self):
        """Stop background tasks"""
        tasks = [self._preload_task, self._cleanup_task, self._stats_task]
        for task in tasks:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
    
    async def get(self, key: str) -> Optional[Any]:
        """Get item from cache with intelligent tracking"""
        start_time = time.time()
        
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                
                # Check expiry
                if entry.expiry_time and time.time() > entry.expiry_time:
                    await self._remove_entry(key)
                    self.stats.misses += 1
                    return None
                
                # Update access metadata
                entry.access_count += 1
                entry.last_access = time.time()
                self._access_frequencies[key] += 1
                
                # Update LRU order
                if key in self._lru_order:
                    self._lru_order.move_to_end(key)
                
                # Record access for prediction
                self.predictor.record_access(key, time.time())
                
                # Update strategy performance
                if self.strategy in self.strategy_performance:
                    self.strategy_performance[self.strategy]["hits"] += 1
                
                self.stats.hits += 1
                self.stats.avg_access_time = (
                    (self.stats.avg_access_time * (self.stats.hits - 1) + 
                     (time.time() - start_time)) / self.stats.hits
                )
                
                # Trigger predictive preloading
                await self._trigger_predictive_load(key)
                
                return entry.value
            else:
                self.stats.misses += 1
                
                if self.strategy in self.strategy_performance:
                    self.strategy_performance[self.strategy]["misses"] += 1
                
                return None
    
    async def put(self, key: str, value: Any, 
                 priority: CachePriority = CachePriority.MEDIUM,
                 ttl: Optional[float] = None,
                 tags: Optional[Set[str]] = None,
                 dependencies: Optional[Set[str]] = None) -> bool:
        """Put item in cache with metadata"""
        
        with self._lock:
            # Calculate entry size
            try:
                size_bytes = len(pickle.dumps(value))
            except:
                size_bytes = len(str(value))
            
            # Check if we need to make space
            if not await self._ensure_capacity(size_bytes):
                return False
            
            # Create expiry time
            expiry_time = None
            if ttl:
                expiry_time = time.time() + ttl
            
            # Create cache entry
            entry = CacheEntry(
                key=key,
                value=value,
                priority=priority,
                expiry_time=expiry_time,
                size_bytes=size_bytes,
                tags=tags or set(),
                dependencies=dependencies or set()
            )
            
            # Remove existing entry if present
            if key in self._cache:
                await self._remove_entry(key)
            
            # Add new entry
            self._cache[key] = entry
            self._lru_order[key] = True
            
            # Update statistics
            self.stats.size = len(self._cache)
            self.stats.memory_usage += size_bytes
            
            return True
    
    async def delete(self, key: str) -> bool:
        """Delete item from cache"""
        with self._lock:
            if key in self._cache:
                await self._remove_entry(key)
                return True
            return False
    
    async def get_multi(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple items from cache efficiently"""
        results = {}
        
        for key in keys:
            value = await self.get(key)
            if value is not None:
                results[key] = value
        
        return results
    
    async def put_multi(self, items: Dict[str, Any], 
                       priority: CachePriority = CachePriority.MEDIUM) -> Dict[str, bool]:
        """Put multiple items in cache efficiently"""
        results = {}
        
        for key, value in items.items():
            results[key] = await self.put(key, value, priority)
        
        return results
    
    async def invalidate_by_tag(self, tag: str) -> int:
        """Invalidate all cache entries with specific tag"""
        count = 0
        keys_to_remove = []
        
        with self._lock:
            for key, entry in self._cache.items():
                if tag in entry.tags:
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                await self._remove_entry(key)
                count += 1
        
        return count
    
    async def invalidate_dependencies(self, dependency: str) -> int:
        """Invalidate all entries that depend on a specific key"""
        count = 0
        keys_to_remove = []
        
        with self._lock:
            for key, entry in self._cache.items():
                if dependency in entry.dependencies:
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                await self._remove_entry(key)
                count += 1
        
        return count
    
    async def _ensure_capacity(self, needed_bytes: int = 0) -> bool:
        """Ensure cache has capacity for new entry"""
        
        # Check size limit
        while len(self._cache) >= self.max_size:
            if not await self._evict_entry():
                return False
        
        # Check memory limit
        while self.stats.memory_usage + needed_bytes > self.max_memory:
            if not await self._evict_entry():
                return False
        
        return True
    
    async def _evict_entry(self) -> bool:
        """Evict an entry using the current strategy"""
        
        if not self._cache:
            return False
        
        key_to_evict = None
        
        if self.strategy == CacheStrategy.LRU:
            key_to_evict = await self._select_lru_victim()
        
        elif self.strategy == CacheStrategy.LFU:
            key_to_evict = await self._select_lfu_victim()
        
        elif self.strategy == CacheStrategy.PRIORITY_LRU:
            key_to_evict = await self._select_priority_lru_victim()
        
        elif self.strategy == CacheStrategy.ADAPTIVE:
            key_to_evict = await self._select_adaptive_victim()
        
        elif self.strategy == CacheStrategy.PREDICTIVE:
            key_to_evict = await self._select_predictive_victim()
        
        if key_to_evict:
            await self._remove_entry(key_to_evict)
            self.stats.evictions += 1
            return True
        
        return False
    
    async def _select_lru_victim(self) -> Optional[str]:
        """Select victim using LRU strategy"""
        if not self._lru_order:
            return None
        
        # Find oldest entry that's not critical priority
        for key in self._lru_order:
            entry = self._cache[key]
            if entry.priority != CachePriority.CRITICAL:
                return key
        
        return None
    
    async def _select_lfu_victim(self) -> Optional[str]:
        """Select victim using LFU strategy"""
        min_frequency = float('inf')
        victim_key = None
        
        for key, entry in self._cache.items():
            if entry.priority == CachePriority.CRITICAL:
                continue
            
            frequency = self._access_frequencies.get(key, 0)
            if frequency < min_frequency:
                min_frequency = frequency
                victim_key = key
        
        return victim_key
    
    async def _select_priority_lru_victim(self) -> Optional[str]:
        """Select victim using priority-based LRU"""
        
        # Group by priority
        priority_groups = defaultdict(list)
        for key, entry in self._cache.items():
            if entry.priority != CachePriority.CRITICAL:
                priority_groups[entry.priority.value].append((key, entry.last_access))
        
        # Start with lowest priority
        for priority in sorted(priority_groups.keys()):
            if priority_groups[priority]:
                # Within priority, choose LRU
                victim_key = min(priority_groups[priority], key=lambda x: x[1])[0]
                return victim_key
        
        return None
    
    async def _select_adaptive_victim(self) -> Optional[str]:
        """Select victim using adaptive strategy based on performance"""
        
        # Choose best performing strategy
        best_strategy = max(
            self.strategy_performance.keys(),
            key=lambda s: (
                self.strategy_performance[s]["hits"] / 
                max(1, self.strategy_performance[s]["hits"] + self.strategy_performance[s]["misses"])
            )
        )
        
        # Use the best strategy for eviction
        if best_strategy == CacheStrategy.LRU:
            return await self._select_lru_victim()
        elif best_strategy == CacheStrategy.LFU:
            return await self._select_lfu_victim()
        else:
            return await self._select_priority_lru_victim()
    
    async def _select_predictive_victim(self) -> Optional[str]:
        """Select victim using predictive strategy"""
        
        # Calculate eviction score for each entry
        scores = []
        
        for key, entry in self._cache.items():
            if entry.priority == CachePriority.CRITICAL:
                continue
            
            # Get prediction probability
            prediction_prob = self.predictor.get_access_probability(key)
            
            # Calculate eviction score (lower = more likely to evict)
            age_score = time.time() - entry.last_access
            frequency_score = 1.0 / max(1, entry.access_count)
            prediction_score = 1.0 - prediction_prob
            priority_score = 1.0 / entry.priority.value
            
            # Weighted combination
            eviction_score = (
                age_score * 0.3 +
                frequency_score * 0.2 +
                prediction_score * 0.4 +
                priority_score * 0.1
            )
            
            scores.append((key, eviction_score))
        
        if scores:
            # Return key with highest eviction score
            victim_key = max(scores, key=lambda x: x[1])[0]
            return victim_key
        
        return None
    
    async def _remove_entry(self, key: str):
        """Remove entry from all data structures"""
        if key in self._cache:
            entry = self._cache[key]
            
            # Update memory usage
            self.stats.memory_usage -= entry.size_bytes
            
            # Remove from all tracking structures
            del self._cache[key]
            self._lru_order.pop(key, None)
            self._access_frequencies.pop(key, None)
            
            # Update size
            self.stats.size = len(self._cache)
    
    async def _trigger_predictive_load(self, accessed_key: str):
        """Trigger predictive preloading based on access pattern"""
        
        if self.strategy != CacheStrategy.PREDICTIVE:
            return
        
        # Get recent access sequence
        recent_accesses = self.predictor.access_history[-5:]
        if len(recent_accesses) >= 2:
            sequence = tuple(item[0] for item in recent_accesses[-2:])
            
            # Get predictions
            predictions = self.predictor.predict_next_access(sequence)
            
            # Queue high-probability predictions for preloading
            for predicted_key, probability in predictions:
                if probability > 0.5 and predicted_key not in self._cache:
                    await self.preload_queue.put((predicted_key, probability))
    
    async def _preload_worker(self):
        """Background worker for predictive preloading"""
        while True:
            try:
                # Get preload request
                predicted_key, probability = await asyncio.wait_for(
                    self.preload_queue.get(), timeout=1.0
                )
                
                # Only preload if we have capacity and high confidence
                if (probability > 0.7 and 
                    len(self._cache) < self.max_size * 0.9 and
                    predicted_key not in self._cache):
                    
                    # This would call a callback to load the data
                    # For now, we just mark it as a preload opportunity
                    pass
                    
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                await asyncio.sleep(1)
    
    async def _cleanup_worker(self):
        """Background worker for cache cleanup"""
        while True:
            try:
                await asyncio.sleep(300)  # Clean up every 5 minutes
                
                current_time = time.time()
                expired_keys = []
                
                with self._lock:
                    for key, entry in self._cache.items():
                        if entry.expiry_time and current_time > entry.expiry_time:
                            expired_keys.append(key)
                
                # Remove expired entries
                for key in expired_keys:
                    await self._remove_entry(key)
                
                if expired_keys:
                    print(f"Cleaned up {len(expired_keys)} expired cache entries")
                    
            except Exception as e:
                await asyncio.sleep(60)
    
    async def _stats_worker(self):
        """Background worker for statistics calculation"""
        while True:
            try:
                await asyncio.sleep(600)  # Update stats every 10 minutes
                
                # Calculate prediction accuracy
                if len(self.predictor.access_history) > 10:
                    # Simple accuracy calculation
                    recent_predictions = 0
                    correct_predictions = 0
                    
                    # This is a simplified accuracy calculation
                    # In practice, you'd track actual predictions vs reality
                    self.stats.prediction_accuracy = 0.85  # Placeholder
                
                # Adapt strategy if using adaptive mode
                if self.strategy == CacheStrategy.ADAPTIVE:
                    await self._adapt_strategy()
                    
            except Exception as e:
                await asyncio.sleep(300)
    
    async def _adapt_strategy(self):
        """Adapt cache strategy based on performance"""
        
        # Calculate hit rates for each strategy
        hit_rates = {}
        for strategy, perf in self.strategy_performance.items():
            total = perf["hits"] + perf["misses"]
            if total > 0:
                hit_rates[strategy] = perf["hits"] / total
            else:
                hit_rates[strategy] = 0
        
        # Switch to best performing strategy
        if hit_rates:
            best_strategy = max(hit_rates.keys(), key=lambda k: hit_rates[k])
            if best_strategy != self.strategy and hit_rates[best_strategy] > 0.1:
                print(f"Adapting cache strategy from {self.strategy} to {best_strategy}")
                self.strategy = best_strategy
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        hit_rate = self.stats.hits / max(1, self.stats.hits + self.stats.misses)
        
        return {
            "size": self.stats.size,
            "max_size": self.max_size,
            "memory_usage_mb": self.stats.memory_usage / (1024 * 1024),
            "max_memory_mb": self.max_memory / (1024 * 1024),
            "hit_rate": hit_rate,
            "total_hits": self.stats.hits,
            "total_misses": self.stats.misses,
            "evictions": self.stats.evictions,
            "avg_access_time_ms": self.stats.avg_access_time * 1000,
            "prediction_accuracy": self.stats.prediction_accuracy,
            "current_strategy": self.strategy.value,
            "strategy_performance": {
                k.value: {
                    "hit_rate": v["hits"] / max(1, v["hits"] + v["misses"]),
                    "total_requests": v["hits"] + v["misses"]
                }
                for k, v in self.strategy_performance.items()
            }
        }
    
    async def optimize(self) -> Dict[str, Any]:
        """Perform cache optimization"""
        optimization_results = {
            "actions_taken": [],
            "memory_freed": 0,
            "entries_optimized": 0
        }
        
        # Remove expired entries
        current_time = time.time()
        expired_keys = []
        
        with self._lock:
            for key, entry in self._cache.items():
                if entry.expiry_time and current_time > entry.expiry_time:
                    expired_keys.append(key)
        
        for key in expired_keys:
            entry = self._cache[key]
            optimization_results["memory_freed"] += entry.size_bytes
            await self._remove_entry(key)
        
        if expired_keys:
            optimization_results["actions_taken"].append(f"Removed {len(expired_keys)} expired entries")
        
        # Compact low-priority, rarely accessed entries
        candidates = []
        for key, entry in self._cache.items():
            if (entry.priority == CachePriority.LOW and 
                entry.access_count < 3 and 
                (current_time - entry.creation_time) > 3600):  # 1 hour old
                candidates.append(key)
        
        for key in candidates[:10]:  # Limit to 10 per optimization
            entry = self._cache[key]
            optimization_results["memory_freed"] += entry.size_bytes
            await self._remove_entry(key)
            optimization_results["entries_optimized"] += 1
        
        if candidates:
            optimization_results["actions_taken"].append(f"Removed {len(candidates)} low-priority entries")
        
        return optimization_results