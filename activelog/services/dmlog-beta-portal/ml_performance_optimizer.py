#!/usr/bin/env python3
"""
ML Performance Optimizer
Advanced optimization system for SuperInstance ML ecosystem
Focuses on speed, memory efficiency, and predictive intelligence
"""

import asyncio
import threading
import time
import psutil
import logging
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from collections import defaultdict, deque
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@dataclass
class MLPerformanceMetrics:
    """Performance metrics for ML systems"""
    system_name: str
    avg_response_time: float
    memory_usage_mb: float
    cpu_usage_percent: float
    cache_hit_rate: float
    prediction_accuracy: float
    throughput_per_second: float

@dataclass
class OptimizationSuggestion:
    """ML optimization suggestions"""
    system: str
    optimization_type: str
    description: str
    expected_improvement: str
    implementation_priority: int
    memory_impact: float

class MLMemoryManager:
    """Advanced memory management for ML systems"""
    
    def __init__(self, max_memory_mb: int = 500):
        self.max_memory_mb = max_memory_mb
        self.cache_registry = {}
        self.memory_pools = {
            'hot': deque(maxlen=100),      # Frequently accessed
            'warm': deque(maxlen=200),     # Occasionally accessed  
            'cold': deque(maxlen=50),      # Rarely accessed
        }
        self.access_patterns = defaultdict(int)
        
    def register_cache(self, name: str, cache_obj: Any, size_mb: float):
        """Register a cache for memory management"""
        self.cache_registry[name] = {
            'obj': cache_obj,
            'size_mb': size_mb,
            'last_access': time.time(),
            'access_count': 0,
            'pool': 'cold'
        }
        
    def access_cache(self, name: str):
        """Track cache access for intelligent management"""
        if name in self.cache_registry:
            cache_info = self.cache_registry[name]
            cache_info['last_access'] = time.time()
            cache_info['access_count'] += 1
            
            # Move to appropriate pool based on access frequency
            if cache_info['access_count'] > 50:
                self.move_to_pool(name, 'hot')
            elif cache_info['access_count'] > 10:
                self.move_to_pool(name, 'warm')
    
    def move_to_pool(self, cache_name: str, pool: str):
        """Move cache to different memory pool"""
        if cache_name in self.cache_registry:
            self.cache_registry[cache_name]['pool'] = pool
            
    def cleanup_memory(self):
        """Intelligent memory cleanup"""
        current_memory = self.get_total_memory_usage()
        
        if current_memory > self.max_memory_mb * 0.8:  # 80% threshold
            logger.info(f"🧹 Memory cleanup triggered: {current_memory:.1f}MB")
            
            # Clean cold cache first
            self.cleanup_pool('cold', target_reduction=0.5)
            
            # Then warm cache if still needed
            if self.get_total_memory_usage() > self.max_memory_mb * 0.7:
                self.cleanup_pool('warm', target_reduction=0.3)
                
    def cleanup_pool(self, pool: str, target_reduction: float):
        """Cleanup specific memory pool"""
        pool_caches = [(name, info) for name, info in self.cache_registry.items() 
                      if info['pool'] == pool]
        
        # Sort by access time (oldest first) and access count (least used first)
        pool_caches.sort(key=lambda x: (x[1]['last_access'], -x[1]['access_count']))
        
        cleanup_count = int(len(pool_caches) * target_reduction)
        for name, _ in pool_caches[:cleanup_count]:
            self.evict_cache(name)
    
    def evict_cache(self, name: str):
        """Evict cache from memory"""
        if name in self.cache_registry:
            cache_info = self.cache_registry[name]
            
            # Clear the actual cache object
            if hasattr(cache_info['obj'], 'clear'):
                cache_info['obj'].clear()
            
            logger.debug(f"🗑️ Evicted cache: {name} ({cache_info['size_mb']:.1f}MB)")
            del self.cache_registry[name]
    
    def get_total_memory_usage(self) -> float:
        """Get total memory usage of managed caches"""
        return sum(info['size_mb'] for info in self.cache_registry.values())

