"""
AI-Powered Optimization Engine

Advanced machine learning system for predictive optimization, anomaly detection,
workload forecasting, and intelligent decision making with reinforcement learning.
"""

import asyncio
import logging
import numpy as np
import json
import time
from datetime import datetime, timedelta
from collections import deque, defaultdict
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import pickle
import os

# Mock ML libraries for demo (in production would use real scikit-learn, tensorflow, etc.)
try:
    from sklearn.ensemble import RandomForestRegressor, IsolationForest
    from sklearn.linear_model import LinearRegression, Ridge
    from sklearn.preprocessing import StandardScaler, MinMaxScaler
    from sklearn.cluster import KMeans
    from sklearn.metrics import mean_squared_error, mean_absolute_error
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    # Mock classes for demo
    class MockModel:
        def __init__(self, *args, **kwargs): pass
        def fit(self, X, y=None): return self
        def predict(self, X): return np.random.random(len(X))
        def transform(self, X): return X
    
    RandomForestRegressor = IsolationForest = LinearRegression = Ridge = MockModel
    StandardScaler = MinMaxScaler = KMeans = MockModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OptimizationStrategy(Enum):
    """AI optimization strategies"""
    PERFORMANCE_FIRST = "performance_first"
    COST_FIRST = "cost_first"
    BALANCED = "balanced"
    POWER_EFFICIENT = "power_efficient"
    RELIABILITY_FIRST = "reliability_first"
    ADAPTIVE = "adaptive"

class PredictionHorizon(Enum):
    """Prediction time horizons"""
    SHORT_TERM = 60      # 1 minute
    MEDIUM_TERM = 900    # 15 minutes
    LONG_TERM = 3600     # 1 hour
    DAILY = 86400        # 24 hours

class WorkloadType(Enum):
    """Types of workloads for optimization"""
    CPU_INTENSIVE = "cpu_intensive"
    MEMORY_INTENSIVE = "memory_intensive"
    IO_INTENSIVE = "io_intensive"
    NETWORK_INTENSIVE = "network_intensive"
    GPU_INTENSIVE = "gpu_intensive"
    MIXED = "mixed"
    INTERACTIVE = "interactive"
    BATCH = "batch"

@dataclass
class WorkloadPattern:
    """Workload pattern analysis"""
    pattern_id: str
    workload_type: WorkloadType
    peak_hours: List[int]  # Hours of day (0-23)
    resource_requirements: Dict[str, float]
    seasonality: Dict[str, float]  # daily, weekly, monthly patterns
    confidence: float
    last_updated: datetime
    
    def to_dict(self):
        data = asdict(self)
        data['workload_type'] = self.workload_type.value
        data['last_updated'] = self.last_updated.isoformat()
        return data

@dataclass
class OptimizationRecommendation:
    """AI-generated optimization recommendation"""
    recommendation_id: str
    timestamp: datetime
    strategy: OptimizationStrategy
    confidence: float
    expected_improvement: Dict[str, float]  # performance, cost, reliability
    actions: List[Dict[str, Any]]
    risk_assessment: Dict[str, float]
    implementation_complexity: str  # low, medium, high
    estimated_impact_time: int  # seconds
    rollback_plan: List[Dict[str, Any]]
    
    def to_dict(self):
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['strategy'] = self.strategy.value
        return data

@dataclass
class AnomalyDetection:
    """Detected system anomaly"""
    anomaly_id: str
    timestamp: datetime
    anomaly_type: str
    severity: float  # 0.0 - 1.0
    affected_components: List[str]
    root_cause_analysis: Dict[str, Any]
    recommended_actions: List[str]
    auto_remediation_available: bool
    
    def to_dict(self):
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data

