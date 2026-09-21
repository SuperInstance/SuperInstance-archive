"""
Performance Prediction and Testing System
Comprehensive testing and validation of configuration performance predictions
"""

import asyncio
import time
import json
import logging
import statistics
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict
import numpy as np
from concurrent.futures import ThreadPoolExecutor
import psutil

from api.models import (
    HardwareProfile, AdaptiveConfiguration, BenchmarkResult, 
    PerformancePrediction, BenchmarkType, BenchmarkRequest
)
from hardware.benchmarks import BenchmarkEngine
from config.builder import SmartConfigurationBuilder

@dataclass
class PerformanceTest:
    """Individual performance test definition"""
    test_id: str
    test_name: str
    test_type: str  # 'synthetic', 'real_world', 'stress'
    configuration: AdaptiveConfiguration
    hardware_profile: HardwareProfile
    expected_metrics: Dict[str, float]
    test_parameters: Dict[str, Any]
    timeout_seconds: int = 300

@dataclass
class TestResult:
    """Result of a performance test"""
    test_id: str
    start_time: datetime
    end_time: datetime
    success: bool
    actual_metrics: Dict[str, float]
    predicted_metrics: Dict[str, float]
    prediction_accuracy: Dict[str, float]
    performance_issues: List[str]
    resource_usage: Dict[str, float]
    error_messages: List[str]

@dataclass
class TestSuite:
    """Collection of related performance tests"""
    suite_id: str
    suite_name: str
    description: str
    tests: List[PerformanceTest]
    validation_criteria: Dict[str, Any]
    created_at: datetime

