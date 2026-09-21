#!/usr/bin/env python3
"""
Advanced Bottleneck Analysis and Resolution System

Sophisticated analysis engine that identifies, categorizes, and provides
automated resolution for performance bottlenecks in real-time.
"""

import asyncio
import time
import threading
import psutil
import statistics
import json
import logging
import traceback
import re
from typing import Dict, List, Any, Optional, Callable, Tuple, Set
from dataclasses import dataclass, asdict
from enum import Enum
from collections import deque, defaultdict, Counter
import numpy as np
from datetime import datetime, timedelta
import pickle
import os

logger = logging.getLogger(__name__)


class AnalysisType(Enum):
    REAL_TIME = "real_time"
    HISTORICAL = "historical"
    PREDICTIVE = "predictive"
    COMPARATIVE = "comparative"


class ResolutionStrategy(Enum):
    AUTOMATIC = "automatic"
    SEMI_AUTOMATIC = "semi_automatic"
    MANUAL = "manual"
    PREVENTIVE = "preventive"


class BottleneckPattern(Enum):
    SPIKE = "spike"
    GRADUAL_DEGRADATION = "gradual_degradation"
    PERIODIC = "periodic"
    CASCADING = "cascading"
    THRESHOLD_BREACH = "threshold_breach"
    RESOURCE_EXHAUSTION = "resource_exhaustion"


@dataclass
class BottleneckSignature:
    pattern: BottleneckPattern
    characteristics: Dict[str, float]
    frequency: int
    severity_trend: List[float]
    locations: Set[str]
    first_seen: float
    last_seen: float


@dataclass
class ResolutionAction:
    id: str
    strategy: ResolutionStrategy
    description: str
    implementation: Optional[Callable]
    parameters: Dict[str, Any]
    estimated_impact: float
    risk_level: str
    prerequisites: List[str]
    rollback_plan: Optional[Dict[str, Any]]


@dataclass
class AnalysisResult:
    timestamp: float
    analysis_type: AnalysisType
    bottlenecks_found: List[Dict[str, Any]]
    patterns_detected: List[BottleneckSignature]
    resolution_actions: List[ResolutionAction]
    performance_prediction: Optional[Dict[str, float]]
    confidence_score: float


