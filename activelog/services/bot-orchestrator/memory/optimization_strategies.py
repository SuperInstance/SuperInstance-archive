import gc
import os
import sys
import time
import psutil
import threading
import weakref
from typing import Dict, List, Optional, Callable, Any, Set, Tuple
from dataclasses import dataclass
from enum import Enum
from collections import defaultdict, deque
import sqlite3
import json
from datetime import datetime, timedelta

from .efficient_structures import (
    CompactArray, SparseArray, RingBuffer, MemoryMappedDict,
    MultiLevelCache, BloomFilter, AdaptiveCache
)

class OptimizationStrategy(Enum):
    AGGRESSIVE = "aggressive"
    MODERATE = "moderate" 
    CONSERVATIVE = "conservative"
    ADAPTIVE = "adaptive"

@dataclass
class MemoryThresholds:
    critical: float = 0.9  # 90% memory usage
    warning: float = 0.75  # 75% memory usage
    optimal: float = 0.6   # 60% memory usage
    
@dataclass
class OptimizationConfig:
    strategy: OptimizationStrategy = OptimizationStrategy.ADAPTIVE
    thresholds: MemoryThresholds = None
    gc_frequency: int = 300  # seconds
    cleanup_interval: int = 60  # seconds
    enable_compression: bool = True
    enable_memory_mapping: bool = True
    max_cache_size_mb: int = 512