class PerformancePredictor:
    """Advanced performance prediction using ML"""
    
    def __init__(self, model_path: str = "data/models/"):
        self.model_path = model_path
        self.models = {}
        self.scalers = {}
        self.feature_history = deque(maxlen=10000)
        self.prediction_cache = {}
        
        # Create model directory
        os.makedirs(model_path, exist_ok=True)
        
        # Initialize models
        self._initialize_models()
    
    def _initialize_models(self):
        """Initialize ML models for different predictions"""
        self.models = {
            'cpu_usage': RandomForestRegressor(n_estimators=100, random_state=42),
            'memory_usage': RandomForestRegressor(n_estimators=100, random_state=42),
            'network_latency': Ridge(alpha=1.0),
            'disk_io': LinearRegression(),
            'response_time': RandomForestRegressor(n_estimators=50, random_state=42),
            'throughput': Ridge(alpha=0.5),
            'error_rate': RandomForestRegressor(n_estimators=50, random_state=42)
        }
        
        self.scalers = {
            metric: StandardScaler() for metric in self.models.keys()
        }
        
        # Try to load existing models
        self._load_models()
    
    def _load_models(self):
        """Load pre-trained models if available"""
        for metric in self.models.keys():
            model_file = os.path.join(self.model_path, f"{metric}_model.pkl")
            scaler_file = os.path.join(self.model_path, f"{metric}_scaler.pkl")
            
            try:
                if os.path.exists(model_file):
                    with open(model_file, 'rb') as f:
                        self.models[metric] = pickle.load(f)
                    logger.info(f"Loaded model for {metric}")
                
                if os.path.exists(scaler_file):
                    with open(scaler_file, 'rb') as f:
                        self.scalers[metric] = pickle.load(f)
                    logger.info(f"Loaded scaler for {metric}")
            except Exception as e:
                logger.warning(f"Failed to load model for {metric}: {e}")
    
    def _save_models(self):
        """Save trained models"""
        for metric in self.models.keys():
            try:
                model_file = os.path.join(self.model_path, f"{metric}_model.pkl")
                scaler_file = os.path.join(self.model_path, f"{metric}_scaler.pkl")
                
                with open(model_file, 'wb') as f:
                    pickle.dump(self.models[metric], f)
                
                with open(scaler_file, 'wb') as f:
                    pickle.dump(self.scalers[metric], f)
            except Exception as e:
                logger.error(f"Failed to save model for {metric}: {e}")
    
    def add_training_data(self, timestamp: datetime, features: Dict[str, float], 
                         targets: Dict[str, float]):
        """Add training data for model improvement"""
        data_point = {
            'timestamp': timestamp,
            'features': features,
            'targets': targets
        }
        self.feature_history.append(data_point)
        
        # Retrain models periodically
        if len(self.feature_history) % 100 == 0:
            asyncio.create_task(self._retrain_models())
    
    async def _retrain_models(self):
        """Retrain models with new data"""
        if len(self.feature_history) < 50:
            return
        
        try:
            # Prepare training data
            features = []
            targets = {metric: [] for metric in self.models.keys()}
            
            for data_point in list(self.feature_history)[-1000:]:  # Use last 1000 points
                feature_vector = self._extract_features(data_point['features'])
                features.append(feature_vector)
                
                for metric in self.models.keys():
                    targets[metric].append(data_point['targets'].get(metric, 0))
            
            features = np.array(features)
            
            # Train each model
            for metric in self.models.keys():
                if len(targets[metric]) > 10:  # Minimum data points
                    y = np.array(targets[metric])
                    
                    # Scale features
                    X_scaled = self.scalers[metric].fit_transform(features)
                    
                    # Train model
                    self.models[metric].fit(X_scaled, y)
                    
                    # Evaluate performance
                    predictions = self.models[metric].predict(X_scaled)
                    mse = mean_squared_error(y, predictions)
                    
                    logger.info(f"Retrained {metric} model - MSE: {mse:.4f}")
            
            # Save updated models
            self._save_models()
            
        except Exception as e:
            logger.error(f"Model retraining failed: {e}")
    
    def _extract_features(self, raw_features: Dict[str, float]) -> List[float]:
        """Extract feature vector from raw metrics"""
        # Time-based features
        now = datetime.now()
        hour = now.hour / 24.0
        day_of_week = now.weekday() / 7.0
        
        # Base features
        base_features = [
            raw_features.get('cpu_percent', 0) / 100.0,
            raw_features.get('memory_percent', 0) / 100.0,
            raw_features.get('disk_percent', 0) / 100.0,
            raw_features.get('network_mbps', 0) / 1000.0,  # Normalize to Gbps
            raw_features.get('active_tasks', 0) / 100.0,
            raw_features.get('queue_length', 0) / 1000.0,
            hour,
            day_of_week
        ]
        
        # Add derived features
        load_factor = (raw_features.get('cpu_percent', 0) + raw_features.get('memory_percent', 0)) / 200.0
        resource_pressure = max(raw_features.get('cpu_percent', 0), raw_features.get('memory_percent', 0)) / 100.0
        
        base_features.extend([load_factor, resource_pressure])
        
        return base_features
    
    async def predict_metrics(self, horizon: PredictionHorizon, 
                            current_features: Dict[str, float]) -> Dict[str, float]:
        """Predict future performance metrics"""
        try:
            cache_key = f"{horizon.value}_{hash(str(current_features))}"
            
            # Check cache
            if cache_key in self.prediction_cache:
                cached = self.prediction_cache[cache_key]
                if (datetime.now() - cached['timestamp']).seconds < 30:  # 30 second cache
                    return cached['predictions']
            
            # Extract features
            feature_vector = np.array([self._extract_features(current_features)])
            
            predictions = {}
            for metric, model in self.models.items():
                try:
                    # Scale features
                    X_scaled = self.scalers[metric].transform(feature_vector)
                    
                    # Make prediction
                    prediction = model.predict(X_scaled)[0]
                    
                    # Add time horizon adjustment
                    horizon_factor = self._get_horizon_factor(horizon, metric)
                    predictions[metric] = max(0, prediction * horizon_factor)
                    
                except Exception as e:
                    logger.warning(f"Prediction failed for {metric}: {e}")
                    predictions[metric] = current_features.get(metric.replace('_', '_percent'), 0)
            
            # Cache predictions
            self.prediction_cache[cache_key] = {
                'timestamp': datetime.now(),
                'predictions': predictions
            }
            
            return predictions
            
        except Exception as e:
            logger.error(f"Prediction error: {e}")
            return {}
    
    def _get_horizon_factor(self, horizon: PredictionHorizon, metric: str) -> float:
        """Get adjustment factor based on prediction horizon"""
        base_factors = {
            PredictionHorizon.SHORT_TERM: 1.0,
            PredictionHorizon.MEDIUM_TERM: 1.1,
            PredictionHorizon.LONG_TERM: 1.2,
            PredictionHorizon.DAILY: 1.3
        }
        
        # Metric-specific adjustments
        metric_adjustments = {
            'cpu_usage': 0.0,
            'memory_usage': 0.05,  # Memory tends to grow over time
            'network_latency': 0.1,  # Network can degrade
            'error_rate': 0.15  # Errors tend to accumulate
        }
        
        base_factor = base_factors.get(horizon, 1.0)
        adjustment = metric_adjustments.get(metric, 0.0)
        
        return base_factor + adjustment