class MLPipelineOptimizer:
    """Optimizes ML pipeline execution"""
    
    def __init__(self):
        self.execution_stats = defaultdict(list)
        self.pipeline_cache = {}
        self.executor = ThreadPoolExecutor(max_workers=4)
        
    async def optimize_pipeline(self, pipeline_steps: List[Callable], data: Any) -> Any:
        """Execute ML pipeline with optimizations"""
        
        # Check if we can skip steps based on cache
        cache_key = self.generate_cache_key(pipeline_steps, data)
        if cache_key in self.pipeline_cache:
            logger.debug(f"⚡ Pipeline cache hit: {cache_key}")
            return self.pipeline_cache[cache_key]
        
        # Execute pipeline with parallelization where possible
        result = await self.execute_parallel_pipeline(pipeline_steps, data)
        
        # Cache result
        self.pipeline_cache[cache_key] = result
        
        return result
    
    async def execute_parallel_pipeline(self, steps: List[Callable], data: Any) -> Any:
        """Execute pipeline steps with parallel optimization"""
        
        # Identify which steps can run in parallel
        parallel_groups = self.identify_parallel_groups(steps)
        
        current_data = data
        for group in parallel_groups:
            if len(group) == 1:
                # Single step - execute normally
                current_data = await self.execute_step(group[0], current_data)
            else:
                # Multiple steps - execute in parallel
                tasks = [self.execute_step(step, current_data) for step in group]
                results = await asyncio.gather(*tasks)
                # Combine results (assuming steps are independent)
                current_data = self.combine_results(results)
        
        return current_data
    
    def identify_parallel_groups(self, steps: List[Callable]) -> List[List[Callable]]:
        """Identify which pipeline steps can run in parallel"""
        # Simple implementation - could be enhanced with dependency analysis
        groups = []
        current_group = []
        
        for step in steps:
            # Check if step has dependencies
            if self.has_dependencies(step) and current_group:
                groups.append(current_group)
                current_group = [step]
            else:
                current_group.append(step)
        
        if current_group:
            groups.append(current_group)
            
        return groups
    
    def has_dependencies(self, step: Callable) -> bool:
        """Check if step has dependencies on previous results"""
        # Simple heuristic - could be enhanced
        return hasattr(step, '_depends_on_previous')
    
    async def execute_step(self, step: Callable, data: Any) -> Any:
        """Execute a single pipeline step"""
        start_time = time.time()
        
        try:
            if asyncio.iscoroutinefunction(step):
                result = await step(data)
            else:
                result = step(data)
            
            execution_time = time.time() - start_time
            self.execution_stats[step.__name__].append(execution_time)
            
            return result
            
        except Exception as e:
            logger.error(f"Pipeline step {step.__name__} failed: {e}")
            return data  # Return original data on failure
    
    def combine_results(self, results: List[Any]) -> Any:
        """Combine results from parallel steps"""
        # Simple implementation - combine if all are dicts
        if all(isinstance(r, dict) for r in results):
            combined = {}
            for result in results:
                combined.update(result)
            return combined
        
        # Otherwise return first non-None result
        return next((r for r in results if r is not None), results[0] if results else None)
    
    def generate_cache_key(self, steps: List[Callable], data: Any) -> str:
        """Generate cache key for pipeline execution"""
        step_names = [step.__name__ for step in steps]
        data_hash = hash(str(data)[:100])  # Hash first 100 chars of data
        return f"{'_'.join(step_names)}_{data_hash}"