class MemoryOptimizer:
    def __init__(self, config: OptimizationConfig = None):
        self.config = config or OptimizationConfig()
        if self.config.thresholds is None:
            self.config.thresholds = MemoryThresholds()
            
        self.process = psutil.Process()
        self.optimization_history = deque(maxlen=1000)
        self.memory_stats = defaultdict(list)
        
        # Track objects for cleanup
        self.tracked_objects = weakref.WeakSet()
        self.cache_objects = {}
        self.temporary_objects = set()
        
        # Optimization timers
        self.last_gc = time.time()
        self.last_cleanup = time.time()
        self.last_optimization = time.time()
        
        # Strategy patterns
        self.strategy_handlers = {
            OptimizationStrategy.AGGRESSIVE: self._aggressive_optimization,
            OptimizationStrategy.MODERATE: self._moderate_optimization,
            OptimizationStrategy.CONSERVATIVE: self._conservative_optimization,
            OptimizationStrategy.ADAPTIVE: self._adaptive_optimization
        }
        
        self.running = False
        self.optimization_thread = None
        
    def start_optimization(self):
        """Start the continuous optimization process"""
        if self.running:
            return
            
        self.running = True
        self.optimization_thread = threading.Thread(
            target=self._optimization_loop,
            daemon=True
        )
        self.optimization_thread.start()
        
    def stop_optimization(self):
        """Stop the optimization process"""
        self.running = False
        if self.optimization_thread:
            self.optimization_thread.join(timeout=5)
            
    def _optimization_loop(self):
        """Main optimization loop"""
        while self.running:
            try:
                current_usage = self.get_memory_usage()
                
                # Check if optimization is needed
                if self._should_optimize(current_usage):
                    optimization_result = self.optimize_memory()
                    self._record_optimization(optimization_result)
                    
                # Periodic garbage collection
                if time.time() - self.last_gc > self.config.gc_frequency:
                    self.force_garbage_collection()
                    
                # Periodic cleanup
                if time.time() - self.last_cleanup > self.config.cleanup_interval:
                    self.cleanup_temporary_objects()
                    
                time.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                print(f"Error in optimization loop: {e}")
                time.sleep(30)  # Wait longer on error
                
    def get_memory_usage(self) -> Dict[str, float]:
        """Get detailed memory usage information"""
        memory_info = self.process.memory_info()
        system_memory = psutil.virtual_memory()
        
        return {
            'rss_mb': memory_info.rss / 1024 / 1024,
            'vms_mb': memory_info.vms / 1024 / 1024,
            'percent': self.process.memory_percent(),
            'system_percent': system_memory.percent / 100,
            'available_mb': system_memory.available / 1024 / 1024
        }
        
    def _should_optimize(self, usage: Dict[str, float]) -> bool:
        """Determine if optimization should be triggered"""
        if usage['system_percent'] > self.config.thresholds.critical:
            return True
        if usage['percent'] > 20 and usage['system_percent'] > self.config.thresholds.warning:
            return True
        if time.time() - self.last_optimization > 3600:  # Hourly optimization
            return True
        return False
        
    def optimize_memory(self) -> Dict[str, Any]:
        """Execute memory optimization based on current strategy"""
        start_usage = self.get_memory_usage()
        start_time = time.time()
        
        # Execute strategy-specific optimization
        strategy_handler = self.strategy_handlers[self.config.strategy]
        strategy_result = strategy_handler()
        
        # Common optimizations
        gc_result = self.force_garbage_collection()
        cleanup_result = self.cleanup_temporary_objects()
        cache_result = self.optimize_caches()
        
        end_usage = self.get_memory_usage()
        optimization_time = time.time() - start_time
        
        result = {
            'timestamp': datetime.now().isoformat(),
            'strategy': self.config.strategy.value,
            'optimization_time': optimization_time,
            'memory_before': start_usage,
            'memory_after': end_usage,
            'memory_saved_mb': start_usage['rss_mb'] - end_usage['rss_mb'],
            'strategy_result': strategy_result,
            'gc_result': gc_result,
            'cleanup_result': cleanup_result,
            'cache_result': cache_result
        }
        
        self.last_optimization = time.time()
        return result
        
    def _aggressive_optimization(self) -> Dict[str, Any]:
        """Aggressive optimization strategy - maximum memory recovery"""
        results = {}
        
        # Force immediate garbage collection multiple times
        for i in range(3):
            collected = gc.collect()
            results[f'gc_round_{i+1}'] = collected
            
        # Clear all non-essential caches
        cleared_caches = 0
        for cache_name, cache_obj in list(self.cache_objects.items()):
            if hasattr(cache_obj, 'clear') and not cache_name.endswith('_essential'):
                cache_obj.clear()
                cleared_caches += 1
                
        results['cleared_caches'] = cleared_caches
        
        # Compress remaining data structures
        if self.config.enable_compression:
            compressed = self._compress_data_structures()
            results['compressed_structures'] = compressed
            
        # Force cleanup of weak references
        import weakref
        weakref.finalize._registry.clear()
        
        results['strategy'] = 'aggressive'
        return results
        
    def _moderate_optimization(self) -> Dict[str, Any]:
        """Moderate optimization strategy - balanced approach"""
        results = {}
        
        # Single garbage collection pass
        collected = gc.collect()
        results['objects_collected'] = collected
        
        # Clear only temporary caches
        cleared_caches = 0
        for cache_name, cache_obj in list(self.cache_objects.items()):
            if hasattr(cache_obj, 'clear') and 'temp' in cache_name.lower():
                cache_obj.clear()
                cleared_caches += 1
                
        results['cleared_temp_caches'] = cleared_caches
        
        # Optimize cache sizes
        optimized_caches = self._optimize_cache_sizes()
        results['optimized_caches'] = optimized_caches
        
        results['strategy'] = 'moderate'
        return results
        
    def _conservative_optimization(self) -> Dict[str, Any]:
        """Conservative optimization strategy - minimal disruption"""
        results = {}
        
        # Light garbage collection
        gc.set_threshold(700, 10, 10)  # More conservative thresholds
        collected = gc.collect()
        results['objects_collected'] = collected
        
        # Only clear expired cache entries
        expired_cleared = 0
        for cache_obj in self.cache_objects.values():
            if hasattr(cache_obj, 'clear_expired'):
                cleared = cache_obj.clear_expired()
                expired_cleared += cleared
                
        results['expired_entries_cleared'] = expired_cleared
        
        results['strategy'] = 'conservative'
        return results
        
    def _adaptive_optimization(self) -> Dict[str, Any]:
        """Adaptive optimization - changes strategy based on conditions"""
        current_usage = self.get_memory_usage()
        
        # Choose strategy based on memory pressure
        if current_usage['system_percent'] > self.config.thresholds.critical:
            return self._aggressive_optimization()
        elif current_usage['system_percent'] > self.config.thresholds.warning:
            return self._moderate_optimization()
        else:
            return self._conservative_optimization()
            
    def force_garbage_collection(self) -> Dict[str, int]:
        """Force comprehensive garbage collection"""
        # Collect statistics before
        stats_before = {
            'objects': len(gc.get_objects()),
            'gen0': len(gc.get_objects(0)),
            'gen1': len(gc.get_objects(1)),
            'gen2': len(gc.get_objects(2))
        }
        
        # Force collection of all generations
        collected = {
            'gen0': gc.collect(0),
            'gen1': gc.collect(1), 
            'gen2': gc.collect(2)
        }
        
        # Collect statistics after
        stats_after = {
            'objects': len(gc.get_objects()),
            'gen0': len(gc.get_objects(0)),
            'gen1': len(gc.get_objects(1)),
            'gen2': len(gc.get_objects(2))
        }
        
        self.last_gc = time.time()
        
        return {
            'collected': collected,
            'before': stats_before,
            'after': stats_after,
            'objects_freed': stats_before['objects'] - stats_after['objects']
        }
        
    def cleanup_temporary_objects(self) -> Dict[str, int]:
        """Clean up temporary objects and expired data"""
        results = {
            'temp_objects_cleared': 0,
            'weak_refs_cleared': 0,
            'expired_data_cleared': 0
        }
        
        # Clear temporary objects
        temp_objects = list(self.temporary_objects)
        self.temporary_objects.clear()
        results['temp_objects_cleared'] = len(temp_objects)
        
        # Clean up expired weak references
        alive_objects = set()
        for obj in self.tracked_objects:
            try:
                # Access the object to check if it's still alive
                _ = obj
                alive_objects.add(obj)
            except:
                results['weak_refs_cleared'] += 1
                
        # Clear expired cache entries
        for cache_obj in self.cache_objects.values():
            if hasattr(cache_obj, 'clear_expired'):
                cleared = cache_obj.clear_expired()
                results['expired_data_cleared'] += cleared
                
        self.last_cleanup = time.time()
        return results
        
    def optimize_caches(self) -> Dict[str, Any]:
        """Optimize all cache objects"""
        results = {
            'caches_optimized': 0,
            'memory_freed_mb': 0,
            'hit_rates': {}
        }
        
        for cache_name, cache_obj in self.cache_objects.items():
            if hasattr(cache_obj, 'optimize'):
                cache_obj.optimize()
                results['caches_optimized'] += 1
                
            # Track hit rates for adaptive optimization
            if hasattr(cache_obj, 'get_hit_rate'):
                results['hit_rates'][cache_name] = cache_obj.get_hit_rate()
                
        return results
        
    def _compress_data_structures(self) -> int:
        """Compress data structures when possible"""
        compressed_count = 0
        
        for obj in self.tracked_objects:
            try:
                if hasattr(obj, 'compress'):
                    obj.compress()
                    compressed_count += 1
            except:
                pass  # Object may have been deleted
                
        return compressed_count
        
    def _optimize_cache_sizes(self) -> int:
        """Optimize cache sizes based on usage patterns"""
        optimized_count = 0
        
        for cache_obj in self.cache_objects.values():
            if hasattr(cache_obj, 'auto_resize'):
                cache_obj.auto_resize()
                optimized_count += 1
                
        return optimized_count
        
    def register_cache(self, name: str, cache_obj: Any):
        """Register a cache object for optimization"""
        self.cache_objects[name] = cache_obj
        
    def register_object(self, obj: Any):
        """Register an object for tracking and optimization"""
        self.tracked_objects.add(obj)
        
    def add_temporary_object(self, obj: Any):
        """Mark an object as temporary for cleanup"""
        self.temporary_objects.add(obj)
        
    def _record_optimization(self, result: Dict[str, Any]):
        """Record optimization results for analysis"""
        self.optimization_history.append(result)
        
        # Update memory statistics
        self.memory_stats['rss_mb'].append(result['memory_after']['rss_mb'])
        self.memory_stats['percent'].append(result['memory_after']['percent'])
        self.memory_stats['system_percent'].append(result['memory_after']['system_percent'])
        
        # Keep only recent statistics
        for key in self.memory_stats:
            if len(self.memory_stats[key]) > 1000:
                self.memory_stats[key] = self.memory_stats[key][-500:]
                
    def get_optimization_report(self) -> Dict[str, Any]:
        """Generate comprehensive optimization report"""
        if not self.optimization_history:
            return {'error': 'No optimization history available'}
            
        recent_optimizations = list(self.optimization_history)[-10:]
        
        # Calculate averages
        avg_memory_saved = sum(opt.get('memory_saved_mb', 0) for opt in recent_optimizations) / len(recent_optimizations)
        avg_optimization_time = sum(opt.get('optimization_time', 0) for opt in recent_optimizations) / len(recent_optimizations)
        
        current_usage = self.get_memory_usage()
        
        return {
            'current_memory_usage': current_usage,
            'optimization_config': {
                'strategy': self.config.strategy.value,
                'thresholds': {
                    'critical': self.config.thresholds.critical,
                    'warning': self.config.thresholds.warning,
                    'optimal': self.config.thresholds.optimal
                }
            },
            'performance_metrics': {
                'avg_memory_saved_mb': avg_memory_saved,
                'avg_optimization_time': avg_optimization_time,
                'total_optimizations': len(self.optimization_history)
            },
            'recent_optimizations': recent_optimizations[-5:],
            'cache_status': {
                'registered_caches': len(self.cache_objects),
                'tracked_objects': len(self.tracked_objects),
                'temporary_objects': len(self.temporary_objects)
            }
        }