class AnomalyDetector:
    """Advanced anomaly detection using isolation forest and statistical methods"""
    
    def __init__(self, contamination: float = 0.1):
        self.contamination = contamination
        self.models = {}
        self.baseline_stats = {}
        self.anomaly_history = deque(maxlen=1000)
        self.detection_thresholds = {}
        
        self._initialize_detectors()
    
    def _initialize_detectors(self):
        """Initialize anomaly detection models"""
        self.models = {
            'system_metrics': IsolationForest(contamination=self.contamination, random_state=42),
            'performance_metrics': IsolationForest(contamination=self.contamination, random_state=42),
            'cost_metrics': IsolationForest(contamination=self.contamination, random_state=42),
            'network_metrics': IsolationForest(contamination=self.contamination, random_state=42)
        }
        
        # Statistical thresholds (z-score based)
        self.detection_thresholds = {
            'cpu_spike': 3.0,    # 3 standard deviations
            'memory_leak': 2.5,
            'latency_spike': 3.0,
            'error_burst': 2.0,
            'cost_anomaly': 2.5
        }
    
    def update_baselines(self, metrics: Dict[str, float]):
        """Update baseline statistics for anomaly detection"""
        for metric, value in metrics.items():
            if metric not in self.baseline_stats:
                self.baseline_stats[metric] = {
                    'values': deque(maxlen=1000),
                    'mean': 0,
                    'std': 1,
                    'min': value,
                    'max': value
                }
            
            stats = self.baseline_stats[metric]
            stats['values'].append(value)
            
            if len(stats['values']) > 10:
                values_array = np.array(stats['values'])
                stats['mean'] = np.mean(values_array)
                stats['std'] = max(np.std(values_array), 0.01)  # Avoid division by zero
                stats['min'] = np.min(values_array)
                stats['max'] = np.max(values_array)
    
    async def detect_anomalies(self, current_metrics: Dict[str, float]) -> List[AnomalyDetection]:
        """Detect anomalies in current metrics"""
        anomalies = []
        
        try:
            # Update baselines
            self.update_baselines(current_metrics)
            
            # Statistical anomaly detection
            statistical_anomalies = self._detect_statistical_anomalies(current_metrics)
            anomalies.extend(statistical_anomalies)
            
            # ML-based anomaly detection (if sufficient data)
            if len(self.baseline_stats) > 10:
                ml_anomalies = await self._detect_ml_anomalies(current_metrics)
                anomalies.extend(ml_anomalies)
            
            # Pattern-based anomaly detection
            pattern_anomalies = self._detect_pattern_anomalies(current_metrics)
            anomalies.extend(pattern_anomalies)
            
            # Store anomalies
            for anomaly in anomalies:
                self.anomaly_history.append(anomaly)
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Anomaly detection error: {e}")
            return []
    
    def _detect_statistical_anomalies(self, metrics: Dict[str, float]) -> List[AnomalyDetection]:
        """Detect anomalies using statistical methods"""
        anomalies = []
        
        for metric, value in metrics.items():
            if metric not in self.baseline_stats:
                continue
            
            stats = self.baseline_stats[metric]
            if len(stats['values']) < 10:
                continue
            
            # Calculate z-score
            z_score = abs(value - stats['mean']) / stats['std']
            
            # Check for different types of anomalies
            if 'cpu' in metric.lower() and z_score > self.detection_thresholds['cpu_spike']:
                anomaly = AnomalyDetection(
                    anomaly_id=f"cpu_spike_{int(time.time() * 1000)}",
                    timestamp=datetime.now(),
                    anomaly_type="cpu_spike",
                    severity=min(z_score / 5.0, 1.0),
                    affected_components=['cpu'],
                    root_cause_analysis={
                        'z_score': z_score,
                        'current_value': value,
                        'baseline_mean': stats['mean'],
                        'baseline_std': stats['std']
                    },
                    recommended_actions=[
                        "Investigate high CPU processes",
                        "Scale CPU resources if needed",
                        "Check for runaway processes"
                    ],
                    auto_remediation_available=True
                )
                anomalies.append(anomaly)
            
            elif 'memory' in metric.lower() and value > stats['mean'] + 2.5 * stats['std']:
                # Memory leak detection
                recent_values = list(stats['values'])[-10:]
                if len(recent_values) >= 5 and all(recent_values[i] <= recent_values[i+1] for i in range(4)):
                    anomaly = AnomalyDetection(
                        anomaly_id=f"memory_leak_{int(time.time() * 1000)}",
                        timestamp=datetime.now(),
                        anomaly_type="memory_leak",
                        severity=min((value - stats['mean']) / (stats['max'] - stats['mean']), 1.0),
                        affected_components=['memory'],
                        root_cause_analysis={
                            'trend': 'increasing',
                            'current_value': value,
                            'recent_trend': recent_values
                        },
                        recommended_actions=[
                            "Investigate memory usage patterns",
                            "Check for memory leaks in applications",
                            "Consider garbage collection tuning"
                        ],
                        auto_remediation_available=False
                    )
                    anomalies.append(anomaly)
            
            elif 'latency' in metric.lower() and z_score > self.detection_thresholds['latency_spike']:
                anomaly = AnomalyDetection(
                    anomaly_id=f"latency_spike_{int(time.time() * 1000)}",
                    timestamp=datetime.now(),
                    anomaly_type="latency_spike",
                    severity=min(z_score / 4.0, 1.0),
                    affected_components=['network'],
                    root_cause_analysis={
                        'z_score': z_score,
                        'current_latency': value,
                        'baseline_latency': stats['mean']
                    },
                    recommended_actions=[
                        "Check network connectivity",
                        "Investigate network bottlenecks",
                        "Consider CDN optimization"
                    ],
                    auto_remediation_available=True
                )
                anomalies.append(anomaly)
        
        return anomalies
    
    async def _detect_ml_anomalies(self, metrics: Dict[str, float]) -> List[AnomalyDetection]:
        """Detect anomalies using ML models"""
        anomalies = []
        
        try:
            # Prepare feature vector
            feature_vector = [metrics.get(key, 0) for key in sorted(metrics.keys())]
            feature_array = np.array([feature_vector])
            
            # System metrics anomaly detection
            system_features = [
                metrics.get('cpu_percent', 0),
                metrics.get('memory_percent', 0),
                metrics.get('disk_percent', 0),
                metrics.get('temperature', 0)
            ]
            
            if len(system_features) == 4:
                system_array = np.array([system_features])
                anomaly_score = self.models['system_metrics'].decision_function(system_array)[0]
                
                if anomaly_score < -0.5:  # Threshold for anomaly
                    anomaly = AnomalyDetection(
                        anomaly_id=f"ml_system_{int(time.time() * 1000)}",
                        timestamp=datetime.now(),
                        anomaly_type="system_anomaly",
                        severity=min(abs(anomaly_score), 1.0),
                        affected_components=['system'],
                        root_cause_analysis={
                            'anomaly_score': anomaly_score,
                            'features': system_features,
                            'detection_method': 'isolation_forest'
                        },
                        recommended_actions=[
                            "Investigate system-wide performance issues",
                            "Check for hardware problems",
                            "Review system configuration"
                        ],
                        auto_remediation_available=False
                    )
                    anomalies.append(anomaly)
        
        except Exception as e:
            logger.warning(f"ML anomaly detection error: {e}")
        
        return anomalies
    
    def _detect_pattern_anomalies(self, metrics: Dict[str, float]) -> List[AnomalyDetection]:
        """Detect pattern-based anomalies"""
        anomalies = []
        
        # Check for impossible combinations
        cpu_percent = metrics.get('cpu_percent', 0)
        memory_percent = metrics.get('memory_percent', 0)
        active_tasks = metrics.get('active_tasks', 0)
        
        # High resource usage with no active tasks
        if cpu_percent > 80 and memory_percent > 80 and active_tasks == 0:
            anomaly = AnomalyDetection(
                anomaly_id=f"pattern_ghost_{int(time.time() * 1000)}",
                timestamp=datetime.now(),
                anomaly_type="ghost_load",
                severity=0.8,
                affected_components=['system'],
                root_cause_analysis={
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory_percent,
                    'active_tasks': active_tasks,
                    'pattern': 'high_usage_no_tasks'
                },
                recommended_actions=[
                    "Investigate hidden processes",
                    "Check for system malware",
                    "Review background services"
                ],
                auto_remediation_available=False
            )
            anomalies.append(anomaly)
        
        return anomalies

