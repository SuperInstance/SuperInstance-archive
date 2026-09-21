"""
Predictive Performance Optimization System
Real-time ML-powered performance monitoring and optimization
"""

import torch
import torch.nn as nn
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging
import time
import threading
from collections import deque
import json

class MetricType(Enum):
    CPU_USAGE = "cpu_usage"
    MEMORY_USAGE = "memory_usage"
    NETWORK_LATENCY = "network_latency"
    DATABASE_RESPONSE = "database_response"
    API_RESPONSE_TIME = "api_response_time"
    CONCURRENT_USERS = "concurrent_users"
    ERROR_RATE = "error_rate"
    THROUGHPUT = "throughput"

class OptimizationAction(Enum):
    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down"
    CACHE_PRELOAD = "cache_preload"
    REDISTRIBUTE_LOAD = "redistribute_load"
    OPTIMIZE_QUERIES = "optimize_queries"
    INCREASE_CONNECTION_POOL = "increase_connection_pool"
    ENABLE_COMPRESSION = "enable_compression"
    ADJUST_TIMEOUT = "adjust_timeout"

@dataclass
class PerformanceMetric:
    timestamp: float
    metric_type: MetricType
    value: float
    service_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class OptimizationRecommendation:
    action: OptimizationAction
    confidence: float
    expected_improvement: float
    service_id: str
    parameters: Dict[str, Any]
    urgency: int  # 1-10 scale
    estimated_impact: str  # "low", "medium", "high"

@dataclass
class PerformancePrediction:
    timestamp: float
    predicted_values: Dict[MetricType, float]
    confidence_intervals: Dict[MetricType, Tuple[float, float]]
    alert_level: str  # "green", "yellow", "red"