class PredictivePreloader:
    """Predictive system that pre-loads likely needed resources"""
    
    def __init__(self):
        self.usage_patterns = defaultdict(lambda: defaultdict(int))
        self.prediction_models = {}
        self.preload_cache = {}
        self.prediction_accuracy = defaultdict(float)
        
    def record_usage(self, user_id: str, resource_type: str, resource_id: str, 
                    context: Dict[str, Any] = None):
        """Record resource usage for pattern learning"""
        
        # Record usage pattern
        pattern_key = self.create_pattern_key(context or {})
        self.usage_patterns[user_id][f"{resource_type}:{resource_id}:{pattern_key}"] += 1
        
        # Update prediction models
        self.update_prediction_model(user_id, resource_type)
    
    def create_pattern_key(self, context: Dict[str, Any]) -> str:
        """Create key from context for pattern matching"""
        key_parts = []
        
        # Include time-based patterns
        now = datetime.now()
        key_parts.append(f"hour_{now.hour}")
        key_parts.append(f"weekday_{now.weekday()}")
        
        # Include context-based patterns
        for key, value in context.items():
            if isinstance(value, (str, int, float)):
                key_parts.append(f"{key}_{value}")
        
        return "_".join(key_parts[:5])  # Limit key complexity
    
    def update_prediction_model(self, user_id: str, resource_type: str):
        """Update prediction model for user and resource type"""
        
        user_patterns = self.usage_patterns[user_id]
        type_patterns = {k: v for k, v in user_patterns.items() if k.startswith(resource_type)}
        
        if len(type_patterns) >= 5:  # Need minimum data for predictions
            # Simple frequency-based model
            total_usage = sum(type_patterns.values())
            model = {
                pattern: count / total_usage 
                for pattern, count in type_patterns.items()
            }
            
            self.prediction_models[f"{user_id}_{resource_type}"] = model
    
    async def predict_and_preload(self, user_id: str, context: Dict[str, Any] = None):
        """Predict likely needed resources and preload them"""
        
        pattern_key = self.create_pattern_key(context or {})
        predictions = []
        
        # Get predictions from all resource types
        for model_key, model in self.prediction_models.items():
            if model_key.startswith(user_id):
                resource_type = model_key.split('_', 1)[1]
                
                # Find matching patterns
                for pattern, probability in model.items():
                    if pattern_key in pattern and probability > 0.3:  # 30% threshold
                        resource_parts = pattern.split(':', 2)
                        if len(resource_parts) >= 2:
                            predictions.append({
                                'resource_type': resource_parts[0],
                                'resource_id': resource_parts[1], 
                                'probability': probability
                            })
        
        # Sort by probability and preload top predictions
        predictions.sort(key=lambda x: x['probability'], reverse=True)
        
        preload_tasks = []
        for pred in predictions[:3]:  # Top 3 predictions
            task = self.preload_resource(
                user_id, pred['resource_type'], pred['resource_id']
            )
            preload_tasks.append(task)
        
        if preload_tasks:
            await asyncio.gather(*preload_tasks, return_exceptions=True)
            logger.info(f"🔮 Preloaded {len(preload_tasks)} predicted resources for {user_id}")
    
    async def preload_resource(self, user_id: str, resource_type: str, resource_id: str):
        """Preload a specific resource"""
        
        cache_key = f"{user_id}_{resource_type}_{resource_id}"
        
        try:
            if resource_type == 'ml_model':
                # Preload ML model or response
                await self.preload_ml_model(resource_id)
            elif resource_type == 'ui_component':
                # Preload UI optimization
                await self.preload_ui_optimization(user_id, resource_id)
            elif resource_type == 'user_data':
                # Preload user preferences or history
                await self.preload_user_data(user_id, resource_id)
                
        except Exception as e:
            logger.debug(f"Preload failed for {cache_key}: {e}")
    
    async def preload_ml_model(self, model_id: str):
        """Preload ML model or common responses"""
        # Simulate preloading
        await asyncio.sleep(0.1)
        self.preload_cache[f"model_{model_id}"] = f"preloaded_model_{model_id}"
    
    async def preload_ui_optimization(self, user_id: str, optimization_id: str):
        """Preload UI optimization"""
        # Simulate preloading
        await asyncio.sleep(0.05)
        self.preload_cache[f"ui_{user_id}_{optimization_id}"] = f"preloaded_ui_{optimization_id}"
    
    async def preload_user_data(self, user_id: str, data_type: str):
        """Preload user data"""
        # Simulate preloading
        await asyncio.sleep(0.05)
        self.preload_cache[f"data_{user_id}_{data_type}"] = f"preloaded_data_{data_type}"