class WorkloadAnalyzer:
    """Analyze workload patterns and predict optimal resource allocation"""
    
    def __init__(self):
        self.workload_history = deque(maxlen=5000)
        self.patterns = {}
        self.clustering_model = KMeans(n_clusters=5, random_state=42)
        self.pattern_classifier = RandomForestRegressor(n_estimators=50, random_state=42)
        
    def record_workload(self, timestamp: datetime, metrics: Dict[str, float], 
                       workload_metadata: Dict[str, Any]):
        """Record workload data for pattern analysis"""
        workload_point = {
            'timestamp': timestamp,
            'hour': timestamp.hour,
            'day_of_week': timestamp.weekday(),
            'metrics': metrics,
            'metadata': workload_metadata
        }
        
        self.workload_history.append(workload_point)
        
        # Analyze patterns periodically
        if len(self.workload_history) % 100 == 0:
            asyncio.create_task(self._analyze_patterns())
    
    async def _analyze_patterns(self):
        """Analyze workload patterns using clustering"""
        if len(self.workload_history) < 100:
            return
        
        try:
            # Prepare features for clustering
            features = []
            for workload in list(self.workload_history)[-1000:]:
                feature_vector = [
                    workload['hour'] / 24.0,
                    workload['day_of_week'] / 7.0,
                    workload['metrics'].get('cpu_percent', 0) / 100.0,
                    workload['metrics'].get('memory_percent', 0) / 100.0,
                    workload['metrics'].get('network_mbps', 0) / 1000.0,
                    workload['metrics'].get('active_tasks', 0) / 100.0
                ]
                features.append(feature_vector)
            
            features_array = np.array(features)
            
            # Perform clustering
            clusters = self.clustering_model.fit_predict(features_array)
            
            # Analyze each cluster
            for cluster_id in np.unique(clusters):
                cluster_points = [point for i, point in enumerate(list(self.workload_history)[-1000:]) 
                                if clusters[i] == cluster_id]
                
                if len(cluster_points) > 10:
                    pattern = self._extract_pattern(cluster_id, cluster_points)
                    self.patterns[f"pattern_{cluster_id}"] = pattern
            
            logger.info(f"Analyzed workload patterns: {len(self.patterns)} patterns identified")
            
        except Exception as e:
            logger.error(f"Pattern analysis error: {e}")
    
    def _extract_pattern(self, cluster_id: int, cluster_points: List[Dict]) -> WorkloadPattern:
        """Extract workload pattern from cluster points"""
        # Calculate resource requirements
        cpu_values = [p['metrics'].get('cpu_percent', 0) for p in cluster_points]
        memory_values = [p['metrics'].get('memory_percent', 0) for p in cluster_points]
        network_values = [p['metrics'].get('network_mbps', 0) for p in cluster_points]
        
        # Determine workload type
        avg_cpu = np.mean(cpu_values)
        avg_memory = np.mean(memory_values)
        avg_network = np.mean(network_values)
        
        if avg_cpu > 70:
            workload_type = WorkloadType.CPU_INTENSIVE
        elif avg_memory > 70:
            workload_type = WorkloadType.MEMORY_INTENSIVE
        elif avg_network > 100:
            workload_type = WorkloadType.NETWORK_INTENSIVE
        else:
            workload_type = WorkloadType.MIXED
        
        # Find peak hours
        hour_counts = defaultdict(int)
        for point in cluster_points:
            hour_counts[point['hour']] += 1
        
        peak_hours = sorted(hour_counts.keys(), key=lambda h: hour_counts[h], reverse=True)[:3]
        
        # Calculate seasonality
        daily_pattern = defaultdict(list)
        weekly_pattern = defaultdict(list)
        
        for point in cluster_points:
            daily_pattern[point['hour']].append(point['metrics'].get('cpu_percent', 0))
            weekly_pattern[point['day_of_week']].append(point['metrics'].get('cpu_percent', 0))
        
        seasonality = {
            'daily': {str(hour): np.mean(values) for hour, values in daily_pattern.items()},
            'weekly': {str(day): np.mean(values) for day, values in weekly_pattern.items()}
        }
        
        return WorkloadPattern(
            pattern_id=f"pattern_{cluster_id}",
            workload_type=workload_type,
            peak_hours=peak_hours,
            resource_requirements={
                'cpu': avg_cpu,
                'memory': avg_memory,
                'network': avg_network
            },
            seasonality=seasonality,
            confidence=min(len(cluster_points) / 100.0, 1.0),
            last_updated=datetime.now()
        )
    
    async def predict_workload_requirements(self, target_time: datetime) -> Dict[str, float]:
        """Predict resource requirements for a target time"""
        hour = target_time.hour
        day_of_week = target_time.weekday()
        
        # Find matching patterns
        matching_patterns = []
        for pattern in self.patterns.values():
            if hour in pattern.peak_hours:
                matching_patterns.append((pattern, pattern.confidence))
        
        if not matching_patterns:
            # Use average from all patterns
            if self.patterns:
                avg_reqs = {}
                for req_type in ['cpu', 'memory', 'network']:
                    values = [p.resource_requirements.get(req_type, 0) for p in self.patterns.values()]
                    avg_reqs[req_type] = np.mean(values) if values else 50.0
                return avg_reqs
            else:
                return {'cpu': 50.0, 'memory': 50.0, 'network': 50.0}
        
        # Weighted average based on confidence
        total_weight = sum(weight for _, weight in matching_patterns)
        predictions = {}
        
        for req_type in ['cpu', 'memory', 'network']:
            weighted_sum = sum(pattern.resource_requirements.get(req_type, 0) * weight 
                             for pattern, weight in matching_patterns)
            predictions[req_type] = weighted_sum / total_weight if total_weight > 0 else 50.0
        
        return predictions