class TimeSeriesPredictor(nn.Module):
    """LSTM-based time series predictor for performance metrics"""
    
    def __init__(self, input_size: int = 8, hidden_size: int = 64, 
                 num_layers: int = 2, output_size: int = 8, sequence_length: int = 20):
        super().__init__()
        
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.sequence_length = sequence_length
        
        # LSTM for time series prediction
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=0.2 if num_layers > 1 else 0
        )
        
        # Attention mechanism for important time steps
        self.attention = nn.Sequential(
            nn.Linear(hidden_size, hidden_size // 2),
            nn.Tanh(),
            nn.Linear(hidden_size // 2, 1),
            nn.Softmax(dim=1)
        )
        
        # Output layers
        self.output_layer = nn.Sequential(
            nn.Linear(hidden_size, hidden_size // 2),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_size // 2, output_size)
        )
        
        # Confidence estimator
        self.confidence_layer = nn.Sequential(
            nn.Linear(hidden_size, hidden_size // 2),
            nn.ReLU(),
            nn.Linear(hidden_size // 2, output_size),
            nn.Sigmoid()
        )
    
    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        batch_size = x.size(0)
        
        # LSTM forward pass
        lstm_out, (hidden, cell) = self.lstm(x)
        
        # Apply attention
        attention_weights = self.attention(lstm_out)
        context = torch.sum(attention_weights * lstm_out, dim=1)
        
        # Generate predictions and confidence
        predictions = self.output_layer(context)
        confidence = self.confidence_layer(context)
        
        return predictions, confidence

class OptimizationRecommender(nn.Module):
    """Neural network for optimization recommendation"""
    
    def __init__(self, input_size: int = 16, num_actions: int = 8):
        super().__init__()
        
        self.feature_encoder = nn.Sequential(
            nn.Linear(input_size, 128),
            nn.ReLU(),
            nn.BatchNorm1d(128),
            nn.Dropout(0.3),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.BatchNorm1d(64),
            nn.Dropout(0.2)
        )
        
        # Action recommendation head
        self.action_head = nn.Sequential(
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, num_actions)
        )
        
        # Confidence head
        self.confidence_head = nn.Sequential(
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, num_actions),
            nn.Sigmoid()
        )
        
        # Impact prediction head
        self.impact_head = nn.Sequential(
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, num_actions),
            nn.ReLU()  # Positive impact values
        )
    
    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        features = self.feature_encoder(x)
        
        action_logits = self.action_head(features)
        confidence = self.confidence_head(features)
        impact = self.impact_head(features)
        
        return action_logits, confidence, impact

class PredictivePerformanceOptimizer:
    """Main performance optimization system with predictive capabilities"""
    
    def __init__(self, prediction_horizon: int = 10):
        self.logger = logging.getLogger(__name__)
        
        # Models
        self.predictor = TimeSeriesPredictor()
        self.recommender = OptimizationRecommender()
        
        # Data storage
        self.metrics_buffer = deque(maxlen=1000)  # Store recent metrics
        self.historical_data = {}  # Service-specific historical data
        
        # Configuration
        self.prediction_horizon = prediction_horizon
        self.metric_types = list(MetricType)
        self.optimization_actions = list(OptimizationAction)
        
        # Performance thresholds
        self.thresholds = {
            MetricType.CPU_USAGE: {'warning': 70, 'critical': 85},
            MetricType.MEMORY_USAGE: {'warning': 75, 'critical': 90},
            MetricType.NETWORK_LATENCY: {'warning': 200, 'critical': 500},
            MetricType.DATABASE_RESPONSE: {'warning': 100, 'critical': 500},
            MetricType.API_RESPONSE_TIME: {'warning': 200, 'critical': 1000},
            MetricType.ERROR_RATE: {'warning': 1, 'critical': 5},
            MetricType.THROUGHPUT: {'warning_low': 100, 'critical_low': 50}
        }
        
        # Optimization history for learning
        self.optimization_history = []
        
        # Background monitoring thread
        self.monitoring_active = False
        self.monitoring_thread = None
        
        self.logger.info("Predictive Performance Optimizer initialized")
    
    def add_metric(self, metric: PerformanceMetric):
        """Add a new performance metric"""
        self.metrics_buffer.append(metric)
        
        # Store in service-specific history
        if metric.service_id not in self.historical_data:
            self.historical_data[metric.service_id] = {mt: deque(maxlen=200) for mt in MetricType}
        
        self.historical_data[metric.service_id][metric.metric_type].append(
            (metric.timestamp, metric.value)
        )
    
    def predict_performance(self, service_id: str, 
                          time_horizon: int = None) -> Optional[PerformancePrediction]:
        """Predict future performance metrics for a service"""
        if time_horizon is None:
            time_horizon = self.prediction_horizon
        
        if service_id not in self.historical_data:
            self.logger.warning(f"No historical data for service {service_id}")
            return None
        
        # Prepare input data
        input_sequences = self._prepare_prediction_input(service_id)
        if input_sequences is None:
            return None
        
        # Make predictions
        with torch.no_grad():
            predictions, confidence = self.predictor(input_sequences.unsqueeze(0))
            predictions = predictions.squeeze(0)
            confidence = confidence.squeeze(0)
        
        # Convert to metric predictions
        predicted_values = {}
        confidence_intervals = {}
        
        for i, metric_type in enumerate(self.metric_types):
            pred_value = predictions[i].item()
            conf_value = confidence[i].item()
            
            # Calculate confidence interval
            uncertainty = (1 - conf_value) * pred_value * 0.3  # 30% uncertainty range
            lower_bound = max(0, pred_value - uncertainty)
            upper_bound = pred_value + uncertainty
            
            predicted_values[metric_type] = pred_value
            confidence_intervals[metric_type] = (lower_bound, upper_bound)
        
        # Determine alert level
        alert_level = self._calculate_alert_level(predicted_values)
        
        return PerformancePrediction(
            timestamp=time.time() + time_horizon * 60,  # Future timestamp
            predicted_values=predicted_values,
            confidence_intervals=confidence_intervals,
            alert_level=alert_level
        )
    
    def get_optimization_recommendations(self, service_id: str) -> List[OptimizationRecommendation]:
        """Get optimization recommendations based on current and predicted performance"""
        recommendations = []
        
        # Get current metrics
        current_metrics = self._get_current_metrics(service_id)
        if not current_metrics:
            return recommendations
        
        # Get predictions
        prediction = self.predict_performance(service_id)
        if not prediction:
            return recommendations
        
        # Prepare input for recommender
        recommender_input = self._prepare_recommender_input(current_metrics, prediction)
        
        if recommender_input is not None:
            with torch.no_grad():
                action_logits, confidence, impact = self.recommender(recommender_input.unsqueeze(0))
                
                action_probs = torch.softmax(action_logits, dim=-1).squeeze(0)
                confidence = confidence.squeeze(0)
                impact = impact.squeeze(0)
            
            # Generate recommendations
            for i, action in enumerate(self.optimization_actions):
                if action_probs[i] > 0.3:  # Threshold for recommendation
                    recommendations.append(OptimizationRecommendation(
                        action=action,
                        confidence=confidence[i].item(),
                        expected_improvement=impact[i].item(),
                        service_id=service_id,
                        parameters=self._get_action_parameters(action, current_metrics),
                        urgency=self._calculate_urgency(current_metrics, prediction),
                        estimated_impact=self._classify_impact(impact[i].item())
                    ))
        
        # Sort by confidence and expected improvement
        recommendations.sort(key=lambda x: (x.confidence, x.expected_improvement), reverse=True)
        
        return recommendations[:5]  # Return top 5 recommendations
    
    def apply_optimization(self, recommendation: OptimizationRecommendation) -> Dict[str, Any]:
        """Apply an optimization recommendation"""
        self.logger.info(f"Applying optimization: {recommendation.action.value} "
                        f"for service {recommendation.service_id}")
        
        result = {
            'action': recommendation.action.value,
            'service_id': recommendation.service_id,
            'applied_at': time.time(),
            'success': False,
            'message': '',
            'metrics_before': self._get_current_metrics(recommendation.service_id)
        }
        
        try:
            # Simulate optimization application
            # In real implementation, this would interact with infrastructure APIs
            success = self._execute_optimization_action(recommendation)
            
            result['success'] = success
            result['message'] = f"Successfully applied {recommendation.action.value}" if success else "Failed to apply optimization"
            
            # Record optimization for learning
            self.optimization_history.append({
                'timestamp': time.time(),
                'recommendation': recommendation,
                'result': result
            })
            
        except Exception as e:
            result['message'] = f"Error applying optimization: {str(e)}"
            self.logger.error(f"Optimization failed: {e}")
        
        return result
    
    def start_monitoring(self, interval: int = 30):
        """Start background performance monitoring"""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, args=(interval,))
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()
        
        self.logger.info(f"Performance monitoring started with {interval}s interval")
    
    def stop_monitoring(self):
        """Stop background performance monitoring"""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join()
        
        self.logger.info("Performance monitoring stopped")
    
    def _prepare_prediction_input(self, service_id: str) -> Optional[torch.Tensor]:
        """Prepare input sequence for time series prediction"""
        if service_id not in self.historical_data:
            return None
        
        # Get recent data for all metric types
        sequences = []
        min_length = float('inf')
        
        for metric_type in self.metric_types:
            data = list(self.historical_data[service_id][metric_type])
            if len(data) < self.predictor.sequence_length:
                return None
            
            # Extract values (ignore timestamps for now)
            values = [d[1] for d in data[-self.predictor.sequence_length:]]
            sequences.append(values)
            min_length = min(min_length, len(values))
        
        if min_length < self.predictor.sequence_length:
            return None
        
        # Create tensor
        input_tensor = torch.tensor(sequences, dtype=torch.float32).transpose(0, 1)
        return input_tensor
    
    def _prepare_recommender_input(self, current_metrics: Dict[MetricType, float], 
                                 prediction: PerformancePrediction) -> Optional[torch.Tensor]:
        """Prepare input for optimization recommender"""
        features = []
        
        # Current metrics (8 features)
        for metric_type in self.metric_types:
            features.append(current_metrics.get(metric_type, 0.0))
        
        # Predicted metrics (8 features)
        for metric_type in self.metric_types:
            features.append(prediction.predicted_values.get(metric_type, 0.0))
        
        return torch.tensor(features, dtype=torch.float32)
    
    def _get_current_metrics(self, service_id: str) -> Dict[MetricType, float]:
        """Get current metrics for a service"""
        current_metrics = {}
        
        if service_id in self.historical_data:
            for metric_type in self.metric_types:
                data = list(self.historical_data[service_id][metric_type])
                if data:
                    current_metrics[metric_type] = data[-1][1]  # Latest value
                else:
                    current_metrics[metric_type] = 0.0
        
        return current_metrics
    
    def _calculate_alert_level(self, predicted_values: Dict[MetricType, float]) -> str:
        """Calculate alert level based on predicted values"""
        critical_count = 0
        warning_count = 0
        
        for metric_type, value in predicted_values.items():
            if metric_type in self.thresholds:
                thresholds = self.thresholds[metric_type]
                
                if 'critical' in thresholds and value > thresholds['critical']:
                    critical_count += 1
                elif 'critical_low' in thresholds and value < thresholds['critical_low']:
                    critical_count += 1
                elif 'warning' in thresholds and value > thresholds['warning']:
                    warning_count += 1
                elif 'warning_low' in thresholds and value < thresholds['warning_low']:
                    warning_count += 1
        
        if critical_count > 0:
            return "red"
        elif warning_count > 0:
            return "yellow"
        else:
            return "green"
    
    def _get_action_parameters(self, action: OptimizationAction, 
                             current_metrics: Dict[MetricType, float]) -> Dict[str, Any]:
        """Get parameters for optimization actions"""
        params = {}
        
        if action == OptimizationAction.SCALE_UP:
            params['scale_factor'] = 1.5
            params['max_instances'] = 10
        elif action == OptimizationAction.SCALE_DOWN:
            params['scale_factor'] = 0.7
            params['min_instances'] = 1
        elif action == OptimizationAction.INCREASE_CONNECTION_POOL:
            current_pool = current_metrics.get(MetricType.CONCURRENT_USERS, 100)
            params['new_pool_size'] = int(current_pool * 1.3)
        
        return params
    
    def _calculate_urgency(self, current_metrics: Dict[MetricType, float], 
                          prediction: PerformancePrediction) -> int:
        """Calculate urgency level for optimization"""
        urgency = 1
        
        # Check current critical metrics
        for metric_type, value in current_metrics.items():
            if metric_type in self.thresholds:
                thresholds = self.thresholds[metric_type]
                if 'critical' in thresholds and value > thresholds['critical']:
                    urgency = max(urgency, 9)
                elif 'warning' in thresholds and value > thresholds['warning']:
                    urgency = max(urgency, 6)
        
        # Check predicted metrics
        if prediction.alert_level == "red":
            urgency = max(urgency, 8)
        elif prediction.alert_level == "yellow":
            urgency = max(urgency, 4)
        
        return urgency
    
    def _classify_impact(self, impact_value: float) -> str:
        """Classify the expected impact level"""
        if impact_value > 0.7:
            return "high"
        elif impact_value > 0.3:
            return "medium"
        else:
            return "low"
    
    def _execute_optimization_action(self, recommendation: OptimizationRecommendation) -> bool:
        """Execute the optimization action (placeholder implementation)"""
        # In real implementation, this would interact with:
        # - Container orchestration systems (Docker, Kubernetes)
        # - Cloud provider APIs (AWS, Azure, GCP)
        # - Database management systems
        # - Load balancers and caches
        
        self.logger.info(f"Executing {recommendation.action.value} with parameters: {recommendation.parameters}")
        
        # Simulate execution time
        time.sleep(0.1)
        
        # Simulate success rate based on confidence
        return recommendation.confidence > 0.5
    
    def _monitoring_loop(self, interval: int):
        """Background monitoring loop"""
        while self.monitoring_active:
            try:
                # Collect metrics from all services
                for service_id in self.historical_data.keys():
                    # Get recommendations
                    recommendations = self.get_optimization_recommendations(service_id)
                    
                    # Auto-apply high-confidence, low-risk optimizations
                    for rec in recommendations:
                        if (rec.confidence > 0.9 and 
                            rec.urgency >= 7 and 
                            rec.action in [OptimizationAction.CACHE_PRELOAD, 
                                         OptimizationAction.ENABLE_COMPRESSION]):
                            self.apply_optimization(rec)
                
                time.sleep(interval)
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                time.sleep(5)

# Example usage and testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Initialize optimizer
    optimizer = PredictivePerformanceOptimizer()
    
    # Add some sample metrics
    import random
    current_time = time.time()
    
    for i in range(50):
        for service_id in ['dmlog-service', 'auth-service', 'database']:
            # Generate realistic metrics
            cpu_usage = 50 + random.uniform(-20, 30)
            memory_usage = 60 + random.uniform(-15, 25)
            api_response = 150 + random.uniform(-50, 100)
            
            optimizer.add_metric(PerformanceMetric(
                timestamp=current_time - (50-i) * 60,  # 1 minute intervals
                metric_type=MetricType.CPU_USAGE,
                value=max(0, min(100, cpu_usage)),
                service_id=service_id
            ))
            
            optimizer.add_metric(PerformanceMetric(
                timestamp=current_time - (50-i) * 60,
                metric_type=MetricType.API_RESPONSE_TIME,
                value=max(50, api_response),
                service_id=service_id
            ))
    
    # Test prediction
    prediction = optimizer.predict_performance('dmlog-service')
    if prediction:
        print(f"Prediction for dmlog-service:")
        print(f"Alert level: {prediction.alert_level}")
        print(f"CPU prediction: {prediction.predicted_values[MetricType.CPU_USAGE]:.2f}")
        print(f"API response prediction: {prediction.predicted_values[MetricType.API_RESPONSE_TIME]:.2f}")
    
    # Get recommendations
    recommendations = optimizer.get_optimization_recommendations('dmlog-service')
    print(f"\nOptimization recommendations: {len(recommendations)}")
    
    for i, rec in enumerate(recommendations[:3]):
        print(f"{i+1}. {rec.action.value} (confidence: {rec.confidence:.3f}, "
              f"improvement: {rec.expected_improvement:.3f})")
    
    # Start monitoring (uncomment for background monitoring)
    # optimizer.start_monitoring(interval=10)
    # time.sleep(30)
    # optimizer.stop_monitoring()