class RealWorldScenarioTester:
    """Tests configurations against real-world usage scenarios"""
    
    def __init__(self):
        self.scenarios = self._load_scenarios()
        self.baseline_metrics = {}
    
    async def test_web_browsing_scenario(self, 
                                       configuration: AdaptiveConfiguration,
                                       hardware_profile: HardwareProfile) -> TestResult:
        """Test web browsing performance scenario"""
        
        test_start = datetime.now()
        success = True
        actual_metrics = {}
        issues = []
        resource_usage = {}
        
        try:
            # Simulate web browsing workload
            tasks = []
            for i in range(configuration.max_concurrent_tasks):
                tasks.append(self._simulate_web_tab(i, configuration))
            
            start_time = time.time()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()
            
            # Collect results
            total_load_time = end_time - start_time
            tab_load_times = [r for r in results if isinstance(r, float)]
            
            actual_metrics = {
                'total_load_time': total_load_time,
                'average_tab_load_time': statistics.mean(tab_load_times) if tab_load_times else 0,
                'tabs_loaded_successfully': len(tab_load_times),
                'responsiveness_score': self._calculate_responsiveness_score(tab_load_times),
                'memory_efficiency': self._calculate_memory_efficiency(configuration)
            }
            
            # Check for issues
            if total_load_time > 30:  # 30 seconds timeout
                issues.append('slow_loading')
            
            if len(tab_load_times) < configuration.max_concurrent_tasks * 0.8:
                issues.append('task_failures')
            
            # Collect resource usage
            resource_usage = {
                'cpu_percent': psutil.cpu_percent(),
                'memory_percent': psutil.virtual_memory().percent,
                'memory_used_mb': psutil.virtual_memory().used / (1024*1024)
            }
            
        except Exception as e:
            success = False
            issues.append(f'test_exception: {str(e)}')
        
        return TestResult(
            test_id='web_browsing',
            start_time=test_start,
            end_time=datetime.now(),
            success=success,
            actual_metrics=actual_metrics,
            predicted_metrics={},  # Would be filled by caller
            prediction_accuracy={},  # Would be calculated by caller
            performance_issues=issues,
            resource_usage=resource_usage,
            error_messages=[]
        )
    
    async def test_video_streaming_scenario(self,
                                          configuration: AdaptiveConfiguration,
                                          hardware_profile: HardwareProfile) -> TestResult:
        """Test video streaming performance scenario"""
        
        test_start = datetime.now()
        success = True
        actual_metrics = {}
        issues = []
        resource_usage = {}
        
        try:
            # Simulate video streaming workload
            stream_quality = self._determine_stream_quality(hardware_profile)
            buffer_size = configuration.cache_size_mb
            
            # Simulate streaming performance
            start_time = time.time()
            
            # Simulate network buffering and decoding
            for i in range(10):  # 10 second test
                await asyncio.sleep(0.1)
                
                # Simulate CPU-intensive video decoding
                if hardware_profile.gpu and configuration.ml_acceleration:
                    decode_time = 0.02  # GPU acceleration
                else:
                    decode_time = 0.05  # CPU only
                
                await asyncio.sleep(decode_time)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # Calculate metrics
            frame_rate = 30 * (10 / total_time) if total_time > 0 else 0
            buffer_health = min(100, buffer_size / 10)  # 10MB per second ideal
            
            actual_metrics = {
                'average_frame_rate': frame_rate,
                'buffer_health_percent': buffer_health,
                'stream_quality': stream_quality,
                'total_test_duration': total_time,
                'dropped_frames': max(0, 300 - frame_rate * 10)  # Expected 300 frames in 10s
            }
            
            # Check for issues
            if frame_rate < 25:
                issues.append('low_frame_rate')
            
            if buffer_health < 50:
                issues.append('insufficient_buffering')
            
            # Resource usage
            resource_usage = {
                'cpu_percent': psutil.cpu_percent(),
                'memory_percent': psutil.virtual_memory().percent,
                'gpu_utilization': 50 if hardware_profile.gpu else 0  # Estimated
            }
            
        except Exception as e:
            success = False
            issues.append(f'streaming_exception: {str(e)}')
        
        return TestResult(
            test_id='video_streaming',
            start_time=test_start,
            end_time=datetime.now(),
            success=success,
            actual_metrics=actual_metrics,
            predicted_metrics={},
            prediction_accuracy={},
            performance_issues=issues,
            resource_usage=resource_usage,
            error_messages=[]
        )
    
    async def test_gaming_scenario(self,
                                 configuration: AdaptiveConfiguration,
                                 hardware_profile: HardwareProfile) -> TestResult:
        """Test gaming performance scenario"""
        
        test_start = datetime.now()
        success = True
        actual_metrics = {}
        issues = []
        resource_usage = {}
        
        try:
            # Simulate gaming workload
            if not hardware_profile.gpu:
                issues.append('no_gpu_for_gaming')
                success = False
            
            # Simulate game rendering
            start_time = time.time()
            frame_times = []
            
            for frame in range(300):  # 10 seconds at 30 FPS
                frame_start = time.time()
                
                # Simulate rendering workload
                if hardware_profile.gpu:
                    render_time = 0.016  # 16ms for 60 FPS
                else:
                    render_time = 0.033  # 33ms for 30 FPS
                
                # Add CPU processing
                cpu_time = 0.005 if hardware_profile.cpu.cores >= 4 else 0.010
                
                await asyncio.sleep(render_time + cpu_time)
                
                frame_end = time.time()
                frame_times.append((frame_end - frame_start) * 1000)  # Convert to ms
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # Calculate gaming metrics
            average_fps = 300 / total_time if total_time > 0 else 0
            frame_time_avg = statistics.mean(frame_times)
            frame_time_99th = np.percentile(frame_times, 99)
            
            actual_metrics = {
                'average_fps': average_fps,
                'frame_time_ms_avg': frame_time_avg,
                'frame_time_ms_99th': frame_time_99th,
                'frame_consistency': 100 - (statistics.stdev(frame_times) / frame_time_avg * 100),
                'total_test_duration': total_time
            }
            
            # Performance analysis
            if average_fps < 30:
                issues.append('low_fps')
            
            if frame_time_99th > 50:  # 50ms = very stuttery
                issues.append('frame_drops')
            
            resource_usage = {
                'cpu_percent': 80 if hardware_profile.cpu.cores >= 4 else 95,
                'gpu_percent': 85 if hardware_profile.gpu else 0,
                'memory_percent': 70
            }
            
        except Exception as e:
            success = False
            issues.append(f'gaming_exception: {str(e)}')
        
        return TestResult(
            test_id='gaming',
            start_time=test_start,
            end_time=datetime.now(),
            success=success,
            actual_metrics=actual_metrics,
            predicted_metrics={},
            prediction_accuracy={},
            performance_issues=issues,
            resource_usage=resource_usage,
            error_messages=[]
        )
    
    async def _simulate_web_tab(self, tab_id: int, configuration: AdaptiveConfiguration) -> float:
        """Simulate loading a web tab"""
        
        start_time = time.time()
        
        # Simulate network request
        await asyncio.sleep(np.random.uniform(0.1, 0.5))
        
        # Simulate HTML parsing and rendering
        parsing_time = 0.1 if configuration.processing_threads > 2 else 0.2
        await asyncio.sleep(parsing_time)
        
        # Simulate JavaScript execution
        js_time = 0.05 if configuration.ml_acceleration else 0.1
        await asyncio.sleep(js_time)
        
        end_time = time.time()
        return end_time - start_time
    
    def _determine_stream_quality(self, hardware_profile: HardwareProfile) -> str:
        """Determine appropriate streaming quality"""
        
        if hardware_profile.system_tier == 'high_end':
            return '4K'
        elif hardware_profile.system_tier == 'standard':
            return '1080p'
        else:
            return '720p'
    
    def _calculate_responsiveness_score(self, load_times: List[float]) -> float:
        """Calculate responsiveness score from load times"""
        
        if not load_times:
            return 0
        
        avg_time = statistics.mean(load_times)
        
        # Score based on average load time
        if avg_time < 1.0:
            return 100
        elif avg_time < 2.0:
            return 80
        elif avg_time < 5.0:
            return 60
        else:
            return 40
    
    def _calculate_memory_efficiency(self, configuration: AdaptiveConfiguration) -> float:
        """Calculate memory efficiency score"""
        
        current_memory = psutil.virtual_memory().percent
        allocated_percent = (configuration.memory_allocation_mb / 1024) / psutil.virtual_memory().total * 100
        
        efficiency = 100 - abs(current_memory - allocated_percent)
        return max(0, min(100, efficiency))
    
    def _load_scenarios(self) -> Dict[str, Dict[str, Any]]:
        """Load test scenario definitions"""
        
        return {
            'web_browsing': {
                'name': 'Web Browsing',
                'description': 'Multiple tab browsing with mixed content',
                'expected_duration': 30,
                'success_criteria': {
                    'min_responsiveness_score': 60,
                    'max_average_load_time': 3.0,
                    'min_success_rate': 0.8
                }
            },
            'video_streaming': {
                'name': 'Video Streaming',
                'description': 'HD video streaming with buffering',
                'expected_duration': 60,
                'success_criteria': {
                    'min_frame_rate': 25,
                    'min_buffer_health': 40,
                    'max_dropped_frames': 30
                }
            },
            'gaming': {
                'name': 'Gaming Performance',
                'description': '3D gaming simulation',
                'expected_duration': 30,
                'success_criteria': {
                    'min_fps': 30,
                    'max_frame_time_99th': 40,
                    'min_consistency': 80
                }
            }
        }