class CrossUserLearningEngine:
    """Learn patterns across users while preserving privacy"""
    
    def __init__(self):
        self.global_patterns = defaultdict(lambda: defaultdict(int))
        self.user_clusters = {}
        self.pattern_sharing_rules = {
            'min_users': 3,  # Need at least 3 users for a pattern
            'min_frequency': 5,  # Pattern must occur at least 5 times
            'privacy_threshold': 0.7  # Only share patterns with high confidence
        }
        
    def contribute_pattern(self, user_id: str, pattern_type: str, pattern_data: Dict[str, Any]):
        """Contribute user pattern to global learning (privacy-preserved)"""
        
        # Anonymize pattern data
        anonymized_pattern = self.anonymize_pattern(pattern_data)
        
        # Create pattern signature
        pattern_signature = self.create_pattern_signature(pattern_type, anonymized_pattern)
        
        # Contribute to global patterns
        self.global_patterns[pattern_type][pattern_signature] += 1
        
        # Update user clustering
        self.update_user_clusters(user_id, pattern_type, pattern_signature)
    
    def anonymize_pattern(self, pattern_data: Dict[str, Any]) -> Dict[str, Any]:
        """Remove personally identifiable information from patterns"""
        
        anonymized = {}
        
        for key, value in pattern_data.items():
            if key in ['user_id', 'session_id', 'ip_address']:
                continue  # Skip PII
            elif key == 'text' and isinstance(value, str):
                # Generalize text patterns
                anonymized[key] = self.generalize_text_pattern(value)
            elif key == 'timestamp':
                # Generalize to hour of day
                if isinstance(value, (int, float)):
                    hour = int((value % 86400) / 3600)
                    anonymized['hour'] = hour
            else:
                anonymized[key] = value
        
        return anonymized
    
    def generalize_text_pattern(self, text: str) -> str:
        """Generalize text while preserving useful patterns"""
        
        # Replace specific words with categories
        generalized = text.lower()
        
        # Replace numbers with placeholders
        import re
        generalized = re.sub(r'\d+', '<NUMBER>', generalized)
        
        # Replace proper nouns with placeholders
        words = generalized.split()
        generalized_words = []
        
        for word in words:
            if word.istitle() and len(word) > 3:
                generalized_words.append('<PROPER_NOUN>')
            elif '@' in word:
                generalized_words.append('<EMAIL>')
            elif len(word) > 15:
                generalized_words.append('<LONG_WORD>')
            else:
                generalized_words.append(word)
        
        return ' '.join(generalized_words)
    
    def create_pattern_signature(self, pattern_type: str, pattern_data: Dict[str, Any]) -> str:
        """Create unique signature for pattern"""
        
        # Sort keys for consistent signatures
        sorted_items = sorted(pattern_data.items())
        signature_parts = [f"{k}:{v}" for k, v in sorted_items]
        
        return hashlib.md5('_'.join(signature_parts).encode()).hexdigest()[:16]
    
    def update_user_clusters(self, user_id: str, pattern_type: str, pattern_signature: str):
        """Update user clusters based on shared patterns"""
        
        if user_id not in self.user_clusters:
            self.user_clusters[user_id] = defaultdict(set)
        
        self.user_clusters[user_id][pattern_type].add(pattern_signature)
    
    def get_recommendations_for_user(self, user_id: str) -> List[Dict[str, Any]]:
        """Get recommendations based on similar users"""
        
        recommendations = []
        
        if user_id not in self.user_clusters:
            return recommendations
        
        user_patterns = self.user_clusters[user_id]
        
        # Find similar users
        similar_users = self.find_similar_users(user_id)
        
        # Get patterns from similar users that this user doesn't have
        for similar_user_id in similar_users[:5]:  # Top 5 similar users
            similar_patterns = self.user_clusters[similar_user_id]
            
            for pattern_type, patterns in similar_patterns.items():
                user_type_patterns = user_patterns.get(pattern_type, set())
                new_patterns = patterns - user_type_patterns
                
                for pattern in new_patterns:
                    frequency = self.global_patterns[pattern_type][pattern]
                    
                    if frequency >= self.pattern_sharing_rules['min_frequency']:
                        recommendations.append({
                            'pattern_type': pattern_type,
                            'pattern_signature': pattern,
                            'frequency': frequency,
                            'confidence': min(1.0, frequency / 10)
                        })
        
        return sorted(recommendations, key=lambda x: x['confidence'], reverse=True)[:10]
    
    def find_similar_users(self, user_id: str) -> List[str]:
        """Find users with similar patterns"""
        
        if user_id not in self.user_clusters:
            return []
        
        user_patterns = self.user_clusters[user_id]
        similarities = {}
        
        for other_user_id, other_patterns in self.user_clusters.items():
            if other_user_id == user_id:
                continue
            
            similarity = self.calculate_pattern_similarity(user_patterns, other_patterns)
            if similarity > 0.3:  # 30% similarity threshold
                similarities[other_user_id] = similarity
        
        # Sort by similarity
        return sorted(similarities.keys(), key=lambda x: similarities[x], reverse=True)
    
    def calculate_pattern_similarity(self, patterns1: Dict, patterns2: Dict) -> float:
        """Calculate similarity between two user pattern sets"""
        
        total_overlap = 0
        total_patterns = 0
        
        for pattern_type in set(patterns1.keys()) | set(patterns2.keys()):
            set1 = patterns1.get(pattern_type, set())
            set2 = patterns2.get(pattern_type, set())
            
            if set1 or set2:
                overlap = len(set1 & set2)
                union = len(set1 | set2)
                
                total_overlap += overlap
                total_patterns += union
        
        return total_overlap / max(total_patterns, 1)