class SmartGarbageCollector:
    """Advanced garbage collection with intelligent scheduling"""
    
    def __init__(self):
        self.collection_stats = deque(maxlen=100)
        self.generation_thresholds = [700, 10, 10]  # Default thresholds
        self.adaptive_mode = True
        self.last_collection_time = time.time()
        
    def configure_adaptive_gc(self, enable: bool = True):
        """Enable or disable adaptive garbage collection"""
        self.adaptive_mode = enable
        if enable:
            self._optimize_thresholds()
            
    def _optimize_thresholds(self):
        """Optimize GC thresholds based on collection statistics"""
        if len(self.collection_stats) < 10:
            return
            
        # Analyze recent collection patterns
        recent_stats = list(self.collection_stats)[-10:]
        avg_objects_freed = sum(stat.get('objects_freed', 0) for stat in recent_stats) / len(recent_stats)
        avg_collection_time = sum(stat.get('collection_time', 0) for stat in recent_stats) / len(recent_stats)
        
        # Adjust thresholds based on efficiency
        if avg_objects_freed < 100 and avg_collection_time > 0.1:
            # Collections are inefficient, increase thresholds
            self.generation_thresholds[0] = min(1000, self.generation_thresholds[0] + 100)
        elif avg_objects_freed > 500 and avg_collection_time < 0.05:
            # Collections are very efficient, decrease thresholds
            self.generation_thresholds[0] = max(500, self.generation_thresholds[0] - 50)
            
        # Apply new thresholds
        gc.set_threshold(*self.generation_thresholds)
        
    def smart_collect(self, generation: Optional[int] = None) -> Dict[str, Any]:
        """Perform intelligent garbage collection"""
        start_time = time.time()
        objects_before = len(gc.get_objects())
        
        if generation is None:
            # Collect all generations
            collected = {
                'gen0': gc.collect(0),
                'gen1': gc.collect(1),
                'gen2': gc.collect(2)
            }
        else:
            collected = gc.collect(generation)
            
        objects_after = len(gc.get_objects())
        collection_time = time.time() - start_time
        
        stats = {
            'timestamp': datetime.now().isoformat(),
            'generation': generation,
            'objects_before': objects_before,
            'objects_after': objects_after,
            'objects_freed': objects_before - objects_after,
            'collection_time': collection_time,
            'collected': collected
        }
        
        self.collection_stats.append(stats)
        self.last_collection_time = time.time()
        
        # Update thresholds if adaptive mode is enabled
        if self.adaptive_mode:
            self._optimize_thresholds()
            
        return stats
        
    def get_gc_stats(self) -> Dict[str, Any]:
        """Get comprehensive garbage collection statistics"""
        gc_stats = gc.get_stats()
        
        return {
            'generation_stats': gc_stats,
            'current_thresholds': gc.get_threshold(),
            'recent_collections': list(self.collection_stats)[-5:],
            'adaptive_mode': self.adaptive_mode,
            'objects_by_generation': {
                'gen0': len(gc.get_objects(0)),
                'gen1': len(gc.get_objects(1)), 
                'gen2': len(gc.get_objects(2))
            }
        }

# Global optimizer instance
global_optimizer = None

def get_memory_optimizer(config: OptimizationConfig = None) -> MemoryOptimizer:
    """Get or create global memory optimizer instance"""
    global global_optimizer
    if global_optimizer is None:
        global_optimizer = MemoryOptimizer(config)
        global_optimizer.start_optimization()
    return global_optimizer

def optimize_memory_for_bots() -> Dict[str, Any]:
    """Convenience function to optimize memory for bot operations"""
    optimizer = get_memory_optimizer()
    return optimizer.optimize_memory()

if __name__ == "__main__":
    # Example usage
    config = OptimizationConfig(
        strategy=OptimizationStrategy.ADAPTIVE,
        thresholds=MemoryThresholds(critical=0.85, warning=0.7, optimal=0.5)
    )
    
    optimizer = MemoryOptimizer(config)
    optimizer.start_optimization()
    
    # Run for a while
    try:
        time.sleep(60)
        report = optimizer.get_optimization_report()
        print(json.dumps(report, indent=2))
    finally:
        optimizer.stop_optimization()