class PredictionAccuracyValidator:
    """Validates the accuracy of performance predictions"""
    
    def __init__(self):
        self.validation_history = []
        self.accuracy_thresholds = {
            'excellent': 0.95,
            'good': 0.85,
            'acceptable': 0.70,
            'poor': 0.50
        }
    
    def validate_prediction(self, 
                          prediction: PerformancePrediction,
                          actual_result: TestResult) -> Dict[str, Any]:
        """Validate prediction accuracy against actual results"""
        
        validation = {
            'overall_accuracy': 0.0,
            'metric_accuracies': {},
            'accuracy_rating': 'poor',
            'significant_deviations': [],
            'confidence_analysis': {}
        }
        
        # Compare each predicted metric with actual
        total_accuracy = 0.0
        metric_count = 0
        
        for metric_name, predicted_value in prediction.predicted_metrics.items():
            if metric_name in actual_result.actual_metrics:
                actual_value = actual_result.actual_metrics[metric_name]
                
                # Calculate accuracy (avoid division by zero)
                if actual_value != 0:
                    accuracy = 1 - abs(predicted_value - actual_value) / abs(actual_value)
                else:
                    accuracy = 1 if predicted_value == 0 else 0
                
                accuracy = max(0, accuracy)  # Clamp to non-negative
                
                validation['metric_accuracies'][metric_name] = accuracy
                total_accuracy += accuracy
                metric_count += 1
                
                # Check for significant deviations
                deviation_threshold = 0.3  # 30% deviation
                if accuracy < (1 - deviation_threshold):
                    validation['significant_deviations'].append({
                        'metric': metric_name,
                        'predicted': predicted_value,
                        'actual': actual_value,
                        'deviation_percent': (1 - accuracy) * 100
                    })
        
        # Calculate overall accuracy
        if metric_count > 0:
            validation['overall_accuracy'] = total_accuracy / metric_count
        
        # Determine accuracy rating
        accuracy = validation['overall_accuracy']
        if accuracy >= self.accuracy_thresholds['excellent']:
            validation['accuracy_rating'] = 'excellent'
        elif accuracy >= self.accuracy_thresholds['good']:
            validation['accuracy_rating'] = 'good'
        elif accuracy >= self.accuracy_thresholds['acceptable']:
            validation['accuracy_rating'] = 'acceptable'
        else:
            validation['accuracy_rating'] = 'poor'
        
        # Analyze confidence intervals
        validation['confidence_analysis'] = self._analyze_confidence_intervals(
            prediction, actual_result
        )
        
        # Store validation history
        self.validation_history.append({
            'timestamp': datetime.now(),
            'prediction': prediction,
            'actual': actual_result,
            'validation': validation
        })
        
        return validation
    
    def get_prediction_accuracy_trends(self, 
                                     time_window_hours: int = 168) -> Dict[str, Any]:
        """Analyze prediction accuracy trends over time"""
        
        cutoff_time = datetime.now() - timedelta(hours=time_window_hours)
        recent_validations = [
            v for v in self.validation_history 
            if v['timestamp'] > cutoff_time
        ]
        
        if not recent_validations:
            return {}
        
        # Calculate trends
        accuracies = [v['validation']['overall_accuracy'] for v in recent_validations]
        
        trends = {
            'total_predictions': len(recent_validations),
            'average_accuracy': statistics.mean(accuracies),
            'accuracy_std': statistics.stdev(accuracies) if len(accuracies) > 1 else 0,
            'accuracy_trend': self._calculate_trend(accuracies),
            'accuracy_distribution': self._calculate_accuracy_distribution(recent_validations),
            'common_prediction_errors': self._identify_common_errors(recent_validations),
            'improvement_recommendations': self._generate_improvement_recommendations(recent_validations)
        }
        
        return trends
    
    def _analyze_confidence_intervals(self, 
                                    prediction: PerformancePrediction,
                                    actual_result: TestResult) -> Dict[str, Any]:
        """Analyze how well confidence intervals predicted actual results"""
        
        analysis = {
            'intervals_available': bool(prediction.confidence_intervals),
            'actual_within_intervals': {},
            'interval_accuracy': 0.0
        }
        
        if not prediction.confidence_intervals:
            return analysis
        
        within_count = 0
        total_count = 0
        
        for metric_name, interval in prediction.confidence_intervals.items():
            if metric_name in actual_result.actual_metrics:
                actual_value = actual_result.actual_metrics[metric_name]
                lower, upper = interval
                
                within_interval = lower <= actual_value <= upper
                analysis['actual_within_intervals'][metric_name] = within_interval
                
                if within_interval:
                    within_count += 1
                total_count += 1
        
        if total_count > 0:
            analysis['interval_accuracy'] = within_count / total_count
        
        return analysis
    
    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend direction for values"""
        
        if len(values) < 3:
            return 'insufficient_data'
        
        # Simple linear regression
        x = list(range(len(values)))
        slope = np.polyfit(x, values, 1)[0]
        
        if slope > 0.01:
            return 'improving'
        elif slope < -0.01:
            return 'declining'
        else:
            return 'stable'
    
    def _calculate_accuracy_distribution(self, validations: List[Dict]) -> Dict[str, int]:
        """Calculate distribution of accuracy ratings"""
        
        distribution = defaultdict(int)
        for v in validations:
            rating = v['validation']['accuracy_rating']
            distribution[rating] += 1
        
        return dict(distribution)
    
    def _identify_common_errors(self, validations: List[Dict]) -> List[Dict[str, Any]]:
        """Identify common prediction errors"""
        
        error_patterns = defaultdict(int)
        metric_errors = defaultdict(list)
        
        for v in validations:
            for deviation in v['validation']['significant_deviations']:
                metric = deviation['metric']
                error_patterns[metric] += 1
                metric_errors[metric].append(deviation['deviation_percent'])
        
        common_errors = []
        for metric, count in error_patterns.items():
            if count >= len(validations) * 0.2:  # 20% occurrence threshold
                avg_deviation = statistics.mean(metric_errors[metric])
                common_errors.append({
                    'metric': metric,
                    'occurrence_rate': count / len(validations),
                    'average_deviation_percent': avg_deviation,
                    'error_type': 'systematic_over_estimation' if avg_deviation > 0 else 'systematic_under_estimation'
                })
        
        return sorted(common_errors, key=lambda x: x['occurrence_rate'], reverse=True)
    
    def _generate_improvement_recommendations(self, validations: List[Dict]) -> List[str]:
        """Generate recommendations for improving predictions"""
        
        recommendations = []
        
        # Analyze overall accuracy
        accuracies = [v['validation']['overall_accuracy'] for v in validations]
        avg_accuracy = statistics.mean(accuracies)
        
        if avg_accuracy < 0.7:
            recommendations.append("Consider retraining ML models with more recent data")
        
        if len(accuracies) > 1 and statistics.stdev(accuracies) > 0.2:
            recommendations.append("High prediction variance detected - improve model consistency")
        
        # Analyze confidence intervals
        interval_accuracies = [
            v['validation']['confidence_analysis'].get('interval_accuracy', 0)
            for v in validations
            if v['validation']['confidence_analysis'].get('intervals_available', False)
        ]
        
        if interval_accuracies and statistics.mean(interval_accuracies) < 0.8:
            recommendations.append("Calibrate confidence intervals - too many actuals outside predicted ranges")
        
        # Analyze common errors
        common_errors = self._identify_common_errors(validations)
        for error in common_errors[:3]:  # Top 3 common errors
            recommendations.append(f"Address systematic prediction bias in {error['metric']} metric")
        
        return recommendations

class PerformanceTester:
    """Main performance testing and validation system"""
    
    def __init__(self):
        self.benchmark_engine = BenchmarkEngine()
        self.scenario_tester = RealWorldScenarioTester()
        self.accuracy_validator = PredictionAccuracyValidator()
        self.config_builder = SmartConfigurationBuilder()
        self.test_suites = {}
        
    async def run_comprehensive_test(self, 
                                   hardware_profile: HardwareProfile,
                                   configuration: AdaptiveConfiguration,
                                   test_scope: str = 'standard') -> Dict[str, Any]:
        """Run comprehensive performance testing"""
        
        test_results = {
            'test_id': f"comprehensive_{int(time.time())}",
            'start_time': datetime.now(),
            'hardware_profile': hardware_profile.profile_id,
            'configuration': configuration.config_id,
            'test_scope': test_scope,
            'synthetic_benchmarks': {},
            'real_world_scenarios': {},
            'prediction_validation': {},
            'overall_assessment': {},
            'recommendations': []
        }
        
        try:
            # Run synthetic benchmarks
            if test_scope in ['standard', 'comprehensive']:
                test_results['synthetic_benchmarks'] = await self._run_synthetic_benchmarks(
                    hardware_profile, configuration
                )
            
            # Run real-world scenario tests
            if test_scope in ['standard', 'comprehensive']:
                test_results['real_world_scenarios'] = await self._run_real_world_scenarios(
                    hardware_profile, configuration
                )
            
            # Validate predictions if available
            if configuration.predicted_performance:
                test_results['prediction_validation'] = await self._validate_predictions(
                    configuration, test_results
                )
            
            # Generate overall assessment
            test_results['overall_assessment'] = self._generate_overall_assessment(test_results)
            
            # Generate recommendations
            test_results['recommendations'] = self._generate_test_recommendations(test_results)
            
        except Exception as e:
            test_results['error'] = str(e)
            test_results['success'] = False
        
        test_results['end_time'] = datetime.now()
        test_results['duration_seconds'] = (test_results['end_time'] - test_results['start_time']).total_seconds()
        
        return test_results
    
    async def _run_synthetic_benchmarks(self, 
                                      hardware_profile: HardwareProfile,
                                      configuration: AdaptiveConfiguration) -> Dict[str, BenchmarkResult]:
        """Run synthetic performance benchmarks"""
        
        benchmark_results = {}
        
        # CPU benchmark
        cpu_request = BenchmarkRequest(
            benchmark_type=BenchmarkType.CPU_COMPUTE,
            duration=30,
            intensity='medium'
        )
        benchmark_results['cpu_compute'] = await self.benchmark_engine.run_benchmark(cpu_request)
        
        # Memory benchmark
        memory_request = BenchmarkRequest(
            benchmark_type=BenchmarkType.MEMORY_BANDWIDTH,
            duration=30,
            intensity='medium'
        )
        benchmark_results['memory_bandwidth'] = await self.benchmark_engine.run_benchmark(memory_request)
        
        # Storage benchmark
        storage_request = BenchmarkRequest(
            benchmark_type=BenchmarkType.STORAGE_SPEED,
            duration=30,
            intensity='medium'
        )
        benchmark_results['storage_speed'] = await self.benchmark_engine.run_benchmark(storage_request)
        
        # GPU benchmark if available
        if hardware_profile.gpu:
            gpu_request = BenchmarkRequest(
                benchmark_type=BenchmarkType.GPU_COMPUTE,
                duration=30,
                intensity='medium'
            )
            benchmark_results['gpu_compute'] = await self.benchmark_engine.run_benchmark(gpu_request)
        
        return benchmark_results
    
    async def _run_real_world_scenarios(self, 
                                      hardware_profile: HardwareProfile,
                                      configuration: AdaptiveConfiguration) -> Dict[str, TestResult]:
        """Run real-world scenario tests"""
        
        scenario_results = {}
        
        # Web browsing scenario
        scenario_results['web_browsing'] = await self.scenario_tester.test_web_browsing_scenario(
            configuration, hardware_profile
        )
        
        # Video streaming scenario
        scenario_results['video_streaming'] = await self.scenario_tester.test_video_streaming_scenario(
            configuration, hardware_profile
        )
        
        # Gaming scenario (if GPU available)
        if hardware_profile.gpu:
            scenario_results['gaming'] = await self.scenario_tester.test_gaming_scenario(
                configuration, hardware_profile
            )
        
        return scenario_results
    
    async def _validate_predictions(self, 
                                  configuration: AdaptiveConfiguration,
                                  test_results: Dict[str, Any]) -> Dict[str, Any]:
        """Validate configuration predictions against test results"""
        
        # Create a mock PerformancePrediction from configuration
        prediction = PerformancePrediction(
            config_id=configuration.config_id,
            predicted_metrics=configuration.predicted_performance,
            confidence_intervals={},
            bottlenecks=[],
            recommendations=[]
        )
        
        # Aggregate actual metrics from test results
        actual_metrics = {}
        
        # From synthetic benchmarks
        if 'synthetic_benchmarks' in test_results:
            for benchmark_name, result in test_results['synthetic_benchmarks'].items():
                if isinstance(result, BenchmarkResult):
                    actual_metrics[f'{benchmark_name}_score'] = result.score
        
        # From real-world scenarios
        if 'real_world_scenarios' in test_results:
            for scenario_name, result in test_results['real_world_scenarios'].items():
                if isinstance(result, TestResult) and result.success:
                    for metric_name, value in result.actual_metrics.items():
                        actual_metrics[f'{scenario_name}_{metric_name}'] = value
        
        # Create aggregate test result
        aggregate_result = TestResult(
            test_id='aggregate',
            start_time=test_results['start_time'],
            end_time=datetime.now(),
            success=True,
            actual_metrics=actual_metrics,
            predicted_metrics=configuration.predicted_performance,
            prediction_accuracy={},
            performance_issues=[],
            resource_usage={},
            error_messages=[]
        )
        
        # Validate prediction
        validation = self.accuracy_validator.validate_prediction(prediction, aggregate_result)
        
        return validation
    
    def _generate_overall_assessment(self, test_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate overall performance assessment"""
        
        assessment = {
            'performance_score': 0.0,
            'reliability_score': 0.0,
            'efficiency_score': 0.0,
            'overall_grade': 'C',
            'strengths': [],
            'weaknesses': [],
            'critical_issues': []
        }
        
        scores = []
        
        # Analyze synthetic benchmark results
        if 'synthetic_benchmarks' in test_results:
            benchmark_scores = []
            for result in test_results['synthetic_benchmarks'].values():
                if isinstance(result, BenchmarkResult):
                    # Normalize score to 0-1 range
                    normalized_score = min(1.0, result.score / 100.0)
                    benchmark_scores.append(normalized_score)
            
            if benchmark_scores:
                assessment['performance_score'] = statistics.mean(benchmark_scores) * 100
                scores.append(assessment['performance_score'])
        
        # Analyze real-world scenario results
        if 'real_world_scenarios' in test_results:
            scenario_scores = []
            success_count = 0
            total_count = 0
            
            for scenario_name, result in test_results['real_world_scenarios'].items():
                if isinstance(result, TestResult):
                    total_count += 1
                    if result.success:
                        success_count += 1
                        # Calculate scenario score based on key metrics
                        scenario_score = self._calculate_scenario_score(scenario_name, result)
                        scenario_scores.append(scenario_score)
                    
                    # Check for critical issues
                    if result.performance_issues:
                        assessment['critical_issues'].extend(result.performance_issues)
            
            if scenario_scores:
                assessment['efficiency_score'] = statistics.mean(scenario_scores)
                scores.append(assessment['efficiency_score'])
            
            if total_count > 0:
                assessment['reliability_score'] = (success_count / total_count) * 100
                scores.append(assessment['reliability_score'])
        
        # Calculate overall grade
        if scores:
            overall_score = statistics.mean(scores)
            if overall_score >= 90:
                assessment['overall_grade'] = 'A'
            elif overall_score >= 80:
                assessment['overall_grade'] = 'B'
            elif overall_score >= 70:
                assessment['overall_grade'] = 'C'
            elif overall_score >= 60:
                assessment['overall_grade'] = 'D'
            else:
                assessment['overall_grade'] = 'F'
        
        # Identify strengths and weaknesses
        assessment['strengths'], assessment['weaknesses'] = self._identify_strengths_weaknesses(test_results)
        
        return assessment
    
    def _calculate_scenario_score(self, scenario_name: str, result: TestResult) -> float:
        """Calculate performance score for a scenario"""
        
        if scenario_name == 'web_browsing':
            responsiveness = result.actual_metrics.get('responsiveness_score', 50)
            return min(100, responsiveness)
        
        elif scenario_name == 'video_streaming':
            frame_rate = result.actual_metrics.get('average_frame_rate', 15)
            buffer_health = result.actual_metrics.get('buffer_health_percent', 50)
            return (min(100, frame_rate * 2) + buffer_health) / 2
        
        elif scenario_name == 'gaming':
            fps = result.actual_metrics.get('average_fps', 15)
            consistency = result.actual_metrics.get('frame_consistency', 50)
            return (min(100, fps * 2) + consistency) / 2
        
        return 50  # Default score
    
    def _identify_strengths_weaknesses(self, test_results: Dict[str, Any]) -> Tuple[List[str], List[str]]:
        """Identify performance strengths and weaknesses"""
        
        strengths = []
        weaknesses = []
        
        # Analyze benchmark results
        if 'synthetic_benchmarks' in test_results:
            for benchmark_name, result in test_results['synthetic_benchmarks'].items():
                if isinstance(result, BenchmarkResult):
                    if result.score > 80:
                        strengths.append(f"Excellent {benchmark_name} performance")
                    elif result.score < 40:
                        weaknesses.append(f"Poor {benchmark_name} performance")
        
        # Analyze scenario results
        if 'real_world_scenarios' in test_results:
            for scenario_name, result in test_results['real_world_scenarios'].items():
                if isinstance(result, TestResult):
                    if result.success and not result.performance_issues:
                        strengths.append(f"Good {scenario_name} performance")
                    elif result.performance_issues:
                        for issue in result.performance_issues:
                            weaknesses.append(f"{scenario_name}: {issue}")
        
        # Analyze prediction accuracy if available
        if 'prediction_validation' in test_results:
            accuracy = test_results['prediction_validation'].get('overall_accuracy', 0)
            if accuracy > 0.85:
                strengths.append("Accurate performance predictions")
            elif accuracy < 0.60:
                weaknesses.append("Inaccurate performance predictions")
        
        return strengths, weaknesses
    
    def _generate_test_recommendations(self, test_results: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on test results"""
        
        recommendations = []
        
        # Overall assessment recommendations
        assessment = test_results.get('overall_assessment', {})
        overall_grade = assessment.get('overall_grade', 'C')
        
        if overall_grade in ['D', 'F']:
            recommendations.append("Consider hardware upgrades or configuration optimization")
        
        # Critical issues recommendations
        critical_issues = assessment.get('critical_issues', [])
        if 'low_fps' in critical_issues:
            recommendations.append("Enable GPU acceleration or reduce graphics quality")
        
        if 'insufficient_memory' in critical_issues:
            recommendations.append("Reduce memory allocation or add more RAM")
        
        if 'slow_loading' in critical_issues:
            recommendations.append("Optimize for faster loading times or upgrade storage")
        
        # Prediction accuracy recommendations
        if 'prediction_validation' in test_results:
            validation = test_results['prediction_validation']
            if validation.get('accuracy_rating') == 'poor':
                recommendations.append("Retrain performance prediction models with current hardware data")
        
        return recommendations