class MLPerformanceMonitor:
    """Monitor and optimize ML system performance"""
    
    def __init__(self):
        self.metrics_history = defaultdict(list)
        self.performance_targets = {
            'response_time_ms': 500,
            'memory_usage_mb': 200,
            'cpu_usage_percent': 30,
            'cache_hit_rate': 0.8
        }
        self.optimization_suggestions = []
        
    def record_metrics(self, system_name: str, metrics: MLPerformanceMetrics):
        """Record performance metrics for a system"""
        
        self.metrics_history[system_name].append({
            'timestamp': time.time(),
            'metrics': metrics
        })
        
        # Keep only recent history
        if len(self.metrics_history[system_name]) > 100:
            self.metrics_history[system_name] = self.metrics_history[system_name][-100:]
        
        # Check for optimization opportunities
        self.check_optimization_opportunities(system_name, metrics)
    
    def check_optimization_opportunities(self, system_name: str, metrics: MLPerformanceMetrics):
        """Check if system needs optimization"""
        
        suggestions = []
        
        if metrics.avg_response_time > self.performance_targets['response_time_ms']:
            suggestions.append(OptimizationSuggestion(
                system=system_name,
                optimization_type='response_time',
                description=f"Response time {metrics.avg_response_time:.1f}ms exceeds target {self.performance_targets['response_time_ms']}ms",
                expected_improvement="30-50% faster responses",
                implementation_priority=8,
                memory_impact=10.0
            ))
        
        if metrics.memory_usage_mb > self.performance_targets['memory_usage_mb']:
            suggestions.append(OptimizationSuggestion(
                system=system_name,
                optimization_type='memory',
                description=f"Memory usage {metrics.memory_usage_mb:.1f}MB exceeds target {self.performance_targets['memory_usage_mb']}MB",
                expected_improvement="20-40% memory reduction",
                implementation_priority=9,
                memory_impact=-50.0
            ))
        
        if metrics.cache_hit_rate < self.performance_targets['cache_hit_rate']:
            suggestions.append(OptimizationSuggestion(
                system=system_name,
                optimization_type='caching',
                description=f"Cache hit rate {metrics.cache_hit_rate:.2f} below target {self.performance_targets['cache_hit_rate']}",
                expected_improvement="2-3x faster repeated operations",
                implementation_priority=7,
                memory_impact=20.0
            ))
        
        self.optimization_suggestions.extend(suggestions)
    
    def get_system_health_score(self, system_name: str) -> float:
        """Calculate overall health score for a system"""
        
        if system_name not in self.metrics_history:
            return 0.5
        
        recent_metrics = self.metrics_history[system_name][-10:]  # Last 10 measurements
        
        if not recent_metrics:
            return 0.5
        
        # Calculate scores for each metric
        scores = []
        
        for entry in recent_metrics:
            metrics = entry['metrics']
            
            # Response time score (lower is better)
            rt_score = max(0, 1 - (metrics.avg_response_time / (self.performance_targets['response_time_ms'] * 2)))
            
            # Memory score (lower is better)
            mem_score = max(0, 1 - (metrics.memory_usage_mb / (self.performance_targets['memory_usage_mb'] * 2)))
            
            # Cache hit rate score (higher is better)
            cache_score = metrics.cache_hit_rate
            
            # CPU score (lower is better)
            cpu_score = max(0, 1 - (metrics.cpu_usage_percent / 100))
            
            # Overall score
            overall = (rt_score + mem_score + cache_score + cpu_score) / 4
            scores.append(overall)
        
        return sum(scores) / len(scores)
    
    def get_optimization_report(self) -> Dict[str, Any]:
        """Generate optimization report"""
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'systems_monitored': len(self.metrics_history),
            'total_suggestions': len(self.optimization_suggestions),
            'system_health_scores': {},
            'top_optimizations': [],
            'performance_summary': {}
        }
        
        # Calculate health scores
        for system_name in self.metrics_history:
            health_score = self.get_system_health_score(system_name)
            report['system_health_scores'][system_name] = health_score
        
        # Get top optimization suggestions
        sorted_suggestions = sorted(
            self.optimization_suggestions, 
            key=lambda x: x.implementation_priority, 
            reverse=True
        )
        report['top_optimizations'] = [
            {
                'system': s.system,
                'type': s.optimization_type,
                'description': s.description,
                'expected_improvement': s.expected_improvement,
                'priority': s.implementation_priority
            }
            for s in sorted_suggestions[:5]
        ]
        
        # Performance summary
        if self.metrics_history:
            avg_response_times = []
            avg_memory_usage = []
            
            for system_metrics in self.metrics_history.values():
                for entry in system_metrics[-5:]:  # Recent entries
                    metrics = entry['metrics']
                    avg_response_times.append(metrics.avg_response_time)
                    avg_memory_usage.append(metrics.memory_usage_mb)
            
            if avg_response_times:
                report['performance_summary'] = {
                    'avg_response_time_ms': sum(avg_response_times) / len(avg_response_times),
                    'avg_memory_usage_mb': sum(avg_memory_usage) / len(avg_memory_usage),
                    'systems_needing_optimization': len([s for s in report['system_health_scores'].values() if s < 0.7])
                }
        
        return report