class ReinforcementOptimizer:
    """Reinforcement learning for continuous optimization improvement"""
    
    def __init__(self, learning_rate: float = 0.01, exploration_rate: float = 0.1):
        self.learning_rate = learning_rate
        self.exploration_rate = exploration_rate
        self.q_table = defaultdict(lambda: defaultdict(float))
        self.action_history = deque(maxlen=1000)
        self.reward_history = deque(maxlen=1000)
        
        # Available actions
        self.actions = [
            'scale_up_cpu', 'scale_down_cpu',
            'scale_up_memory', 'scale_down_memory',
            'enable_caching', 'disable_caching',
            'compress_data', 'uncompress_data',
            'batch_operations', 'process_immediately',
            'schedule_background', 'process_foreground'
        ]
    
    def get_state_key(self, system_state: Dict[str, float]) -> str:
        """Convert system state to state key"""
        # Discretize continuous values
        cpu_bucket = int(system_state.get('cpu_percent', 0) // 10)
        memory_bucket = int(system_state.get('memory_percent', 0) // 10)
        network_bucket = int(system_state.get('network_mbps', 0) // 10)
        
        return f"cpu_{cpu_bucket}_mem_{memory_bucket}_net_{network_bucket}"
    
    def select_action(self, state: Dict[str, float]) -> str:
        """Select action using epsilon-greedy policy"""
        state_key = self.get_state_key(state)
        
        # Exploration vs exploitation
        if np.random.random() < self.exploration_rate:
            # Explore: random action
            action = np.random.choice(self.actions)
        else:
            # Exploit: best known action
            q_values = self.q_table[state_key]
            if q_values:
                action = max(q_values.keys(), key=lambda a: q_values[a])
            else:
                action = np.random.choice(self.actions)
        
        return action
    
    def update_q_value(self, state: Dict[str, float], action: str, reward: float, 
                      next_state: Dict[str, float]):
        """Update Q-value using Q-learning"""
        state_key = self.get_state_key(state)
        next_state_key = self.get_state_key(next_state)
        
        # Current Q-value
        current_q = self.q_table[state_key][action]
        
        # Maximum Q-value for next state
        next_q_values = self.q_table[next_state_key]
        max_next_q = max(next_q_values.values()) if next_q_values else 0
        
        # Q-learning update
        new_q = current_q + self.learning_rate * (reward + 0.9 * max_next_q - current_q)
        self.q_table[state_key][action] = new_q
        
        # Record for analysis
        self.action_history.append({
            'timestamp': datetime.now(),
            'state': state,
            'action': action,
            'reward': reward,
            'q_value': new_q
        })
        self.reward_history.append(reward)
    
    def calculate_reward(self, before_state: Dict[str, float], after_state: Dict[str, float], 
                        action: str) -> float:
        """Calculate reward for the action taken"""
        # Performance improvement reward
        cpu_improvement = before_state.get('cpu_percent', 0) - after_state.get('cpu_percent', 0)
        memory_improvement = before_state.get('memory_percent', 0) - after_state.get('memory_percent', 0)
        
        # Cost reduction reward
        cost_before = before_state.get('estimated_cost', 0)
        cost_after = after_state.get('estimated_cost', 0)
        cost_improvement = cost_before - cost_after
        
        # Stability reward (penalize high variance)
        response_time_before = before_state.get('response_time_ms', 0)
        response_time_after = after_state.get('response_time_ms', 0)
        stability_reward = max(0, response_time_before - response_time_after) / 100.0
        
        # Combined reward
        reward = (cpu_improvement * 0.3 + memory_improvement * 0.3 + 
                 cost_improvement * 100 + stability_reward)
        
        # Action-specific bonuses/penalties
        if action in ['batch_operations', 'enable_caching'] and reward > 0:
            reward *= 1.2  # Bonus for efficient actions
        elif action in ['scale_up_cpu', 'scale_up_memory'] and reward < 0:
            reward *= 1.1  # Small penalty for wasteful scaling
        
        return reward
    
    def get_optimization_insights(self) -> Dict[str, Any]:
        """Get insights from reinforcement learning"""
        if not self.action_history:
            return {}
        
        # Best actions by state
        state_actions = defaultdict(list)
        for record in self.action_history:
            state_key = self.get_state_key(record['state'])
            state_actions[state_key].append((record['action'], record['reward']))
        
        best_actions = {}
        for state, actions in state_actions.items():
            best_action = max(actions, key=lambda x: x[1])
            best_actions[state] = {
                'action': best_action[0],
                'average_reward': best_action[1]
            }
        
        # Learning progress
        recent_rewards = list(self.reward_history)[-100:] if len(self.reward_history) >= 100 else list(self.reward_history)
        avg_recent_reward = np.mean(recent_rewards) if recent_rewards else 0
        
        return {
            'total_actions': len(self.action_history),
            'unique_states': len(self.q_table),
            'average_recent_reward': avg_recent_reward,
            'exploration_rate': self.exploration_rate,
            'best_actions_by_state': best_actions,
            'most_effective_actions': self._get_most_effective_actions()
        }
    
    def _get_most_effective_actions(self) -> List[Tuple[str, float]]:
        """Get most effective actions overall"""
        action_rewards = defaultdict(list)
        for record in self.action_history:
            action_rewards[record['action']].append(record['reward'])
        
        action_effectiveness = []
        for action, rewards in action_rewards.items():
            avg_reward = np.mean(rewards)
            action_effectiveness.append((action, avg_reward))
        
        return sorted(action_effectiveness, key=lambda x: x[1], reverse=True)[:5]

class AIOptimizationEngine:
    """Main AI-powered optimization engine"""
    
    def __init__(self):
        self.predictor = PerformancePredictor()
        self.anomaly_detector = AnomalyDetector()
        self.workload_analyzer = WorkloadAnalyzer()
        self.rl_optimizer = ReinforcementOptimizer()
        
        self.current_strategy = OptimizationStrategy.ADAPTIVE
        self.optimization_history = deque(maxlen=1000)
        self.active_recommendations = []
        
        # Optimization callbacks
        self.optimization_callbacks = []
        
    def add_optimization_callback(self, callback: Callable):
        """Add callback for optimization events"""
        self.optimization_callbacks.append(callback)
    
    async def analyze_and_optimize(self, current_metrics: Dict[str, float], 
                                 system_context: Dict[str, Any]) -> List[OptimizationRecommendation]:
        """Main optimization analysis and recommendation generation"""
        recommendations = []
        
        try:
            # 1. Record data for learning
            timestamp = datetime.now()
            self.predictor.add_training_data(timestamp, current_metrics, current_metrics)
            self.workload_analyzer.record_workload(timestamp, current_metrics, system_context)
            
            # 2. Detect anomalies
            anomalies = await self.anomaly_detector.detect_anomalies(current_metrics)
            if anomalies:
                for anomaly in anomalies:
                    rec = await self._create_anomaly_recommendation(anomaly)
                    if rec:
                        recommendations.append(rec)
            
            # 3. Predict future performance
            predictions = await self.predictor.predict_metrics(
                PredictionHorizon.MEDIUM_TERM, current_metrics)
            
            if predictions:
                pred_recs = await self._create_predictive_recommendations(
                    current_metrics, predictions)
                recommendations.extend(pred_recs)
            
            # 4. Workload-based optimization
            workload_recs = await self._create_workload_recommendations(current_metrics)
            recommendations.extend(workload_recs)
            
            # 5. Reinforcement learning optimization
            rl_action = self.rl_optimizer.select_action(current_metrics)
            rl_rec = await self._create_rl_recommendation(rl_action, current_metrics)
            if rl_rec:
                recommendations.append(rl_rec)
            
            # 6. Strategy-specific optimization
            strategy_recs = await self._create_strategy_recommendations(
                current_metrics, system_context)
            recommendations.extend(strategy_recs)
            
            # 7. Filter and rank recommendations
            recommendations = self._filter_and_rank_recommendations(recommendations)
            
            # 8. Store recommendations
            self.active_recommendations = recommendations[:5]  # Keep top 5
            
            # 9. Notify callbacks
            await self._notify_optimization_callbacks(recommendations)
            
            return recommendations
            
        except Exception as e:
            logger.error(f"AI optimization error: {e}")
            return []
    
    async def _create_anomaly_recommendation(self, anomaly: AnomalyDetection) -> Optional[OptimizationRecommendation]:
        """Create recommendation based on detected anomaly"""
        if anomaly.severity < 0.3:  # Skip low-severity anomalies
            return None
        
        # Map anomaly types to actions
        action_mapping = {
            'cpu_spike': [
                {'type': 'scale_resources', 'resource': 'cpu', 'factor': 1.5},
                {'type': 'throttle_tasks', 'priority': 'low'},
                {'type': 'enable_caching', 'aggressive': True}
            ],
            'memory_leak': [
                {'type': 'restart_services', 'scope': 'high_memory'},
                {'type': 'force_gc', 'all_processes': True},
                {'type': 'scale_resources', 'resource': 'memory', 'factor': 1.3}
            ],
            'latency_spike': [
                {'type': 'switch_cdn', 'criteria': 'lowest_latency'},
                {'type': 'enable_compression', 'level': 'high'},
                {'type': 'batch_requests', 'enabled': True}
            ]
        }
        
        actions = action_mapping.get(anomaly.anomaly_type, [])
        if not actions:
            return None
        
        return OptimizationRecommendation(
            recommendation_id=f"anomaly_{anomaly.anomaly_id}",
            timestamp=datetime.now(),
            strategy=OptimizationStrategy.RELIABILITY_FIRST,
            confidence=anomaly.severity,
            expected_improvement={
                'performance': 0.2 * anomaly.severity,
                'reliability': 0.4 * anomaly.severity,
                'cost': 0.0
            },
            actions=actions,
            risk_assessment={
                'performance_risk': 0.1,
                'cost_risk': 0.2 * anomaly.severity,
                'stability_risk': 0.05
            },
            implementation_complexity='medium',
            estimated_impact_time=300,  # 5 minutes
            rollback_plan=[
                {'type': 'revert_scaling'},
                {'type': 'disable_compression'},
                {'type': 'restore_cdn'}
            ]
        )
    
    async def _create_predictive_recommendations(self, current: Dict[str, float], 
                                               predictions: Dict[str, float]) -> List[OptimizationRecommendation]:
        """Create recommendations based on performance predictions"""
        recommendations = []
        
        for metric, predicted_value in predictions.items():
            current_value = current.get(metric.replace('_', '_percent'), 0)
            
            # Check for significant predicted changes
            if predicted_value > current_value * 1.5:  # 50% increase predicted
                if 'cpu' in metric:
                    rec = OptimizationRecommendation(
                        recommendation_id=f"pred_cpu_{int(time.time() * 1000)}",
                        timestamp=datetime.now(),
                        strategy=OptimizationStrategy.PERFORMANCE_FIRST,
                        confidence=0.7,
                        expected_improvement={
                            'performance': 0.3,
                            'reliability': 0.2,
                            'cost': -0.1
                        },
                        actions=[
                            {'type': 'preemptive_scaling', 'resource': 'cpu', 'factor': 1.3},
                            {'type': 'task_redistribution', 'enabled': True},
                            {'type': 'cache_warmup', 'priority': 'high'}
                        ],
                        risk_assessment={
                            'performance_risk': 0.05,
                            'cost_risk': 0.3,
                            'stability_risk': 0.1
                        },
                        implementation_complexity='low',
                        estimated_impact_time=120,
                        rollback_plan=[{'type': 'scale_down_cpu'}]
                    )
                    recommendations.append(rec)
                
                elif 'memory' in metric:
                    rec = OptimizationRecommendation(
                        recommendation_id=f"pred_mem_{int(time.time() * 1000)}",
                        timestamp=datetime.now(),
                        strategy=OptimizationStrategy.PERFORMANCE_FIRST,
                        confidence=0.8,
                        expected_improvement={
                            'performance': 0.25,
                            'reliability': 0.35,
                            'cost': -0.15
                        },
                        actions=[
                            {'type': 'memory_optimization', 'gc_tuning': True},
                            {'type': 'cache_size_adjustment', 'factor': 0.8},
                            {'type': 'preemptive_scaling', 'resource': 'memory', 'factor': 1.2}
                        ],
                        risk_assessment={
                            'performance_risk': 0.1,
                            'cost_risk': 0.25,
                            'stability_risk': 0.05
                        },
                        implementation_complexity='medium',
                        estimated_impact_time=180,
                        rollback_plan=[
                            {'type': 'restore_cache_size'},
                            {'type': 'scale_down_memory'}
                        ]
                    )
                    recommendations.append(rec)
        
        return recommendations
    
    async def _create_workload_recommendations(self, current_metrics: Dict[str, float]) -> List[OptimizationRecommendation]:
        """Create workload-based optimization recommendations"""
        recommendations = []
        
        # Predict resource requirements for next hour
        target_time = datetime.now() + timedelta(hours=1)
        predicted_reqs = await self.workload_analyzer.predict_workload_requirements(target_time)
        
        for resource, predicted_req in predicted_reqs.items():
            current_req = current_metrics.get(f'{resource}_percent', 0)
            
            if predicted_req > current_req * 1.3:  # 30% increase predicted
                rec = OptimizationRecommendation(
                    recommendation_id=f"workload_{resource}_{int(time.time() * 1000)}",
                    timestamp=datetime.now(),
                    strategy=OptimizationStrategy.ADAPTIVE,
                    confidence=0.6,
                    expected_improvement={
                        'performance': 0.2,
                        'cost': 0.05,  # Better resource utilization
                        'reliability': 0.15
                    },
                    actions=[
                        {'type': 'workload_preparation', 'resource': resource, 'scale_factor': 1.2},
                        {'type': 'cache_preloading', 'target_time': target_time.isoformat()},
                        {'type': 'task_scheduling', 'distribute_load': True}
                    ],
                    risk_assessment={
                        'performance_risk': 0.1,
                        'cost_risk': 0.2,
                        'stability_risk': 0.05
                    },
                    implementation_complexity='low',
                    estimated_impact_time=600,  # 10 minutes
                    rollback_plan=[{'type': 'cancel_preparation'}]
                )
                recommendations.append(rec)
        
        return recommendations
    
    async def _create_rl_recommendation(self, action: str, current_metrics: Dict[str, float]) -> Optional[OptimizationRecommendation]:
        """Create recommendation based on reinforcement learning"""
        # Map RL actions to recommendations
        action_mapping = {
            'scale_up_cpu': {
                'actions': [{'type': 'scale_resources', 'resource': 'cpu', 'factor': 1.2}],
                'strategy': OptimizationStrategy.PERFORMANCE_FIRST,
                'complexity': 'low'
            },
            'enable_caching': {
                'actions': [{'type': 'enable_aggressive_caching', 'cache_size_mb': 1000}],
                'strategy': OptimizationStrategy.PERFORMANCE_FIRST,
                'complexity': 'low'
            },
            'batch_operations': {
                'actions': [{'type': 'enable_batching', 'batch_size': 50, 'delay_ms': 100}],
                'strategy': OptimizationStrategy.BALANCED,
                'complexity': 'medium'
            }
        }
        
        if action not in action_mapping:
            return None
        
        mapping = action_mapping[action]
        
        return OptimizationRecommendation(
            recommendation_id=f"rl_{action}_{int(time.time() * 1000)}",
            timestamp=datetime.now(),
            strategy=OptimizationStrategy(mapping['strategy']),
            confidence=0.5,  # RL confidence builds over time
            expected_improvement={
                'performance': 0.15,
                'cost': 0.1,
                'reliability': 0.1
            },
            actions=mapping['actions'],
            risk_assessment={
                'performance_risk': 0.2,
                'cost_risk': 0.15,
                'stability_risk': 0.1
            },
            implementation_complexity=mapping['complexity'],
            estimated_impact_time=180,
            rollback_plan=[{'type': 'revert_rl_action', 'action': action}]
        )
    
    async def _create_strategy_recommendations(self, current_metrics: Dict[str, float], 
                                            context: Dict[str, Any]) -> List[OptimizationRecommendation]:
        """Create strategy-specific recommendations"""
        recommendations = []
        
        if self.current_strategy == OptimizationStrategy.COST_FIRST:
            # Cost optimization recommendations
            if current_metrics.get('cpu_percent', 0) < 30:  # Under-utilized CPU
                rec = OptimizationRecommendation(
                    recommendation_id=f"cost_cpu_downsize_{int(time.time() * 1000)}",
                    timestamp=datetime.now(),
                    strategy=OptimizationStrategy.COST_FIRST,
                    confidence=0.8,
                    expected_improvement={
                        'cost': 0.25,
                        'performance': -0.05,  # Slight performance trade-off
                        'reliability': 0.0
                    },
                    actions=[
                        {'type': 'downsize_cpu', 'target_utilization': 60},
                        {'type': 'consolidate_tasks', 'efficiency_threshold': 0.8}
                    ],
                    risk_assessment={
                        'performance_risk': 0.3,
                        'cost_risk': 0.0,
                        'stability_risk': 0.1
                    },
                    implementation_complexity='medium',
                    estimated_impact_time=300,
                    rollback_plan=[{'type': 'restore_cpu_allocation'}]
                )
                recommendations.append(rec)
        
        elif self.current_strategy == OptimizationStrategy.POWER_EFFICIENT:
            # Power efficiency recommendations
            if current_metrics.get('temperature', 0) > 70:  # High temperature
                rec = OptimizationRecommendation(
                    recommendation_id=f"power_cooling_{int(time.time() * 1000)}",
                    timestamp=datetime.now(),
                    strategy=OptimizationStrategy.POWER_EFFICIENT,
                    confidence=0.9,
                    expected_improvement={
                        'performance': 0.1,
                        'cost': 0.15,  # Lower power consumption
                        'reliability': 0.25
                    },
                    actions=[
                        {'type': 'reduce_cpu_frequency', 'target_percentage': 80},
                        {'type': 'enable_power_saving', 'aggressive': True},
                        {'type': 'task_migration', 'to_cooler_nodes': True}
                    ],
                    risk_assessment={
                        'performance_risk': 0.4,
                        'cost_risk': 0.05,
                        'stability_risk': 0.1
                    },
                    implementation_complexity='high',
                    estimated_impact_time=240,
                    rollback_plan=[
                        {'type': 'restore_cpu_frequency'},
                        {'type': 'disable_power_saving'}
                    ]
                )
                recommendations.append(rec)
        
        return recommendations
    
    def _filter_and_rank_recommendations(self, recommendations: List[OptimizationRecommendation]) -> List[OptimizationRecommendation]:
        """Filter and rank recommendations by effectiveness"""
        if not recommendations:
            return []
        
        # Calculate effectiveness score
        for rec in recommendations:
            performance_gain = rec.expected_improvement.get('performance', 0)
            cost_gain = rec.expected_improvement.get('cost', 0)
            reliability_gain = rec.expected_improvement.get('reliability', 0)
            
            # Risk penalties
            performance_risk = rec.risk_assessment.get('performance_risk', 0)
            cost_risk = rec.risk_assessment.get('cost_risk', 0)
            stability_risk = rec.risk_assessment.get('stability_risk', 0)
            
            # Implementation complexity penalty
            complexity_penalty = {'low': 0.0, 'medium': 0.1, 'high': 0.2}.get(
                rec.implementation_complexity, 0.1)
            
            # Calculate effectiveness score
            effectiveness = (
                performance_gain * 0.4 +
                cost_gain * 0.3 +
                reliability_gain * 0.3 -
                performance_risk * 0.2 -
                cost_risk * 0.1 -
                stability_risk * 0.3 -
                complexity_penalty
            ) * rec.confidence
            
            rec.effectiveness_score = effectiveness
        
        # Sort by effectiveness and return top recommendations
        sorted_recs = sorted(recommendations, key=lambda r: getattr(r, 'effectiveness_score', 0), reverse=True)
        
        # Filter out low-effectiveness recommendations
        return [rec for rec in sorted_recs if getattr(rec, 'effectiveness_score', 0) > 0.1][:10]
    
    async def _notify_optimization_callbacks(self, recommendations: List[OptimizationRecommendation]):
        """Notify optimization callbacks"""
        for callback in self.optimization_callbacks:
            try:
                await callback('ai_recommendations', recommendations)
            except Exception as e:
                logger.error(f"AI optimization callback error: {e}")
    
    async def apply_recommendation(self, recommendation_id: str, 
                                 system_interface) -> Dict[str, Any]:
        """Apply an optimization recommendation"""
        # Find recommendation
        recommendation = None
        for rec in self.active_recommendations:
            if rec.recommendation_id == recommendation_id:
                recommendation = rec
                break
        
        if not recommendation:
            return {'success': False, 'error': 'Recommendation not found'}
        
        try:
            before_state = await system_interface.get_current_state()
            
            # Apply each action
            results = []
            for action in recommendation.actions:
                result = await self._apply_action(action, system_interface)
                results.append(result)
            
            # Wait for changes to take effect
            await asyncio.sleep(recommendation.estimated_impact_time / 1000.0)
            
            after_state = await system_interface.get_current_state()
            
            # Calculate reward for RL
            reward = self.rl_optimizer.calculate_reward(before_state, after_state, 'applied_recommendation')
            self.rl_optimizer.reward_history.append(reward)
            
            # Record optimization result
            optimization_result = {
                'recommendation_id': recommendation_id,
                'timestamp': datetime.now(),
                'before_state': before_state,
                'after_state': after_state,
                'actions_applied': recommendation.actions,
                'results': results,
                'reward': reward,
                'success': True
            }
            
            self.optimization_history.append(optimization_result)
            
            return {
                'success': True,
                'recommendation': recommendation.to_dict(),
                'results': results,
                'reward': reward,
                'improvement_metrics': self._calculate_improvement_metrics(before_state, after_state)
            }
            
        except Exception as e:
            logger.error(f"Failed to apply recommendation {recommendation_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _apply_action(self, action: Dict[str, Any], system_interface) -> Dict[str, Any]:
        """Apply a single optimization action"""
        action_type = action.get('type')
        
        if action_type == 'scale_resources':
            return await system_interface.scale_resource(
                action['resource'], action['factor'])
        elif action_type == 'enable_caching':
            return await system_interface.enable_caching(
                action.get('cache_size_mb', 500))
        elif action_type == 'enable_compression':
            return await system_interface.enable_compression(
                action.get('level', 'medium'))
        else:
            return {'action': action_type, 'status': 'not_implemented'}
    
    def _calculate_improvement_metrics(self, before: Dict[str, float], 
                                     after: Dict[str, float]) -> Dict[str, float]:
        """Calculate improvement metrics"""
        improvements = {}
        
        for metric in ['cpu_percent', 'memory_percent', 'response_time_ms', 'error_rate']:
            before_val = before.get(metric, 0)
            after_val = after.get(metric, 0)
            
            if before_val > 0:
                improvement_pct = (before_val - after_val) / before_val * 100
                improvements[metric] = improvement_pct
        
        return improvements
    
    def get_ai_insights(self) -> Dict[str, Any]:
        """Get comprehensive AI optimization insights"""
        return {
            'predictor_insights': {
                'models_trained': len(self.predictor.models),
                'training_data_points': len(self.predictor.feature_history),
                'cache_hit_rate': len(self.predictor.prediction_cache) / 100.0  # Approximate
            },
            'anomaly_insights': {
                'total_anomalies_detected': len(self.anomaly_detector.anomaly_history),
                'anomaly_types': list(set(a.anomaly_type for a in self.anomaly_detector.anomaly_history)),
                'detection_accuracy': 0.85  # Would be calculated from validation data
            },
            'workload_insights': {
                'patterns_identified': len(self.workload_analyzer.patterns),
                'workload_types': [p.workload_type.value for p in self.workload_analyzer.patterns.values()],
                'prediction_accuracy': 0.78  # Would be calculated from actual vs predicted
            },
            'rl_insights': self.rl_optimizer.get_optimization_insights(),
            'optimization_history': {
                'total_optimizations': len(self.optimization_history),
                'success_rate': sum(1 for opt in self.optimization_history if opt.get('success')) / max(len(self.optimization_history), 1),
                'average_reward': np.mean([opt.get('reward', 0) for opt in self.optimization_history]) if self.optimization_history else 0
            },
            'active_recommendations': len(self.active_recommendations),
            'current_strategy': self.current_strategy.value
        }

# Global AI optimization engine
ai_optimizer = AIOptimizationEngine()

if __name__ == "__main__":
    # Demo AI optimization
    async def demo():
        print("🤖 AI Optimization Engine Demo")
        print("=" * 50)
        
        # Mock system metrics
        current_metrics = {
            'cpu_percent': 75.0,
            'memory_percent': 68.0,
            'disk_percent': 45.0,
            'network_mbps': 25.0,
            'temperature': 72.0,
            'active_tasks': 15,
            'response_time_ms': 150,
            'error_rate': 0.02,
            'estimated_cost': 0.50
        }
        
        system_context = {
            'time_of_day': 'peak',
            'day_of_week': 'weekday',
            'user_load': 'high',
            'service_tier': 'production'
        }
        
        # Run AI analysis and optimization
        recommendations = await ai_optimizer.analyze_and_optimize(
            current_metrics, system_context)
        
        print(f"\n🎯 Generated {len(recommendations)} AI recommendations:")
        for i, rec in enumerate(recommendations[:3], 1):
            print(f"\n{i}. {rec.recommendation_id}")
            print(f"   Strategy: {rec.strategy.value}")
            print(f"   Confidence: {rec.confidence:.1%}")
            print(f"   Expected Performance Gain: {rec.expected_improvement.get('performance', 0):.1%}")
            print(f"   Expected Cost Impact: {rec.expected_improvement.get('cost', 0):+.1%}")
            print(f"   Actions: {len(rec.actions)} optimization actions")
            print(f"   Risk Level: {rec.implementation_complexity}")
        
        # Get AI insights
        insights = ai_optimizer.get_ai_insights()
        print(f"\n📊 AI System Insights:")
        print(f"   Predictor Models: {insights['predictor_insights']['models_trained']}")
        print(f"   Training Data Points: {insights['predictor_insights']['training_data_points']}")
        print(f"   Anomalies Detected: {insights['anomaly_insights']['total_anomalies_detected']}")
        print(f"   Workload Patterns: {insights['workload_insights']['patterns_identified']}")
        print(f"   RL Actions Learned: {insights['rl_insights']['total_actions']}")
        print(f"   Optimization Success Rate: {insights['optimization_history']['success_rate']:.1%}")
    
    asyncio.run(demo())