class StatisticalAnalyzer:
    """Statistical analysis for performance metrics"""
    
    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self.metrics_history = defaultdict(lambda: deque(maxlen=window_size))
        
    def add_metric(self, metric_name: str, value: float, timestamp: float = None):
        """Add metric value to history"""
        if timestamp is None:
            timestamp = time.time()
        
        self.metrics_history[metric_name].append({
            'value': value,
            'timestamp': timestamp
        })
    
    def detect_anomalies(self, metric_name: str, threshold: float = 2.0) -> List[Dict[str, Any]]:
        """Detect statistical anomalies using z-score"""
        if metric_name not in self.metrics_history:
            return []
        
        values = [item['value'] for item in self.metrics_history[metric_name]]
        if len(values) < 10:
            return []
        
        mean = statistics.mean(values)
        stdev = statistics.stdev(values)
        
        if stdev == 0:
            return []
        
        anomalies = []
        for i, item in enumerate(self.metrics_history[metric_name]):
            z_score = abs(item['value'] - mean) / stdev
            if z_score > threshold:
                anomalies.append({
                    'timestamp': item['timestamp'],
                    'value': item['value'],
                    'z_score': z_score,
                    'expected_range': (mean - threshold * stdev, mean + threshold * stdev)
                })
        
        return anomalies
    
    def detect_trends(self, metric_name: str, min_points: int = 20) -> Dict[str, Any]:
        """Detect trends in metric values"""
        if metric_name not in self.metrics_history:
            return {}
        
        values = [item['value'] for item in self.metrics_history[metric_name]]
        timestamps = [item['timestamp'] for item in self.metrics_history[metric_name]]
        
        if len(values) < min_points:
            return {}
        
        # Linear regression for trend detection
        n = len(values)
        x = list(range(n))
        
        # Calculate slope
        x_mean = statistics.mean(x)
        y_mean = statistics.mean(values)
        
        numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return {}
        
        slope = numerator / denominator
        intercept = y_mean - slope * x_mean
        
        # Calculate correlation coefficient
        correlation = self._calculate_correlation(x, values)
        
        # Determine trend direction and strength
        trend_direction = "increasing" if slope > 0 else "decreasing" if slope < 0 else "stable"
        trend_strength = abs(correlation)
        
        return {
            'direction': trend_direction,
            'strength': trend_strength,
            'slope': slope,
            'correlation': correlation,
            'confidence': min(trend_strength, 1.0),
            'time_range': (timestamps[0], timestamps[-1])
        }
    
    def _calculate_correlation(self, x: List[float], y: List[float]) -> float:
        """Calculate Pearson correlation coefficient"""
        if len(x) != len(y) or len(x) < 2:
            return 0.0
        
        n = len(x)
        x_mean = statistics.mean(x)
        y_mean = statistics.mean(y)
        
        numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
        x_variance = sum((x[i] - x_mean) ** 2 for i in range(n))
        y_variance = sum((y[i] - y_mean) ** 2 for i in range(n))
        
        if x_variance == 0 or y_variance == 0:
            return 0.0
        
        return numerator / (x_variance * y_variance) ** 0.5
    
    def detect_periodicity(self, metric_name: str) -> Optional[Dict[str, Any]]:
        """Detect periodic patterns in metrics"""
        if metric_name not in self.metrics_history:
            return None
        
        values = [item['value'] for item in self.metrics_history[metric_name]]
        timestamps = [item['timestamp'] for item in self.metrics_history[metric_name]]
        
        if len(values) < 20:
            return None
        
        # Simple autocorrelation analysis for periodicity
        max_lag = min(len(values) // 4, 50)
        autocorrelations = []
        
        for lag in range(1, max_lag):
            if len(values) > lag:
                correlation = self._autocorrelation(values, lag)
                autocorrelations.append((lag, correlation))
        
        # Find peaks in autocorrelation
        peaks = []
        for i in range(1, len(autocorrelations) - 1):
            if (autocorrelations[i][1] > autocorrelations[i-1][1] and
                autocorrelations[i][1] > autocorrelations[i+1][1] and
                autocorrelations[i][1] > 0.3):  # Minimum correlation threshold
                peaks.append(autocorrelations[i])
        
        if not peaks:
            return None
        
        # Find strongest periodic pattern
        strongest_peak = max(peaks, key=lambda x: x[1])
        lag, correlation = strongest_peak
        
        # Calculate period in time units
        if len(timestamps) > lag:
            time_period = (timestamps[lag] - timestamps[0]) * len(values) / lag
        else:
            time_period = None
        
        return {
            'period_samples': lag,
            'period_time': time_period,
            'strength': correlation,
            'confidence': min(correlation * 2, 1.0)
        }
    
    def _autocorrelation(self, values: List[float], lag: int) -> float:
        """Calculate autocorrelation at given lag"""
        if len(values) <= lag:
            return 0.0
        
        n = len(values) - lag
        x1 = values[:-lag] if lag > 0 else values
        x2 = values[lag:]
        
        return self._calculate_correlation(x1, x2)


class PatternRecognizer:
    """Advanced pattern recognition for bottleneck identification"""
    
    def __init__(self):
        self.known_patterns = {}
        self.pattern_signatures = []
        self.load_pattern_library()
    
    def load_pattern_library(self):
        """Load known bottleneck patterns"""
        self.known_patterns = {
            'memory_leak': {
                'characteristics': ['increasing_memory', 'stable_cpu', 'eventual_crash'],
                'signature': lambda metrics: (
                    metrics.get('memory_trend', {}).get('direction') == 'increasing' and
                    metrics.get('memory_trend', {}).get('strength', 0) > 0.7
                )
            },
            'cpu_spike': {
                'characteristics': ['sudden_cpu_increase', 'temporary_duration', 'potential_recovery'],
                'signature': lambda metrics: (
                    metrics.get('cpu_max', 0) > 90 and
                    metrics.get('cpu_variance', 0) > 100
                )
            },
            'io_bottleneck': {
                'characteristics': ['high_io_wait', 'low_throughput', 'queue_buildup'],
                'signature': lambda metrics: (
                    metrics.get('io_wait', 0) > 20 and
                    metrics.get('disk_busy', 0) > 80
                )
            },
            'deadlock': {
                'characteristics': ['blocking_threads', 'no_progress', 'circular_wait'],
                'signature': lambda metrics: (
                    metrics.get('blocked_threads', 0) > 0 and
                    metrics.get('progress_rate', 0) < 0.1
                )
            },
            'cascade_failure': {
                'characteristics': ['multiple_service_degradation', 'error_propagation', 'system_wide_impact'],
                'signature': lambda metrics: (
                    metrics.get('error_rate', 0) > 0.1 and
                    len(metrics.get('affected_services', [])) > 2
                )
            }
        }
    
    def recognize_patterns(self, metrics: Dict[str, Any], bottlenecks: List[Dict[str, Any]]) -> List[BottleneckSignature]:
        """Recognize patterns in current metrics and bottlenecks"""
        recognized_patterns = []
        
        for pattern_name, pattern_info in self.known_patterns.items():
            if pattern_info['signature'](metrics):
                signature = BottleneckSignature(
                    pattern=self._get_pattern_enum(pattern_name),
                    characteristics=self._extract_characteristics(metrics, pattern_info['characteristics']),
                    frequency=self._calculate_pattern_frequency(pattern_name, bottlenecks),
                    severity_trend=self._calculate_severity_trend(pattern_name, bottlenecks),
                    locations=self._extract_affected_locations(bottlenecks),
                    first_seen=time.time(),
                    last_seen=time.time()
                )
                recognized_patterns.append(signature)
        
        return recognized_patterns
    
    def _get_pattern_enum(self, pattern_name: str) -> BottleneckPattern:
        """Convert pattern name to enum"""
        pattern_mapping = {
            'memory_leak': BottleneckPattern.GRADUAL_DEGRADATION,
            'cpu_spike': BottleneckPattern.SPIKE,
            'io_bottleneck': BottleneckPattern.THRESHOLD_BREACH,
            'deadlock': BottleneckPattern.RESOURCE_EXHAUSTION,
            'cascade_failure': BottleneckPattern.CASCADING
        }
        return pattern_mapping.get(pattern_name, BottleneckPattern.THRESHOLD_BREACH)
    
    def _extract_characteristics(self, metrics: Dict[str, Any], char_list: List[str]) -> Dict[str, float]:
        """Extract characteristic values from metrics"""
        characteristics = {}
        
        for char in char_list:
            if char == 'increasing_memory':
                characteristics[char] = metrics.get('memory_trend', {}).get('strength', 0)
            elif char == 'stable_cpu':
                characteristics[char] = 1.0 - metrics.get('cpu_variance', 100) / 100
            elif char == 'sudden_cpu_increase':
                characteristics[char] = metrics.get('cpu_max', 0) / 100
            elif char == 'high_io_wait':
                characteristics[char] = metrics.get('io_wait', 0) / 100
            elif char == 'blocking_threads':
                characteristics[char] = min(metrics.get('blocked_threads', 0) / 10, 1.0)
            else:
                characteristics[char] = 0.5  # Default neutral value
        
        return characteristics
    
    def _calculate_pattern_frequency(self, pattern_name: str, bottlenecks: List[Dict[str, Any]]) -> int:
        """Calculate how frequently this pattern occurs"""
        # Simple implementation - count related bottlenecks
        related_count = 0
        for bottleneck in bottlenecks:
            if pattern_name.lower() in bottleneck.get('description', '').lower():
                related_count += 1
        return related_count
    
    def _calculate_severity_trend(self, pattern_name: str, bottlenecks: List[Dict[str, Any]]) -> List[float]:
        """Calculate severity trend for this pattern"""
        severity_values = []
        severity_mapping = {'low': 0.25, 'medium': 0.5, 'high': 0.75, 'critical': 1.0}
        
        for bottleneck in bottlenecks:
            if pattern_name.lower() in bottleneck.get('description', '').lower():
                severity = bottleneck.get('severity', 'medium')
                severity_values.append(severity_mapping.get(severity, 0.5))
        
        return severity_values if severity_values else [0.5]
    
    def _extract_affected_locations(self, bottlenecks: List[Dict[str, Any]]) -> Set[str]:
        """Extract affected locations from bottlenecks"""
        locations = set()
        for bottleneck in bottlenecks:
            if 'location' in bottleneck:
                locations.add(bottleneck['location'])
        return locations


class ResolutionEngine:
    """Automated resolution engine for performance bottlenecks"""
    
    def __init__(self):
        self.resolution_strategies = {}
        self.applied_actions = []
        self.action_effectiveness = defaultdict(list)
        self.load_resolution_strategies()
    
    def load_resolution_strategies(self):
        """Load resolution strategies for different bottleneck types"""
        self.resolution_strategies = {
            BottleneckPattern.SPIKE: [
                ResolutionAction(
                    id="scale_resources",
                    strategy=ResolutionStrategy.AUTOMATIC,
                    description="Temporarily scale up resources",
                    implementation=self._scale_resources,
                    parameters={'scale_factor': 1.5, 'duration': 300},
                    estimated_impact=0.8,
                    risk_level="low",
                    prerequisites=["auto_scaling_enabled"],
                    rollback_plan={"action": "scale_down", "timeout": 600}
                ),
                ResolutionAction(
                    id="enable_circuit_breaker",
                    strategy=ResolutionStrategy.AUTOMATIC,
                    description="Enable circuit breaker to prevent cascade failures",
                    implementation=self._enable_circuit_breaker,
                    parameters={'failure_threshold': 10, 'timeout': 60},
                    estimated_impact=0.6,
                    risk_level="low",
                    prerequisites=[],
                    rollback_plan={"action": "disable_circuit_breaker", "timeout": 300}
                )
            ],
            BottleneckPattern.GRADUAL_DEGRADATION: [
                ResolutionAction(
                    id="gc_optimization",
                    strategy=ResolutionStrategy.SEMI_AUTOMATIC,
                    description="Optimize garbage collection settings",
                    implementation=self._optimize_gc,
                    parameters={'max_heap': '2g', 'gc_algorithm': 'G1'},
                    estimated_impact=0.7,
                    risk_level="medium",
                    prerequisites=["memory_profiling_data"],
                    rollback_plan={"action": "restore_gc_settings", "timeout": 120}
                ),
                ResolutionAction(
                    id="memory_cleanup",
                    strategy=ResolutionStrategy.AUTOMATIC,
                    description="Force memory cleanup and optimization",
                    implementation=self._force_memory_cleanup,
                    parameters={'aggressive': False},
                    estimated_impact=0.5,
                    risk_level="low",
                    prerequisites=[],
                    rollback_plan=None
                )
            ],
            BottleneckPattern.RESOURCE_EXHAUSTION: [
                ResolutionAction(
                    id="emergency_scaling",
                    strategy=ResolutionStrategy.AUTOMATIC,
                    description="Emergency resource scaling",
                    implementation=self._emergency_scaling,
                    parameters={'scale_factor': 2.0, 'priority': 'high'},
                    estimated_impact=0.9,
                    risk_level="medium",
                    prerequisites=["emergency_scaling_enabled"],
                    rollback_plan={"action": "restore_original_scale", "timeout": 900}
                ),
                ResolutionAction(
                    id="load_shedding",
                    strategy=ResolutionStrategy.AUTOMATIC,
                    description="Implement load shedding to protect system",
                    implementation=self._implement_load_shedding,
                    parameters={'drop_percentage': 20, 'priority_based': True},
                    estimated_impact=0.7,
                    risk_level="high",
                    prerequisites=["load_balancer_configured"],
                    rollback_plan={"action": "disable_load_shedding", "timeout": 300}
                )
            ],
            BottleneckPattern.CASCADING: [
                ResolutionAction(
                    id="circuit_breaker_all",
                    strategy=ResolutionStrategy.AUTOMATIC,
                    description="Enable circuit breakers system-wide",
                    implementation=self._enable_system_circuit_breakers,
                    parameters={'failure_threshold': 5, 'recovery_time': 120},
                    estimated_impact=0.8,
                    risk_level="medium",
                    prerequisites=["circuit_breaker_framework"],
                    rollback_plan={"action": "disable_system_circuit_breakers", "timeout": 600}
                ),
                ResolutionAction(
                    id="graceful_degradation",
                    strategy=ResolutionStrategy.SEMI_AUTOMATIC,
                    description="Enable graceful service degradation",
                    implementation=self._enable_graceful_degradation,
                    parameters={'degradation_levels': ['non_critical', 'optional', 'enhanced']},
                    estimated_impact=0.6,
                    risk_level="low",
                    prerequisites=["service_priority_configuration"],
                    rollback_plan={"action": "restore_full_service", "timeout": 300}
                )
            ]
        }
    
    async def generate_resolution_plan(self, patterns: List[BottleneckSignature], 
                                     current_metrics: Dict[str, Any]) -> List[ResolutionAction]:
        """Generate resolution plan for detected patterns"""
        resolution_plan = []
        
        for pattern in patterns:
            if pattern.pattern in self.resolution_strategies:
                strategies = self.resolution_strategies[pattern.pattern]
                
                for strategy in strategies:
                    # Check prerequisites
                    if self._check_prerequisites(strategy.prerequisites):
                        # Adjust parameters based on current situation
                        adjusted_strategy = self._adjust_strategy_parameters(strategy, pattern, current_metrics)
                        resolution_plan.append(adjusted_strategy)
        
        # Sort by estimated impact and risk level
        resolution_plan.sort(key=lambda x: (x.estimated_impact, -self._risk_score(x.risk_level)), reverse=True)
        
        return resolution_plan
    
    def _check_prerequisites(self, prerequisites: List[str]) -> bool:
        """Check if prerequisites are met"""
        # Simplified implementation - in real system would check actual conditions
        prerequisite_checks = {
            'auto_scaling_enabled': True,
            'emergency_scaling_enabled': True,
            'load_balancer_configured': True,
            'circuit_breaker_framework': True,
            'service_priority_configuration': True,
            'memory_profiling_data': True
        }
        
        return all(prerequisite_checks.get(prereq, False) for prereq in prerequisites)
    
    def _adjust_strategy_parameters(self, strategy: ResolutionAction, 
                                  pattern: BottleneckSignature, 
                                  metrics: Dict[str, Any]) -> ResolutionAction:
        """Adjust strategy parameters based on current situation"""
        adjusted_strategy = ResolutionAction(
            id=strategy.id,
            strategy=strategy.strategy,
            description=strategy.description,
            implementation=strategy.implementation,
            parameters=strategy.parameters.copy(),
            estimated_impact=strategy.estimated_impact,
            risk_level=strategy.risk_level,
            prerequisites=strategy.prerequisites,
            rollback_plan=strategy.rollback_plan
        )
        
        # Adjust parameters based on severity
        severity_multiplier = statistics.mean(pattern.severity_trend) if pattern.severity_trend else 0.5
        
        if 'scale_factor' in adjusted_strategy.parameters:
            base_factor = adjusted_strategy.parameters['scale_factor']
            adjusted_strategy.parameters['scale_factor'] = base_factor * (1 + severity_multiplier)
        
        if 'drop_percentage' in adjusted_strategy.parameters:
            base_percentage = adjusted_strategy.parameters['drop_percentage']
            adjusted_strategy.parameters['drop_percentage'] = min(base_percentage * (1 + severity_multiplier), 50)
        
        return adjusted_strategy
    
    def _risk_score(self, risk_level: str) -> float:
        """Convert risk level to numeric score"""
        risk_scores = {'low': 0.1, 'medium': 0.5, 'high': 0.9, 'critical': 1.0}
        return risk_scores.get(risk_level, 0.5)
    
    async def _scale_resources(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Scale resources up"""
        logger.info(f"Scaling resources by factor {parameters['scale_factor']}")
        # Implementation would interact with orchestration system
        return {'status': 'success', 'scaled_factor': parameters['scale_factor']}
    
    async def _enable_circuit_breaker(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Enable circuit breaker"""
        logger.info("Enabling circuit breaker")
        # Implementation would configure circuit breaker
        return {'status': 'success', 'threshold': parameters['failure_threshold']}
    
    async def _optimize_gc(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize garbage collection"""
        logger.info("Optimizing garbage collection settings")
        # Implementation would adjust GC parameters
        return {'status': 'success', 'algorithm': parameters['gc_algorithm']}
    
    async def _force_memory_cleanup(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Force memory cleanup"""
        logger.info("Forcing memory cleanup")
        import gc
        gc.collect()
        return {'status': 'success', 'objects_collected': gc.collect()}
    
    async def _emergency_scaling(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Emergency scaling"""
        logger.warning(f"Emergency scaling by factor {parameters['scale_factor']}")
        # Implementation would trigger emergency scaling
        return {'status': 'success', 'emergency_scale': parameters['scale_factor']}
    
    async def _implement_load_shedding(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Implement load shedding"""
        logger.warning(f"Implementing load shedding at {parameters['drop_percentage']}%")
        # Implementation would configure load shedding
        return {'status': 'success', 'drop_rate': parameters['drop_percentage']}
    
    async def _enable_system_circuit_breakers(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Enable system-wide circuit breakers"""
        logger.info("Enabling system-wide circuit breakers")
        # Implementation would enable all circuit breakers
        return {'status': 'success', 'system_wide': True}
    
    async def _enable_graceful_degradation(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Enable graceful service degradation"""
        logger.info("Enabling graceful service degradation")
        # Implementation would configure service degradation
        return {'status': 'success', 'degradation_levels': parameters['degradation_levels']}


class BottleneckAnalyzer:
    """Main bottleneck analyzer with comprehensive analysis capabilities"""
    
    def __init__(self):
        self.statistical_analyzer = StatisticalAnalyzer()
        self.pattern_recognizer = PatternRecognizer()
        self.resolution_engine = ResolutionEngine()
        
        self.analysis_history = deque(maxlen=1000)
        self.active_patterns = []
        self.pending_resolutions = []
        
    async def analyze_bottlenecks(self, performance_data: Dict[str, Any], 
                                analysis_type: AnalysisType = AnalysisType.REAL_TIME) -> AnalysisResult:
        """Perform comprehensive bottleneck analysis"""
        start_time = time.time()
        
        try:
            # Extract metrics from performance data
            metrics = self._extract_metrics(performance_data)
            
            # Update statistical analyzer
            self._update_statistical_analyzer(metrics)
            
            # Perform statistical analysis
            statistical_results = await self._perform_statistical_analysis(metrics)
            
            # Detect patterns
            patterns = self.pattern_recognizer.recognize_patterns(
                statistical_results, 
                performance_data.get('bottlenecks', [])
            )
            
            # Generate resolution actions
            resolution_actions = await self.resolution_engine.generate_resolution_plan(
                patterns, 
                statistical_results
            )
            
            # Predict future performance
            performance_prediction = None
            if analysis_type == AnalysisType.PREDICTIVE:
                performance_prediction = await self._predict_performance(metrics)
            
            # Calculate confidence score
            confidence_score = self._calculate_confidence_score(
                statistical_results, patterns, len(performance_data.get('bottlenecks', []))
            )
            
            # Create analysis result
            result = AnalysisResult(
                timestamp=time.time(),
                analysis_type=analysis_type,
                bottlenecks_found=performance_data.get('bottlenecks', []),
                patterns_detected=patterns,
                resolution_actions=resolution_actions,
                performance_prediction=performance_prediction,
                confidence_score=confidence_score
            )
            
            # Store in history
            self.analysis_history.append(result)
            
            logger.info(f"Bottleneck analysis completed in {time.time() - start_time:.3f}s")
            return result
            
        except Exception as e:
            logger.error(f"Error during bottleneck analysis: {e}")
            traceback.print_exc()
            
            # Return minimal result on error
            return AnalysisResult(
                timestamp=time.time(),
                analysis_type=analysis_type,
                bottlenecks_found=[],
                patterns_detected=[],
                resolution_actions=[],
                performance_prediction=None,
                confidence_score=0.0
            )
    
    def _extract_metrics(self, performance_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metrics from performance data"""
        system_metrics = performance_data.get('system_metrics', {})
        
        return {
            'cpu_avg': system_metrics.get('cpu_avg', 0),
            'memory_avg': system_metrics.get('memory_avg', 0),
            'active_threads': system_metrics.get('active_threads', 0),
            'bottleneck_count': len(performance_data.get('bottlenecks', [])),
            'function_count': len(performance_data.get('function_performance', {})),
            'timestamp': time.time()
        }
    
    def _update_statistical_analyzer(self, metrics: Dict[str, Any]):
        """Update statistical analyzer with new metrics"""
        for metric_name, value in metrics.items():
            if isinstance(value, (int, float)):
                self.statistical_analyzer.add_metric(metric_name, value)
    
    async def _perform_statistical_analysis(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Perform comprehensive statistical analysis"""
        analysis_results = {}
        
        for metric_name in ['cpu_avg', 'memory_avg', 'active_threads', 'bottleneck_count']:
            if metric_name in metrics:
                # Anomaly detection
                anomalies = self.statistical_analyzer.detect_anomalies(metric_name)
                analysis_results[f'{metric_name}_anomalies'] = anomalies
                
                # Trend detection
                trends = self.statistical_analyzer.detect_trends(metric_name)
                analysis_results[f'{metric_name}_trend'] = trends
                
                # Periodicity detection
                periodicity = self.statistical_analyzer.detect_periodicity(metric_name)
                if periodicity:
                    analysis_results[f'{metric_name}_periodicity'] = periodicity
        
        # Additional derived metrics
        analysis_results.update({
            'cpu_max': max(100, metrics.get('cpu_avg', 0) * 1.2),  # Estimated max
            'cpu_variance': abs(metrics.get('cpu_avg', 0) - 50) * 2,  # Simplified variance
            'memory_trend': analysis_results.get('memory_avg_trend', {}),
            'io_wait': metrics.get('cpu_avg', 0) * 0.3,  # Estimated I/O wait
            'disk_busy': metrics.get('cpu_avg', 0) * 0.8,  # Estimated disk usage
            'blocked_threads': max(0, metrics.get('active_threads', 0) - 10),
            'progress_rate': max(0, 1.0 - metrics.get('bottleneck_count', 0) / 10),
            'error_rate': metrics.get('bottleneck_count', 0) / 100,
            'affected_services': [f'service_{i}' for i in range(min(metrics.get('bottleneck_count', 0), 5))]
        })
        
        return analysis_results
    
    async def _predict_performance(self, metrics: Dict[str, Any]) -> Dict[str, float]:
        """Predict future performance based on current metrics and trends"""
        predictions = {}
        
        # Simple prediction based on trends
        for metric_name in ['cpu_avg', 'memory_avg']:
            trend_key = f'{metric_name}_trend'
            if trend_key in metrics:
                trend = metrics[trend_key]
                current_value = metrics.get(metric_name, 0)
                
                if trend.get('direction') == 'increasing':
                    # Predict 10% increase over next 5 minutes
                    predictions[f'{metric_name}_5min'] = current_value * (1 + trend.get('strength', 0) * 0.1)
                elif trend.get('direction') == 'decreasing':
                    # Predict decrease
                    predictions[f'{metric_name}_5min'] = current_value * (1 - trend.get('strength', 0) * 0.1)
                else:
                    # Stable
                    predictions[f'{metric_name}_5min'] = current_value
        
        return predictions
    
    def _calculate_confidence_score(self, statistical_results: Dict[str, Any], 
                                  patterns: List[BottleneckSignature], 
                                  bottleneck_count: int) -> float:
        """Calculate confidence score for the analysis"""
        confidence_factors = []
        
        # Data quality factor
        data_points = len(self.statistical_analyzer.metrics_history.get('cpu_avg', []))
        data_quality = min(data_points / 50, 1.0)  # Full confidence with 50+ data points
        confidence_factors.append(data_quality)
        
        # Pattern recognition factor
        pattern_confidence = statistics.mean([0.8] * len(patterns)) if patterns else 0.3
        confidence_factors.append(pattern_confidence)
        
        # Statistical significance factor
        significant_trends = sum(1 for key, value in statistical_results.items() 
                               if 'trend' in key and isinstance(value, dict) and 
                               value.get('confidence', 0) > 0.7)
        trend_confidence = min(significant_trends / 3, 1.0)
        confidence_factors.append(trend_confidence)
        
        # Bottleneck detection factor
        bottleneck_confidence = min(bottleneck_count / 5, 1.0) if bottleneck_count > 0 else 0.5
        confidence_factors.append(bottleneck_confidence)
        
        return statistics.mean(confidence_factors) if confidence_factors else 0.5
    
    def get_analysis_summary(self) -> Dict[str, Any]:
        """Get summary of recent analyses"""
        if not self.analysis_history:
            return {'status': 'no_analyses_available'}
        
        recent_analyses = list(self.analysis_history)[-10:]  # Last 10 analyses
        
        return {
            'total_analyses': len(self.analysis_history),
            'recent_analyses_count': len(recent_analyses),
            'avg_confidence': statistics.mean([a.confidence_score for a in recent_analyses]),
            'pattern_frequency': Counter([p.pattern.value for a in recent_analyses for p in a.patterns_detected]),
            'resolution_actions_suggested': sum(len(a.resolution_actions) for a in recent_analyses),
            'latest_analysis': asdict(recent_analyses[-1]) if recent_analyses else None
        }
    
    async def execute_resolution_action(self, action_id: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute a resolution action"""
        # Find the action
        action = None
        for analysis in reversed(self.analysis_history):
            for res_action in analysis.resolution_actions:
                if res_action.id == action_id:
                    action = res_action
                    break
            if action:
                break
        
        if not action:
            return {'status': 'error', 'message': 'Action not found'}
        
        if action.strategy == ResolutionStrategy.MANUAL:
            return {'status': 'manual_intervention_required', 'description': action.description}
        
        try:
            # Use provided parameters or action defaults
            exec_params = parameters if parameters else action.parameters
            
            # Execute the action
            result = await action.implementation(exec_params)
            
            # Track effectiveness
            self.resolution_engine.applied_actions.append({
                'action_id': action_id,
                'timestamp': time.time(),
                'parameters': exec_params,
                'result': result
            })
            
            return {'status': 'success', 'action_result': result}
            
        except Exception as e:
            logger.error(f"Error executing resolution action {action_id}: {e}")
            return {'status': 'error', 'message': str(e)}


# Global analyzer instance
_global_analyzer: Optional[BottleneckAnalyzer] = None


def get_analyzer() -> BottleneckAnalyzer:
    """Get global bottleneck analyzer instance"""
    global _global_analyzer
    if _global_analyzer is None:
        _global_analyzer = BottleneckAnalyzer()
    return _global_analyzer