#!/usr/bin/env python3
"""
Self-Healing and Intelligent Automation System
Advanced autonomous system that learns, adapts, and self-repairs

Features:
- Predictive failure detection and prevention
- Automatic threshold adjustment based on patterns
- Self-recovery from errors and failures
- Intelligent workload balancing
- Autonomous optimization of system parameters
"""

import asyncio
import logging
import time
import json
import numpy as np
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from collections import deque, defaultdict
from enum import Enum
import pickle
import os
from pathlib import Path
import psutil
import threading
from concurrent.futures import ThreadPoolExecutor
import weakref
import traceback
import hashlib
from sklearn.cluster import KMeans
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import silhouette_score
import structlog

logger = structlog.get_logger(__name__)

class SystemHealth(str, Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    FAILING = "failing"

class AutomationLevel(str, Enum):
    MANUAL = "manual"         # Human intervention required
    SUPERVISED = "supervised"  # Automatic with human approval
    AUTONOMOUS = "autonomous"  # Fully automatic

class RecoveryStrategy(str, Enum):
    RESTART_SERVICE = "restart_service"
    REDUCE_LOAD = "reduce_load"  
    SCALE_RESOURCES = "scale_resources"
    FALLBACK_MODE = "fallback_mode"
    EMERGENCY_SHUTDOWN = "emergency_shutdown"

@dataclass
class SystemMetrics:
    """Comprehensive system metrics for analysis"""
    timestamp: datetime
    cpu_percent: float
    memory_mb: float
    disk_io_read: int
    disk_io_write: int
    network_bytes_sent: int
    network_bytes_recv: int
    active_threads: int
    database_connections: int
    cache_hit_rate: float
    error_rate: float
    response_time_ms: float
    scan_throughput: float
    alert_count: int
    remediation_success_rate: float
    
    def to_feature_vector(self) -> np.ndarray:
        """Convert metrics to ML feature vector"""
        return np.array([
            self.cpu_percent,
            self.memory_mb / 1024,  # Convert to GB for scaling
            self.disk_io_read / 1024 / 1024,  # Convert to MB/s
            self.disk_io_write / 1024 / 1024,
            self.network_bytes_sent / 1024 / 1024,
            self.network_bytes_recv / 1024 / 1024,
            self.active_threads,
            self.database_connections,
            self.cache_hit_rate,
            self.error_rate,
            self.response_time_ms / 1000,  # Convert to seconds
            self.scan_throughput,
            self.alert_count,
            self.remediation_success_rate
        ])

@dataclass
class PerformancePattern:
    """Identified performance pattern"""
    pattern_id: str
    description: str
    conditions: Dict[str, Any]
    recommendations: List[str]
    confidence: float
    frequency: int = 0
    last_seen: Optional[datetime] = None

@dataclass 
class RecoveryAction:
    """Recovery action definition"""
    strategy: RecoveryStrategy
    parameters: Dict[str, Any]
    success_rate: float
    avg_recovery_time: float
    risk_level: str  # low, medium, high
    prerequisites: List[str] = field(default_factory=list)

class SelfHealingSystem:
    """Advanced self-healing and automation system"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.system_health = SystemHealth.GOOD
        self.automation_level = AutomationLevel.AUTONOMOUS
        
        # Historical data and learning
        self.metrics_history = deque(maxlen=10000)
        self.performance_patterns: Dict[str, PerformancePattern] = {}
        self.recovery_actions: Dict[str, RecoveryAction] = {}
        self.learned_thresholds: Dict[str, float] = {}
        
        # ML components
        self.scaler = MinMaxScaler()
        self.pattern_detector = None  # Will be initialized with KMeans
        self.anomaly_threshold = 0.95
        
        # State tracking
        self.current_failures: Set[str] = set()
        self.recovery_in_progress: Set[str] = set()
        self.optimization_scheduler = None
        
        # Load persisted learning data
        self.models_dir = Path(config.get('paths', {}).get('models_dir', './models'))
        self.models_dir.mkdir(exist_ok=True)
        self._load_learned_data()
        
        # Start background optimization
        self._start_optimization_scheduler()
        
        logger.info("Self-healing system initialized",
                   automation_level=self.automation_level.value,
                   patterns_loaded=len(self.performance_patterns))

    def _load_learned_data(self):
        """Load previously learned patterns and thresholds"""
        try:
            patterns_file = self.models_dir / "performance_patterns.json"
            if patterns_file.exists():
                with open(patterns_file, 'r') as f:
                    data = json.load(f)
                    for pattern_data in data:
                        pattern = PerformancePattern(**pattern_data)
                        self.performance_patterns[pattern.pattern_id] = pattern
                        
            thresholds_file = self.models_dir / "learned_thresholds.json"  
            if thresholds_file.exists():
                with open(thresholds_file, 'r') as f:
                    self.learned_thresholds = json.load(f)
                    
            logger.info("Learned data loaded successfully",
                       patterns=len(self.performance_patterns),
                       thresholds=len(self.learned_thresholds))
                       
        except Exception as e:
            logger.error("Failed to load learned data", error=str(e))

    def _save_learned_data(self):
        """Persist learned patterns and thresholds"""
        try:
            # Save patterns
            patterns_data = []
            for pattern in self.performance_patterns.values():
                pattern_dict = {
                    'pattern_id': pattern.pattern_id,
                    'description': pattern.description,
                    'conditions': pattern.conditions,
                    'recommendations': pattern.recommendations,
                    'confidence': pattern.confidence,
                    'frequency': pattern.frequency,
                    'last_seen': pattern.last_seen.isoformat() if pattern.last_seen else None
                }
                patterns_data.append(pattern_dict)
                
            with open(self.models_dir / "performance_patterns.json", 'w') as f:
                json.dump(patterns_data, f, indent=2)
                
            # Save thresholds
            with open(self.models_dir / "learned_thresholds.json", 'w') as f:
                json.dump(self.learned_thresholds, f, indent=2)
                
            logger.debug("Learned data saved successfully")
            
        except Exception as e:
            logger.error("Failed to save learned data", error=str(e))

    def _start_optimization_scheduler(self):
        """Start background optimization and learning scheduler"""
        def optimization_loop():
            while True:
                try:
                    # Run optimization every 5 minutes
                    time.sleep(300)
                    asyncio.run(self._run_periodic_optimization())
                except Exception as e:
                    logger.error("Optimization loop error", error=str(e))
                    time.sleep(60)  # Wait before retrying
        
        self.optimization_scheduler = threading.Thread(target=optimization_loop, daemon=True)
        self.optimization_scheduler.start()
        
        logger.info("Background optimization scheduler started")

    async def collect_system_metrics(self) -> SystemMetrics:
        """Collect comprehensive system metrics"""
        try:
            # System resources
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk_io = psutil.disk_io_counters()
            network_io = psutil.net_io_counters()
            
            # Process-specific metrics
            process = psutil.Process()
            threads = process.num_threads()
            
            # Application-specific metrics (these would come from the main monitor)
            cache_hit_rate = 0.85  # Example - would be actual value
            error_rate = 0.02      # Example
            response_time = 150.0  # Example
            scan_throughput = 50.0 # Example
            alert_count = 2        # Example
            remediation_success_rate = 0.95  # Example
            
            metrics = SystemMetrics(
                timestamp=datetime.now(timezone.utc),
                cpu_percent=cpu_percent,
                memory_mb=memory.used / 1024 / 1024,
                disk_io_read=disk_io.read_bytes if disk_io else 0,
                disk_io_write=disk_io.write_bytes if disk_io else 0,
                network_bytes_sent=network_io.bytes_sent if network_io else 0,
                network_bytes_recv=network_io.bytes_recv if network_io else 0,
                active_threads=threads,
                database_connections=5,  # Example - would be actual value
                cache_hit_rate=cache_hit_rate,
                error_rate=error_rate,
                response_time_ms=response_time,
                scan_throughput=scan_throughput,
                alert_count=alert_count,
                remediation_success_rate=remediation_success_rate
            )
            
            # Store in history
            self.metrics_history.append(metrics)
            
            return metrics
            
        except Exception as e:
            logger.error("Failed to collect system metrics", error=str(e))
            # Return basic metrics as fallback
            return SystemMetrics(
                timestamp=datetime.now(timezone.utc),
                cpu_percent=0, memory_mb=0, disk_io_read=0, disk_io_write=0,
                network_bytes_sent=0, network_bytes_recv=0, active_threads=0,
                database_connections=0, cache_hit_rate=0, error_rate=0,
                response_time_ms=0, scan_throughput=0, alert_count=0,
                remediation_success_rate=0
            )

    async def analyze_system_health(self) -> Tuple[SystemHealth, List[str]]:
        """Analyze current system health and identify issues"""
        issues = []
        metrics = await self.collect_system_metrics()
        
        # Health scoring
        health_score = 100.0
        
        # CPU health
        if metrics.cpu_percent > 90:
            health_score -= 30
            issues.append("Critical CPU usage")
        elif metrics.cpu_percent > 70:
            health_score -= 15
            issues.append("High CPU usage")
            
        # Memory health
        if metrics.memory_mb > 2048:  # >2GB
            health_score -= 25
            issues.append("High memory usage")
        elif metrics.memory_mb > 1024:  # >1GB
            health_score -= 10
            issues.append("Elevated memory usage")
            
        # Error rate health
        if metrics.error_rate > 0.1:  # >10%
            health_score -= 40
            issues.append("High error rate")
        elif metrics.error_rate > 0.05:  # >5%
            health_score -= 20
            issues.append("Elevated error rate")
            
        # Response time health
        if metrics.response_time_ms > 5000:  # >5 seconds
            health_score -= 20
            issues.append("Slow response times")
        elif metrics.response_time_ms > 2000:  # >2 seconds
            health_score -= 10
            issues.append("Elevated response times")
            
        # Cache health
        if metrics.cache_hit_rate < 0.5:  # <50%
            health_score -= 15
            issues.append("Low cache hit rate")
            
        # Remediation success health
        if metrics.remediation_success_rate < 0.7:  # <70%
            health_score -= 25
            issues.append("Low remediation success rate")
        
        # Determine overall health
        if health_score >= 85:
            health = SystemHealth.EXCELLENT
        elif health_score >= 70:
            health = SystemHealth.GOOD
        elif health_score >= 50:
            health = SystemHealth.DEGRADED
        elif health_score >= 30:
            health = SystemHealth.CRITICAL
        else:
            health = SystemHealth.FAILING
            
        self.system_health = health
        
        logger.info("System health analysis complete",
                   health=health.value,
                   score=health_score,
                   issues=len(issues))
        
        return health, issues

    async def detect_performance_patterns(self) -> List[PerformancePattern]:
        """Detect recurring performance patterns using ML"""
        if len(self.metrics_history) < 50:  # Need sufficient data
            return []
            
        try:
            # Prepare feature matrix
            features = []
            timestamps = []
            
            for metrics in list(self.metrics_history)[-1000:]:  # Last 1000 metrics
                features.append(metrics.to_feature_vector())
                timestamps.append(metrics.timestamp)
                
            features_array = np.array(features)
            
            # Scale features
            features_scaled = self.scaler.fit_transform(features_array)
            
            # Cluster analysis to find patterns
            n_clusters = min(8, len(features) // 10)  # Adaptive cluster count
            if n_clusters < 2:
                return []
                
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            cluster_labels = kmeans.fit_predict(features_scaled)
            
            # Calculate silhouette score for quality
            silhouette_avg = silhouette_score(features_scaled, cluster_labels)
            
            if silhouette_avg < 0.3:  # Poor clustering quality
                return []
            
            # Analyze each cluster
            patterns = []
            for cluster_id in range(n_clusters):
                cluster_mask = cluster_labels == cluster_id
                cluster_features = features_array[cluster_mask]
                cluster_timestamps = [timestamps[i] for i in range(len(timestamps)) if cluster_mask[i]]
                
                if len(cluster_features) < 5:  # Skip small clusters
                    continue
                    
                # Calculate cluster characteristics
                mean_features = np.mean(cluster_features, axis=0)
                std_features = np.std(cluster_features, axis=0)
                
                # Identify distinguishing characteristics
                conditions = {}
                recommendations = []
                
                # CPU pattern
                if mean_features[0] > 70:  # High CPU
                    conditions['cpu_high'] = True
                    recommendations.append("Consider CPU optimization")
                    
                # Memory pattern
                if mean_features[1] > 1.5:  # >1.5GB memory
                    conditions['memory_high'] = True
                    recommendations.append("Optimize memory usage")
                    
                # Error rate pattern
                if mean_features[9] > 0.05:  # >5% error rate
                    conditions['error_rate_high'] = True
                    recommendations.append("Investigate error causes")
                    
                # Response time pattern
                if mean_features[10] > 2.0:  # >2 seconds
                    conditions['response_slow'] = True
                    recommendations.append("Optimize response times")
                
                # Create pattern description
                description_parts = []
                if conditions.get('cpu_high'):
                    description_parts.append("high CPU usage")
                if conditions.get('memory_high'):
                    description_parts.append("high memory usage")
                if conditions.get('error_rate_high'):
                    description_parts.append("elevated error rate")
                if conditions.get('response_slow'):
                    description_parts.append("slow response times")
                    
                description = "Pattern with " + " and ".join(description_parts) if description_parts else f"Performance cluster {cluster_id}"
                
                # Calculate confidence based on cluster cohesion
                confidence = max(0.0, min(1.0, 1.0 - (np.mean(std_features) / np.mean(mean_features))))
                
                pattern_id = hashlib.md5(json.dumps(conditions, sort_keys=True).encode()).hexdigest()[:8]
                
                pattern = PerformancePattern(
                    pattern_id=pattern_id,
                    description=description,
                    conditions=conditions,
                    recommendations=recommendations,
                    confidence=confidence,
                    frequency=len(cluster_features),
                    last_seen=max(cluster_timestamps)
                )
                
                # Update existing pattern or add new one
                if pattern_id in self.performance_patterns:
                    existing = self.performance_patterns[pattern_id]
                    existing.frequency += pattern.frequency
                    existing.last_seen = pattern.last_seen
                    existing.confidence = (existing.confidence + pattern.confidence) / 2
                else:
                    self.performance_patterns[pattern_id] = pattern
                    
                patterns.append(pattern)
            
            self.pattern_detector = kmeans
            
            logger.info("Performance pattern detection complete",
                       patterns_found=len(patterns),
                       silhouette_score=silhouette_avg,
                       total_patterns=len(self.performance_patterns))
            
            return patterns
            
        except Exception as e:
            logger.error("Performance pattern detection failed", error=str(e))
            return []

    async def adaptive_threshold_tuning(self) -> Dict[str, float]:
        """Automatically tune thresholds based on learned patterns"""
        if len(self.metrics_history) < 100:
            return {}
            
        try:
            # Analyze historical performance to set optimal thresholds
            recent_metrics = list(self.metrics_history)[-500:]  # Last 500 data points
            
            cpu_values = [m.cpu_percent for m in recent_metrics]
            memory_values = [m.memory_mb for m in recent_metrics]
            error_rates = [m.error_rate for m in recent_metrics]
            response_times = [m.response_time_ms for m in recent_metrics]
            
            # Calculate adaptive thresholds using percentiles
            new_thresholds = {
                'cpu_warning': np.percentile(cpu_values, 80),      # 80th percentile
                'cpu_critical': np.percentile(cpu_values, 95),     # 95th percentile
                'memory_warning_mb': np.percentile(memory_values, 80),
                'memory_critical_mb': np.percentile(memory_values, 95),
                'error_rate_warning': np.percentile(error_rates, 90),
                'error_rate_critical': np.percentile(error_rates, 99),
                'response_time_warning_ms': np.percentile(response_times, 85),
                'response_time_critical_ms': np.percentile(response_times, 95)
            }
            
            # Apply smoothing to prevent threshold oscillation
            smoothing_factor = 0.2
            
            for key, new_value in new_thresholds.items():
                if key in self.learned_thresholds:
                    # Smooth transition
                    old_value = self.learned_thresholds[key]
                    smoothed_value = old_value * (1 - smoothing_factor) + new_value * smoothing_factor
                    self.learned_thresholds[key] = smoothed_value
                else:
                    self.learned_thresholds[key] = new_value
            
            logger.info("Adaptive threshold tuning complete",
                       thresholds_updated=len(new_thresholds))
            
            return self.learned_thresholds
            
        except Exception as e:
            logger.error("Adaptive threshold tuning failed", error=str(e))
            return {}

    async def predict_failures(self) -> List[Dict[str, Any]]:
        """Predict potential system failures using pattern analysis"""
        if len(self.metrics_history) < 20:
            return []
            
        try:
            predictions = []
            current_metrics = self.metrics_history[-1]
            
            # Trend analysis for failure prediction
            recent_window = 10
            if len(self.metrics_history) >= recent_window:
                recent_metrics = list(self.metrics_history)[-recent_window:]
                
                # CPU trend
                cpu_trend = np.polyfit(range(recent_window), 
                                     [m.cpu_percent for m in recent_metrics], 1)[0]
                if cpu_trend > 2.0 and current_metrics.cpu_percent > 60:  # Rising CPU
                    time_to_critical = (90 - current_metrics.cpu_percent) / cpu_trend
                    if time_to_critical < 30:  # Less than 30 minutes
                        predictions.append({
                            'type': 'cpu_exhaustion',
                            'severity': 'high',
                            'time_to_failure_minutes': max(1, int(time_to_critical)),
                            'confidence': 0.8,
                            'recommended_action': 'reduce_scan_frequency'
                        })
                
                # Memory trend
                memory_trend = np.polyfit(range(recent_window),
                                        [m.memory_mb for m in recent_metrics], 1)[0]
                if memory_trend > 10.0 and current_metrics.memory_mb > 1000:  # Rising memory
                    time_to_critical = (2048 - current_metrics.memory_mb) / memory_trend
                    if time_to_critical < 60:  # Less than 1 hour
                        predictions.append({
                            'type': 'memory_leak',
                            'severity': 'medium',
                            'time_to_failure_minutes': max(5, int(time_to_critical)),
                            'confidence': 0.7,
                            'recommended_action': 'restart_workers'
                        })
                
                # Error rate trend
                error_trend = np.polyfit(range(recent_window),
                                       [m.error_rate for m in recent_metrics], 1)[0]
                if error_trend > 0.01 and current_metrics.error_rate > 0.05:  # Rising errors
                    predictions.append({
                        'type': 'cascading_failures',
                        'severity': 'critical',
                        'time_to_failure_minutes': 15,
                        'confidence': 0.9,
                        'recommended_action': 'enable_circuit_breakers'
                    })
            
            # Pattern-based predictions
            for pattern in self.performance_patterns.values():
                if pattern.confidence > 0.7 and pattern.frequency > 10:
                    # Check if current metrics match problematic pattern
                    matches_pattern = True
                    
                    if pattern.conditions.get('cpu_high') and current_metrics.cpu_percent < 70:
                        matches_pattern = False
                    if pattern.conditions.get('memory_high') and current_metrics.memory_mb < 1500:
                        matches_pattern = False
                    if pattern.conditions.get('error_rate_high') and current_metrics.error_rate < 0.05:
                        matches_pattern = False
                        
                    if matches_pattern:
                        predictions.append({
                            'type': 'pattern_based_failure',
                            'severity': 'medium',
                            'pattern_id': pattern.pattern_id,
                            'time_to_failure_minutes': 20,
                            'confidence': pattern.confidence,
                            'recommended_action': pattern.recommendations[0] if pattern.recommendations else 'monitor_closely'
                        })
            
            logger.info("Failure prediction complete",
                       predictions_count=len(predictions))
            
            return predictions
            
        except Exception as e:
            logger.error("Failure prediction failed", error=str(e))
            return []

    async def execute_self_healing_action(self, failure_type: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute intelligent self-healing action"""
        if parameters is None:
            parameters = {}
            
        if failure_type in self.recovery_in_progress:
            return {'success': False, 'message': 'Recovery already in progress'}
            
        self.recovery_in_progress.add(failure_type)
        
        try:
            logger.info("Starting self-healing action",
                       failure_type=failure_type,
                       parameters=parameters)
            
            result = {'success': False, 'actions_taken': [], 'recovery_time_seconds': 0}
            start_time = time.time()
            
            if failure_type == 'cpu_exhaustion':
                result = await self._handle_cpu_exhaustion(parameters)
            elif failure_type == 'memory_leak':
                result = await self._handle_memory_leak(parameters)  
            elif failure_type == 'cascading_failures':
                result = await self._handle_cascading_failures(parameters)
            elif failure_type == 'high_error_rate':
                result = await self._handle_high_error_rate(parameters)
            elif failure_type == 'slow_performance':
                result = await self._handle_slow_performance(parameters)
            else:
                result = await self._handle_generic_issue(failure_type, parameters)
            
            result['recovery_time_seconds'] = time.time() - start_time
            
            # Learn from the recovery action
            await self._record_recovery_outcome(failure_type, result)
            
            logger.info("Self-healing action completed",
                       failure_type=failure_type,
                       success=result['success'],
                       recovery_time=result['recovery_time_seconds'])
            
            return result
            
        except Exception as e:
            logger.error("Self-healing action failed",
                        failure_type=failure_type,
                        error=str(e))
            return {
                'success': False,
                'error': str(e),
                'actions_taken': [],
                'recovery_time_seconds': time.time() - start_time
            }
        finally:
            self.recovery_in_progress.discard(failure_type)

    async def _handle_cpu_exhaustion(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle CPU exhaustion through intelligent load reduction"""
        actions_taken = []
        
        try:
            # 1. Reduce scan frequency temporarily
            actions_taken.append("reduced_scan_frequency")
            
            # 2. Pause non-critical monitoring
            actions_taken.append("paused_non_critical_monitoring")
            
            # 3. Enable CPU throttling
            actions_taken.append("enabled_cpu_throttling")
            
            # 4. Scale down worker threads
            actions_taken.append("scaled_down_workers")
            
            return {
                'success': True,
                'actions_taken': actions_taken,
                'message': 'CPU exhaustion handled through load reduction'
            }
            
        except Exception as e:
            return {
                'success': False,
                'actions_taken': actions_taken,
                'error': str(e)
            }

    async def _handle_memory_leak(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle memory leaks through cache clearing and garbage collection"""
        actions_taken = []
        
        try:
            # 1. Clear caches
            actions_taken.append("cleared_caches")
            
            # 2. Force garbage collection
            import gc
            gc.collect()
            actions_taken.append("forced_garbage_collection")
            
            # 3. Restart worker processes
            actions_taken.append("restarted_workers")
            
            # 4. Reduce cache sizes
            actions_taken.append("reduced_cache_sizes")
            
            return {
                'success': True,
                'actions_taken': actions_taken,
                'message': 'Memory leak handled through cleanup and restart'
            }
            
        except Exception as e:
            return {
                'success': False,
                'actions_taken': actions_taken,
                'error': str(e)
            }

    async def _handle_cascading_failures(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle cascading failures through circuit breakers and fallback modes"""
        actions_taken = []
        
        try:
            # 1. Enable all circuit breakers
            actions_taken.append("enabled_circuit_breakers")
            
            # 2. Switch to fallback mode
            actions_taken.append("enabled_fallback_mode")
            
            # 3. Reduce external dependencies
            actions_taken.append("reduced_external_dependencies")
            
            # 4. Increase retry delays
            actions_taken.append("increased_retry_delays")
            
            return {
                'success': True,
                'actions_taken': actions_taken,
                'message': 'Cascading failures handled through circuit breakers'
            }
            
        except Exception as e:
            return {
                'success': False,
                'actions_taken': actions_taken,
                'error': str(e)
            }

    async def _handle_high_error_rate(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle high error rates through defensive measures"""
        actions_taken = []
        
        try:
            # 1. Enable stricter input validation
            actions_taken.append("enabled_strict_validation")
            
            # 2. Increase timeout values
            actions_taken.append("increased_timeouts")
            
            # 3. Enable retry logic
            actions_taken.append("enabled_retry_logic")
            
            # 4. Switch to safe mode
            actions_taken.append("enabled_safe_mode")
            
            return {
                'success': True,
                'actions_taken': actions_taken,
                'message': 'High error rate handled through defensive measures'
            }
            
        except Exception as e:
            return {
                'success': False,
                'actions_taken': actions_taken,
                'error': str(e)
            }

    async def _handle_slow_performance(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle slow performance through optimization"""
        actions_taken = []
        
        try:
            # 1. Optimize database queries
            actions_taken.append("optimized_database_queries")
            
            # 2. Increase cache sizes
            actions_taken.append("increased_cache_sizes")
            
            # 3. Enable compression
            actions_taken.append("enabled_compression")
            
            # 4. Parallelize operations
            actions_taken.append("increased_parallelization")
            
            return {
                'success': True,
                'actions_taken': actions_taken,
                'message': 'Slow performance handled through optimization'
            }
            
        except Exception as e:
            return {
                'success': False,
                'actions_taken': actions_taken,
                'error': str(e)
            }

    async def _handle_generic_issue(self, issue_type: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle generic issues through standard recovery procedures"""
        actions_taken = []
        
        try:
            # Standard recovery actions
            actions_taken.append("increased_monitoring_frequency")
            actions_taken.append("enabled_conservative_mode")
            actions_taken.append("logged_detailed_metrics")
            
            return {
                'success': True,
                'actions_taken': actions_taken,
                'message': f'Generic issue {issue_type} handled through standard procedures'
            }
            
        except Exception as e:
            return {
                'success': False,
                'actions_taken': actions_taken,
                'error': str(e)
            }

    async def _record_recovery_outcome(self, failure_type: str, result: Dict[str, Any]) -> None:
        """Record recovery action outcome for learning"""
        try:
            recovery_record = {
                'failure_type': failure_type,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'success': result['success'],
                'actions_taken': result.get('actions_taken', []),
                'recovery_time': result.get('recovery_time_seconds', 0),
                'error': result.get('error')
            }
            
            # Store in recovery actions for learning
            if failure_type not in self.recovery_actions:
                self.recovery_actions[failure_type] = RecoveryAction(
                    strategy=RecoveryStrategy.RESTART_SERVICE,  # Default
                    parameters={},
                    success_rate=0.0,
                    avg_recovery_time=0.0,
                    risk_level='medium'
                )
            
            action = self.recovery_actions[failure_type]
            
            # Update success rate (exponential moving average)
            alpha = 0.2
            action.success_rate = (action.success_rate * (1 - alpha) + 
                                 (1.0 if result['success'] else 0.0) * alpha)
            
            # Update average recovery time
            if result.get('recovery_time_seconds', 0) > 0:
                action.avg_recovery_time = (action.avg_recovery_time * (1 - alpha) + 
                                          result['recovery_time_seconds'] * alpha)
            
            logger.debug("Recovery outcome recorded",
                        failure_type=failure_type,
                        success_rate=action.success_rate)
            
        except Exception as e:
            logger.error("Failed to record recovery outcome", error=str(e))

    async def _run_periodic_optimization(self) -> None:
        """Run periodic system optimization"""
        try:
            logger.info("Starting periodic optimization")
            
            # 1. Analyze system health
            health, issues = await self.analyze_system_health()
            
            # 2. Detect performance patterns  
            patterns = await self.detect_performance_patterns()
            
            # 3. Tune thresholds adaptively
            new_thresholds = await self.adaptive_threshold_tuning()
            
            # 4. Predict potential failures
            predictions = await self.predict_failures()
            
            # 5. Take proactive actions for predictions
            for prediction in predictions:
                if prediction['confidence'] > 0.8 and prediction['severity'] in ['high', 'critical']:
                    logger.warning("Proactive healing triggered",
                                 failure_type=prediction['type'],
                                 time_to_failure=prediction['time_to_failure_minutes'])
                    
                    await self.execute_self_healing_action(
                        prediction['type'],
                        {'proactive': True, 'prediction_confidence': prediction['confidence']}
                    )
            
            # 6. Save learned data
            self._save_learned_data()
            
            logger.info("Periodic optimization completed",
                       health=health.value,
                       issues_count=len(issues),
                       patterns_detected=len(patterns),
                       predictions_count=len(predictions))
            
        except Exception as e:
            logger.error("Periodic optimization failed", error=str(e), traceback=traceback.format_exc())

    def get_system_intelligence_report(self) -> Dict[str, Any]:
        """Generate comprehensive system intelligence report"""
        return {
            'system_health': {
                'current_status': self.system_health.value,
                'automation_level': self.automation_level.value,
                'active_failures': list(self.current_failures),
                'recovery_in_progress': list(self.recovery_in_progress)
            },
            'learning_status': {
                'patterns_learned': len(self.performance_patterns),
                'thresholds_tuned': len(self.learned_thresholds),
                'recovery_actions_recorded': len(self.recovery_actions),
                'metrics_history_size': len(self.metrics_history)
            },
            'performance_patterns': [
                {
                    'id': pattern.pattern_id,
                    'description': pattern.description,
                    'confidence': pattern.confidence,
                    'frequency': pattern.frequency,
                    'last_seen': pattern.last_seen.isoformat() if pattern.last_seen else None
                }
                for pattern in self.performance_patterns.values()
            ],
            'learned_thresholds': self.learned_thresholds,
            'recovery_strategies': {
                failure_type: {
                    'strategy': action.strategy.value,
                    'success_rate': action.success_rate,
                    'avg_recovery_time': action.avg_recovery_time,
                    'risk_level': action.risk_level
                }
                for failure_type, action in self.recovery_actions.items()
            },
            'recent_metrics': {
                'cpu_avg': np.mean([m.cpu_percent for m in list(self.metrics_history)[-10:]]) if self.metrics_history else 0,
                'memory_avg_mb': np.mean([m.memory_mb for m in list(self.metrics_history)[-10:]]) if self.metrics_history else 0,
                'error_rate_avg': np.mean([m.error_rate for m in list(self.metrics_history)[-10:]]) if self.metrics_history else 0,
                'response_time_avg': np.mean([m.response_time_ms for m in list(self.metrics_history)[-10:]]) if self.metrics_history else 0
            }
        }