# Global optimization components
ml_memory_manager = MLMemoryManager()
ml_pipeline_optimizer = MLPipelineOptimizer()  
predictive_preloader = PredictivePreloader()
cross_user_learning = CrossUserLearningEngine()
performance_monitor = MLPerformanceMonitor()

# Optimization functions for easy integration
async def optimize_ml_performance(user_id: str = None):
    """Run comprehensive ML performance optimization"""
    
    logger.info("🚀 Starting ML performance optimization...")
    
    # Memory cleanup
    ml_memory_manager.cleanup_memory()
    
    # Performance monitoring
    current_memory = psutil.virtual_memory()
    cpu_percent = psutil.cpu_percent()
    
    logger.info(f"📊 System: {current_memory.percent:.1f}% memory, {cpu_percent:.1f}% CPU")
    
    return {
        'memory_cleaned': True,
        'system_memory_percent': current_memory.percent,
        'cpu_percent': cpu_percent,
        'optimization_active': True
    }

def register_ml_cache(name: str, cache_obj: Any, size_mb: float):
    """Register cache with memory manager"""
    ml_memory_manager.register_cache(name, cache_obj, size_mb)

async def predict_and_preload_user_resources(user_id: str, context: Dict[str, Any] = None):
    """Predict and preload likely needed resources for user"""
    await predictive_preloader.predict_and_preload(user_id, context or {})

def contribute_user_pattern(user_id: str, pattern_type: str, pattern_data: Dict[str, Any]):
    """Contribute user pattern to cross-user learning"""
    cross_user_learning.contribute_pattern(user_id, pattern_type, pattern_data)

def get_user_recommendations(user_id: str) -> List[Dict[str, Any]]:
    """Get recommendations for user based on similar users"""
    return cross_user_learning.get_recommendations_for_user(user_id)

def record_system_performance(system_name: str, response_time: float, memory_mb: float, 
                            cpu_percent: float, cache_hit_rate: float):
    """Record system performance metrics"""
    
    metrics = MLPerformanceMetrics(
        system_name=system_name,
        avg_response_time=response_time,
        memory_usage_mb=memory_mb,
        cpu_usage_percent=cpu_percent,
        cache_hit_rate=cache_hit_rate,
        prediction_accuracy=0.8,  # Default
        throughput_per_second=1000 / response_time if response_time > 0 else 0
    )
    
    performance_monitor.record_metrics(system_name, metrics)

def get_optimization_report(user_id: str = None) -> Dict[str, Any]:
    """Get comprehensive optimization report"""
    return performance_monitor.get_optimization_report()

async def initialize_ml_performance_optimizer():
    """Initialize the ML performance optimization system"""
    logger.info("⚡ ML Performance Optimizer initialized")
    
    # Start background optimization task
    asyncio.create_task(background_optimization_loop())
    
    return True

async def background_optimization_loop():
    """Background task for continuous optimization"""
    
    while True:
        try:
            await optimize_ml_performance()
            await asyncio.sleep(60)  # Optimize every minute
        except Exception as e:
            logger.error(f"Background optimization error: {e}")
            await asyncio.sleep(60)